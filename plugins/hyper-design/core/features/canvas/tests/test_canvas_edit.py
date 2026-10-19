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
