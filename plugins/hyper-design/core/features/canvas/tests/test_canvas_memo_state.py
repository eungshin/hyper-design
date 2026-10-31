"""움직이는 화면(안내 단계)의 메모 — 단계가 바뀌면 점선·번호를 숨기고, 칩 줄의 번호를 누르면 그 단계로 간다(브라우저).

화면 둘:
- `steps` = 단계 약속 없음 — 같은 요소(#tip)의 글만 단계마다 바뀐다. 메모 상태 = 대상 글 스냅숏, 가기 = 클릭 기록(#next) 다시 하기(화면을 다시 읽은 뒤).
- `stepsx` = 단계 약속(`documentElement.dataset.hdState` · `window.hdGoto`)을 지키는 화면 — 가기 = hdGoto.
메모는 '둘째 단계'(#next 한 번 누른 뒤)에 달린 것으로 심는다(view = palette 가 메모 만들 때 싣는 상태와 같은 모양).
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import fit_view, frame_of

SHOTS = Path(os.environ.get("HD_SHOTS_MEMO_STATE", Path(tempfile.gettempdir()) / "claude" / "memo-state"))
BODY = """<div id="tip" style="margin:40px 16px;padding:14px;width:240px;background:#222;color:#fff;border-radius:12px"><b id="h">첫 단계</b> <span id="b">하나</span></div>
<button id="next" style="display:block;margin:16px;width:200px;height:44px">다음</button>"""
STEPS = """<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif">""" + BODY + """
<script>
var S = [['첫 단계', '하나'], ['둘째 단계', '둘'], ['셋째 단계', '셋']], i = 0;
function r() { document.getElementById('h').textContent = S[i][0]; document.getElementById('b').textContent = S[i][1]; %s }
document.getElementById('next').addEventListener('click', function () { i = Math.min(i + 1, 2); r(); });
%s
r();
</script></body></html>"""
PLAIN = STEPS % ("", "")
WITH_STATE = STEPS % ("document.documentElement.dataset.hdState = 'step-' + i;",
                      "window.hdGoto = function (s) { var k = +String(s).replace('step-', ''); if (!(k >= 0 && k < S.length)) return false; i = k; r(); return true; };")
SEED_JS = """() => {
    const t = (sid) => ({path: '#tip', text: '둘째 단계 둘', quote: {exact: '둘째 단계 둘', prefix: '', suffix: ''}});
    const m = (id, sid, view) => ({id, no: 1, screen: sid, targets: [t(sid)], path: '#tip', text: '둘째 단계 둘', rect: null, note: '둘째 단계 말풍선을 더 짧게',
                                   intent: 'change', sent: false, replies: [], view});
    const a = [m('m1', 'steps', {hd: null, trail: ['#next']}), m('m2', 'stepsx', {hd: 'step-1', trail: ['#next']})];
    const h = (function (s) { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(location.pathname);
    localStorage.setItem('hd-notes:' + h, JSON.stringify(a)); localStorage.setItem('hd-note-seq:' + h, JSON.stringify({steps: 1, stepsx: 1})); }"""


@pytest.fixture()
def spage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-memo-state-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "steps.html").write_text(PLAIN, encoding="utf-8")
    (out / "screens" / "stepsx.html").write_text(WITH_STATE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["안내"], "screens": [
        {"id": "steps", "file": "screens/steps.html", "title": "안내 단계", "group": "안내", "purpose": "단계", "policies": []},
        {"id": "stepsx", "file": "screens/stepsx.html", "title": "안내 단계(약속)", "group": "안내", "purpose": "단계", "policies": []}]},
        ensure_ascii=False), encoding="utf-8")
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


def _open_modal(pg, sid):
    fit_view(pg)
    pg.evaluate("(s) => document.querySelector('.card[data-id=\"' + s + '\"] .pres').click()", sid)
    pg.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    mf = _mframe(pg)
    mf.wait_for_selector("#next", timeout=5000)
    return mf


def _overlap(a, b):
    return a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]


@pytest.mark.area("modal", "notes")
def test_modal_step_change_hides_outline_chip_goes_back(spage):
    pg = spage
    mf = _open_modal(pg, "steps")
    box, chip = "#mpins .pin-box", "#mwin .mschips .mschip"
    pg.wait_for_selector(chip, timeout=5000)                       # 첫 단계 = 메모를 단 단계가 아님 → 칩
    assert pg.locator(box).count() == 0, "다른 단계에서는 점선·번호를 그리지 않는다"
    mf.click("#next")                                              # 둘째 단계 = 메모를 단 단계
    pg.wait_for_selector(box, state="attached", timeout=5000)
    pg.wait_for_selector(chip, state="detached", timeout=5000)
    mf.click("#next")                                              # 셋째 단계로 넘김 → 점선 사라짐 + 칩 생김
    pg.wait_for_selector(box, state="detached", timeout=5000)
    pg.wait_for_selector(chip, timeout=5000)
    c = pg.locator(chip)
    assert c.inner_text().strip() == "1", "칩 = 메모 번호(n.no)"
    assert not _overlap(c.bounding_box(), pg.locator("#mframe").bounding_box()), "칩은 화면 내용 밖(크게 보기 머리 줄)"
    c.hover()
    pg.wait_for_selector("#mschtip:not([hidden])", timeout=3000)
    assert "둘째 단계 말풍선을 더 짧게" in pg.inner_text("#mschtip"), "칩에 올리면 메모 글 미리보기"
    assert pg.locator(".nlost").count() == 0, "다른 단계의 메모는 '요소를 찾을 수 없음'이 아니다"
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / "modal-chip.png"))
    c.click()                                                      # 칩 누름 → 화면을 다시 읽고 #next 다시 → 둘째 단계
    pg.wait_for_selector(box, state="attached", timeout=8000)
    assert _mframe(pg).evaluate("document.getElementById('h').textContent") == "둘째 단계"
    pg.wait_for_selector(chip, state="detached", timeout=3000)
    pg.wait_for_selector("#thread:not([hidden]) li.focus", timeout=3000)   # 그 메모를 고른 상태
    pg.screenshot(path=str(SHOTS / "modal-after-chip.png"))


@pytest.mark.area("modal", "notes")
def test_board_chip_uses_screen_goto(spage):
    pg = spage
    zoom_to(pg, "stepsx", 0.7 * 812)
    fr = frame_of(pg, "stepsx")
    fr.wait_for_selector("#next", state="attached", timeout=5000)
    card = '.card[data-id="stepsx"]'
    chip = card + " > .mschips .mschip"
    pg.wait_for_selector(chip, timeout=5000)
    assert not _overlap(pg.locator(chip).bounding_box(), pg.locator(card + " .phone").bounding_box()), "칩은 카드 화면 밖(위쪽 빈 줄)"
    assert pg.locator(card + " .npbox").count() == 0
    fr.evaluate("window.__reloads = (window.__reloads || 0) + 1")
    pg.locator(chip).click()
    pg.wait_for_selector(card + " .npbox", state="attached", timeout=5000)
    assert fr.evaluate("document.documentElement.dataset.hdState") == "step-1"
    assert fr.evaluate("window.__reloads") == 1, "단계 약속이 있으면 다시 읽지 않고 hdGoto 로 간다"
    pg.wait_for_selector(chip, state="detached", timeout=3000)
    fr.evaluate("document.getElementById('next').click()")        # 넘기면 다시 칩
    pg.wait_for_selector(chip, timeout=5000)
    assert pg.locator(card + " .npbox").count() == 0


@pytest.mark.area("modal", "notes")
def test_chip_replay_failure_toasts_and_keeps_chip(spage):
    pg = spage
    pg.evaluate("""() => { const k = Object.keys(localStorage).find(k => k.startsWith('hd-notes:')), a = JSON.parse(localStorage.getItem(k));
        a.find(n => n.id === 'm1').view.trail = ['#nope']; localStorage.setItem(k, JSON.stringify(a)); }""")   # 다시 할 클릭의 요소가 없음
    reload(pg)
    _open_modal(pg, "steps")
    chip = "#mwin .mschips .mschip"
    pg.wait_for_selector(chip, timeout=5000)
    pg.locator(chip).click()
    pg.wait_for_function("(document.getElementById('toast').textContent || '').indexOf('이 단계로 바로 갈 수 없어요') >= 0", timeout=8000)
    assert pg.locator(chip).count() == 1, "실패하면 칩은 그대로"
