"""캔버스 v2 — 연결 보기 · 요소 고르기 · 메모 저장 · 보내기 (Playwright, 실제 브라우저).

runs/laundry-v1/out 를 임시 폴더로 복사하고 build_canvas.py 로 다시 만든 뒤 index.html 을 file:// 로 연다.
"""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
REPO = SCRIPTS.parents[3]
FIXTURE = REPO / "runs" / "laundry-v1" / "out"
SHOTS = REPO / "tasks" / "0-harness-v2" / "phase3-shots"

sync_api = pytest.importorskip("playwright.sync_api")
if not FIXTURE.exists():
    pytest.skip(f"fixture 없음: {FIXTURE}", allow_module_level=True)


@pytest.fixture(scope="module")
def out_dir():
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-v2-"))
    out = tmp / "out"
    shutil.copytree(FIXTURE, out)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    yield out
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                b = p.chromium.launch(**kw)
                break
            except Exception:
                continue
        if b is None:
            pytest.skip("chromium 을 띄울 수 없음")
        yield b
        b.close()


@pytest.fixture(scope="module")
def ctx(browser):
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    yield c
    c.close()


@pytest.fixture(scope="module")
def page(ctx, out_dir):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((out_dir / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    pg.errors = errors
    yield pg
    assert not errors, errors


def reload(pg):
    pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.wait_for_timeout(200)


def visible_paths(pg):
    return pg.evaluate("[...document.querySelectorAll('#rows path.ln')].filter(p => getComputedStyle(p).display !== 'none').length")


def test_arrow_toggle_persists(page):
    total = page.locator("#rows path.ln").count()
    assert total > 0
    assert visible_paths(page) == total
    page.click("#arrows")
    assert visible_paths(page) == 0
    reload(page)
    assert visible_paths(page) == 0
    assert page.get_attribute("#arrows", "aria-pressed") == "false"
    page.keyboard.press("a")                       # 단축키 A 로 다시 켜기
    assert visible_paths(page) == total
    reload(page)
    assert visible_paths(page) == total


def test_shift_click_focus(page):
    page.click("#fit")
    page.wait_for_timeout(200)
    fid = page.evaluate("document.querySelector('#rows path.ln').getAttribute('data-from')")
    linked = set(page.evaluate("""(id) => [...document.querySelectorAll('#rows path.ln')]
        .filter(p => p.dataset.from === id || p.dataset.to === id).flatMap(p => [p.dataset.from, p.dataset.to])""", fid))
    box = page.locator(f'.card[data-id="{fid}"] .cover').bounding_box()
    page.keyboard.down("Shift")
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.keyboard.up("Shift")
    page.wait_for_timeout(250)
    assert page.evaluate("document.getElementById('modal').hidden"), "Shift+클릭은 크게 보기를 열지 않는다"
    state = page.evaluate("""() => [...document.querySelectorAll('#rows .card')].map(c =>
        [c.dataset.id, c.classList.contains('hl'), +getComputedStyle(c).opacity])""")
    for cid, hl, op in state:
        if cid in linked:
            assert hl and op == 1, (cid, hl, op)
        else:
            assert not hl and op < 0.5, (cid, hl, op)
    on = page.evaluate("[...document.querySelectorAll('#rows path.ln')].map(p => [p.classList.contains('on'), +getComputedStyle(p).opacity])")
    assert any(o for o, _ in on) and all((op == 1) if o else (op < 0.5) for o, op in on)
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / "focus-mode.png"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(100)
    assert page.evaluate("!document.getElementById('rows').classList.contains('focusing') && !document.querySelector('#rows .card.hl')")
    page.click("#zoom")


def open_screen(pg, sid):
    pg.evaluate("""(id) => { const c = document.querySelector('.card[data-id="' + id + '"] .cover');
        c.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); }""", sid)
    pg.wait_for_function("!document.getElementById('modal').hidden")
    fr = pg.frame_locator("#mframe")
    fr.locator("body").wait_for()
    pg.wait_for_timeout(300)
    return fr


def test_pick_note_pin_persists(page):
    sid = page.evaluate("document.querySelector('#rows .card').dataset.id")
    fr = open_screen(page, sid)
    page.click("#mpick")
    assert page.get_attribute("#mpick", "aria-pressed") == "true"
    page.wait_for_timeout(150)
    target = fr.locator("h1, h2, button, a").filter(has_text=re.compile(r"\S")).first
    want = re.sub(r"\s+", " ", target.inner_text()).strip()[:60]
    target.click()
    page.wait_for_selector("#pop:not([hidden])")
    assert page.text_content("#ptitle") == want
    assert page.text_content("#ppath")
    page.fill("#pnote", "가격을 오른쪽 끝으로 붙이고 굵게")
    page.click("#padd")
    assert page.locator("#mpins .pin").count() == 1
    assert page.text_content("#mpins .pin") == "①"
    SHOTS.mkdir(parents=True, exist_ok=True)
    # 팝오버 + 핀을 한 장에: 두 번째 요소를 고른 상태로 찍고 취소
    fr.locator("body *").filter(has_text=re.compile(r"\S")).nth(3).click()
    page.wait_for_selector("#pop:not([hidden])")
    page.screenshot(path=str(SHOTS / "popover-pin.png"))
    page.click("#pcancel")
    assert page.locator(f'.card[data-id="{sid}"] .nbadge').text_content() == "1"
    reload(page)
    assert page.locator(f'.card[data-id="{sid}"] .nbadge').text_content() == "1"
    open_screen(page, sid)
    assert page.locator("#mpins .pin").count() == 1
    page.keyboard.press("Escape")


def test_send_format(page):
    page.wait_for_selector("#notes:not([hidden])")
    page.click("#nsend")
    t = page.evaluate("window.__hdLastSend")
    assert t, "보내기 글이 없음"
    lines = t.split("\n")
    m = re.match(r"^\[hyper-design 수정 요청\] out=(.+) · (\d+)건$", lines[0])
    assert m, lines[0]
    out = m.group(1)
    assert not out.startswith("/") or os.name != "nt", out
    assert out.replace("\\", "/").rstrip("/").lower().endswith("/out")
    n = int(m.group(2))
    assert n == 1 and len(lines) == 1 + 3 * n
    assert re.match(r"^1\. screen=\S+ · path=.+$", lines[1]), lines[1]
    assert re.match(r'^   text=".*" · intent=(change|question)$', lines[2]), lines[2]
    assert lines[3] == "   요청: 가격을 오른쪽 끝으로 붙이고 굵게"
    assert "복사했어요" in page.text_content("#nmsg")


def test_clear_sent(page):
    assert page.is_visible("#nclear")
    page.click("#nclear")
    assert page.evaluate("document.querySelectorAll('#nlist li').length") == 0
    assert page.is_hidden("#notes")
    reload(page)
    assert page.locator(".nbadge").count() == 0
