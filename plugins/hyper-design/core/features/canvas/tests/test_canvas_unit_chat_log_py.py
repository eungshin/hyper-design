"""대화 기록(S3) 서버 규칙 — chat_log.py(순수): 이벤트 → 기록 모양 · 턴 붙이기 · 열린 턴 · 한도/보관 · 깨진 줄 · since. I/O 없음.
ChatLog(chat_store.py, 파일)는 아래 slow 하나 — 버스 탭으로 남고, 다시 열어도 이어지고, 한도를 넘으면 보관 파일로 옮긴다."""
import json, shutil, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import chat_log as CL  # noqa: E402

T0 = 1_700_000_000_000


def ev(t, **k):
    return dict({"id": 1, "type": t, "ts": T0, "project": "p"}, **k)


def feed(items):
    idx, out = CL.empty(), []
    for kind, fields, at in items:
        rec, idx = CL.assign(idx, kind, fields, at)
        out.append(rec)
    return out, idx


def test_from_event_shapes():
    assert CL.from_event(ev("request.sent", to="a1", via="event", notes=["n1", 3], text=" 요청문 ", path="x")) == \
        ("sent", {"notes": ["n1"], "to": "a1", "via": "event", "text": "요청문"})
    assert CL.from_event(ev("agent.progress", agent=None, text="  파일 읽는 중 ", screen="pay")) == \
        ("progress", {"agent": None, "text": "파일 읽는 중", "screen": "pay"})
    assert CL.from_event(ev("agent.progress", agent="a", text="  ", screen=None)) is None, "빈 진행 글은 버린다"
    r = CL.from_event(ev("agent.reply", note="n1", kind="반영됨", screen="pay", agent="a", status="done", text="버튼을 키웠어요"))
    assert r[0] == "reply" and r[1]["text"] == "버튼을 키웠어요" and r[1]["status"] == "done" and r[1]["rkind"] == "반영됨" and "kind" not in r[1]
    assert CL.from_event(ev("ai.write", seq=1, stamp="S1", screen="pay", label="AI 반영 · 결제", act="record"))[1]["stamp"] == "S1"
    assert CL.from_event(ev("ai.write", seq=1, stamp="S1", screen="pay", label="x", act="update")) is None, "update 는 새 줄이 아니다"
    assert CL.from_event(ev("build.failed", reason="깨짐", reverted=[], kept=[], ids=[], stamps=[], screens=["pay"], repaired=True)) == \
        ("failed", {"reason": "깨짐", "screens": ["pay"]})
    assert CL.from_event(ev("notes.changed", rev=3)) is None and CL.from_event(None) is None


def test_reply_text_picks_the_visible_field():
    assert CL.reply_text({"kind": "답변", "text": "네"}) == "네"
    assert CL.reply_text({"kind": "반영됨", "what": "키움"}) == "키움"
    assert CL.reply_text({"kind": "일부", "done": "하나만"}) == "하나만"
    assert CL.reply_text({"kind": "질문", "question": "어느 쪽?"}) == "어느 쪽?"
    assert CL.reply_text({"kind": "x"}) is None and CL.reply_text("x") is None


def test_turns_join_by_note_and_last_turn():
    recs, idx = feed([
        ("ask", {"text": "버튼 키워", "notes": ["n1"], "chips": ["결제"]}, T0),
        ("sent", {"notes": ["n1", "n0"], "to": "a", "via": "event"}, T0 + 10),       # 같은 메모 → 같은 턴
        ("progress", {"text": "읽는 중"}, T0 + 20),                                   # 마지막 턴
        ("reply", {"note": "n1", "rkind": "반영됨", "status": "done"}, T0 + 30),
        ("sent", {"notes": ["n9"], "to": None, "via": "queue"}, T0 + 40),            # 새 메모 → 새 턴
        ("reply", {"note": "n1", "rkind": "답변", "status": "done"}, T0 + 50),        # 옛 메모 답 → 그 턴
        ("reply", {"note": "zz", "rkind": "답변", "status": "done"}, T0 + 60),        # 모르는 메모 → 마지막 턴
    ])
    assert [r["turn"] for r in recs] == [1, 1, 1, 1, 5, 1, 5]
    assert [r["seq"] for r in recs] == [1, 2, 3, 4, 5, 6, 7] and idx["seq"] == 7
    assert "to" not in recs[4], "None 칸은 기록에 쓰지 않는다"


def test_ask_after_sent_joins_the_same_turn():
    recs, _ = feed([("sent", {"notes": ["n1"], "via": "event"}, T0), ("ask", {"text": "x", "notes": ["n1"]}, T0 + 5)])
    assert recs[1]["turn"] == recs[0]["turn"] == 1


def test_build_lines_only_join_an_open_turn():
    recs, _ = feed([
        ("built", {"screens": []}, T0),                                               # 턴 없음 → 버림
        ("failed", {"reason": "깨짐"}, T0 + 1),                                       # 턴 없음 → 새 턴(빨간 줄은 늘)
        ("ask", {"text": "a", "notes": ["n1"]}, T0 + 2),
        ("built", {"screens": ["pay"]}, T0 + 3),                                      # 열림 → 붙음
        ("built", {"screens": ["pay"]}, T0 + 3 + CL.OPEN_MS + 5),                     # 10분 지남 → 버림
        ("failed", {"reason": "또"}, T0 + 3 + CL.OPEN_MS + 6),                        # 닫힘 → 새 턴
    ])
    assert recs[0] is None and recs[4] is None
    assert recs[1]["turn"] == recs[1]["seq"] == 1, "버린 줄은 seq 를 쓰지 않는다"
    assert recs[3]["turn"] == recs[2]["turn"] == 2
    assert recs[5]["turn"] == recs[5]["seq"] == 4


def test_built_does_not_keep_a_turn_open():
    _, idx = feed([("ask", {"text": "a", "notes": ["n1"]}, T0), ("built", {}, T0 + CL.OPEN_MS)])
    assert not CL.is_open(idx, T0 + CL.OPEN_MS + 1), "빌드 줄은 열린 시간을 늘리지 않는다(사람 편집이 끝없이 붙지 않게)"


def test_undone_needs_a_known_turn():
    recs, _ = feed([("ask", {"text": "a", "notes": ["n1"]}, T0), ("undone", {"turn_of": 1}, T0 + 1), ("undone", {"turn_of": 99}, T0 + 2)])
    assert recs[1]["turn"] == 1 and "turn_of" not in recs[1] and recs[2] is None


def test_check_post():
    assert CL.check_post({"kind": "ask", "text": " 버튼 ", "notes": ["n1"], "chips": ["결제", " "], "screens": ["pay", 1], "agent": "Claude"}) == \
        (("ask", {"text": "버튼", "notes": ["n1"], "chips": ["결제"], "screens": ["pay"], "agent": "Claude"}), None)
    for bad in ({"kind": "ask", "text": ""}, {"kind": "ask", "text": "a", "notes": "n1"}, {"kind": "ask", "text": "a", "chips": [1]},
                {"kind": "undone", "turn": 0}, {"kind": "undone", "turn": True}, {"kind": "zz"}, []):
        got, err = CL.check_post(bad)
        assert got is None and err, bad
    assert CL.check_post({"kind": "undone", "turn": 4}) == (("undone", {"turn_of": 4}), None)


def test_trim_keeps_newest_turns_in_order():
    recs = [{"seq": i, "at": 0, "turn": t, "kind": "progress"} for i, t in enumerate([1, 1, 2, 3, 2, 4], 1)]
    keep, old = CL.trim(recs, cap=2)
    assert [r["seq"] for r in keep] == [4, 6] and [r["seq"] for r in old] == [1, 2, 3, 5]
    assert CL.trim(recs, cap=9) == (recs, [])
    assert not CL.over(recs, cap=2, slack=2) and CL.over(recs, cap=2, slack=1)


def test_parse_lines_skips_broken_and_sorts():
    lines = ['{"seq":2,"at":1,"turn":1,"kind":"sent"}', "{bad", "", '{"seq":1,"at":1,"turn":1,"kind":"ask"}',
             '{"seq":3,"at":1,"turn":1,"kind":"zzz"}', '{"seq":"4","at":1,"turn":1,"kind":"ask"}']
    recs, bad = CL.parse_lines(lines)
    assert [r["seq"] for r in recs] == [1, 2] and bad == 3
    assert CL.index(recs)["seq"] == 2 and CL.index(recs)["notes"] == {}


def test_since():
    recs = [{"seq": i, "at": 0, "turn": 1, "kind": "ask"} for i in (1, 2, 3)]
    assert [r["seq"] for r in CL.since(recs, 1, 3)["records"]] == [2, 3]
    assert CL.since(recs, None, 3)["records"] == recs and "reset" not in CL.since(recs, 3, 3)
    assert CL.since(recs, 9, 3)["reset"] is True and len(CL.since(recs, 9, 3)["records"]) == 3
    assert CL.parse_since(None) is None and CL.parse_since("4") == 4
    with pytest.raises(ValueError):
        CL.parse_since("-1")


@pytest.mark.slow
def test_chatlog_file_tap_reload_and_archive():
    import events as EV
    import chat_store
    tmp = Path(tempfile.mkdtemp(prefix="hd-chatlog-"))
    try:
        bus = EV.EventBus("p")
        log = chat_store.ChatLog(tmp)
        bus.taps.append(log.tap)
        assert log.post({"kind": "ask", "text": "버튼 키워", "notes": ["n1"], "chips": ["결제"]})[0] == 200
        bus.publish("request.sent", to=None, via="queue", notes=["n1"], text="요청문", path="q")
        bus.publish("agent.progress", agent=None, text="읽는 중", screen=None)
        bus.publish("notes.changed", rev=1)
        got = log.get(None)
        assert [r["kind"] for r in got["records"]] == ["ask", "sent", "progress"] and got["seq"] == 3
        assert log.post({"kind": "undone", "turn": 77})[0] == 404 and log.post({"kind": "x"})[0] == 400
        (tmp / CL.FILE).open("a", encoding="utf-8").write("{broken\n")
        again = chat_store.ChatLog(tmp)                                   # 다시 열기 — 파일에서 이어서(깨진 줄은 건너뜀)
        assert [r["seq"] for r in again.get(1)["records"]] == [2, 3]
        assert again.add("sent", {"notes": ["n2"], "via": "queue"})["seq"] == 4
        again.cap, again.slack = 1, 0
        again.add("sent", {"notes": ["n3"], "via": "queue"})
        arch = [json.loads(x) for x in (tmp / CL.ARCHIVE).read_text(encoding="utf-8").splitlines()]
        assert {r["turn"] for r in arch} == {1, 4}, "오래된 턴은 보관 파일로"
        assert [r["turn"] for r in chat_store.ChatLog(tmp).get(None)["records"]] == [5]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

