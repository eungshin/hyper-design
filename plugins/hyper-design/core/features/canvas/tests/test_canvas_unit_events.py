"""47-4a — EventBus(events.py: 번호·고리 버퍼·이어 받기·구독자) · BuildPlan/Rebuilder(rebuild.py: 하나씩·묶기·마지막이 이김·실패면 되돌림). I/O 없음."""
import json, pathlib, sys, threading, time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import events as E  # noqa: E402
import rebuild as RB  # noqa: E402


def bus(ring=4, start=1000, **k):
    t = [5.0]
    return E.EventBus("proj", ring=ring, clock=lambda: t[0], start=start, **k)


# ---------------------------------------------------------------- 번호·모양
def test_ids_go_up_by_one_from_start_and_carry_common_fields():
    b = bus()
    assert b.last == 999, "아무것도 없을 때 newest = start-1"
    a = b.publish("notes.changed", rev=4)
    c = b.publish("claim", screen="home", rev=5, by=None, note=None)
    assert (a["id"], c["id"]) == (1000, 1001) and b.last == 1001
    assert a == {"id": 1000, "type": "notes.changed", "ts": 5000, "project": "proj", "rev": 4}


def test_default_start_is_the_clock_in_ms():
    b = E.EventBus("p", clock=lambda: 1700000000.25)
    assert b.publish("notes.changed", rev=1)["id"] == 1700000000250


def test_unknown_type_is_refused():
    with pytest.raises(ValueError):
        bus().publish("nope")


def test_data_cannot_overwrite_common_fields():
    with pytest.raises(ValueError):
        bus().publish("notes.changed", id=3)


# ---------------------------------------------------------------- 이어 받기(고리 버퍼)
@pytest.mark.parametrize("want, expect", [
    (None, ([], None)),                 # 처음 = 지금부터
    (1005, ([], None)),                 # newest 와 같음
    (1004, ([1005], None)),
    (1001, ([1002, 1003, 1004, 1005], None)),   # 고리 앞보다 하나 앞 = 다 있음
    (1000, ([], "too-old")),            # 1001 이 빠졌다
    (5, ([], "too-old")),
    (1006, ([], "unknown")),            # 앞날 id
    ("abc", ([], "unknown")),
])
def test_resume_plan(want, expect):
    b = bus(ring=4)
    for i in range(6):
        b.publish("notes.changed", rev=i)
    got, reset = b.backlog(want)
    assert ([e["id"] for e in got], reset) == expect


def test_resume_on_an_empty_bus():
    b = bus()
    assert b.backlog(999) == ([], None) and b.backlog(998)[1] == "too-old" and b.backlog(1000)[1] == "unknown"


def test_parse_last_id():
    assert E.parse_last(None) is None and E.parse_last("") is None
    assert E.parse_last(" 12 ") == 12 and E.parse_last("x") == "x" and E.parse_last("-3") == "-3"


# ---------------------------------------------------------------- 구독
def test_subscribe_gives_backlog_then_live_without_gap():
    b = bus(ring=8)
    b.publish("notes.changed", rev=1)
    first = b.last
    b.publish("notes.changed", rev=2)
    sub, back, reset = b.subscribe(first)
    assert reset is None and [e["rev"] for e in back] == [2]
    b.publish("notes.changed", rev=3)
    assert sub.get(0)["rev"] == 3 and sub.get(0) is None, "빈 줄 = None(시간 초과)"


def test_close_wakes_subscribers_and_refuses_new_ones():
    b = bus()
    sub = b.subscribe(None)[0]
    got = []
    t = threading.Thread(target=lambda: got.append(sub.get(5)))
    t.start()
    b.close()
    t.join(2)
    assert got == [E.CLOSED] and b.subscribe(None)[0] is None and b.count() == 0


def test_too_many_subscribers_and_unsubscribe():
    b = bus(max_subs=2)
    s1, s2 = b.subscribe(None)[0], b.subscribe(None)[0]
    assert b.subscribe(None)[0] is None and b.count() == 2
    b.unsubscribe(s1)
    assert b.count() == 1 and b.subscribe(None)[0] is not None
    b.unsubscribe(s2); b.unsubscribe(s2)                      # 두 번 = 괜찮음


def test_lagging_subscriber_is_closed_after_what_it_has():
    b = bus(queue_max=2)
    sub = b.subscribe(None)[0]
    for i in range(3):
        b.publish("notes.changed", rev=i)
    assert [sub.get(0)["rev"], sub.get(0)["rev"]] == [0, 1] and sub.get(0) is E.CLOSED and sub.lagged
    assert b.count() == 0, "뒤처진 구독자는 버스에서 빠진다"


# ---------------------------------------------------------------- SSE 글
def test_frames():
    ev = {"id": 7, "type": "notes.changed", "ts": 1, "project": "가", "rev": 2}
    f = E.frame(ev).decode("utf-8")
    assert f.startswith("id: 7\nevent: notes.changed\ndata: ") and f.endswith("\n\n") and f.count("\n") == 4
    assert json.loads(f.split("data: ", 1)[1]) == ev
    r = E.reset_event(bus(), "too-old")
    assert r["type"] == "reset" and r["id"] == 999 and r["last"] == 999 and r["reason"] == "too-old"
    assert E.HEARTBEAT_FRAME == b": hb\n\n" and E.RETRY_FRAME == b"retry: 2000\n\n"


# ---------------------------------------------------------------- BuildPlan(순수 상태 기계)
def w(n, screens=("home",)):
    return {"stamp": "s%d" % n, "ids": ["e%d" % n], "screens": list(screens)}


def test_plan_first_submit_starts_later_ones_coalesce():
    p = RB.BuildPlan()
    assert p.submit(w(1)) is True and p.submit(w(2)) is False, "돌고 있으면 새 일꾼 없이 묶는다"
    assert [x["stamp"] for x in p.begin()] == ["s1", "s2"]


def test_plan_done_when_nothing_new_arrived():
    p = RB.BuildPlan()
    p.submit(w(1)); batch = p.begin()
    assert p.finish(True) == ("done", batch) and p.begin() is None and p.submit(w(2)) is True, "쉬면 다음 쓰기가 새로 시작"


def test_plan_latest_wins_when_overtaken():
    p = RB.BuildPlan()
    p.submit(w(1)); p.begin(); p.submit(w(2))
    assert p.finish(True) == ("again", None), "새 쓰기가 앞지른 빌드는 알리지 않는다"
    assert [x["stamp"] for x in p.begin()] == ["s1", "s2"]
    assert p.finish(True)[0] == "done"


def test_plan_failure_reverts_everything_unbuilt():
    p = RB.BuildPlan()
    p.submit(w(1)); p.submit(w(2)); p.begin()
    verdict, writes = p.finish(False)
    assert verdict == "revert" and [x["stamp"] for x in writes] == ["s1", "s2"] and p.begin() is None


def test_plan_failure_overtaken_tries_again_with_all():
    p = RB.BuildPlan()
    p.submit(w(1)); p.begin(); p.submit(w(2))
    assert p.finish(False) == ("again", None)
    p.begin()
    assert [x["stamp"] for x in p.finish(False)[1]] == ["s1", "s2"]


def test_plan_summary():
    assert RB.summary([w(1, ["list"]), w(2, ["home", "list"])]) == {"stamps": ["s1", "s2"], "ids": ["e1", "e2"], "screens": ["home", "list"]}


# ---------------------------------------------------------------- Rebuilder(일꾼 — 가짜 빌드·되돌림, 파일 없음)
class Fake:
    def __init__(self, results=None, gate=None):
        self.results, self.gate, self.builds, self.events, self.reverted = list(results or []), gate, 0, [], []
        self.started = threading.Event()

    def build(self):
        self.builds += 1
        self.started.set()
        if self.gate is not None:
            self.gate.wait(5)
        return self.results.pop(0) if self.results else True

    def revert(self, writes):
        self.reverted.append([x["stamp"] for x in writes])
        return [i for x in writes for i in x["ids"]], []

    def emit(self, t, **d):
        self.events.append((t, d))


def wait(pred, t=5):
    end = time.time() + t
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


def test_rebuilder_coalesces_writes_during_a_build():
    gate = threading.Event()
    f = Fake(gate=gate)
    r = RB.Rebuilder(f.build, f.revert, f.emit, coalesce=0)
    r.submit(w(1))
    assert f.started.wait(2)
    r.submit(w(2)); r.submit(w(3))
    gate.set()
    assert wait(lambda: any(t == "build.done" for t, _ in f.events)) and r.join(2)
    assert f.builds == 2, "첫 빌드 + 묶은 빌드 하나"
    assert [t for t, _ in f.events] == ["build.started", "build.started", "build.done"]
    assert f.events[-1][1]["ids"] == ["e1", "e2", "e3"]


def test_rebuilder_failure_reverts_then_repairs_then_reports():
    f = Fake(results=[False, True])
    r = RB.Rebuilder(f.build, f.revert, f.emit, coalesce=0, reason=lambda: "boom")
    r.submit(w(1))
    assert wait(lambda: any(t == "build.failed" for t, _ in f.events)) and r.join(2)
    assert f.reverted == [["s1"]] and f.builds == 2, "되돌린 뒤 한 번 더 빌드(고침)"
    t, d = f.events[-1]
    assert d == {"reason": "boom", "reverted": ["e1"], "kept": [], "stamps": ["s1"], "ids": ["e1"], "screens": ["home"], "repaired": True}


def test_rebuilder_close_stops_before_next_build():
    f = Fake()
    r = RB.Rebuilder(f.build, f.revert, f.emit, coalesce=0.3)
    r.submit(w(1))
    r.close()
    assert r.join(2) and f.builds == 0 and r.pending() == 1
