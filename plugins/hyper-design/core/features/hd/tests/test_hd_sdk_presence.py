"""hd_sdk 접속(47-5a) — Project.hello · 맥박(Heartbeat.tick, 스레드 없이) · progress · agents · requests · bye · Hub.hello(프로젝트) · hd attach/progress.
가짜 Transport 만(서버·자식 프로세스 없음). 순수 규칙 whoami 는 환경 사전을 받는다."""
import sys, time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402
from test_hd_sdk_unit import FakeTransport, project  # noqa: E402

sys.path.insert(0, str(hdfix.HD))
import hd  # noqa: E402
import hd_sdk as S  # noqa: E402
from hd_sdk import presence as SP  # noqa: E402


@pytest.fixture()
def out(tmp_path):
    return hdfix.make_out(tmp_path / "w")


def answer(first=True, lease=30, aid="ag-1"):
    return {"agent": {"id": aid, "state": "here"}, "lease": lease, "beat": lease / 3, "first": first}


# ---------------------------------------------------------------- 순수: 나는 누구
def test_whoami_from_env():
    assert SP.whoami({"PASEO_AGENT_ID": "p-1"}, 7) == {"id": "p-1", "name": "p-1", "kind": "paseo", "pid": 7}
    assert SP.whoami({"CLAUDECODE": "1"}, 7) == {"id": "claude-7", "name": "Claude Code", "kind": "claude", "pid": 7}
    assert SP.whoami({}, 7) == {"id": "agent-7", "name": "agent-7", "kind": "other", "pid": 7}
    assert SP.whoami({"PASEO_AGENT_ID": "p-1", "CLAUDECODE": "1"}, 7)["kind"] == "paseo", "Paseo 안의 Claude = Paseo 로 깨운다"


SID = "0f8e2a64-1111-4c2d-9a7b-00000000000a"


def test_whoami_claude_reports_session_id_and_cwd():
    who = SP.whoami({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": SID}, 7, "C:\\Code\\proj")
    assert who == {"id": "claude-7", "name": "Claude Code", "kind": "claude", "pid": 7, "session": SID, "cwd": "C:\\Code\\proj"}
    for bad in ("../" + SID, "a b", "x" * 129, "", "C:\\x"):
        assert "session" not in SP.whoami({"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": bad}, 7), bad
    assert "session" not in SP.whoami({"CLAUDE_CODE_SESSION_ID": SID}, 7), "Claude 가 아니면 세션 id 를 내지 않는다"
    assert "session" not in SP.whoami({"PASEO_AGENT_ID": "p-1", "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": SID}, 7)


def test_hello_as_claude_sends_env_session_and_cwd(out, monkeypatch, tmp_path):
    monkeypatch.delenv("PASEO_AGENT_ID", raising=False)
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", SID)
    monkeypatch.chdir(tmp_path)
    p, t = project(out, {("POST", "/hello"): (200, answer())})
    p.hello(beat=False)
    agent = t.calls[-1][2]["agent"]
    assert agent["kind"] == "claude" and agent["session"] == SID and agent["cwd"] == str(tmp_path)
    p.hello("ag-1", kind="claude", session="s-given", beat=False)
    assert t.calls[-1][2]["agent"]["session"] == "s-given" and t.calls[-1][2]["agent"]["cwd"] == str(tmp_path), "준 session 이 먼저"
    p.hello("ag-2", kind="other", beat=False)
    assert "session" not in t.calls[-1][2]["agent"] and "cwd" not in t.calls[-1][2]["agent"], "claude 가 아니면 보내지 않는다"


def test_presence_module_is_pure():
    import ast
    tree = ast.parse((hdfix.HD / "hd_sdk" / "presence.py").read_text(encoding="utf-8"))
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} | \
           {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= {"threading", "errors"}, mods


# ---------------------------------------------------------------- Project
def test_hello_posts_who_and_remembers_me(out):
    p, t = project(out, {("POST", "/hello"): (200, answer())})
    res = p.hello("ag-1", name="나", kind="claude", pid=5, session="s-1", beat=False, cwd="C:\\w")
    assert res["first"] is True and p.me == "ag-1" and p.heartbeat is None
    assert t.calls[-1] == ("POST", "/hello", {"agent": {"id": "ag-1", "name": "나", "kind": "claude", "pid": 5, "listen": True, "session": "s-1", "cwd": "C:\\w"}})
    p.hello("ag-1", listen=False, lease=60, beat=False)
    assert t.calls[-1][2] == {"agent": {"id": "ag-1", "name": "ag-1", "kind": "other", "listen": False}, "lease": 60}


def test_hello_defaults_from_env(out, monkeypatch):
    monkeypatch.setenv("PASEO_AGENT_ID", "p-9")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    p, t = project(out, {("POST", "/hello"): (200, answer(aid="p-9"))})
    p.hello(beat=False)
    assert t.calls[-1][2]["agent"]["id"] == "p-9" and t.calls[-1][2]["agent"]["kind"] == "paseo" and p.me == "p-9"


def test_hello_on_an_old_server_is_not_yet_and_checks_first(out):
    p, t = project(out, {})
    with pytest.raises(S.NotYet):
        p.hello("ag-1", beat=False)
    with pytest.raises(S.Invalid):
        p.hello("a b", beat=False)
    with pytest.raises(S.Invalid):
        p.hello("ag", kind="robot", beat=False)
    assert [c for c in t.calls if c[1] == "/hello"] == [("POST", "/hello", {"agent": {"id": "ag-1", "name": "ag-1", "kind": "other", "listen": True}})]


def test_heartbeat_tick_beats_and_hellos_again_when_forgotten(out):
    calls = {"n": 0}

    def beat(b):
        calls["n"] += 1
        return (404, {"error": "모름", "reason": "unknown"}) if calls["n"] == 2 else (200, answer(first=False))
    p, t = project(out, {("POST", "/hello"): (200, answer()), ("POST", "/beat"): beat})
    p.hello("ag-1", beat=False)
    hb = SP.Heartbeat(p, every=10)
    assert hb.tick() is True and t.calls[-1] == ("POST", "/beat", {"id": "ag-1"})
    assert hb.tick() is True and [c[1] for c in t.calls[-2:]] == ["/beat", "/hello"], "서버가 잊었으면(다시 뜸) hello 를 다시"
    t.script[("POST", "/beat")] = S.Offline("닿지 않음")
    assert hb.tick() is False and hb.fails == 1, "닿지 않으면 다음 차례에 다시(멈추지 않음)"


def test_hello_starts_a_daemon_heartbeat_and_bye_stops_it(out):
    p, t = project(out, {("POST", "/hello"): (200, answer(lease=3)), ("POST", "/beat"): (200, answer(first=False)),
                         ("POST", "/bye"): (200, {"agent": {"id": "ag-1", "state": "away"}})})
    p.hello("ag-1")
    hb = p.heartbeat
    assert hb is not None and hb.every == 1.0 and hb.thread.daemon and hb.thread.is_alive()
    assert p.bye()["agent"]["state"] == "away" and p.heartbeat is None
    hb.thread.join(2)
    assert not hb.thread.is_alive(), "bye 가 맥박 스레드를 멈춘다"
    assert t.calls[-1] == ("POST", "/bye", {"id": "ag-1"})


def test_progress_agents_and_requests(out):
    lines = [b"retry: 2000\n", b"\n",
             b'id: 5\nevent: request.sent\ndata: {"id":5,"type":"request.sent","ts":1,"project":"p","to":"ag-1","via":"event","notes":["n1"],"text":"t","path":"q"}\n\n',
             b'id: 6\nevent: request.sent\ndata: {"id":6,"type":"request.sent","ts":1,"project":"p","to":"other","via":"event","notes":[],"text":"x","path":"q"}\n\n',
             b'id: 7\nevent: request.sent\ndata: {"id":7,"type":"request.sent","ts":1,"project":"p","to":"ag-1","via":"paseo","notes":[],"text":"y","path":"q"}\n\n',
             b'id: 8\nevent: notes.changed\ndata: {"id":8,"type":"notes.changed","ts":1,"project":"p","rev":4}\n\n']
    lines = b"".join(lines).splitlines(keepends=True)                 # 흐름은 줄 하나씩

    class T(FakeTransport):
        def stream(self, path, last=None, timeout=30):     # 처음만 줄들, 다시 붙으면(last 다음) 새것 없음
            self.calls.append(("STREAM", path, last))
            if last is not None:
                time.sleep(0.05)
                return iter([])
            return iter(lines)
    t = T({("POST", "/hello"): (200, answer()), ("POST", "/progress"): (200, {"event": 9}),
           ("GET", "/agents"): (200, {"agents": [{"id": "ag-1", "state": "here"}], "lease": 30})})
    m = {"pid": 1, "project": "proj-a", "out": str(out), "url": "http://x/", "token": "t", "port": 1, "agent": None}
    p = S.Project(m, transport=t)
    with pytest.raises(S.Invalid):
        p.progress("  ")
    assert p.progress("보는 중") == 9 and t.calls[-1] == ("POST", "/progress", {"text": "보는 중"})
    p.hello("ag-1", beat=False)
    p.progress("홈 고치는 중", screen="home")
    assert t.calls[-1] == ("POST", "/progress", {"text": "홈 고치는 중", "agent": "ag-1", "screen": "home"})
    assert p.agents() == [{"id": "ag-1", "state": "here"}]
    got = list(p.requests(timeout=0.5, retries=0))
    assert [e.id for e in got] == [5] and got[0].data["notes"] == ["n1"] and got[0].data["text"] == "t", "나에게 온 이벤트 요청만"


def test_requests_needs_hello(out):
    p, _ = project(out, {})
    with pytest.raises(S.HdError, match="hello"):
        next(iter(p.requests(timeout=0.1)))


# ---------------------------------------------------------------- Hub.hello(프로젝트)
def test_hub_hello_with_a_project_registers_there(out, monkeypatch):
    t = FakeTransport({("POST", "/hello"): (200, answer())})
    p = S.Project({"pid": 1, "project": "proj-a", "out": str(out), "url": "u", "token": "t", "port": 1, "agent": None}, transport=t)
    hub = S.Hub(record={"url": "http://h/", "port": 5, "pid": 2, "token": "k"},
                transport=FakeTransport({("GET", "/v1/sessions"): (200, {"sessions": []})}))
    monkeypatch.setattr(hub, "pick", lambda ref=None, stale_ok=False: p)
    got = hub.hello("proj-a", id="ag-1", beat=False)
    assert got is p and p.me == "ag-1" and t.calls[-1][1] == "/hello"
    assert hub.hello() == {"url": "http://h/", "port": 5, "pid": 2, "sessions": 0}, "인자 없으면 예전 그대로(닿는지·토큰)"


# ---------------------------------------------------------------- CLI: hd attach 가 hello 를 · hd progress
class FakeHub:
    def __init__(self, p):
        self.p = p

    def pick(self, ref=None, stale_ok=False):
        return self.p


def test_cli_attach_also_says_hello_without_listening_and_ignores_old_servers(out, monkeypatch, capsys):
    t = FakeTransport({("POST", "/api/attach"): lambda b: (200, {"agent": b["agent"]}), ("POST", "/hello"): (200, answer(aid="p-1"))})
    p = S.Project({"pid": 1, "project": "proj-a", "out": str(out), "url": "u", "token": "t", "port": 1, "agent": None}, transport=t)
    monkeypatch.setattr(hd, "_hub", lambda: FakeHub(p))
    assert hd.main(["attach", "--agent", "p-1"]) == 0
    assert ("POST", "/hello", {"agent": {"id": "p-1", "name": "p-1", "kind": "paseo", "listen": False}}) in t.calls
    assert "보내기 → p-1" in capsys.readouterr().out
    del t.script[("POST", "/hello")]
    assert hd.main(["attach", "--agent", "p-1"]) == 0, "접속 알리기를 모르는 옛 서버여도 attach 는 된다"
    t.calls.clear()
    assert hd.main(["attach", "--agent", "none"]) == 0 and not [c for c in t.calls if c[1] == "/hello"], "떼기는 hello 를 하지 않는다"


def test_cli_progress(out, monkeypatch, capsys):
    t = FakeTransport({("POST", "/progress"): (200, {"event": 3})})
    p = S.Project({"pid": 1, "project": "proj-a", "out": str(out), "url": "u", "token": "t", "port": 1, "agent": None}, transport=t)
    monkeypatch.setattr(hd, "_hub", lambda: FakeHub(p))
    monkeypatch.setenv("PASEO_AGENT_ID", "p-1")
    assert hd.main(["progress", "홈 고치는 중", "--screen", "home"]) == 0
    assert t.calls[-1] == ("POST", "/progress", {"text": "홈 고치는 중", "agent": "p-1", "screen": "home"})
    assert "홈 고치는 중" in capsys.readouterr().out
    assert hd.main(["progress", " "]) == 1
