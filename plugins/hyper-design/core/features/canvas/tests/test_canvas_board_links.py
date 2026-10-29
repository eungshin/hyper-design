"""판 메모 선(R47) — 메모 변의 점을 끌어 메모·화면 카드·줄(폴더) 제목에 잇기 · 새로고침 · 고르기·끊기·되돌리기 · 이름 · 메모를 지우면 선도 거둠(되돌리면 함께).

도우미로 연 페이지 = 상태 파일 .hd-canvas.json 'board-links'. 규칙은 modules/board-links.js(unit: test_canvas_unit_board_links.py), 화면은 modules/view-board-links.js."""
import json, os

import pytest

from test_canvas_v2 import browser, ctx, reload  # noqa: F401
from test_canvas_board_text import out, _helper  # noqa: F401
from test_canvas_edit import fit_view
from test_canvas_board_notes import _state, _until, _rows, _seed
from test_canvas_chat_log import served  # noqa: F401

SHOT = os.environ.get("HD_R47_SHOT")                 # 눈으로 볼 때만: 스크린숏 폴더

CENTER = """(sel) => { const e = document.querySelector(sel); if (!e) return null; const b = e.getBoundingClientRect();
  return {x: b.left + b.width / 2, y: b.top + b.height / 2, w: b.width, h: b.height}; }"""
LINE_MID = """(id) => { const p = document.querySelector('#blk-h g.blk-e[data-id="' + id + '"] path.blk-hit'); if (!p) return null;
  const pt = p.getPointAtLength(p.getTotalLength() / 2), m = p.getScreenCTM(); return {x: pt.x * m.a + m.e, y: pt.y * m.d + m.f}; }"""
CARD_PT = """() => { for (const c of document.querySelectorAll('#rows .card')) { const p = c.querySelector('.phone'); if (!p) continue;
  const b = p.getBoundingClientRect(), x = b.left + 40, y = b.top + Math.min(b.height / 2, 200);
  const e = document.elementFromPoint(x, y); if (e && e.closest('.card') === c) return {x, y, id: c.dataset.id}; } return null; }"""
CACHE = "() => Object.keys(JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.indexOf('hd-board-links:') === 0)) || '{}'))"
DRAWN = "() => [...document.querySelectorAll('#blk-l path.blk:not(.blk-tmp)')].map(p => p.dataset.id)"


def _links(o):
    return _state(o).get("board-links") or {}


def _close(pg, note="na", z=0.45):
    """작게 보는 중에는 점이 숨는다 — 메모와 첫 카드 사이를 가운데 두고 그 배율까지 키운다."""
    for _ in range(40):
        if float(pg.evaluate("document.getElementById('stage').dataset.zoom")) >= z:
            break
        a = pg.evaluate(CENTER, f'.bnote[data-id="{note}"]'); c = pg.evaluate(CENTER, "#rows .card")
        pg.mouse.move((a["x"] + c["x"]) / 2, a["y"])
        pg.keyboard.down("Control"); pg.mouse.wheel(0, -200); pg.keyboard.up("Control")
        pg.wait_for_timeout(60)
    for _ in range(20):                                # 왼쪽 패널 밑에서 꺼낸다(판 밀기)
        a = pg.evaluate(CENTER, f'.bnote[data-id="{note}"]')
        if a["x"] > 520 and a["y"] > 220:
            break
        pg.mouse.move(720, 500); pg.mouse.wheel(-150 if a["x"] <= 520 else 0, -150 if a["y"] <= 220 else 0)
        pg.wait_for_timeout(60)
    pg.wait_for_timeout(150)


def _drag_dot(pg, note, side, to):
    """메모에 올려 점을 보이게 한 뒤 그 변의 점을 to(화면 좌표)로 끈다."""
    c = pg.evaluate(CENTER, f'.bnote[data-id="{note}"]')
    pg.mouse.move(c["x"] - 6, c["y"] - 3); pg.mouse.move(c["x"], c["y"])   # 마우스가 이미 그 자리면 움직임이 없다(확대 뒤)
    pg.wait_for_timeout(50)
    dot = pg.locator(f'#blk-dots .blk-dot[data-side="{side}"]')
    assert dot.is_visible(), "올린 메모에 변의 점"
    d = dot.bounding_box()
    sx, sy = d["x"] + d["width"] / 2, d["y"] + d["height"] / 2
    pg.mouse.move(sx, sy); pg.mouse.down()
    pg.mouse.move((sx + to["x"]) / 2, (sy + to["y"]) / 2, steps=4); pg.mouse.move(to["x"], to["y"], steps=4)
    pg.mouse.up()
    pg.wait_for_timeout(120)


@pytest.mark.area("tools", "notes")
def test_drag_a_note_dot_to_note_screen_and_folder_then_reload_unlink_undo_and_name(ctx, out):
    _seed(out, {"na": {"x": -420, "y": 1750, "w": 240, "text": "가입 화면 유의: 버튼은 하나만", "at": 1},
                "nb": {"x": -420, "y": 2150, "w": 240, "text": "이유: 사용자 조사", "at": 2}})
    srv, pg, errors = _helper(ctx, out)
    try:
        pg.keyboard.press("v")
        assert pg.locator("#blk-l path.blk:not(.blk-tmp)").count() == 0, "선이 없으면 그리지 않는다"
        c = pg.evaluate(CENTER, '.bnote[data-id="na"]'); pg.mouse.move(c["x"], c["y"]); pg.wait_for_timeout(50)
        assert not pg.locator("#blk-dots .blk-dot").first.is_visible(), "작게 보는 중에는 점이 메모를 덮지 않게 숨는다"
        _close(pg)
        rows = _rows(pg)

        _drag_dot(pg, "na", "bottom", pg.evaluate(CENTER, '.bnote[data-id="nb"]'))
        links = _until(lambda: _links(out))
        assert [(v["from"], v["to"]) for v in links.values()] == [("note:na", "note:nb")], "메모 → 메모 선을 쓴다"
        nn = list(links)[0]
        assert links[nn]["fromSide"] == "bottom" and links[nn]["toSide"] == "top" and "T" in links[nn]["at"], links
        assert pg.evaluate(DRAWN) == [nn], "선이 그려진다"
        assert _rows(pg) == rows + 1, "잇기 = 기록 한 줄"

        cov = pg.evaluate(CARD_PT)
        assert cov, "보이는 카드가 없음"
        _drag_dot(pg, "na", "right", cov)
        sid = cov["id"]
        g = pg.evaluate(CENTER, "#rows > .flow > .glabel")
        gname = pg.text_content("#rows > .flow > .glabel")
        _drag_dot(pg, "nb", "right", g)
        ends = lambda: sorted(v["to"] for v in _links(out).values())
        assert _until(lambda: len(ends()) == 3), _links(out)
        assert ends() == sorted(["note:nb", "screen:" + sid, "folder:" + gname]), "화면 카드·줄 제목에도 잇는다"
        _drag_dot(pg, "na", "bottom", pg.evaluate(CENTER, '.bnote[data-id="nb"]'))
        assert len(_links(out)) == 3, "같은 쌍은 다시 잇지 않는다"

        reload(pg)
        pg.evaluate("window.__hdStay = 1")
        fit_view(pg)
        _close(pg)
        assert sorted(pg.evaluate(DRAWN)) == sorted(_links(out)), "새로고침해도 선이 그려진다"

        pg.keyboard.press("v")
        m = pg.evaluate(LINE_MID, nn)
        rows = _rows(pg)
        pg.mouse.click(m["x"], m["y"])
        assert pg.locator(f'#blk-l path.blk.sel[data-id="{nn}"]').count() == 1, "선 누르기 = 고르기"
        pg.keyboard.press("Delete")
        assert _until(lambda: nn not in _links(out)), "Delete = 끊기"
        assert nn not in pg.evaluate(DRAWN) and pg.locator(".bnote").count() == 2, "메모는 그대로"
        assert _rows(pg) == rows + 1
        pg.keyboard.press("Control+z")
        assert _until(lambda: nn in _links(out)), "되돌리면 선이 돌아온다"
        pg.wait_for_timeout(100)
        assert nn in pg.evaluate(DRAWN)

        m = pg.evaluate(LINE_MID, nn)
        pg.mouse.dblclick(m["x"], m["y"])
        pg.wait_for_selector("#blk-dots input.blk-in", timeout=2000)
        pg.keyboard.type("근거")
        pg.keyboard.press("Enter")
        assert _until(lambda: _links(out).get(nn, {}).get("label") == "근거"), "두 번 누르기 = 선 이름"
        pg.wait_for_timeout(100)
        assert pg.text_content(f'#blk-h g.blk-e[data-id="{nn}"] text.blk-lab') == "근거", "이름이 선 위에"

        if SHOT:
            pg.set_viewport_size({"width": 1440, "height": 1000})
            os.makedirs(SHOT, exist_ok=True)
            pg.keyboard.press("Escape")
            c = pg.evaluate(CENTER, '.bnote[data-id="na"]'); pg.mouse.move(c["x"] - 6, c["y"]); pg.mouse.move(c["x"], c["y"])
            pg.wait_for_timeout(200)
            pg.screenshot(path=os.path.join(SHOT, "links-hover-dots.png"))
            m = pg.evaluate(LINE_MID, nn); pg.mouse.click(m["x"], m["y"]); pg.mouse.move(m["x"] + 200, m["y"] + 300)
            pg.wait_for_timeout(200)
            pg.screenshot(path=os.path.join(SHOT, "links-selected.png"))
        cov = pg.evaluate(CARD_PT)
        pg.mouse.click(cov["x"], cov["y"])
        pg.wait_for_timeout(150)
        assert pg.locator(f'#rows .card.picked[data-id="{sid}"]').count() == 1, "선이 닿은 카드도 누르면 그대로 골라진다"
        assert pg.locator("#blk-l path.blk.sel").count() == 0, "다른 곳 누르기 = 선 고르기 풀림"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "notes")
def test_deleting_a_note_takes_its_links_and_undo_brings_both_back(ctx, out):
    _seed(out, {"na": {"x": -900, "y": 300, "w": 240, "text": "가", "at": 1}, "nb": {"x": -900, "y": 700, "w": 240, "text": "나", "at": 2},
                "nc": {"x": -500, "y": 700, "w": 240, "text": "다", "at": 3}})
    f = out / ".hd-canvas.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["state"]["board-links"] = {"l1": {"from": "note:na", "to": "note:nb", "at": "2026-10-29T00:00:00Z"},
                                 "l2": {"from": "note:nc", "to": "note:na", "at": "2026-10-29T00:00:00Z"},
                                 "l3": {"from": "note:nb", "to": "screen:없는화면", "at": "2026-10-29T00:00:00Z"}}
    f.write_text(json.dumps(d), encoding="utf-8")
    srv, pg, errors = _helper(ctx, out)
    try:
        pg.keyboard.press("v")
        assert sorted(pg.evaluate(DRAWN)) == ["l1", "l2"], "없는 끝(l3)은 그리지 않는다"
        c = pg.evaluate(CENTER, '.bnote[data-id="na"]')
        pg.mouse.click(c["x"], c["y"])
        rows = _rows(pg)
        pg.keyboard.press("Delete")
        assert pg.locator('.bnote[data-id="na"]').count() == 0
        assert sorted(pg.evaluate(CACHE)) == ["l3"], "지운 메모에 닿은 선을 바로 거둔다(없는 끝 선은 남김)"
        assert _until(lambda: sorted(_links(out)) == ["l3"], 25), "파일에도(같은 PUT — 이 고정본 도우미는 PUT 이 10초쯤 걸릴 때가 있다)"
        assert pg.evaluate(DRAWN) == [] or _until(lambda: pg.evaluate(DRAWN) == [])
        assert _rows(pg) == rows + 1, "메모 지우기 한 줄(선 거두기는 줄을 더하지 않는다)"
        pg.keyboard.press("Control+z")
        assert pg.locator('.bnote[data-id="na"]').count() == 1
        assert _until(lambda: sorted(pg.evaluate(CACHE)) == ["l1", "l2", "l3"]), "되돌리면 선도 돌아온다"
        assert _until(lambda: sorted(pg.evaluate(DRAWN)) == ["l1", "l2"])
        pg.keyboard.press("Control+Shift+z")
        assert _until(lambda: sorted(pg.evaluate(CACHE)) == ["l3"]), "다시 하기 = 다시 거둔다"
        assert _until(lambda: sorted(_links(out)) == ["l3"], 25)
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "notes")
def test_renaming_a_row_folder_keeps_its_links_and_undo_follows_back_and_reader_tab_cannot_unlink(ctx, out):
    sj = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    group = sj["screens"][0]["group"]
    _seed(out, {"na": {"x": -420, "y": 1750, "w": 240, "text": "가", "at": 1}})
    f = out / ".hd-canvas.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["state"]["board-links"] = {"l1": {"from": "note:na", "to": "folder:" + group, "at": "2026-10-29T00:00:00Z"}}
    f.write_text(json.dumps(d), encoding="utf-8")
    srv, pg, errors = _helper(ctx, out)
    try:
        assert pg.evaluate(DRAWN) == ["l1"], "줄 제목 끝 선이 그려진다"
        pg.evaluate("([a, b]) => document.dispatchEvent(new CustomEvent('hd-row-rename', {detail: {from: a, to: b}}))", [group, group + " 새 이름"])
        assert _until(lambda: _links(out).get("l1", {}).get("to") == "folder:" + group + " 새 이름", 25), "줄 이름을 바꾸면 선 끝이 따라간다"
        assert _until(lambda: pg.evaluate(DRAWN) == ["l1"]), "새 이름 줄 제목에 그대로 그려진다"
        pg.wait_for_timeout(300)
        pg.keyboard.press("Control+z")
        assert _until(lambda: _links(out).get("l1", {}).get("to") == "folder:" + group, 25), "줄 이름 되돌리기 = 선 끝도 옛 이름으로"

        pg.evaluate("document.documentElement.dataset.hdTab = 'reader'")
        _close(pg)
        m = pg.evaluate(LINE_MID, "l1")
        pg.mouse.click(m["x"], m["y"])
        pg.keyboard.press("Delete")
        pg.wait_for_timeout(200)
        assert "l1" in _links(out), "읽기만인 탭은 끊지 않는다"
        c = pg.evaluate(CENTER, '.bnote[data-id="na"]'); pg.mouse.move(c["x"] - 6, c["y"]); pg.mouse.move(c["x"], c["y"])
        assert not pg.locator("#blk-dots .blk-dot").first.is_visible(), "읽기만인 탭에는 잇는 점이 없다"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


PAY_PT = """(id) => { const c = document.querySelector('#rows .card[data-id="' + id + '"]'), p = c && c.querySelector('.phone'); if (!p) return null;
  const b = p.getBoundingClientRect(), x = b.left + 40, y = b.top + Math.min(b.height / 2, 200), e = document.elementFromPoint(x, y);
  return e && e.closest('.card') === c ? {x, y} : null; }"""


@pytest.mark.area("chat", "notes", "tools")
def test_linking_a_note_to_a_screen_shows_the_card_badge_at_once_and_send_carries_the_card_block(served, ctx):
    """통합(R47 A+B): 판에서 끌어 이은 선 = 정보 카드의 진실 원천(BL.map) — 레이어 배지가 바로 '카드 1', 보낸 요청문에 그 화면 카드 한 번."""
    from test_canvas_chat_log import call, open_page
    from test_canvas_chat_memo import memo
    out, srv = served
    rev = call(srv, "GET", "/api/state")[1].get("rev", 0)
    seed = [memo("m1", "pay", 1, "결제 버튼을 더 크게"), memo("m2", "done", 1, "완료 문구를 짧게")]
    board = {"a": {"x": -420, "y": 0, "w": 240, "text": "결제 버튼은 화면에 하나만\n\n이 문단은 빠진다", "at": 1}}
    assert call(srv, "PUT", "/api/state", {"rev": rev, "state": {"notes": seed, "board-notes": board}})[0] == 200
    pg, errors = open_page(ctx, srv)
    try:
        pg.set_viewport_size({"width": 1440, "height": 1000})
        pg.keyboard.press("v")
        assert pg.locator("[data-ly='pay'] .ly-card").count() == 0, "선이 없으면 배지 없음"
        _close(pg, "a")
        to = pg.evaluate(PAY_PT, "pay")
        assert to, "pay 카드가 보이지 않음"
        _drag_dot(pg, "a", "right", to)
        assert _until(lambda: [v["to"] for v in (_state(out).get("board-links") or {}).values()] == ["screen:pay"]), _state(out).get("board-links")
        pg.wait_for_function("document.querySelector('[data-ly=\"pay\"] .ly-card')", timeout=5000)
        assert pg.inner_text("[data-ly='pay'] .ly-card") == "카드 1", "잇자마자 레이어 배지(새로고침 없이)"
        assert pg.locator("[data-ly='done'] .ly-card").count() == 0
        pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
        pg.keyboard.press("Control+z")                  # 선 잇기 되돌리기 = 선만 바뀜(메모는 그대로)
        assert _until(lambda: not _state(out).get("board-links")), "되돌리면 선이 빠진다"
        pg.wait_for_function("!document.querySelector('[data-ly=\"pay\"] .ly-card')", timeout=5000)   # 선만 바뀌어도 배지가 따라온다
        pg.keyboard.press("Control+Shift+z")
        pg.wait_for_function("document.querySelector('[data-ly=\"pay\"] .ly-card')", timeout=5000)
        assert pg.inner_text("[data-ly='pay'] .ly-card") == "카드 1"

        ta = "#hdchat textarea"
        pg.click(ta); pg.keyboard.type("/me")
        pg.wait_for_selector("#hdchat .ch-cmds li[data-cmd='memo'][aria-selected='true']", timeout=5000)
        pg.keyboard.press("Enter")
        pg.wait_for_selector("#hdchat .ch-chip.memos", timeout=5000)
        pg.click(ta); pg.keyboard.type("같이 반영해 줘"); pg.keyboard.press("Enter")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        req = pg.evaluate("window.__hdLastSend")
        assert req.count("유의(정보 카드):") == 1, req
        lines = req.split("\n")
        i = lines.index("   유의(정보 카드):")
        assert " screen=pay " in lines[i - 1], "pay 항목 머리 바로 아래"
        assert lines[i + 1] == "   - 결제 버튼은 화면에 하나만" and "이 문단은 빠진다" not in req, req
    finally:
        pg.close()
    assert not errors, errors
