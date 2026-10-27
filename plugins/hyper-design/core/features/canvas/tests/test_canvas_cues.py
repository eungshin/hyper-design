"""보이는 고르기 안내(51-3, Figma F6·F10·F11) — 브라우저.

- 이동(V)으로 카드 하나를 고른 뒤 그 카드 안에 마우스를 올리면 다음 클릭이 고를 요소에 얇은 테두리(.elbox.hov) · 카드 밖으로 나가면 걷힘
- 요소를 고르면 그 부모에 점선(.elbox.par — 더 얇고 --ui-muted)
- 요소 오른쪽 클릭 메뉴 맨 위 '고르기 ▸' = 그 요소 + 조상(같은 상자 감싸기 건너뜀) — 고르면 그 요소
- 레이어 줄에 올리면 판의 그 카드 강조(.lyhov)
- 앱 카드 = 요소 상자 data-tone=app(--ui-app) + 고른 상자에 '요청으로만'
- 도우미 없이 끌어 옮기기 = 반영 대기 메모 하나(move op:to) + 미리보기가 그 자리로
규칙은 test_canvas_unit_cues.py(unit). 스크린샷 = HD_SHOTS_51_3(기본 %TEMP%/claude/t51-3)."""
import os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_text_remove import _open, out  # noqa: F401
from test_canvas_blocks import _xy, app_out  # noqa: F401
from test_canvas_edit import notes_of, wait_notes
from test_canvas_instant import TILE, TILES_JS, _grip_drag, _modal, _pick

SHOTS = Path(os.environ.get("HD_SHOTS_51_3", Path(tempfile.gettempdir()) / "claude" / "t51-3"))
H1 = "h1.title"
BOX = "(s) => { const b = document.querySelector(s); if (!b) return null; const r = b.getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height, bw: parseFloat(getComputedStyle(b).borderTopWidth), bs: getComputedStyle(b).borderTopStyle}; }"


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def _inside(b, x, y):
    return b and b["x"] - 1 <= x <= b["x"] + b["w"] + 1 and b["y"] - 1 <= y <= b["y"] + b["h"] + 1


def _url(o):
    return (o / "index.html").resolve().as_uri()


@pytest.mark.area("tools", "links")
def test_move_hover_shows_next_pick_then_parent_dashed_and_pick_menu(ctx, out):
    pg, errors = _open(ctx, _url(out))
    try:
        x, y = _xy(pg, H1)
        pg.keyboard.press("v")
        pg.mouse.move(x, y); pg.wait_for_timeout(500)
        assert pg.locator(".elbox").count() == 0, "카드를 고르기 전 이동 도구 = 다음 클릭은 카드 고르기 — 요소 테두리 없음"
        pg.mouse.click(x, y)
        pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
        pg.wait_for_timeout(600)
        pg.mouse.move(x - 4, y); pg.mouse.move(x, y)
        pg.wait_for_selector('.card[data-id="job"] .elbox.hov', timeout=4000)
        hv = pg.evaluate(BOX, '.card[data-id="job"] .elbox.hov')
        assert _inside(hv, x, y) and hv["bs"] == "solid", ("다음 클릭이 고를 요소(제목)에 얇은 실선", hv)
        shot(pg, "1-hover-before-click.png")
        pr = pg.locator("#screens").bounding_box()
        pg.mouse.move(pr["x"] + pr["width"] - 30, pr["y"] + pr["height"] - 30)   # 카드 밖(빈 판)
        pg.wait_for_function("!document.querySelector('.elbox.hov')", timeout=2000)

        pg.mouse.move(x, y); pg.wait_for_timeout(300)
        pg.mouse.click(x, y)
        pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
        pg.wait_for_selector('.card[data-id="job"] .elbox.par', timeout=4000)
        sel, par = pg.evaluate(BOX, ".elbox.sel"), pg.evaluate(BOX, ".elbox.par")
        assert par["bs"] == "dashed" and par["bw"] < sel["bw"], ("부모 = 더 얇은 점선", sel, par)
        assert par["x"] <= sel["x"] + 1 and par["y"] <= sel["y"] + 1 and par["x"] + par["w"] >= sel["x"] + sel["w"] - 1 and (par["w"], par["h"]) != (sel["w"], sel["h"]), ("부모 상자가 고른 요소를 감싸고 더 크다", sel, par)
        shot(pg, "2-picked-with-dashed-parent.png")

        pg.mouse.click(x, y, button="right")
        pg.wait_for_selector('#cmenu:not([hidden]) button[data-act="chain"]', timeout=4000)
        first = pg.evaluate("document.querySelector('#cmenu button[data-act]').dataset.act")
        assert first == "chain", ("요소 메뉴 첫 항목 = 레이어 고르기(R17 · R27 F05 소제목 없음)", first)
        assert pg.get_attribute('#cmenu button[data-act="chain"]', "aria-haspopup") == "menu", "레이어 고르기 ▸ = 옆 목록"
        pg.hover('#cmenu button[data-act="chain"]')
        pg.wait_for_selector("#cmsub:not([hidden]) button", timeout=4000)
        items = pg.evaluate("[...document.querySelectorAll('#cmsub button')].map(b => b.textContent)")
        assert len(items) >= 2 and items[0].startswith("✓ h1"), ("그 요소 + 조상", items)
        shot(pg, "5-select-layer-submenu.png")
        pg.click("#cmsub button:nth-of-type(2)")
        pg.wait_for_timeout(300)
        sel2 = pg.evaluate(BOX, ".elbox.sel")
        assert abs(sel2["w"] - par["w"]) < 2 and abs(sel2["h"] - par["h"]) < 2, ("둘째 = 상자가 다른 첫 조상(부모 점선과 같은 것)이 골라진다", sel2, par)
        assert pg.is_hidden("#cmenu") and pg.is_hidden("#cmsub")
    finally:
        pass                                             # 도우미 없음(file://) — 닫을 서버 없음
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "layers")
def test_layer_row_hover_highlights_board_card(ctx, out):
    pg, errors = _open(ctx, _url(out))
    pg.keyboard.press("0"); pg.wait_for_timeout(200)
    pg.click('#dock .dk-tab[data-p="layers"]')
    pg.hover('#lyTree [data-ly="job"] .ly-name')
    pg.wait_for_selector('.card[data-id="job"].lyhov', timeout=2000)
    assert pg.locator(".card.lyhov").count() == 1
    ol = pg.evaluate("getComputedStyle(document.querySelector('.card[data-id=\"job\"] .phone')).outlineStyle")
    assert ol == "solid", ol
    shot(pg, "3-layers-hover-card.png")
    pg.hover('#lyTree [data-kind="row"] .ly-name')
    pg.wait_for_function("document.querySelectorAll('.card.lyhov').length >= 1 && !document.querySelector('.card[data-id=\"job\"].lyhov') || document.querySelectorAll('.card.lyhov').length > 1", timeout=2000)
    pg.mouse.move(5, 300)                                # 나무 밖
    pg.wait_for_function("!document.querySelector('.card.lyhov')", timeout=2000)
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_app_card_boxes_carry_request_only_accent(ctx, app_out):
    pg, errors = _open(ctx, _url(app_out))
    x, y = _xy(pg, H1)
    pg.keyboard.press("v")
    pg.mouse.click(x, y)
    pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(x, y)
    pg.wait_for_selector('.elbox.sel[data-tone="app"]', timeout=8000)
    tag = pg.evaluate("getComputedStyle(document.querySelector('.elbox.sel'), '::after').content")
    assert "요청으로만" in tag, tag
    col = pg.evaluate("getComputedStyle(document.querySelector('.elbox.sel')).borderTopColor")
    app = pg.evaluate("(() => { const d = document.createElement('div'); d.style.color = 'var(--ui-app)'; document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; })()")
    assert col == app, ("앱 카드 상자 = --ui-app", col, app)
    shot(pg, "4-app-card-accent-tag.png")
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "modal")
def test_drag_without_helper_queues_one_move_to_note_and_previews_it(ctx, out):
    pg, errors = _open(ctx, _url(out))
    mf = _modal(pg)
    before = mf.evaluate(TILES_JS)
    _pick(pg, mf, TILE % 1)
    _grip_drag(pg, mf, TILE % 3, 0.8)
    wait_notes(pg, 1)
    n = notes_of(pg)
    assert [(x.get("edit"), x.get("op"), x.get("to")) for x in n] == [("move", "to", 2)], ("끌기 한 번 = 반영 대기 하나(move op:to)", n)
    want = [before[1], before[2], before[0]]
    for _ in range(30):
        if mf.evaluate(TILES_JS)[:3] == want:
            break
        pg.wait_for_timeout(100)
    assert mf.evaluate(TILES_JS)[:3] == want, ("미리보기 = 놓은 자리", mf.evaluate(TILES_JS)[:3])
    assert not errors, errors
    pg.close()
