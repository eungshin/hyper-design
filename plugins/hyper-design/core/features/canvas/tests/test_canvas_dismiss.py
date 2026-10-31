"""떠 있는 것 닫기 규칙 하나(U1, 10-31) — Esc·바깥 누르기·같은 것 다시 누르기 = 맨 위 한 층만, 쓰던 글은 잃지 않는다 (Playwright).

먼저 고정(지금 잘 닫히는 것 — 바꾸지 않는다): 위 막대 메뉴(창·배율)·도크 더보기·오른쪽 클릭 메뉴는 Esc·바깥 누르기로 닫힌다.
고친 것: F2 크게 보기 화면 틀 안을 누른 뒤 Esc·화면 안 누르기 · F3 메모 창 바깥 누르기·다른 메뉴 · F5 같은 핀 다시 누르기 ·
F16 덮개 한 번 = 맨 위 한 층 · F4 탭을 바꾸면 크게 보기 닫힘 · F1b 메모를 지운 뒤 묶음 창이 연 자리 그대로.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import fit_view

PAY = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><header><h1 class="title" style="margin:16px">결제</h1></header>
<main style="padding:16px"><p class="lead">카드를 고르세요</p><div style="height:120px"></div><button class="pay" style="display:block;width:240px;height:48px;font-size:16px">지금 결제하기</button>
<a href="done.html" class="go">다음</a></main></body></html>"""
DONE = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><h1 style="margin:16px">완료</h1><p>결제가 끝났어요</p></body></html>"""

# 보내기 전 메모 둘(핀 1 = 버튼, 핀 2 = 안내 글)
SEED_JS = """() => { const q = (p, t) => ({path: p, text: t, quote: {exact: t, prefix: '', suffix: ''}});
    const t = q('button.pay', '지금 결제하기'), l = q('p.lead', '카드를 고르세요');
    const a = [{id: 'm1', no: 1, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: null, note: '버튼을 더 크게', intent: 'change', sent: false, replies: []},
               {id: 'm2', no: 2, screen: 'pay', targets: [l], path: l.path, text: l.text, rect: null, note: '안내 글 색', intent: 'change', sent: false, replies: []}];
    const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
    localStorage.setItem('hd-notes:' + h, JSON.stringify(a)); localStorage.setItem('hd-note-seq:' + h, JSON.stringify({pay: 2})); localStorage.removeItem('hd-show-sent:' + h); }"""


@pytest.fixture(scope="module")
def dpage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-dismiss-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "pay.html").write_text(PAY, encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다"},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝"}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((out / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    yield pg
    assert not errors, errors
    pg.close()
    shutil.rmtree(tmp, ignore_errors=True)


PIN = '.card[data-id="pay"] .npin'
BADGE = '.card[data-id="pay"] .nbadge'
MENUS = "() => [...document.querySelectorAll('[role=menu]')].filter(m => !m.closest('[hidden]') && m.getClientRects().length && getComputedStyle(m).visibility !== 'hidden').length"


def seeded(pg):
    """메모 둘을 심고 다시 읽은 뒤 pay 카드를 핀이 보이는 크기로."""
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
    pg.evaluate(SEED_JS)
    reload(pg)
    fit_view(pg)
    ph = zoom_to(pg, "pay", 520)
    pg.mouse.move(ph["x"] + ph["width"] / 2, ph["y"] + 8)       # 카드에 올리면 핀이 보인다
    pg.wait_for_selector(PIN + '[data-no="2"]', state="visible", timeout=5000)
    return ph


def empty_board(pg):
    """판 빈 자리(카드·막대·떠 있는 창 밖) — test_canvas_baseline.empty_point 와 같은 찾기에 묶음·메모 창을 더 뺀다."""
    p = pg.evaluate("""() => { const r = document.getElementById('screens').getBoundingClientRect();
        for (let y = r.top + 30; y < r.bottom - 30; y += 17) for (let x = r.left + 30; x < r.right - 30; x += 19) {
          const e = document.elementFromPoint(x, y);
          if (e && e.closest('#screens') && !e.closest('.card, #legend, .alabel, button, #hdchat, #ptabs, #tools, #thread, #pop, .mschips')) return [x, y]; }
        return null; }""")
    assert p, "빈 자리를 못 찾음"
    return p


def open_modal(pg):
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
    fit_view(pg)
    pg.keyboard.press("h")
    pg.dblclick('.card[data-id="pay"] .cover')
    pg.wait_for_selector("#modal:not([hidden])", timeout=5000)
    for _ in range(100):
        mf = pg.query_selector("#mframe").content_frame()
        if mf and mf.query_selector("button.pay"):
            return mf
        pg.wait_for_timeout(100)
    raise AssertionError("크게 보기 화면이 안 실림")


def overlay_point(pg):
    """크게 보기 덮개(화면 창 밖) 한 점."""
    w = pg.locator("#mwin").bounding_box()
    return (w["x"] + w["width"] + 40, w["y"] + 60)


@pytest.mark.area("modal", "notes", "tools")
def test_existing_menus_still_close_on_esc_and_outside(dpage):
    """고정(R57-4): 지금 잘 닫히는 메뉴 — 창 메뉴·배율 메뉴·도크 더보기·판 오른쪽 클릭 메뉴는 Esc 와 바깥(판 빈 자리) 누르기로 닫힌다."""
    pg = dpage
    pg.keyboard.press("Escape")
    fit_view(pg)
    x, y = empty_board(pg)
    openers = [("창 메뉴", lambda: pg.click("#wbtn")), ("배율 메뉴", lambda: pg.click("#zoom")),
               ("도크 더보기", lambda: pg.click(".dk-more")), ("오른쪽 클릭", lambda: pg.mouse.click(x, y, button="right"))]
    for name, op in openers:
        for how, shut in (("Esc", lambda: pg.keyboard.press("Escape")), ("바깥", lambda: pg.mouse.click(x, y))):
            assert pg.evaluate(MENUS) == 0, (name, how, "앞 메뉴가 남음")
            op()
            pg.wait_for_timeout(300)
            assert pg.evaluate(MENUS) > 0, (name, how, "메뉴가 안 열림")
            shut()
            pg.wait_for_function(f"({MENUS})() === 0", timeout=3000)


@pytest.mark.area("notes")
def test_same_pin_again_closes_thread_and_outside_closes(dpage):
    """F5: 핀을 누르면 묶음 창, 같은 핀을 다시 누르면 닫힘(배지와 같은 규칙) · 다른 핀이면 그 메모로 그대로 · 바깥 누르기 = 닫기."""
    pg = dpage
    seeded(pg)
    pg.click(PIN + '[data-no="1"]')
    pg.wait_for_selector("#thread:not([hidden])")
    pg.click(PIN + '[data-no="2"]')
    pg.wait_for_timeout(250)
    assert pg.is_visible("#thread") and pg.get_attribute("#thread li.focus", "data-no") == "2", "다른 핀 = 그 메모로"
    pg.click(PIN + '[data-no="2"]')
    pg.wait_for_selector("#thread", state="hidden", timeout=2000)
    pg.click(PIN + '[data-no="1"]')
    pg.wait_for_selector("#thread:not([hidden])")
    pg.mouse.click(*empty_board(pg))
    pg.wait_for_selector("#thread", state="hidden", timeout=2000)


@pytest.mark.area("notes")
def test_thread_stays_where_it_opened_after_delete(dpage):
    """F1b: 핀 옆에 연 묶음 창에서 다른 메모를 지워도 창은 연 자리 그대로(카드 배지 아래로 뛰지 않는다)."""
    pg = dpage
    seeded(pg)
    pg.click(PIN + '[data-no="1"]')
    pg.wait_for_selector("#thread:not([hidden])")
    pg.wait_for_timeout(200)
    a = pg.locator("#thread").bounding_box()
    pg.click('#thread li[data-id="m2"] button[data-act="del"]')
    pg.wait_for_function("!document.querySelector('#thread li[data-id=\"m2\"]')", timeout=3000)
    pg.wait_for_timeout(400)
    b = pg.locator("#thread").bounding_box()
    assert abs(a["x"] - b["x"]) < 3 and abs(a["y"] - b["y"]) < 3, ("연 자리 그대로", a, b)
    pg.keyboard.press("Escape")


@pytest.mark.area("notes", "tools")
def test_memo_pop_outside_and_other_menu_follow_the_rule(dpage):
    """F3: 메모 창(고치기) — 쓴 글 없음 + 바깥 누르기 = 닫힘 · 다른 메뉴를 열어도 닫힘(겹치지 않음).
    쓴 글이 있으면 바깥 누르기·다른 메뉴에도 남는다 · Esc 는 닫되 글을 지켜 같은 메모를 다시 열면 되살린다."""
    pg = dpage
    seeded(pg)

    def open_edit():
        pg.click(BADGE)
        pg.wait_for_selector("#thread:not([hidden])")
        pg.click('#thread li[data-id="m1"] button[data-act="edit"]')
        pg.wait_for_selector("#pop:not([hidden])")

    open_edit()
    pg.mouse.click(*empty_board(pg))
    pg.wait_for_selector("#pop", state="hidden", timeout=2000)
    open_edit()
    pg.click("#zoom")
    pg.wait_for_selector("#pop", state="hidden", timeout=2000)
    pg.keyboard.press("Escape")
    open_edit()
    pg.fill("#pnote", "버튼을 더 크게 — 빨강")
    pg.mouse.click(*empty_board(pg))
    pg.click("#zoom")
    pg.wait_for_timeout(250)
    assert pg.is_visible("#pop") and pg.input_value("#pnote") == "버튼을 더 크게 — 빨강", "쓴 글이 있으면 남는다"
    pg.keyboard.press("Escape")                         # 배율 메뉴(맨 위)
    pg.wait_for_function(f"({MENUS})() === 0", timeout=2000)
    assert pg.is_visible("#pop"), "Esc 한 번 = 맨 위 한 층(메뉴)만"
    pg.focus("#pnote")
    pg.keyboard.press("Escape")
    pg.wait_for_selector("#pop", state="hidden", timeout=2000)
    open_edit()
    assert pg.input_value("#pnote") == "버튼을 더 크게 — 빨강", "Esc 로 닫은 쓰던 글은 다시 열면 되살아난다"
    pg.click("#pcancel")


@pytest.mark.area("modal")
def test_large_view_esc_after_clicking_inside_screen(dpage):
    """F2: 크게 보기 화면 틀 안을 누른 뒤(포커스가 틀 안) Esc = 크게 보기 닫기."""
    pg = dpage
    mf = open_modal(pg)
    mf.click("h1.title")
    pg.keyboard.press("Escape")
    pg.wait_for_selector("#modal", state="hidden", timeout=2000)


@pytest.mark.area("modal", "notes")
def test_large_view_thread_closes_by_press_inside_screen_and_esc_is_top_only(dpage):
    """F2: 크게 보기 위 묶음 창 — 화면 틀 안 누르기 = 묶음 창만 닫힘 · 틀 안에 포커스가 있어도 Esc = 맨 위(묶음)만, 크게 보기는 남는다."""
    pg = dpage
    seeded(pg)
    mf = open_modal(pg)
    pg.wait_for_selector('#mpins .pin[data-no="1"]', state="visible", timeout=5000)
    pg.click('#mpins .pin[data-no="1"]')
    pg.wait_for_selector("#thread:not([hidden])")
    mf.click("h1.title")
    pg.wait_for_selector("#thread", state="hidden", timeout=2000)
    assert pg.is_visible("#modal")
    pg.click('#mpins .pin[data-no="1"]')
    pg.wait_for_selector("#thread:not([hidden])")
    mf.evaluate("document.body.tabIndex = -1, document.body.focus()")
    mf.press("body", "Escape")
    pg.wait_for_selector("#thread", state="hidden", timeout=2000)
    assert pg.is_visible("#modal"), "Esc 한 번 = 맨 위 한 층"
    mf.press("body", "Escape")
    pg.wait_for_selector("#modal", state="hidden", timeout=2000)


@pytest.mark.area("modal", "notes")
def test_large_view_overlay_closes_top_layer_only(dpage):
    """F16: 크게 보기 위 메모 창 — 덮개 한 번 = 메모 창만(쓴 글이 있으면 그것도 남음) · 다음 덮개 = 크게 보기."""
    pg = dpage
    seeded(pg)
    open_modal(pg)
    pg.wait_for_selector('#mpins .pin[data-no="1"]', state="visible", timeout=5000)
    pg.click('#mpins .pin[data-no="1"]')
    pg.click('#thread li[data-id="m1"] button[data-act="edit"]')
    pg.wait_for_selector("#pop:not([hidden])")
    pg.fill("#pnote", "크게 보기에서 쓰던 글")
    pg.mouse.click(*overlay_point(pg))
    pg.wait_for_timeout(300)
    assert pg.is_visible("#modal") and pg.is_visible("#pop") and pg.input_value("#pnote") == "크게 보기에서 쓰던 글", "쓴 글이 있는 창은 남는다"
    pg.fill("#pnote", "")
    pg.mouse.click(*overlay_point(pg))
    pg.wait_for_selector("#pop", state="hidden", timeout=2000)
    assert pg.is_visible("#modal"), "덮개 한 번 = 맨 위 한 층(메모 창)만"
    pg.mouse.click(*overlay_point(pg))
    pg.wait_for_selector("#modal", state="hidden", timeout=2000)


@pytest.mark.area("modal")
def test_switching_tab_closes_large_view(dpage):
    """F4: 크게 보기가 열린 채 다른 탭(Foundation)으로 가면 크게 보기는 닫힌다 · 돌아와도 다시 뜨지 않는다."""
    pg = dpage
    open_modal(pg)
    pg.click('.tab[data-tab="foundation"]')
    pg.wait_for_selector("#modal", state="hidden", timeout=2000)
    pg.click('.tab[data-tab="screens"]')
    pg.wait_for_timeout(200)
    assert pg.is_hidden("#modal")
