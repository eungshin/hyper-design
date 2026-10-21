"""0단계 — 편집 기능을 붙이기 전에 지금 캔버스의 입력 규칙을 고정한다 (docs/eungshin/canvas-edit-plan-2026-10-19.md §1·§4).

이미 test_canvas_v2.py 가 덮는 것(Shift+클릭 연결 보기·순환, 색, A, 0, T, Ctrl+클릭, 메모·보내기)은 다시 쓰지 않는다.
여기서는 그 밖의 손 규칙: 휠 = 이동, Ctrl+휠 = 확대, 왼쪽 끌기 = 이동(카드 위에서 시작해도 크게 보기 안 열림),
오른쪽 버튼 = 메뉴 · 가운데 = 이동(4단계에서 좁힘), 클릭 = 크게 보기, Esc 순서, P 는 크게 보기 안에서만, 입력 중에는 단축키 무시.
"""
import pytest

from test_canvas_v2 import browser, ctx, out_dir, reload  # noqa: F401 — 같은 laundry-v1 고정본·브라우저를 쓴다


@pytest.fixture(scope="module")
def bpage(ctx, out_dir):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((out_dir / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    yield pg
    assert not errors, errors
    pg.close()


def cam(pg):
    return pg.evaluate("[document.getElementById('stage').style.transform, +document.getElementById('stage').dataset.zoom]")


def modal_open(pg):
    return pg.evaluate("!document.getElementById('modal').hidden")


def empty_point(pg):
    """판(#screens) 안에서 카드·범례·도구 막대가 아닌 빈 자리 하나."""
    p = pg.evaluate("""() => { const r = document.getElementById('screens').getBoundingClientRect();
        for (let y = r.top + 30; y < r.bottom - 30; y += 17) for (let x = r.left + 30; x < r.right - 30; x += 19) {
          const e = document.elementFromPoint(x, y);
          if (e && e.closest('#screens') && !e.closest('.card, #legend, .alabel, button, #khint')) return {x, y}; }
        return null; }""")
    assert p, "빈 자리를 못 찾음"
    return p


def cover_center(pg):
    """판 안에 가운데가 보이는 첫 카드 표지의 가운데."""
    p = pg.evaluate("""() => { const r = document.getElementById('screens').getBoundingClientRect();
        for (const c of document.querySelectorAll('#rows .card .cover')) { const b = c.getBoundingClientRect();
          const x = b.left + b.width / 2, y = b.top + Math.min(b.height / 2, 80);
          if (x > r.left + 10 && x < r.right - 10 && y > r.top + 10 && y < r.bottom - 10 && document.elementFromPoint(x, y) === c) return {x, y}; }
        return null; }""")
    assert p, "판 안에 보이는 카드가 없음"
    return p


def fit_view(pg):
    pg.click("#zoom"); pg.click("#fit")
    pg.wait_for_timeout(120)


def test_wheel_pans_ctrl_wheel_zooms(bpage):
    fit_view(bpage)
    p = empty_point(bpage)
    t0, z0 = cam(bpage)
    bpage.mouse.move(p["x"], p["y"])
    bpage.mouse.wheel(0, 120)
    bpage.wait_for_timeout(80)
    t1, z1 = cam(bpage)
    assert t1 != t0 and z1 == z0, "휠은 확대 없이 이동만"
    bpage.keyboard.down("Control"); bpage.mouse.wheel(0, -200); bpage.keyboard.up("Control")
    bpage.wait_for_timeout(80)
    assert cam(bpage)[1] > z1, "Ctrl+휠 위로 = 확대"


def test_left_drag_pans_even_from_a_card(bpage):
    fit_view(bpage)
    for start in (empty_point(bpage), cover_center(bpage)):
        t0, z0 = cam(bpage)
        bpage.mouse.move(start["x"], start["y"])
        bpage.mouse.down()
        bpage.mouse.move(start["x"] + 90, start["y"] + 40, steps=6)
        bpage.mouse.up()
        bpage.wait_for_timeout(120)
        t1, z1 = cam(bpage)
        assert t1 != t0 and z1 == z0, start
        assert not modal_open(bpage), "끌기 끝의 클릭은 크게 보기를 열지 않는다"


def test_right_button_menu_middle_pans(bpage):
    """4단계에서 좁힌 규칙: 오른쪽 = 메뉴(끌어도 판은 그대로), 가운데 = 화면 이동(카드 위에서도, 크게 보기 안 열림)."""
    fit_view(bpage)
    p = empty_point(bpage)
    t0 = cam(bpage)
    bpage.mouse.move(p["x"], p["y"])
    bpage.mouse.down(button="right")
    bpage.mouse.move(p["x"] + 120, p["y"] + 60, steps=6)
    bpage.mouse.up(button="right")
    bpage.wait_for_timeout(80)
    assert cam(bpage) == t0, "오른쪽 끌기는 판을 움직이지 않는다"
    bpage.keyboard.press("Escape")
    bpage.wait_for_timeout(80)
    assert bpage.evaluate("document.getElementById('cmenu').hidden")
    for start in (empty_point(bpage), cover_center(bpage)):
        t0 = cam(bpage)
        bpage.mouse.move(start["x"], start["y"])
        bpage.mouse.down(button="middle")
        bpage.mouse.move(start["x"] + 120, start["y"] + 60, steps=6)
        bpage.mouse.up(button="middle")
        bpage.wait_for_timeout(80)
        assert cam(bpage)[0] != t0[0] and cam(bpage)[1] == t0[1], ("가운데 끌기 = 이동", start)
        assert not modal_open(bpage)
    c = cover_center(bpage)                         # 가운데 끌기 뒤 첫 왼쪽 두 번 누르기는 먹히지 않는다
    bpage.mouse.dblclick(c["x"], c["y"])
    bpage.wait_for_function("!document.getElementById('modal').hidden")
    bpage.keyboard.press("Escape")
    bpage.wait_for_timeout(120)


def test_dblclick_opens_modal_and_esc_order(bpage):
    """재작업 S3: 마우스 한 번 = 크게 보기 아님(판 위에서 고른다), 두 번 = 크게 보기."""
    fit_view(bpage)
    c = cover_center(bpage)
    bpage.mouse.click(c["x"], c["y"])
    bpage.wait_for_timeout(300)
    assert not modal_open(bpage), "한 번 누르기는 크게 보기를 열지 않는다"
    bpage.mouse.dblclick(c["x"], c["y"])
    bpage.wait_for_function("!document.getElementById('modal').hidden")
    bpage.keyboard.press("Escape")
    bpage.wait_for_timeout(120)
    assert not modal_open(bpage), "Esc 한 번 = 크게 보기 닫기"
    bpage.mouse.click(c["x"], c["y"])
    bpage.wait_for_timeout(300)
    assert bpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "누르기 = 그 화면 연결 보기(E15)"
    assert not modal_open(bpage), "누르기는 크게 보기를 열지 않는다"
    bpage.keyboard.press("Escape")
    bpage.wait_for_timeout(150)
    assert not bpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "다음 Esc = 연결 보기 끝"


def test_p_picks_only_inside_modal(bpage):
    fit_view(bpage)
    bpage.keyboard.press("p")
    bpage.wait_for_timeout(80)
    assert not modal_open(bpage)
    assert bpage.get_attribute("#mpick", "aria-pressed") != "true", "판에서 P 는 크게 보기·주석 달기를 켜지 않는다(재작업 S4: 주석 도구)"
    bpage.keyboard.press("h")
    c = cover_center(bpage)
    bpage.mouse.dblclick(c["x"], c["y"])
    bpage.wait_for_function("!document.getElementById('modal').hidden")
    bpage.keyboard.press("p")
    bpage.wait_for_timeout(80)
    assert bpage.get_attribute("#mpick", "aria-pressed") == "true"
    bpage.keyboard.press("Escape")
    bpage.wait_for_timeout(120)
    if modal_open(bpage):
        bpage.keyboard.press("Escape")
        bpage.wait_for_timeout(120)
    assert not modal_open(bpage)


def test_typing_guard_blocks_shortcuts(bpage):
    fit_view(bpage)
    tool0 = bpage.evaluate("[...document.querySelectorAll('#tools [aria-pressed=\"true\"]')].map(b => b.dataset.tool)")
    bpage.evaluate("""() => { const i = document.createElement('input'); i.id = 'hd-test-input';
        document.body.appendChild(i); i.focus(); }""")
    for k in ("l", "0", "t", "p"):
        bpage.keyboard.press(k)
    bpage.wait_for_timeout(80)
    assert bpage.evaluate("[...document.querySelectorAll('#tools [aria-pressed=\"true\"]')].map(b => b.dataset.tool)") == tool0, "입력 중 L 은 도구를 바꾸지 않는다"
    assert not modal_open(bpage)
    bpage.evaluate("document.getElementById('hd-test-input').remove()")


def test_notes_roundtrip_same_key(bpage):
    """메모는 hd-notes:<hash(pathname)> 한 키에 저장되고, 새로고침 뒤 같은 키·같은 내용으로 다시 그려진다."""
    import re
    from test_canvas_v2 import open_screen
    sid = bpage.evaluate("document.querySelector('#rows .card').dataset.id")
    fr = open_screen(bpage, sid)
    bpage.click("#mpick")
    bpage.wait_for_timeout(150)
    fr.locator("h1, h2, button, a").filter(has_text=re.compile(r"\S")).first.click()
    bpage.wait_for_selector("#pop:not([hidden])")
    bpage.fill("#pnote", "기준선 메모")
    bpage.click("#padd")
    bpage.keyboard.press("Escape")
    bpage.keyboard.press("Escape")
    keys = bpage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-notes'))")
    assert len(keys) == 1 and re.match(r"^hd-notes:\S+$", keys[0]), keys
    before = bpage.evaluate("(k) => localStorage.getItem(k)", keys[0])
    assert "기준선 메모" in before
    reload(bpage)
    assert bpage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-notes'))") == keys
    assert bpage.evaluate("(k) => localStorage.getItem(k)", keys[0]) == before
    assert "기준선 메모" in bpage.text_content("#nlist")
    assert bpage.locator(f'.card[data-id="{sid}"] .nbadge').text_content() == "1"
    bpage.evaluate("(k) => localStorage.removeItem(k)", keys[0])
    reload(bpage)
