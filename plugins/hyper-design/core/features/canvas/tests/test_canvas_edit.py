"""캔버스 편집 기능 (docs/eungshin/canvas-edit-plan-2026-10-19.md) — 단계마다 새 동작을 여기에 더한다."""
import json
import re

import pytest

from test_canvas_v2 import REPO, browser, ctx, out_dir, reload, open_screen  # noqa: F401

ESHOTS = REPO / "tasks" / "4-canvas-edit" / "shots"


@pytest.fixture(scope="module")
def epage(ctx, out_dir):
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


def seed_notes(pg, n):
    """메모 하나를 화면에서 만들고(키를 얻으려고) 그 키에 메모 n개를 채운 뒤 새로고침."""
    sid = pg.evaluate("document.querySelector('#rows .card').dataset.id")
    fr = open_screen(pg, sid)
    pg.click("#mpick")
    pg.wait_for_timeout(150)
    fr.locator("h1, h2, button, a").filter(has_text=re.compile(r"\S")).first.click()
    pg.wait_for_selector("#pop:not([hidden])")
    pg.fill("#pnote", "씨앗")
    pg.click("#padd")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    key = pg.evaluate("Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))")
    one = json.loads(pg.evaluate("(k) => localStorage.getItem(k)", key))[0]
    many = [dict(one, id=f"{one['id']}-{i}", note=f"메모 {i + 1} — 긴 목록에서도 끝까지 내려 볼 수 있어야 한다") for i in range(n)]
    pg.evaluate("([k, v]) => localStorage.setItem(k, v)", [key, json.dumps(many, ensure_ascii=False)])
    reload(pg)
    return key


# ---------------------------------------------------------------- 1단계: 메모 패널 드롭다운 + 긴 목록 스크롤
def test_notes_dropdown_scrolls_and_collapses(epage):
    key = seed_notes(epage, 18)
    epage.wait_for_selector("#notes:not([hidden])")
    assert epage.get_attribute("#ntoggle", "aria-expanded") == "true"
    vh = epage.viewport_size["height"]
    pb = epage.locator("#notes").bounding_box()
    assert pb["height"] <= vh * 0.6 + 1, ("메모가 많아도 패널은 화면의 60% 안", pb["height"])
    lst = epage.locator("#nlist")
    assert epage.evaluate("(() => { const l = document.getElementById('nlist'); return l.scrollHeight > l.clientHeight + 20; })()")
    cam0 = epage.evaluate("document.getElementById('stage').style.transform")
    lb = lst.bounding_box()
    epage.mouse.move(lb["x"] + lb["width"] / 2, lb["y"] + lb["height"] / 2)
    for _ in range(30):
        epage.mouse.wheel(0, 400)
    epage.wait_for_timeout(200)
    at_end = epage.evaluate("(() => { const l = document.getElementById('nlist'); return l.scrollTop + l.clientHeight >= l.scrollHeight - 2; })()")
    assert at_end, "휠로 목록 끝까지 내려간다"
    assert epage.evaluate("document.getElementById('stage').style.transform") == cam0, "목록 위 휠은 판을 움직이지 않는다"
    assert epage.locator("#nsend").is_visible()
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "1-notes-open-scrolled.png"))

    epage.click("#ntoggle")
    assert epage.get_attribute("#ntoggle", "aria-expanded") == "false"
    assert not lst.is_visible()
    assert epage.locator("#nsend").is_visible(), "접어도 보내기는 남는다"
    assert "18" in epage.text_content("#ncount")
    assert epage.locator("#notes").bounding_box()["height"] < 140
    epage.wait_for_timeout(250)
    epage.screenshot(path=str(ESHOTS / "1-notes-collapsed.png"))
    reload(epage)
    assert epage.get_attribute("#ntoggle", "aria-expanded") == "false", "접힌 상태가 새로고침 뒤에도"
    assert epage.evaluate("Object.keys(localStorage).some(k => k.startsWith('hd-canvas-prefs') && localStorage.getItem(k).includes('notes'))") is False, "prefs 에 넣지 않는다(normalize 가 버림)"
    epage.click("#ntoggle")
    assert epage.get_attribute("#ntoggle", "aria-expanded") == "true" and lst.is_visible()
    epage.evaluate("(k) => localStorage.removeItem(k)", key)
    reload(epage)


# ---------------------------------------------------------------- 2단계: 도구 막대 · V 로 카드 옮기기 (4B · 6A)
def visible_cover(pg, skip=()):
    p = pg.evaluate("""(skip) => { const r = document.getElementById('screens').getBoundingClientRect();
        for (const c of document.querySelectorAll('#rows .card .cover')) { const id = c.closest('.card').dataset.id; if (skip.includes(id)) continue;
          const b = c.getBoundingClientRect(), x = b.left + b.width / 2, y = b.top + Math.min(b.height / 2, 80);
          if (x > r.left + 80 && x < r.right - 380 && y > r.top + 10 && y < r.bottom - 60 && document.elementFromPoint(x, y) === c) return {id, x, y}; }
        return null; }""", list(skip))
    assert p, "판 안에 보이는 카드가 없음"
    return p


def card_xy(pg, cid):
    return pg.evaluate("""(id) => { const c = document.querySelector('.card[data-id="' + id + '"]'); return [c.offsetLeft, c.offsetTop]; }""", cid)


def ln_d(pg, cid):
    return pg.evaluate("""(id) => [...document.querySelectorAll('#rows path.ln')].filter(p => p.dataset.from === id || p.dataset.to === id).map(p => p.getAttribute('d'))""", cid)


def tool(pg):
    return pg.evaluate("[...document.querySelectorAll('#tools [data-tool]')].filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.tool)")


def drag(pg, p, dx, dy):
    pg.mouse.move(p["x"], p["y"])
    pg.mouse.down()
    pg.mouse.move(p["x"] + dx, p["y"] + dy, steps=10)
    pg.mouse.up()
    pg.wait_for_timeout(150)


def test_toolbar_default_hand_and_keys(epage):
    epage.click("#fit")
    assert epage.locator("#tools").is_visible()
    assert tool(epage) == ["hand"], "기본 도구 = 손(지금처럼 끌면 화면 이동)"
    epage.keyboard.press("v")
    assert tool(epage) == ["move"]
    epage.keyboard.press("h")
    assert tool(epage) == ["hand"]
    epage.click('#tools [data-tool="move"]')
    assert tool(epage) == ["move"]
    epage.evaluate("() => { const i = document.createElement('input'); i.id = 'hd-t'; document.body.appendChild(i); i.focus(); }")
    epage.keyboard.press("h")
    assert tool(epage) == ["move"], "입력 중에는 도구 키 무시"
    epage.evaluate("document.getElementById('hd-t').remove()")
    tb = epage.locator('#tools [data-tool="move"]').bounding_box()
    cam0 = epage.evaluate("document.getElementById('stage').style.transform")
    drag(epage, {"x": tb["x"] + tb["width"] / 2, "y": tb["y"] + tb["height"] / 2}, 60, 30)
    assert epage.evaluate("document.getElementById('stage').style.transform") == cam0, "도구 막대 위 끌기는 판을 움직이지 않는다"
    epage.keyboard.press("h")


def test_move_tool_moves_card_and_persists(epage):
    epage.click("#fit")
    epage.wait_for_timeout(150)
    z = float(epage.get_attribute("#stage", "data-zoom"))
    p = visible_cover(epage)
    x0, y0 = card_xy(epage, p["id"])
    d0 = ln_d(epage, p["id"])
    cam0 = epage.evaluate("document.getElementById('stage').style.transform")
    # 손(기본)에서는 카드 위 끌기 = 화면 이동, 카드는 그대로
    drag(epage, p, 80, 40)
    assert card_xy(epage, p["id"]) == [x0, y0]
    assert epage.evaluate("document.getElementById('stage').style.transform") != cam0
    epage.click("#fit")
    epage.wait_for_timeout(150)
    p = visible_cover(epage)
    x0, y0 = card_xy(epage, p["id"])
    d0 = ln_d(epage, p["id"])
    cam0 = epage.evaluate("document.getElementById('stage').style.transform")
    epage.keyboard.press("v")
    drag(epage, p, 120, 60)
    x1, y1 = card_xy(epage, p["id"])
    assert abs((x1 - x0) - 120 / z) < 3 and abs((y1 - y0) - 60 / z) < 3, ((x0, y0), (x1, y1), z)
    assert epage.evaluate("document.getElementById('stage').style.transform") == cam0, "이동 도구로 카드를 끌면 판은 그대로"
    assert not epage.evaluate("!document.getElementById('modal').hidden"), "끌기 끝은 크게 보기를 열지 않는다"
    if d0:
        assert ln_d(epage, p["id"]) != d0, "주요 흐름 화살표가 옮긴 카드를 따라온다"
    keys = epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-card-pos:'))")
    assert len(keys) == 1
    assert "pos" not in (epage.evaluate("localStorage.getItem('hd-canvas-prefs')") or ""), "prefs 에 넣지 않는다"
    reload(epage)
    assert card_xy(epage, p["id"]) == [x1, y1], "새로고침 뒤에도 옮긴 자리"
    # 이동 도구에서도 그냥 클릭 = 크게 보기(1A)
    epage.click("#fit")
    epage.wait_for_timeout(150)
    epage.keyboard.press("v")
    q = visible_cover(epage)
    epage.mouse.click(q["x"], q["y"])
    epage.wait_for_function("!document.getElementById('modal').hidden")
    epage.keyboard.press("Escape")
    epage.wait_for_timeout(150)
    epage.keyboard.press("h")


def test_fit_includes_moved_card_and_drops_stale(epage):
    key = epage.evaluate("Object.keys(localStorage).find(k => k.startsWith('hd-card-pos:'))")
    cid = epage.evaluate("document.querySelector('#rows .card').dataset.id")
    epage.evaluate("""([k, id]) => { const o = JSON.parse(localStorage.getItem(k) || '{}');
        o[id] = Object.assign({}, o[id] || {}, {dx: 2600, dy: 900}); o['gone-screen'] = {dx: 10, dy: 10};
        localStorage.setItem(k, JSON.stringify(o)); }""", [key, cid])
    reload(epage)
    o = epage.evaluate("(k) => JSON.parse(localStorage.getItem(k))", key)
    assert "gone-screen" not in o, "없는 화면의 옮긴 거리는 버린다"
    epage.keyboard.press("0")
    epage.wait_for_timeout(250)
    pr = epage.locator("#screens").bounding_box()
    for cid2, l, t, r, b in epage.evaluate("[...document.querySelectorAll('#rows .card .phone')].map(c => { const r = c.getBoundingClientRect(); return [c.closest('.card').dataset.id, r.left, r.top, r.right, r.bottom]; })"):
        assert l >= pr["x"] - 1 and t >= pr["y"] - 1 and r <= pr["x"] + pr["width"] + 1 and b <= pr["y"] + pr["height"] + 1, cid2
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "2-fit-with-moved-card.png"))
    epage.evaluate("(k) => localStorage.removeItem(k)", key)
    reload(epage)


def test_card_drag_has_no_long_tasks(epage):
    epage.click("#fit")
    epage.wait_for_timeout(150)
    epage.evaluate("""() => { window.__lt = 0; try { new PerformanceObserver(l => { window.__lt += l.getEntries().filter(e => e.duration > 50).length; })
        .observe({type: 'longtask', buffered: false}); } catch (e) { window.__lt = -1; } }""")
    epage.keyboard.press("v")
    p = visible_cover(epage)
    epage.mouse.move(p["x"], p["y"])
    epage.mouse.down()
    for i in range(40):
        epage.mouse.move(p["x"] + 4 * i, p["y"] + 2 * i)
    epage.mouse.up()
    epage.wait_for_timeout(200)
    lt = epage.evaluate("window.__lt")
    assert lt <= 2, ("끄는 동안 50ms 넘는 작업", lt)
    epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-card-pos:')).forEach(k => localStorage.removeItem(k))")
    epage.keyboard.press("h")
    reload(epage)


def test_moved_card_paints_above_its_new_neighbours(epage):
    epage.click("#fit")
    epage.wait_for_timeout(150)
    epage.keyboard.press("v")
    p = visible_cover(epage)
    others = epage.evaluate("""(id) => [...document.querySelectorAll('#rows .card')].filter(c => c.dataset.id !== id).map(c => { const b = c.querySelector('.phone').getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; })""", p["id"])
    tgt = next(o for o in others if abs(o[1] - p["y"]) > 50)        # 다른 줄의 카드 위로 놓는다
    me = epage.locator(f'.card[data-id="{p["id"]}"] .phone').bounding_box()
    drag(epage, p, tgt[0] + tgt[2] / 2 - (me["x"] + me["width"] / 2), tgt[1] + tgt[3] / 2 - (me["y"] + me["height"] / 2))
    mb = epage.locator(f'.card[data-id="{p["id"]}"] .phone').bounding_box()
    hit = epage.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return e && e.closest('.card') ? e.closest('.card').dataset.id : null; }",
                         [mb["x"] + mb["width"] / 2, mb["y"] + mb["height"] / 2])
    assert hit == p["id"], ("놓은 카드가 그 자리 카드 밑으로 들어가면 안 된다", hit)
    epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-card-pos:')).forEach(k => localStorage.removeItem(k))")
    epage.keyboard.press("h")
    reload(epage)


# ---------------------------------------------------------------- 3단계: 직선 우선 · 위계 · 태그 자리 · 태그 이름 (Dayfine 온보딩 고정본)
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"


@pytest.fixture(scope="module")
def dpage(ctx):
    import os, shutil, subprocess, sys, tempfile
    from pathlib import Path
    from test_canvas_v2 import SCRIPTS
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-dayfine-"))
    out = tmp / "out"
    shutil.copytree(DAYFINE, out)
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


SHIFT_CLICK = """(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, shiftKey: true}))"""


def focus_dayfine(pg, sid):
    from test_canvas_v2 import zoom_to
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(150)
    zoom_to(pg, sid, 330)
    pg.evaluate(SHIFT_CLICK, sid)
    pg.wait_for_function("document.querySelectorAll('#lks path.lk').length >= 1", timeout=5000)
    for _ in range(10):
        if "전체" in (pg.text_content("#lgTitle") or ""):
            break
        pg.evaluate(SHIFT_CLICK, sid)
        pg.wait_for_timeout(250)
    pg.wait_for_timeout(700)


def paths(pg):
    return pg.evaluate("""[...document.querySelectorAll('#lks path.lk')].map(p => ({k: +p.dataset.k, to: p.dataset.to, pts: JSON.parse(p.dataset.pts),
        bk: p.classList.contains('bk'), op: +getComputedStyle(p).opacity}))""")


def phone_boxes(pg):
    return pg.evaluate("""[...document.querySelectorAll('#rows .card .phone')].map(p => { const r = p.getBoundingClientRect();
        return [p.closest('.card').dataset.id, r.left, r.top, r.right, r.bottom]; })""")


TAGS_JS = """[...document.querySelectorAll('#lkl .ltag')].map(n => { const r = n.getBoundingClientRect();
    return {k: +n.dataset.k, float: n.classList.contains('float'), vis: getComputedStyle(n).visibility, box: [r.left, r.top, r.right, r.bottom]}; })"""


def test_straight_neighbour_back_faint_and_under_cards(dpage):
    focus_dayfine(dpage, "job")
    ps = {p["to"]: p for p in paths(dpage)}
    nxt = ps["language"]
    lang_x = dpage.evaluate("""document.querySelector('.card[data-id="language"]').offsetLeft""")
    pts = nxt["pts"]
    assert len(pts) == 2 and abs(pts[0][1] - pts[1][1]) < 0.01 and abs(pts[1][0] - lang_x) < 1, ("바로 옆 화면은 꺾임 없이 옆면으로", pts)
    back = [p for p in ps.values() if p["bk"]]
    assert back and all(p["to"] in ("login", "login--done") for p in back), list(ps)
    assert all(p["op"] < 0.6 for p in back) and nxt["op"] == 1 and not nxt["bk"], "앞 화면으로 가는 연결은 흐리게"
    assert dpage.evaluate("getComputedStyle(document.getElementById('lks')).zIndex") == "-1"
    # 출발 카드 안을 지나는 선 구간은 카드에 가려진다(그 자리의 맨 위는 카드)
    x0, y0 = pts[0]
    hit = dpage.evaluate("""([x, y]) => { const s = document.getElementById('stage').getBoundingClientRect(), z = +document.getElementById('stage').dataset.zoom,
        r = document.getElementById('rows'); const px = s.left + (r.offsetLeft + x - 6) * z, py = s.top + (r.offsetTop + y) * z;
        const e = document.elementFromPoint(px, py); return e && e.closest('.card') ? e.closest('.card').dataset.id : (e && e.tagName); }""", [x0, y0])
    assert hit == "job", hit
    ESHOTS.mkdir(parents=True, exist_ok=True)
    dpage.screenshot(path=str(ESHOTS / "3-after-job.png"))


def test_tags_never_on_cards_and_float_on_hover(dpage):
    focus_dayfine(dpage, "job")
    boxes = phone_boxes(dpage)
    tags = dpage.evaluate(TAGS_JS)
    assert dpage.evaluate("document.querySelectorAll('#lgRows .lgrow[data-k]').length") == len(tags), "범례엔 연결마다 한 줄(태그가 떠 있어도)"

    def on_card(b):
        return [i for i, l, t, r, bt in boxes if b[0] < r and l < b[2] and b[1] < bt and t < b[3]]
    for t in tags:
        if t["vis"] == "visible":
            assert not on_card(t["box"]), ("보이는 태그는 카드 위에 놓이지 않는다", t, on_card(t["box"]))
    fl = [t for t in tags if t["float"]]
    assert fl and all(t["vis"] == "hidden" for t in fl), "곧은 선 위 자리 없는 태그는 평소 숨김"
    k = fl[0]["k"]
    dpage.locator(f'#lgRows .lgrow[data-k="{k}"]').hover()
    dpage.wait_for_timeout(200)
    t = [x for x in dpage.evaluate(TAGS_JS) if x["k"] == k][0]
    assert t["vis"] == "visible" and not on_card(t["box"]), ("마우스 올리면 보이고, 그때도 카드 밖", t)
    dpage.screenshot(path=str(ESHOTS / "3-after-job-hover-tag.png"))
    dpage.mouse.move(5, 300)


def bring_into_view(pg, sel):
    """휠로 판을 옮겨 그 요소를 판 가운데로(Ctrl 없이 = 이동)."""
    r = pg.locator(sel).bounding_box()
    pr = pg.locator("#screens").bounding_box()
    pg.mouse.move(pr["x"] + 400, pr["y"] + 300)
    pg.mouse.wheel(r["x"] + r["width"] / 2 - (pr["x"] + pr["width"] / 2), r["y"] + r["height"] / 2 - (pr["y"] + pr["height"] / 2))
    pg.wait_for_timeout(250)


def test_tag_rename_keeps_button_text(dpage):
    focus_dayfine(dpage, "job")
    on = dpage.evaluate("[...document.querySelectorAll('#lkl .ltag.on')].map(n => [+n.dataset.k, n.dataset.to, n.textContent])")
    k, to, old = on[0]
    legend0 = dpage.text_content(f'#lgRows .lgrow[data-k="{k}"]')
    frame = dpage.frame_locator('.card[data-id="job"] .phone iframe')
    btn0 = frame.locator("body").inner_text()
    bring_into_view(dpage, f'#lkl .ltag[data-k="{k}"]')
    dpage.dblclick(f'#lkl .ltag[data-k="{k}"]')
    inp = dpage.locator(f'#lkl .ltag[data-k="{k}"] input')
    inp.fill("처음 화면으로")
    inp.press("Enter")
    dpage.wait_for_timeout(200)
    assert dpage.text_content(f'#lkl .ltag[data-k="{k}"]') == "처음 화면으로"
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "이름 바꾸기가 연결 보기를 끄지 않는다"
    assert dpage.text_content(f'#lgRows .lgrow[data-k="{k}"]') == legend0, "범례(버튼 글)는 그대로"
    assert frame.locator("body").inner_text() == btn0, "화면 안 버튼 글은 그대로"
    keys = dpage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-link-names:'))")
    assert len(keys) == 1 and "처음 화면으로" in dpage.evaluate("(k) => localStorage.getItem(k)", keys[0])
    assert "처음 화면으로" not in (dpage.evaluate("localStorage.getItem('hd-canvas-prefs')") or "")
    reload(dpage)
    focus_dayfine(dpage, "job")
    assert dpage.text_content(f'#lkl .ltag[data-to="{to}"]') == "처음 화면으로", "새로고침 뒤에도"
    bring_into_view(dpage, f'#lkl .ltag[data-to="{to}"]')
    # Esc = 취소(연결 보기는 그대로), 비우고 Enter = 버튼 글로 돌아감
    dpage.dblclick(f'#lkl .ltag[data-to="{to}"]')
    dpage.locator(f'#lkl .ltag[data-to="{to}"] input').fill("버릴 이름")
    dpage.locator(f'#lkl .ltag[data-to="{to}"] input').press("Escape")
    dpage.wait_for_timeout(150)
    assert dpage.text_content(f'#lkl .ltag[data-to="{to}"]') == "처음 화면으로"
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "입력 중 Esc 는 연결 보기를 끄지 않는다"
    dpage.dblclick(f'#lkl .ltag[data-to="{to}"]')
    dpage.locator(f'#lkl .ltag[data-to="{to}"] input').fill("")
    dpage.locator(f'#lkl .ltag[data-to="{to}"] input').press("Enter")
    dpage.wait_for_timeout(150)
    assert dpage.text_content(f'#lkl .ltag[data-to="{to}"]') == old
    dpage.keyboard.press("Escape")
