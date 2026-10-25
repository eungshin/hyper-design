"""48c AI 되돌리기 — 순수 규칙(helper_model.ai_*): claim 때 쓰기 전 모습을 잡고, 처음 바뀌면 기록 한 줄, 또 바뀌면 같은 줄의 기준만, release 로 끝. 브라우저·I/O 없음."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import helper_model as H  # noqa: E402


def test_label_uses_title_else_id():
    assert H.ai_label("home", "홈") == "AI 반영 · 홈"
    assert H.ai_label("home", "  ") == "AI 반영 · home" and H.ai_label("home") == "AI 반영 · home"


def test_begin_keeps_first_snapshot():
    t = H.ai_begin({}, "home", "s1", "screens/home.html", "a", True)
    assert t == {"home": {"stamp": "s1", "rel": "screens/home.html", "before": "a", "existed": True, "after": "a", "logged": False}}
    assert H.ai_begin(t, "home", "s2", "screens/home.html", "b", True) is t, "다시 claim 해도 처음 모습(AI 쓰기 전)"


def test_seen_records_once_then_updates():
    t = H.ai_begin({}, "home", "s1", "screens/home.html", "a", True)
    t0 = t
    t, act = H.ai_seen(t, "home", "a")
    assert act is None and t is t0, "안 바뀜 = 할 일 없음"
    t, act = H.ai_seen(t, "home", "b")
    assert act == "record" and t["home"]["after"] == "b" and t["home"]["logged"] and t0["home"]["after"] == "a", "처음 바뀜 = 한 줄(원래 추적은 그대로)"
    t, act = H.ai_seen(t, "home", "c")
    assert act == "update" and t["home"]["after"] == "c", "또 바뀜 = 같은 줄의 기준만"
    assert H.ai_seen(t, "list", "x") == (t, None), "추적하지 않는 화면"


def test_end_returns_entry():
    t = H.ai_begin({}, "home", "s1", "r", "a", False)
    rest, e = H.ai_end(t, "home")
    assert rest == {} and e["stamp"] == "s1" and e["existed"] is False
    assert H.ai_end(rest, "home") == ({}, None)


def test_since_baseline_and_newer():
    log = [{"seq": 1, "stamp": "s1"}, {"seq": 2, "stamp": "s2"}]
    assert H.ai_since(log, None) == {"seq": 2, "writes": []} and H.ai_since(log, -1) == {"seq": 2, "writes": []}
    assert H.ai_since(log, 1) == {"seq": 2, "writes": [log[1]]} and H.ai_since(log, 2)["writes"] == []
    assert H.ai_since([], 0) == {"seq": 0, "writes": []}
