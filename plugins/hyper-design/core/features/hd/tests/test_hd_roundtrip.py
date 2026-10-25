"""hd 왕복 통합 — stop · attach · wait 와 도우미 GET /api/projects · POST /api/open. HD_HOME 임시, 도우미는 이 테스트가 띄운 자식만. 브라우저 없음."""
import json, os, subprocess, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

HD_PY = hdfix.HD / "hd.py"


def env(home):
    e = hdfix.env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        e.pop(k, None)
    return e


def hd(home, *args, timeout=60):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=env(home), timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def hdj(home, *args):
    code, out, err = hd(home, *args, "--json")
    return code, json.loads(out), err


def marker(home, pid):
    return home / "active" / ("%d.json" % pid)


def api(url, path, body=None, method=None):
    base, token = url.split("/index.html?hd=")
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                                 method=method or ("GET" if body is None else "POST"),
                                 headers={"X-HD-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def port_of(url):
    return int(url.split(":")[2].split("/")[0])


def port_open(port):
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def test_stop_by_route_removes_marker_and_closes_port_keeps_link(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    try:
        assert marker(home, p.pid).is_file()
        code, d, err = hdj(home, "stop")
        assert code == 0 and d["how"] == "route" and d["pid"] == p.pid, err
        assert p.wait(5) is not None, "도우미 프로세스가 끝남"
        assert not marker(home, p.pid).exists() and not port_open(port_of(url))
        reg = json.loads((home / "projects.json").read_text(encoding="utf-8"))
        assert [e["name"] for e in reg["projects"]] == ["proj-a"], "링크는 그대로"
        code, o, err = hd(home, "stop")
        assert code == 1 and "떠 있는 캔버스가 없어요" in err
    finally:
        if p.poll() is None:
            p.kill(); p.wait()


DEAF = "import socket,time\ns=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(5)\nprint(s.getsockname()[1], flush=True)\ntime.sleep(60)\n"


def test_stop_falls_back_to_kill_when_helper_does_not_answer(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"; (home / "active").mkdir(parents=True)
    p = subprocess.Popen([sys.executable, "-c", DEAF], stdout=subprocess.PIPE, text=True)   # 포트는 열었지만 HTTP 에 답하지 않는 python
    try:
        port = int(p.stdout.readline())
        m = {"pid": p.pid, "project": "deaf", "out": str(out), "url": "x", "token": "t", "port": port, "agent": None}
        marker(home, p.pid).write_text(json.dumps(m), encoding="utf-8")
        code, o, err = hd(home, "stop")
        assert code == 1 and "떠 있는 캔버스가 없어요" in err, "기본은 살아 있는 것만 — 답 없는 것은 이름으로"
        code, d, err = hdj(home, "stop", "deaf")
        assert code == 0 and d["how"] == "kill", err
        assert p.wait(5) is not None and not marker(home, p.pid).exists()
    finally:
        if p.poll() is None:
            p.kill(); p.wait()
    gone = {"pid": 999999, "project": "ghost", "out": str(out), "url": "x", "token": "t", "port": 1}
    marker(home, 999999).write_text(json.dumps(gone), encoding="utf-8")
    code, text, err = hd(home, "stop", "ghost")
    assert code == 0 and "표지만 지웠어요" in text and not marker(home, 999999).exists(), err


def fake_paseo(tmp_path):
    log = tmp_path / "paseo.log"
    if sys.platform == "win32":
        cmd = tmp_path / "paseo.cmd"
        cmd.write_text('@echo %%* >> "%s"\r\n@exit /b 0\r\n' % log, encoding="ascii")
    else:
        cmd = tmp_path / "paseo"
        cmd.write_text('#!/bin/sh\necho "$@" >> "%s"\n' % log, encoding="ascii"); cmd.chmod(0o755)
    return cmd, log


def test_attach_changes_forward_target_without_restart(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    cmd, log = fake_paseo(tmp_path)
    p, url = hdfix.start_helper(out, home, extra_env={"HD_PASEO_CMD": str(cmd)})
    try:
        assert api(url, "/api/forward", {"text": "a"})[1]["via"] == "queue", "처음엔 에이전트 없음"
        code, d, err = hdj(home, "attach", "--agent", "ag-new", "proj-a")
        assert code == 0 and d["agent"] == "ag-new" and d["was"] is None and d["pid"] == p.pid, err
        assert json.loads(marker(home, p.pid).read_text(encoding="utf-8"))["agent"] == "ag-new", "표지도 고침"
        assert p.poll() is None, "다시 띄우지 않음(같은 pid)"
        code, res = api(url, "/api/forward", {"text": "b"})
        assert res == dict(res, via="paseo", agent="ag-new") and "send ag-new --prompt-file" in log.read_text(encoding="utf-8", errors="replace")
        code, rows, _ = hdj(home, "ls")
        assert rows[0]["agent"] == "ag-new"
        code, o, err = hd(home, "attach", "--agent", "a b")
        assert code == 1 and "띄어쓰기" in err
        assert api(url, "/api/attach", {"agent": "x" * 129})[0] == 400 and api(url, "/api/attach", {})[0] == 400
        code, text, err = hd(home, "attach", "--agent", "none")
        assert code == 0 and "보내기 → 대기열 파일 (전: ag-new)" in text, err
        assert json.loads(marker(home, p.pid).read_text(encoding="utf-8"))["agent"] is None
        assert api(url, "/api/forward", {"text": "c"})[1]["via"] == "queue"
        code, o, err = hd(home, "attach")
        assert code == 1 and "--agent" in err, "PASEO_AGENT_ID 도 없으면 무엇을 줄지 알려 준다"
    finally:
        hdfix.stop_helper(p)


QUIET = [{"id": "q1", "screen": "home", "no": 1, "intent": "change", "sent": False, "note": "아직", "path": "h1", "text": ""}]


def test_wait_returns_when_a_memo_is_sent_and_times_out_with_2(tmp_path):
    out = hdfix.make_out(tmp_path / "w", notes=QUIET)
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    try:
        t0 = time.time()
        code, o, err = hd(home, "wait", "--timeout", "1")
        assert code == 2 and "보낸 메모가 없어요" in err and time.time() - t0 < 15, (code, err)

        def send():
            time.sleep(1.0)
            rev = api(url, "/api/state")[1]["rev"]
            assert api(url, "/api/state", {"rev": rev, "state": {"notes": [dict(QUIET[0], sent=True)]}}, method="PUT")[0] == 200
        th = threading.Thread(target=send); th.start()
        t0 = time.time()
        code, text, err = hd(home, "wait", "proj-a", "--timeout", "20")
        th.join()
        assert code == 0 and time.time() - t0 < 10, err
        assert "proj-a · rev 4 · working · 1개" in text and "home #1 · working · change · h1 · 아직" in text
        code, d, err = hdj(home, "wait")
        assert code == 0 and [(n["id"], n["status"]) for n in d["notes"]] == [("q1", "working")], "이미 있으면 바로"
    finally:
        hdfix.stop_helper(p)


def test_wait_survives_helper_restart(tmp_path):
    out = hdfix.make_out(tmp_path / "w", notes=QUIET)
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    w = subprocess.Popen([sys.executable, str(HD_PY), "wait", "--timeout", "30"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", env=env(home))
    p2 = None
    try:
        time.sleep(2.5)                               # hd wait 이 도우미를 고를 때까지(부하에서 파이썬 시작이 1초를 넘는다 — 47-3)
        hdfix.stop_helper(p)
        p2, url2 = hdfix.start_helper(out, home)
        rev = api(url2, "/api/state")[1]["rev"]
        api(url2, "/api/state", {"rev": rev, "state": {"notes": [dict(QUIET[0], sent=True)]}}, method="PUT")
        so, se = w.communicate(timeout=20)
        assert w.returncode == 0 and "home #1 · working" in so, (so, se)
        assert se.count("[hd]") == 1 and "다시 읽으며" in se, se
    finally:
        if w.poll() is None:
            w.kill(); w.wait()
        if p2:
            hdfix.stop_helper(p2)


def test_helper_projects_and_open_routes(tmp_path):
    a = hdfix.make_out(tmp_path / "a")
    b_root = tmp_path / "b"; b = hdfix.make_out(b_root); b.parent.rename(b_root / "proj-b"); b = b_root / "proj-b" / "out"
    home = tmp_path / "home"
    assert hd(home, "save", "--out", str(b))[0] == 0
    p, url = hdfix.start_helper(a, home, agent="ag-a")
    opened = None
    try:
        code, rows = api(url, "/api/projects")
        cli = hdj(home, "projects")[1]
        assert code == 200 and [{k: v for k, v in r.items() if k != "thumb"} for r in rows] == cli, "hd projects --json 과 같은 줄(+ 허브 썸네일 thumb)"
        assert all("thumb" in r for r in rows)
        assert {(r["name"], r["state"]) for r in rows} == {("proj-a", "running"), ("proj-b", "off")}
        code, res = api(url, "/api/open", {"name": "nope"})
        assert code == 404 and "모르는 프로젝트" in res["error"]
        assert api(url, "/api/open", {})[0] == 400
        code, res = api(url, "/api/open", {"name": "proj-a"})
        assert code == 200 and res["reused"] and res["url"] == url and res["pid"] == p.pid, "자기 자신은 그대로"
        code, res = api(url, "/api/open", {"name": "proj-b"})
        assert code == 200 and not res["reused"] and res["url"].startswith("http://127.0.0.1:"), res
        opened = res["pid"]
        assert res["agent"] == "ag-a", "새로 띄운 도우미는 이 도우미의 agent 로 보낸다"
        assert {(r["name"], r["state"]) for r in api(url, "/api/projects")[1]} == {("proj-a", "running"), ("proj-b", "running")}
    finally:
        if opened:
            code, d, err = hdj(home, "stop", "proj-b")
            assert code == 0 and d["how"] == "route", err
        hdfix.stop_helper(p)
