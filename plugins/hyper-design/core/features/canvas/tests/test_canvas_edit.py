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
    pg.click('#tools [data-tool="annotate"]')
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
    assert epage.locator("#nsend").is_visible() and epage.evaluate("!!document.getElementById('nsend').closest('header')"), "보내기는 위쪽 줄 한 자리(E16)"
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


TABS_FIT_JS = """() => [...document.querySelectorAll('#dock .dk-tabs')].map(t => {
  const r = t.getBoundingClientRect();
  return [...t.querySelectorAll('.dk-tab, .dk-ib')].map(b => { const q = b.getBoundingClientRect();
    return {p: b.dataset.p || b.className, on: b.classList.contains('on'), left: q.left, right: q.right, lo: r.left, hi: r.right}; });
})"""


def test_dock_tabs_fit_when_many(epage):
    """탭이 많아도(테마까지 켜서 한 묶음에 5개) 탭 줄 밖으로 잘리지 않는다 — 고른 탭과 ＋·» 단추도 다 보인다."""
    epage.evaluate("localStorage.removeItem('hd-dock')")
    reload(epage)
    epage.click("#wbtn"); epage.click('#wmenu [data-w="theme"]'); epage.keyboard.press("Escape")
    epage.click('#dock .dk-tab[data-p="theme"]')
    rows = epage.evaluate(TABS_FIT_JS)
    assert max(len(g) for g in rows) >= 5, rows
    out = [b for g in rows for b in g if b["left"] < b["lo"] - 1 or b["right"] > b["hi"] + 1]
    assert not out, out
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "dock-tabs-many.png"))
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
    epage.click("#zoom"); epage.click("#fit")
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
    epage.click("#zoom"); epage.click("#fit")
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
    epage.click("#zoom"); epage.click("#fit")
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
    epage.click("#zoom"); epage.click("#fit")
    epage.wait_for_timeout(150)
    epage.keyboard.press("v")
    q = visible_cover(epage)
    epage.mouse.dblclick(q["x"], q["y"])
    epage.wait_for_function("!document.getElementById('modal').hidden")
    epage.keyboard.press("Escape")
    epage.wait_for_timeout(150)
    epage.keyboard.press("h")


def test_fit_includes_moved_card_and_drops_stale(epage):
    epage.click("#zoom"); epage.click("#fit")          # 옮긴 자리 키를 이 테스트가 직접 만든다(앞 테스트에 기대지 않게)
    epage.wait_for_timeout(150)
    epage.keyboard.press("v")
    drag(epage, visible_cover(epage), 20, 0)
    epage.keyboard.press("h")
    key = epage.evaluate("Object.keys(localStorage).find(k => k.startsWith('hd-card-pos:'))")
    assert key, "이동 도구 끌기가 옮긴 자리 키를 만든다"
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
    epage.click("#zoom"); epage.click("#fit")
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
    epage.click("#zoom"); epage.click("#fit")
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


def focus_dayfine(pg, sid):
    """그 카드만 고른다(누르기) — 그 선이 진해지고, 화면 안 버튼 표시·소켓·연결 패널이 채워질 때까지."""
    from test_canvas_v2 import zoom_to
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(150)
    zoom_to(pg, sid, 330)
    pg.evaluate(CLICK, sid)
    pg.wait_for_function("!document.getElementById('legend').hidden", timeout=5000)
    pg.wait_for_timeout(700)


LN_PT_JS = """([a, b]) => { const p = [...document.querySelectorAll('#ar path.ln')].find(p => (p.dataset.from === a && p.dataset.to === b) || (p.dataset.from === b && p.dataset.to === a));
    const scr = (o, t) => { const q = o.getPointAtLength(t), n = o.getScreenCTM(); return [q.x * n.a + q.y * n.c + n.e, q.x * n.b + q.y * n.d + n.f]; };
    const L = p.getTotalLength(), others = [...document.querySelectorAll('#ar path.ln')].filter(o => o !== p && getComputedStyle(o).display !== 'none')
      .flatMap(o => { const n = o.getTotalLength(), out = []; for (let t = 0; t <= n; t += 4) out.push(scr(o, t)); return out; });
    for (const gap of [16, 8, 0]) {                      // 이웃 선과 떨어진 점부터(자르는 획 ±12px 이 이웃 선을 건드리지 않게), 없으면 점점 가까운 점
      let best = null;
      for (let i = 5; i < 96; i++) { const [x, y] = scr(p, L * i / 100);
        if (gap && others.some(([u, v]) => Math.hypot(u - x, v - y) < gap)) continue;
        if (!best || Math.abs(i - 50) < best[2]) best = [x, y, Math.abs(i - 50)]; }
      if (best) return best.slice(0, 2); }
    return null; }"""


def ln_mid(pg, a, b):
    """판의 선(a—b 쌍)에서 이웃 선과 가장 떨어진(16 → 8 → 0px) 점 중 가운데에 가까운 점 — 판을 휠로 밀어 그 점을 판 가운데로 가져온 뒤 화면 좌표."""
    x, y = pg.evaluate(LN_PT_JS, [a, b])
    pr = pg.locator("#screens").bounding_box()
    cx, cy = pr["x"] + (pr["width"] - 360) / 2, pr["y"] + pr["height"] / 2      # 오른쪽 360px 은 도크
    pg.mouse.move(cx, cy)
    pg.mouse.wheel(x - cx, y - cy)
    pg.wait_for_timeout(250)
    return pg.evaluate(LN_PT_JS, [a, b])


def right_cut(pg, x, y, d=12):
    pg.mouse.move(x - d, y - d)
    pg.mouse.down(button="right")
    pg.mouse.move(x + d, y + d, steps=6)
    pg.mouse.up(button="right")


def bring_into_view(pg, sel):
    """휠로 판을 옮겨 그 요소를 판 가운데로(Ctrl 없이 = 이동)."""
    r = pg.locator(sel).bounding_box()
    pr = pg.locator("#screens").bounding_box()
    pg.mouse.move(pr["x"] + 400, pr["y"] + 300)
    pg.mouse.wheel(r["x"] + r["width"] / 2 - (pr["x"] + pr["width"] / 2), r["y"] + r["height"] / 2 - (pr["y"] + pr["height"] / 2))
    pg.wait_for_timeout(250)


def tag_sel(frm, to):
    return f'#rows .alabel[data-from="{frm}"][data-to="{to}"]'


def tag_text(pg, frm, to):
    """선 태그 글에서 번호(첫 글자)를 뺀 것."""
    return pg.text_content(tag_sel(frm, to)).split(" ", 1)[-1]


def test_tag_rename_keeps_button_text(dpage):
    """E20: 선 태그(번호 + 이름)를 두 번 눌러 이름 바꾸기 — 버튼 글·연결 패널은 그대로, hd-link-names 별도 키, 새로고침 뒤에도."""
    focus_dayfine(dpage, "job")
    to = dpage.evaluate("[...document.querySelectorAll('#rows .alabel.on')].find(n => n.dataset.from === 'job').dataset.to")
    sel, old = tag_sel("job", to), tag_text(dpage, "job", to)
    num = dpage.text_content(sel).split(" ", 1)[0]
    btns = f'#lgRows .lgrow[data-to="{to}"] .lgtx > b:not(.lgnm)'
    legend0 = dpage.text_content(btns)
    frame = dpage.frame_locator('.card[data-id="job"] .phone iframe')
    btn0 = frame.locator("body").inner_text()
    bring_into_view(dpage, sel)
    dpage.dblclick(sel)
    inp = dpage.locator(f"{sel} input")
    inp.fill("처음 화면으로")
    inp.press("Enter")
    dpage.wait_for_timeout(200)
    assert dpage.text_content(sel) == num + " 처음 화면으로", "번호는 그대로, 이름만"
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "이름 바꾸기가 고르기를 풀지 않는다"
    assert dpage.text_content(btns) == legend0, "연결 패널의 버튼 글은 그대로(이름은 그 위에 따로)"
    assert frame.locator("body").inner_text() == btn0, "화면 안 버튼 글은 그대로"
    keys = dpage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-link-names:'))")
    assert len(keys) == 1 and "처음 화면으로" in dpage.evaluate("(k) => localStorage.getItem(k)", keys[0])
    assert "처음 화면으로" not in (dpage.evaluate("localStorage.getItem('hd-canvas-prefs')") or "")
    reload(dpage)
    focus_dayfine(dpage, "job")
    assert tag_text(dpage, "job", to) == "처음 화면으로", "새로고침 뒤에도"
    bring_into_view(dpage, sel)
    # Esc = 취소(고르기는 그대로), 비우고 Enter = 버튼 글로 돌아감
    dpage.dblclick(sel)
    dpage.locator(f"{sel} input").fill("버릴 이름")
    dpage.locator(f"{sel} input").press("Escape")
    dpage.wait_for_timeout(150)
    assert tag_text(dpage, "job", to) == "처음 화면으로"
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "입력 중 Esc 는 고르기를 풀지 않는다"
    dpage.dblclick(sel)
    dpage.locator(f"{sel} input").fill("")
    dpage.locator(f"{sel} input").press("Enter")
    dpage.wait_for_timeout(150)
    assert tag_text(dpage, "job", to) == old
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
    epage.click("#zoom"); epage.click("#fit")
    epage.wait_for_timeout(150)
    p = empty_point(epage)
    epage.mouse.click(p["x"], p["y"], button="right")
    assert cmenu_items(epage) == ["여기에 레이아웃", "전체 보기", "100%"], "빈 곳: 여기에 레이아웃 · 전체 보기 · 100% (숨긴 화면이 없으면 그 줄은 없다)"
    pick(epage, "100%")
    assert epage.get_attribute("#stage", "data-zoom") == "1.0000"
    assert epage.evaluate("document.getElementById('cmenu').hidden")
    epage.click("#zoom"); epage.click("#fit")
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
    epage.click("#zoom"); epage.click("#fit")
    epage.wait_for_timeout(150)
    c = visible_cover(epage)
    epage.mouse.click(c["x"], c["y"], button="right")
    cmenu_items(epage)
    epage.keyboard.press("Escape")
    assert epage.evaluate("document.getElementById('cmenu').hidden"), "Esc 는 메뉴부터 닫는다"
    epage.mouse.click(c["x"], c["y"], button="right")
    pick(epage, "크게 보기")
    epage.wait_for_function("!document.getElementById('modal').hidden")
    assert epage.get_attribute('#tools [data-tool="annotate"]', "aria-pressed") != "true", "메뉴의 크게 보기 = ▶ 보기와 같다(주석은 왼쪽 도구)"
    epage.keyboard.press("Escape")
    epage.wait_for_timeout(150)
    if epage.evaluate("!document.getElementById('modal').hidden"):
        epage.keyboard.press("Escape")
        epage.wait_for_timeout(150)


def test_hide_screen_and_hidden_list(epage):
    from test_canvas_baseline import empty_point
    epage.click("#zoom"); epage.click("#fit")
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
    assert epage.locator("#pLayers").is_visible() and epage.get_attribute('#lyF [data-f="hidden"]', "aria-pressed") == "true", "숨긴 것은 레이어 패널 '숨긴 것만'(H7)"
    title = epage.get_attribute(f'.card[data-id="{sid}"] .cover', "data-title")
    assert title in epage.text_content("#lyTree")
    ESHOTS.mkdir(parents=True, exist_ok=True)
    epage.screenshot(path=str(ESHOTS / "4-hidden-list.png"))
    epage.locator(f'#lyTree [data-ly="{sid}"] .ly-eye').click()
    epage.wait_for_timeout(150)
    assert epage.locator(f'.card[data-id="{sid}"]').is_visible()
    assert not epage.locator("#thid").is_visible() and epage.locator(f'#lyTree [data-ly="{sid}"]').count() == 0, "다 보이면 '숨긴 것만' 목록도 빈다"
    epage.click('#lyF [data-f="hidden"]')
    assert epage.evaluate("(k) => localStorage.getItem(k)", keys[0]) == "[]"


def test_undo_redo_card_moves(epage):
    epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-card-pos:')).forEach(k => localStorage.removeItem(k))")   # 앞 테스트가 옮겨 둔 카드 없이(-n 에서 순서가 바뀌어도)
    reload(epage)                                    # 되돌리기 기록은 새로고침하면 비어 있다(50단계 상한은 unit: test_history_model_caps_undo_at_50)
    epage.click("#zoom"); epage.click("#fit")
    epage.wait_for_timeout(150)
    assert epage.is_disabled("#undo") and epage.is_disabled("#redo")
    z = float(epage.get_attribute("#stage", "data-zoom"))
    epage.keyboard.press("v")
    p = visible_cover(epage)
    x0, _ = card_xy(epage, p["id"])
    for i in range(2):                               # 오른쪽 → 왼쪽: 첫 번째 뒤 = x0 + 30/z, 두 번째 뒤 = x0
        sx = p["x"] + (30 if i % 2 else 0)
        epage.mouse.move(sx, p["y"])
        epage.mouse.down()
        epage.mouse.move(sx + (-30 if i % 2 else 30), p["y"], steps=3)
        epage.mouse.up()
    epage.wait_for_timeout(150)
    assert abs(card_xy(epage, p["id"])[0] - x0) < 3
    assert "카드 옮기기" in epage.get_attribute("#undo", "title")
    epage.keyboard.press("Control+z")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - (x0 + 30 / z)) < 3, "Ctrl+Z = 한 단계 뒤로"
    epage.keyboard.press("Control+z")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - x0) < 3
    assert epage.is_disabled("#undo") and not epage.is_disabled("#redo")
    epage.keyboard.press("Control+Shift+z")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - (x0 + 30 / z)) < 3
    epage.keyboard.press("Control+y")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - x0) < 3
    epage.click("#undo")
    epage.wait_for_timeout(100)
    assert abs(card_xy(epage, p["id"])[0] - (x0 + 30 / z)) < 3, "위쪽 막대 ↶ 버튼도 같다"
    epage.click("#undo")
    epage.wait_for_timeout(100)
    stored = epage.evaluate("Object.values(JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-card-pos:'))) || '{}'))")
    assert all(abs(s["dx"]) < 3 for s in stored), "되돌린 자리가 저장된다"
    epage.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-card-pos:')).forEach(k => localStorage.removeItem(k))")
    epage.keyboard.press("h")
    reload(epage)


def test_link_menu_rename_undo_and_go(dpage):
    focus_dayfine(dpage, "job")
    to = dpage.evaluate("[...document.querySelectorAll('#rows .alabel.on')].find(n => n.dataset.from === 'job').dataset.to")
    sel, old = tag_sel("job", to), tag_text(dpage, "job", to)
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
    assert tag_text(dpage, "job", to) == "맥락 이름"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(150)
    assert tag_text(dpage, "job", to) == old, "되돌리면 버튼 글로"
    assert "맥락 이름" not in (dpage.evaluate("localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-link-names:')))") or "")
    dpage.keyboard.press("Control+Shift+z")
    dpage.wait_for_timeout(150)
    assert tag_text(dpage, "job", to) == "맥락 이름"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(150)
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "되돌리기는 고르기를 풀지 않는다"
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
    assert dpage.locator("#pend").is_visible(), "잇기는 기계적 편집 — 반영 대기 패널이 앞으로(E5)"
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
    """E20: 늘 보이는 선을 오른쪽 끌기로 가로지르면 그 쌍의 화면 안 링크 전부 끊기 메모(되돌리기 한 번에)."""
    focus_dayfine(dpage, "job")
    n0 = len(notes_of(dpage))
    right_cut(dpage, *ln_mid(dpage, "job", "language"))
    dpage.wait_for_function("(n) => " + NOTES_JS + ".length > n", arg=n0, timeout=4000)
    new = notes_of(dpage)[n0:]
    assert all(n["op"] == "cut" and {n["screen"], n["to"]} == {"job", "language"} and "연결 끊기" in n["note"] for n in new), new
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
    dpage.dblclick(t_sel)                            # H16: 제목을 두 번 누르면 카드 글 한 상자가 열리고 글자 자리는 제목에
    box = dpage.locator('.card[data-id="job"] .capbox')
    ttl = box.locator('[data-f="title"]')
    assert box.is_visible() and old.endswith(ttl.text_content())
    dpage.keyboard.press("Control+a")
    dpage.keyboard.type("새 이름")
    dpage.keyboard.press("Control+Enter")
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
    dpage.dblclick(d_sel)                            # 설명을 두 번 누르면 같은 상자, 글자 자리는 설명에
    assert dpage.locator('.card[data-id="job"] .capbox [data-f="purpose"]').is_visible()
    dpage.keyboard.press("Control+a")
    dpage.keyboard.type("첫 줄")
    dpage.keyboard.press("Shift+Enter")
    dpage.keyboard.type("둘째 줄")
    dpage.keyboard.press("Control+Enter")
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
def lk_to(pg, to, frm="job"):
    """판의 선(frm—to 쌍)의 class 목록 — 없으면 []."""
    return pg.evaluate("""([a, b]) => [...document.querySelectorAll('#ar path.ln')].filter(p => (p.dataset.from === a && p.dataset.to === b) || (p.dataset.from === b && p.dataset.to === a))
        .map(p => p.getAttribute('class'))""", [frm, to])


def test_cut_hides_line_at_once_with_live_mark_and_toast_undo(dpage):
    focus_dayfine(dpage, "job")
    sx, sy = ln_mid(dpage, "job", "language")
    dpage.mouse.move(sx - 14, sy - 14)
    dpage.mouse.down(button="right")
    dpage.mouse.move(sx + 14, sy + 14, steps=6)
    assert any("cutting" in c for c in lk_to(dpage, "language")), "끄는 동안 가로지른 선은 바로 빨갛게"
    dpage.mouse.up(button="right")
    dpage.wait_for_timeout(600)
    assert lk_to(dpage, "language") == [], "놓으면 그 선은 바로 사라진다"
    assert "끊었어요" in dpage.text_content("#toast")
    dpage.click("#toast button")
    dpage.wait_for_timeout(250)
    assert lk_to(dpage, "language"), "토스트의 되돌리기 = 선이 돌아온다"
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
    dash = dpage.evaluate("""(to) => { const p = [...document.querySelectorAll('#ar path.ln.pd')].find(p => p.dataset.from === to || p.dataset.to === to);
        const z = +document.getElementById('stage').dataset.zoom, d = getComputedStyle(p).strokeDasharray.split(/[ ,]+/).map(parseFloat);
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
    assert dpage.get_attribute('#tools [data-tool="annotate"]', "aria-pressed") != "true", "보기는 주석 달기를 켜지 않는다"
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
    dpage.locator(sel).first.click()                 # H16: 글자 도구로 한 번 누르면 카드 글 상자, 글자 자리는 그 정책 줄
    li = dpage.locator('.card[data-id="job"] .capbox ul[data-f="policies"] > li').first
    assert li.is_visible() and li.text_content() == old
    assert dpage.evaluate("document.activeElement === document.querySelector('.card[data-id=\"job\"] .capbox ul[data-f=\"policies\"] > li')")
    dpage.keyboard.press("Control+a")
    dpage.keyboard.type("새 정책 문장")
    dpage.keyboard.press("Control+Enter")
    wait_notes(dpage, n0 + 1)
    n = notes_of(dpage)[-1]
    assert n["edit"] == "policy" and n["index"] == 0 and "policies[0]" in n["path"], n
    assert dpage.locator(sel).first.text_content() == "새 정책 문장" and "pend" in dpage.locator(sel).first.get_attribute("class")
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    assert dpage.locator(sel).first.text_content() == old
    dpage.keyboard.press("h")


def test_caption_one_box_edits_all_fields(dpage):
    """H16: 카드 아래 글(제목·설명·정책 줄)은 한 상자에서 고친다 — 바뀐 칸마다 반영 대기 편집, 되돌리기는 한 번에, Esc 는 버린다."""
    from test_canvas_baseline import empty_point
    fit_view(dpage)
    __import__("test_canvas_v2").zoom_to(dpage, "job", 200)
    card = '.card[data-id="job"]'
    t_sel, d_sel, p_sel = card + ' .ftitle', card + ' .fdesc', card + ' ul.pol li'
    bring_into_view(dpage, d_sel)
    old_desc = dpage.text_content(d_sel)
    old_pol = dpage.locator(p_sel).first.text_content()
    n0 = len(notes_of(dpage))
    dpage.dblclick(d_sel)
    box = dpage.locator(card + ' .capbox')
    assert box.is_visible()
    ttl, desc, pols = box.locator('[data-f="title"]'), box.locator('[data-f="purpose"]'), box.locator('ul[data-f="policies"] > li')
    old_title = ttl.text_content()
    assert old_title and dpage.text_content(t_sel).endswith(old_title)
    assert desc.text_content() == old_desc and pols.count() == len(dpage.locator(p_sel).all_text_contents())
    assert pols.first.text_content() == old_pol
    assert not dpage.locator(t_sel).is_visible() and not dpage.locator(d_sel).is_visible(), "상자가 카드 아래 글 자리를 대신한다"
    assert "Esc 취소" in box.locator(".capfoot").text_content()
    ttl.click()
    dpage.keyboard.press("Control+a")
    dpage.keyboard.type("한 상자 제목")
    pols.first.click()
    dpage.keyboard.press("Control+a")
    dpage.keyboard.type("한 상자 정책")
    ESHOTS.mkdir(parents=True, exist_ok=True)
    dpage.screenshot(path=str(ESHOTS / "h16-caption-box.png"))
    assert len(notes_of(dpage)) == n0, "상자를 닫기 전에는 편집이 아니다"
    e = empty_point(dpage)
    dpage.mouse.click(e["x"], e["y"])                # 밖을 누르면 저장
    wait_notes(dpage, n0 + 2)
    assert not box.count()
    ns = notes_of(dpage)[-2:]
    assert sorted((n["edit"], n.get("index")) for n in ns) == [("policy", 0), ("title", None)], ns
    assert all(n["screen"] == "job" and "screens.json" in n["path"] for n in ns), ns
    assert dpage.text_content(t_sel).endswith("한 상자 제목") and "pend" in dpage.get_attribute(t_sel, "class")
    assert dpage.locator(p_sel).first.text_content() == "한 상자 정책" and "pend" in dpage.locator(p_sel).first.get_attribute("class")
    assert dpage.text_content(d_sel) == old_desc and "pend" not in dpage.get_attribute(d_sel, "class"), "안 바꾼 칸은 편집이 아니다"
    dpage.keyboard.press("Control+z")                # 한 번 되돌리면 두 칸 다
    wait_notes(dpage, n0)
    assert dpage.text_content(t_sel).endswith(old_title) and "pend" not in dpage.get_attribute(t_sel, "class")
    assert dpage.locator(p_sel).first.text_content() == old_pol
    dpage.dblclick(d_sel)                            # 다시 열고 Esc = 버리기
    assert box.is_visible()
    dpage.keyboard.press("Control+a")
    dpage.keyboard.type("버릴 설명")
    dpage.keyboard.press("Escape")
    assert not box.count()
    dpage.wait_for_timeout(200)
    assert len(notes_of(dpage)) == n0 and dpage.text_content(d_sel) == old_desc


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
    return pg.evaluate("(() => { const b = document.getElementById('selbar'); return b && !b.hidden ? [...b.querySelectorAll('button')].filter(x => !x.hidden).map(x => x.getAttribute('aria-label')) : null; })()")


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
    dpage.click('#selbar [data-act="del"]')
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
    into = lambda: [l for l in lines(dpage) if (l["from"], l["to"]) == ("job", "language") or ((l["from"], l["to"]) == ("language", "job") and l["both"])]
    assert into() == [], "그 화면으로 오는 선이 바로 사라진다(반대 방향 language → job 은 남는다)"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(250)
    assert into(), "되돌리면 돌아온다"
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
    """기존 연결과 같은 도착으로 합쳐진 반영 대기는 선을 점선으로 만들지 않는다(점선 = 반영 대기로만 있는 쌍)."""
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
    assert cls and not any("pd" in c for c in cls), ("기존 연결이 섞인 쌍의 선은 실선", cls)
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(250)
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
    dpage.wait_for_function("!document.getElementById('legend').hidden", timeout=5000)
    assert dpage.evaluate("document.querySelector('.card.focus').dataset.id") == "job"
    dpage.wait_for_timeout(300)
    assert sel_sock(dpage), "연결 보기가 그려진 뒤에도 고른 요소의 소켓은 남는다"
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("h")


def test_cutting_a_pending_line_cancels_that_edit(dpage):
    """E4: 아직 반영 안 된(점선) 연결을 자르면 '연결 끊기' 메모가 아니라 그 편집이 취소된다. 되돌리기 = 점선이 돌아온다."""
    focus_dayfine(dpage, "job")
    dpage.keyboard.press("l")
    s = dpage.evaluate("""(() => { const s = [...document.querySelectorAll('.sock')].find(n => getComputedStyle(n).display !== 'none');
        const r = s.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2, to: s.dataset.to}; })()""")
    n0 = len(notes_of(dpage))
    q = visible_cover(dpage, skip=["job", s["to"]])
    drag(dpage, s, q["x"] - s["x"], q["y"] - s["y"])
    wait_notes(dpage, n0 + 1)
    dpage.wait_for_timeout(250)
    assert all("pd" in c for c in lk_to(dpage, q["id"])), "새 도착 선은 반영 대기(점선)"
    sel = tag_sel("job", q["id"])                    # 왼쪽 통로는 선이 촘촘해 그어 자르기는 이웃 선도 건드린다 — 그 선의 태그 메뉴 '끊기'(같은 자르기 경로)
    bring_into_view(dpage, sel)
    dpage.click(sel, button="right")
    pick(dpage, "끊기")
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
    D9: [주요 흐름] 버튼·표시 패널 체크·A 키는 없다."""
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
    want = set(dpage.evaluate("[...document.querySelectorAll('#lgRows .lgrow')].map(r => r.dataset.to)"))
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


# ---------------------------------------------------------------- 조각 2.5d 선 체계 하나 (E20·E21, rework §7-3)
LN_OF_JS = """(id) => [...document.querySelectorAll('#ar path.ln')].filter(p => p.dataset.from === id || p.dataset.to === id)
    .map(p => ({key: p.dataset.from + '>' + p.dataset.to, stroke: p.getAttribute('stroke'), d: p.getAttribute('d'),
                on: p.classList.contains('on'), op: +getComputedStyle(p).opacity}))"""


def test_click_keeps_the_same_lines_and_numbers_buttons(dpage):
    """E20 A: 카드를 누르면 새 선을 그리지 않는다 — 그 카드의 늘 보이는 선이 같은 색·같은 길로 진해지고, 나머지는 흐려진다.
    화면 안 출발 버튼은 그 선과 같은 색 테두리 + 번호, 선 태그에도 같은 번호."""
    fit_view(dpage)
    from test_canvas_v2 import zoom_to
    zoom_to(dpage, "job", 330)
    before = {l["key"]: l for l in dpage.evaluate(LN_OF_JS, "job")}
    assert before, "job 에 늘 보이는 선이 있어야 한다"
    d = dpage.locator("#dock").bounding_box()
    dpage.mouse.move(d["x"] + d["width"] / 2, d["y"] + d["height"] - 20)   # 카드 위가 아니게(마우스를 올린 카드의 선은 따로 진해진다)
    dpage.evaluate(CLICK, "job")
    dpage.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
    fr = frame_of(dpage, "job")
    fr.wait_for_function("document.querySelectorAll('[data-hd-links]').length >= 1", timeout=5000)
    dpage.wait_for_timeout(400)
    assert dpage.locator("#lks path.lk").count() == 0, "연결 보기 전용 선은 그리지 않는다"
    after = {l["key"]: l for l in dpage.evaluate(LN_OF_JS, "job")}
    assert after.keys() == before.keys()
    for k, l in after.items():
        assert l["stroke"] == before[k]["stroke"] and l["d"] == before[k]["d"], ("같은 색·같은 길", k, before[k], l)
        assert l["on"] and l["op"] > 0.9, ("그 카드의 선은 진하게", k, l)
    others = [l for l in lines(dpage) if "job" not in (l["from"], l["to"]) and l["shown"]]
    assert others and all(l["op"] < 0.3 for l in others), "나머지 선은 흐리게"
    paint = fr.evaluate("""[...document.querySelectorAll('[data-hd-links]')].map(d => ({color: getComputedStyle(d).borderTopColor,
        n: (d.querySelector('span') || {}).textContent || ''}))""")
    assert all(p["n"] for p in paint), ("출발 버튼마다 번호", paint)
    def rgb(hx):
        return "rgb(%d, %d, %d)" % (int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16))
    colors = {rgb(l["stroke"]) for l in after.values()}
    assert {p["color"] for p in paint} <= colors, ("버튼 테두리 = 그 선의 색", paint, colors)
    tags = dpage.evaluate("""[...document.querySelectorAll('#rows .alabel.on')].filter(n => n.dataset.from === 'job' && getComputedStyle(n).display !== 'none')
        .map(n => n.textContent)""")
    assert tags and {t[0] for t in tags} <= {p["n"] for p in paint}, ("선 태그에 같은 번호", tags, paint)
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Escape")


def test_shift_select_keeps_every_picked_card_bright(dpage):
    """E21: Shift 로 여러 장 고르면 고른 카드 모두 또렷하고 그 카드들의 선이 진하다(두 번째 카드가 흐려지지 않는다)."""
    fit_view(dpage)
    p = visible_cover(dpage)
    q = visible_cover(dpage, skip=[p["id"]])
    dpage.mouse.click(p["x"], p["y"])
    dpage.keyboard.down("Shift"); dpage.mouse.click(q["x"], q["y"]); dpage.keyboard.up("Shift")
    dpage.wait_for_timeout(400)
    ops = dpage.evaluate("(ids) => ids.map(id => +getComputedStyle(document.querySelector('.card[data-id=\"' + id + '\"]')).opacity)", [p["id"], q["id"]])
    assert all(o > 0.95 for o in ops), ("고른 카드 모두 또렷", ops)
    for cid in (p["id"], q["id"]):
        ls = dpage.evaluate(LN_OF_JS, cid)
        assert all(l["on"] and l["op"] > 0.9 for l in ls), ("고른 카드의 선은 모두 진하게", cid, ls)
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Escape")


# ---------------------------------------------------------------- 조각 2.5c 연결 패널 (E13, rework §8-3)
def test_link_panel_trash_and_rename(dpage):
    """E13: 연결 패널 = 고른 화면의 연결(선과 같은 번호). 줄마다 휴지통 = 그 연결 하나 끊기(되돌리기), 이름 = 선 태그 이름(hd-link-names)."""
    focus_dayfine(dpage, "job")
    row = '#lgRows .lgrow[data-from="job"][data-to="language"]'
    assert dpage.text_content(f"{row} .lgdot") == dpage.text_content(tag_sel("job", "language")).split(" ", 1)[0], "패널 번호 = 선 태그 번호"
    n0 = len(notes_of(dpage))
    dpage.click(f"{row} button.lgcut")
    dpage.wait_for_function("(n) => " + NOTES_JS + ".length > n", arg=n0, timeout=4000)
    new = notes_of(dpage)[n0:]
    assert new and all(n["op"] == "cut" and n["screen"] == "job" and n["to"] == "language" for n in new), new
    assert "끊었어요" in dpage.text_content("#toast")
    dpage.wait_for_timeout(250)
    assert dpage.locator(tag_sel("job", "language")).count() == 0 and dpage.locator(row).count() == 0, "끊은 연결은 선 태그·패널에서 바로 빠진다"
    dpage.keyboard.press("Control+z")
    wait_notes(dpage, n0)
    dpage.wait_for_timeout(250)
    assert dpage.locator(row).count() == 1, "되돌리면 돌아온다"
    dpage.click(f"{row} button.lgname")
    inp = dpage.locator(f"{row} input")
    inp.fill("언어 고르기로")
    inp.press("Enter")
    dpage.wait_for_timeout(200)
    assert tag_text(dpage, "job", "language") == "언어 고르기로", "패널에서 바꾼 이름 = 선 태그 이름"
    assert "언어 고르기로" in dpage.text_content(row)
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(200)
    assert tag_text(dpage, "job", "language") != "언어 고르기로"
    dpage.keyboard.press("Escape")


# ---------------------------------------------------------------- 조각 2 메모·반영 대기·기록 (E2·E5·E8·E16, rework §8-3)
HIST_JS = """[...document.querySelectorAll('#hlist li[data-i]')].map(li => ({i: +li.dataset.i, label: (li.querySelector('.hl') || {}).textContent || '',
    status: (li.querySelector('.hs') || {}).textContent || '', undone: li.classList.contains('undone'), lock: li.classList.contains('lock')}))"""


def test_memo_pending_history_panels(dpage):
    """E5: 기계적 편집(끊기)은 반영 대기 패널, AI 요청(메모)은 메모 패널 — 탭에 배지 수. E16: 보내기는 한 자리(#nsend).
    E2·E8: 기록 패널 = 시간줄 하나 — 줄마다 상태, 줄을 누르면 그 단계로, 보낸 뒤는 경계선 아래로 되돌릴 수 없다."""
    focus_dayfine(dpage, "job")
    n0 = len(notes_of(dpage))
    dpage.click('#lgRows .lgrow[data-from="job"][data-to="language"] button.lgcut')
    dpage.wait_for_function("(n) => " + NOTES_JS + ".length > n", arg=n0, timeout=4000)
    k = len(notes_of(dpage)) - n0
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("m")
    c = visible_cover(dpage)
    dpage.mouse.click(c["x"], c["y"])
    dpage.wait_for_selector("#pop:not([hidden])")
    dpage.fill("#pnote", "패널 나누기 확인")
    dpage.click("#padd")
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("h")
    wait_notes(dpage, n0 + k + 1)
    memos = dpage.evaluate("[...document.querySelectorAll('#nlist li')].map(li => li.textContent)")
    pend = dpage.evaluate("[...document.querySelectorAll('#plist li')].map(li => li.textContent)")
    assert any("패널 나누기 확인" in t for t in memos) and not any("연결 끊기" in t for t in memos), memos
    assert len([t for t in pend if "연결 끊기" in t]) == k and not any("패널 나누기 확인" in t for t in pend), pend
    assert dpage.text_content('#dock .dk-tab[data-p="notes"] .dk-cnt') == str(len(memos))
    assert dpage.text_content('#dock .dk-tab[data-p="pending"] .dk-cnt') == str(len(pend))
    assert dpage.locator("#nsend").count() == 1 and dpage.evaluate("!!document.getElementById('nsend').closest('header')"), "주 행동은 위쪽 줄 한 자리"
    assert dpage.text_content("#nsendc") == str(len([n for n in notes_of(dpage) if not n.get("sent")])), "보내기에 안 보낸 건수"
    dpage.click('#dock .dk-tab[data-p="history"]')
    h = dpage.evaluate(HIST_JS)
    cut = [r for r in h if r["label"] == "선 자르기"][-1]
    assert cut["status"] == "반영 대기" and not cut["undone"], h
    dpage.click(f'#hlist li[data-i="{cut["i"] - 1}"]')                # 끊기 바로 앞 단계로
    wait_notes(dpage, n0 + 1)
    assert [r for r in dpage.evaluate(HIST_JS) if r["i"] == cut["i"]][0]["undone"], "되돌린 줄은 흐리게 남는다(다시 하기)"
    dpage.click(f'#hlist li[data-i="{cut["i"]}"]')                    # 다시 그 단계로
    wait_notes(dpage, n0 + k + 1)
    dpage.click("#nsend")                                              # 기록 탭이 앞이어도 위쪽 줄에서 바로
    dpage.wait_for_timeout(300)
    h = dpage.evaluate(HIST_JS)
    assert [r for r in h if r["i"] == cut["i"]][0]["status"] == "AI에 보냄", h
    assert dpage.locator("#hlist .hbound").count() == 1, "보낸 자리에 경계선"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_timeout(200)
    assert len(notes_of(dpage)) == n0 + k + 1 and "되돌릴 수 없어요" in dpage.text_content("#toast"), "보낸 것은 되돌리지 않는다"
    dpage.click('#dock .dk-tab[data-p="notes"]')
    dpage.click("#nclear")
    dpage.wait_for_timeout(150)


def test_file_mode_chip(epage):                                            # 2.2 E9 — 파일로 열면 바로 쓰기가 안 된다고 위쪽 줄에 늘 보인다
    assert epage.text_content("#mode") == "파일로 열림 · 바로 쓰기 안 됨"
    assert "도우미" not in epage.text_content("header"), "화면 글에 '도우미' 말을 쓰지 않는다"


# ---------------------------------------------------------------- 조각 3 보기·창 메뉴 (H1·H2·H4·H11·G4)
def zoom_of(pg):
    return round(float(pg.evaluate("document.getElementById('stage').dataset.zoom")), 3)


def test_view_and_window_menus(dpage):
    """H1·H2: 배율 칩 `72% ▾` = 보기 메뉴(전체 보기 0 · 100% 1 · 확대 · 축소 · 고른 화면에 맞추기) — 따로 있던 [전체 보기]·[전환] 버튼 없음.
    H4·H11: [창 ▾] = 도구 막대·패널마다·판 아래 안내 켜고 끄기(체크) + 작업 영역 되돌리기, Tab = 패널 모두 숨기기.
    G4: 전환 메뉴 없음 — T = 글자 도구(E 도 그대로), 움직임 줄이기는 표시 패널 체크 하나."""
    errs = []
    dpage.on("pageerror", lambda e: errs.append(str(e)))
    dpage.keyboard.press("Escape")
    assert dpage.locator("#tbtn, #tmenu").count() == 0, "전환 버튼·메뉴는 없앤다(G4)"
    assert dpage.locator("header #fit").count() == 0, "[전체 보기]는 위쪽 줄 버튼이 아니다"
    assert dpage.text_content("#zoom").strip().endswith("▾")
    # 보기 메뉴 — 화면 아이콘 단추로도 연다(배율 칩만 누르면 열린다는 게 어색하다는 피드백)
    dpage.click("#vbtn")
    dpage.wait_for_selector("#vmenu:not([hidden])")
    assert dpage.get_attribute("#vbtn", "aria-expanded") == "true"
    dpage.click("#vbtn")
    dpage.wait_for_selector("#vmenu", state="hidden")
    dpage.click("#zoom")
    dpage.wait_for_selector("#vmenu:not([hidden])")
    dpage.click("#fit")
    dpage.wait_for_selector("#vmenu", state="hidden")
    zf = zoom_of(dpage)
    dpage.click("#zoom"); dpage.click('#vmenu [data-z="100"]')
    assert zoom_of(dpage) == 1.0
    dpage.click("#zoom"); dpage.click('#vmenu [data-z="out"]')
    assert zoom_of(dpage) < 1.0
    assert dpage.is_visible("#vmenu"), "확대·축소는 여러 번 누르게 메뉴를 열어 둔다"
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("1")
    assert zoom_of(dpage) == 1.0, "1 = 100%"
    dpage.keyboard.press("0")
    assert zoom_of(dpage) == zf, "0 = 전체 보기"
    focus_dayfine(dpage, "job")
    dpage.click("#zoom"); dpage.click('#vmenu [data-z="pick"]')
    box = dpage.evaluate("""() => { const c = document.querySelector('.card[data-id="job"]').getBoundingClientRect(),
        p = document.getElementById('screens').getBoundingClientRect();
        return c.left >= p.left && c.right <= p.right && c.top >= p.top && c.bottom <= p.bottom && c.height > p.height * 0.5; }""")
    assert box, "고른 화면에 맞추기 = 그 카드가 판을 채운다"
    # 창 메뉴
    dpage.keyboard.press("Escape")
    dpage.click("#wbtn")
    dpage.wait_for_selector("#wmenu:not([hidden])")
    rows = dpage.evaluate("[...document.querySelectorAll('#wmenu [data-w]')].map(r => [r.dataset.w, r.getAttribute('aria-checked'), r.textContent.trim()])")
    keys = [r[0] for r in rows]
    assert keys[:2] == ["tools", "hint"] and set(["links", "show", "notes", "pending", "history", "layers"]) <= set(keys), rows
    assert all(r[2] for r in rows), "줄마다 짧은 이름(H11)"
    assert all(r[1] == ("false" if r[0] == "theme" else "true") for r in rows), "체크 = 실제로 켜져 있는지(테마 패널은 처음엔 꺼짐)"
    dpage.click('#wmenu [data-w="tools"]')
    assert dpage.is_hidden("#tools")
    dpage.click('#wmenu [data-w="history"]')
    assert dpage.locator('#dock .dk-tab[data-p="history"]').count() == 0
    assert dpage.get_attribute('#wmenu [data-w="history"]', "aria-checked") == "false"
    dpage.click('#wmenu [data-w="history"]')
    assert dpage.locator('#dock .dk-tab[data-p="history"]').count() == 1, "다시 켜면 그 패널이 열린다"
    dpage.click('#wmenu [data-w="hint"]')
    assert dpage.is_hidden("#khint")
    dpage.click('#wmenu [data-act="reset"]')
    assert dpage.is_visible("#tools") and dpage.is_visible("#khint"), "작업 영역 되돌리기"
    dpage.keyboard.press("Escape")
    dpage.wait_for_selector("#wmenu", state="hidden")
    # Tab = 패널 모두 숨기기 / 다시
    dpage.mouse.click(5, 300)
    dpage.keyboard.press("Tab")
    assert dpage.is_hidden("#dock") and dpage.is_hidden("#tools")
    dpage.keyboard.press("Tab")
    assert dpage.is_visible("#dock") and dpage.is_visible("#tools")
    # T = 글자 도구, E 도
    dpage.keyboard.press("h"); dpage.keyboard.press("t")
    assert dpage.get_attribute('#tools [data-tool="text"]', "aria-pressed") == "true"
    dpage.keyboard.press("h"); dpage.keyboard.press("e")
    assert dpage.get_attribute('#tools [data-tool="text"]', "aria-pressed") == "true"
    dpage.keyboard.press("h")
    # 움직임 줄이기 = 표시 패널 체크
    dpage.click('#dock .dk-tab[data-p="show"]')
    dpage.check("#mvOff")
    assert dpage.evaluate("document.body.classList.contains('nomotion') && JSON.parse(localStorage.getItem('hd-canvas-prefs')).motion === false")
    dpage.uncheck("#mvOff")
    assert not dpage.evaluate("document.body.classList.contains('nomotion')")
    assert not errs, errs


# ---------------------------------------------------------------- 조각 4 레이어 (H6·H7)
LAYERS_JS = """() => [...document.querySelectorAll('#lyTree [data-ly]')].filter(r => r.offsetParent).map(r => ({
    id: r.dataset.ly, kind: r.dataset.kind, name: (r.querySelector('.ly-name') || {}).textContent || '',
    hid: r.classList.contains('hid'), lock: r.classList.contains('locked'), memo: (r.querySelector('.ly-cnt') || {}).textContent || ''}))"""


def layers(pg):
    return pg.evaluate(LAYERS_JS)


def card_spot(pg, sid):
    return pg.evaluate("(id) => { const c = document.querySelector('.card[data-id=\"' + id + '\"]'); return [c.offsetLeft, c.offsetTop, c.style.transform]; }", sid)



TRANSLATE_JS = r"(sel) => { const m = /translate\(([-\d.]+)px,\s*([-\d.]+)px\)/.exec(document.querySelector(sel).style.transform); return [+m[1], +m[2]]; }"


def test_split_view_left_right_and_sync(dpage):
    """H2·H3(조각 6, 범위 A): 보기 메뉴 → 좌우로 나누기 = 오른쪽 칸(보기 전용 판 복사본, 따로 이동·배율, 작은 배율 칩).
    동시 스크롤은 나눴을 때만 — 켜면 한 칸을 움직일 때 다른 칸도 같은 만큼. 나누지 않기 = 칸이 사라지고 판이 다시 넓어짐."""
    errs = []
    dpage.on("pageerror", lambda e: errs.append(str(e)))
    dpage.keyboard.press("Escape")
    w0 = dpage.locator("#screens").bounding_box()["width"]
    dpage.click("#zoom")
    assert dpage.is_disabled('#vmenu [data-act="sync"]'), "나누지 않았으면 동시 스크롤은 못 누른다"
    dpage.click('#vmenu [data-split="lr"]')
    dpage.wait_for_selector("#vp2")
    assert dpage.get_attribute('#vmenu [data-split="lr"]', "aria-checked") == "true"
    a, b = dpage.locator("#screens").bounding_box(), dpage.locator("#vp2").bounding_box()
    assert abs(a["width"] - b["width"]) < 3 and abs(a["x"] + a["width"] - b["x"]) < 3 and a["width"] < w0 * 0.6, (a, b, w0)
    n = dpage.evaluate("[document.querySelectorAll('#rows .card').length, document.querySelectorAll('#vp2 .card').length, document.querySelectorAll('#vp2 [id]').length]")
    assert n[0] == n[1] > 0 and n[2] == 0, ("복사본 = 같은 카드, id 는 겹치지 않게", n)
    assert dpage.evaluate("document.querySelector('#vp2 .vp2-stage').inert"), "오른쪽 칸은 보기 전용"
    dpage.wait_for_timeout(600)
    ESHOTS.mkdir(parents=True, exist_ok=True)
    dpage.screenshot(path=str(ESHOTS / "6-split-lr.png"))
    dpage.keyboard.press("Escape")
    main0, side0 = dpage.evaluate(TRANSLATE_JS, "#stage"), dpage.evaluate(TRANSLATE_JS, "#vp2 .vp2-stage")
    dpage.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    dpage.mouse.wheel(0, 120)
    dpage.wait_for_timeout(100)
    side1 = dpage.evaluate(TRANSLATE_JS, "#vp2 .vp2-stage")
    assert abs(side1[1] - (side0[1] - 120)) < 1 and dpage.evaluate(TRANSLATE_JS, "#stage") == main0, "칸마다 따로 이동"
    z0 = dpage.text_content("#vp2 .pz")
    dpage.keyboard.down("Control"); dpage.mouse.wheel(0, -200); dpage.keyboard.up("Control")
    dpage.wait_for_timeout(100)
    assert dpage.text_content("#vp2 .pz") != z0 and dpage.evaluate(TRANSLATE_JS, "#stage") == main0, "칸마다 따로 배율(칩)"
    # 동시 스크롤
    dpage.click("#zoom"); dpage.click('#vmenu [data-act="sync"]')
    assert dpage.get_attribute('#vmenu [data-act="sync"]', "aria-checked") == "true"
    dpage.keyboard.press("Escape")
    side1 = dpage.evaluate(TRANSLATE_JS, "#vp2 .vp2-stage")
    dpage.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
    dpage.mouse.wheel(0, 90)
    dpage.wait_for_timeout(100)
    main1, side2 = dpage.evaluate(TRANSLATE_JS, "#stage"), dpage.evaluate(TRANSLATE_JS, "#vp2 .vp2-stage")
    assert abs((main1[1] - main0[1]) - (side2[1] - side1[1])) < 1 and main1[1] != main0[1], ("왼쪽을 움직이면 오른쪽도", main0, main1, side1, side2)
    dpage.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    dpage.mouse.wheel(0, 60)
    dpage.wait_for_timeout(100)
    main2, side3 = dpage.evaluate(TRANSLATE_JS, "#stage"), dpage.evaluate(TRANSLATE_JS, "#vp2 .vp2-stage")
    assert abs((main2[1] - main1[1]) + 60) < 1 and abs((side3[1] - side2[1]) + 60) < 1, "오른쪽을 움직여도 왼쪽이 같은 만큼(한 번만)"
    # 나누지 않기
    dpage.click("#zoom"); dpage.click('#vmenu [data-split="one"]')
    assert dpage.locator("#vp2").count() == 0
    assert abs(dpage.locator("#screens").bounding_box()["width"] - w0) < 3
    assert dpage.is_disabled('#vmenu [data-act="sync"]') and dpage.get_attribute('#vmenu [data-act="sync"]', "aria-checked") == "false"
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("0")
    assert not errs, errs

def test_layers_panel_tree_hide_lock_search(dpage):
    """H6: 레이어 패널 = 줄(묶음, 접기) 아래 화면 — 줄마다 눈(숨김)·이름·잠금·메모 수, 위 검색(화면·줄 이름) + 거르기 아이콘,
    누르면 그 카드로, 아래 막대(빈 레이아웃·숨기기·잠그기·삭제). H7: 숨긴 화면 패널은 없애고 판 글(소개·끝 글)도 레이어 —
    왼쪽 [숨긴 화면]은 레이어를 '숨긴 것만'으로 연다. 잠금 = 옮기기·삭제·글자 고치기를 막는다(되돌리기 됨)."""
    errs = []
    dpage.on("pageerror", lambda e: errs.append(str(e)))
    dpage.keyboard.press("Escape")
    assert dpage.locator("#pHidden, #hidl").count() == 0 and dpage.locator('#dock .dk-tab[data-p="hidden"]').count() == 0
    dpage.click('#dock .dk-tab[data-p="layers"]')
    ls = layers(dpage)
    groups = dpage.evaluate("[...document.querySelectorAll('#rows .flow .glabel')].map(g => g.textContent)")
    cards = dpage.evaluate("[...document.querySelectorAll('#rows .card:not(.del)')].map(c => c.dataset.id)")
    assert [l["name"] for l in ls if l["kind"] == "row" and l["id"] != "@drafts"] == groups, ls
    assert [l["id"] for l in ls if l["kind"] == "screen"] == cards
    assert {"@intro", "@foot"} <= {l["id"] for l in ls if l["kind"] == "text"}, "판 글도 레이어(H7)"
    sid = "job"
    title = dpage.get_attribute(f'.card[data-id="{sid}"] .cover', "data-title")
    # 검색: 화면 이름
    dpage.fill("#lyQ", title)
    assert [l["id"] for l in layers(dpage) if l["kind"] == "screen"] == [sid]
    dpage.fill("#lyQ", "")
    # 누르면 그 카드로 + 고르기
    dpage.click(f'#lyTree [data-ly="{sid}"] .ly-name')
    assert dpage.evaluate("(id) => { const c = document.querySelector('.card[data-id=\"' + id + '\"]').getBoundingClientRect(), p = document.getElementById('screens').getBoundingClientRect();"
                          " return document.querySelector('.card[data-id=\"' + id + '\"]').classList.contains('picked') && c.left >= p.left && c.right <= p.right && c.top >= p.top && c.bottom <= p.bottom; }", sid)
    # 눈 = 숨김, 왼쪽 [숨긴 화면] = 숨긴 것만
    dpage.click(f'#lyTree [data-ly="{sid}"] .ly-eye')
    assert not dpage.locator(f'.card[data-id="{sid}"]').is_visible()
    assert dpage.is_visible("#thid")
    dpage.click('#dock .dk-tab[data-p="links"]')
    dpage.click("#thid")
    assert dpage.get_attribute('#lyF [data-f="hidden"]', "aria-pressed") == "true"
    assert [l["id"] for l in layers(dpage) if l["kind"] not in ("row", "folder")] == [sid], layers(dpage)
    dpage.click(f'#lyTree [data-ly="{sid}"] .ly-eye')
    assert dpage.locator(f'.card[data-id="{sid}"]').is_visible()
    dpage.click('#lyF [data-f="hidden"]')
    # 판 글 숨기기
    dpage.click('#lyTree [data-ly="@intro"] .ly-eye')
    assert dpage.is_hidden("#intro")
    dpage.click('#lyTree [data-ly="@intro"] .ly-eye')
    assert dpage.is_visible("#intro")
    # 줄 접기
    row0 = [l for l in layers(dpage) if l["kind"] == "row"][0]["id"]
    n0 = len(layers(dpage))
    dpage.click(f'#lyTree [data-ly="{row0}"] .ly-fold')
    assert len(layers(dpage)) < n0
    dpage.click(f'#lyTree [data-ly="{row0}"] .ly-fold')
    # 잠금: 옮기기·삭제 막음, 되돌리기
    dpage.click(f'#lyTree [data-ly="{sid}"] .ly-lock')
    assert [l for l in layers(dpage) if l["id"] == sid][0]["lock"]
    assert dpage.evaluate("Object.keys(localStorage).some(k => k.startsWith('hd-locked:'))")
    focus_dayfine(dpage, sid)
    before = card_spot(dpage, sid)
    dpage.keyboard.press("v")
    b = dpage.locator(f'.card[data-id="{sid}"] .cover').bounding_box()
    dpage.mouse.move(b["x"] + b["width"] / 2, b["y"] + 60); dpage.mouse.down()
    dpage.mouse.move(b["x"] + b["width"] / 2 + 120, b["y"] + 140, steps=6); dpage.mouse.up()
    assert card_spot(dpage, sid) == before, "잠긴 카드는 옮겨지지 않는다"
    assert "잠긴" in (dpage.text_content("#toast") or "")
    dpage.keyboard.press("h")
    n_notes = len(notes_of(dpage))
    dpage.evaluate("(id) => document.querySelector('.card[data-id=\"' + id + '\"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))", sid)
    dpage.keyboard.press("Delete")
    dpage.wait_for_timeout(200)
    assert dpage.locator(f'.card[data-id="{sid}"]').is_visible() and len(notes_of(dpage)) == n_notes, "잠긴 카드는 지워지지 않는다"
    dpage.keyboard.press("Escape")
    dpage.keyboard.press("Control+z")
    assert not [l for l in layers(dpage) if l["id"] == sid][0]["lock"], "잠금도 되돌리기"
    # 아래 막대: 고른 화면 숨기기
    dpage.click(f'#lyTree [data-ly="{sid}"] .ly-name')
    dpage.click('#lyBar [data-act="hide"]')
    assert not dpage.locator(f'.card[data-id="{sid}"]').is_visible()
    dpage.keyboard.press("Control+z")
    assert dpage.locator(f'.card[data-id="{sid}"]').is_visible()
    assert not errs, errs


# ---------------------------------------------------------------- 크게 보기 위쪽 줄 (G7 · 사용자 10-22 → H15 사용자 10-23)
def test_modal_header_has_no_gap_and_no_text_close(dpage):
    """크게 보기: 덮개는 위쪽 줄 아래부터 — 도크 위에 빈 칸이 남지 않는다. 위쪽 줄은 그대로(탭 보임, H15),
    화면 제목과 닫기 아이콘(×)은 그 창 위 제목 막대. 글자 [닫기] 버튼은 없고, 바깥(덮개)을 누르거나 × · Esc 로 닫힌다."""
    dpage.keyboard.press("Escape")
    dpage.click("#zoom"); dpage.click("#fit")
    c = visible_cover(dpage)
    dpage.mouse.dblclick(c["x"], c["y"])
    dpage.wait_for_function("!document.getElementById('modal').hidden")
    g = dpage.evaluate("""() => { const hd = document.querySelector('.hd').getBoundingClientRect(), m = document.getElementById('modal').getBoundingClientRect(),
        dk = document.getElementById('dock').getBoundingClientRect(), t = document.getElementById('mtitle').getBoundingClientRect(),
        tabs = document.querySelector('.hd .tabs'), x = document.getElementById('mclose'), f = document.getElementById('mframe').getBoundingClientRect();
      return {modalTop: m.top, hdBottom: hd.bottom, dockTop: dk.top, titleInModal: t.top >= hd.bottom && t.bottom <= f.top + 1 && t.width > 0,
              tabsVisible: getComputedStyle(tabs).visibility === 'visible', closeText: x.textContent.trim(), closeLabel: x.getAttribute('aria-label'),
              closeInModal: !!x.closest('#modal') && x.getBoundingClientRect().top >= hd.bottom}; }""")
    assert abs(g["modalTop"] - g["hdBottom"]) < 1 and abs(g["dockTop"] - g["hdBottom"]) < 1, g
    assert g["titleInModal"] and g["tabsVisible"], g
    assert g["closeText"] != "닫기" and g["closeLabel"] == "닫기" and g["closeInModal"], g
    assert dpage.is_hidden("#selbar"), "크게 보기 위에 선택 막대가 뜨지 않는다(두 번 누르기의 첫 누르기가 고른 카드)"
    m = dpage.locator("#modal").bounding_box()
    assert dpage.evaluate("([x, y]) => document.elementFromPoint(x, y).id", [m["x"] + 12, m["y"] + m["height"] - 12]) == "modal"
    dpage.mouse.click(m["x"] + 12, m["y"] + m["height"] - 12)            # 화면 바깥 덮개(왼쪽 아래 구석)
    dpage.wait_for_function("document.getElementById('modal').hidden")
    dpage.mouse.dblclick(c["x"], c["y"])
    dpage.wait_for_function("!document.getElementById('modal').hidden")
    dpage.click("#mclose")
    dpage.wait_for_function("document.getElementById('modal').hidden")
    assert dpage.evaluate("getComputedStyle(document.querySelector('.hd .tabs')).visibility") == "visible"


HEADER_JS = """() => { const hd = document.querySelector('.hd'), r = hd.getBoundingClientRect();
  const kids = [...hd.querySelectorAll('*')].filter(e => e.getClientRects().length && getComputedStyle(e).visibility === 'visible')
    .map(e => { const b = e.getBoundingClientRect(); return [e.id || e.className.baseVal || e.className || e.tagName, Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)].join(' '); });
  return {box: [r.left, r.top, r.width, r.height], kids}; }"""


def test_header_compact_and_stable_on_modal(dpage):
    """H15: 위쪽 줄은 32px 한 줄(포토샵·블렌더식). 카드를 크게 봐도 위쪽 줄은 그대로 — 크기·보이는 것 모두 같다.
    화면 제목은 크게 보기 창 위 제목 막대(#mtitle, 화면 위), × 를 누르면 닫힌다."""
    dpage.keyboard.press("Escape")
    dpage.click("#zoom"); dpage.click("#fit")
    dpage.keyboard.press("Escape")
    h0 = dpage.evaluate(HEADER_JS)
    assert h0["box"][3] <= 34, h0["box"]
    c = visible_cover(dpage)
    title = dpage.evaluate("(id) => document.querySelector('.card[data-id=\"' + id + '\"] .ftitle').textContent.trim()", c["id"])
    dpage.mouse.dblclick(c["x"], c["y"])
    dpage.wait_for_function("!document.getElementById('modal').hidden")
    dpage.wait_for_timeout(300)                                          # 여는 움직임이 끝난 뒤
    h1 = dpage.evaluate(HEADER_JS)
    assert h1 == h0, (h0, h1)
    t = dpage.evaluate("""() => { const t = document.getElementById('mtitle'), f = document.getElementById('mframe');
      return {text: t.textContent.trim(), inModal: !!t.closest('#modal'), above: t.getBoundingClientRect().bottom <= f.getBoundingClientRect().top + 1,
              h: t.closest('.mbar').getBoundingClientRect().height}; }""")
    assert t["text"] and t["text"] in title or title in t["text"], (t, title)
    assert t["inModal"] and t["above"] and abs(t["h"] - 26) < 1, t
    ESHOTS.mkdir(parents=True, exist_ok=True)
    dpage.screenshot(path=str(ESHOTS / "h15-header-modal.png"))
    dpage.click("#mclose")
    dpage.wait_for_function("document.getElementById('modal').hidden")
    assert dpage.evaluate(HEADER_JS) == h0


# ---------------------------------------------------------------- 조각 7a 크게 보기 = 모드 · 선택 막대 아이콘 (G5·G6·G8)
TOOLS_JS = """() => [...document.querySelectorAll('#tools [data-tool]')].map(b => [b.dataset.tool, b.getAttribute('aria-pressed'), b.getAttribute('aria-disabled')])"""


def test_modal_keeps_tools_annotate_is_a_tool_and_selbar_icons(dpage):
    """G8: 선택 막대 = 아이콘 + 툴팁(이름·키). G5: 크게 보기에서도 왼쪽 도구 막대가 남는다 — 쓸 수 있는 도구는 손(눌러 보기)·주석뿐.
    G6: 화면 위 [주석 달기] 버튼은 없애고 왼쪽 주석 도구 하나로(P 도 같음). 닫으면 판의 도구로 돌아온다."""
    dpage.keyboard.press("Escape")
    dpage.click("#zoom"); dpage.click("#fit")
    c = visible_cover(dpage)
    dpage.mouse.click(c["x"], c["y"])
    dpage.wait_for_selector("#selbar:not([hidden])")
    bar = dpage.evaluate("[...document.querySelectorAll('#selbar button')].map(b => [b.dataset.act, b.textContent.trim(), b.getAttribute('aria-label'), !!b.querySelector('svg'), b.title])")
    assert [b[0] for b in bar] == ["memo", "hide", "del"], bar
    assert all(b[1] == "" and b[2] and b[3] and b[4] for b in bar), "아이콘만 · 이름은 aria-label · 툴팁"
    dpage.mouse.dblclick(c["x"], c["y"])
    dpage.wait_for_function("!document.getElementById('modal').hidden")
    assert dpage.locator("#mpick").count() == 0, "화면 위 [주석 달기] 버튼은 없다(G6)"
    assert dpage.is_visible("#tools"), "크게 보기에서도 도구 막대(G5)"
    t = {k: (p, d) for k, p, d in dpage.evaluate(TOOLS_JS)}
    assert t["hand"][1] != "true" and t["annotate"][1] != "true", t
    assert all(t[k][1] == "true" for k in ("move", "trigger", "knife", "layout", "memo")), t
    dpage.click('#tools [data-tool="annotate"]')
    assert dpage.get_attribute('#tools [data-tool="annotate"]', "aria-pressed") == "true"
    dpage.keyboard.press("p")
    assert dpage.get_attribute('#tools [data-tool="hand"]', "aria-pressed") == "true", "P 로 끄면 손(눌러 보기)"
    dpage.keyboard.press("p")
    assert dpage.get_attribute('#tools [data-tool="annotate"]', "aria-pressed") == "true"
    dpage.keyboard.press("Escape")
    dpage.wait_for_function("document.getElementById('modal').hidden")
    t = {k: (p, d) for k, p, d in dpage.evaluate(TOOLS_JS)}
    assert t["hand"][0] == "true" and all(d != "true" for p, d in t.values()), "닫으면 판의 도구(손)로, 모두 다시 쓸 수 있게"


# ---------------------------------------------------------------- 조각 5 테마 패널 (H10·H12·H14)
THEME_JS = """() => [...document.querySelectorAll('#thList [data-th]')].map(r => ({id: r.dataset.th, name: (r.querySelector('.th-name') || {}).textContent || '',
    on: r.classList.contains('on'), lock: !!r.querySelector('.th-lock'), del: !!r.querySelector('[data-act="del"]')}))"""


def theme_rows(pg):
    return pg.evaluate(THEME_JS)


def frame_text_color(pg, want="#EEEEEE"):
    """불러온 화면 iframe 하나의 --c-text-1(file:// 라 부모에서 못 읽음 — 그 frame 안에서) · 바뀔 때까지 잠깐 기다린다."""
    fr = [f for f in pg.frames if "/screens/" in f.url]
    assert fr, "불러온 화면 iframe 이 없다"
    v = None
    for _ in range(20):
        v = fr[0].evaluate("getComputedStyle(document.documentElement).getPropertyValue('--c-text-1').trim().toUpperCase()")
        if v == want:
            break
        pg.wait_for_timeout(50)
    return v


def test_theme_panel_switch_copy_edit_contrast_delete(dpage):
    """H10: 위쪽 색 팔레트는 없애고 테마 패널(창 메뉴로 켬, 기본은 닫힘). H12: '+ 새 테마' = 지금 테마 복제 → 색 네 칸(주 색·글자·바탕·강조)
    고치면 판의 화면에 바로, 글자 대비 4.5:1 미만이면 경고. 기본 테마는 자물쇠(복제해서 고침). H14: 이름 바꾸기·복제·삭제(기본은 복제만, 삭제는 되돌리기)."""
    errs = []
    dpage.on("pageerror", lambda e: errs.append(str(e)))
    dpage.keyboard.press("Escape")
    assert dpage.locator("header .dot").count() == 0, "위쪽 줄 색 팔레트는 없다(H10)"
    assert dpage.locator('#dock .dk-tab[data-p="theme"]').count() == 0, "테마 패널은 기본으로 닫힘"
    dpage.click("#wbtn"); dpage.click('#wmenu [data-w="theme"]'); dpage.keyboard.press("Escape")
    dpage.click('#dock .dk-tab[data-p="theme"]')
    rows = theme_rows(dpage)
    assert len(rows) >= 2 and all(r["lock"] and not r["del"] for r in rows), rows
    second = rows[1]["id"]
    dpage.click(f'#thList [data-th="{second}"] .th-name')
    assert dpage.evaluate("document.getElementById('tokens').getAttribute('href')").endswith(f"tokens-{second}.css")
    assert [r["id"] for r in theme_rows(dpage) if r["on"]] == [second]
    # 새 테마 = 지금 테마 복제 → 고치기
    dpage.click("#thNew")
    rows = theme_rows(dpage)
    mine = [r for r in rows if not r["lock"]]
    assert len(mine) == 1 and mine[0]["on"] and mine[0]["del"], rows
    assert dpage.is_visible("#thEdit") and dpage.locator('#thEdit [data-role]').count() == 4
    dpage.fill('#thEdit [data-role="text"] .th-hex', "#EEEEEE"); dpage.keyboard.press("Enter")
    assert "4.5" in (dpage.text_content("#thWarn") or ""), "글자 대비 미달 경고"
    assert frame_text_color(dpage) == "#EEEEEE", "판의 화면에 바로(화면 iframe 의 --c-text-1)"
    dpage.fill('#thEdit [data-role="text"] .th-hex', "#111111"); dpage.keyboard.press("Enter")
    assert not (dpage.text_content("#thWarn") or "").strip()
    # 이름 바꾸기 · 저장 · 삭제 + 되돌리기
    mid = mine[0]["id"]
    dpage.hover(f'#thList [data-th="{mid}"]')
    dpage.click(f'#thList [data-th="{mid}"] [data-act="ren"]')
    dpage.fill("#thList .th-in", "내 새벽"); dpage.keyboard.press("Enter")
    assert [r["name"] for r in theme_rows(dpage) if r["id"] == mid] == ["내 새벽"]
    assert "내 새벽" in (dpage.evaluate("localStorage.getItem('hd-themes')") or ""), "모든 캔버스 공용 키에 저장"
    dpage.hover(f'#thList [data-th="{mid}"]')
    dpage.click(f'#thList [data-th="{mid}"] [data-act="del"]')
    assert mid not in [r["id"] for r in theme_rows(dpage)]
    dpage.keyboard.press("Control+z")
    assert mid in [r["id"] for r in theme_rows(dpage)], "테마 삭제도 되돌리기"
    dpage.hover(f'#thList [data-th="{mid}"]'); dpage.click(f'#thList [data-th="{mid}"] [data-act="del"]')
    dpage.click(f'#thList [data-th="{rows[0]["id"]}"] .th-name')
    # Foundation 탭에서도 테마를 바꿀 수 있다(예전 위쪽 팔레트처럼 — 색 견본을 보며 비교하는 곳)
    dpage.click('.tab[data-tab="foundation"]')
    assert dpage.is_visible("#wbtn") and dpage.is_visible("#thList"), "Foundation 탭에서도 창 메뉴·테마 패널"
    fb = dpage.locator("#foundation").bounding_box(); dk = dpage.locator("#dock").bounding_box()
    assert fb["x"] + fb["width"] <= dk["x"] + 1, "Foundation 판은 도크에 가리지 않는다"
    dpage.click(f'#thList [data-th="{second}"] .th-name')
    assert dpage.evaluate("document.getElementById('tokens').getAttribute('href')").endswith(f"tokens-{second}.css")
    dpage.click(f'#thList [data-th="{rows[0]["id"]}"] .th-name')
    dpage.click('.tab[data-tab="screens"]')
    assert not errs, errs


# ---------------------------------------------------------------- Q3: 선 누르기 = 그 쌍 강조 + 도착 끝 손잡이 · 끌어 놓기 = 도착 바꾸기(되돌리기 한 단계) · Esc
def ln_ends(pg):
    return pg.evaluate("""[...document.querySelectorAll('#ar circle.ln-end')].map(c => { const r = c.getBoundingClientRect();
        return {from: c.dataset.from, to: c.dataset.to, x: r.left + r.width / 2, y: r.top + r.height / 2}; })""")


def test_line_click_shows_end_handles_and_drag_retargets(dpage):
    fit_view(dpage)
    dpage.keyboard.press("h")
    pairs = dpage.evaluate("""[...document.querySelectorAll('#ar path.ln:not(.plan):not(.pd)')].filter(p => p.dataset.both === '0').map(p => [p.dataset.from, p.dataset.to])""")
    assert pairs, "한쪽으로만 가는 진짜 연결선이 있어야 한다"
    frm, to = pairs[0]
    x, y = ln_mid(dpage, frm, to)
    dpage.mouse.click(x, y)
    dpage.wait_for_selector("#ar circle.ln-end")
    ends = ln_ends(dpage)
    assert [(e["from"], e["to"]) for e in ends] == [(frm, to)], ("한쪽 선 = 도착 끝 손잡이 하나", ends)
    assert lk_to(dpage, to, frm) and "on" in lk_to(dpage, to, frm)[0].split(), "누른 선은 진하게(쌍 강조)"
    assert dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "나머지는 흐리게"
    hx, hy = ends[0]["x"], ends[0]["y"]
    dpage.mouse.move(hx, hy)
    for dy in (-300, 300):                                # 가까이 당겨 찍고 같은 만큼 되돌린다
        dpage.keyboard.down("Control"); dpage.mouse.wheel(0, dy); dpage.keyboard.up("Control")
        dpage.wait_for_timeout(200)
        if dy < 0:
            ESHOTS.mkdir(parents=True, exist_ok=True)
            dpage.screenshot(path=str(ESHOTS / "q3-line-handle.png"))
    q = visible_cover(dpage, skip=[frm, to])
    h = ln_ends(dpage)[0]
    drag(dpage, h, q["x"] - h["x"], q["y"] - h["y"])
    dpage.wait_for_function("([a, b]) => [...document.querySelectorAll('#ar path.ln.pd')].some(p => p.dataset.from === a && p.dataset.to === b)", arg=[frm, q["id"]], timeout=5000)
    assert lk_to(dpage, to, frm) == [], "옛 도착으로 가던 선은 사라진다"
    assert not ln_ends(dpage), "도착을 바꾸면 고른 선은 풀린다"
    dpage.keyboard.press("Control+z")
    dpage.wait_for_function("([a, b]) => ![...document.querySelectorAll('#ar path.ln')].some(p => p.dataset.from === a && p.dataset.to === b)", arg=[frm, q["id"]], timeout=4000)
    assert lk_to(dpage, to, frm) and "pd" not in lk_to(dpage, to, frm)[0].split(), "되돌리면 옛 선이 그대로"
    x, y = ln_mid(dpage, frm, to)
    dpage.mouse.click(x, y)
    dpage.wait_for_selector("#ar circle.ln-end")
    dpage.keyboard.press("Escape")
    assert not ln_ends(dpage) and not dpage.evaluate("document.getElementById('rows').classList.contains('focusing')"), "Esc = 손잡이·강조 풀기"


# ---------------------------------------------------------------- task 7: 정렬 패널(H18) · 레이어 폴더(H17)
BOX_JS = """(ids) => { const z = +document.getElementById('stage').dataset.zoom, rr = document.getElementById('rows').getBoundingClientRect();
    return ids.map(id => { const r = document.querySelector('.card[data-id="' + id + '"]').getBoundingClientRect();
      return {id, x: (r.left - rr.left) / z, y: (r.top - rr.top) / z, w: r.width / z, h: r.height / z}; }); }"""
# 줄마다 옮길 수 있는 카드(숨김·삭제 대기·잠김 아님) 하나 — 앞 테스트가 남긴 상태와 상관없이
MOVABLE_JS = """(n) => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-locked:')), lk = k ? JSON.parse(localStorage.getItem(k) || '[]') : [];
    return [...document.querySelectorAll('#rows .flow')].slice(0, n).map((f, i) => {
      const cs = [...f.querySelectorAll('.card')].filter(c => !c.classList.contains('hid') && !c.classList.contains('del') && c.offsetWidth && !lk.includes(c.dataset.id));
      return cs.length ? cs[Math.min(i, cs.length - 1)].dataset.id : null; }); }"""
CLEAR_T7 = "Object.keys(localStorage).filter(k => /^hd-(card-pos|folders):/.test(k) || k === 'hd-align-gap').forEach(k => localStorage.removeItem(k))"


def boxes(pg, ids):
    return {b["id"]: b for b in pg.evaluate(BOX_JS, ids)}


def near(a, b, tol=1.5):
    return abs(a - b) <= tol


def shift_pick(pg, ids):
    """판에서 첫 카드 누르기 + 나머지 Shift+클릭(여러 장 고르기)."""
    pg.keyboard.press("Escape")
    for i, sid in enumerate(ids):
        pg.evaluate("([id, sh]) => document.querySelector('.card[data-id=\"' + id + '\"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1, shiftKey: sh}))", [sid, i > 0])


def test_align_panel_aligns_distributes_and_stacks(dpage):
    """H18: Shift 로 고른 카드 셋 → 정렬 패널(도크 '정렬' 탭) 위 맞추기 = 위 끝이 같게, Ctrl+Z 한 번에 셋 다 제자리 ·
    가로 간격 같게 = 이웃 카드 사이 빈칸이 같게(처음·끝 그대로) · 간격 40 + 가로로 늘어놓기 = 정확히 40px · 새로고침 뒤에도 그 자리."""
    errs = []
    dpage.on("pageerror", lambda e: errs.append(str(e)))
    dpage.evaluate(CLEAR_T7)
    reload(dpage)
    ids = dpage.evaluate(MOVABLE_JS, 3)
    assert None not in ids and len(set(ids)) == 3, ids
    fit_view(dpage)
    dpage.click('#dock .dk-tab[data-p="align"]')
    assert dpage.text_content("#pAlign .al-n") == "화면을 두 개 이상 고르세요" and dpage.is_disabled('#pAlign [data-al="top"]')
    shift_pick(dpage, ids)
    assert dpage.text_content("#pAlign .al-n") == "고른 화면 3개" and not dpage.is_disabled('#pAlign [data-dist="x"]')
    b0 = boxes(dpage, ids)
    assert len({round(b["y"]) for b in b0.values()}) == 3, ("줄이 다른 카드 셋", b0)
    # 위 맞추기 → 되돌리기 한 번
    dpage.click('#pAlign [data-al="top"]')
    b1 = boxes(dpage, ids)
    top = min(b["y"] for b in b0.values())
    assert all(near(b1[i]["y"], top) and near(b1[i]["x"], b0[i]["x"]) for i in ids), ("위 끝이 가장 위 카드에 맞는다", b0, b1)
    assert "정렬: 위" in dpage.text_content("#hlist li.now"), "기록 한 줄"
    dpage.keyboard.press("Control+z")
    b2 = boxes(dpage, ids)
    assert all(near(b2[i]["x"], b0[i]["x"]) and near(b2[i]["y"], b0[i]["y"]) for i in ids), ("Ctrl+Z 한 번에 셋 다 제자리", b0, b2)
    # 가로 간격 같게
    dpage.click('#pAlign [data-dist="x"]')
    b3 = sorted(boxes(dpage, ids).values(), key=lambda b: b["x"])
    s0 = sorted(b0.values(), key=lambda b: b["x"])
    gaps = [b3[k + 1]["x"] - (b3[k]["x"] + b3[k]["w"]) for k in range(2)]
    assert near(gaps[0], gaps[1]) and near(b3[0]["x"], s0[0]["x"]) and near(b3[2]["x"], s0[2]["x"]), ("빈칸이 같고 처음·끝은 그대로", b3)
    # 간격 40 + 가로로 늘어놓기
    dpage.fill("#alGap", "40")
    dpage.click('#pAlign [data-stack="x"]')
    b4 = sorted(boxes(dpage, ids).values(), key=lambda b: b["x"])
    assert all(near(b4[k + 1]["x"] - (b4[k]["x"] + b4[k]["w"]), 40) for k in range(2)), ("카드 사이 정확히 40px", b4)
    assert all(near(b["y"], b4[0]["y"]) for b in b4), ("한 줄(위 끝 같게)", b4)
    assert "늘어놓기 (40px)" in dpage.text_content("#hlist li.now")
    # 새로고침 뒤에도
    reload(dpage)
    b5 = boxes(dpage, ids)
    assert all(near(b5[b["id"]]["x"], b["x"]) and near(b5[b["id"]]["y"], b["y"]) for b in b4), ("옮긴 자리 저장", b4, b5)
    assert dpage.input_value("#alGap") == "40", "간격 칸도 저장"
    dpage.evaluate(CLEAR_T7)
    reload(dpage)
    assert not errs, errs


FOLDER_LINES_JS = """() => [...document.querySelectorAll('#lyTree [data-kind="folder"]')].map(r => ({id: r.dataset.id,
    name: (r.querySelector('.ly-name') || {}).textContent || '', count: (r.querySelector('.ly-count') || {}).textContent || '', icon: !!r.querySelector('.ly-ficon svg')}))"""
IN_FOLDER_JS = """() => [...document.querySelectorAll('#lyTree [data-kind="screen"].infolder')].map(r => r.dataset.ly)"""
DRAG_JS = """([c, h]) => { const dt = new DataTransfer(), s = document.querySelector('#lyTree [data-ly="' + c + '"]'), t = document.querySelector(h);
    s.dispatchEvent(new DragEvent('dragstart', {bubbles: true, dataTransfer: dt}));
    t.dispatchEvent(new DragEvent('dragover', {bubbles: true, cancelable: true, dataTransfer: dt}));
    t.dispatchEvent(new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: dt})); }"""


def test_layer_folders_group_rename_arrange_unfolder(dpage):
    """H17: 레이어 패널에서 화면 줄 둘을 Ctrl/Shift+클릭 → [폴더로 묶기] = 맨 위에 폴더 줄(폴더 아이콘·화면 수 2), 바로 이름 바꾸기 →
    새로고침 뒤에도 · 폴더 [세로로 늘어놓기] = 그 카드 둘이 정렬 패널 간격으로 한 열 · 화면 줄을 폴더 줄에 끌어 놓으면 폴더에 ·
    [폴더 풀기] = 화면은 원래 줄 아래로. 폴더로 묶기만으로는 판 카드가 움직이지 않는다."""
    errs = []
    dpage.on("pageerror", lambda e: errs.append(str(e)))
    dpage.evaluate(CLEAR_T7)
    reload(dpage)
    a, b, c = dpage.evaluate(MOVABLE_JS, 3)
    assert None not in (a, b, c) and len({a, b, c}) == 3, (a, b, c)
    dpage.keyboard.press("Escape")
    dpage.click('#dock .dk-tab[data-p="layers"]')
    assert dpage.is_disabled('#lyBar [data-act="folder"]'), "고른 화면이 없으면 못 누른다"
    b0 = boxes(dpage, [a, b, c])
    dpage.click(f'#lyTree [data-ly="{a}"] .ly-name', modifiers=["Control"])
    dpage.click(f'#lyTree [data-ly="{b}"] .ly-name', modifiers=["Shift"])
    assert dpage.evaluate("(ids) => ids.every(id => document.querySelector('.card[data-id=\"' + id + '\"]').classList.contains('picked'))", [a, b])
    dpage.click('#lyBar [data-act="folder"]')
    dpage.wait_for_selector("#lyTree input.ly-rename")
    first = dpage.evaluate("(() => { const r = document.querySelector('#lyTree [data-ly]'), i = r.querySelector('.ly-rename'); return [r.dataset.kind, i ? i.value : '']; })()")
    assert first == ["folder", "새 폴더 1"], first
    dpage.fill("#lyTree input.ly-rename", "내 묶음")
    dpage.keyboard.press("Enter")
    fl = dpage.evaluate(FOLDER_LINES_JS)
    assert fl == [{"id": "f1", "name": "내 묶음", "count": "2", "icon": True}], fl
    assert sorted(dpage.evaluate(IN_FOLDER_JS)) == sorted([a, b]), "폴더 아래 두 화면"
    assert [l["id"] for l in layers(dpage) if l["kind"] == "screen"].count(a) == 1, "폴더 화면은 원래 줄 아래에서 빠진다"
    assert boxes(dpage, [a, b, c]) == b0, "폴더로 묶어도 판 카드는 그대로"
    # 새로고침 뒤에도
    reload(dpage)
    dpage.click('#dock .dk-tab[data-p="layers"]')
    assert dpage.evaluate(FOLDER_LINES_JS)[0]["name"] == "내 묶음"
    # 폴더 [세로로 늘어놓기] — 간격 = 정렬 패널 칸
    gap = int(dpage.input_value("#alGap"))
    head = '#lyTree [data-kind="folder"][data-id="f1"]'
    dpage.hover(head)
    dpage.click(f'{head} [data-arr="y"]')
    col = sorted(boxes(dpage, [a, b]).values(), key=lambda q: q["y"])
    assert near(col[1]["y"] - (col[0]["y"] + col[0]["h"]), gap) and near(col[0]["x"], col[1]["x"]), ("한 열, 정렬 패널 간격", gap, col)
    assert "늘어놓기 (%dpx)" % gap in dpage.text_content("#hlist li.now")
    # 끌어 넣기: 화면 줄 → 폴더 줄. Playwright 마우스 끌기는 긴 나무가 스크롤되며 다른 줄을 잡는다 — 같은 HTML5 끌기 이벤트(dragstart·dragover·drop)를 직접 보낸다
    dpage.evaluate(DRAG_JS, [c, head])
    fl = dpage.evaluate(FOLDER_LINES_JS)
    assert fl[0]["count"] == "3" and c in dpage.evaluate(IN_FOLDER_JS), fl
    # 스크린샷: 레이어 패널의 폴더 + 정렬 패널(따로 띄운 창)
    dpage.evaluate("(ids) => ids.forEach((id, i) => document.querySelector('.card[data-id=\"' + id + '\"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1, shiftKey: i > 0})))", [a, b])
    t = dpage.locator('#dock .dk-tab[data-p="align"]').bounding_box()
    drag_to(dpage, t, 520, 200)
    dpage.click('#dock .dk-tab[data-p="layers"]')
    dpage.wait_for_timeout(200)
    ESHOTS.mkdir(parents=True, exist_ok=True)
    dpage.screenshot(path=str(ESHOTS / "h17-folders-align.png"))
    dpage.evaluate("localStorage.removeItem('hd-dock')")
    # 폴더 풀기
    dpage.hover(head)
    dpage.click(f'{head} [data-act="unfolder"]')
    assert dpage.evaluate(FOLDER_LINES_JS) == [] and dpage.evaluate(IN_FOLDER_JS) == []
    cards = dpage.evaluate("[...document.querySelectorAll('#rows .card:not(.del)')].map(c => c.dataset.id)")
    assert [l["id"] for l in layers(dpage) if l["kind"] == "screen"] == cards, "화면은 원래 줄 아래로"
    dpage.evaluate(CLEAR_T7)
    reload(dpage)
    assert not errs, errs
