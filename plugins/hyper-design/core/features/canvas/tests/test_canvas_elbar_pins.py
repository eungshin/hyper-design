"""R50 요소 막대에 기능 고정하기 — 브라우저(크게 보기, file://).

요소 메뉴 줄 끝 핀(Chrome 확장 메뉴처럼) → 누르면 실행하지 않고 고정만, 메뉴는 열린 채, 막대가 바로 다시 그려짐 → 새로고침 뒤에도 그대로(prefs) →
막대 아이콘 오른쪽 클릭 '막대에서 빼기'(Office 빠른 실행처럼) → 빠짐. 6개면 고정 안 된 줄의 핀은 꺼짐 + 까닭.
캡처: HD_SHOTS_PINS(기본 %TEMP%/claude/tpins) — 메뉴 핀 · 고정 6개 막대 · '막대에서 빼기'."""
import os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx, reload  # noqa: F401
from test_canvas_text_remove import _open, out  # noqa: F401
from test_canvas_blocks import _modal, H1

SHOTS = Path(os.environ.get("HD_SHOTS_PINS", Path(tempfile.gettempdir()) / "claude" / "tpins"))
BAR = "[...document.querySelectorAll('#elbar button[data-act]')].map(b => b.dataset.act)"
PINS = "JSON.parse(localStorage.getItem('hd-canvas-prefs') || '{}').elbarPins"


def _pick(pg, mf):
    pg.click('#tools [data-tool="move"]')
    mf.click(H1)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)


def _menu(pg, mf):
    mf.click(H1, button="right")
    pg.wait_for_selector("#cmenu:not([hidden]) button[data-act]", timeout=3000)


def _pin(pg, act, box="#cmenu"):
    return pg.evaluate("([b, a]) => { const p = document.querySelector(b + ' [data-pin=\"' + a + '\"]'); return p && [p.getAttribute('aria-pressed'), p.getAttribute('aria-disabled'), p.getAttribute('aria-label'), p.title]; }", [box, act])


@pytest.mark.area("modal", "tools")
def test_pin_from_menu_shows_on_bar_survives_reload_and_unpins_by_right_click(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        mf = _modal(pg)
        _pick(pg, mf)
        assert pg.evaluate(BAR) == ["grip", "memo", "text", "ai", "more"], "고정 목록이 없으면 지금 막대 그대로"
        _menu(pg, mf)
        assert _pin(pg, "memo")[0] == "true" and _pin(pg, "dup")[0] == "false", (_pin(pg, "memo"), _pin(pg, "dup"))
        assert _pin(pg, "dup")[2] == "막대에 고정" and _pin(pg, "memo")[2] == "막대에서 빼기"
        assert _pin(pg, "chain") is None and _pin(pg, "part") is None, "묶음 머리('레이어 고르기 ▸'·'부품 ▸')에는 핀이 없다"
        assert pg.evaluate("[...document.querySelectorAll('#cmenu button[data-act]')].every(b => !b.closest('[data-pin]'))"), "핀은 줄 단추 밖(줄 단추 목록은 그대로)"
        pg.focus('#cmenu button[data-act="dup"]')
        pg.keyboard.press("Tab")
        assert pg.evaluate("document.activeElement.dataset.pin") == "dup", "줄에서 Tab = 그 줄의 핀"
        pg.hover('#cmenu button[data-act="dup"]')
        pg.screenshot(path=str(SHOTS / "menu-pins.png"))
        pg.click('#cmenu [data-pin="dup"]')
        assert pg.is_visible("#cmenu"), "핀을 누르면 메뉴는 열린 채"
        assert _pin(pg, "dup")[0] == "true"
        assert pg.evaluate(BAR) == ["grip", "memo", "text", "ai", "dup", "more"], "새로 고정 = 끝에, 막대가 바로 다시 그려짐"
        assert pg.evaluate(PINS) == ["memo", "text", "ai", "dup"]
        assert mf.evaluate("(s) => document.querySelectorAll(s).length", H1) == 1, "핀은 동작을 실행하지 않는다(복제 없음)"
        pg.keyboard.press("Escape")

        reload(pg)
        mf = _modal(pg)
        _pick(pg, mf)
        assert pg.evaluate(BAR) == ["grip", "memo", "text", "ai", "dup", "more"], "새로고침 뒤에도 고정 그대로"

        pg.click('#elbar [data-act="more"]', button="right")
        assert pg.is_hidden("#elunpin"), "⋯ 는 오른쪽 클릭해도 빼기 메뉴 없음"
        pg.click('#elbar [data-act="grip"]', button="right")
        assert pg.is_hidden("#elunpin"), "손잡이도 빼기 메뉴 없음"
        pg.click('#elbar [data-act="dup"]', button="right")
        pg.wait_for_selector("#elunpin:not([hidden])", timeout=2000)
        assert pg.inner_text("#elunpin").strip() == "막대에서 빼기"
        pg.screenshot(path=str(SHOTS / "bar-unpin.png"))
        pg.click('#elunpin [data-act="unpin"]')
        assert pg.is_hidden("#elunpin")
        assert pg.evaluate(BAR) == ["grip", "memo", "text", "ai", "more"]
        assert pg.evaluate(PINS) == ["memo", "text", "ai"]
        assert not errors, errors
    finally:
        pg.close()


@pytest.mark.area("modal", "tools")
def test_six_pins_max_disables_unpinned_rows_with_reason(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    SHOTS.mkdir(parents=True, exist_ok=True)
    try:
        mf = _modal(pg)
        _pick(pg, mf)
        _menu(pg, mf)
        for a in ("dup", "remove", "addr"):
            pg.click('#cmenu [data-pin="%s"]' % a)
        assert pg.evaluate(BAR) == ["grip", "memo", "text", "ai", "dup", "remove", "addr", "more"]
        pg.hover('#cmenu button[data-act="part"]')
        pg.wait_for_selector('#cmsub:not([hidden]) [data-pin="swap"]', timeout=3000)
        st = _pin(pg, "swap", "#cmsub")
        assert st[0] == "false" and st[1] == "true" and st[3] == "막대에는 6개까지 — 하나를 빼고 고정해 주세요", st
        pg.click('#cmsub [data-pin="swap"]', force=True)              # 꺼진 핀(aria-disabled)을 눌러도
        assert pg.evaluate(BAR)[-2] == "addr", "6개면 더 고정되지 않는다"
        pg.click('#cmenu [data-pin="remove"]')                      # 6개여도 고정된 줄은 뺄 수 있고, 빼면 다른 줄이 다시 켜진다
        pg.hover('#cmenu button[data-act="part"]')
        pg.wait_for_selector('#cmsub:not([hidden]) [data-pin="swap"]', timeout=3000)
        assert _pin(pg, "swap", "#cmsub")[1] is None, _pin(pg, "swap", "#cmsub")
        pg.click('#cmsub [data-pin="swap"]')
        assert pg.evaluate(BAR) == ["grip", "memo", "text", "ai", "dup", "addr", "swap", "more"]
        pg.keyboard.press("Escape")                                   # 옆 목록 닫기 → 메뉴 닫기(막대는 그대로)
        pg.keyboard.press("Escape")
        pg.wait_for_selector("#cmenu", state="hidden", timeout=2000)
        assert pg.is_visible("#elbar") and pg.evaluate(BAR)[-1] == "more"
        pg.wait_for_timeout(150)
        pg.screenshot(path=str(SHOTS / "bar-six.png"))
        assert not errors, errors
    finally:
        pg.close()
