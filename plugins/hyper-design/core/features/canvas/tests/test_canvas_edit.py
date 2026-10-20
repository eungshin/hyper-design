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


# ---------------------------------------------------------------- 메모 패널(오른쪽 도크) + 긴 목록 스크롤
def test_notes_panel_in_dock_scrolls(epage):
    key = seed_notes(epage, 18)
    epage.wait_for_selector("#notes:not([hidden])")
    assert epage.evaluate("!!document.getElementById('notes').closest('#dock')"), "메모 목록은 오른쪽 도크 안"
    body = "document.getElementById('notes').closest('.dk-body')"
    assert epage.evaluate(f"(() => {{ const l = {body}; return l.scrollHeight > l.clientHeight + 20; }})()")
    cam0 = epage.evaluate("document.getElementById('stage').style.transform")
    lb = epage.locator("#nlist").bounding_box()
    epage.mouse.move(lb["x"] + lb["width"] / 2, min(lb["y"] + 60, epage.viewport_size["height"] - 60))
    for _ in range(30):
        epage.mouse.wheel(0, 400)
    epage.wait_for_timeout(200)
    assert epage.evaluate(f"(() => {{ const l = {body}; return l.scrollTop + l.clientHeight >= l.scrollHeight - 2; }})()"), "휠로 목록 끝까지 내려간다"
    assert epage.evaluate("document.getElementById('stage').style.transform") == cam0, "목록 위 휠은 판을 움직이지 않는다"
    assert epage.locator("#nsend").is_visible(), "보내기는 아래에 붙어 늘 보인다"
    assert epage.text_content('#dock .dk-tab[data-p="notes"] .dk-cnt') == "18", "탭에 메모 수"
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "1-notes-open-scrolled.png"))
    epage.evaluate("(k) => localStorage.removeItem(k)", key)
    reload(epage)
    assert epage.is_hidden("#notes") and epage.is_visible("#pNotes .dkp-empty"), "메모가 없으면 빈 안내"


# ---------------------------------------------------------------- 오른쪽 패널 도크: 합치기·떼기·띄우기·크기·접기·닫기·저장
def tab_box(pg, pid, where="#dock"):
    return pg.locator(f'{where} .dk-tab[data-p="{pid}"]').bounding_box()


def drag_to(pg, box, x, y):
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(box["x"] + box["width"] / 2 + 8, box["y"] + box["height"] / 2 + 8, steps=3)
    pg.mouse.move(x, y, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(120)


def dock_state(pg):
    return pg.evaluate("JSON.parse(localStorage.getItem('hd-dock') || 'null')")


def test_dock_merge_split_float_resize_collapse_persist(epage):
    epage.evaluate("localStorage.removeItem('hd-dock')")
    reload(epage)
    sw = lambda: epage.evaluate("getComputedStyle(document.body).getPropertyValue('--dockw').trim()")
    assert sw() == "300px" and epage.locator("#dock .dk-g").count() == 3, "기본: 세 묶음 · 너비 300"
    right = epage.evaluate("document.getElementById('screens').getBoundingClientRect().right")
    assert abs(right - epage.evaluate("document.getElementById('dock').getBoundingClientRect().left")) <= 1, "도크가 판을 밀어 좁힌다(겹치지 않음)"
    # 합치기: 메모 탭 → 첫 묶음 탭 줄
    t0 = epage.locator("#dock .dk-g").first.locator(".dk-tabs").bounding_box()
    drag_to(epage, tab_box(epage, "notes"), t0["x"] + t0["width"] - 70, t0["y"] + t0["height"] / 2)
    assert dock_state(epage)["groups"][0]["tabs"] == ["links", "notes"] and dock_state(epage)["groups"][0]["active"] == "notes"
    assert epage.evaluate("!!document.getElementById('pNotes').closest('.dk-g[data-g=\"0\"]')"), "합친 묶음에 메모 패널"
    # 띄우기: 메모 탭 → 판 위
    drag_to(epage, tab_box(epage, "notes"), 500, 400)
    st = dock_state(epage)
    assert len(st["floats"]) == 1 and st["floats"][0]["tabs"] == ["notes"], st
    assert epage.evaluate("!!document.getElementById('pNotes').closest('.dk-f')"), "떠 있는 창에 메모 패널"
    f0 = epage.locator(".dk-f").bounding_box()
    # 떠 있는 창 옮기기(탭 줄 빈 곳) · 크기(모서리)
    g = epage.locator(".dk-f .dk-grip").bounding_box()
    drag_to(epage, g, g["x"] + g["width"] / 2 - 100, g["y"] + g["height"] / 2 + 50)
    f1 = epage.locator(".dk-f").bounding_box()
    assert abs((f1["x"] - f0["x"]) + 100) <= 3 and abs((f1["y"] - f0["y"]) - 50) <= 3, (f0, f1)
    rs = epage.locator(".dk-f .dk-rs").bounding_box()
    drag_to(epage, rs, rs["x"] + 60, rs["y"] + 40)
    f2 = epage.locator(".dk-f").bounding_box()
    assert f2["width"] > f1["width"] + 40 and f2["height"] > f1["height"] + 25, (f1, f2)
    # 도크 너비
    e = epage.locator("#dock .dk-edge").bounding_box()
    drag_to(epage, e, e["x"] - 80, e["y"] + 200)
    assert 370 <= int(sw()[:-2]) <= 395, sw()
    # 닫기 · 다시 열기
    epage.hover('#dock .dk-tab[data-p="show"]')
    epage.click('#dock .dk-tab[data-p="show"] .dk-x')
    assert "show" in dock_state(epage)["closed"] and epage.locator('#dock .dk-tab[data-p="show"]').count() == 0
    epage.click("#dock .dk-more")
    epage.click('.dk-menu button[data-p="show"]')
    assert "show" not in dock_state(epage)["closed"] and epage.is_visible("#lgDdb"), "다시 열면 보인다"
    # 접기 → 아이콘 줄, 아이콘 누르면 펴짐
    epage.click("#dock .dk-fold")
    assert sw() == "44px" and epage.locator("#dock .dk-sb").count() >= 2
    assert epage.is_visible(".dk-f"), "접어도 떠 있는 창은 남는다"
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "s1-dock-folded-float.png"))
    epage.click('#dock .dk-sb[data-p="links"]')
    assert not dock_state(epage)["collapsed"] and sw() != "44px"
    # 새로고침 뒤에도 같은 배치
    before = dock_state(epage)
    reload(epage)
    assert dock_state(epage) == before and epage.locator(".dk-f").count() == 1
    epage.screenshot(path=str(ESHOTS / "s1-dock-after-reload.png"))
    epage.evaluate("localStorage.removeItem('hd-dock')")
    reload(epage)

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


SHIFT_CLICK = """(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))"""


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
    assert cmenu_items(epage)[-9:] == ["크게 보기", "연결 보기", "이름", "설명", "메모", "복제", "들어오는 연결 끊기", "숨기기", "삭제"]
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
    pick(epage, "크게 보기")
    epage.wait_for_function("!document.getElementById('modal').hidden")
    assert epage.get_attribute("#mpick", "aria-pressed") != "true", "메뉴의 크게 보기 = ▶ 보기와 같다(주석은 왼쪽 도구)"
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
    dash = dpage.evaluate("""(to) => { const p = [...document.querySelectorAll('#lks path.lk.pd')].find(p => p.dataset.to === to);
        const z = +document.getElementById('stage').dataset.zoom, d = getComputedStyle(p).strokeDasharray.split(',').map(parseFloat);
        return [d[0] * z, p.hasAttribute('pathLength')]; }""", q["id"])
    assert dash[0] >= 4 and not dash[1], ("점선 한 칸이 화면에서 4px 이상(길이 비율이 아니라 화면 px) — 재검증 C2", dash)
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


def test_trigger_tool_click_selects_element_with_its_socket(dpage):
    """S6: 트리거 도구에서 요소를 누르면 그 요소가 골라지고(테두리 고정 + 소켓) 그 소켓을 끌어 잇는다."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 330)
    fr = frame_of(dpage, "job")
    dpage.keyboard.press("l")
    x, y = el_point(dpage, ph, fr, "h1")
    dpage.mouse.click(x, y)
    dpage.wait_for_selector(".elbox.sel", timeout=3000)
    dpage.wait_for_timeout(200)
    assert dpage.evaluate("document.getElementById('cmenu').hidden"), "누르기 = 고르기만(메뉴는 우클릭) — 소켓 끌기를 막지 않는다(재검증 C1)"
    dpage.mouse.move(5, 300)
    dpage.wait_for_timeout(200)
    assert dpage.locator(".elbox.sel").count() == 1, "마우스가 떠나도 고른 요소 테두리는 남는다"
    s = dpage.evaluate("(() => { const r = document.querySelector('.sock.selsock').getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()")
    n0 = len(notes_of(dpage))
    q = visible_cover(dpage, skip=["job"])
    drag(dpage, s, q["x"] - s["x"], q["y"] - s["y"])
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and "h1" in n["path"] and n["to"] == q["id"], n
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("Escape")
    assert dpage.locator(".elbox.sel").count() == 0, "Esc = 고른 요소 풀기"
    dpage.keyboard.press("h")


def picked(pg):
    return pg.evaluate("[...document.querySelectorAll('#rows .card.picked')].map(c => c.dataset.id)")


def selbar(pg):
    return pg.evaluate("(() => { const b = document.getElementById('selbar'); return b && !b.hidden ? [...b.querySelectorAll('button')].filter(x => !x.hidden).map(x => x.textContent) : null; })()")


def test_pick_cards_selection_bar_delete_and_del_key(dpage):
    """S7: 카드 누르기 = 고르기 · 이동 도구 Ctrl+클릭 = 여러 장 · 선택 막대(메모·숨기기·삭제) · Del."""
    from test_canvas_baseline import empty_point
    fit_view(dpage)
    p = visible_cover(dpage)
    q = visible_cover(dpage, skip=[p["id"]])
    dpage.mouse.click(p["x"], p["y"])
    dpage.wait_for_timeout(150)
    assert picked(dpage) == [p["id"]] and selbar(dpage) == ["메모", "숨기기", "삭제"]
    dpage.keyboard.press("v")
    dpage.keyboard.down("Shift"); dpage.mouse.click(q["x"], q["y"]); dpage.keyboard.up("Shift")
    dpage.wait_for_timeout(150)
    assert sorted(picked(dpage)) == sorted([p["id"], q["id"]]) and selbar(dpage) == ["숨기기", "삭제"], "여러 장이면 메모는 빠진다"
    n0 = len(notes_of(dpage))
    dpage.locator("#selbar button", has_text="삭제").click()
    wait_notes(dpage, n0 + 2)
    assert {n["edit"] for n in notes_of(dpage)[-2:]} == {"delete"}
    for cid in (p["id"], q["id"]):                    # 재검증 C3: 사라지지 않고 흐리게 + '삭제 대기'
        card = dpage.locator(f'.card[data-id="{cid}"]')
        assert card.is_visible() and "del" in card.get_attribute("class")
        dpage.wait_for_function("(id) => +getComputedStyle(document.querySelector('.card[data-id=\"' + id + '\"]')).opacity < 0.6", arg=cid, timeout=3000)   # 흐려지는 움직임이 끝난 뒤
        assert "삭제 대기" in card.locator(".delchip").text_content()
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    assert "del" not in dpage.locator(f'.card[data-id="{p["id"]}"]').get_attribute("class")
    e = empty_point(dpage)
    dpage.mouse.click(e["x"], e["y"])
    dpage.wait_for_timeout(150)
    assert picked(dpage) == [] and selbar(dpage) is None, "빈 곳 = 고르기 풀기"
    dpage.mouse.click(p["x"], p["y"])
    dpage.keyboard.press("Delete")
    wait_notes(dpage, n0 + 1)
    assert "del" in dpage.locator(f'.card[data-id="{p["id"]}"]').get_attribute("class")
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("h")


def test_card_menu_full_items_duplicate_and_cut_incoming(dpage):
    """S7: 카드 우클릭 = 크게 보기·연결 보기·이름·설명·메모·복제·들어오는 연결 끊기·숨기기·삭제."""
    fit_view(dpage)
    c = visible_cover(dpage)
    dpage.mouse.click(c["x"], c["y"], button="right")
    dpage.wait_for_timeout(400)
    items = cmenu_items(dpage)
    assert items[-9:] == ["크게 보기", "연결 보기", "이름", "설명", "메모", "복제", "들어오는 연결 끊기", "숨기기", "삭제"], items
    pick(dpage, "복제")
    dpage.wait_for_timeout(200)
    d = drafts(dpage)
    assert len(d) == 1 and "복사" in dpage.text_content(f'.card[data-id="{d[0]["id"]}"] .ftitle')
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(200)
    assert drafts(dpage) == []
    focus_dayfine(dpage, "job")
    assert lk_to(dpage, "language")
    dpage.keyboard.press("Escape")
    zoom_to = __import__("test_canvas_v2").zoom_to
    b = zoom_to(dpage, "language", 200)
    dpage.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, button="right")
    pick(dpage, "들어오는 연결 끊기")
    focus_dayfine(dpage, "job")
    assert lk_to(dpage, "language") == [], "그 화면으로 오는 선이 바로 사라진다"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(250)
    assert lk_to(dpage, "language"), "되돌리면 돌아온다"
    dpage.keyboard.press("Escape")


def test_shortcuts_work_after_closing_text_box_and_selbar_hugs_cards(dpage):
    """스크린샷에서 찾은 버그: 글자 고치기 칸을 Esc 로 닫은 뒤 단축키가 먹혀야 하고, 작게 볼 때 선택 막대가 카드 바로 위에 붙어야 한다."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 420)
    fr = frame_of(dpage, "job")
    dpage.keyboard.press("e")
    x, y = el_point(dpage, ph, fr, "h1")
    dpage.mouse.click(x, y)
    dpage.wait_for_selector("#tedit:not([hidden])", timeout=3000)
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("h")
    assert tool(dpage) == ["hand"], "닫은 뒤 첫 단축키부터 먹힌다"
    dpage.keyboard.press("0")
    dpage.wait_for_timeout(300)
    c = visible_cover(dpage)
    dpage.mouse.click(c["x"], c["y"])
    dpage.wait_for_timeout(150)
    bar = dpage.locator("#selbar").bounding_box()
    card = dpage.locator(f'.card[data-id="{c["id"]}"] .phone').bounding_box()
    gap = card["y"] - (bar["y"] + bar["height"])
    assert 0 <= gap <= 20, ("선택 막대는 카드 바로 위", gap)
    dpage.keyboard.press("Escape")


def test_memo_and_annotate_tooltips_say_whole_screen_vs_one_element(dpage):
    """재검증 C6: 메모(M) = 화면 전체, 주석(P) = 요소 하나 — 툴팁 첫 줄에서 바로 구분."""
    tips = dpage.evaluate("Object.fromEntries([...document.querySelectorAll('#tools [data-tool]')].map(b => [b.dataset.tool, b.dataset.tip.split('|')[0]]))")
    assert "화면 전체" in tips["memo"] and "요소" in tips["annotate"], tips


def test_partly_pending_group_keeps_solid_line_and_marks_tag(dpage):
    """재검증 남은 한계: 기존 연결과 같은 도착으로 합쳐진 반영 대기는 선을 점선으로 만들지 않고 태그에 '반영 대기 n'."""
    focus_dayfine(dpage, "job")
    dpage.keyboard.press("l")
    s = dpage.evaluate("""(() => { const s = [...document.querySelectorAll('.sock')].find(n => getComputedStyle(n).display !== 'none' && n.dataset.to !== 'language');
        const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()""")
    t, pr = dpage.locator('.card[data-id="language"] .cover').bounding_box(), dpage.locator("#screens").bounding_box()
    tx = min(t["x"] + t["width"] / 2, pr["x"] + pr["width"] - 30)        # 판 오른쪽은 도크 — 보이는 부분에 놓는다
    assert tx > t["x"] + 10, ("도착 카드가 판 안에 보여야", t, pr)
    drag(dpage, s, tx - s["x"], t["y"] + t["height"] / 2 - s["y"])
    dpage.wait_for_timeout(250)
    cls = lk_to(dpage, "language")
    assert cls and not any("pd" in c for c in cls), ("기존 연결이 섞인 그룹의 선은 실선", cls)
    assert "반영 대기 1" in dpage.text_content('#lkl .ltag[data-to="language"]')
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(250)
    assert "반영 대기" not in dpage.text_content('#lkl .ltag[data-to="language"]')
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


# ---------------------------------------------------------------- 실제 캔버스 피드백 E3·E4·E6 (rework §7-3)
def sel_sock(pg):
    return pg.evaluate("(() => { const s = document.querySelector('.sock.selsock'); if (!s) return null; const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()")


def test_trigger_click_on_card_shows_its_links_like_shift_click(dpage):
    """E3: 트리거 도구로 카드(요소)를 누르면 Shift+클릭처럼 그 화면의 연결 보기가 켜지고, 고른 요소와 소켓은 남는다."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 330)
    fr = frame_of(dpage, "job")
    dpage.keyboard.press("l")
    x, y = el_point(dpage, ph, fr, "h1")
    dpage.mouse.click(x, y)
    dpage.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
    dpage.wait_for_function("document.querySelectorAll('#lks path.lk').length >= 1", timeout=5000)
    assert dpage.evaluate("document.querySelector('.card.focus').dataset.id") == "job"
    dpage.wait_for_timeout(300)
    assert sel_sock(dpage), "연결 보기가 그려진 뒤에도 고른 요소의 소켓은 남는다"
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("h")


def test_cutting_a_pending_line_cancels_that_edit(dpage):
    """E4: 아직 반영 안 된(점선) 연결을 오른쪽 끌기로 자르면 '연결 끊기' 메모가 아니라 그 편집이 취소된다. 되돌리기 = 점선이 돌아온다."""
    focus_dayfine(dpage, "job")
    dpage.keyboard.press("l")
    s = dpage.evaluate("""(() => { const s = [...document.querySelectorAll('.sock')].find(n => getComputedStyle(n).display !== 'none');
        const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, to: s.dataset.to}; })()""")
    n0 = len(notes_of(dpage))
    q = visible_cover(dpage, skip=["job", s["to"]])
    drag(dpage, s, q["x"] - s["x"], q["y"] - s["y"])
    wait_notes(dpage, n0 + 1)
    dpage.wait_for_timeout(250)
    lk = next(p for p in paths(dpage) if p["to"] == q["id"])
    (x0, y0), (x1, y1) = lk["pts"][0], lk["pts"][1]
    sx, sy = dpage.evaluate("""([x, y]) => { const r = document.getElementById('lks').getBoundingClientRect(),
        z = +document.getElementById('stage').dataset.zoom; return [r.left + x * z, r.top + y * z]; }""", [(x0 + x1) / 2, (y0 + y1) / 2])
    dpage.mouse.move(sx - 12, sy - 12)
    dpage.mouse.down(button="right")
    dpage.mouse.move(sx + 12, sy + 12, steps=6)
    dpage.mouse.up(button="right")
    wait_notes(dpage, n0)
    dpage.wait_for_timeout(250)
    assert lk_to(dpage, q["id"]) == [], "취소된 점선은 사라진다"
    assert lk_to(dpage, s["to"]), "도착 바꾸기를 취소하면 파일에 있는 원래 선이 돌아온다"
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0 + 1)
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


def test_trigger_drag_can_reach_a_far_card_in_another_row(dpage):
    """E6: 크게 확대해 둔 채 도착 없는 요소에서 끌기 시작 → 판 가장자리에 대면 판이 따라 움직이고, 끄는 중 Ctrl+휠로 줄여도
    끄는 선은 그 요소에 붙어 있으며, 다른 줄의 먼 카드에 놓으면 이어진다."""
    fit_view(dpage)
    ph = __import__("test_canvas_v2").zoom_to(dpage, "job", 330)
    fr = frame_of(dpage, "job")
    dpage.keyboard.press("l")
    x, y = el_point(dpage, ph, fr, "h1")
    dpage.mouse.click(x, y)
    dpage.wait_for_selector(".sock.selsock", timeout=3000)
    dpage.wait_for_timeout(300)
    s = sel_sock(dpage)
    n0 = len(notes_of(dpage))
    pr = dpage.locator("#screens").bounding_box()
    t0 = dpage.evaluate("document.getElementById('stage').style.transform")
    dpage.mouse.move(s["x"], s["y"])
    dpage.mouse.down()
    dpage.mouse.move(s["x"] + 30, s["y"] + 10, steps=4)
    dpage.mouse.move(pr["x"] + pr["width"] - 6, pr["y"] + pr["height"] / 2, steps=8)
    dpage.wait_for_timeout(500)
    assert dpage.evaluate("document.getElementById('stage').style.transform") != t0, "끄는 중 판 가장자리에 대면 판이 따라 움직인다"
    mx, my = pr["x"] + pr["width"] / 2, pr["y"] + pr["height"] / 2
    dpage.mouse.move(mx, my, steps=4)
    for _ in range(12):
        dpage.keyboard.down("Control"); dpage.mouse.wheel(0, 300); dpage.keyboard.up("Control")
        dpage.wait_for_timeout(40)
    dpage.wait_for_timeout(200)
    start = dpage.evaluate(r"""(() => { const d = document.querySelector('#ghost path').getAttribute('d').match(/M([\d.-]+),([\d.-]+)/),
        r = document.getElementById('screens').getBoundingClientRect(); return [r.left + +d[1], r.top + +d[2]]; })()""")
    ss = sel_sock(dpage)
    assert abs(start[0] - ss["x"]) < 8 and abs(start[1] - ss["y"]) < 8, ("줄여도 끄는 선은 고른 요소의 소켓에서 시작", start, ss)
    far = dpage.evaluate("""(() => { const g = c => (c.closest('.flow') || {}).querySelector?.('.glabel')?.textContent || '';
        const job = document.querySelector('.card[data-id="job"]'), r = document.getElementById('screens').getBoundingClientRect();
        for (const c of document.querySelectorAll('#rows .card .cover')) { const card = c.closest('.card');
          if (card.dataset.id === 'job' || g(card) === g(job) || card.classList.contains('hid')) continue;
          const b = c.getBoundingClientRect(), x = b.left + b.width / 2, y = b.top + b.height / 2;
          if (x > r.left + 20 && x < r.right - 340 && y > r.top + 20 && y < r.bottom - 20 && document.elementFromPoint(x, y) === c) return {id: card.dataset.id, x, y}; }
        return null; })()""")
    assert far, "줄인 뒤 다른 줄 카드가 보여야 한다"
    dpage.mouse.move(far["x"], far["y"], steps=6)
    dpage.mouse.up()
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["screen"] == "job" and n["to"] == far["id"], n
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("h")


# ---------------------------------------------------------------- 조각 2.5a 고르기 (E15·E11·E18, rework §8-3)
CLICK = """(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))"""


def sel_state(pg):
    return pg.evaluate("""({picked: [...document.querySelectorAll('#rows .card.picked')].map(c => c.dataset.id).sort(),
        focus: (document.querySelector('#rows .card.focus') || {dataset: {}}).dataset.id || null,
        focusing: document.getElementById('rows').classList.contains('focusing')})""")


def test_click_selects_and_shows_links_shift_adds(dpage):
    """E15: 카드 누르기 = 그 카드 고르기 + 그 화면 연결 강조(예전 Shift+클릭). Shift+클릭 = 여러 장 고르기. 빈 판 = 모두 풀기."""
    fit_view(dpage)
    p = visible_cover(dpage)
    q = visible_cover(dpage, skip=[p["id"]])
    dpage.mouse.click(p["x"], p["y"])
    dpage.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
    st = sel_state(dpage)
    assert st["picked"] == [p["id"]] and st["focus"] == p["id"], st
    assert not dpage.evaluate("document.getElementById('modal').hidden === false"), "한 번 누르기는 크게 보기를 열지 않는다"
    dpage.keyboard.down("Shift"); dpage.mouse.click(q["x"], q["y"]); dpage.keyboard.up("Shift")
    dpage.wait_for_timeout(150)
    st = sel_state(dpage)
    assert st["picked"] == sorted([p["id"], q["id"]]), ("Shift+클릭 = 고른 것에 더하기", st)
    dpage.keyboard.down("Shift"); dpage.mouse.click(p["x"], p["y"]); dpage.keyboard.up("Shift")
    dpage.wait_for_timeout(150)
    st = sel_state(dpage)
    assert st["picked"] == [q["id"]] and st["focus"] == q["id"], ("다시 Shift+클릭 = 빼기, 하나 남으면 그 화면 연결 강조", st)
    from test_canvas_baseline import empty_point
    e = empty_point(dpage)
    dpage.mouse.click(e["x"], e["y"])
    dpage.wait_for_timeout(150)
    st = sel_state(dpage)
    assert st["picked"] == [] and not st["focusing"], st
    assert "Shift" in dpage.text_content("#khint") and "누르면 연결" in dpage.text_content("#khint")


def test_trigger_drag_esc_cancels_and_deleted_card_refuses(dpage):
    """E11: 트리거를 끄는 중 Esc = 취소(아무것도 남지 않음). E18: 삭제 대기 카드에 놓으면 잇지 않고 알린다."""
    fit_view(dpage)
    dpage.keyboard.press("l")
    p = visible_cover(dpage)
    q = visible_cover(dpage, skip=[p["id"]])
    n0 = len(notes_of(dpage))
    dpage.mouse.move(p["x"], p["y"]); dpage.mouse.down()
    dpage.mouse.move((p["x"] + q["x"]) / 2, (p["y"] + q["y"]) / 2, steps=6)
    dpage.keyboard.press("Escape")
    assert dpage.evaluate("document.getElementById('ghost').innerHTML") == "", "Esc = 끄는 선 지움"
    dpage.mouse.move(q["x"], q["y"], steps=4); dpage.mouse.up()
    dpage.wait_for_timeout(400)
    assert len(notes_of(dpage)) == n0, "Esc 뒤 놓아도 잇지 않는다"
    assert visible_cover(dpage)["id"] == p["id"] and abs(visible_cover(dpage)["x"] - p["x"]) < 2, "Esc 뒤 놓을 때까지 판이 움직이지 않는다"
    dpage.keyboard.press("h")
    dpage.mouse.click(q["x"], q["y"])
    dpage.wait_for_timeout(150)
    dpage.keyboard.press("Delete")
    wait_notes(dpage, n0 + 1)
    dpage.keyboard.press("l")
    drag(dpage, p, q["x"] - p["x"], q["y"] - p["y"])
    dpage.wait_for_timeout(1600)
    assert len(notes_of(dpage)) == n0 + 1, "삭제 대기 화면에는 잇지 않는다"
    assert "삭제" in dpage.text_content("#toast")
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.keyboard.press("h")
    dpage.keyboard.press("Escape")


# ---------------------------------------------------------------- 조각 2.5b 늘 보이는 선 (E7·E12·E14·D6b·D6c·D8·D9, rework §8-3)
LINES_JS = """[...document.querySelectorAll('#ar path.ln')].map(p => ({from: p.dataset.from, to: p.dataset.to, both: p.dataset.both === '1',
    pd: p.classList.contains('pd'), plan: p.classList.contains('plan'), stroke: p.getAttribute('stroke'),
    dash: getComputedStyle(p).strokeDasharray, op: +getComputedStyle(p).opacity, w: parseFloat(getComputedStyle(p).strokeWidth),
    shown: getComputedStyle(p).display !== 'none'}))"""


def lines(pg):
    return pg.evaluate(LINES_JS)


def test_all_lines_visible_without_clicking(dpage):
    """E7·D6b: 아무것도 누르지 않아도 모든 화면 연결이 판에 보인다(출발 줄마다 한 색, 양방향은 선 하나, 점선 없음).
    D9: [주요 흐름] 버튼·표시 패널 체크·A 키는 없다. 누르면(한 화면 연결 보기) 그 화면의 자세한 선이 대신한다."""
    fit_view(dpage)
    assert not dpage.evaluate("document.getElementById('rows').classList.contains('focusing')")
    ls = [l for l in lines(dpage) if not l["plan"]]
    assert len(ls) >= 3 and all(l["shown"] for l in ls), ls
    assert all(l["dash"] in ("none", "") for l in ls if not l["pd"]), "점선은 반영 대기에만"
    pairs = [frozenset((l["from"], l["to"])) for l in ls]
    assert len(pairs) == len(set(pairs)), "양방향 연결도 선 하나"
    row = dpage.evaluate("""(() => { const m = {}; document.querySelectorAll('#rows .flow').forEach((f, i) => f.querySelectorAll('.card').forEach(c => m[c.dataset.id] = i)); return m; })()""")
    by_row = {}
    for l in ls:
        by_row.setdefault(row[l["from"]], set()).add(l["stroke"])
    assert all(len(v) == 1 for v in by_row.values()), ("출발 줄마다 한 색", by_row)
    if len(by_row) >= 2:
        assert len({next(iter(v)) for v in by_row.values()}) >= 2, "줄이 다르면 색도 다르다"
    assert dpage.locator("#arrows").count() == 0 and dpage.locator("#lgFlow").count() == 0
    n = len(lines(dpage))
    dpage.keyboard.press("a")
    dpage.wait_for_timeout(150)
    assert len([l for l in lines(dpage) if l["shown"]]) == n, "A 키는 비워 둔다"
    # 화면 안 링크(palette.js hd-links)와 같은 연결이어야 한다
    focus_dayfine(dpage, "job")
    want = {p["to"] for p in paths(dpage)}
    have = {l["to"] if l["from"] == "job" else l["from"] for l in ls if "job" in (l["from"], l["to"]) and (l["from"] == "job" or l["both"])}
    assert want <= have, (want, have)
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Escape")


def test_line_controls_show_width_opacity_persist(dpage):
    """E7: 표시 패널에서 전체 선 보이기/숨기기 · 굵기 · 투명도 — 새로고침 뒤에도 그대로."""
    fit_view(dpage)
    d = dpage.locator("#dock").bounding_box()
    dpage.mouse.move(d["x"] + d["width"] / 2, d["y"] + d["height"] - 20)   # 카드 위가 아니게(올린 카드 선은 진하게 바뀐다)
    dpage.wait_for_timeout(250)
    l0 = [l for l in lines(dpage) if not l["plan"]][0]
    dpage.evaluate("(v) => { const r = document.getElementById('lnOp'); r.value = v; r.dispatchEvent(new Event('input', {bubbles: true})); r.dispatchEvent(new Event('change', {bubbles: true})); }", "0.3")
    dpage.evaluate("(v) => { const r = document.getElementById('lgW'); r.value = v; r.dispatchEvent(new Event('input', {bubbles: true})); r.dispatchEvent(new Event('change', {bubbles: true})); }", "5")
    dpage.wait_for_timeout(300)
    l1 = next(l for l in lines(dpage) if l["from"] == l0["from"] and l["to"] == l0["to"])
    assert abs(l1["op"] - 0.3) < 0.05 and l1["w"] > l0["w"], (l0, l1)
    dpage.click("#lnShow")
    dpage.wait_for_timeout(150)
    assert not any(l["shown"] for l in lines(dpage)), "숨기기 = 선 모두 숨김"
    reload(dpage)
    assert not any(l["shown"] for l in lines(dpage)), "새로고침 뒤에도 숨김"
    assert dpage.evaluate("document.getElementById('lnOp').value") == "0.3"
    dpage.click("#lnShow")
    dpage.evaluate("(v) => { const r = document.getElementById('lnOp'); r.value = v; r.dispatchEvent(new Event('input', {bubbles: true})); r.dispatchEvent(new Event('change', {bubbles: true})); }", "0.55")
    dpage.evaluate("(v) => { const r = document.getElementById('lgW'); r.value = v; r.dispatchEvent(new Event('input', {bubbles: true})); r.dispatchEvent(new Event('change', {bubbles: true})); }", "2.5")
    dpage.wait_for_timeout(150)
    assert all(l["shown"] for l in lines(dpage))


def test_trigger_link_draws_dashed_line_without_clicking(dpage):
    """E7·E14: 트리거로 다른 화면에 이으면 아무것도 누르지 않아도 판에 반영 대기 점선이 바로 보인다(투명도와 상관없이 진하게). 되돌리면 사라진다."""
    fit_view(dpage)
    dpage.keyboard.press("l")
    have = {frozenset((l["from"], l["to"])) for l in lines(dpage)}
    cards = dpage.evaluate("[...document.querySelectorAll('#rows .card:not(.hid)')].map(c => c.dataset.id)")
    p = visible_cover(dpage)
    q = next((visible_cover(dpage, skip=[c for c in cards if c != t]) for t in cards if t != p["id"] and frozenset((p["id"], t)) not in have
              and dpage.evaluate("(id) => { const c = document.querySelector('.card[data-id=\"' + id + '\"] .cover'), r = document.getElementById('screens').getBoundingClientRect(), b = c.getBoundingClientRect(); return b.left + b.width / 2 > r.left + 80 && b.left + b.width / 2 < r.right - 380; }", t)), None)
    assert q, "이을 곳(아직 연결 없는 카드)이 판에 보여야 한다"
    n0 = len(notes_of(dpage))
    drag(dpage, p, q["x"] - p["x"], q["y"] - p["y"])
    wait_notes(dpage, n0 + 1)
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Escape")
    dpage.wait_for_timeout(200)
    pd = [l for l in lines(dpage) if l["pd"] and {l["from"], l["to"]} == {p["id"], q["id"]}]
    assert pd and pd[0]["shown"] and pd[0]["dash"] not in ("none", "") and pd[0]["op"] > 0.9, (pd, lines(dpage))
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.wait_for_timeout(200)
    assert not [l for l in lines(dpage) if l["pd"]], "되돌리면 점선이 사라진다"
    dpage.keyboard.press("h")
