"""Figma 고르기 키(51-2) — 브라우저. 판에서 요소를 고른 채: Tab/Shift+Tab = 형제(끝에서 돈다) · Shift+Enter = 부모 · Enter = 글자면 그 자리 고치기, 아니면 첫 자식.
그 자리 고치기를 취소·저장해도 그 요소가 골라진 채 막대가 남는다(Figma F14). Alt+클릭 = 카드를 안 골랐어도 그 자리 가장 안쪽 요소. 입력 칸(대화창)의 Tab 은 건드리지 않는다.
규칙은 test_canvas_unit_figma_keys.py(unit)."""
import os

import pytest

from test_canvas_v2 import browser, ctx, zoom_to  # noqa: F401
from test_canvas_text_remove import _open, _frame, _serve, inline_type, out  # noqa: F401
from test_canvas_blocks import _xy, _pick_element, _wait_file

SHOTS = os.environ.get("HD_SHOTS")                   # 눈으로 볼 때만: 스크린숏 폴더
TILES = ".tile-grid > button"

# 고른 테두리(.elbox.sel)가 그 화면 요소(sel, nth)와 같은 자리인가 — 카드 틀 좌표로 비교(배율 = phone 너비 / 카드 너비)
SAME = """([sid, sel, nth]) => {
  const card = document.querySelector('.card[data-id="' + sid + '"]'), box = card && card.querySelector('.elbox.sel');
  if (!box) return false;
  const fs = card.querySelectorAll('.phone iframe'), f = fs[fs.length - 1], d = f && f.contentDocument;
  const el = d && d.querySelectorAll(sel)[nth || 0]; if (!el) return false;
  const ph = card.querySelector('.phone'), sc = ph.getBoundingClientRect().width / f.offsetWidth * (f.offsetWidth / ph.offsetWidth);
  const r = el.getBoundingClientRect(), b = box.getBoundingClientRect(), p = ph.getBoundingClientRect(), k = p.width / f.offsetWidth;
  return Math.abs(p.left + r.left * k - b.left) < 3 && Math.abs(p.top + r.top * k - b.top) < 3 && Math.abs(r.width * k - b.width) < 3;
}"""


def _is(pg, sel, nth=0, sid="job"):
    pg.wait_for_function(SAME, arg=[sid, sel, nth], timeout=5000)
    assert pg.is_visible("#elbar"), "막대가 떠 있다"


@pytest.mark.area("tools", "modal")
def test_figma_keys_walk_siblings_parent_child_and_enter_edits_text(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        _pick_element(pg, _xy(pg, TILES + ":nth-of-type(2)"))
        _is(pg, TILES, 1)
        pg.keyboard.press("Tab")
        _is(pg, TILES, 2)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-2-tab.png"))
        pg.keyboard.press("Shift+Tab"); _is(pg, TILES, 1)
        pg.keyboard.press("Shift+Tab"); pg.keyboard.press("Shift+Tab")
        _is(pg, TILES, 8)                                # 맨 앞에서 Shift+Tab = 맨 뒤로(돈다)
        pg.keyboard.press("Tab"); _is(pg, TILES, 0)      # 맨 뒤에서 Tab = 맨 앞으로
        pg.keyboard.press("Shift+Enter"); _is(pg, ".tile-grid")
        pg.keyboard.press("Enter"); _is(pg, TILES, 0)    # 글자 요소가 아니면 첫 자식
        pg.keyboard.press("Shift+Enter"); pg.keyboard.press("Shift+Tab"); _is(pg, "p.lead")
        pg.keyboard.press("Shift+Tab"); _is(pg, "h1.title")
        pg.keyboard.press("Enter")                       # 글자 요소 = 그 자리 고치기(49c)
        fr = _frame(pg)
        fr.wait_for_function("document.querySelector('h1.title').isContentEditable", timeout=3000)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-2-enter-edit.png"))
        pg.keyboard.press("Escape")
        fr.wait_for_function("!document.querySelector('h1.title').isContentEditable", timeout=3000)
        _is(pg, "h1.title")                              # 취소 뒤에도 그 요소가 골라진 채(Figma F14)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-2-after-edit.png"))
        pg.keyboard.press("Enter")                       # 저장해도 그대로(도우미가 쓰고 카드를 다시 실은 뒤에도)
        inline_type(pg, _frame(pg), "h1.title", "새 제목")
        _wait_file(pg, out, lambda s: '<h1 class="title">새 제목</h1>' in s, "그 자리 고치기가 파일에 써지지 않았다")
        pg.wait_for_timeout(1500)
        _is(pg, "h1.title")
        pg.focus("#hdchat textarea")                     # 입력 칸의 Tab 은 그 칸 것 — 고른 요소는 그대로
        pg.keyboard.press("Tab")
        _is(pg, "h1.title")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_alt_click_picks_the_innermost_element_without_selecting_the_card_first(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        ph = zoom_to(pg, "job", 420)
        fr = _frame(pg)
        fr.wait_for_selector(TILES, state="attached", timeout=5000)
        r = fr.evaluate("(s) => { const b = document.querySelectorAll(s)[1].querySelector('.n').getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }", TILES)
        k = ph["width"] / pg.evaluate("document.querySelector('.card[data-id=\"job\"] .phone iframe').offsetWidth")
        pg.keyboard.press("Escape")
        assert pg.evaluate("!document.querySelector('.card.picked')"), "카드를 아직 안 골랐다"
        pg.keyboard.down("Alt"); pg.mouse.click(ph["x"] + r["x"] * k, ph["y"] + r["y"] * k); pg.keyboard.up("Alt")
        _is(pg, TILES + " > .n", 1)                      # 버튼(누를 수 있는 요소)이 아니라 그 안 번호 글
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
