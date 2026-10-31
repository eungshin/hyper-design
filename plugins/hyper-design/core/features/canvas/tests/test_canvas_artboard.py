"""카드(아트보드) 크기(task 46) — 새 화면 대화상자 · 고른 카드 크기 팝오버 · 여러 장 · 되돌리기 · 크게 보기 · 선 (Playwright).

화면 셋(home → pay → done)을 file:// 로 연다. 크기는 view-artboard 가 상태 이름 card-size(hd-card-size:<hash>)에 둔다.
스크린샷은 HD_T46_SHOTS 폴더가 있으면 거기에 남긴다(검토용 — 판정은 단언이 한다).
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY, DONE

pytestmark = pytest.mark.area("tools")
SHOTS = os.environ.get("HD_T46_SHOTS")
HOME = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><h1 style="margin:16px">홈</h1><a href="pay.html" class="buy" style="display:block;margin:16px">결제하기</a></body></html>"""


def shot(pg, name):
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(SHOTS) / name))


@pytest.fixture(scope="module")
def abpage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-artboard-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "home.html").write_text(HOME, encoding="utf-8")
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["흐름"], "screens": [
        {"id": "home", "file": "screens/home.html", "title": "홈", "group": "흐름", "purpose": "시작", "policies": []},
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "흐름", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "흐름", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((out / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.errors = errors
    yield pg
    pg.close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def fresh(pg):
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.keyboard.press("0")
    pg.wait_for_timeout(200)


def phone(pg, cid):
    return pg.evaluate("""id => { const c = document.querySelector('.card[data-id="' + id + '"]'), p = c.querySelector('.phone'), f = p.querySelector('iframe'), r = p.getBoundingClientRect();
        return {w: p.offsetWidth, h: p.offsetHeight, fw: f ? f.offsetWidth : null, x: r.left, y: r.top}; }""", cid)


def sizes(pg):
    return pg.evaluate("(() => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-card-size:')); return k ? JSON.parse(localStorage.getItem(k)) : {}; })()")


def select(pg, cid, shift=False):
    b = pg.locator(f'.card[data-id="{cid}"] .cover').bounding_box()
    if shift:
        pg.keyboard.down("Shift")
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + 40)
    if shift:
        pg.keyboard.up("Shift")
    pg.wait_for_timeout(120)


def empty_spot(pg):
    return pg.evaluate("""(() => { const r = document.querySelector('#screens').getBoundingClientRect();
        for (let y = r.bottom - 40; y > r.top + 60; y -= 40) for (let x = r.left + 120; x < r.right - 60; x += 60) {
          const el = document.elementFromPoint(x, y); if (el && !el.closest('.card, #tools, .alabel, #selbar') && el.closest('#screens')) return {x, y}; }
        return null; })()""")


def test_new_screen_dialog_creates_sized_blank_card_and_undo(abpage):
    pg = abpage
    fresh(pg)
    pg.keyboard.press("n")
    e = empty_spot(pg)
    pg.mouse.click(e["x"], e["y"])
    pg.wait_for_selector("#abNew:not([hidden])")
    tabs = pg.evaluate("[...document.querySelectorAll('#abNew .ab-cat')].map(b => b.textContent)")
    assert tabs == ["최근", "모바일", "태블릿", "웹/데스크톱", "사용자 정의"], tabs
    assert pg.input_value("#abW") == "375" and pg.input_value("#abH") == "812", "처음 고른 크기 = 프로젝트 카드 크기"
    pg.click('#abNew .ab-cat[data-cat="tablet"]')
    pg.click('#abNew .ab-card[data-name="iPad Pro 11"]')
    assert pg.input_value("#abW") == "834" and pg.input_value("#abH") == "1194"
    pg.fill("#abName", "설정")
    shot(pg, "new-screen-dialog.png")
    pg.click("#abMake")
    pg.wait_for_selector("#abNew", state="hidden")
    did = pg.evaluate("document.querySelector('.card.draft').dataset.id")
    p = phone(pg, did)
    assert (p["w"], p["h"]) == (834, 1194), p
    assert pg.text_content(f'.card.draft[data-id="{did}"] .ftitle') == "설정"
    assert sizes(pg)[did] == {"w": 834, "h": 1194, "preset": "iPad Pro 11"}
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(200)
    assert pg.evaluate("document.querySelectorAll('.card.draft').length") == 0, "되돌리기 한 번 = 빈 카드가 사라짐"
    pg.keyboard.press("h")


def test_dialog_checks_input_keys_and_saves_preset(abpage):
    pg = abpage
    fresh(pg)
    pg.keyboard.press("n")
    e = empty_spot(pg)
    pg.mouse.click(e["x"], e["y"])
    pg.wait_for_selector("#abNew:not([hidden])")
    pg.fill("#abW", "10")
    pg.click("#abMake")
    assert pg.is_visible("#abNew"), "잘못된 값이면 만들지 않는다"
    assert "16~60000" in pg.text_content("#abErr") and pg.get_attribute("#abW", "aria-invalid") == "true"
    pg.fill("#abW", "393")
    pg.focus("#abW")
    pg.keyboard.press("ArrowUp")
    assert pg.input_value("#abW") == "394"
    pg.keyboard.press("Shift+ArrowDown")
    assert pg.input_value("#abW") == "384" and pg.text_content("#abErr") == ""
    pg.click("#abSaveOpen")
    pg.fill("#abPName", "내 폰")
    pg.keyboard.press("Enter")
    assert pg.get_attribute('#abNew .ab-cat[data-cat="saved"]', "aria-selected") == "true"
    assert pg.evaluate("[...document.querySelectorAll('#abNew .ab-card')].map(c => c.dataset.name)") == ["내 폰"]
    pg.keyboard.press("Escape")
    assert pg.is_hidden("#abNew") and pg.evaluate("document.querySelectorAll('.card.draft').length") == 0, "Esc = 취소(카드 없음)"
    pg.keyboard.press("h")


def test_selected_card_size_popover_keeps_top_left_and_undo(abpage):
    pg = abpage
    fresh(pg)
    select(pg, "pay")
    btn = '#selbar [data-act="size"]'
    assert pg.text_content(btn) == "375×812 ▾"
    before = phone(pg, "pay")
    pg.click(btn)
    pg.wait_for_selector("#abPop:not([hidden])")
    heads = pg.evaluate("[...document.querySelectorAll('#abPop .abp-h')].map(h => h.textContent)")
    assert heads[:3] == ["모바일", "태블릿", "웹/데스크톱"], heads
    shot(pg, "size-popover.png")
    pg.click('#abPop .abp-row[data-name="iPad Pro 11"]')
    assert pg.is_hidden("#abPop")
    pg.wait_for_timeout(150)
    after = phone(pg, "pay")
    assert (after["w"], after["fw"], after["h"]) == (834, 834, 1194), after
    assert abs(after["x"] - before["x"]) < 1 and abs(after["y"] - before["y"]) < 1, ("왼쪽 위 그대로", before, after)
    assert pg.text_content(btn) == "834×1194 ▾"
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(150)
    assert phone(pg, "pay")["w"] == 375 and sizes(pg) == {}
    pg.keyboard.press("Control+Shift+z")
    pg.wait_for_timeout(150)
    assert phone(pg, "pay")["w"] == 834 and sizes(pg)["pay"]["preset"] == "iPad Pro 11"


def test_multi_select_inputs_apply_to_all_in_one_step(abpage):
    pg = abpage
    fresh(pg)
    select(pg, "home")
    select(pg, "done", shift=True)
    pg.click('#selbar [data-act="size"]')
    pg.wait_for_selector("#abPop:not([hidden])")
    pg.fill("#abPW", "15")
    pg.click("#abPOk")
    assert pg.is_visible("#abPop") and "16~60000" in pg.text_content("#abPErr"), "잘못된 값 = 알리고 그대로"
    pg.fill("#abPW", "1440")
    pg.fill("#abPH", "1024")
    pg.focus("#abPH")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(150)
    assert phone(pg, "home")["w"] == 1440 and phone(pg, "done")["w"] == 1440 and phone(pg, "pay")["w"] == 375
    assert sizes(pg)["home"] == {"w": 1440, "h": 1024, "preset": "Desktop"}
    pg.click('#selbar [data-act="size"]')
    pg.click("#abPSwap")
    pg.wait_for_timeout(100)
    assert phone(pg, "home")["w"] == 1024 and phone(pg, "home")["h"] == 1440, "가로·세로 바꾸기"
    pg.click("#abPDef")
    pg.wait_for_timeout(100)
    assert sizes(pg) == {} and phone(pg, "done")["w"] == 375, "기본 크기로"
    pg.keyboard.press("Control+z")
    pg.keyboard.press("Control+z")
    pg.wait_for_timeout(150)
    assert phone(pg, "home")["w"] == 1440 and phone(pg, "done")["w"] == 1440, "되돌리기 한 번 = 두 장 함께"


def test_size_survives_reload_and_modal_follows(abpage):
    pg = abpage
    fresh(pg)
    select(pg, "pay")
    pg.click('#selbar [data-act="size"]')
    pg.click('#abPop .abp-row[data-name="iPad Pro 11"]')
    pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    assert phone(pg, "pay")["w"] == 834, "새로고침 뒤에도"
    pg.keyboard.press("0")
    pg.wait_for_timeout(200)
    b = pg.locator('.card[data-id="pay"] .cover').bounding_box()
    pg.mouse.dblclick(b["x"] + b["width"] / 2, b["y"] + 40)
    pg.wait_for_selector("#modal:not([hidden])")
    m = pg.evaluate("(() => { const f = document.querySelector('#mframe'), b = document.querySelector('#mbox'); return {fw: f.offsetWidth, fh: f.offsetHeight, bw: b.offsetWidth, bh: b.offsetHeight}; })()")
    assert (m["fw"], m["fh"]) == (834, 1194), m
    assert abs(m["bw"] / m["bh"] - 834 / 1194) < 0.02, ("크게 보기 틀도 그 비율", m)
    pg.keyboard.press("Escape")


def test_board_with_phone_tablet_desktop_draws_lines(abpage):
    pg = abpage
    fresh(pg)
    for cid, name in (("pay", "iPad Pro 11"), ("done", "Desktop")):
        pg.keyboard.press("0")                           # 넓어진 카드가 다음 카드를 판 밖으로 밀 수 있어 전체 보기 뒤 고른다
        pg.wait_for_timeout(200)
        select(pg, cid)
        pg.click('#selbar [data-act="size"]')
        pg.click(f'#abPop .abp-row[data-name="{name}"]')
    assert {k: v["preset"] for k, v in sizes(pg).items()} == {"pay": "iPad Pro 11", "done": "Desktop"}
    pg.keyboard.press("Escape")
    pg.keyboard.press("0")
    pg.wait_for_timeout(400)
    boxes = pg.evaluate("""[...document.querySelectorAll('#rows .card')].map(c => { const r = c.querySelector('.phone').getBoundingClientRect(); return {id: c.dataset.id, l: r.left, r: r.right, t: r.top, b: r.bottom}; })""")
    by = {b["id"]: b for b in boxes}
    assert by["home"]["r"] <= by["pay"]["l"] and by["pay"]["r"] <= by["done"]["l"], ("크기가 달라도 겹치지 않게 줄을 다시 흐름", boxes)
    pane = pg.evaluate("(() => { const r = document.querySelector('#screens').getBoundingClientRect(); return {r: r.right, b: r.bottom}; })()")
    for b in boxes:
        assert b["r"] <= pane["r"] + 1 and b["b"] <= pane["b"] + 1, ("전체 보기(0)에 모두 들어옴", b, pane)
    n = pg.evaluate("document.querySelectorAll('#ar path.ln, #ar path').length")
    assert n >= 2, "home → pay → done 선"
    shot(pg, "board-phone-tablet-desktop.png")


def set_size(pg, cid, w, h):
    pg.keyboard.press("0")
    pg.wait_for_timeout(200)
    select(pg, cid)
    pg.click('#selbar [data-act="size"]')
    pg.wait_for_selector("#abPop:not([hidden])")
    pg.fill("#abPW", str(w))
    pg.fill("#abPH", str(h))
    pg.click("#abPOk")
    pg.wait_for_timeout(150)


def test_ad_banner_and_detail_page_sizes_are_accepted(abpage):
    """R57 A: 광고 320×50 · 상세페이지 860×40000 — 받고, 판에 그 크기로 서고, 전체 보기에 겹치지 않고 들어온다."""
    pg = abpage
    fresh(pg)
    set_size(pg, "pay", 320, 50)
    assert pg.is_hidden("#abPop"), pg.text_content("#abPErr")
    set_size(pg, "done", 860, 40000)
    assert pg.is_hidden("#abPop"), pg.text_content("#abPErr")
    assert {k: (v["w"], v["h"]) for k, v in sizes(pg).items()} == {"pay": (320, 50), "done": (860, 40000)}
    p, d = phone(pg, "pay"), phone(pg, "done")
    assert (p["w"], p["h"], p["fw"]) == (320, 50, 320) and (d["w"], d["h"], d["fw"]) == (860, 40000, 860), (p, d)
    pg.keyboard.press("Escape")
    pg.keyboard.press("0")
    pg.wait_for_timeout(400)
    boxes = pg.evaluate("""[...document.querySelectorAll('#rows .card')].map(c => { const r = c.querySelector('.phone').getBoundingClientRect(); return {id: c.dataset.id, l: r.left, r: r.right, t: r.top, b: r.bottom}; })""")
    by = {b["id"]: b for b in boxes}
    assert by["home"]["r"] <= by["pay"]["l"] and by["pay"]["r"] <= by["done"]["l"], boxes
    pane = pg.evaluate("(() => { const r = document.querySelector('#screens').getBoundingClientRect(); return {t: r.top, b: r.bottom}; })()")
    assert by["done"]["t"] >= pane["t"] - 1 and by["done"]["b"] <= pane["b"] + 1, ("40000 높이도 전체 보기에 들어옴", by["done"], pane)
    shot(pg, "r57-board-ad-and-detail.png")
