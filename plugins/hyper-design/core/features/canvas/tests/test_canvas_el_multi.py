"""여러 요소 고르기(R19) — 브라우저. 선택(V)으로 카드 → 요소 A → Shift+요소 B = 두 테두리 · 대화창 요소 칩 둘 → 보내면 요소마다 메모.
Shift+A 다시 = A 만 빠짐. 막대는 주인(마지막 것)만. 크게 보기도 Shift = 더하기·빼기. 규칙은 test_canvas_unit_el_pick.py(unit).
"""
import os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx, zoom_to  # noqa: F401
from test_canvas_chat import _serve, queued

pytestmark = pytest.mark.area("tools", "chat")
SHOT = Path(os.environ.get("HD_SHOTS_R19", Path(tempfile.gettempdir()) / "claude" / "r19-impl"))


@pytest.fixture()
def live(ctx):
    pg, errors, done = _serve(ctx)
    yield pg
    done()
    assert not errors, errors


def _frame(pg, sid):
    for _ in range(100):
        f = pg.query_selector(f'.card[data-id="{sid}"] .phone iframe')
        fr = f and f.content_frame()
        if fr and fr.url.split("?")[0].endswith(f"/{sid}.html"):
            return fr
        pg.wait_for_timeout(100)
    raise AssertionError("카드 화면이 실리지 않았어요")


def _xy(pg, ph, fr, sel):
    r = fr.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }", sel)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    return ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc


def _keys(pg, q):
    return pg.evaluate("(q) => [...document.querySelectorAll(q)].map(n => n.dataset.key.split(':').slice(1).join(':'))", q)


def test_shift_click_adds_and_removes_elements_and_chat_chips_follow(live):
    pg = live
    pg.set_viewport_size({"width": 1440, "height": 1000})
    ph = zoom_to(pg, "pay", 420)
    fr = _frame(pg, "pay")
    fr.wait_for_selector("button.pay", state="attached", timeout=5000)
    a, b = _xy(pg, ph, fr, "button.pay"), _xy(pg, ph, fr, "p.lead")
    pg.keyboard.press("v")
    pg.mouse.click(*a)                                    # 카드 고르기
    pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(*a)                                    # 요소 A
    pg.wait_for_selector(".elbox.sel", timeout=8000)
    pg.keyboard.down("Shift"); pg.mouse.click(*b); pg.keyboard.up("Shift")   # + 요소 B
    pg.wait_for_function("document.querySelectorAll('.elbox.sel').length === 2", timeout=8000)
    sel = _keys(pg, ".elbox.sel")
    assert any("button.pay" in k for k in sel) and any("p.lead" in k for k in sel), sel
    assert "p.lead" in _keys(pg, ".elbox.sel.pri")[0], "주인 = 마지막에 고른 B"
    assert pg.locator(".sock.selsock").count() == 1 and pg.is_visible("#elbar"), "소켓·막대는 주인 하나"
    assert pg.evaluate("document.querySelector('.card[data-id=\"pay\"]').classList.contains('picked')"), "Shift 가 카드 고르기를 풀지 않는다"
    pg.wait_for_function("document.querySelectorAll('#hdchat .ch-chip.el').length === 2", timeout=3000)
    SHOT.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOT / "r19-multi.png"))
    keys = pg.evaluate("[...document.querySelectorAll('#hdchat .ch-chip.el')].map(c => c.dataset.key)")
    assert any("button.pay" in k for k in keys) and any("p.lead" in k for k in keys), keys

    pg.keyboard.down("Shift"); pg.mouse.click(*a); pg.keyboard.up("Shift")   # A 다시 = 빼기
    pg.wait_for_function("document.querySelectorAll('.elbox.sel').length === 1", timeout=8000)
    assert "p.lead" in _keys(pg, ".elbox.sel")[0]
    pg.wait_for_function("document.querySelectorAll('#hdchat .ch-chip.el').length === 1", timeout=3000)

    pg.keyboard.down("Shift"); pg.mouse.click(*a); pg.keyboard.up("Shift")   # 다시 더해 둘을 보낸다
    pg.wait_for_function("document.querySelectorAll('#hdchat .ch-chip.el').length === 2", timeout=8000)
    pg.click("#hdchat textarea")
    pg.keyboard.type("둘 다 더 크게")
    pg.keyboard.press("Enter")
    text = queued(pg)
    assert "button.pay" in text and "p.lead" in text and "no=1,2" in text, text   # 요소 메모 둘(no 1·2)(같은 글·같은 화면 = 요청문 한 항목 + '다른 곳:' 줄, edits.request 그대로)

    pg.keyboard.press("Escape")                           # 입력창에서 나가기
    pg.keyboard.press("Escape")                           # 고른 요소 모두 풀기
    pg.wait_for_function("document.querySelectorAll('.elbox.sel').length === 0", timeout=3000)


def test_modal_select_shift_click_adds_a_second_outline(live):
    pg = live
    pg.keyboard.press("0")
    pg.dblclick('.card[data-id="pay"] .cover')
    pg.wait_for_selector("#modal:not([hidden])", timeout=5000)
    fr = None
    for _ in range(100):
        fr = pg.frame_locator("#mframe")
        if pg.query_selector("#mframe").content_frame() and pg.query_selector("#mframe").content_frame().query_selector("button.pay"):
            break
        pg.wait_for_timeout(100)
    pg.keyboard.press("v")
    pg.wait_for_function("document.querySelector('#tools [data-tool=\"move\"]').getAttribute('aria-pressed') === 'true'", timeout=3000)
    mf = pg.query_selector("#mframe").content_frame()
    mf.click("button.pay")
    pg.wait_for_function("document.querySelectorAll('#mbox .msel-box').length === 1", timeout=5000)
    mf.click("p.lead", modifiers=["Shift"])
    pg.wait_for_function("document.querySelectorAll('#mbox .msel-box').length === 2", timeout=5000)
    assert "p.lead" in _keys(pg, "#mbox .msel-box.pri")[0], "주인 = 마지막 것"
    mf.click("button.pay", modifiers=["Shift"])
    pg.wait_for_function("document.querySelectorAll('#mbox .msel-box').length === 1", timeout=5000)
    mf.click("button.pay")
    pg.wait_for_function("document.querySelectorAll('#mbox .msel-box').length === 1 && document.querySelector('#mbox .msel-box').dataset.key.includes('button.pay')", timeout=5000)
