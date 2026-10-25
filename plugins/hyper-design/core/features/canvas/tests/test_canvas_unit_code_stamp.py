"""code_stamp.py(Model) — 코드 도장 모양과 '떠 있는 서버를 다시 쓸까' 규칙. I/O 없음(통합은 hd/tests/test_hd_code_fresh.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import code_stamp as CS  # noqa: E402

NOW, OLD = "g:aaaaaaaaaaaaaaaa", "g:bbbbbbbbbbbbbbbb"


def test_tree_stamp_takes_a_sha_prefix_and_refuses_junk():
    assert CS.tree_stamp("5BCCBCA152545188" + "0" * 24 + "\n") == "g:5bccbca152545188"
    assert CS.tree_stamp("") is None and CS.tree_stamp("fatal: not a tree") is None and CS.tree_stamp(None) is None


def test_content_stamp_follows_content_not_order():
    a = CS.content_stamp([("x.js", b"1"), ("y.js", b"2")])
    assert a.startswith("w:") and len(a) == 18
    assert a == CS.content_stamp([("y.js", b"2"), ("x.js", b"1")]), "차례가 달라도 같은 도장"
    assert a != CS.content_stamp([("x.js", b"1"), ("y.js", b"3")]), "한 바이트만 달라도 다른 도장"
    assert a != CS.content_stamp([("z.js", b"1"), ("y.js", b"2")]), "이름도 도장에 든다"


def test_page_round_trip_and_replace():
    html = "<!doctype html><html><head><meta charset=utf-8></head><body></body></html>"
    once = CS.stamp_page(html, NOW)
    assert CS.page_stamp(once) == NOW and once.index("hd-code") < once.index("charset"), "<head> 바로 뒤(앞 8 KB 만 읽어도 보이게)"
    twice = CS.stamp_page(once, OLD)
    assert CS.page_stamp(twice) == OLD and twice.count("hd-code") == 1, "다시 구우면 바꾼다(둘이 되지 않음)"
    assert CS.page_stamp(html) is None and CS.page_stamp("") is None and CS.page_stamp(None) is None, "도장 전 빌드 = None(옛것)"
    assert CS.stamp_page(html, None) == html


def test_stale_only_when_the_current_stamp_is_known():
    assert CS.stale(OLD, NOW) and CS.stale(None, NOW)
    assert not CS.stale(NOW, NOW)
    assert not CS.stale(OLD, None) and not CS.stale(None, ""), "지금 도장을 모르면(git 실패) 헛 빌드·헛 재시작을 하지 않는다"


def test_reuse_verdict_fresh_rebuild_restart_busy():
    v = CS.reuse_verdict
    assert v(NOW, NOW, NOW) == "fresh"
    assert v(OLD, NOW, NOW) == "rebuild", "새 코드 서버 + 옛 페이지 = 페이지만"
    assert v(None, NOW, NOW) == "rebuild", "도장 전 빌드(이번 버그의 프로젝트) = 옛 페이지"
    assert v(NOW, OLD, NOW) == "restart" and v(OLD, None, NOW) == "restart", "옛 코드로 뜬 쉬는 도우미(옛 도우미는 code 칸이 없음) = 끄고 새로"
    assert v(OLD, OLD, NOW, busy=True) == "busy", "AI 덮개 중이면 끄지 않는다"
    assert v(OLD, OLD, NOW, movable=False) == "rebuild", "허브 안 세션은 끌 수 없다 — 페이지만(허브 알림은 따로)"
    assert v(NOW, OLD, NOW, busy=True, movable=False) == "fresh"
    assert v(OLD, OLD, None) == "fresh", "지금 도장을 모르면 그대로"


def test_page_after_rebuilds_the_page_even_when_the_busy_process_stays():
    assert CS.page_after("rebuild", OLD, NOW)
    assert CS.page_after("busy", OLD, NOW) and not CS.page_after("busy", NOW, NOW)
    assert not CS.page_after("fresh", OLD, NOW) and not CS.page_after("restart", OLD, NOW), "restart 는 새 프로세스 앞에서 빌드한다"


def test_model_has_no_io():
    src = (Path(CS.__file__)).read_text(encoding="utf-8")
    for bad in ("open(", "subprocess", "pathlib", "os.", "urllib", "time."):
        assert bad not in src, bad
