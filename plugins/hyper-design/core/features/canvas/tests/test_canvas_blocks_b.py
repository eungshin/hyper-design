"""블록 조립(task 49b) — 브라우저. 막대 자리(크게 보기: 고른 요소 위, 자리 없으면 아래, 요소를 덮지 않음) · [상위]·[ 키 ·
쓴 뒤 고른 요소 따라가기 · 속성 칸(attr) · 부품 바꾸기/넣기. 규칙은 test_canvas_unit_blocks_b.py(unit)."""
import os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, zoom_to  # noqa: F401
from test_canvas_text_remove import _open, _frame, _serve, out  # noqa: F401
from test_canvas_blocks import _xy, _pick_element, _bar, _frame_until, _logged, _job, _wait_file, _modal, H1, TILE2

SHOTS = Path(os.environ.get("HD_SHOTS_49B", Path(tempfile.gettempdir()) / "claude" / "t49b"))


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def _modal_sel(pg, mf, sel):
    mf.click(sel)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(150)
    return pg.evaluate("""(s) => {
      const f = document.getElementById('mframe'), fr = f.getBoundingClientRect(), sc = fr.width / f.offsetWidth;
      const e = f.contentDocument ? null : null;
      const b = document.querySelector('#elbar').getBoundingClientRect();
      return {bar: {x: b.left, y: b.top, w: b.width, h: b.height}, frame: {x: fr.left, y: fr.top, w: fr.width, h: fr.height}, sc: sc};
    }""", sel)


def _el_rect(pg, mf, sel):
    r = mf.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }", sel)
    m = pg.evaluate("(() => { const f = document.getElementById('mbox').getBoundingClientRect(); return {x: f.left, y: f.top, w: f.width}; })()")
    sc = pg.evaluate("(() => { const f = document.getElementById('mframe'); return document.getElementById('mbox').getBoundingClientRect().width / f.offsetWidth; })()")
    return {"x": m["x"] + r["x"] * sc, "y": m["y"] + r["y"] * sc, "w": r["w"] * sc, "h": r["h"] * sc}


def _overlap(a, b):
    return a["x"] < b["x"] + b["w"] and a["x"] + a["w"] > b["x"] and a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"]


@pytest.mark.area("modal", "tools")
def test_large_view_bar_sits_above_the_element_and_never_covers_it(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    mf = _modal(pg)
    pg.click('#tools [data-tool="move"]')
    pg.set_viewport_size({"width": 1280, "height": 720})       # 작은 창 — 크게 보기가 위쪽 줄 바로 아래까지 찬다
    pg.wait_for_timeout(300)
    box = pg.evaluate("(() => { const r = document.getElementById('modal').getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; })()")
    for i, sel in enumerate([".lead", TILE2, H1, "a.wizard-close", "p.eyebrow"]):
        got = _modal_sel(pg, mf, sel)
        mb = pg.evaluate("(() => { const r = document.querySelector('#modal .mbar').getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; })()")
        el = _el_rect(pg, mf, sel)
        bar = got["bar"]
        assert box["x"] <= bar["x"] and bar["x"] + bar["w"] <= box["x"] + box["w"] and bar["y"] >= box["y"], (sel, "막대는 크게 보기 덮개 안(도크·위쪽 줄 위가 아님)", bar, box)
        shot(pg, "step1-modal-%d-%s.png" % (i, os.environ.get("HD_49B_PHASE", "after")))
        assert not _overlap(bar, el), (sel, "막대가 고른 요소를 덮는다", bar, el)
        assert not _overlap(bar, mb), (sel, "창 제목 막대(닫기)를 덮지 않는다", bar, mb)
        room = el["y"] - bar["h"] - 6 >= mb["y"] + mb["h"]                 # 창 제목 막대 아래에 자리가 있으면
        if room:
            assert bar["y"] + bar["h"] <= el["y"] + 1, (sel, "자리가 있으면 요소 위", bar, el)
    assert not errors, errors
    pg.close()


def _path(pg):
    return pg.get_attribute("#elbar", "data-path")


def _wait_path(pg, ok, what):
    for _ in range(150):
        try:
            if not pg.is_hidden("#elbar") and ok(_path(pg) or ""):
                return _path(pg)
        except Exception:
            pass
        pg.wait_for_timeout(100)
    raise AssertionError(what + " — 지금: " + str(_path(pg)))


@pytest.mark.area("modal", "tools")
def test_large_view_parent_button_and_bracket_key_walk_up_to_a_section(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    mf = _modal(pg)
    pg.click('#tools [data-tool="move"]')
    mf.click(TILE2)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    assert "tile" in _path(pg) and "nth-of-type(2)" in _path(pg), _path(pg)
    pg.click('#elbar [data-act="parent"]')
    _wait_path(pg, lambda p: p.endswith("div.tile-grid") or p.endswith("div.tile-grid:nth-of-type(1)"), "[상위] = 타일 묶음")
    shot(pg, "step2-modal-parent-grid.png")
    pg.keyboard.press("BracketLeft")
    _wait_path(pg, lambda p: "wizard-content" in p, "[ = 한 번 더 위(내용 묶음)")
    shot(pg, "step2-modal-parent-section.png")
    pg.keyboard.press("Delete")                                 # 고른 묶음 통째로 지우기(도우미 없음 = 반영 대기)
    from test_canvas_edit import notes_of, wait_notes
    wait_notes(pg, 1)
    n = notes_of(pg)[0]
    assert n["edit"] == "remove" and "wizard-content" in n["path"], n
    mf.wait_for_function("() => getComputedStyle(document.querySelector('.wizard-content')).display === 'none'", timeout=3000)
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools")
def test_board_selection_follows_the_moved_element_so_alt_down_repeats(ctx, out):
    before = _job(out)
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        _pick_element(pg, _xy(pg, TILE2))
        p0 = _path(pg)
        pg.keyboard.press("Alt+ArrowDown")
        _wait_file(pg, out, lambda s: s.index("어학 시험 준비") < s.index("대학원생·연구원"), "Alt+↓ 한 번")
        _wait_path(pg, lambda p: p != p0 and "nth-of-type(3)" in p, "쓴 뒤 막대가 옮긴 요소(3번째)로 돌아온다")
        shot(pg, "step3-board-after-first-move.png")
        _logged(pg)
        pg.keyboard.press("Alt+ArrowDown")                      # 다시 고르지 않고 한 번 더
        _wait_file(pg, out, lambda s: s.index("개발자·엔지니어") < s.index("대학원생·연구원"), "Alt+↓ 두 번째 — 다시 고르지 않아도")
        _wait_path(pg, lambda p: "nth-of-type(4)" in p, "두 번째 뒤에도 같은 요소")
        _frame_until(pg, "() => document.querySelectorAll('.tile-grid > button')[3].textContent.indexOf('대학원생') >= 0")
        pg.wait_for_timeout(400)
        shot(pg, "step3-board-after-second-move.png")
        box = pg.evaluate("(() => { const b = document.querySelector('.elbox.sel'); return b ? b.getBoundingClientRect().width : 0; })()")
        assert box > 0, "고른 테두리도 다시 그려진다"
        _logged(pg)
        pg.keyboard.press("Control+z")
        pg.wait_for_timeout(300)
        pg.keyboard.press("Control+z")
        _wait_file(pg, out, lambda s: s == before, "되돌리기 두 번 = 처음")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def _modal_helper(pg):
    mf = _modal(pg)
    pg.click('#tools [data-tool="move"]')
    return mf


def _modal_frame_until(pg, js):
    """크게 보기가 새 파일(?v=)로 다시 실려 js 가 참이 될 때까지."""
    for _ in range(200):
        try:
            f = pg.query_selector("#mframe")
            if "?v=" in (f.get_attribute("src") or ""):
                fr = f.content_frame()
                if fr and fr.evaluate(js):
                    return fr
        except Exception:
            pass
        pg.wait_for_timeout(100)
    raise AssertionError("크게 보기가 새 파일로 다시 실리지 않았다: " + js)


IMG = "aside .art-card > img"


@pytest.mark.area("helper", "modal")
def test_attr_fields_write_img_alt_at_once_and_undo_restores(ctx, out):
    before = _job(out)
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal_helper(pg)
        mf.click(IMG)
        pg.wait_for_selector('#elbar [data-act="attr"]', timeout=8000)
        pg.click('#elbar [data-act="attr"]')
        pg.wait_for_selector("#elpop:not([hidden]) input[data-name]", timeout=3000)
        names = pg.evaluate("[...document.querySelectorAll('#elpop input[data-name]')].map(i => [i.dataset.name, i.value])")
        assert names == [["src", "../assets/fluent/microscope.svg"], ["alt", ""]], ("허용 목록만(src·alt) — on*·style 없음", names)
        pg.fill('#elpop input[data-name="alt"]', "현미경 그림")
        shot(pg, "step4-attr-fields.png")
        pg.press('#elpop input[data-name="alt"]', "Enter")
        _wait_file(pg, out, lambda s: '<img src="../assets/fluent/microscope.svg" alt="현미경 그림">' in s, "alt 가 바로 파일에")
        _modal_frame_until(pg, "() => document.querySelector('aside .art-card > img').alt === '현미경 그림'")
        _wait_path(pg, lambda p: "img" in p, "쓴 뒤 크게 보기에서도 같은 그림이 다시 골라진다")
        shot(pg, "step4-attr-after.png")
        _logged(pg)
        pg.keyboard.press("Control+z")
        _wait_file(pg, out, lambda s: s == before, "되돌리기 = 되살리기")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal")
def test_insert_part_below_writes_a_neutral_skeleton_and_undo_restores(ctx, out):
    before = _job(out)
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal_helper(pg)
        mf.click(".lead")
        pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
        pg.click('#elbar [data-act="insert"]')
        pg.wait_for_selector("#elpop .ep-part", timeout=5000)
        titles = pg.evaluate("[...document.querySelectorAll('#elpop .ep-part')].map(b => b.textContent)")
        assert "버튼" in titles and "입력 칸" in titles, titles
        shot(pg, "step5-parts-picker.png")
        pg.locator("#elpop .ep-part", has_text="입력 칸").first.click()
        sk = '<div class="field"><label class="label">텍스트</label><input class="input"></div>'
        _wait_file(pg, out, lambda s: sk in s, "고른 부품 뼈대가 바로 파일에")
        s = _job(out)
        assert s.index("골라 드릴게요.</p>") < s.index(sk) < s.index('<div class="tile-grid"'), "고른 요소 바로 아래"
        assert "김지은" not in s and "s-name" not in s, "견본 보기 글·id 는 화면에 들어가지 않는다"
        _modal_frame_until(pg, "() => !!document.querySelector('.wizard-content > .field')")
        _wait_path(pg, lambda p: "field" in p or "div:nth-of-type" in p, "막대는 넣은 부품으로")
        shot(pg, "step5-inserted.png")
        _logged(pg)
        pg.keyboard.press("Control+z")
        _wait_file(pg, out, lambda s: s == before, "되돌리기 = 되살리기")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal")
def test_replace_with_part_swaps_the_element(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal_helper(pg)
        mf.click(TILE2)
        pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
        pg.click('#elbar [data-act="swap"]')
        pg.wait_for_selector("#elpop .ep-part", timeout=5000)
        pg.locator("#elpop .ep-part", has_text="버튼").first.click()
        _wait_file(pg, out, lambda s: "대학원생·연구원<span" not in s and '<button class="btn primary">텍스트</button>' in s, "타일이 버튼 뼈대로 바뀐다")
        _modal_frame_until(pg, "() => !!document.querySelector('.tile-grid > .btn')")
        shot(pg, "step5-replaced.png")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("modal", "notes")
def test_without_helper_parts_become_an_ai_request_memo(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    mf = _modal_helper(pg)
    mf.click(".lead")
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    pg.click('#elbar [data-act="insert"]')
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.input_value("#pnote") == "이 자리에 부품 넣기 — 데이터는 화면에 맞게", pg.input_value("#pnote")
    shot(pg, "step5-fallback-memo.png")
    assert not errors, errors
    pg.close()
