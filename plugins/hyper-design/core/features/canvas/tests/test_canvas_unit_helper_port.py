"""도우미 포트·한 out 에 하나(#270 · #271)의 순수 규칙 — 포트 차례 · .hd-helper.json 풀기 · 띄울지 정하기. I/O 없음."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import helper  # noqa: E402
import hd_model  # noqa: E402  (helper 가 hd 폴더를 path 에 넣는다)


def test_port_order_tries_last_port_then_any():
    assert helper.port_order(51234) == [51234, 0], "지난 포트 먼저, 막히면 빈 포트"
    assert helper.port_order(None) == [0]
    assert helper.port_order(0) == [0] and helper.port_order(70000) == [0] and helper.port_order("51234") == [0], "이상한 값은 버림"
    assert helper.port_order(51234, 4000) == [4000], "--port 를 주면 그것만"
    assert helper.port_order(True) == [0], "bool 은 포트가 아님"


def test_helper_record_reads_live_stopped_and_old_shapes():
    live = {"url": "http://127.0.0.1:5123/index.html?hd=tok-1", "pid": 42, "port": 5123, "token": "tok-1"}
    assert hd_model.helper_record(live) == {"port": 5123, "pid": 42, "url": live["url"], "token": "tok-1"}
    assert hd_model.helper_record({"port": 5123}) == {"port": 5123, "pid": None, "url": None, "token": None}, "정상 종료 뒤 = 포트만"
    old = hd_model.helper_record({"url": "http://127.0.0.1:6001/index.html?hd=abc_D-9", "pid": 7})
    assert old["port"] == 6001 and old["token"] == "abc_D-9" and old["pid"] == 7, "옛 모양은 url 에서 포트·토큰"
    assert hd_model.helper_record([1]) is None and hd_model.helper_record(None) is None
    bad = hd_model.helper_record({"url": "", "pid": -3, "port": "x"})
    assert bad == {"port": None, "pid": None, "url": None, "token": None}


def test_start_verdict_refuses_only_live_answering_helper():
    rec = {"port": 5123, "pid": 42, "url": "http://127.0.0.1:5123/index.html?hd=t", "token": "t"}
    assert hd_model.start_verdict(rec, alive=True, answers=True) == "refuse"
    assert hd_model.start_verdict(rec, alive=False, answers=False) == "start", "죽은 pid → 덮어씀"
    assert hd_model.start_verdict(rec, alive=True, answers=False) == "start", "pid 번호를 다른 프로그램이 받음 · 답 없음 → 덮어씀"
    assert hd_model.start_verdict({"port": 5123, "pid": None, "url": None, "token": None}, True, True) == "start", "정상 종료 기록"
    assert hd_model.start_verdict(None, True, True) == "start"
