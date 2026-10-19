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
