"""메모 주석·핀(task 11) — 판 카드 위 메모 핀 · 화면마다 바뀌지 않는 번호 · 다시 찾기(hd-locate) · 완료/다시 열기 (Playwright).

작은 화면 두 장을 임시 out 에 만들어 build_canvas.py 로 빌드한다(화면 파일을 고쳐 다시 찾기를 본다 — 고정본은 건드리지 않는다).
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import fit_view, notes_of, wait_notes, el_point, frame_of

PAY = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><header><h1 class="title" style="margin:16px">결제</h1></header>
<main style="padding:16px"><p class="lead">카드를 고르세요</p>{gap}<button class="pay" style="display:block;width:240px;height:48px;font-size:16px">{label}</button>
<a href="done.html" class="go">다음</a></main></body></html>"""
DONE = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><h1 style="margin:16px">완료</h1><p>결제가 끝났어요</p></body></html>"""


def write_pay(out, gap="", label="지금 결제하기"):
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", gap).replace("{label}", label), encoding="utf-8")


@pytest.fixture(scope="module")
def apage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-annot-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    write_pay(out)
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
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
    pg.out = out
    yield pg
    assert not errors, errors
    pg.close()
    shutil.rmtree(tmp, ignore_errors=True)


PIN = '.card[data-id="pay"] .npin'
BADGE = '.card[data-id="pay"] .nbadge'


def pins(pg):
    return pg.evaluate(f"""[...document.querySelectorAll('{PIN}')].map(p => ({{no: p.textContent, st: p.dataset.st, top: parseFloat(p.style.top),
        vis: getComputedStyle(p.parentNode).display !== 'none'}}))""")


def annotate_button(pg, note):
    ph = zoom_to(pg, "pay", 420)                     # 카드 화면 ≈ 실제의 52% — 배율만으로는 핀이 안 보이는 크기
    fr = frame_of(pg, "pay")
    pg.keyboard.press("p")
    x, y = el_point(pg, ph, fr, "button.pay")
    pg.mouse.click(x, y)
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.locator('.card[data-id="pay"] .npsel').count() == 1 and pg.is_visible('.card[data-id="pay"] .npsel'), "메모 창이 열린 동안 고른 요소 테두리"
    pg.fill("#pnote", note)
    pg.click("#padd")
    assert pg.locator(".npsel").count() == 0, "창을 닫으면 테두리도"
    pg.keyboard.press("h")
    return ph, (x, y)


def test_board_pin_numbers_thread_and_done(apage):
    """(a) 카드 요소에 메모 → 그 요소 자리에 핀 1(다시 불러오지 않고 바로) · 핀 누르기 = 그 메모로 열린 묶음(카드 고르기 아님).
    (b) 1 을 지우고 더하면 2. 완료 → 핀·배지 수가 빠지고 '완료' 묶음 · 다시 열기 → 핀이 돌아온다."""
    pg = apage
    fit_view(pg)
    ph, (x, y) = annotate_button(pg, "버튼을 더 크게")
    wait_notes(pg, 1)
    assert notes_of(pg)[0]["no"] == 1 and notes_of(pg)[0]["targets"][0]["quote"]["exact"] == "지금 결제하기", notes_of(pg)[0]
    pg.wait_for_selector(PIN + '[data-no="1"]', state="visible", timeout=4000)
    b = pg.locator(PIN).bounding_box()
    assert abs(b["x"] - (x - 120 * ph["width"] / 375)) < 30 and abs(b["y"] + b["height"] / 2 - y) < 40, (b, x, y)
    assert pg.locator(PIN).text_content() == "1" and pins(pg)[0]["st"] == "draft"
    pg.click(PIN)
    pg.wait_for_selector("#thread:not([hidden])")
    assert pg.locator("#rows .card.picked").count() == 0, "핀 누르기는 카드 고르기가 아니다"
    assert pg.get_attribute("#thread li.focus", "data-no") == "1"
    assert pg.text_content("#thread li.focus .thn") == "#1" and pg.text_content("#thread li.focus .ths") == "보내기 전"
    pg.hover("#thread li.focus .tht")
    assert pg.locator('.card[data-id="pay"] .npbox.hi').count() == 1, "묶음 줄에 올리면 그 요소 테두리"
    pg.click('#thread li.focus button[data-act="del"]')   # (b) 지우고 다시
    wait_notes(pg, 0)
    pg.keyboard.press("Escape")
    fit_view(pg)
    annotate_button(pg, "버튼 색")
    wait_notes(pg, 1)
    pg.wait_for_selector(PIN + '[data-no="2"]', state="visible", timeout=4000)
    assert notes_of(pg)[0]["no"] == 2 and [p["no"] for p in pins(pg)] == ["2"], "지운 번호는 다시 쓰지 않는다"
    assert pg.text_content(BADGE) == "1"
    pg.click(PIN)
    pg.wait_for_selector("#thread:not([hidden])")
    pg.click('#thread li.focus button[data-act="done"]')   # 완료(사람 답 '확인')
    pg.wait_for_function(f"!document.querySelector('{PIN}')")
    assert pg.locator(BADGE).count() == 0, "완료한 메모는 배지 수에서 빠진다"
    assert pg.locator("#thread details.thdone li").count() == 1 and "완료 1" in pg.text_content("#thread details.thdone summary")
    assert notes_of(pg)[0]["replies"][-1]["kind"] == "확인"
    pg.click("#thread details.thdone summary")
    pg.click('#thread details.thdone button[data-act="reopen"]')
    pg.wait_for_selector(PIN + '[data-no="2"]', state="attached", timeout=4000)
    n = notes_of(pg)[0]
    assert [r["kind"] for r in n["replies"]] == ["확인", "다시"] and n["sent"] is False and pg.text_content(BADGE) == "1"
    pg.keyboard.press("Control+z")                     # 다시 열기 = 되돌리기 한 단계
    pg.wait_for_function(f"!document.querySelector('{PIN}')")
    pg.keyboard.press("Control+y")
    pg.wait_for_selector(PIN, state="attached", timeout=4000)
    pg.keyboard.press("Escape")


def test_pins_reanchor_after_screen_changes(apage):
    """(c) 화면 파일이 바뀌어 요소가 내려가도(글 그대로) 다시 불러오면 핀이 따라간다 · 글이 바뀌면 핀은 없고 묶음 줄에 '대상이 바뀌었어요'."""
    pg = apage
    if not notes_of(pg):
        fit_view(pg)
        annotate_button(pg, "버튼")
    reload(pg)
    fit_view(pg)
    pg.wait_for_selector(PIN, state="attached", timeout=5000)
    top0 = pins(pg)[0]["top"]
    write_pay(pg.out, gap='<div style="height:200px"></div>')
    reload(pg)
    fit_view(pg)
    pg.wait_for_function(f"(() => {{ const p = document.querySelector('{PIN}'); return p && parseFloat(p.style.top) > {top0} + 150; }})()", timeout=5000)
    write_pay(pg.out, gap='<div style="height:200px"></div>', label="결제 완료")
    reload(pg)
    fit_view(pg)
    pg.wait_for_function("document.querySelector('.card[data-id=\"pay\"] .phone iframe').getAttribute('src')", timeout=5000)
    pg.click(BADGE)
    pg.wait_for_selector("#thread .thlost", timeout=5000)
    assert pg.text_content("#thread .thlost") == "대상이 바뀌었어요"
    assert pg.locator(PIN).count() == 0, "다시 찾지 못한 대상에는 핀이 없다"
    pg.keyboard.press("Escape")
    write_pay(pg.out)


def test_answered_memo_has_no_pin_and_leaves_badge(apage):
    """(d) 반영됨 답이 달린 메모(상태 파일에 끼워 넣음) → 핀 없음, 배지 수에서 빠짐. 배율로 화면이 실제의 60% 이상이면 고르지 않아도 핀이 보인다."""
    pg = apage
    pg.evaluate("""() => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:')); const a = JSON.parse(localStorage.getItem(k));
        const t = a[0].targets[0];
        a.push({id: 'ans1', no: 9, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: t.rect, note: '답 받은 메모', intent: 'change', sent: true,
                replies: [{kind: '반영됨', what: '크게 했어요', screens: ['pay'], captured: true}]});
        a.push({id: 'ask1', no: 10, screen: 'pay', targets: [t], path: t.path, text: t.text, rect: t.rect, note: '물어본 메모', intent: 'change', sent: true,
                replies: [{kind: '질문', question: '어느 색?', choices: ['파랑', '검정']}]});
        localStorage.setItem(k, JSON.stringify(a)); }""")
    reload(pg)
    fit_view(pg)
    pg.wait_for_selector(PIN + '[data-no="10"]', state="attached", timeout=5000)
    ps = pins(pg)
    assert "9" not in [p["no"] for p in ps], ps
    assert [p["st"] for p in ps if p["no"] == "10"] == ["decide"], "결정 필요 = 강조색 핀"
    assert pg.text_content(BADGE) == str(len(ps)), "배지 = 열린 메모 수"
    assert pg.evaluate("getComputedStyle(document.querySelector('.npin[data-st=\"decide\"]')).backgroundColor") != pg.evaluate("getComputedStyle(document.querySelector('.npin[data-st=\"draft\"], .npin[data-st=\"working\"]')).backgroundColor")
    zoom = lambda: float(pg.evaluate("document.getElementById('stage').dataset.zoom"))
    for _ in range(20):                                # 작게(배율 0.5 아래로)
        if zoom() < 0.5:
            break
        pg.mouse.move(5, 500)
        pg.keyboard.down("Control"); pg.mouse.wheel(0, 200); pg.keyboard.up("Control")
        pg.wait_for_timeout(60)
    pg.mouse.move(5, 500)
    assert zoom() < 0.5 and not pins(pg)[0]["vis"], (zoom(), "작게 볼 때는 고르거나 올려야 보인다")
    zoom_to(pg, "pay", 0.7 * 812)
    pg.mouse.move(5, 500)
    assert pins(pg)[0]["vis"], "화면이 실제의 60% 이상이면 늘 보인다"
