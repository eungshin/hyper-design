"""47-5a — AgentPresence(presence.py: hello 검사·임대 자르기·맥박·임대 끝 = away·잊기·progress 검사) · AgentAdapter(adapters.py: 받는 곳 고르기 ·
Paseo/Claude/None 어댑터 · 새 에이전트 열기 꺼짐). 시계·하위 프로세스는 가짜 — 실제 paseo·claude 를 띄우지 않는다."""
import pathlib, subprocess, sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import adapters as AD  # noqa: E402
import presence as PR  # noqa: E402


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def pres(t=1000.0):
    seen, clock = [], Clock(t)
    p = PR.AgentPresence(publish=lambda type_, **d: seen.append(dict(d, type=type_)) or {"id": len(seen)}, clock=clock)
    return p, seen, clock


# ---------------------------------------------------------------- 순수 규칙
def test_check_hello_defaults_and_refusals():
    who, lease, err = PR.check_hello({"agent": {"id": "ag-1"}})
    assert err is None and lease == PR.LEASE
    assert who == {"id": "ag-1", "name": "ag-1", "kind": "other", "pid": None, "listen": True, "session": None, "cwd": None}
    who, lease, _ = PR.check_hello({"agent": {"id": "c", "name": " 클로드 ", "kind": "claude", "pid": 7, "listen": False, "session": "s-1"}, "lease": 999})
    assert who["name"] == "클로드" and who["kind"] == "claude" and who["pid"] == 7 and who["listen"] is False and who["session"] == "s-1" and lease == PR.LEASE_MAX
    bad = [{}, {"agent": "x"}, {"agent": {}}, {"agent": {"id": "a b"}}, {"agent": {"id": ""}}, {"agent": {"id": "a", "kind": "robot"}},
           {"agent": {"id": "a", "pid": "1"}}, {"agent": {"id": "a", "pid": True}}, {"agent": {"id": "a", "pid": 0}}, {"agent": {"id": "a", "listen": "y"}},
           {"agent": {"id": "a", "name": "x" * (PR.NAME_MAX + 1)}}, {"agent": {"id": "a", "session": 3}}, {"agent": {"id": "a"}, "lease": "10"}, [],
           {"agent": {"id": "a", "cwd": 3}}, {"agent": {"id": "a", "cwd": " "}}, {"agent": {"id": "a", "cwd": "C:/x\ny"}},
           {"agent": {"id": "a", "cwd": "x" * (PR.CWD_MAX + 1)}}]
    for b in bad:
        assert PR.check_hello(b)[2], b


def test_check_hello_keeps_cwd_but_public_hides_it():
    who, _, err = PR.check_hello({"agent": {"id": "c", "kind": "claude", "session": "s-1", "cwd": "C:\\Code\\proj"}})
    assert err is None and who["cwd"] == "C:\\Code\\proj"
    p, _, _ = pres()
    code, res = p.hello({"agent": {"id": "c", "kind": "claude", "session": "s-1", "cwd": "C:\\Code\\proj"}})
    assert code == 200 and "cwd" not in res["agent"] and p.get("c")["cwd"] == "C:\\Code\\proj", "작업 폴더는 서버 안에서만(어댑터·소스)"


def test_lease_is_clamped_and_beat_is_a_third():
    assert [PR.lease_of(v) for v in (None, 0, 1, 2.6, 30, 10 ** 6)] == [PR.LEASE, PR.LEASE_MIN, 1, 3, 30, PR.LEASE_MAX]
    assert PR.beat_of(30) == 10 and PR.beat_of(1) == pytest.approx(1 / 3)


def test_check_progress():
    assert PR.check_progress({"text": " 고치는 중 ", "screen": "home", "agent": "a"}) == (("a", "고치는 중", "home"), None)
    assert PR.check_progress({"text": "x"}) == ((None, "x", None), None)
    for b in ({}, {"text": " "}, {"text": "x" * (PR.TEXT_MAX + 1)}, {"text": "x", "screen": 3}, {"text": "x", "agent": "a b"}, {"text": 5}, []):
        assert PR.check_progress(b)[1], b


def test_sweep_plan_marks_away_after_the_lease_and_forgets_after_an_hour():
    a = {"x": {"state": "here", "seen": 0, "lease": 30}, "y": {"state": "here", "seen": 0, "lease": 300},
         "z": {"state": "away", "seen": 0, "lease": 30}}
    assert PR.sweep_plan(a, 30_000) == ([], [])
    assert PR.sweep_plan(a, 30_001) == (["x"], [])
    assert PR.sweep_plan(a, PR.AWAY_KEEP * 1000 + 1) == (["x", "y"], ["z"])


# ---------------------------------------------------------------- AgentPresence(상태 주인 · 가짜 시계)
def test_hello_registers_once_and_refreshes_without_an_event():
    p, seen, clock = pres()
    code, res = p.hello({"agent": {"id": "ag-1", "kind": "claude"}})
    assert code == 200 and res["first"] is True and res["lease"] == 30 and res["beat"] == 10
    assert res["agent"]["state"] == "here" and res["agent"]["since"] == res["agent"]["seen"] == 1_000_000 and "session" not in res["agent"]
    clock.t += 5
    code, res = p.hello({"agent": {"id": "ag-1", "kind": "claude", "name": "새 이름"}})
    assert res["first"] is False and res["agent"]["seen"] == 1_005_000 and res["agent"]["since"] == 1_000_000 and res["agent"]["name"] == "새 이름"
    assert [e["type"] for e in seen] == ["agent.hello"] and seen[0]["agent"]["id"] == "ag-1"


def test_missed_lease_marks_away_then_a_beat_brings_it_back():
    p, seen, clock = pres()
    p.hello({"agent": {"id": "a"}, "lease": 2})
    clock.t += 2
    assert p.sweep() == [] and p.get("a")["state"] == "here", "임대 끝 그 순간까지는 here"
    clock.t += 0.01
    assert p.sweep() == ["a"] and p.get("a")["state"] == "away"
    assert seen[-1] == {"type": "agent.away", "agent": "a", "name": "a", "reason": "lease"}
    assert p.sweep() == [], "away 는 한 번만 알린다"
    code, res = p.beat({"id": "a"})
    assert code == 200 and res["first"] is True and p.get("a")["state"] == "here" and seen[-1]["type"] == "agent.hello"


def test_beat_and_bye_refusals_and_bye_is_away_at_once():
    p, seen, clock = pres()
    assert p.beat({"id": "nobody"}) == (404, {"error": PR.UNKNOWN % "nobody", "reason": "unknown"})
    assert p.beat({})[0] == 400 and p.bye([])[0] == 400
    p.hello({"agent": {"id": "a"}})
    code, res = p.bye({"id": "a"})
    assert code == 200 and res["agent"]["state"] == "away" and seen[-1]["reason"] == "bye"
    assert p.bye({"id": "a"})[0] == 200 and len(seen) == 2, "이미 away 면 알리지 않는다"
    assert p.bye({"id": "zz"})[0] == 404


def test_away_agents_are_forgotten_after_an_hour_and_the_list_is_public():
    p, seen, clock = pres()
    p.hello({"agent": {"id": "a", "session": "secret"}})
    p.hello({"agent": {"id": "b"}, "lease": 300})
    clock.t += 31
    p.sweep()
    lst = p.list()
    assert lst["lease"] == PR.LEASE and [(x["id"], x["state"]) for x in lst["agents"]] == [("a", "away"), ("b", "here")]
    assert all("session" not in x for x in lst["agents"]), "claude 이어 받기 id 는 밖으로 내지 않는다"
    clock.t += PR.AWAY_KEEP
    p.sweep()
    assert p.get("a") is None


def test_too_many_agents_forgets_the_oldest_away_first_then_refuses(monkeypatch):
    monkeypatch.setattr(PR, "MAX_AGENTS", 2)
    p, seen, clock = pres()
    p.hello({"agent": {"id": "a"}}); p.bye({"id": "a"})
    p.hello({"agent": {"id": "b"}})
    assert p.hello({"agent": {"id": "c"}})[0] == 200 and p.get("a") is None
    code, res = p.hello({"agent": {"id": "d"}})
    assert code == 400 and "에이전트" in res["error"]


def test_progress_publishes_and_counts_as_a_beat():
    p, seen, clock = pres()
    p.hello({"agent": {"id": "a"}})
    clock.t += 3
    code, res = p.progress({"agent": "a", "text": "홈 보는 중", "screen": "home"})
    assert code == 200 and res == {"event": 2}
    assert seen[-1] == {"type": "agent.progress", "agent": "a", "text": "홈 보는 중", "screen": "home"}
    assert p.get("a")["seen"] == 1_003_000 and p.get("a")["progress"] == {"text": "홈 보는 중", "screen": "home", "at": 1_003_000}
    assert p.progress({"text": "누구인지 모름"})[0] == 200 and seen[-1]["agent"] is None
    assert p.progress({"text": "x", "agent": "nobody"})[0] == 404


# ---------------------------------------------------------------- 받는 곳 고르기(순수)
@pytest.mark.parametrize("target, entry, ready, want", [
    (None, None, {"paseo": True, "claude": True}, "queue"),                                   # 받는 곳 없음 = 대기열(오늘)
    ("p1", None, {"paseo": True, "claude": False}, "paseo"),                                  # 모르는 id = Paseo id(오늘)
    ("p1", None, {"paseo": False, "claude": False}, "queue"),                                 # Paseo 가 없음
    ("a", {"state": "here", "listen": True, "kind": "claude"}, {"paseo": True, "claude": True}, "event"),
    ("a", {"state": "here", "listen": False, "kind": "paseo"}, {"paseo": True, "claude": True}, "paseo"),
    ("a", {"state": "away", "listen": True, "kind": "paseo"}, {"paseo": True, "claude": True}, "paseo"),
    ("a", {"state": "away", "listen": True, "kind": "claude", "session": "s"}, {"paseo": True, "claude": True}, "claude"),
    ("a", {"state": "away", "listen": True, "kind": "claude", "session": "s"}, {"paseo": True, "claude": False}, "queue"),   # 깨우기 꺼짐(기본)
    ("a", {"state": "away", "listen": True, "kind": "claude", "session": None}, {"paseo": True, "claude": True}, "queue"),
    ("a", {"state": "here", "listen": False, "kind": "codex"}, {"paseo": True, "claude": True}, "queue"),
    ("a", {"state": "here", "listen": False, "kind": "other"}, {"paseo": True, "claude": True}, "queue"),
])
def test_choose(target, entry, ready, want):
    assert AD.choose(target, entry, ready) == want


def test_config_from_env_is_off_by_default():
    assert AD.config_from_env({}) == {"claude_wake": False, "allow_spawn": False, "claude_cmd": None}
    assert AD.config_from_env({"HD_CLAUDE_WAKE": "1", "HD_ALLOW_SPAWN": "1", "HD_CLAUDE_CMD": "c.exe"}) == {"claude_wake": True, "allow_spawn": True, "claude_cmd": "c.exe"}
    assert AD.config_from_env({"HD_CLAUDE_WAKE": "yes", "HD_ALLOW_SPAWN": "0"})["claude_wake"] is False, "정확히 '1' 만 켠다"


# ---------------------------------------------------------------- 어댑터(가짜 하위 프로세스)
class Runner:
    def __init__(self, code=0, out=b"", exc=None):
        self.code, self.out, self.exc, self.calls = code, out, exc, []

    def __call__(self, args, **kw):
        self.calls.append((args, kw))
        if self.exc:
            raise self.exc
        return subprocess.CompletedProcess(args, self.code, self.out, b"")


def test_none_adapter_only_keeps_the_queue_file(tmp_path):
    a = AD.NoneAdapter()
    assert a.name == "queue" and a.ready() and a.send(tmp_path / "q.txt", "글", None) == (True, None)


def test_paseo_adapter_is_todays_paseo_send(tmp_path):
    r = Runner()
    a = AD.PaseoAdapter(lambda: "C:/x/paseo.cmd", run=r)
    p = tmp_path / "q.txt"
    assert a.ready() and a.send(p, "글", "ag-1") == (True, None)
    args, kw = r.calls[0]
    assert args == ["cmd", "/c", "C:/x/paseo.cmd", "send", "ag-1", "--prompt-file", str(p), "--no-wait"]
    assert kw["creationflags"] == AD.NO_WINDOW and kw["timeout"] == 60
    assert AD.PaseoAdapter(lambda: "paseo", run=Runner(code=1)).send(p, "글", "a")[0] is False
    assert AD.PaseoAdapter(lambda: "paseo", run=Runner(exc=OSError("x"))).send(p, "글", "a")[0] is False
    assert AD.PaseoAdapter(lambda: "paseo", run=Runner(exc=subprocess.TimeoutExpired("p", 60))).send(p, "글", "a")[0] is False
    assert not AD.PaseoAdapter(lambda: None).ready()


class Popen:
    def __init__(self):
        self.calls = []

    def __call__(self, args, **kw):
        self.calls.append((args, kw))
        return object()


def test_claude_adapter_is_off_by_default_and_spawns_without_a_window(tmp_path):
    p = tmp_path / ".hd-queue" / "20261025-100000-000000.txt"
    p.parent.mkdir(); p.write_text("고쳐 주세요", encoding="utf-8")
    off = AD.ClaudeCliAdapter(lambda: "claude.exe", enabled=False, popen=Popen())
    assert not off.ready() and off.send(p, "x", {"session": "s"})[0] is False and not off.popen.calls
    po = Popen()
    on = AD.ClaudeCliAdapter(lambda: "claude.exe", enabled=True, popen=po, cwd=str(tmp_path))
    assert on.ready() and on.send(p, "고쳐 주세요", {"id": "a", "session": "sess-1"}) == (True, None)
    args, kw = po.calls[0]
    assert args == ["claude.exe", "-p", "--resume", "sess-1"] and kw["creationflags"] == AD.NO_WINDOW and kw["cwd"] == str(tmp_path)
    assert kw["stdin"].name == str(p) and p.with_suffix(".claude.log").is_file(), "요청문 = 표준 입력, 출력 = 대기열 옆 로그"
    assert on.send(p, "x", {"id": "a", "session": None})[0] is False, "이어 받을 세션이 없으면 못 깨운다"
    assert not AD.ClaudeCliAdapter(lambda: None, enabled=True, popen=Popen()).ready()


def test_spawn_is_disabled_unless_opted_in_and_checks_kind_first():
    r = Runner(out=b'{"id": "new-1"}')
    off = AD.PaseoSpawner(lambda: "paseo", enabled=False, run=r)
    assert off.spawn({"kind": "robot"}, "C:/w", "proj")[0] == 400
    code, res = off.spawn({"kind": "claude"}, "C:/w", "proj")
    assert code == 403 and res["reason"] == "disabled" and not r.calls
    on = AD.PaseoSpawner(lambda: "paseo", enabled=True, run=r)
    code, res = on.spawn({"kind": "codex"}, "C:/w", "proj")
    assert code == 200 and res == {"spawned": True, "via": "paseo", "agent": "new-1"}
    args, kw = r.calls[0]
    assert args[:2] == ["paseo", "run"] and "--no-wait" in args and args[args.index("--provider") + 1] == "codex"
    assert args[args.index("--cwd") + 1] == "C:/w" and kw["creationflags"] == AD.NO_WINDOW
    assert AD.PaseoSpawner(lambda: None, enabled=True, run=r).spawn({"kind": "claude"}, "C:/w", "p")[0] == 503
    assert AD.PaseoSpawner(lambda: "paseo", enabled=True, run=Runner(code=2)).spawn({"kind": "claude"}, "C:/w", "p")[0] == 502
