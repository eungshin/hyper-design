"""캔버스 v2 — 연결 보기 · 요소 고르기 · 메모 저장 · 보내기 (Playwright, 실제 브라우저).

runs/laundry-v1/out 를 임시 폴더로 복사하고 build_canvas.py 로 다시 만든 뒤 index.html 을 file:// 로 연다.
"""
import os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
REPO = SCRIPTS.parents[4]
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


@pytest.mark.area("flow")
def test_arrow_toggle_persists(page):
    """E7: 판에 늘 그리는 선 — 표시 패널의 보이기 버튼으로 끄고 켜며, 새로고침 뒤에도 그대로. [주요 흐름] 버튼·A 키는 없다(D9)."""
    total = page.locator("#rows path.ln").count()
    assert total > 0
    assert visible_paths(page) == total
    assert page.locator("#arrows").count() == 0
    page.click("#lnShow")
    assert visible_paths(page) == 0
    reload(page)
    assert visible_paths(page) == 0
    assert page.get_attribute("#lnShow", "aria-pressed") == "false"
    page.keyboard.press("a")                       # A 는 비워 둔다
    assert visible_paths(page) == 0
    page.click("#lnShow")
    assert visible_paths(page) == total
    reload(page)
    assert visible_paths(page) == total


@pytest.mark.area("links")
def test_shift_click_focus(page):
    page.click("#zoom"); page.click("#fit")
    page.wait_for_timeout(200)
    fid = page.evaluate("document.querySelector('#rows path.ln').getAttribute('data-from')")
    linked = set(page.evaluate("""(id) => [...document.querySelectorAll('#rows path.ln')]
        .filter(p => p.dataset.from === id || p.dataset.to === id).flatMap(p => [p.dataset.from, p.dataset.to])""", fid))
    box = page.locator(f'.card[data-id="{fid}"] .cover').bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_timeout(600)
    assert page.evaluate("document.getElementById('modal').hidden"), "누르기(연결 보기)는 크게 보기를 열지 않는다"
    state = page.evaluate("""() => [...document.querySelectorAll('#rows .card')].map(c =>
        [c.dataset.id, c.classList.contains('hl'), +getComputedStyle(c).opacity])""")
    for cid, hl, op in state:
        if cid in linked:
            assert hl and op == 1, (cid, hl, op)
        else:
            assert not hl and op < 0.5, (cid, hl, op)
    on = page.evaluate("[...document.querySelectorAll('#rows path.ln')].map(p => [p.classList.contains('on'), +getComputedStyle(p).strokeOpacity])")
    assert all((op == 1) if o else (op < 0.5) for o, op in on), on     # 그 화면의 선(나가고 들어오는)은 같은 선이 진하게, 나머지는 흐리게(E20)
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / "focus-mode.png"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(100)
    assert page.evaluate("!document.getElementById('rows').classList.contains('focusing') && !document.querySelector('#rows .card.hl')")
    page.click("#zoom"); page.click("#fit")


def open_screen(pg, sid):
    pg.evaluate("""(id) => { const c = document.querySelector('.card[data-id="' + id + '"] .cover');
        c.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true})); }""", sid)
    pg.wait_for_function("!document.getElementById('modal').hidden")
    fr = pg.frame_locator("#mframe")
    fr.locator("body").wait_for()
    pg.wait_for_timeout(300)
    return fr


@pytest.mark.area("notes", "modal")
def test_pick_note_pin_persists(page):
    sid = page.evaluate("document.querySelector('#rows .card').dataset.id")
    fr = open_screen(page, sid)
    page.click('#tools [data-tool="annotate"]')
    assert page.get_attribute('#tools [data-tool="annotate"]', "aria-pressed") == "true"
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
    assert page.text_content("#mpins .pin") == "1", "핀 = 그 화면의 메모 번호(n.no)"
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


@pytest.mark.area("notes")
def test_send_format(page):
    page.wait_for_selector("#notes:not([hidden])")
    page.click("#nsend")
    # 복사는 비동기(클립보드 약속) — 알림·'보냄' 표시는 복사가 끝난 뒤에 붙는다. 바로 읽으면 #nmsg 가 비어 있다(-n 4 에서 가끔)
    page.wait_for_function("document.getElementById('nmsg').textContent.indexOf('복사') >= 0", timeout=5000)
    t = page.evaluate("window.__hdLastSend")
    assert t, "보내기 글이 없음"
    lines = t.split("\n")
    m = re.match(r"^\[hyper-design 수정 요청\] out=(.+) · (\d+)건$", lines[0])
    assert m, lines[0]
    out = m.group(1)
    assert not out.startswith("/") or os.name != "nt", out
    assert out.replace("\\", "/").rstrip("/").lower().endswith("/out")
    assert int(m.group(2)) == 1                      # 줄 형식은 unit(test_canvas_unit_send_composition)·fix 스킬 계약(test_fix_skill)이 지킨다
    assert "   요청: 가격을 오른쪽 끝으로 붙이고 굵게" in lines, "보낸 글에 그 메모"
    assert "복사했어요" in page.text_content("#nmsg")


@pytest.mark.area("notes")
def test_clear_sent(page):
    """[보낸 것 완료로]: 보낸 메모를 지우지 않고 완료(답 '확인')로 — 목록·배지에서 빠지고 기록은 메모 안에 남는다.
    보낸 메모를 스스로 심는다(#264) — 앞 테스트(메모 달기·보내기)에 기대지 않아 혼자·영역(-m)·-n 에서 같게 돈다."""
    page.evaluate("""() => { const sid = document.querySelector('#rows .card').dataset.id,
        h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(window.__hdKeyPath || location.pathname);
        Object.keys(localStorage).filter(k => k.startsWith('hd-notes:') || k.startsWith('hd-note-seq:') || k.startsWith('hd-show-sent:')).forEach(k => localStorage.removeItem(k));
        localStorage.setItem('hd-notes:' + h, JSON.stringify([{id: 'sent1', no: 1, screen: sid, targets: [{path: 'body', text: ''}], path: 'body', text: '',
            rect: null, note: '보낸 메모', intent: 'change', sent: true, replies: []}]));
        localStorage.setItem('hd-note-seq:' + h, JSON.stringify({[sid]: 1})); }""")
    reload(page)
    page.click('#dock .dk-tab[data-p="notes"]')
    assert page.is_visible("#nclear") and page.get_attribute("#nclear", "aria-label") == page.get_attribute("#nclear", "title") == "보낸 것 완료로"
    page.click("#nclear")
    assert page.evaluate("document.querySelectorAll('#nlist li').length") == 0
    assert page.get_attribute("#nsent .ncb", "data-n") == "1"   # 완료한 메모는 지운 것이 아니라 숨김(task 29) — 보낸 메모 보기로 다시 볼 수 있다
    reload(page)
    assert page.locator(".nbadge").count() == 0
    ns = page.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))))")
    assert ns and all(n["replies"][-1]["kind"] == "확인" and n["replies"][-1]["by"] == "user" for n in ns), ns


@pytest.mark.area("notes", "modal")
def test_multi_select_note(page):
    """주석 달기에서 Shift+클릭 2개 → 요소 2개 · 핀 번호 하나가 두 곳 · 보내기는 한 항목 + 다른 곳 줄(task 17 R6, 머리 형식 그대로)."""
    # 메모 없이 시작 — 영역(-m)으로 골라 돌리면 앞 테스트(test_pick_note_pin_persists)의 메모를 지우는 test_clear_sent 가 빠진다
    page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-notes:') || k.startsWith('hd-note-seq:')).forEach(k => localStorage.removeItem(k))")
    reload(page)
    sid = page.evaluate("document.querySelector('#rows .card').dataset.id")
    fr = open_screen(page, sid)
    page.click('#tools [data-tool="annotate"]')
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
    assert pins.count() == 2 and pins.nth(0).text_content() == pins.nth(1).text_content() == "1"
    assert "2개 요소" in page.text_content("#nlist")
    page.keyboard.press("Escape")
    page.click("#nsend")
    t = page.evaluate("window.__hdLastSend")
    lines = t.split("\n")
    assert re.match(r"^\[hyper-design 수정 요청\] out=.+ · 1건$", lines[0]), lines[0]   # task 17 R6: 여러 요소 메모 = 한 항목 + 다른 곳
    assert len(lines) == 5
    assert lines[1].startswith("1. screen=" + sid + " · path=")
    assert lines[3] == "   요청: 두 곳 모두 굵게"
    assert lines[4].startswith("   다른 곳: ")
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


@pytest.mark.area("links")
def test_gym_link_colors(gpage, gym_out):
    """E20 A: 카드를 누르면 화면 안 출발 버튼마다 그 선과 같은 색 테두리 + 번호 — 같은 도착 = 같은 번호. Esc = 모두 지움."""
    sid = "pass" if len(link_targets(gym_out, "pass")) >= 2 else next(
        p.stem for p in sorted((gym_out / "screens").glob("*.html")) if len(link_targets(gym_out, p.stem)) >= 2)
    want = link_targets(gym_out, sid)
    zoom_to(gpage, sid, 380)
    shift_click(gpage, sid)
    fr = gpage.frame_locator(f'.card[data-id="{sid}"] .phone iframe')
    outl = fr.locator("[data-hd-links]")
    outl.first.wait_for(state="attached", timeout=5000)
    assert gpage.evaluate("document.getElementById('modal').hidden")
    gpage.wait_for_timeout(200)
    lines = gpage.evaluate("""(id) => [...document.querySelectorAll('#rows path.ln')].filter(p => p.dataset.from === id || p.dataset.to === id)
        .map(p => p.getAttribute('stroke'))""", sid)
    got = outl.evaluate_all("els => els.map(e => [getComputedStyle(e).borderTopColor, (e.querySelector('span') || {}).textContent || ''])")
    assert {c for c, _ in got} <= {rgb(c) for c in lines}, (got, lines)
    assert all(n for _, n in got), ("버튼마다 번호", got)
    rows = gpage.evaluate("[...document.querySelectorAll('#lgRows .lgrow')].map(r => [r.dataset.to, r.querySelector('.lgdot').textContent])")
    assert {t for t, _ in rows} == set(want), (rows, want)
    assert len({n for _, n in rows}) == len(rows), ("도착마다 다른 번호", rows)
    assert {n for _, n in got} == {n for _, n in rows}, ("버튼 번호 = 패널 번호", got, rows)
    GSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(GSHOTS / "a-focus-links.png"))
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(300)
    assert gpage.evaluate("!document.getElementById('rows').classList.contains('focusing') && document.getElementById('legend').hidden")
    assert outl.count() == 0


@pytest.mark.area("input")
def test_gym_zoom_floor_and_fit(gpage):
    gpage.click("#zoom"); gpage.click("#fit")
    gpage.wait_for_timeout(150)
    gpage.mouse.move(700, 500)
    for _ in range(20):
        gpage.keyboard.down("Control"); gpage.mouse.wheel(0, 400); gpage.keyboard.up("Control")
        gpage.wait_for_timeout(30)
    z = float(gpage.get_attribute("#stage", "data-zoom"))
    assert z < 0.25, z
    assert int(gpage.text_content("#zoom").rstrip(" ▾%")) < 25
    gpage.keyboard.press("0")
    gpage.wait_for_timeout(200)
    pr = gpage.locator("#screens").bounding_box()
    boxes = gpage.evaluate("[...document.querySelectorAll('#rows .card')].map(c => { const r = c.getBoundingClientRect(); return [c.dataset.id, r.left, r.top, r.right, r.bottom]; })")
    for cid, l, t, r, b in boxes:
        assert l >= pr["x"] - 1 and t >= pr["y"] - 1 and r <= pr["x"] + pr["width"] + 1 and b <= pr["y"] + pr["height"] + 1, cid
    gpage.wait_for_timeout(800)
    GSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(GSHOTS / "b-zoomed-out.png"))


@pytest.mark.area("modal")
def test_gym_annotate_button(gpage):
    sid = gpage.evaluate("document.querySelector('#rows .card').dataset.id")
    gpage.evaluate("""(id) => document.querySelector('.card[data-id="' + id + '"] .cover')
        .dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))""", sid)
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    gpage.frame_locator("#mframe").locator("body").wait_for()
    gpage.wait_for_timeout(400)
    assert gpage.is_visible('#tools [data-tool="annotate"]'), "크게 보기의 주석 = 왼쪽 주석 도구(G6)"
    GSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(GSHOTS / "c-modal-annotate.png"))
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)
    assert gpage.evaluate("document.getElementById('modal').hidden")
    # 카드에 올리면 '▶ 보기' → 누르면 실제로 눌러 보는 크게 보기(재작업 S3: 주석 버튼은 왼쪽 도구로)
    b = zoom_to(gpage, sid)
    pres = gpage.locator(f'.card[data-id="{sid}"] .pres')
    gpage.mouse.move(5, 5)
    assert not pres.is_visible()
    gpage.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    gpage.wait_for_timeout(100)
    assert pres.is_visible() and pres.text_content().strip() == "보기"
    ab = pres.bounding_box()
    assert ab["y"] + ab["height"] <= b["y"] + 0.5, (ab, b)      # 카드 바깥(오른쪽 위)
    pres.click()
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    assert gpage.get_attribute('#tools [data-tool="annotate"]', "aria-pressed") != "true"
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)


@pytest.mark.area("input")
def test_gym_no_shortcut_hint(gpage):
    """S1b: 아래 왼쪽 단축키 안내 줄(#khint)은 지웠다 — 그 자리는 프로젝트 탭 바. 누르면 크게 보기·Esc 는 그대로."""
    assert gpage.locator("#khint").count() == 0
    gpage.evaluate("document.querySelector('#rows .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))")
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    gpage.keyboard.press("Escape")
    gpage.wait_for_function("document.getElementById('modal').hidden")


# ---------------------------------------------------------------- canvas-focus-v2
FSHOTS = REPO / "tasks" / "2-canvas-focus-v2" / "shots"
V3SHOTS = REPO / "tasks" / "3-canvas-v3" / "shots"

LABEL_GEOM_JS = """() => [...document.querySelectorAll('#rows .alabel')].map(n => {
    const p = [...document.querySelectorAll('#rows path.ln')].find(q => (q.dataset.from === n.dataset.from && q.dataset.to === n.dataset.to) ||
                                                                    (q.dataset.from === n.dataset.to && q.dataset.to === n.dataset.from));   // 태그는 방향마다
    const b = p ? p.getBBox() : null;
    return {left: n.style.left, top: n.style.top, box: b && [b.x, b.y, b.x + b.width, b.y + b.height]};
})"""


@pytest.mark.area("flow", "links")
def test_v2_label_positions(gpage):
    """회귀(0efa322): .alabel 의 style 따옴표가 깨져 모든 이름표가 판 원점에 쌓였다."""
    labels = gpage.evaluate(LABEL_GEOM_JS)
    assert labels, "gym-v2 에 갈래 이름표가 있어야 한다"
    for l in labels:
        assert l["left"].endswith("px") and l["top"].endswith("px"), l
        x, y = float(l["left"][:-2]), float(l["top"][:-2])
        assert not (abs(x) < 1 and abs(y) < 1), ("원점에 쌓임", l)
        x0, y0, x1, y1 = l["box"]
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        assert (dx * dx + dy * dy) ** 0.5 <= 400, l


def shift_click(pg, sid):
    pg.evaluate("""(id) => document.querySelector('.card[data-id="' + id + '"] .cover')
        .dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))""", sid)


EMPTY_JS = r"""() => {
  const pane = document.getElementById('screens'), r = pane.getBoundingClientRect();
  const ok = el => el && (el === pane || el.id === 'stage' || el.id === 'rows' || el.classList.contains('flow') ||
                          el.classList.contains('cards') || el.id === 'intro' || el.id === 'foot');
  for (let y = r.top + 40; y < r.bottom - 60; y += 17)
    for (let x = r.left + 40; x < r.right - 400; x += 23) if (ok(document.elementFromPoint(x, y))) return {x, y};
  return null;
}"""


def parse_path(d):
    toks = re.findall(r"[MLQCSAZ]|-?\d+(?:\.\d+)?", d)
    cmds, i = [], 0
    while i < len(toks):
        c = toks[i]; i += 1
        nums = []
        while i < len(toks) and not toks[i].isalpha():
            nums.append(float(toks[i])); i += 1
        cmds.append((c, nums))
    return cmds


def check_route(d, max_q=3):
    """둥근 직각 연결선: M/L/Q 만, L 은 가로·세로만, 꺾임(Q) ≤ max_q, 자기 교차 없음."""
    cmds = parse_path(d)
    assert {c for c, _ in cmds} <= {"M", "L", "Q"}, d
    assert cmds[0][0] == "M"
    assert sum(1 for c, _ in cmds if c == "Q") <= max_q, d
    pts, cur = [], tuple(cmds[0][1])
    pts.append(cur)
    for c, n in cmds[1:]:
        if c == "L":
            nxt = (n[0], n[1])
            assert abs(nxt[0] - cur[0]) < 0.25 or abs(nxt[1] - cur[1]) < 0.25, ("사선", cur, nxt, d)
            pts.append(nxt); cur = nxt
        else:
            qx, qy, ex, ey = n
            for t in [i / 8 for i in range(1, 9)]:
                pts.append(((1 - t) ** 2 * cur[0] + 2 * (1 - t) * t * qx + t * t * ex, (1 - t) ** 2 * cur[1] + 2 * (1 - t) * t * qy + t * t * ey))
            cur = (ex, ey)
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if pts[i] != pts[i + 1]]

    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def cross(a, b, c, e):
        d1, d2, d3, d4 = o(c, e, a), o(c, e, b), o(a, b, c), o(a, b, e)
        return d1 * d2 < -1e-6 and d3 * d4 < -1e-6
    for i in range(len(segs)):
        for j in range(i + 2, len(segs)):
            assert not cross(*segs[i], *segs[j]), ("자기 교차", d)
    return cmds


@pytest.mark.area("flow")
def test_v2_route_shapes(gpage):
    cases = gpage.evaluate("""() => {
        const R = window.HDCanvas.routeCurve, s = {x: 400, y: 500, dir: 'right'};
        return [R(s, {x: 1100, y: 100}), R(s, {x: -300, y: 100}), R(s, {x: -200, y: 1500}), R(s, {x: 900, y: 1500}),
                R(s, {x: 420, y: 100}), R(s, {x: 400, y: 100}, {apex: 32, k: 2}),
                R({x: 500, y: 300, dir: 'up'}, {x: 1300, y: 290}), R({x: 500, y: 300, dir: 'up'}, {x: 100, y: 1300}, {apex: 28}),
                R({x: 500, y: 1300, dir: 'up'}, {x: 1200, y: 290})];
    }""")
    for d in cases:
        check_route(d)
    lane = gpage.evaluate("window.HDCanvas.routeCurve({x: 900, y: 300, dir: 'up'}, {x: 400, y: 1300}, {lift: 16, apex: 10, laneX: 220})")
    check_route(lane, 4)                                  # 다른 줄 갈래: 왼쪽 통로(꺾임 4)
    a, b, c = (parse_path(d) for d in cases[:3])          # (a) 오른쪽 (b) 왼쪽 (c) 아래 왼쪽
    assert a[-1][1] == [1100, 100] and b[-1][1] == [-300, 100] and c[-1][1] == [-200, 1500]
    # 판의 모든 선도 같은 규칙, 화살촉 색 = 선 색
    on = gpage.evaluate("""() => [...document.querySelectorAll('#rows path.ln')].map(p => {
        const id = (p.getAttribute('marker-end') || '').match(/#([^)]+)/)[1];
        return [p.getAttribute('d'), p.getAttribute('stroke'), document.querySelector('#' + id + ' path').getAttribute('fill')]; })""")
    assert on
    for d, stroke, fill in on:
        check_route(d, 4)
        assert stroke.lower() == fill.lower(), (stroke, fill)


@pytest.mark.area("links")
def test_v2_exit_focus(gpage):
    """빈 판 누르기 · Esc = 고르기 풀기(강조·연결 패널도 꺼짐). 두 번 누르기(키보드 detail 0) = 크게 보기."""
    zoom_to(gpage, "pass", 380)
    shift_click(gpage, "pass")
    gpage.wait_for_function("!document.getElementById('legend').hidden", timeout=5000)
    assert gpage.evaluate("document.getElementById('rows').classList.contains('focusing')")
    pt = gpage.evaluate(EMPTY_JS)
    assert pt, "빈 판 자리를 찾지 못함"
    gpage.mouse.click(pt["x"], pt["y"])
    gpage.wait_for_timeout(150)
    assert gpage.evaluate("!document.getElementById('rows').classList.contains('focusing') && document.getElementById('legend').hidden")
    assert gpage.evaluate("document.getElementById('modal').hidden")
    shift_click(gpage, "pass")
    gpage.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)
    assert gpage.evaluate("!document.getElementById('rows').classList.contains('focusing')")
    gpage.evaluate("""() => document.querySelector('.card[data-id="pass"] .cover')
        .dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}))""")
    gpage.wait_for_function("!document.getElementById('modal').hidden")
    gpage.frame_locator("#mframe").locator("body").wait_for()
    gpage.wait_for_timeout(300)
    FSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(FSHOTS / "e-modal-annotate-top.png"))
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(150)


@pytest.mark.area("links")
def test_v2_expand_tall_screen(gpage, gym_out):
    sid = "renew"
    assert link_targets(gym_out, sid)
    zoom_to(gpage, sid, 300)
    before = gpage.evaluate("[...document.querySelectorAll('#rows .card')].map(c => [c.dataset.id, c.offsetLeft, c.offsetTop])")
    shift_click(gpage, sid)
    gpage.wait_for_function(f"""document.querySelector('.card[data-id="{sid}"] .phone').offsetHeight > 812""", timeout=5000)
    gpage.wait_for_timeout(300)
    after = gpage.evaluate("[...document.querySelectorAll('#rows .card')].map(c => [c.dataset.id, c.offsetLeft, c.offsetTop])")
    assert before == after
    FSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(FSHOTS / "d-expanded-tall.png"))
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(400)
    assert gpage.evaluate(f"""document.querySelector('.card[data-id="{sid}"] .phone').offsetHeight""") == 812


@pytest.mark.area("flow")
def test_v2_base_curves_shot(gpage):
    gpage.keyboard.press("0")
    gpage.wait_for_timeout(300)
    assert gpage.evaluate("[...document.querySelectorAll('#rows .alabel')].every(n => getComputedStyle(n).display === 'none')")
    FSHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(FSHOTS / "f-base-fit.png"))
    zoom_to(gpage, "pt-detail", 300)
    gpage.mouse.wheel(-420, -160)                          # 줄 위 통로와 왼쪽 카드가 보이게
    gpage.wait_for_timeout(400)
    gpage.screenshot(path=str(FSHOTS / "f-base-curves.png"))


CARD_BOXES_JS = """() => [...document.querySelectorAll('#rows .card')].map(c => {
    const ph = c.querySelector('.phone');
    return [c.dataset.id, c.offsetLeft, c.offsetTop, c.offsetLeft + c.offsetWidth, c.offsetTop + Math.max(c.offsetHeight, ph.offsetHeight)]; })"""


def vertical_points(d, step=4, skip=12):
    """세로 L 구간 위 점들(경로 처음·끝 12px 제외)."""
    cmds = parse_path(d)
    cur, out, segs = tuple(cmds[0][1]), [], []
    for c, n in cmds[1:]:
        nxt = (n[-2], n[-1])
        if c == "L" and abs(nxt[0] - cur[0]) < 0.25 and abs(nxt[1] - cur[1]) > 0:
            segs.append((cur, nxt))
        cur = nxt
    start, end = tuple(cmds[0][1]), cur
    for a, b in segs:
        n = max(1, int(abs(b[1] - a[1]) // step))
        for i in range(n + 1):
            p = (a[0], a[1] + (b[1] - a[1]) * i / n)
            if min(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 for q in (start, end)) > skip:
                out.append(p)
    return out


def assert_no_vertical_in_cards(pg, sel):
    boxes = pg.evaluate(CARD_BOXES_JS)
    paths = pg.evaluate(f"[...document.querySelectorAll('{sel}')].map(p => [p.dataset.from, p.dataset.to, p.getAttribute('d')])")
    for fr, to, d in paths:
        for x, y in vertical_points(d):
            for cid, l, t, r, b in boxes:
                assert not (l < x < r and t < y < b), (f"{fr}→{to} 세로선이 카드 {cid} 안을 지남", (x, y), d)
    return len(paths)


@pytest.mark.area("flow", "links")
def test_v2_no_vertical_through_cards(gpage, gym_out):
    """카드 높이가 늦게 정해지면(부하 아래 화면 크기 맞추기) 선은 다음 다시 그리기 때 따라온다 — 그 사이의 옛 선은 보지 않고 다시 잰다.
    R55(브라우저 4개 동시 부하에서 잡음): 첫 측정 때 gym 카드 위 7844 · home→gym 선은 7992 에서 들어감(옛 배치) → 2초 뒤 카드 7757·선 그대로 → 5초 안에 선이 다시 그려져 통과.
    길 찾기가 정말 틀리면 10초 뒤에도 그대로라 마지막 실패를 그대로 던진다."""
    gpage.keyboard.press("Escape")
    end = time.time() + 10
    while True:
        try:
            assert assert_no_vertical_in_cards(gpage, "#rows path.ln") > 0
            return
        except AssertionError:
            if time.time() > end:
                raise
            gpage.wait_for_timeout(250)


# ---------------------------------------------------------------- canvas-v3 (phase 1): 주요 흐름 점선 · 같은 도착 묶기
def focus_all(pg, sid):
    """그 카드만 고른다 — 그 선이 진해지고 화면 안 버튼 표시·연결 패널이 채워질 때까지."""
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    zoom_to(pg, sid, 300)
    shift_click(pg, sid)
    pg.wait_for_function("!document.getElementById('legend').hidden", timeout=5000)
    pg.wait_for_timeout(900)                               # 긴 화면은 펼친 뒤 다시 그린다


@pytest.mark.area("links")
def test_v3_same_target_merge(gpage, gym_out):
    """같은 도착으로 가는 버튼 여럿 = 연결 패널 한 줄 · 화면 안 테두리는 버튼마다, 번호는 같다."""
    focus_all(gpage, "home")
    n = len(link_targets(gym_out, "home"))
    rows = gpage.evaluate("[...document.querySelectorAll('#lgRows .lgrow')].map(r => [r.dataset.to, r.querySelector('.lgdot').textContent, r.querySelector('b').textContent])")
    assert len(rows) == n, rows
    socks = gpage.evaluate("[...document.querySelectorAll('.card[data-id=\"home\"] .sock:not(.selsock)')].map(s => s.dataset.to)")
    merged = [r for r in rows if socks.count(r[0]) >= 2]
    assert merged, (rows, socks)
    got = gpage.frame_locator('.card[data-id="home"] .phone iframe').locator("[data-hd-links]").evaluate_all(
        "els => els.map(e => (e.querySelector('span') || {}).textContent || '')")
    for _, num, _ in merged:
        assert got.count(num) >= 2, ("같은 도착 버튼들은 같은 번호", num, got)


def pointer_off_board(pg):
    """마우스를 판 밖(위쪽 줄 왼쪽 끝)으로 — (5, 300) 같은 고정 자리는 앞 테스트가 남긴 카메라에 따라 카드 위일 수 있다(그러면 그 카드 선·태그가 강조된다).
    올린 카드 강조(#rows.lnhov)가 꺼질 때까지 기다린다."""
    b = pg.locator("header.hd").bounding_box()
    pg.mouse.move(b["x"] + 2, b["y"] + b["height"] / 2)
    pg.wait_for_function("!document.getElementById('rows').classList.contains('lnhov')", timeout=3000)


@pytest.mark.area("flow")
def test_v3_main_flow_dashed(gpage):
    """2.5b(E7·E14·D9): 판에 늘 그리는 선은 실선(점선 = 반영 대기뿐), [주요 흐름] 버튼·범례 체크·A 키 없음, 태그는 평소 숨김.
    고르면(E20) 선은 그대로 다 보이고, 그 카드 선이 아닌 것만 흐리게(.18)."""
    gpage.keyboard.press("Escape")
    gpage.wait_for_timeout(200)
    vis = lambda: gpage.evaluate("[...document.querySelectorAll('#rows path.ln')].filter(p => getComputedStyle(p).display !== 'none').length")
    total = gpage.locator("#rows path.ln").count()
    assert total > 0 and vis() == total
    dash = gpage.evaluate("[...document.querySelectorAll('#rows path.ln:not(.pd)')].map(p => getComputedStyle(p).strokeDasharray)")
    assert all(d in ("none", "") for d in dash), dash
    assert gpage.locator("#arrows").count() == 0 and gpage.locator("#lgFlow").count() == 0
    assert "설계 단계" not in gpage.evaluate("document.body.innerText")
    pointer_off_board(gpage)
    assert gpage.evaluate("[...document.querySelectorAll('#rows .alabel')].every(n => getComputedStyle(n).display === 'none')")
    zoom_to(gpage, "pt-detail", 300)
    gpage.mouse.wheel(-420, -160)
    gpage.wait_for_timeout(500)
    V3SHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(V3SHOTS / "p1-e-base.png"))
    zoom_to(gpage, "pass", 300)
    shift_click(gpage, "pass")
    gpage.wait_for_function("!document.getElementById('legend').hidden", timeout=5000)
    assert gpage.evaluate("document.getElementById('rows').classList.contains('focusing')")
    pointer_off_board(gpage)
    gpage.wait_for_timeout(250)
    assert vis() == total
    ops = gpage.evaluate("[...document.querySelectorAll('#rows path.ln:not(.on):not(.pd)')].map(p => +getComputedStyle(p).strokeOpacity)")
    assert ops and all(abs(o - 0.18) < 0.01 for o in ops), ops
    gpage.keyboard.press("Escape")
    gpage.keyboard.press("Escape")


HEADS_JS = """() => [...document.querySelectorAll('#rows path.ln')].flatMap(p => ['marker-end', 'marker-start'].filter(a => p.getAttribute(a)).map(a => {
    const id = p.getAttribute(a).match(/#([^)]+)/)[1], h = document.querySelector('#' + id + ' path');
    return [p.dataset.from + '>' + p.dataset.to, +(+getComputedStyle(p).strokeOpacity).toFixed(3), +(+getComputedStyle(h).fillOpacity).toFixed(3), p.style.opacity || '']; }))"""


@pytest.mark.area("flow", "links")
def test_v3_arrowheads_fade_with_line(gpage):
    """#286: 화살촉(채운 marker)의 투명도 = 그 선의 stroke-opacity — 평소 · 카드에 올림(나머지 흐리게) · 고름(나머지 .18). 선에 opacity 는 없다(래스터 그대로)."""
    gpage.keyboard.press("Escape")
    pointer_off_board(gpage)
    gpage.wait_for_timeout(200)

    def same(state):
        hs = gpage.evaluate(HEADS_JS)
        assert hs, state
        bad = [h for h in hs if abs(h[1] - h[2]) > 0.01 or h[3]]
        assert not bad, (state, bad)
        return hs
    base = same("평소")
    zoom_to(gpage, "pass", 300)                        # 마지막 move = 카드 밖 → 올린 카드 없음
    b = gpage.locator('.card[data-id="pass"] .phone').bounding_box()
    gpage.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    gpage.wait_for_function("document.getElementById('rows').classList.contains('lnhov')", timeout=3000)
    hov = same("올림")
    assert len({h[2] for h in hov}) > 1, ("올린 카드 선은 진하고 나머지는 흐리다", hov)
    pointer_off_board(gpage)
    shift_click(gpage, "pass")
    gpage.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
    pointer_off_board(gpage)
    gpage.wait_for_timeout(200)
    foc = same("고름")
    assert any(abs(h[2] - 0.18) < 0.01 for h in foc) and any(h[2] == 1 for h in foc), foc
    gpage.keyboard.press("Escape")
    gpage.keyboard.press("Escape")
    pointer_off_board(gpage)
    gpage.wait_for_timeout(200)
    assert same("다시 평소") and len(base) == len(same("다시 평소"))


# ---------------------------------------------------------------- canvas-v3 (phase 2): Ctrl+클릭 카메라 · 전환 메뉴 · 선 색/굵기
CAM_DONE = "window.__hdCam && !window.__hdCam.running"
OFFSET_JS = """(id) => { const r = document.querySelector('.card[data-id="' + id + '"] .phone').getBoundingClientRect(),
    p = document.getElementById('screens').getBoundingClientRect();
    return [r.left + r.width / 2 - (p.left + p.width / 2), r.top + r.height / 2 - (p.top + p.height / 2)]; }"""


def ctrl_click_link(pg, sid, text):
    """카드 안 링크 요소 자리를 Ctrl+클릭(카드 위 덮개가 받는다)."""
    b = pg.frame_locator(f'.card[data-id="{sid}"] .phone iframe').locator("a", has_text=text).first.bounding_box()
    pg.keyboard.down("Control")
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    pg.keyboard.up("Control")


def centred(pg, sid, tol=8):
    dx, dy = pg.evaluate(OFFSET_JS, sid)
    return abs(dx) <= tol and abs(dy) <= tol


@pytest.mark.area("motion")
def test_v3_ctrl_click_camera(gpage, gym_out):
    """S4: 카드 안 링크 Ctrl+클릭 → 화면은 이동하지 않고, 카메라가 대상 카드 가운데로(8px) · 그 쌍의 선만 강조. 연결 패널 줄 Ctrl+클릭도. Esc 는 바로 멈춤."""
    want = link_targets(gym_out, "pass")
    gpage.keyboard.press("Escape")
    zoom_to(gpage, "pass", 380)
    frame_url = lambda: gpage.frame_locator('.card[data-id="pass"] .phone iframe').locator("body").evaluate("() => location.href")
    url0 = frame_url()
    ctrl_click_link(gpage, "pass", "일시정지 신청")
    gpage.wait_for_function("window.__hdCam && window.__hdCam.running", timeout=3000)
    gpage.wait_for_timeout(420)
    V3SHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(V3SHOTS / "p2-b-mid.png"))
    gpage.wait_for_function(CAM_DONE, timeout=4000)
    assert gpage.evaluate("window.__hdCam.to") == "pause"
    gpage.wait_for_timeout(120)
    gpage.screenshot(path=str(V3SHOTS / "p2-c-end.png"))
    assert centred(gpage, "pause"), gpage.evaluate(OFFSET_JS, "pause")
    assert frame_url() == url0, "Ctrl+클릭은 화면을 이동시키지 않는다"
    assert gpage.evaluate("document.querySelector('.card[data-id=\"pause\"]').classList.contains('pulse')")
    on = gpage.evaluate("[...document.querySelectorAll('#rows path.ln.on')].map(p => [p.dataset.from, p.dataset.to].sort().join('|'))")
    assert on == ["|".join(sorted(["pass", "pause"]))], ("고른 카드가 없으면 그 쌍의 선 하나만", on)
    # 연결 패널 줄 Ctrl+클릭: 그 도착으로
    zoom_to(gpage, "pass", 380)
    shift_click(gpage, "pass")
    gpage.wait_for_function("!document.getElementById('legend').hidden", timeout=5000)
    gpage.locator('#lgRows .lgrow[data-to="renew"] .lgtx').click(modifiers=["Control"])
    gpage.wait_for_function(CAM_DONE + " && window.__hdCam.to === 'renew'", timeout=4000)
    assert centred(gpage, "renew")
    # Esc 중간에 → 그 자리에서 멈춤
    gpage.locator(f'#lgRows .lgrow[data-to="{want[0]}"] .lgtx').click(modifiers=["Control"])
    gpage.wait_for_timeout(200)
    gpage.keyboard.press("Escape")
    v0 = gpage.evaluate("HDCanvas.view()")
    gpage.wait_for_timeout(300)
    assert gpage.evaluate("window.__hdCam.running") is False and gpage.evaluate("HDCanvas.view()") == v0
    assert not centred(gpage, want[0])


@pytest.mark.area("motion")
def test_v3_reduced_motion_jumps(gpage):
    """S4: prefers-reduced-motion: reduce → 카메라는 끝 상태로 바로."""
    gpage.emulate_media(reduced_motion="reduce")
    try:
        gpage.keyboard.press("Escape")
        zoom_to(gpage, "pass", 380)
        ctrl_click_link(gpage, "pass", "연장하기")
        gpage.wait_for_function("window.__hdCam && window.__hdCam.to === 'renew'", timeout=3000)
        assert gpage.evaluate("window.__hdCam.keys.length") == 1 and gpage.evaluate("window.__hdCam.running") is False
        assert centred(gpage, "renew")
    finally:
        gpage.emulate_media(reduced_motion="no-preference")
        gpage.keyboard.press("Escape")


@pytest.mark.area("motion", "dock")
def test_v3_reduce_motion(gpage):
    """G4: 전환 메뉴는 없앰 — '움직임 줄이기'는 표시 패널 체크 하나(#mvOff), 새로고침 뒤에도, 카메라는 바로."""
    errs = []
    gpage.on("pageerror", lambda e: errs.append(str(e)))
    gpage.keyboard.press("Escape")
    gpage.click('#dock .dk-tab[data-p="show"]')
    gpage.check("#mvOff")
    assert gpage.evaluate("document.body.classList.contains('nomotion')")
    reload(gpage)
    assert gpage.evaluate("document.body.classList.contains('nomotion') && JSON.parse(localStorage.getItem('hd-canvas-prefs')).motion === false")
    zoom_to(gpage, "pass", 380)
    ctrl_click_link(gpage, "pass", "연장하기")
    gpage.wait_for_function("window.__hdCam && window.__hdCam.to === 'renew'", timeout=3000)
    assert gpage.evaluate("window.__hdCam.keys.length") == 1 and centred(gpage, "renew")
    gpage.keyboard.press("Escape")
    gpage.click('#dock .dk-tab[data-p="show"]')
    assert gpage.is_checked("#mvOff")
    gpage.uncheck("#mvOff")
    assert not gpage.evaluate("document.body.classList.contains('nomotion')")
    assert not errs, errs


STROKES_JS = """() => [...document.querySelectorAll('#rows path.ln:not(.plan)')].map(p => {
    const id = (p.getAttribute('marker-end') || '').match(/#([^)]+)/)[1];
    return [p.dataset.from + '>' + p.dataset.to, p.getAttribute('stroke').toLowerCase(), document.querySelector('#' + id + ' path').getAttribute('fill').toLowerCase(), parseFloat(getComputedStyle(p).strokeWidth)]; })"""


def set_width(pg, w):
    pg.evaluate("(w) => { const i = document.getElementById('lgW'); i.value = String(w); i.dispatchEvent(new Event('input', {bubbles: true})); }", w)


@pytest.mark.area("links")
def test_v3_line_style(gpage):
    """S5·E20: 색 드롭다운(진하게 = 줄 색이 그 팔레트에서) · 랜덤(누를 때마다 다름, 메뉴 그대로) · 밖 클릭 닫기 · 굵기 · 새로고침 유지 · 설명 글 없음."""
    gpage.keyboard.press("Escape")
    deep = [c.lower() for c in gpage.evaluate("HDCanvas.style.PRESETS.deep.c")]
    w0 = {k: w for k, _, _, w in gpage.evaluate(STROKES_JS)}
    gpage.click("#lgDdb")
    gpage.wait_for_selector("#lgDd:not([hidden])")
    gpage.wait_for_timeout(300)
    V3SHOTS.mkdir(parents=True, exist_ok=True)
    gpage.screenshot(path=str(V3SHOTS / "p3-a-dropdown.png"))
    dd, bt = gpage.locator("#lgDd").bounding_box(), gpage.locator("#lgDdb").bounding_box()
    assert dd["y"] >= bt["y"] + bt["height"], "아래로 열림(도크 위쪽)"
    gpage.click('#lgDd button[data-preset="deep"]')
    gpage.wait_for_timeout(250)
    assert gpage.is_hidden("#lgDd")
    st = gpage.evaluate(STROKES_JS)
    assert st and all(s in deep and f == s for _, s, f, _ in st), st
    set_width(gpage, 5)
    st = gpage.evaluate(STROKES_JS)
    assert all(w > w0[k] for k, _, _, w in st), (w0, st)
    gpage.screenshot(path=str(V3SHOTS / "p3-b-deep-width5.png"))
    reload(gpage)
    st2 = gpage.evaluate(STROKES_JS)
    assert [(k, s) for k, s, _, _ in st2] == [(k, s) for k, s, _, _ in st], "새로고침 뒤에도 같은 색"
    assert gpage.evaluate("document.getElementById('lgW').value") == "5", "굵기 설정도 그대로(화면 굵기는 배율 따라 달라진다)"
    # 밖 클릭 → 닫힘
    gpage.click("#lgDdb")
    gpage.wait_for_selector("#lgDd:not([hidden])")
    gpage.mouse.click(5, 300)
    gpage.wait_for_timeout(250)
    assert gpage.is_hidden("#lgDd")
    # 랜덤 두 번 → 색이 다름, 메뉴는 열린 채
    gpage.click("#lgDdb")
    gpage.click('#lgDd button[data-preset="random"]')
    gpage.wait_for_timeout(150)
    r1 = [s for _, s, _, _ in gpage.evaluate(STROKES_JS)]
    assert gpage.is_visible("#lgDd")
    gpage.click('#lgDd button[data-preset="random"]')
    gpage.wait_for_timeout(150)
    r2 = [s for _, s, _, _ in gpage.evaluate(STROKES_JS)]
    assert r1 != r2 and gpage.is_visible("#lgDd")
    # 스타일 줄엔 설명 문장이 없다(요소마다 자기 글 40자 이하)
    long = gpage.evaluate("""() => [...document.querySelectorAll('#lgStyle, #lgStyle *, #lgDd *')]
        .map(e => [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join(' ')).filter(t => t.length > 40)""")
    assert not long, long
    gpage.evaluate("localStorage.removeItem('hd-canvas-prefs')")
    gpage.keyboard.press("Escape")


