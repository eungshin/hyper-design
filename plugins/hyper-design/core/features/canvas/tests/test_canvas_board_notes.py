"""판 메모(R23) — 빈 판에 글을 두고 쓰기·새로고침·옮기기·지우기·되돌리기(도우미로 연 페이지 = 상태 파일 .hd-canvas.json 'board-notes').

규칙은 modules/board-notes.js(unit: test_canvas_unit_board_notes.py), 화면은 modules/view-board-notes.js."""
import json, os, time

import pytest

from test_canvas_v2 import browser, ctx, reload  # noqa: F401
from test_canvas_board_text import out, _helper  # noqa: F401
from test_canvas_edit import fit_view
from test_canvas_baseline import cover_center

SHOT = os.environ.get("HD_R23_SHOT")                 # 눈으로 볼 때만: 스크린숏 파일

EMPTY = """(minRight) => { const r = document.getElementById('screens').getBoundingClientRect();
  const ok = ['screens', 'stage', 'intro', 'rows', 'foot'];
  for (let y = r.top + 80; y < r.bottom - 120; y += 23) for (let x = r.left + 120; x < r.right - minRight; x += 29) {
    const e = document.elementFromPoint(x, y);
    if (e && (ok.includes(e.id) || e.classList.contains('flow') || e.classList.contains('cards'))) return {x, y}; }
  return null; }"""
BOX = """() => { const n = document.querySelector('.bnote'); if (!n) return null; const b = n.getBoundingClientRect(), s = document.getElementById('stage');
  const r = s.getBoundingClientRect(), z = parseFloat(s.dataset.zoom);
  return {x: b.left, y: b.top, w: b.width, h: b.height, z, sx: (b.left - r.left) / z, sy: (b.top - r.top) / z}; }"""


def _state(o):
    f = o / ".hd-canvas.json"
    return (json.loads(f.read_text(encoding="utf-8")).get("state") or {}) if f.exists() else {}


def _until(fn, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(0.1)
    return fn()


def _rows(pg):
    return pg.locator("#hlist li").count()


@pytest.mark.area("tools", "notes")
def test_t_click_empty_board_writes_multiline_note_that_survives_reload_moves_and_undoes_delete(ctx, out):
    srv, pg, errors = _helper(ctx, out)
    try:
        p = pg.evaluate(EMPTY, 420)
        assert p, "빈 판 자리를 못 찾음"
        pg.keyboard.press("t")
        pg.mouse.click(p["x"], p["y"])
        pg.wait_for_selector(".bnote textarea", timeout=3000)
        assert pg.evaluate("document.activeElement.closest('.bnote') !== null"), "누른 자리에서 바로 쓴다"
        pg.keyboard.type("첫 줄")
        pg.keyboard.press("Enter")                    # Enter = 줄바꿈(끝내지 않음)
        pg.keyboard.type("둘째 줄")
        assert pg.locator(".bnote textarea").count() == 1
        pg.keyboard.press("Escape")
        assert pg.locator(".bnote textarea").count() == 0 and pg.text_content(".bnote") == "첫 줄\n둘째 줄"
        assert pg.get_attribute('#tools [data-tool="move"]', "aria-pressed") == "true", "하나 쓰면 V 로 돌아온다"
        assert pg.locator(".bnote.sel").count() == 1, "끝낸 메모는 골라진 채"
        notes = _until(lambda: _state(out).get("board-notes"))
        assert notes and [n["text"] for n in notes.values()] == ["첫 줄\n둘째 줄"], "상태 파일에 쓴다"
        before = pg.evaluate(BOX)
        assert before["z"] >= 0.6 - 1e-3, "작게 보고 있었으면 쓰는 동안 읽히는 배율로"
        assert before["x"] <= p["x"] <= before["x"] + before["w"] and before["y"] <= p["y"] <= before["y"] + before["h"], "누른 자리에 놓인다"

        reload(pg)
        pg.evaluate("window.__hdStay = 1")
        fit_view(pg)
        after = pg.evaluate(BOX)
        assert after and pg.text_content(".bnote") == "첫 줄\n둘째 줄", "새로고침해도 있다"
        assert abs(after["sx"] - before["sx"]) < 2 and abs(after["sy"] - before["sy"]) < 2, "같은 자리(판 좌표)"

        pg.keyboard.press("v")
        rows = _rows(pg)
        sx, sy = after["x"] + after["w"] / 2, after["y"] + after["h"] / 2
        pg.mouse.move(sx, sy); pg.mouse.down(); pg.mouse.move(sx + 60, sy + 30, steps=4); pg.mouse.move(sx + 120, sy + 60, steps=4); pg.mouse.up()
        moved = pg.evaluate(BOX)
        assert abs(moved["x"] - after["x"] - 120) < 2 and abs(moved["y"] - after["y"] - 60) < 2, "끌면 옮겨진다"
        assert abs(moved["sx"] - after["sx"] - 120 / after["z"]) < 3, "판이 아니라 메모가 움직였다"
        assert _rows(pg) == rows + 1, "옮기기 = 기록 한 줄"
        x0 = list(notes.values())[0]["x"]
        assert _until(lambda: abs(list((_state(out).get("board-notes") or {"": {"x": -1e9}}).values())[0]["x"] - (x0 + 120 / after["z"])) < 3), "옮긴 자리를 쓴다"

        pg.keyboard.press("Delete")
        assert pg.locator(".bnote").count() == 0
        assert _until(lambda: _state(out).get("board-notes") == {}), "지우면 파일에서도 빠진다"
        pg.keyboard.press("Control+z")
        assert pg.locator(".bnote").count() == 1 and pg.text_content(".bnote") == "첫 줄\n둘째 줄", "되돌리면 돌아온다"
        back = pg.evaluate(BOX)
        assert abs(back["x"] - moved["x"]) < 1.5, "옮긴 자리 그대로"
        assert _until(lambda: len(_state(out).get("board-notes") or {}) == 1)
        assert pg.evaluate("window.__hdStay") == 1
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "notes")
def test_empty_note_leaves_nothing_and_no_undo_row_and_cards_keep_their_clicks(ctx, out):
    srv, pg, errors = _helper(ctx, out)
    try:
        pg.keyboard.press("v")
        rows = _rows(pg)
        p = pg.evaluate(EMPTY, 420)
        pg.mouse.dblclick(p["x"], p["y"])               # V 두 번 누르기 = 만들기
        pg.wait_for_selector(".bnote textarea", timeout=3000)
        pg.keyboard.press("Escape")
        assert pg.locator(".bnote").count() == 0, "빈 메모는 남지 않는다"
        pg.wait_for_timeout(500)
        assert _rows(pg) == rows, "기록 줄도 없다"
        assert not _state(out).get("board-notes"), "파일에도 없다"

        pg.keyboard.press("t")                          # 카드 위 T = 카드 안 글자 고치기 그대로(메모를 만들지 않음)
        fit_view(pg)
        cov = cover_center(pg)
        pg.mouse.click(cov["x"], cov["y"])
        pg.wait_for_timeout(300)
        assert pg.locator(".bnote").count() == 0, "카드 위에서는 메모를 만들지 않는다"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.skipif(not SHOT, reason="HD_R23_SHOT 이 있을 때만(눈 판정용 스크린숏)")
@pytest.mark.area("tools", "notes")
def test_shot_notes_beside_cards(ctx, out):
    srv, pg, errors = _helper(ctx, out)
    try:
        pg.set_viewport_size({"width": 1440, "height": 1000})
        pg.keyboard.press("0"); pg.wait_for_timeout(300)
        c = pg.evaluate("(() => { const b = document.querySelector('#rows .card').getBoundingClientRect(); return {x: b.left, y: b.top}; })()")
        pg.mouse.move(700, 500)
        pg.mouse.wheel(c["x"] - 520, c["y"] - 260)      # 첫 줄 카드를 판 가운데 쪽으로
        pg.wait_for_timeout(200)
        pg.keyboard.down("Control"); pg.mouse.wheel(0, -700); pg.keyboard.up("Control")
        pg.wait_for_timeout(400)
        texts = ["온보딩 첫 화면 — 건너뛰기 버튼이\n너무 작다는 의견", "다음 회의: 알림 권한 묻는 시점", "아이디어: 진행 막대를 위로"]
        far = """() => { const r = document.getElementById('screens').getBoundingClientRect(), ok = ['screens', 'stage', 'rows'];
          const taken = [...document.querySelectorAll('.bnote')].map(n => n.getBoundingClientRect());
          for (let y = r.top + 120; y < r.bottom - 220; y += 23) for (let x = r.left + 120; x < r.right - 260; x += 29) {
            const free = (a, b) => { const e = document.elementFromPoint(a, b); return e && (ok.includes(e.id) || e.classList.contains('flow') || e.classList.contains('cards')); };
            if (!free(x, y) || !free(x + 200, y) || !free(x + 200, y + 70) || !free(x, y + 70)) continue;
            if (taken.every(t => x > t.right + 40 || x + 220 < t.left || y > t.bottom + 40 || y + 120 < t.top)) return {x, y}; }
          return null; }"""
        for t in texts:
            p = pg.evaluate(far)
            if not p:
                break
            pg.keyboard.press("t")
            pg.mouse.click(p["x"], p["y"])
            pg.wait_for_selector(".bnote textarea", timeout=3000)
            lines = t.split("\n")
            pg.keyboard.type(lines[0])
            for line in lines[1:]:
                pg.keyboard.press("Enter"); pg.keyboard.type(line)
            pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        os.makedirs(os.path.dirname(SHOT), exist_ok=True)
        pg.screenshot(path=SHOT)
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
