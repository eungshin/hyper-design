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
    # 이동 도구에서도 두 번 누르기 = 크게 보기(재작업 S3)
    epage.click("#fit")
    epage.wait_for_timeout(150)
    epage.keyboard.press("v")
    q = visible_cover(epage)
    epage.mouse.dblclick(q["x"], q["y"])
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
    assert len(pts) == 2 and abs(pts[0][1] - pts[1][1]) < 0.01 and abs(pts[1][0] - (lang_x - 10)) < 1, ("바로 옆 화면은 꺾임 없이 옆면 10px 앞까지", pts)
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


def test_tags_never_on_cards_gap_tag_ellipsis_then_full(dpage):
    """곧은 선의 태그: 카드 사이 틈 칸 안, 선 바로 위 · 틈보다 길면 말줄임 · 마우스 올리면 전체 글자(맨 위) · 범례엔 늘."""
    focus_dayfine(dpage, "job")
    boxes = phone_boxes(dpage)
    tags = dpage.evaluate(TAGS_JS)
    assert dpage.evaluate("document.querySelectorAll('#lgRows .lgrow[data-k]').length") == len(tags), "범례엔 연결마다 한 줄"

    def on_card(b):
        return [i for i, l, t, r, bt in boxes if b[0] < r - 0.5 and l + 0.5 < b[2] and b[1] < bt and t < b[3]]
    for t in tags:
        if t["vis"] == "visible":
            assert not on_card(t["box"]), ("보이는 태그는 카드 위에 놓이지 않는다", t, on_card(t["box"]))
    k = [p for p in paths(dpage) if p["to"] == "language"][0]["k"]
    t = [x for x in dpage.evaluate(TAGS_JS) if x["k"] == k][0]
    job = [b for b in boxes if b[0] == "job"][0]
    lang = [b for b in boxes if b[0] == "language"][0]
    line_y = dpage.evaluate("""() => { const p = document.querySelector('#lks path.lk[data-to="language"]'); return p.getBoundingClientRect().top; }""")
    assert t["vis"] == "visible" and not t["float"], t
    assert job[3] <= t["box"][0] and t["box"][2] <= lang[1], ("틈 칸 안", t["box"], job, lang)
    assert t["box"][3] <= line_y + 1 and line_y - t["box"][3] < 12, ("선 바로 위", t["box"], line_y)
    clip = dpage.evaluate(f"""(() => {{ const n = document.querySelector('#lkl .ltag[data-k="{k}"]'); return [n.scrollWidth > n.clientWidth + 1, n.textContent]; }})()""")
    assert clip[0], ("'다음으로'는 틈보다 길어 말줄임", clip)
    dpage.locator(f'#lgRows .lgrow[data-k="{k}"]').hover()
    dpage.wait_for_timeout(200)
    full = dpage.evaluate(f"""(() => {{ const n = document.querySelector('#lkl .ltag[data-k="{k}"]'); return [n.scrollWidth <= n.clientWidth + 1, getComputedStyle(n).zIndex, getComputedStyle(n).visibility]; }})()""")
    assert full[0] and full[2] == "visible", ("마우스 올리면 전체 글자", full)
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


# ---------------------------------------------------------------- 4단계: 우클릭 메뉴 · 숨기기 · 되돌리기 50단계
def cmenu_items(pg):
    pg.wait_for_selector("#cmenu:not([hidden])")
    return pg.evaluate("[...document.querySelectorAll('#cmenu button')].map(b => b.childNodes[0].textContent)")


def pick(pg, label):
    pg.locator("#cmenu button", has_text=label).first.click()
    pg.wait_for_timeout(150)


def test_context_menu_by_target(epage):
    from test_canvas_baseline import empty_point
    epage.click("#fit")
    epage.wait_for_timeout(150)
    p = empty_point(epage)
    epage.mouse.click(p["x"], p["y"], button="right")
    assert cmenu_items(epage) == ["여기에 레이아웃", "전체 보기", "100%"], "빈 곳: 여기에 레이아웃 · 전체 보기 · 100% (숨긴 화면이 없으면 그 줄은 없다)"
    pick(epage, "100%")
    assert epage.get_attribute("#stage", "data-zoom") == "1.0000"
    assert epage.evaluate("document.getElementById('cmenu').hidden")
    epage.click("#fit")
    epage.wait_for_timeout(150)
    c = visible_cover(epage)
    title = epage.get_attribute(f'.card[data-id="{c["id"]}"] .cover', "data-title")
    epage.mouse.click(c["x"], c["y"], button="right")
    cmenu_items(epage)
    epage.wait_for_timeout(400)                      # 5단계: 그 자리 요소(hd-hit-at)가 답하면 요소 항목이 위에 붙는다
    assert cmenu_items(epage)[-4:] == ["크게 보기", "주석 달기", "연결 보기", "숨기기"]
    assert epage.text_content("#cmenu .cmh") == title
    assert not epage.evaluate("!document.getElementById('modal').hidden"), "오른쪽 클릭은 크게 보기를 열지 않는다"
    epage.mouse.move(c["x"], c["y"])
    epage.mouse.wheel(0, 100)                        # 휠(판 이동)은 메뉴를 닫는다
    epage.wait_for_timeout(80)
    assert epage.evaluate("document.getElementById('cmenu').hidden")
    epage.click("#fit")
    epage.wait_for_timeout(150)
    c = visible_cover(epage)
    epage.mouse.click(c["x"], c["y"], button="right")
    cmenu_items(epage)
    epage.keyboard.press("Escape")
    assert epage.evaluate("document.getElementById('cmenu').hidden"), "Esc 는 메뉴부터 닫는다"
    epage.mouse.click(c["x"], c["y"], button="right")
    pick(epage, "주석 달기")
    epage.wait_for_function("!document.getElementById('modal').hidden")
    assert epage.get_attribute("#mpick", "aria-pressed") == "true", "메뉴의 주석 달기 = 주석 버튼과 같다"
    epage.keyboard.press("Escape")
    epage.wait_for_timeout(150)
    if epage.evaluate("!document.getElementById('modal').hidden"):
        epage.keyboard.press("Escape")
        epage.wait_for_timeout(150)


def test_hide_screen_and_hidden_list(epage):
    from test_canvas_baseline import empty_point
    epage.click("#fit")
    epage.wait_for_timeout(150)
    c = visible_cover(epage)
    sid = c["id"]
    assert not epage.locator("#thid").is_visible(), "숨긴 화면이 없으면 목록 버튼도 없다"
    epage.mouse.click(c["x"], c["y"], button="right")
    pick(epage, "숨기기")
    assert not epage.locator(f'.card[data-id="{sid}"]').is_visible()
    assert epage.locator("#thid").is_visible() and epage.text_content("#thidn") == "1"
    assert epage.evaluate("(id) => [...document.querySelectorAll('#rows path.ln')].every(p => p.dataset.from !== id && p.dataset.to !== id)", sid), "숨긴 화면의 흐름 화살표는 그리지 않는다"
    keys = epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-hidden:'))")
    assert len(keys) == 1 and sid in epage.evaluate("(k) => localStorage.getItem(k)", keys[0])
    assert sid not in (epage.evaluate("localStorage.getItem('hd-canvas-prefs')") or ""), "prefs 에 넣지 않는다"
    reload(epage)
    assert not epage.locator(f'.card[data-id="{sid}"]').is_visible(), "새로고침 뒤에도 숨김"
    epage.keyboard.press("0")
    epage.wait_for_timeout(150)
    p = empty_point(epage)
    epage.mouse.click(p["x"], p["y"], button="right")
    assert cmenu_items(epage)[-1] == "숨긴 화면 1개"
    pick(epage, "숨긴 화면 1개")
    assert epage.locator("#hidl").is_visible()
    title = epage.get_attribute(f'.card[data-id="{sid}"] .cover', "data-title")
    assert title in epage.text_content("#hidl")
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "4-hidden-list.png"))
    epage.locator(f'#hidl .hrow[data-id="{sid}"] button').click()
    epage.wait_for_timeout(150)
    assert epage.locator(f'.card[data-id="{sid}"]').is_visible()
    assert not epage.locator("#thid").is_visible() and not epage.locator("#hidl").is_visible()
    assert epage.evaluate("(k) => localStorage.getItem(k)", keys[0]) == "[]"


def test_undo_redo_card_moves_capped_at_50(epage):
    reload(epage)                                    # 되돌리기 기록은 새로고침하면 비어 있다
    epage.click("#fit")
    epage.wait_for_timeout(150)
    assert epage.is_disabled("#undo") and epage.is_disabled("#redo")
    z = float(epage.get_attribute("#stage", "data-zoom"))
    epage.keyboard.press("v")
    p = visible_cover(epage)
    x0, _ = card_xy(epage, p["id"])
    for i in range(51):                              # 오른쪽·왼쪽 번갈아 51번 → 홀수 번째 뒤 = x0 + 30/z, 짝수 번째 뒤 = x0
        sx = p["x"] + (30 if i % 2 else 0)
        epage.mouse.move(sx, p["y"])
        epage.mouse.down()
        epage.mouse.move(sx + (-30 if i % 2 else 30), p["y"], steps=3)
        epage.mouse.up()
    epage.wait_for_timeout(150)
    assert abs(card_xy(epage, p["id"])[0] - (x0 + 30 / z)) < 3
    assert not epage.is_disabled("#undo")
    assert "카드 옮기기" in epage.get_attribute("#undo", "title")
    for _ in range(60):
        epage.keyboard.press("Control+z")
    epage.wait_for_timeout(150)
    assert epage.is_disabled("#undo") and not epage.is_disabled("#redo"), "50단계까지만 기억한다"
    assert abs(card_xy(epage, p["id"])[0] - (x0 + 30 / z)) < 3, "가장 오래된 1단계는 버려져 첫 번째 옮김 뒤 자리에서 멈춘다"
    epage.keyboard.press("Control+Shift+z")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - x0) < 3
    epage.keyboard.press("Control+y")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - (x0 + 30 / z)) < 3
    epage.click("#undo")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - x0) < 3, "위쪽 막대 ↶ 버튼도 같다"
    stored = epage.evaluate("Object.values(JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-card-pos:'))) || '{}'))")
    assert all(abs(s["dx"]) < 3 for s in stored), "되돌린 자리가 저장된다"
    epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-card-pos:')).forEach(k => localStorage.removeItem(k))")
    epage.keyboard.press("h")
    reload(epage)


def test_link_menu_rename_undo_and_go(dpage):
    focus_dayfine(dpage, "job")
    k, to, old = dpage.evaluate("[...document.querySelectorAll('#lkl .ltag.on')].map(n => [+n.dataset.k, n.dataset.to, n.textContent])")[0]
    sel = f'#lkl .ltag[data-k="{k}"]'
    bring_into_view(dpage, sel)
    dpage.click(sel, button="right")
    assert cmenu_items(dpage) == ["이름 고치기", "도착으로 가기", "도착 바꾸기", "끊기"]
    assert dpage.text_content("#cmenu .cmh").startswith("연결 →")
    pick(dpage, "이름 고치기")
    inp = dpage.locator(f"{sel} input")
    assert inp.is_visible()
    inp.fill("맥락 이름")
    inp.press("Enter")
    dpage.wait_for_timeout(150)
    assert dpage.text_content(sel) == "맥락 이름"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(150)
    assert dpage.text_content(sel) == old, "되돌리면 버튼 글로"
    assert "맥락 이름" not in (dpage.evaluate("localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-link-names:')))") or "")
    dpage.keyboard.press("Control+Shift+z")
    dpage.wait_for_timeout(150)
    assert dpage.text_content(sel) == "맥락 이름"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(150)
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "되돌리기는 연결 보기를 끄지 않는다"
    bring_into_view(dpage, sel)
    dpage.click(sel, button="right")
    pick(dpage, "도착으로 가기")
    dpage.wait_for_function("(to) => window.__hdCam && window.__hdCam.to === to", arg=to)
    dpage.keyboard.press("Escape")


# ---------------------------------------------------------------- 5단계: 트리거(L) · 소켓 끌기 · 자르기(C·오른쪽 끌기) · hd-hit-at
# 화면 파일을 바꾸는 편집은 메모(intent=change)로 쌓인다 — 보내기 요청문 형식은 그대로(contract.md)
NOTES_JS = "JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]')"


def notes_of(pg):
    return pg.evaluate(NOTES_JS)


def wait_notes(pg, n):
    pg.wait_for_function(f"({NOTES_JS}).length === {n}", timeout=4000)


def fit_view(pg):
    pg.keyboard.press("Escape")
    pg.keyboard.press("0")
    pg.wait_for_timeout(200)


def test_trigger_drag_to_card_adds_link_note_and_undo(dpage):
    from test_canvas_baseline import empty_point
    fit_view(dpage)
    dpage.keyboard.press("l")
    assert tool(dpage) == ["trigger"]
    n0 = len(notes_of(dpage))
    p = visible_cover(dpage)
    q = visible_cover(dpage, skip=[p["id"]])
    drag(dpage, p, q["x"] - p["x"], q["y"] - p["y"])
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == p["id"] and n["intent"] == "change" and q["id"] in n["note"], n
    assert dpage.locator("#notes").is_visible()
    assert "트리거" in dpage.get_attribute("#undo", "title")
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("Control+Shift+z")
    wait_notes(dpage, n0 + 1)
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    e = empty_point(dpage)
    drag(dpage, p, e["x"] - p["x"], e["y"] - p["y"])
    items = cmenu_items(dpage)
    assert items[0] == "새 화면 만들고 잇기" and items[-1] == "취소", items
    pick(dpage, "취소")
    assert len(notes_of(dpage)) == n0, "취소는 아무것도 남기지 않는다"
    dpage.keyboard.press("h")


def test_knife_right_drag_cuts_link_into_note(dpage):
    focus_dayfine(dpage, "job")
    n0 = len(notes_of(dpage))
    lk = paths(dpage)[0]
    (x0, y0), (x1, y1) = lk["pts"][0], lk["pts"][1]
    sx, sy = dpage.evaluate("""([x, y]) => { const r = document.getElementById('lks').getBoundingClientRect(),
        z = +document.getElementById('stage').dataset.zoom; return [r.left + x * z, r.top + y * z]; }""", [(x0 + x1) / 2, (y0 + y1) / 2])
    dpage.mouse.move(sx - 12, sy - 12)
    dpage.mouse.down(button="right")
    dpage.mouse.move(sx + 12, sy + 12, steps=6)
    dpage.mouse.up(button="right")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and "연결 끊기" in n["note"] and lk["to"] in n["note"], n
    assert dpage.evaluate("document.getElementById('cmenu').hidden"), "오른쪽 끌기 뒤에는 메뉴를 띄우지 않는다"
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("c")
    assert tool(dpage) == ["knife"]
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


def test_trigger_tool_shows_sockets_and_socket_drag_changes_target(dpage):
    focus_dayfine(dpage, "job")
    assert dpage.evaluate("[...document.querySelectorAll('.sock')].every(s => getComputedStyle(s).display === 'none')"), "손 도구에서는 소켓을 숨긴다"
    dpage.keyboard.press("l")
    socks = dpage.evaluate("""[...document.querySelectorAll('.sock')].filter(s => getComputedStyle(s).display !== 'none').map(s => {
        const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, to: s.dataset.to}; })""")
    assert socks, "트리거 도구에서 연결 출발 요소마다 소켓"
    w = dpage.evaluate("document.querySelector('.sock').getBoundingClientRect().width")
    assert 10 <= w <= 16, ("소켓은 판 배율과 상관없이 화면에서 12px 안팎", w)
    s = socks[0]
    n0 = len(notes_of(dpage))
    q = visible_cover(dpage, skip=["job", s["to"]])
    drag(dpage, s, q["x"] - s["x"], q["y"] - s["y"])
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and "도착 바꾸기" in n["note"] and q["id"] in n["note"], n
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


def test_element_menu_via_hit_at(dpage):
    fit_view(dpage)
    c = visible_cover(dpage)
    dpage.mouse.click(c["x"], c["y"], button="right")
    dpage.wait_for_function("[...document.querySelectorAll('#cmenu button')].some(b => /트리거/.test(b.textContent))", timeout=3000)
    items = cmenu_items(dpage)
    assert ("트리거 지정" in items or "트리거 해제" in items) and "크게 보기" in items, items
    assert items.index("크게 보기") > 0, "요소 항목이 먼저, 카드 항목이 뒤"
    dpage.keyboard.press("Escape")


def test_hit_at_without_palette_says_cannot_edit(dpage):
    fit_view(dpage)
    p = visible_cover(dpage)
    q = visible_cover(dpage, skip=[p["id"]])
    dpage.evaluate("""(id) => { const f = document.querySelector('.card[data-id="' + id + '"] iframe');
        f.removeAttribute('data-src'); f.removeAttribute('src'); f.srcdoc = '<p>palette 없음</p>'; }""", p["id"])
    dpage.wait_for_timeout(300)
    n0 = len(notes_of(dpage))
    dpage.keyboard.press("l")
    drag(dpage, p, q["x"] - p["x"], q["y"] - p["y"])
    dpage.wait_for_function("(document.getElementById('toast') || {}).textContent === '이 화면은 편집할 수 없어요'", timeout=3000)
    assert len(notes_of(dpage)) == n0
    dpage.keyboard.press("h")
    reload(dpage)


# ---------------------------------------------------------------- 6단계: 더블클릭 고치기 → 요청문 · 반영 대기 표시 · 닫기 전 확인
def unsent_guard(pg):
    """닫기 전 확인이 걸려 있나 — 실제 대화 상자 없이 beforeunload 를 흉내 낸다."""
    return pg.evaluate("(() => { const e = new Event('beforeunload', {cancelable: true}); dispatchEvent(e); return e.defaultPrevented; })()")


def test_dblclick_title_and_desc_queue_pending_edits(dpage):
    dpage.on("dialog", lambda d: d.accept())         # 새로고침 전 확인 창은 받아들인다
    fit_view(dpage)
    zoom_to = __import__("test_canvas_v2").zoom_to
    zoom_to(dpage, "job", 200)
    t_sel, d_sel = '.card[data-id="job"] .ftitle', '.card[data-id="job"] .fdesc'
    bring_into_view(dpage, t_sel)
    old = dpage.text_content(t_sel)
    n0 = len(notes_of(dpage))
    assert not unsent_guard(dpage)
    dpage.dblclick(t_sel)
    inp = dpage.locator(f"{t_sel} input")
    assert inp.is_visible() and inp.input_value() == old
    inp.fill("새 이름")
    inp.press("Enter")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and n["intent"] == "change" and "screens.json" in n["path"] and "새 이름" in n["note"], n
    assert dpage.text_content(t_sel) == "새 이름" and "pend" in dpage.get_attribute(t_sel, "class"), "반영 대기: 새 글을 보여 주고 표시"
    assert unsent_guard(dpage), "보내지 않은 편집이 있으면 닫기 전에 묻는다"
    reload(dpage)
    assert dpage.text_content(t_sel) == "새 이름", "새로고침 뒤에도 반영 대기 표시"
    assert dpage.locator('.card[data-id="job"] .pchip').is_visible()
    dpage.keyboard.press("0")
    zoom_to(dpage, "job", 200)
    bring_into_view(dpage, d_sel)
    dpage.dblclick(d_sel)
    ta = dpage.locator(f"{d_sel} textarea")
    assert ta.is_visible()
    ta.fill("첫 줄")
    ta.press("Shift+Enter")
    ta.type("둘째 줄")
    ta.press("Enter")
    wait_notes(dpage, n0 + 2)
    n = notes_of(dpage)[-1]
    assert "purpose" in n["path"] and "첫 줄\n둘째 줄" in n["note"], n
    assert "둘째 줄" in dpage.text_content(d_sel)
    log = dpage.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-edit-log:'))) || '[]')")
    assert len(log) >= 1, "변경 기록은 별도 키에 남는다"
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0 + 1)
    assert "둘째 줄" not in dpage.text_content(d_sel)
    # 새로고침 앞의 이름 고치기는 되돌리기 기록이 없다(새로고침하면 비어 있다) → 메모를 처음 개수로 잘라 정리
    dpage.evaluate(f"""(() => {{ const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:'));
        localStorage.setItem(k, JSON.stringify(JSON.parse(localStorage.getItem(k)).slice(0, {n0}))); }})()""")
    reload(dpage)
    assert dpage.text_content(t_sel) == old and not unsent_guard(dpage)


def test_dblclick_screen_text_edits_with_preview(dpage):
    fit_view(dpage)
    zoom_to = __import__("test_canvas_v2").zoom_to
    ph = zoom_to(dpage, "job", 420)
    fr = next(f for f in dpage.frames if f.url.split("?")[0].endswith("/job.html"))
    leaf = fr.evaluate("""(() => { for (const el of document.querySelectorAll('h1, h2, p, span, button, a, div')) {
        if (el.children.length || !el.textContent.trim()) continue; const r = el.getBoundingClientRect();
        if (r.width > 20 && r.height > 8 && r.top > 0 && r.top < 500) return {text: el.textContent.trim(), x: r.left + r.width / 2, y: r.top + r.height / 2}; } return null; })()""")
    assert leaf, "글자 요소가 있어야 한다"
    sc = ph["width"] / dpage.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    x, y = ph["x"] + leaf["x"] * sc, ph["y"] + leaf["y"] * sc
    n0 = len(notes_of(dpage))
    dpage.keyboard.press("e")                        # 글자 도구(재작업 S5): 글자 위를 한 번 누르면 그 자리에서 고친다
    dpage.mouse.click(x, y)
    dpage.wait_for_selector("#tedit:not([hidden])", timeout=3000)
    assert dpage.input_value("#tedit textarea") == leaf["text"]
    assert dpage.evaluate("document.getElementById('modal').hidden")
    dpage.fill("#tedit textarea", "바뀐 글자")
    dpage.press("#tedit textarea", "Enter")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and "바뀐 글자" in n["note"] and n["text"].startswith(leaf["text"][:20]), n
    fr.wait_for_function("[...document.querySelectorAll('*')].some(el => !el.children.length && el.textContent.trim() === '바뀐 글자')", timeout=3000)
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    fr.wait_for_function("(t) => [...document.querySelectorAll('*')].some(el => !el.children.length && el.textContent.trim() === t)", arg=leaf["text"], timeout=3000)
    box = fr.evaluate("""(() => { for (const el of document.querySelectorAll('section, main, div')) {   // 자기 글자가 없는 큰 요소의 빈 자리
        const r = el.getBoundingClientRect(); if (r.width < 200 || r.height < 200) continue;
        for (let yy = r.top + 4; yy < Math.min(r.bottom, 600); yy += 6) for (let xx = r.left + 4; xx < r.right; xx += 12)
          if (document.elementFromPoint(xx, yy) === el) return {x: xx, y: yy}; } return null; })()""")
    if box:
        dpage.mouse.click(ph["x"] + box["x"] * sc, ph["y"] + box["y"] * sc)
        dpage.wait_for_function("(document.getElementById('toast') || {}).textContent === '여기에는 고칠 글자가 없어요'", timeout=3000)
        assert dpage.evaluate("document.getElementById('tedit').hidden"), "글자 없는 큰 요소는 고치지 않는다"
    dpage.keyboard.press("h")
    dpage.mouse.dblclick(x, y)                       # 두 번 누르기 = 크게 보기(재작업 S3)
    dpage.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    dpage.keyboard.press("Escape")
    dpage.wait_for_timeout(200)


def test_element_menu_edit_text(dpage):
    fit_view(dpage)
    c = visible_cover(dpage)
    dpage.mouse.click(c["x"], c["y"], button="right")
    dpage.wait_for_function("[...document.querySelectorAll('#cmenu button')].some(b => /글자 고치기/.test(b.textContent))", timeout=3000)
    pick(dpage, "글자 고치기")
    dpage.wait_for_selector("#tedit:not([hidden])", timeout=3000)
    dpage.keyboard.press("Escape")
    assert dpage.evaluate("document.getElementById('tedit').hidden"), "Esc 는 고치기를 취소"


# ---------------------------------------------------------------- 재작업 A: 연결 편집은 캔버스에 바로 보인다(원 세션 검증 10-20)
def lk_to(pg, to):
    return pg.evaluate("(to) => [...document.querySelectorAll('#lks path.lk')].filter(p => p.dataset.to === to).map(p => p.getAttribute('class'))", to)


def test_cut_hides_line_at_once_with_live_mark_and_toast_undo(dpage):
    focus_dayfine(dpage, "job")
    lk = paths(dpage)[0]
    (x0, y0), (x1, y1) = lk["pts"][0], lk["pts"][1]
    sx, sy = dpage.evaluate("""([x, y]) => { const r = document.getElementById('lks').getBoundingClientRect(),
        z = +document.getElementById('stage').dataset.zoom; return [r.left + x * z, r.top + y * z]; }""", [(x0 + x1) / 2, (y0 + y1) / 2])
    dpage.mouse.move(sx - 14, sy - 14)
    dpage.mouse.down(button="right")
    dpage.mouse.move(sx + 14, sy + 14, steps=6)
    assert any("cutting" in c for c in lk_to(dpage, lk["to"])), "끄는 동안 가로지른 선은 바로 빨갛게"
    dpage.mouse.up(button="right")
    dpage.wait_for_timeout(250)
    assert lk_to(dpage, lk["to"]) == [], "놓으면 그 선은 바로 사라진다"
    assert "끊었어요" in dpage.text_content("#toast")
    dpage.click("#toast button")
    dpage.wait_for_timeout(250)
    assert lk_to(dpage, lk["to"]), "토스트의 되돌리기 = 선이 돌아온다"
    dpage.keyboard.press("Escape")


def test_socket_drag_draws_pending_line_at_once(dpage):
    focus_dayfine(dpage, "job")
    dpage.keyboard.press("l")
    s = dpage.evaluate("""(() => { const s = [...document.querySelectorAll('.sock')].find(n => getComputedStyle(n).display !== 'none');
        const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, to: s.dataset.to}; })()""")
    q = visible_cover(dpage, skip=["job", s["to"]])
    drag(dpage, s, q["x"] - s["x"], q["y"] - s["y"])
    dpage.wait_for_timeout(250)
    cls = lk_to(dpage, q["id"])
    assert cls and all("pd" in c for c in cls), ("새 도착으로 가는 선이 바로 반영 대기 모양(점선)으로", cls)
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(250)
    assert lk_to(dpage, q["id"]) == [], "되돌리면 사라진다"
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


# ---------------------------------------------------------------- 재작업 B: 레이아웃 N · 메모 M · 도구 막대 세 묶음 · 여기에 레이아웃
def drafts(pg):
    return pg.evaluate("[...document.querySelectorAll('#rows .card.draft')].map(c => ({id: c.dataset.id, vis: c.offsetWidth > 0}))")


def test_toolbar_has_add_group(dpage):
    tools = dpage.evaluate("[...document.querySelectorAll('#tools [data-tool]')].map(b => b.dataset.tool)")
    assert tools == ["hand", "move", "trigger", "knife", "annotate", "text", "layout", "memo"], tools
    assert dpage.evaluate("document.querySelectorAll('#tools hr').length") >= 2, "도구 / 추가 / 보기 세 묶음"


def test_layout_tool_drops_blank_card_and_undo(dpage):
    from test_canvas_baseline import empty_point
    fit_view(dpage)
    n0 = len(notes_of(dpage))
    dpage.keyboard.press("n")
    assert tool(dpage) == ["layout"]
    e = empty_point(dpage)
    dpage.mouse.click(e["x"], e["y"])
    dpage.wait_for_timeout(200)
    d = drafts(dpage)
    assert len(d) == 1 and d[0]["vis"], d
    box = dpage.locator("#rows .card.draft .phone").bounding_box()
    assert abs(box["x"] - e["x"]) < 6 and abs(box["y"] - e["y"]) < 6, ("누른 자리에 빈 카드", box, e)
    assert tool(dpage) == ["move"], "놓은 뒤 이동 도구로"
    n = notes_of(dpage)[-1]
    assert n["edit"] == "new-screen" and n["screen"] == d[0]["id"] and len(notes_of(dpage)) == n0 + 1
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(200)
    assert drafts(dpage) == [] and len(notes_of(dpage)) == n0
    dpage.keyboard.press("h")


def test_empty_drop_makes_layout_and_links_it(dpage):
    from test_canvas_baseline import empty_point
    focus_dayfine(dpage, "job")
    dpage.keyboard.press("l")
    s = dpage.evaluate("""(() => { const s = [...document.querySelectorAll('.sock')].find(n => getComputedStyle(n).display !== 'none');
        const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()""")
    e = empty_point(dpage)
    drag(dpage, s, e["x"] - s["x"], e["y"] - s["y"])
    assert cmenu_items(dpage)[0] == "새 화면 만들고 잇기"
    pick(dpage, "새 화면 만들고 잇기")
    dpage.wait_for_timeout(300)
    d = drafts(dpage)
    assert len(d) == 1, d
    assert lk_to(dpage, d[0]["id"]), "새 빈 카드로 가는 선이 바로 그려진다"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(250)
    assert drafts(dpage) == [] and lk_to(dpage, d[0]["id"]) == [], "되돌리기 한 번에 카드와 선이 같이"
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


def test_empty_right_click_layout_here(dpage):
    from test_canvas_baseline import empty_point
    fit_view(dpage)
    e = empty_point(dpage)
    dpage.mouse.click(e["x"], e["y"], button="right")
    assert "여기에 레이아웃" in cmenu_items(dpage)
    pick(dpage, "여기에 레이아웃")
    dpage.wait_for_timeout(200)
    assert len(drafts(dpage)) == 1
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(200)
    assert drafts(dpage) == []


def test_memo_tool_opens_card_memo(dpage):
    fit_view(dpage)
    n0 = len(notes_of(dpage))
    dpage.keyboard.press("m")
    assert tool(dpage) == ["memo"]
    c = visible_cover(dpage)
    title = dpage.get_attribute(f'.card[data-id="{c["id"]}"] .cover', "data-title")
    dpage.mouse.click(c["x"], c["y"])
    dpage.wait_for_selector("#pop:not([hidden])")
    assert title in dpage.text_content("#ptitle")
    assert dpage.evaluate("document.getElementById('modal').hidden"), "메모 도구에서는 크게 보기를 열지 않는다"
    dpage.fill("#pnote", "이 화면 전체를 더 밝게")
    dpage.click("#padd")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == c["id"] and n["path"] == "body" and "밝게" in n["note"], n
    dpage.evaluate(f"""(() => {{ const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:'));
        localStorage.setItem(k, JSON.stringify(JSON.parse(localStorage.getItem(k)).slice(0, {n0}))); }})()""")
    dpage.keyboard.press("h")
    reload(dpage)


# ---------------------------------------------------------------- 재작업 S0~S7 (docs/eungshin/canvas-edit-rework-2026-10-20.md)
def test_modal_pins_follow_navigated_screen(dpage):
    """S0 버그: 크게 보기 안에서 다른 화면으로 넘어가면 그 화면의 번호만 보인다."""
    from test_canvas_v2 import open_screen
    n0 = len(notes_of(dpage))
    dpage.evaluate("""() => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:')) ||
        'hd-notes:' + (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
        const a = JSON.parse(localStorage.getItem(k) || '[]');
        a.push({id: 'pin1', screen: 'job', targets: [{path: 'h1.title:nth-of-type(1)', text: 't', rect: {x: 20, y: 20, w: 100, h: 30}}],
                path: 'h1.title:nth-of-type(1)', text: 't', rect: {x: 20, y: 20, w: 100, h: 30}, note: '핀', intent: 'question', sent: false});
        localStorage.setItem(k, JSON.stringify(a)); }""")
    reload(dpage)
    fr = open_screen(dpage, "job")
    assert dpage.locator("#mpins .pin").count() == 1
    fr.locator('a[href="language.html"]').first.click()
    dpage.wait_for_function("document.getElementById('mtitle').textContent.indexOf('언어') >= 0", timeout=5000)
    assert dpage.locator("#mpins .pin").count() == 0, "넘어간 화면에는 앞 화면 번호가 없다"
    dpage.keyboard.press("Escape")
    dpage.wait_for_timeout(200)
    dpage.evaluate(f"""(() => {{ const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:'));
        localStorage.setItem(k, JSON.stringify(JSON.parse(localStorage.getItem(k)).slice(0, {n0}))); }})()""")
    reload(dpage)


def frame_of(pg, sid):
    return next(f for f in pg.frames if f.url.split("?")[0].endswith("/" + sid + ".html"))


def el_point(pg, ph, fr, sel):
    """카드 안 요소 sel 의 가운데 → 화면 좌표."""
    q = fr.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }", sel)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card.w")
    return ph["x"] + q[0] * sc, ph["y"] + q[1] * sc


def elbox(pg):
    return pg.evaluate("""(() => { const b = document.querySelector('.elbox'); if (!b || getComputedStyle(b).display === 'none') return null;
        const r = b.getBoundingClientRect(); return {kind: b.dataset.kind, label: b.dataset.label, x: r.left, y: r.top, w: r.width, h: r.height}; })()""")


def test_element_tools_outline_hovered_element_by_kind(dpage):
    """S2: 트리거 도구에서 카드 안 요소에 마우스를 올리면 종류별 테두리(글자·버튼/링크)."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 420)
    fr = frame_of(dpage, "job")
    dpage.keyboard.press("l")
    x, y = el_point(dpage, ph, fr, "h1")
    dpage.mouse.move(x, y)
    dpage.wait_for_function("document.querySelector('.elbox') && document.querySelector('.elbox').dataset.kind === 'text'", timeout=3000)
    b = elbox(dpage)
    assert b["label"] == "글자" and b["x"] <= x <= b["x"] + b["w"], b
    x, y = el_point(dpage, ph, fr, 'a[href="language.html"]')
    dpage.mouse.move(x, y)
    dpage.wait_for_function("document.querySelector('.elbox') && document.querySelector('.elbox').dataset.kind === 'link'", timeout=3000)
    assert elbox(dpage)["label"].startswith("링크")
    dpage.keyboard.press("h")
    dpage.mouse.move(x + 2, y + 2)
    dpage.wait_for_timeout(200)
    assert elbox(dpage) is None, "손 도구에서는 테두리 없음"


def test_pres_button_and_modal_dblclick_edits_text(dpage):
    """S3: 카드 위 [▶ 보기] = 실제로 눌러 보는 크게 보기. 그 안에서 글자를 두 번 누르면 그 자리에서 고친다."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 420)
    dpage.mouse.move(ph["x"] + ph["width"] / 2, ph["y"] + ph["height"] / 2)
    pres = dpage.locator('.card[data-id="job"] .pres')
    pres.wait_for(state="visible")
    assert "보기" in pres.text_content() and dpage.locator(".anno").count() == 0, "검정 [주석] 버튼은 없어졌다"
    pres.click()
    dpage.wait_for_function("!document.getElementById('modal').hidden")
    assert dpage.get_attribute("#mpick", "aria-pressed") != "true", "보기는 주석 달기를 켜지 않는다"
    fr = dpage.frame_locator("#mframe")
    fr.locator("h1").wait_for()
    dpage.wait_for_timeout(300)
    n0 = len(notes_of(dpage))
    old = fr.locator("h1").text_content().strip()
    fr.locator("h1").dblclick()
    dpage.wait_for_selector("#tedit:not([hidden])", timeout=3000)
    assert dpage.input_value("#tedit textarea") == old
    dpage.fill("#tedit textarea", "크게 보기에서 고침")
    dpage.press("#tedit textarea", "Enter")
    wait_notes(dpage, n0 + 1)
    assert notes_of(dpage)[-1]["screen"] == "job"
    fr.locator("h1", has_text="크게 보기에서 고침").wait_for(timeout=3000)
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("Escape")
    dpage.wait_for_timeout(200)


def test_annotate_tool_notes_an_element_on_the_board(dpage):
    """S4: 주석 도구(P) — 크게 보기 없이 판 위 카드 안 요소를 누르면 그 요소에 메모."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 420)
    fr = frame_of(dpage, "job")
    dpage.keyboard.press("p")
    assert tool(dpage) == ["annotate"]
    n0 = len(notes_of(dpage))
    x, y = el_point(dpage, ph, fr, "h1")
    dpage.mouse.click(x, y)
    dpage.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert dpage.evaluate("document.getElementById('modal').hidden"), "크게 보기를 열지 않는다"
    assert "h1" in dpage.text_content("#ppath")
    dpage.fill("#pnote", "제목을 더 짧게")
    dpage.click("#padd")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and "h1" in n["path"] and n["targets"][0]["rect"], n
    dpage.evaluate(f"""(() => {{ const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:'));
        localStorage.setItem(k, JSON.stringify(JSON.parse(localStorage.getItem(k)).slice(0, {n0}))); }})()""")
    dpage.keyboard.press("h")
    reload(dpage)


def test_text_tool_edits_policy_line(dpage):
    """S5 + 버그 F7: 글자 도구로 카드 아래 정책(•) 줄을 한 번 눌러 고친다 → screens.json policies[i] 메모 · 반영 대기."""
    fit_view(dpage)
    __import__("test_canvas_v2").zoom_to(dpage, "job", 200)
    sel = '.card[data-id="job"] ul.pol li'
    bring_into_view(dpage, sel + ':first-child')
    old = dpage.locator(sel).first.text_content()
    n0 = len(notes_of(dpage))
    dpage.keyboard.press("e")
    dpage.locator(sel).first.click()
    inp = dpage.locator(sel + " input").first
    assert inp.is_visible() and inp.input_value() == old
    inp.fill("새 정책 문장")
    inp.press("Enter")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["edit"] == "policy" and n["index"] == 0 and "policies[0]" in n["path"], n
    assert dpage.locator(sel).first.text_content() == "새 정책 문장" and "pend" in dpage.locator(sel).first.get_attribute("class")
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    assert dpage.locator(sel).first.text_content() == old
    dpage.keyboard.press("h")
