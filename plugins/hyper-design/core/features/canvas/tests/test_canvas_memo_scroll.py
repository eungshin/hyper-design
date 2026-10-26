"""R16 메모 점선·핀이 화면 안 스크롤을 따라간다 — 브라우저.

긴 화면(아래 버튼에 메모 하나)을 크게 보기로 열고 휠로 내리면 #mpins 의 점선 상자·핀이 그 요소 자리로 다시 놓인다(한 애니메이션 프레임에 한 번).
판 카드도 같다 — 카드 화면이 스크롤되면 .npbox·.npin 이 요소를 따라간다. 자리는 palette.js 가 스크롤 뒤 hd-located 를 다시 보내 정한다.
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import fit_view, frame_of

SHOTS = Path(os.environ.get("HD_SHOTS_R16", Path(tempfile.gettempdir()) / "claude" / "r15r16"))
TALL = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><h1 style="margin:16px">길게</h1><div style="height:500px;background:#eef"></div>
<button class="pay" style="display:block;margin:16px;width:240px;height:48px;font-size:16px">지금 결제하기</button>
<div style="height:1600px;background:#efe"></div></body></html>"""
SEED_JS = """() => { const t = {path: 'button.pay', text: '지금 결제하기', quote: {exact: '지금 결제하기', prefix: '', suffix: ''}};
    const a = [{id: 'm1', no: 1, screen: 'tall', targets: [t], path: t.path, text: t.text, rect: null, note: '버튼을 더 크게', intent: 'change', sent: false, replies: []}];
    const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
    localStorage.setItem('hd-notes:' + h, JSON.stringify(a)); localStorage.setItem('hd-note-seq:' + h, JSON.stringify({tall: 1})); }"""


@pytest.fixture()
def tpage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-memo-scroll-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "tall.html").write_text(TALL, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["긴"], "screens": [
        {"id": "tall", "file": "screens/tall.html", "title": "긴 화면", "group": "긴", "purpose": "스크롤", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto((out / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    pg.evaluate(SEED_JS)
    reload(pg)
    yield pg
    assert not errors, errors
    pg.close()
    shutil.rmtree(tmp, ignore_errors=True)


def _mframe(pg):
    return next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")


def _screen_box(pg, frame_sel, fr, sel):
    """틀(frame_sel) 안 요소 sel 의 상자 → 화면 좌표(틀 배율 포함)."""
    r = fr.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }", sel)
    f = pg.evaluate("(s) => { const f = document.querySelector(s), r = f.getBoundingClientRect(), sc = r.width / f.offsetWidth; return [r.left + f.clientLeft * sc, r.top + f.clientTop * sc, sc]; }", frame_sel)
    return {"x": f[0] + r[0] * f[2], "y": f[1] + r[1] * f[2], "w": r[2] * f[2], "h": r[3] * f[2]}


def _box(pg, sel):
    """점선 상자의 화면 자리 — 숨은 판 점선(묶음 줄에 올릴 때만 보임)도 재도록 감싼 카드 화면 상자 + style left/top(카드 CSS px × 판 배율)."""
    return pg.evaluate("""(s) => { const e = document.querySelector(s); if (!e) return null;
        if (getComputedStyle(e).display !== 'none') { const b = e.getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }
        const ph = e.closest('.phone'), r = ph.getBoundingClientRect(), k = r.width / ph.offsetWidth;
        return {x: r.left + parseFloat(e.style.left) * k, y: r.top + parseFloat(e.style.top) * k, w: parseFloat(e.style.width) * k, h: parseFloat(e.style.height) * k}; }""", sel)


def _follows(pg, box_sel, frame_sel, fr):
    """점선 상자가 요소 상자와 2px 안에서 겹칠 때까지(스크롤 뒤 다시 놓기) — 마지막 두 상자를 돌려준다."""
    b = t = None
    for _ in range(40):
        b, t = _box(pg, box_sel), _screen_box(pg, frame_sel, fr, "button.pay")
        if b and abs(b["y"] - t["y"]) <= 2 and abs(b["x"] - t["x"]) <= 2:
            return b, t
        pg.wait_for_timeout(50)
    raise AssertionError(("점선 상자가 요소를 따라가지 않는다", b, t))


@pytest.mark.area("modal", "notes")
def test_modal_memo_outline_and_pin_follow_wheel_scroll(tpage):
    pg = tpage
    fit_view(pg)
    pg.evaluate("document.querySelector('.card[data-id=\"tall\"] .pres').click()")
    pg.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    mf = _mframe(pg)
    mf.wait_for_selector("button.pay", timeout=5000)
    pg.wait_for_selector("#mpins .pin-box", state="attached", timeout=5000)
    _follows(pg, "#mpins .pin-box", "#mframe", mf)
    pin0 = _box(pg, "#mpins .pin")
    fb = _box(pg, "#mframe")
    pg.mouse.move(fb["x"] + fb["w"] / 2, fb["y"] + fb["h"] / 2)
    pg.mouse.wheel(0, 300)
    mf.wait_for_function("scrollY > 100", timeout=3000)
    pg.wait_for_timeout(100)
    b, t = _follows(pg, "#mpins .pin-box", "#mframe", mf)
    pin1 = _box(pg, "#mpins .pin")
    assert pin1["y"] < pin0["y"] - 50, ("번호 핀도 함께 올라간다", pin0, pin1)
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / "r16-modal-after-scroll.png"))


@pytest.mark.area("modal", "notes")
def test_board_card_memo_outline_follows_card_scroll(tpage):
    pg = tpage
    zoom_to(pg, "tall", 0.7 * 812)                    # 화면이 실제의 60% 이상 = 핀이 늘 보임
    fr = frame_of(pg, "tall")
    fr.wait_for_selector("button.pay", state="attached", timeout=5000)
    sel = '.card[data-id="tall"] .phone iframe'
    pg.wait_for_selector('.card[data-id="tall"] .npbox', state="attached", timeout=5000)
    _follows(pg, '.card[data-id="tall"] .npbox', sel, fr)
    fr.evaluate("scrollTo(0, 260)")
    pg.wait_for_timeout(100)
    _follows(pg, '.card[data-id="tall"] .npbox', sel, fr)
