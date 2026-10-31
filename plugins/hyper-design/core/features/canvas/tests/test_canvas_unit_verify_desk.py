"""V2 — hd verify 의 도우미 쪽(unit — verify_desk.VerifyDesk, 소켓 없음): 요청 → 'verify.ask' 이벤트 → 열린 캔버스가 잰 결과를 돌려줌 → 기다리던 요청이 받음.
열린 캔버스(이벤트 흐름)가 없으면 바로 no-canvas, 시간 안에 답이 없으면 timeout. 늦게 온 답·모르는 req 는 버린다(taken false)."""
import sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import events as EV  # noqa: E402
import verify_desk as VD  # noqa: E402


def bus_with_tab():
    bus = EV.EventBus("p", start=1)
    sub, _, _ = bus.subscribe(None)                   # 열린 캔버스 탭 하나(EventSource)
    return bus, sub


def answer_when_asked(desk, sub, result, delay=0.0):
    def run():
        ev = sub.get(5)
        assert ev and ev["type"] == "verify.ask"
        time.sleep(delay)
        desk.answer({"req": ev["req"], "result": dict(result, screen=ev["screen"])})
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_ask_publishes_event_and_returns_the_page_result():
    bus, sub = bus_with_tab()
    desk = VD.VerifyDesk(bus, wait=5)
    t = answer_when_asked(desk, sub, {"status": "differ", "app": "mock-home", "count": 1, "match": 3,
                                      "missing": [], "extra": [], "style": [], "unsure": [{"a": 1, "b": 1}]})
    code, res = desk.ask({"screen": "home"})
    t.join(5)
    assert code == 200 and res["status"] == "differ" and res["screen"] == "home" and res["count"] == 1 and res["app"] == "mock-home"
    assert isinstance(res["req"], str) and res["req"]


def test_no_open_canvas_answers_at_once():
    desk = VD.VerifyDesk(EV.EventBus("p", start=1), wait=5)
    t0 = time.monotonic()
    code, res = desk.ask({"screen": "home"})
    assert code == 200 and res["status"] == "no-canvas" and time.monotonic() - t0 < 1
    assert "hd open" in res["why"]


def test_no_answer_in_time_is_timeout_and_a_late_answer_is_dropped():
    bus, sub = bus_with_tab()
    desk = VD.VerifyDesk(bus, wait=0.3)
    code, res = desk.ask({"screen": "home"})
    assert code == 200 and res["status"] == "timeout" and res["screen"] == "home" and "답하지 않았어요" in res["why"]
    ev = sub.get(1)
    assert desk.answer({"req": ev["req"], "result": {"status": "match"}}) == (200, {"taken": False}), "늦은 답은 버린다"
    assert desk.answer({"req": "nope", "result": {"status": "match"}}) == (200, {"taken": False})


def test_wrong_shapes_are_400_and_a_bad_page_result_is_an_error_status():
    bus, sub = bus_with_tab()
    desk = VD.VerifyDesk(bus, wait=5)
    assert desk.ask({"screen": ""})[0] == 400 and desk.ask({})[0] == 400 and desk.ask({"screen": "x" * 300})[0] == 400
    assert desk.answer({"req": 3})[0] == 400 and desk.answer({"req": "a", "result": "x"})[0] == 400
    t = answer_when_asked(desk, sub, {"status": "great"})
    code, res = desk.ask({"screen": "home"})
    t.join(5)
    assert code == 200 and res["status"] == "error" and "모양" in res["why"]


def test_default_wait_is_ten_seconds():
    assert VD.WAIT == 10.0
    assert EV.TYPES.count("verify.ask") == 1
