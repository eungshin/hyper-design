"""요소 막대 자리·크기(polish-1) — 브라우저. 크게 보기에서 고른 요소 바로 위 줄 글(앞 형제)을 막대가 덮지 않는다 ·
요소 칸보다 넓으면 뒤 단추가 "⋯" 로 넘어가고 ⋯ 목록에서 누를 수 있다. 규칙은 test_canvas_unit_blocks_place.py(unit).
둘레 글 상자는 같은 출처 화면에서만 읽으므로 도우미(http)로 연다."""
import os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_text_remove import _open, _serve, out  # noqa: F401
from test_canvas_blocks import _modal

SHOTS = Path(os.environ.get("HD_SHOTS_POLISH", Path(tempfile.gettempdir()) / "claude" / "tpolish"))
RECT = "(() => { const r = document.querySelector('%s').getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; })()"


def _screen_rect(pg, mf, sel):
    r = mf.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }", sel)
    m = pg.evaluate("(() => { const f = document.getElementById('mframe'), b = f.getBoundingClientRect(); return {x: b.left, y: b.top, sc: b.width / f.offsetWidth}; })()")
    return {"x": m["x"] + r["x"] * m["sc"], "y": m["y"] + r["y"] * m["sc"], "w": r["w"] * m["sc"], "h": r["h"] * m["sc"]}


def _overlap(a, b):
    return a["x"] < b["x"] + b["w"] and a["x"] + a["w"] > b["x"] and a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"]


def _pick(pg, mf, sel):
    mf.click(sel)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    pg.wait_for_function("(s) => document.querySelector('#elbar').dataset.path && document.querySelector('#elbar').dataset.path.length > 0", arg=sel)
    pg.wait_for_timeout(200)
    return pg.evaluate(RECT % "#elbar")


@pytest.mark.area("modal", "tools")
def test_bar_skips_the_text_line_above_and_folds_extra_buttons(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal(pg)
        pg.click('#tools [data-tool="move"]')
        pg.wait_for_timeout(300)
        bar = _pick(pg, mf, "p.lead")
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / "bar-lead-after.png"))
        h1, lead, mb = _screen_rect(pg, mf, "h1.title"), _screen_rect(pg, mf, "p.lead"), pg.evaluate(RECT % "#modal .mbar")
        assert not _overlap(bar, h1), ("막대가 바로 위 줄 글(앞 형제 h1)을 덮는다", bar, h1)
        assert not _overlap(bar, lead), ("막대가 고른 요소를 덮는다", bar, lead)
        assert not _overlap(bar, mb), ("창 제목 막대를 덮는다", bar, mb)
        assert bar["h"] <= 26, ("막대는 한 줄로 낮게", bar)

        tile = ".tile-grid > button:nth-of-type(4)"                    # 좁은 요소 — 막대가 요소 칸(최소 220)을 넘으면 ⋯
        bar = _pick(pg, mf, tile)
        pg.screenshot(path=str(SHOTS / "bar-tile-after.png"))
        el = _screen_rect(pg, mf, tile)
        more = pg.get_attribute("#elbar", "data-more") or ""
        assert more and pg.is_visible("#elbar [data-more]"), ("넘친 단추는 ⋯ 로", more)
        assert bar["w"] <= max(el["w"], 220) + 1, (bar, el)
        assert not _overlap(bar, el), (bar, el)
        assert not _overlap(bar, pg.evaluate(RECT % "#tools")), ("왼쪽 도구 막대를 덮지 않는다", bar)
        pg.click("#elbar [data-more]")
        pg.wait_for_selector("#elpop:not([hidden]) .ep-act", timeout=3000)
        got = pg.evaluate("[...document.querySelectorAll('#elpop .ep-act')].map(b => b.dataset.act)")
        assert got == more.split(), (got, more)
        pg.screenshot(path=str(SHOTS / "bar-tile-more-after.png"))
        assert not errors, errors
    finally:
        pg.close()
        srv.shutdown()
