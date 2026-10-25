"""도우미 포트 유지(#270) · 읽기는 빌드를 기다리지 않음 · 한 out 에 도우미 하나(#271). 자식 프로세스·HTTP, 브라우저 없음.
사용자의 도우미(그 포트)는 건드리지 않는다 — 임시 out 과 빈 포트만."""
import json, socket, subprocess, sys, threading, time, urllib.parse, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path.insert(0, str(hdfix.CANVAS))
import helper  # noqa: E402
import hd_client  # noqa: E402


def port_of(url):
    return urllib.parse.urlparse(url).port


def record(out):
    return json.loads((out / ".hd-helper.json").read_text(encoding="utf-8"))


def test_restart_on_same_out_keeps_port(tmp_path):
    out, home = hdfix.make_out(tmp_path), tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    try:
        port = port_of(url)
        assert record(out)["port"] == port and record(out)["pid"] == p.pid
    finally:
        assert hdfix.stop_helper(p)
    assert record(out) == {"port": port}, "정상 종료 뒤엔 포트만 남는다(주소·pid 없음 → 스킬은 다시 띄움)"
    p2, url2 = hdfix.start_helper(out, home)
    try:
        assert port_of(url2) == port, "같은 포트 → 같은 origin → localStorage 가 이어진다"
        assert url2 != url, "토큰은 실행마다 새로"
    finally:
        hdfix.stop_helper(p2)


def test_busy_last_port_falls_back_and_logs(tmp_path):
    out, home = hdfix.make_out(tmp_path), tmp_path / "home"
    blocker = socket.socket()                        # 지난 포트를 다른 프로그램이 쥐고 있다
    try:
        blocker.bind(("127.0.0.1", 0)); blocker.listen(1)
        busy = blocker.getsockname()[1]
        (out / ".hd-helper.json").write_text(json.dumps({"port": busy}), encoding="utf-8")
        p, url = hdfix.start_helper(out, home)
        try:
            assert port_of(url) not in (busy, None)
        finally:
            hdfix.stop_helper(p)
        assert "지난번 포트 %d" % busy in hdfix.stderr_of(p)
    finally:
        blocker.close()


def test_second_start_on_same_out_is_refused(tmp_path):
    out, home = hdfix.make_out(tmp_path), tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    try:
        r = subprocess.run([sys.executable, str(hdfix.HELPER), str(out), "--no-open"], capture_output=True, text=True, encoding="utf-8",
                           env=hdfix.env(home), timeout=30)
        assert r.returncode != 0 and "이미 도우미가 떠 있어요" in r.stderr and url in r.stderr, (r.returncode, r.stderr)
        assert record(out)["pid"] == p.pid, "첫 도우미의 기록은 그대로"
        assert len(list((home / "active").glob("*.json"))) == 1, "둘째 표지 없음"
    finally:
        hdfix.stop_helper(p)


def test_dead_pid_record_is_overwritten(tmp_path):
    out, home = hdfix.make_out(tmp_path), tmp_path / "home"
    dead = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
    pid = int(dead.stdout)
    (out / ".hd-helper.json").write_text(json.dumps({"url": "http://127.0.0.1:9/index.html?hd=old", "pid": pid, "port": 9, "token": "old"}),
                                         encoding="utf-8")
    p, url = hdfix.start_helper(out, home)
    try:
        assert record(out)["pid"] == p.pid and record(out)["url"] == url
    finally:
        hdfix.stop_helper(p)


def test_hd_open_reuses_helper_named_in_record(tmp_path, monkeypatch):
    out, home = hdfix.make_out(tmp_path), tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    try:
        monkeypatch.setenv("HD_HOME", str(tmp_path / "other-home"))   # 표지가 보이지 않는 곳 — .hd-helper.json 만으로 찾아야 한다
        monkeypatch.setattr(hd_client, "spawn_helper", lambda *a, **k: pytest.fail("둘째 도우미를 띄우면 안 된다"))
        e, m, reused = hd_client.open_project(str(out))
        assert reused and m["url"] == url and m["pid"] == p.pid
    finally:
        hdfix.stop_helper(p)


def test_state_read_does_not_wait_for_build(tmp_path, monkeypatch):
    out = hdfix.make_out(tmp_path)
    entered, release = threading.Event(), threading.Event()

    def slow_build(o):                               # 테스트 갈고리: 빌드를 놓아줄 때까지 붙든다(sleep 없음)
        entered.set()
        assert release.wait(20)
        return subprocess.CompletedProcess([], 0, "", "")

    monkeypatch.setattr(helper, "_build", slow_build)
    srv = helper.make_server(out)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base, tok = "http://127.0.0.1:%d" % srv.server_address[1], srv.token
    res = {}

    def apply():
        req = urllib.request.Request(base + "/api/apply", method="POST", headers={"X-HD-Token": tok, "Content-Type": "application/json"},
                                     data=json.dumps({"edits": [{"id": "e1", "screen": "home", "edit": "title", "value": "홈"}]}).encode("utf-8"))
        with urllib.request.urlopen(req, timeout=30) as r:
            res["apply"] = json.loads(r.read())

    t = threading.Thread(target=apply)
    t.start()
    try:
        assert entered.wait(10), "apply 가 빌드에 들어가지 않았다"
        t0 = time.monotonic()
        assert hd_client.ping({"port": srv.server_address[1], "token": tok}, timeout=1.0), "빌드 중에도 hd 핑이 답해야 한다"
        req = urllib.request.Request(base + "/api/state", headers={"X-HD-Token": tok})
        with urllib.request.urlopen(req, timeout=1.0) as r:
            assert json.loads(r.read())["rev"] == 3
        with urllib.request.urlopen(base + "/index.html", timeout=1.0) as r:
            assert b"__hdState" in r.read()
        assert time.monotonic() - t0 < 1.0
        assert t.is_alive(), "읽는 동안 빌드는 아직 붙들려 있었다"
    finally:
        release.set(); t.join(30)
        srv.shutdown(); srv.server_close()
    assert res["apply"]["applied"] == ["e1"]
