"""크게 보기 확대(R57 C) — 열 때 폭 맞추기 · 긴 화면은 창 안 굴림 · Ctrl+휠 커서 자리 확대 · Ctrl+=/-/0 · 배율 칩 · 화면 위에 그린 것(메모 핀·요소 테두리·요소 막대)이 배율·굴림을 따라감 (Playwright).

화면 셋을 file:// 로 연다: pay(폰 기본 크기 — 짧은 화면) · web(1440×4000 긴 웹 페이지) · tiny(320×50 광고). 크기는 상태 이름 card-size 를 브라우저 저장소에 넣고 다시 연다.
규칙(배율·창 크기·굴림 범위·커서 자리 수식)은 test_canvas_unit_modal_zoom.py — 여기는 사용자에게 보이는 것만 본다.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY

pytestmark = pytest.mark.area("modal")
HEAD = '<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>'
WEB = (HEAD + '<body style="margin:0;font-family:sans-serif"><header style="box-sizing:border-box;height:400px;padding:24px;background:#222;color:#fff">'
       '<h1 style="margin:0;font-size:48px">긴 웹 페이지</h1><button class="buy" style="margin-top:20px;width:240px;height:56px;font-size:20px">구매하기</button></header>'
       + "".join('<section style="box-sizing:border-box;height:900px;padding:24px;border-top:4px solid #ccc"><h2 style="margin:0">섹션 %d</h2></section>' % i for i in range(1, 5))
       + '</body></html>')                               # 400 + 4×900 = 4000 — 카드 높이와 같아 화면 안 굴림 없음
TINY = HEAD + '<body style="margin:0"><div style="height:50px;background:#ffe14d">광고</div></body></html>'
HASH = "(s => { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(window.__hdKeyPath || location.pathname)"
NOTE = {"id": "m1", "screen": "web", "targets": [{"path": "button.buy", "text": "구매하기", "quote": {"exact": "구매하기", "prefix": "", "suffix": ""}}],
        "path": "button.buy", "text": "구매하기", "rect": None, "note": "버튼 색", "intent": "change", "sent": False, "replies": []}
VIEW = """() => { const v = document.querySelector('#mview'), b = document.querySelector('#mbox'), f = document.querySelector('#mframe'), m = /scale\\(([\\d.]+)\\)/.exec(f.style.transform);
  const r = v.getBoundingClientRect(), br = b.getBoundingClientRect();
  return {s: m ? +m[1] : 1, vw: v.clientWidth, vh: v.clientHeight, vx: r.left, vy: r.top, bw: b.offsetWidth, bh: b.offsetHeight, bx: br.left, by: br.top, sl: v.scrollLeft, st: v.scrollTop,
          chip: document.querySelector('#zoom').textContent}; }"""


@pytest.fixture(scope="module")
def zpage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-modal-zoom-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "web.html").write_text(WEB, encoding="utf-8")
    (out / "screens" / "tiny.html").write_text(TINY, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["흐름"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "흐름", "purpose": "짧은 화면"},
        {"id": "tiny", "file": "screens/tiny.html", "title": "광고", "group": "흐름", "purpose": "320×50"},
        {"id": "web", "file": "screens/web.html", "title": "웹", "group": "흐름", "purpose": "1440×4000"}]}, ensure_ascii=False), encoding="utf-8")
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


def fresh(pg, notes=()):
    pg.evaluate("""([h, notes]) => { Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k));
      localStorage.setItem('hd-card-size:' + h, JSON.stringify({web: {w: 1440, h: 4000}, tiny: {w: 320, h: 50}}));
      if (notes.length) localStorage.setItem('hd-notes:' + h, JSON.stringify(notes)); }""", [pg.evaluate(HASH), list(notes)])
    pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.keyboard.press("0")
    pg.wait_for_timeout(300)


def open_modal(pg, cid):
    pg.keyboard.press("0")
    pg.wait_for_timeout(200)
    b = pg.locator(f'.card[data-id="{cid}"] .cover').bounding_box()
    pg.mouse.dblclick(b["x"] + b["width"] / 2, b["y"] + min(b["height"] / 2, 6))
    pg.wait_for_selector("#modal:not([hidden])")
    pg.wait_for_timeout(400)
    return pg.evaluate(VIEW)


def ctrl_wheel(pg, x, y, dy, n=1):
    pg.mouse.move(x, y)
    for _ in range(n):
        pg.keyboard.down("Control")
        pg.mouse.wheel(0, dy)
        pg.keyboard.up("Control")
        pg.wait_for_timeout(60)


def pct(v):
    return int(re.match(r"(\d+)%", v["chip"]).group(1))


def test_tall_page_opens_at_fit_width_and_scrolls_inside(zpage):
    pg = zpage
    fresh(pg)
    board_chip = pg.text_content("#zoom")
    v = open_modal(pg, "web")
    assert v["s"] < 1 and abs(v["bw"] - v["vw"]) <= 1, ("폭 맞추기 = 화면 폭이 창 폭", v)
    assert v["bh"] > v["vh"] * 2, ("긴 화면은 창보다 길다 — 아래로 굴린다", v)
    assert pct(v) == round(v["s"] * 100), ("배율 칩 = 크게 보기 배율", v)
    pg.mouse.move(v["vx"] + v["vw"] / 2, v["vy"] + v["vh"] / 2)
    pg.mouse.wheel(0, 800)
    pg.wait_for_timeout(300)
    assert pg.evaluate(VIEW)["st"] > 0, "그냥 휠 = 창 안 굴림"
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    assert pg.text_content("#zoom") == board_chip, "닫으면 배율 칩 = 판 배율"


def test_short_screen_and_ad_banner_look_as_before(zpage):
    pg = zpage
    fresh(pg)
    v = open_modal(pg, "pay")
    assert v["bh"] <= v["vh"] + 1 and v["bw"] <= v["vw"] + 1, ("짧은 화면은 굴림 없이 한눈에", v)
    pg.keyboard.press("Escape")
    v = open_modal(pg, "tiny")
    assert (v["bw"], v["bh"], v["s"]) == (320, 50, 1), ("작은 광고는 100% 그대로(키우지 않음)", v)
    pg.keyboard.press("Escape")


def test_ctrl_wheel_zooms_at_cursor_keys_and_chip_menu(zpage):
    pg = zpage
    fresh(pg)
    v0 = open_modal(pg, "web")
    cx, cy = v0["vx"] + v0["vw"] * 0.7, v0["vy"] + v0["vh"] * 0.4
    ctrl_wheel(pg, cx, cy, -120)                       # 창이 이미 칸에 꽉 참(폭 맞추기) — 커서 밑 점이 그대로
    v1 = pg.evaluate(VIEW)
    assert v1["s"] > v0["s"], (v0, v1)
    before = ((cx - v0["bx"]) / v0["s"], (cy - v0["by"]) / v0["s"])
    after = ((cx - v1["bx"]) / v1["s"], (cy - v1["by"]) / v1["s"])
    assert abs(before[0] - after[0]) < 2 and abs(before[1] - after[1]) < 2, ("커서 자리 확대", before, after, v0, v1)
    assert pct(v1) == round(v1["s"] * 100)
    pg.keyboard.press("Control+0")
    assert abs(pg.evaluate(VIEW)["s"] - v0["s"]) < 1e-3, "Ctrl+0 = 폭 맞추기"
    pg.keyboard.press("Control+Equal")
    up = pg.evaluate(VIEW)["s"]
    assert up > v0["s"], "Ctrl+= = 확대"
    pg.keyboard.press("Control+Minus")
    assert pg.evaluate(VIEW)["s"] < up, "Ctrl+- = 축소"
    for _ in range(30):
        pg.keyboard.press("Control+Minus")
    assert abs(pg.evaluate(VIEW)["s"] - 0.1) < 1e-6, "10% 에서 멈춤"
    pg.click("#zoom")
    rows = pg.evaluate("[...document.querySelectorAll('#vmenu button')].map(b => b.textContent)")
    assert [re.sub(r"Ctrl.*", "", r) for r in rows] == ["폭 맞추기", "100%", "확대", "축소"], rows
    pg.click('#vmenu button[data-z="100"]')
    v = pg.evaluate(VIEW)
    assert v["s"] == 1 and v["chip"].startswith("100%"), v
    pg.click("#zoom")
    pg.click('#vmenu button[data-z="fit"]')
    assert abs(pg.evaluate(VIEW)["s"] - v0["s"]) < 1e-3
    pg.keyboard.press("Escape")


def test_zoom_keys_and_wheel_inside_the_screen_frame(zpage):
    pg = zpage
    fresh(pg)
    v0 = open_modal(pg, "web")
    pg.mouse.click(v0["vx"] + v0["vw"] * 0.8, v0["vy"] + v0["vh"] * 0.8)   # 손 도구 — 화면 안 빈 곳(초점이 화면 iframe 으로)
    pg.wait_for_timeout(150)
    pg.keyboard.press("Control+Equal")
    pg.wait_for_function(f"(() => {{ const m = /scale\\(([\\d.]+)\\)/.exec(document.querySelector('#mframe').style.transform); return (m ? +m[1] : 1) > {v0['s'] + 0.01}; }})()", timeout=3000)
    pg.keyboard.press("Control+0")
    pg.wait_for_function(f"(() => {{ const m = /scale\\(([\\d.]+)\\)/.exec(document.querySelector('#mframe').style.transform); return Math.abs((m ? +m[1] : 1) - {v0['s']}) < 1e-3; }})()", timeout=3000)
    pg.keyboard.press("Escape")


def test_pin_outline_and_bar_stay_on_the_element_at_200_and_scrolled(zpage):
    pg = zpage
    fresh(pg, [NOTE])
    v0 = open_modal(pg, "web")
    pg.wait_for_selector("#mpins .pin-box", state="attached", timeout=5000)
    pg.click("#zoom")
    pg.click('#vmenu button[data-z="100"]')
    pg.keyboard.press("Control+Equal")
    pg.keyboard.press("Control+Equal")
    pg.keyboard.press("Control+Equal")
    pg.keyboard.press("Control+Equal")
    pg.keyboard.press("Control+Equal")                 # 1 → 1.1 → 1.25 → 1.5 → 1.75 → 2
    v = pg.evaluate(VIEW)
    assert v["s"] == 2 and v["chip"].startswith("200%"), v
    pg.evaluate("document.querySelector('#mview').scrollLeft = 0; document.querySelector('#mview').scrollTop = 0")
    pg.wait_for_timeout(200)
    pin = pg.locator("#mpins .pin-box").bounding_box()
    v = pg.evaluate(VIEW)
    want = {"x": v["bx"] + 24 * 2, "y": v["by"] + (24 + 56 + 20) * 2}   # 버튼 왼쪽 위(패딩 24 · 제목 줄 · 여백 20) × 2 — 대략
    assert abs(pin["x"] - want["x"]) < 12 and abs(pin["width"] - 240 * 2) < 12, ("핀 테두리 = 200% 의 버튼", pin, want)
    pg.keyboard.press("v")                            # 이동(요소 고르기) — 버튼 누르기 = 테두리 + 요소 막대
    pg.mouse.click(pin["x"] + pin["width"] / 2, pin["y"] + pin["height"] / 2)
    pg.wait_for_selector(".msel-box.pri", state="attached", timeout=4000)
    box = pg.locator(".msel-box.pri").bounding_box()
    assert all(abs(box[k] - pin[k]) < 3 for k in ("x", "y", "width", "height")), ("요소 테두리 = 핀 테두리", box, pin)
    bar = pg.locator("#elbar").bounding_box()
    assert bar and v["vx"] - 1 <= bar["x"] and bar["x"] + bar["width"] <= v["vx"] + v["vw"] + 1, ("요소 막대는 보이는 화면 칸 안", bar, v)
    pg.mouse.move(v["vx"] + v["vw"] / 2, v["vy"] + v["vh"] / 2)
    pg.mouse.wheel(0, 120)
    pg.wait_for_timeout(300)
    d = pg.evaluate(VIEW)["st"]
    assert d > 0
    pin2, box2 = pg.locator("#mpins .pin-box").bounding_box(), pg.locator(".msel-box.pri").bounding_box()
    assert abs(pin2["y"] - (pin["y"] - d)) < 2 and abs(box2["y"] - (box["y"] - d)) < 2, ("굴려도 핀·테두리가 버튼에 붙어 있다", pin, pin2, box, box2, d)
    pg.keyboard.press("h")
    pg.keyboard.press("Escape")
