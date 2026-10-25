"""요소 막대(#elbar)가 고른 요소·꼬리표·바로 옆 형제를 덮지 않는다(t51-7a, Figma: 고른 것 바깥 바로 위 — 자리가 없으면 아래).

K1 재현 두 장면(t51-5 alt-drag-mid · t51-3 2-picked-with-dashed-parent):
- 크게 보기(도우미): 첫 타일을 고르면 막대가 아래 줄 타일("개발자·엔지니어")을 덮었다
- 판(file://, 화면 글을 읽을 수 없음): 제목(h1)을 고르면 막대가 그 위 "설정 1 / 3" 줄을 덮었다
규칙은 test_canvas_unit_bar_place.py(unit). 스크린샷 = HD_SHOTS_51_7A(기본 %TEMP%/claude/t51-7a)."""
import os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_text_remove import _frame, _open, _serve, out  # noqa: F401
from test_canvas_blocks import _pick_element, _xy
from test_canvas_instant import TILE, _in_modal, _modal, _pick

SHOTS = Path(os.environ.get("HD_SHOTS_51_7A", Path(tempfile.gettempdir()) / "claude" / "t51-7a"))
RECT = "(() => { const r = document.querySelector('%s').getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; })()"
# 고른 상자 위 종류 꼬리표(.elbox.sel::before) 의 화면 사각형 — 판 배율(z)·꼬리표 배율(--ts) 포함
LABEL = """(() => { const b = document.querySelector('.elbox.sel'), r = b.getBoundingClientRect(), cs = getComputedStyle(b, '::before');
  if (b.classList.contains('in') || cs.display === 'none') return null;
  const z = r.width / b.offsetWidth, ts = parseFloat(b.style.getPropertyValue('--ts')) || 1, w = parseFloat(cs.width) * ts * z, h = parseFloat(cs.height) * ts * z;
  return {x: r.left - 2 * z, y: r.top - (h + 2 * ts * z), w: w, h: h}; })()"""


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


PAD = 3                                              # 둘레 내용과 막대 사이 최소 틈(막대 그림자가 글에 닿으면 덮은 것으로 보인다 — 증거 t51-3 은 2px)


def _overlap(a, b, pad=0):
    return bool(a and b) and a["x"] - pad < b["x"] + b["w"] and a["x"] + a["w"] + pad > b["x"] and a["y"] - pad < b["y"] + b["h"] and a["y"] + a["h"] + pad > b["y"]


def _text_in_modal(pg, mf, sel):
    """크게 보기 틀 안 요소의 글자 상자(줄 높이가 아니라 글자 — Range)의 화면 사각형."""
    r = mf.evaluate("(s) => { const g = document.createRange(); g.selectNodeContents(document.querySelector(s)); const b = g.getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }", sel)
    f = pg.evaluate("(() => { const f = document.getElementById('mframe'), r = f.getBoundingClientRect(), sc = r.width / f.offsetWidth; return {x: r.left + f.clientLeft * sc, y: r.top + f.clientTop * sc, sc: sc}; })()")
    return {"x": f["x"] + r["x"] * f["sc"], "y": f["y"] + r["y"] * f["sc"], "w": r["w"] * f["sc"], "h": r["h"] * f["sc"]}


def _card_rect(pg, sel, sid="job"):
    """판 카드 틀 안 요소의 화면 사각형(틀 배율 포함)."""
    fr = _frame(pg, sid)
    r = fr.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }", sel)
    f = pg.evaluate("""(sid) => { const fs = document.querySelectorAll('.card[data-id="' + sid + '"] .phone iframe'), f = fs[fs.length - 1], r = f.getBoundingClientRect(), sc = r.width / f.offsetWidth;
      return {x: r.left + f.clientLeft * sc, y: r.top + f.clientTop * sc, sc: sc}; }""", sid)
    return {"x": f["x"] + r["x"] * f["sc"], "y": f["y"] + r["y"] * f["sc"], "w": r["w"] * f["sc"], "h": r["h"] * f["sc"]}


@pytest.mark.area("modal", "tools")
def test_modal_bar_does_not_cover_the_picked_tile_or_its_neighbour_tiles(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal(pg)
        _pick(pg, mf, TILE % 1)
        pg.wait_for_timeout(400)                          # 형제 상자 답(hd-sibs) 뒤 다시 놓기
        bar = pg.evaluate(RECT % "#elbar")
        shot(pg, "modal-tile-picked.png")
        tiles = [_in_modal(pg, mf, TILE % i) for i in range(1, 7)]
        assert not _overlap(bar, tiles[0]), ("막대가 고른 타일을 덮는다", bar, tiles[0])
        hit = [i + 1 for i, t in enumerate(tiles[1:], 1) if _overlap(bar, t)]   # 위 안내 글과 타일 사이 틈(27px)이 막대(24px)+틈보다 좁다 — 덮지만 않으면 된다
        assert not hit, ("막대가 옆 타일을 덮는다(위에 빈 자리가 있는데)", hit, bar, tiles[:4])
        lead = _text_in_modal(pg, mf, "p.lead")
        assert not _overlap(bar, lead), ("막대가 위 안내 글(글자)을 덮는다", bar, lead)
        assert not _overlap(bar, pg.evaluate(RECT % "#modal .mbar")), "창 제목 막대를 덮지 않는다"
        assert not errors, errors
    finally:
        pg.close()
        srv.shutdown(); srv.server_close()


@pytest.mark.area("tools", "links")
def test_board_bar_does_not_cover_the_picked_heading_its_label_or_the_line_above(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    try:
        _pick_element(pg, _xy(pg, "h1.title"))
        pg.wait_for_selector(".elbox.sel", timeout=4000)
        pg.wait_for_timeout(500)
        bar, sel, lab = pg.evaluate(RECT % "#elbar"), pg.evaluate(RECT % ".elbox.sel"), pg.evaluate(LABEL)
        eyebrow, lead = _card_rect(pg, "p.eyebrow"), _card_rect(pg, "p.lead")
        shot(pg, "board-heading-picked.png")
        assert not _overlap(bar, sel), ("막대가 고른 제목을 덮는다", bar, sel)
        assert not _overlap(bar, lab), ("막대가 종류 꼬리표를 덮는다", bar, lab)
        assert not _overlap(bar, eyebrow, PAD), ("막대가 제목 위 줄('설정 1 / 3')을 덮는다", bar, eyebrow)
        assert not _overlap(bar, lead, PAD), ("막대가 제목 아래 줄을 덮는다", bar, lead)
        assert not _overlap(bar, pg.evaluate(RECT % "#selbar")) if pg.is_visible("#selbar") else True
        assert not errors, errors
    finally:
        pg.close()
