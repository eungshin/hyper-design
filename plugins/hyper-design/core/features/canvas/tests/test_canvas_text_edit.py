"""글자 고치기 관례(R51·R52, Figma·Photoshop) — 브라우저(도우미 있음).

1. Esc = 저장하고 끝 · 그 요소는 골라진 채 · 고친 게 없으면 쓰기 요청 없음 · 되돌리기는 Ctrl+Z
2. 선택(V) 두 번 누르기 = 그 글자 고치기(판·크게 보기) · 판의 글자 아닌 곳 두 번 누르기 = 크게 보기(그대로)
3. 고치는 중 다른 글자 누르기 = 지금 것 저장 + 그 글자 고치기 · 글자 아닌 곳 = 저장하고 끝
4. Ctrl+Enter = 저장하고 요소 선택으로
키·누르기 규칙은 test_canvas_unit_text_edit.py(unit). 스크린샷 = HD_SHOTS_TEXT_EDIT(기본 %TEMP%/claude/text-edit).
"""
import json, os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx, swap_done, swap_mark, zoom_to  # noqa: F401
from test_canvas_text_remove import _open, _frame, _serve, out  # noqa: F401
from test_canvas_blocks import _pick_element, _wait_file
from test_canvas_figma_keys import _is

SHOTS = Path(os.environ.get("HD_SHOTS_TEXT_EDIT", Path(tempfile.gettempdir()) / "claude" / "text-edit"))
H1, LEAD = "h1.title", "p.lead"
OLD = "하는 일이 무엇인가요?"
EDITING = "(s) => { const e = document.querySelector(s); return !!e && e.isContentEditable && document.activeElement === e; }"
NOT_EDITING = "(s) => !document.querySelector(s).isContentEditable"
# 타일 1·2 사이 틈 = 글자 없는 곳(leaf 답 path:null — .tile-grid 는 글 가진 자손이 여럿)
GAP = """() => { const a = document.querySelector('.tile-grid > button:nth-of-type(1)').getBoundingClientRect(),
                       b = document.querySelector('.tile-grid > button:nth-of-type(2)').getBoundingClientRect();
                 return {x: (a.right + b.left) / 2, y: a.top + a.height / 2}; }"""


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def _points(pg, sid="job"):
    """sid 카드를 키워 제목·안내 글·글자 없는 틈의 판 좌표(한 번 키운 카메라 그대로)."""
    ph = zoom_to(pg, sid, 420)
    fr = _frame(pg, sid)
    fr.wait_for_selector(LEAD, state="attached", timeout=5000)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    mid = "(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }"
    at = lambda r: (ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc)
    gap = fr.evaluate(GAP)
    assert fr.evaluate("([x, y]) => document.elementFromPoint(x, y).className", [gap["x"], gap["y"]]) == "tile-grid", "틈 = 타일 묶음 자체"
    return {"h1": at(fr.evaluate(mid, H1)), "lead": at(fr.evaluate(mid, LEAD)), "gap": at(gap)}


def _applies(pg):
    calls = []
    pg.on("request", lambda r: calls.append(json.loads(r.post_data or "{}")) if r.url.endswith("/api/apply") and r.method == "POST" else None)
    return calls


def _modal(pg):
    pg.keyboard.press("0")
    pg.evaluate("document.querySelector('.card[data-id=\"job\"] .pres').click()")
    pg.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    mf = next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")
    mf.wait_for_selector(H1, timeout=5000)
    pg.wait_for_timeout(300)
    return mf


@pytest.mark.area("helper", "tools")
def test_esc_saves_ends_and_keeps_the_element_selected(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        calls = _applies(pg)
        p = _points(pg)
        _pick_element(pg, p["h1"])
        pg.keyboard.press("Enter")                       # 글자 요소 = 그 자리 고치기
        _frame(pg).wait_for_function(EDITING, arg=H1, timeout=3000)
        pg.keyboard.press("Escape")                      # 고친 게 없음 = 끝만(쓰기 요청 없음)
        _frame(pg).wait_for_function(NOT_EDITING, arg=H1, timeout=3000)
        _is(pg, H1)
        pg.wait_for_timeout(400)
        assert calls == [], ("고친 게 없으면 저장 요청을 보내지 않는다", calls)
        pg.keyboard.press("Enter")
        fr = _frame(pg)
        fr.wait_for_function(EDITING, arg=H1, timeout=3000)
        pg.keyboard.type("Esc 로 저장")
        pg.keyboard.press("Escape")                      # Esc = 저장하고 끝(관례 — 예전엔 취소)
        fr.wait_for_function(NOT_EDITING, arg=H1, timeout=3000)
        assert fr.text_content(H1).strip() == "Esc 로 저장", "화면은 바로 새 글"
        _is(pg, H1)                                      # 끝난 뒤 그 요소가 골라진 채(요소 테두리·막대)
        shot(pg, "esc-selected.png")
        _wait_file(pg, out, lambda s: '<h1 class="title">Esc 로 저장</h1>' in s, "Esc 가 파일에 쓰지 않았다")
        pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hs').textContent === '파일에 씀'", timeout=20000)
        pg.keyboard.press("Control+z")                   # 되돌리기 = 이미 있는 Ctrl+Z
        _wait_file(pg, out, lambda s: '<h1 class="title">%s</h1>' % OLD in s, "Ctrl+Z 가 되돌리지 않았다")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools")
def test_ctrl_enter_saves_and_returns_to_element_selection(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        p = _points(pg)
        _pick_element(pg, p["h1"])
        pg.keyboard.press("Enter")
        fr = _frame(pg)
        fr.wait_for_function(EDITING, arg=H1, timeout=3000)
        pg.keyboard.type("컨트롤 엔터")
        pg.keyboard.press("Control+Enter")
        fr.wait_for_function(NOT_EDITING, arg=H1, timeout=3000)
        assert fr.evaluate("(s) => document.querySelector(s).innerHTML", H1) == "컨트롤 엔터", "줄바꿈이 아니라 저장"
        _is(pg, H1)
        _wait_file(pg, out, lambda s: '<h1 class="title">컨트롤 엔터</h1>' in s, "Ctrl+Enter 가 파일에 쓰지 않았다")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools", "modal")
def test_v_double_click_on_text_edits_on_the_board_and_in_the_large_view(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        p = _points(pg)
        pg.keyboard.press("v")
        pg.mouse.dblclick(*p["h1"])                      # 카드를 안 고른 채여도 글자 = 그 자리 고치기
        _frame(pg).wait_for_function(EDITING, arg=H1, timeout=5000)
        assert pg.evaluate("document.getElementById('modal').hidden"), "글자 위 두 번 누르기는 크게 보기를 열지 않는다"
        shot(pg, "v-dblclick-board.png")
        pg.keyboard.press("Escape")
        _frame(pg).wait_for_function(NOT_EDITING, arg=H1, timeout=3000)
        pg.keyboard.press("Escape"); pg.keyboard.press("Escape")   # 요소 → 카드 고르기 풀기
        pg.wait_for_timeout(300)
        pg.mouse.dblclick(*p["gap"])                     # 글자 아닌 곳 = 지금처럼 크게 보기
        pg.wait_for_function("!document.getElementById('modal').hidden", timeout=5000)
        pg.keyboard.press("Escape")
        pg.wait_for_function("document.getElementById('modal').hidden", timeout=3000)
        mf = _modal(pg)
        pg.click('#tools [data-tool="move"]')
        mf.dblclick(LEAD)                                # 크게 보기 V 두 번 누르기(예전엔 막힘)
        mf.wait_for_function(EDITING, arg=LEAD, timeout=3000)
        shot(pg, "v-dblclick-modal.png")
        pg.keyboard.press("Escape")
        mf.wait_for_function(NOT_EDITING, arg=LEAD, timeout=3000)
        pg.wait_for_function("document.querySelector('#elbar').dataset.where === 'modal' && !document.querySelector('#elbar').hidden", timeout=3000)
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools")
def test_clicking_another_text_while_editing_switches_to_it_on_the_board(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        calls = _applies(pg)
        p = _points(pg)
        pg.keyboard.press("v")
        pg.mouse.dblclick(*p["h1"])
        fr = _frame(pg)
        fr.wait_for_function(EDITING, arg=H1, timeout=5000)
        pg.keyboard.type("바꾼 제목")
        pg.mouse.click(*p["lead"])                       # 다른 글자 = 지금 것 저장 + 그 글자로
        _frame(pg).wait_for_function(EDITING, arg=LEAD, timeout=5000)
        assert not _frame(pg).evaluate("(s) => document.querySelector(s).isContentEditable", H1)
        _wait_file(pg, out, lambda s: '<h1 class="title">바꾼 제목</h1>' in s, "전환 때 앞 글자가 저장되지 않았다")
        n = len(calls)
        pg.mouse.click(*p["gap"])                        # 글자 아닌 곳 = 저장하고 끝(고친 게 없으면 쓰기 없음)
        _frame(pg).wait_for_function("() => !document.querySelector('[contenteditable=\"true\"]')", timeout=5000)
        pg.wait_for_timeout(400)
        assert len(calls) == n, ("안내 글은 고치지 않았다 — 쓰기 없음", calls[n:])
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools", "modal")
def test_clicking_another_text_while_editing_switches_to_it_in_the_large_view(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal(pg)
        pg.click('#tools [data-tool="move"]')
        mf.dblclick(H1)
        mf.wait_for_function(EDITING, arg=H1, timeout=3000)
        pg.keyboard.type("크게 본 제목")
        mf.click(LEAD)
        mf.wait_for_function(EDITING, arg=LEAD, timeout=3000)
        assert not mf.evaluate("(s) => document.querySelector(s).isContentEditable", H1)
        _wait_file(pg, out, lambda s: '<h1 class="title">크게 본 제목</h1>' in s, "전환 때 앞 글자가 저장되지 않았다")
        g = mf.evaluate(GAP)
        f = pg.evaluate("(() => { const f = document.getElementById('mframe'), r = f.getBoundingClientRect(), sc = r.width / f.offsetWidth; return {x: r.left + f.clientLeft * sc, y: r.top + f.clientTop * sc, sc: sc}; })()")
        pg.mouse.click(f["x"] + g["x"] * f["sc"], f["y"] + g["y"] * f["sc"])   # 글자 아닌 곳 = 저장하고 끝
        mf.wait_for_function("() => !document.querySelector('[contenteditable=\"true\"]')", timeout=3000)
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
