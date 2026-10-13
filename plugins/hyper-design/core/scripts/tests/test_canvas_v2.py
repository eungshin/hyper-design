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
    page.wait_for_timeout(600)
    assert page.evaluate("document.getElementById('modal').hidden"), "Shift+클릭은 크게 보기를 열지 않는다"
    # 화면 안 링크의 대상(색 고리)도 연결된 화면이다
    linked |= set(page.evaluate("[...document.querySelectorAll('#rows .card.lt')].map(c => c.dataset.id)"))
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


def test_multi_select_note(page):
    """주석 달기에서 Shift+클릭 2개 → 요소 2개 · 핀 번호 하나가 두 곳 · 보내기는 요소마다 한 항목(형식 그대로)."""
    sid = page.evaluate("document.querySelector('#rows .card').dataset.id")
    fr = open_screen(page, sid)
    page.click("#mpick")
    page.wait_for_timeout(150)
    els = fr.locator("h1, h2, button, a").filter(has_text=re.compile(r"\S"))
    assert els.count() >= 2
    els.nth(0).click(modifiers=["Shift"])
    page.wait_for_selector("#pop:not([hidden])")
    els.nth(1).click(modifiers=["Shift"])
    page.wait_for_timeout(150)
    assert page.text_content("#ptitle").startswith("2개 요소"), page.text_content("#ptitle")
    assert page.locator("#mpins .sel-box").count() == 2
    assert page.evaluate("document.getElementById('mframe').getAttribute('src')"), "Shift+클릭이 화면을 옮기면 안 된다"
    page.fill("#pnote", "두 곳 모두 굵게")
    page.click("#padd")
    pins = page.locator("#mpins .pin")
    assert pins.count() == 2 and pins.nth(0).text_content() == pins.nth(1).text_content() == "①"
    assert "2개 요소" in page.text_content("#nlist")
    page.keyboard.press("Escape")
    page.click("#nsend")
    t = page.evaluate("window.__hdLastSend")
    lines = t.split("\n")
    assert re.match(r"^\[hyper-design 수정 요청\] out=.+ · 2건$", lines[0]), lines[0]
    assert len(lines) == 7
    assert lines[1].startswith("1. screen=" + sid + " · path=") and lines[4].startswith("2. screen=" + sid + " · path=")
    assert lines[1] != lines[4]
    assert lines[3] == lines[6] == "   요청: 두 곳 모두 굵게"
    page.click("#nclear")


# ---------------------------------------------------------------- gym-v2: 색 링크 · 확대 · 주석 달기 · 안내
GYM = REPO / "runs" / "gym-v2" / "out"
GSHOTS = REPO / "tasks" / "1-canvas-links-imggen" / "shots"


@pytest.fixture(scope="module")
def gym_out():
    if not GYM.exists():
        pytest.skip(f"fixture 없음: {GYM}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-gym-"))
    out = tmp / "out"
    shutil.copytree(GYM, out)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    yield out
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def gpage(ctx, gym_out):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((gym_out / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.wait_for_timeout(300)
    yield pg
    assert not errors, errors
    pg.close()


def link_targets(out, sid):
    ids = {p.stem for p in (out / "screens").glob("*.html")}
    t = (out / "screens" / f"{sid}.html").read_text(encoding="utf-8")
    seen = []
    for h in re.findall(r"""href\s*=\s*["']([^"'#?]+)\.html""", t):
        if h in ids and h != sid and h not in seen:
            seen.append(h)
    return seen


def rgb(hx):
    v = int(hx.lstrip("#"), 16)
    return f"rgb({v >> 16 & 255}, {v >> 8 & 255}, {v & 255})"


def zoom_to(pg, sid, min_h=420):
    """전체 보기 → 그 카드 위에서 Ctrl+휠로 카드 높이가 min_h 가 될 때까지 확대."""
    pg.keyboard.press("0")
    pg.wait_for_timeout(150)
    for _ in range(40):
        b = pg.locator(f'.card[data-id="{sid}"] .phone').bounding_box()
        if b["height"] >= min_h:
            break
        pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        pg.keyboard.down("Control"); pg.mouse.wheel(0, -200); pg.keyboard.up("Control")
        pg.wait_for_timeout(60)
    b, pr = pg.locator(f'.card[data-id="{sid}"] .phone').bounding_box(), pg.locator("#screens").bounding_box()
    pg.mouse.move(pr["x"] + 200, pr["y"] + 200)
    pg.mouse.wheel(b["x"] - (pr["x"] + 60), b["y"] - (pr["y"] + 60))    # 카드 윗부분이 판 안에 오게
    pg.wait_for_timeout(400)
    return pg.locator(f'.card[data-id="{sid}"] .phone').bounding_box()


def test_gym_link_colors(gpage, gym_out):
    sid = "pass" if len(link_targets(gym_out, "pass")) >= 2 else next(
        p.stem for p in sorted((gym_out / "screens").glob("*.html")) if len(link_targets(gym_out, p.stem)) >= 2)
    want = link_targets(gym_out, sid)
    zoom_to(gpage, sid, 380)
    gpage.evaluate("""(id) => document.querySelector('.card[data-id="' + id + '"] .cover')
        .dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, shiftKey: true}))""", sid)
    gpage.wait_for_function("document.querySelectorAll('#ar path.lk').length >= 2", timeout=5000)
    assert gpage.evaluate("document.getElementById('modal').hidden")
    arrows = gpage.evaluate("[...document.querySelectorAll('#ar path.lk')].map(p => [p.dataset.to, p.getAttribute('stroke')])")
    color = {}
    for to, c in arrows:
        assert color.setdefault(to, c) == c, ("같은 대상은 같은 색", to)
    assert set(color) == set(want), (color, want)
    assert len(set(color.values())) == len(color), ("대상마다 다른 색", color)
    assert [to for to, _ in arrows][0] == want[0]          # 처음 나온 순서대로 색을 준다
    for to, c in color.items():
        ring = gpage.evaluate("""(id) => { const c = document.querySelector('.card[data-id="' + id + '"]');
            return [c.classList.contains('lt'), c.style.getPropertyValue('--ring'), getComputedStyle(c.querySelector('.phone')).boxShadow]; }""", to)
        assert ring[0] and ring[1].strip().lower() == c.lower() and rgb(c) in ring[2], (to, c, ring)
    fr = gpage.frame_locator(f'.card[data-id="{sid}"] .phone iframe')
    outl = fr.locator("[data-hd-links]")
    assert outl.count() == len(arrows)
    inner = set(outl.evaluate_all("els => els.map(e => getComputedStyle(e).borderTopColor)"))
    assert inner == {rgb(c) for c in color.values()}, inner
    GSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(GSHOTS / "a-focus-links.png"))
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(300)
    assert gpage.evaluate("document.querySelectorAll('#ar path.lk, .card.lt, .lnum').length") == 0
    assert gpage.evaluate("!document.getElementById('rows').classList.contains('focusing')")
    assert outl.count() == 0


def test_gym_zoom_floor_and_fit(gpage):
    gpage.click("#zoom")
    gpage.wait_for_timeout(150)
    gpage.mouse.move(700, 500)
    for _ in range(20):
        gpage.keyboard.down("Control"); gpage.mouse.wheel(0, 400); gpage.keyboard.up("Control")
        gpage.wait_for_timeout(30)
    z = float(gpage.get_attribute("#stage", "data-zoom"))
    assert z < 0.25, z
    assert int(gpage.text_content("#zoom").rstrip("%")) < 25
    gpage.keyboard.press("0")
    gpage.wait_for_timeout(200)
    pr = gpage.locator("#screens").bounding_box()
    boxes = gpage.evaluate("[...document.querySelectorAll('#rows .card')].map(c => { const r = c.getBoundingClientRect(); return [c.dataset.id, r.left, r.top, r.right, r.bottom]; })")
    for cid, l, t, r, b in boxes:
        assert l >= pr["x"] - 1 and t >= pr["y"] - 1 and r <= pr["x"] + pr["width"] + 1 and b <= pr["y"] + pr["height"] + 1, cid
    gpage.wait_for_timeout(800)
    GSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(GSHOTS / "b-zoomed-out.png"))


def test_gym_annotate_button(gpage):
    sid = gpage.evaluate("document.querySelector('#rows .card').dataset.id")
    gpage.evaluate("""(id) => document.querySelector('.card[data-id="' + id + '"] .cover')
        .dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))""", sid)
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    gpage.frame_locator("#mframe").locator("body").wait_for()
    gpage.wait_for_timeout(400)
    assert gpage.text_content("#mpick").strip() == "주석 달기"
    pb, fb = gpage.locator("#mpick").bounding_box(), gpage.locator("#mbox").bounding_box()
    assert pb["y"] >= fb["y"] + fb["height"], (pb, fb)
    assert abs((pb["x"] + pb["width"] / 2) - (fb["x"] + fb["width"] / 2)) < 2
    assert pb["y"] + pb["height"] <= gpage.viewport_size["height"]
    GSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(GSHOTS / "c-modal-annotate.png"))
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)
    assert gpage.evaluate("document.getElementById('modal').hidden")
    # 카드에 올리면 '주석' → 누르면 주석 달기가 켜진 채로 크게 보기
    b = zoom_to(gpage, sid)
    anno = gpage.locator(f'.card[data-id="{sid}"] .anno')
    gpage.mouse.move(5, 5)
    assert not anno.is_visible()
    gpage.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    gpage.wait_for_timeout(100)
    assert anno.is_visible() and anno.text_content().strip() == "주석"
    anno.click()
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    assert gpage.get_attribute("#mpick", "aria-pressed") == "true"
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)


def test_gym_shortcut_hint(gpage):
    hint = gpage.locator("#khint")
    assert hint.is_visible()
    assert hint.text_content().strip() == "Shift+클릭 연결 보기 · A 화살표 · 0 전체 보기 · 클릭 크게 보기"
    hb, pr = hint.bounding_box(), gpage.locator("#screens").bounding_box()
    assert hb["x"] < pr["x"] + 40 and hb["y"] + hb["height"] > pr["y"] + pr["height"] - 40
    gpage.evaluate("document.querySelector('#rows .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))")
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    assert not hint.is_visible()
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)
    assert hint.is_visible()
