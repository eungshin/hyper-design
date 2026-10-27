"""R27 막대 조각(시각 위계) — 카드 선택 막대가 판 칸 안에 머문다(F07) 등, 화면에 보이는 것만 본다 (Playwright).

픽스처는 test_canvas_artboard 의 화면 셋(home → pay → done, file://)을 그대로 쓴다.
"""
import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_artboard import abpage, fresh  # noqa: F401


def _box(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); if (!e || e.hidden || !e.offsetWidth) return null;"
                       " const r = e.getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom}; }", sel)


def _pick(pg, sid):
    pg.evaluate("""(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))""", sid)
    pg.wait_for_timeout(250)


def _pan_until(pg, sid, cond):
    pg.mouse.move(*pg.evaluate("(() => { const r = document.getElementById('screens').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()"))
    for _ in range(400):
        if pg.evaluate(cond, sid):
            break
        pg.mouse.wheel(25, 0)
        pg.wait_for_timeout(16)
    pg.wait_for_timeout(200)


@pytest.mark.area("tools")
def test_card_bar_stays_on_the_board_when_the_card_slides_under_the_side_panel(abpage):
    """F07: 고른 카드를 판 왼쪽 밖(옆 패널 쪽)으로 밀면 막대는 판 칸 안에 남고, 카드가 판에서 다 사라지면 막대도 사라진다."""
    pg = abpage
    fresh(pg)
    _pick(pg, "home")
    assert _box(pg, "#selbar"), "고르면 막대가 뜬다"
    half = """(id) => { const c = document.querySelector('.card[data-id="' + id + '"] .phone').getBoundingClientRect(), s = document.getElementById('screens').getBoundingClientRect();
                 return c.left + c.width / 2 < s.left && c.right > s.left + 10; }"""
    _pan_until(pg, "home", half)
    bar, scr, card = _box(pg, "#selbar"), _box(pg, "#screens"), _box(pg, '.card[data-id="home"] .phone')
    assert card["l"] < scr["l"] < card["r"], ("카드 반 넘게 판 왼쪽 밖", card, scr)
    assert bar and bar["l"] >= scr["l"] and bar["r"] <= scr["r"], ("막대는 판 칸 안 — 옆 패널을 덮지 않음", bar, scr)
    gone = """(id) => document.querySelector('.card[data-id="' + id + '"] .phone').getBoundingClientRect().right < document.getElementById('screens').getBoundingClientRect().left - 20"""
    _pan_until(pg, "home", gone)
    assert _box(pg, "#selbar") is None, "카드가 판 칸 밖이면 막대도 숨김"
    pg.keyboard.press("Escape")


@pytest.mark.area("tools", "links")
def test_picking_one_card_keeps_the_rest_of_the_flow_readable(abpage):
    """F18: 카드 하나를 고르면 이어진 카드는 또렷, 나머지는 살짝만 흐리다(예전 .22 → 읽히는 .85 쯤) — 흐름을 계속 읽을 수 있다."""
    pg = abpage
    fresh(pg)
    _pick(pg, "home")
    pg.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
    pg.wait_for_timeout(500)                          # 흐려지는 움직임이 끝난 뒤
    op = pg.evaluate("(ids) => ids.map(id => +getComputedStyle(document.querySelector('.card[data-id=\"' + id + '\"]')).opacity)", ["home", "pay", "done"])
    assert op[0] > 0.95 and op[1] > 0.95, ("고른 카드·이어진 카드는 또렷", op)
    assert 0.75 <= op[2] < 0.95, ("이어지지 않은 카드도 읽힌다 — 살짝만 흐림", op)
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
