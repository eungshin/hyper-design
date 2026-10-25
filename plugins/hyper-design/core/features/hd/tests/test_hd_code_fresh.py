"""다시 열면 늘 지금 코드의 캔버스(사용자 버그: '먼저 만든 프로젝트는 새 UI 가 안 나와요').

까닭: 떠 있는 도우미·허브 세션을 다시 쓰면 빌드를 건너뛰어, 그때 구운 index.html(과 그 프로세스의 옛 Python)이 그대로 나갔다.
여기서는 임시 HD_HOME · 빈 포트의 진짜 도우미(helper.py 자식 프로세스) · 이 프로세스 안 허브(make_hub)로:
- 옛 도장 index.html + 새 코드 도우미 → 다시 열기 = 같은 도우미, 페이지만 지금 도장으로 다시 빌드
- 옛 코드 도우미(표지 code 가 옛것) · 쉬는 중 → 끄고 새 도우미 / AI 덮개 중 → 프로세스는 그대로(한 줄 알림), 페이지만 다시 빌드
- 허브: 열린 세션의 옛 페이지 → 다시 열기·페이지 받기에서 다시 빌드 · 따로 떠 있는 옛 도우미는 끄고 허브 세션으로 · 허브 자신이 옛것이면 알림
빌드는 작업 트리 build_canvas.py + HD_CODE_STAMP(build_ref 가 넘기는 것과 같은 길) — 커밋 전에도 새 build_canvas 를 시험한다.
12270·12279·실제 ~/.hyper-design 은 건드리지 않는다.
"""
import json, os, subprocess, sys, threading, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path[:0] = [str(hdfix.HD), str(hdfix.HD.parent / "home"), str(hdfix.CANVAS)]
import hd_client as C  # noqa: E402
import home_client as H  # noqa: E402
import home_server  # noqa: E402

pytestmark = pytest.mark.slow

CORE = hdfix.CANVAS.parents[1]
OLD = "g:0123456789abcdef"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def head_stamp():
    r = subprocess.run(["git", "-C", str(CORE), "rev-parse", "HEAD:./"], capture_output=True, text=True, creationflags=NO_WINDOW)
    assert r.returncode == 0, r.stderr
    return "g:" + r.stdout.strip()[:16]


NOW = head_stamp()


def wt_build(out, stamp=NOW):
    """작업 트리 build_canvas.py 로 빌드(build_ref 처럼 HD_CODE_STAMP 를 넘김) → (code, 끝 줄)."""
    r = subprocess.run([sys.executable, str(hdfix.CANVAS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, HD_CODE_STAMP=stamp, PYTHONIOENCODING="utf-8"), creationflags=NO_WINDOW)
    return r.returncode, (r.stdout + r.stderr).strip()


def page(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8")


def stamp_of(html):
    import re
    m = re.search(r'<meta name="hd-code" content="([^"]*)"', html)
    return m.group(1) if m else None


def mark_old(out, pid):
    """떠 있는 도우미를 '옛 코드로 뜬 것'처럼: 표지·.hd-helper.json 의 code 를 옛 도장으로(옛 도우미는 code 칸이 아예 없다)."""
    for p in (Path(os.environ["HD_HOME"]) / "active" / ("%d.json" % pid), Path(out) / ".hd-helper.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        d.pop("code", None)
        p.write_text(json.dumps(d), encoding="utf-8")


@pytest.fixture()
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    monkeypatch.setenv("HD_HOME", str(h))
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD", "HD_CODE_STAMP"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(C, "build", lambda out: wt_build(out))
    monkeypatch.setattr(C, "LOCAL", None)
    return h


@pytest.fixture()
def old_out(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    assert wt_build(out, OLD)[0] == 0
    assert stamp_of((out / "index.html").read_text(encoding="utf-8")) == OLD
    return out


def test_reopen_rebuilds_old_page_on_the_same_helper(home, old_out):
    p, url = hdfix.start_helper(old_out, home)
    try:
        e, m, reused = C.open_project(str(old_out))
        assert reused and m["pid"] == p.pid, "새 코드 도우미는 그대로 쓴다"
        assert stamp_of(page(m["url"])) == NOW, "다시 열면 지금 코드의 캔버스(옛 index.html 을 다시 빌드)"
    finally:
        hdfix.stop_helper(p)


def test_reopen_restarts_an_idle_helper_running_old_code(home, old_out):
    p, url = hdfix.start_helper(old_out, home)
    new = None
    try:
        mark_old(old_out, p.pid)
        e, new, reused = C.open_project(str(old_out))
        assert new["pid"] != p.pid and not reused, "옛 코드로 뜬 쉬는 도우미는 끄고 새로 띄운다"
        assert p.wait(10) is not None
        assert new.get("code") == NOW and stamp_of(page(new["url"])) == NOW
        assert new["port"] == int(url.split(":")[2].split("/")[0]), "같은 포트(주소·localStorage 가 이어짐)"
    finally:
        hdfix.stop_helper(p)
        if new is not None:
            C.stop(new)


def test_reopen_keeps_a_busy_old_helper_and_says_so(home, old_out, capsys):
    p, url = hdfix.start_helper(old_out, home)
    try:
        m0 = C.serving(old_out)
        C.claim(m0, "list", by="ai", note="고치는 중")
        mark_old(old_out, p.pid)
        e, m, reused = C.open_project(str(old_out))
        assert reused and m["pid"] == p.pid, "AI 덮개 중이면 옛 도우미를 끄지 않는다"
        assert "작업 중" in capsys.readouterr().err
        assert stamp_of(page(m["url"])) == NOW, "프로세스는 그대로여도 화면은 지금 코드"
    finally:
        hdfix.stop_helper(p)


def session_build(out):                                          # 세션의 다시 빌드(허브 Builder) — 같은 작업 트리 빌드
    code, tail = wt_build(out)
    return subprocess.CompletedProcess([], code, tail, "")


@pytest.fixture()
def hub(home, tmp_path):
    srv = home_server.make_hub(0, renderer=lambda *a, **k: None, picker=lambda: None, build=session_build, paseo=str(tmp_path / "no-paseo"))
    H.write_hub(srv.url, srv.server_address[1], srv.token)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        H.clear_hub()
        C.LOCAL = None


def test_hub_session_page_is_rebuilt_on_reopen_and_on_load(hub, old_out):
    reg = hub.registry
    e, m, reused = reg.open(str(old_out))
    assert not reused and stamp_of(page(m["url"])) == NOW
    assert wt_build(old_out, OLD)[0] == 0                       # 그 사이 옛 코드로 구운 페이지(이번 버그의 상태)
    e, m, reused = reg.open(str(old_out))
    assert reused and stamp_of(page(m["url"])) == NOW, "허브의 열린 세션도 다시 열면 지금 코드"
    assert wt_build(old_out, OLD)[0] == 0
    assert stamp_of(page(m["url"])) == NOW, "열기 없이 페이지만 다시 받아도(F5 · 즐겨찾기) 지금 코드"


def test_hub_replaces_an_idle_old_helper_with_its_session(hub, old_out):
    p, url = hdfix.start_helper(old_out, Path(os.environ["HD_HOME"]))
    try:
        mark_old(old_out, p.pid)
        e, m, reused = hub.registry.open(str(old_out))
        assert m.get("hub") is True and not reused, "옛 도우미 대신 허브 세션"
        assert p.wait(10) is not None
        assert stamp_of(page(m["url"])) == NOW
    finally:
        hdfix.stop_helper(p)


def test_stale_hub_says_so_once_per_open(hub, old_out):
    hub.registry.code = OLD                                       # 이 허브가 옛 코드로 떠 있다
    e, m, reused = hub.registry.open(str(old_out))
    assert m.get("notice") and "허브를 다시 켜면" in m["notice"]
    assert stamp_of(page(m["url"])) == NOW, "페이지는 그래도 지금 코드로"
    body = page(hub.url)
    assert "__hdStale=true" in body, "홈 화면도 알린다"


def test_home_page_restart_button_route_spawns_the_restarter(home, tmp_path):
    seen = []
    srv = home_server.make_hub(0, renderer=lambda *a, **k: None, picker=lambda: None, build=session_build, paseo=str(tmp_path / "no-paseo"),
                               restarter=seen.append)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = "http://127.0.0.1:%d" % srv.server_address[1]
        assert C.call({"port": srv.server_address[1], "token": "wrong"}, "/api/hub/restart", {})[0] == 403
        assert C.call({"port": srv.server_address[1], "token": srv.token}, "/api/hub/restart", {}) == (200, {"restarting": True})
        assert seen == [srv.server_address[1]], "같은 포트로 다시 띄우게"
        assert "__hdStale" not in page(base + "/"), "지금 코드 허브는 알리지 않는다"
    finally:
        srv.shutdown()
        srv.server_close()


def test_hd_home_restart_replaces_the_running_hub(home, tmp_path):
    env = dict(hdfix.env(home), HD_HUB_PORT="0")
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        env.pop(k, None)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    hd_py = hdfix.HD / "hd.py"

    def start(*extra):
        log = open(tmp_path / ("hub-%d.log" % len(list(tmp_path.glob("hub-*.log")))), "w", encoding="utf-8")
        p = subprocess.Popen([sys.executable, str(hd_py), "home", "--no-browser", "--port", "0", *extra], stdout=subprocess.PIPE, stderr=log,
                             text=True, encoding="utf-8", env=env, creationflags=flags)
        return p, p.stdout.readline().strip()
    a, url_a = start()
    b = None
    try:
        assert "/?hd=" in url_a and json.loads((home / "home.json").read_text(encoding="utf-8"))["code"] == NOW, "허브는 뜬 코드를 기록에 적는다"
        b, url_b = start("--restart")
        assert "/?hd=" in url_b and url_b != url_a
        assert a.wait(15) is not None, "떠 있던 허브는 /api/hub/stop 으로 스스로 끝난다"
        assert json.loads((home / "home.json").read_text(encoding="utf-8"))["pid"] == b.pid
    finally:
        hdfix.stop_helper(a)
        if b is not None:
            hdfix.stop_helper(b)
