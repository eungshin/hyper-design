"""카메라 — 첫 화면 · 사용자 이동 · 내용 높이 변화(U2 F1a, contract/camera.md).

고정(바뀌면 안 되는 것): 전체 보기(배율 칩 → 전체 보기)는 그대로 · 사용자가 옮긴 판을 내용 변화가 되돌리지 않는다.
고침: 메모를 더하거나 지워 줄 높이가 바뀌어도 눈앞 카드가 제자리(1px 안) · 위쪽 내용(소개 글·글꼴)이 늦게 자리 잡아도 첫 화면 줄이 잘리지 않는다.
글꼴이 늦게 오는 일은 테스트가 바깥 글꼴을 막으므로(conftest) 소개 글 높이·접힌 설명 글자를 직접 줄여 흉내 낸다(late_fonts).
"""
import pytest

from test_canvas_v2 import browser, out_dir  # noqa: F401 — 같은 laundry-v1 고정본·브라우저를 쓴다

pytestmark = pytest.mark.area("input", "notes")


@pytest.fixture
def pg(browser, out_dir):
    c = browser.new_context(viewport={"width": 1440, "height": 1000})   # 새 저장소(메모 없음)에서 연다
    p = c.new_page()
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto((out_dir / "index.html").resolve().as_uri())
    p.wait_for_function("window.__hdReady !== undefined")
    p.wait_for_timeout(300)
    yield p
    c.close()
    assert not errors, errors


CARD = """() => { const p = document.getElementById('screens').getBoundingClientRect(),
    f = document.querySelector('#rows .flow').getBoundingClientRect(), c = document.querySelector('#rows .flow .card').getBoundingClientRect();
    return {rowTop: f.top - p.top, x: c.left, y: c.top}; }"""


def cam(p):
    return p.evaluate("document.getElementById('stage').style.transform")


def frames(p, n=3):
    p.evaluate("(n) => new Promise(r => { const f = () => (--n <= 0 ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); })", n)


def late_fonts(p, by=158):
    """글꼴이 늦게 온 것처럼 — 첫 화면 줄 위 소개 글이 줄고, 접힌 카드 설명(줄 사이 여백을 재는 것)도 작아진다.
    접힌 설명은 판 배치를 밀지 않으므로 줄 사이 여백은 다음 다시 재기(메모 더하기·지우기 등) 때 한꺼번에 바뀐다 — 실제 점검(10-31)에서 본 그대로."""
    p.evaluate("""(by) => { const i = document.getElementById('intro'); i.style.overflow = 'hidden'; i.style.height = (i.offsetHeight - by) + 'px';
        const s = document.createElement('style'); s.textContent = '#rows .card > .cbody, #rows .card > .cbody * {font-size: 6px !important; line-height: 1 !important}';
        document.head.appendChild(s); }""", by)
    frames(p)


def add_memo(p, text, fy):
    b = p.locator("#rows .flow .card .phone iframe").first.bounding_box()
    p.keyboard.press("p"); p.wait_for_timeout(150)
    p.mouse.click(b["x"] + b["width"] * 0.39, b["y"] + b["height"] * fy)
    p.wait_for_selector("#pop:not([hidden])")
    p.fill("#pnote", text)
    p.click("#padd")
    p.wait_for_timeout(400)
    p.keyboard.press("v"); p.wait_for_timeout(150)


def close_enough(a, b):
    return abs(a["x"] - b["x"]) <= 1 and abs(a["y"] - b["y"]) <= 1


def test_fit_all_from_zoom_menu_still_shows_every_row(pg):
    """고정: 배율 칩 → 전체 보기는 첫 줄과 끝 줄을 다 판 안에 넣는다 — 뒤의 내용 높이 변화(아래쪽)도 그 카메라를 바꾸지 않는다."""
    pg.click("#zoom"); pg.click("#fit"); frames(pg)
    r = pg.evaluate("""() => { const p = document.getElementById('screens').getBoundingClientRect(), f = [...document.querySelectorAll('#rows .flow')];
        const a = f[0].getBoundingClientRect(), b = f[f.length - 1].getBoundingClientRect();
        return {top: a.top - p.top, bottom: p.bottom - b.bottom}; }""")
    assert r["top"] >= 0 and r["bottom"] >= 0, ("전체 보기 = 모든 줄이 판 안", r)
    t = cam(pg)
    pg.evaluate("() => { const f = [...document.querySelectorAll('#rows .flow')]; f[f.length - 1].style.paddingBottom = '300px'; }")
    frames(pg)
    assert cam(pg) == t, "아래쪽 내용이 커져도 전체 보기 카메라는 그대로"


def test_user_pan_is_never_overridden_by_content_change(pg):
    """고정: 사용자가 판을 옮긴 뒤 눈앞 아래쪽 내용이 바뀌어도 카메라는 사용자가 둔 자리 그대로(첫 카메라로 되돌아가지 않음)."""
    pg.mouse.move(800, 500); pg.mouse.wheel(0, 300); frames(pg)
    t = cam(pg)
    pg.evaluate("() => { const f = [...document.querySelectorAll('#rows .flow')]; f[f.length - 1].style.paddingBottom = '300px'; }")
    frames(pg)
    assert cam(pg) == t


def test_late_layout_above_first_row_keeps_first_view_unclipped(pg):
    """첫 화면 줄은 위쪽 내용이 늦게 자리 잡아도(글꼴) 판 위쪽 그 자리 — 카드 윗부분이 잘리지 않는다."""
    before = pg.evaluate(CARD)
    assert 0 <= before["rowTop"] <= 60, before
    late_fonts(pg)
    after = pg.evaluate(CARD)
    assert after["rowTop"] >= 0, ("첫 화면 줄 윗부분이 잘렸다", before, after)
    assert close_enough(before, after), ("첫 카드가 움직였다", before, after)


def test_adding_and_deleting_a_memo_keeps_the_card_in_place(pg):
    """메모를 더하고 지워도 눈앞 카드의 화면 위치가 1px 안에서 그대로(판이 점프하지 않음). 위쪽 소개 글이 늦게 자리 잡은 뒤에도."""
    late_fonts(pg)
    at = pg.evaluate(CARD)
    add_memo(pg, "카메라 메모 1", 0.30)
    add_memo(pg, "카메라 메모 2", 0.64)
    assert close_enough(at, pg.evaluate(CARD)), ("메모를 더하자 카드가 움직였다", at, pg.evaluate(CARD))
    pg.locator("#rows .flow .card").first.hover()
    pin = pg.locator("#rows .flow .card .npin").first
    pin.click(); pg.wait_for_selector("#thread:not([hidden])")
    pg.locator('#thread li button[data-act="del"]').first.click()
    pg.wait_for_timeout(500); frames(pg)
    assert pg.locator("#rows .flow .card .npin").count() == 1, "메모 하나가 지워졌다"
    assert close_enough(at, pg.evaluate(CARD)), ("메모를 지우자 카드가 움직였다", at, pg.evaluate(CARD))
