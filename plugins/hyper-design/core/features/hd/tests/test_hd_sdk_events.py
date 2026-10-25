"""hd_sdk events(task 47-4b) — SSE 글 풀기(sse.py, 순수) · Project.events() 이어 받기·reset · Project.wait 를 이벤트로(없으면 폴링). 가짜 Transport, 서버 없음.
진짜 허브 위 흐름(events.json 의 주소·reset)은 test_hd_sdk_events_hub.py(slow)."""
import json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path.insert(0, str(hdfix.HD))
import hd_sdk as S  # noqa: E402
from hd_sdk import sse  # noqa: E402


def frame(ev, type_=None):
    return ["id: %d" % ev["id"], "event: %s" % (type_ or ev["type"]), "data: " + json.dumps(ev, ensure_ascii=False), ""]


def ev(i, type_, **d):
    return dict({"id": i, "type": type_, "ts": 1, "project": "proj-a"}, **d)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class StreamTransport:
    """request = 대본(GET /api/state 는 states 차례로) · stream(path, last, timeout) = streams 차례로(줄 목록 | 예외). 다 쓰면 clock 을 timeout 만큼 밀고 빈 흐름."""

    def __init__(self, streams, states=None, clock=None):
        self.streams, self.states, self.clock, self.opened = list(streams), list(states or []), clock, []

    def request(self, method, path, body=None, timeout=10):
        if (method, path) == ("GET", "/api/state") and self.states:
            return 200, self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return 404, {"error": "모르는 주소"}

    def stream(self, path, last=None, timeout=30):
        self.opened.append((path, last))
        if not self.streams:
            if self.clock:
                self.clock.t += timeout
            return iter([])
        s = self.streams.pop(0)
        if isinstance(s, Exception):
            raise s
        return iter(s)


def project(t, out="o"):
    m = {"pid": 1, "project": "proj-a", "out": str(out), "url": "u", "token": "t", "port": 1}
    return S.Project(m, transport=t, finder=lambda o: None)


# ---------------------------------------------------------------- sse.py (순수)
def test_parser_reads_frames_comments_retry_and_multiline_data():
    lines = ["retry: 2000", "", ": hb", "", "id: 7", "event: claim", 'data: {"id": 7,', 'data:  "type": "claim"}', "", "data: no-id", "", "id: 8"]
    got = list(sse.frames(lines))
    assert got == [{"id": "7", "event": "claim", "data": '{"id": 7,\n "type": "claim"}'}, {"id": None, "event": "message", "data": "no-id"}], \
        "retry·주석·빈 frame 은 건너뛰고, data 여러 줄은 \\n 으로, 끝나지 않은 frame 은 내지 않는다"
    assert list(sse.frames(["id: 1\r", "data: x\r", "\r"])) == [{"id": "1", "event": "message", "data": "x"}], "CRLF"


def test_event_of_frame_reads_reset_and_skips_broken():
    e = sse.event_of({"id": "9", "event": "reset", "data": json.dumps({"type": "reset", "reason": "too-old", "last": 9})})
    assert e.type == "reset" and e.id == 9 and e.data == {"reason": "too-old", "last": 9}
    e = sse.event_of({"id": "3", "event": "claim", "data": json.dumps(ev(3, "claim", screen="home", rev=4))})
    assert (e.id, e.type, e.project, e.data["screen"]) == (3, "claim", "proj-a", "home")
    assert sse.event_of({"id": "x", "event": "claim", "data": "{깨짐"}) is None


# ---------------------------------------------------------------- Project.events()
def test_events_resume_from_the_last_id_after_the_stream_ends():
    c = Clock()
    t = StreamTransport([frame(ev(1, "notes.changed", rev=4)) + frame(ev(2, "claim", screen="home", rev=5)),
                         frame(ev(3, "release", screen="home", rev=6))], clock=c)
    got = list(project(t).events(timeout=60, clock=c, sleep=c.sleep))
    assert [(e.id, e.type) for e in got] == [(1, "notes.changed"), (2, "claim"), (3, "release")]
    assert t.opened[:3] == [("/api/events", None), ("/api/events", 2), ("/api/events", 3)], "다시 붙을 때 Last-Event-ID = 마지막 id"


def test_events_since_and_reset_moves_the_resume_point():
    c = Clock()
    reset = ["id: 50", "event: reset", "data: " + json.dumps({"type": "reset", "reason": "too-old", "last": 50}), ""]
    t = StreamTransport([reset + frame(ev(51, "notes.changed", rev=9)), []], clock=c)
    got = list(project(t).events(since=1, timeout=60, clock=c, sleep=c.sleep))
    assert [(e.id, e.type) for e in got] == [(50, "reset"), (51, "notes.changed")] and got[0].data["reason"] == "too-old"
    assert t.opened[0] == ("/api/events", 1) and t.opened[1] == ("/api/events", 51)


def test_events_retry_with_backoff_then_give_up_offline():
    c = Clock()
    t = StreamTransport([S.Offline("x")] * 10, clock=c)
    with pytest.raises(S.Offline):
        list(project(t).events(timeout=600, retries=3, clock=c, sleep=c.sleep))
    assert len(t.opened) == 4 and c.t == pytest.approx(0.5 + 1 + 2), "0.5·1·2초 뒤 다시, 네 번째 실패 = Offline"


def test_events_old_server_without_route_is_not_yet():
    c = Clock()
    t = StreamTransport([S.NotFound("없는 주소")], clock=c)
    with pytest.raises(S.NotYet):
        list(project(t).events(timeout=5, clock=c, sleep=c.sleep))


# ---------------------------------------------------------------- wait 를 이벤트로
NONE = {"rev": 3, "state": {"notes": []}}
SENT = {"rev": 4, "state": {"notes": [{"id": "n1", "screen": "home", "no": 1, "note": "버튼", "sent": True, "intent": "change"}], "note-seq": {"home": 1}}}


def test_wait_wakes_on_an_event_not_on_a_timer():
    c = Clock()
    t = StreamTransport([frame(ev(5, "claim", screen="list", rev=3)) + frame(ev(6, "notes.changed", rev=4))], states=[NONE, NONE, NONE, SENT], clock=c)
    st, ns = project(t).wait(30, clock=c, sleep=c.sleep)
    assert st["rev"] == 4 and [n.ref for n in ns] == ["home#1"] and c.t == 0, "이벤트로 깨어남(2초 잠 없음)"


def test_wait_times_out_on_events():
    c = Clock()
    t = StreamTransport([], states=[NONE], clock=c)
    with pytest.raises(S.TimedOut) as ei:
        project(t).wait(5, clock=c, sleep=c.sleep)
    assert ei.value.code == 2 and "5초 동안 보낸 메모가 없어요" in str(ei.value)


def test_wait_falls_back_to_polling_when_events_are_missing():
    c = Clock()
    t = StreamTransport([S.NotFound("없는 주소")], states=[NONE, NONE, SENT], clock=c)
    st, ns = project(t).wait(30, poll=2, clock=c, sleep=c.sleep)
    assert st["rev"] == 4 and c.t == 2, "흐름이 없으면 2초 폴링"
