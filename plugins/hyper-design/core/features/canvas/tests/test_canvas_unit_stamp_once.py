"""보드 전환 S1 — 허브가 '지금 코드 도장'(git rev-parse)을 전환 한 번에 한 번만 잰다(registry.current_code, 2초 기억).
규칙(registry.stamp_fresh, 순수)은 시계를 바꿔 끼워 보고, 열기 → 페이지는 도장 재기(code_probe.current)를 센다. git·빌드·서버 없음(임시 out 만)."""
import sys
import types
from pathlib import Path

import pytest

CANVAS = Path(__file__).resolve().parents[1]
FEATURES = CANVAS.parent
sys.path[:0] = [str(CANVAS), str(FEATURES / "hd"), str(FEATURES / "home")]
import code_stamp as CS  # noqa: E402
import hd_client as C  # noqa: E402
import registry as RG  # noqa: E402

NOW = "g:aaaaaaaaaaaaaaaa"


def test_stamp_fresh_rule_keeps_a_stamp_under_ttl_only():
    """잰 지 ttl 초 안이면 다시 쓴다 · ttl 이 지나면(같음 포함) 다시 잰다 · 잰 적 없음 · 시계가 뒤로 가면 다시 잰다."""
    assert RG.stamp_fresh(10.0, 10.0, 2.0) and RG.stamp_fresh(10.0, 11.99, 2.0)
    assert not RG.stamp_fresh(10.0, 12.0, 2.0) and not RG.stamp_fresh(10.0, 30.0, 2.0)
    assert not RG.stamp_fresh(None, 10.0, 2.0), "잰 적 없음"
    assert not RG.stamp_fresh(10.0, 9.0, 2.0), "시계가 뒤로 감 — 믿지 않고 다시 잰다"
    assert RG.STAMP_TTL == 2.0


@pytest.fixture
def counted(monkeypatch):
    """code_probe.current(= git rev-parse) 부른 횟수를 센다 — 값은 NOW."""
    calls = []
    monkeypatch.setattr(C.CP, "current", lambda ref="HEAD": calls.append(ref) or NOW)
    return calls


def test_current_code_measures_once_per_ttl_with_injected_clock(counted):
    reg = RG.ProjectRegistry(lambda: 0, lambda: "")
    clock = [100.0]
    reg.clock = lambda: clock[0]
    counted.clear()
    assert reg.current_code() == NOW and len(counted) == 1
    clock[0] = 101.9
    assert reg.current_code() == NOW and len(counted) == 1, "2초 안 = git 을 다시 부르지 않음"
    clock[0] = 102.0
    assert reg.current_code() == NOW and len(counted) == 2, "2초가 지나면 다시 잰다"
    clock[0] = 120.0
    assert reg.current_code(max_age=RG.STALE_TTL) == NOW and len(counted) == 2, "허브 옛 코드 칩(30초)도 같은 기억을 쓴다"


def test_open_then_page_measures_the_code_stamp_once(tmp_path, monkeypatch, counted):
    """허브에서 판 하나로 전환(registry.open → 세션 page) = 코드 도장 재기 한 번."""
    out = tmp_path / "p" / "out"
    out.mkdir(parents=True)
    (out / "screens.json").write_text('{"title": "p", "groups": [], "screens": []}', encoding="utf-8")
    (out / "index.html").write_text(CS.stamp_page("<!doctype html><html><head></head><body></body></html>", NOW), encoding="utf-8")
    monkeypatch.setattr(C, "resolve", lambda target: ({"name": "p", "out": str(out)}, str(out)))
    monkeypatch.setattr(C, "serving", lambda o: None)
    monkeypatch.setattr(C, "live_record", lambda o: None)
    monkeypatch.setattr(C, "build", lambda o: (0, ""))
    monkeypatch.setattr(C, "load_projects", lambda: [])
    monkeypatch.setattr(C, "save_projects", lambda rows: None)
    monkeypatch.setattr(RG.P, "touch", lambda rows, o, t: rows)
    built = []
    reg = RG.ProjectRegistry(lambda: 1, lambda: "", build=lambda o: built.append(o) or types.SimpleNamespace(returncode=0, stdout="", stderr=""))
    clock = [1000.0]
    reg.clock = lambda: clock[0]
    counted.clear()
    try:
        reg.open("p")
        sess = reg.get("p")
        assert sess is not None
        html = sess.page()
        assert b"__hdHelper" in html
        assert len(counted) == 1, "열기와 페이지가 같은 도장을 쓴다(git rev-parse 한 번): %r" % counted
        assert not built, "지금 도장으로 구운 페이지 = 다시 빌드 없음"
        clock[0] += 5
        reg.get("p").page()
        assert len(counted) == 2, "2초 뒤 다음 페이지는 다시 잰다(커밋 뒤 옛 도장이 오래 남지 않게)"
    finally:
        reg.close_all()
