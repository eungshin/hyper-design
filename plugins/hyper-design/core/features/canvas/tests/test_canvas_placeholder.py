"""생성 중 빈 틀(S5) — 도우미로 연 캔버스에서 실제 서버 이벤트(SSE)로 (Playwright).

1) 빈 레이아웃을 접속한(가짜) 에이전트에게 보냄 → 그 카드에 반짝이는 틀 '만드는 중… · <받는 곳>' → 답 반영됨(screens=[done]) →
   빈 카드 자리에 진짜 카드, 틀은 사라짐 + 토스트 '새 화면이 생겼어요' [보기].
2) 에이전트 진행 줄이 판에 없는 화면(coupon)을 말함 → 마지막 줄 옆 빈 자리 틀 + 카메라가 그 틀을 판 창 안으로 → 움직임 줄이기면 반짝임 없음 →
   에이전트가 떠남(bye) → 반짝임 멈춤 + 까닭 + [지우기] → 지우면 틀이 없어짐.

셸 붙이는 줄(ctx.view)은 아직 템플릿에 없다 — 이 테스트는 add_init_script 로 같은 칸을 만든다(셸이 view-motion 에 넘기는 getView/setView 를 잡아
mountAll ctx 에 view 로 더함). 실제 Paseo·Claude 에이전트에는 보내지 않는다(hello 한 가짜 에이전트, 이벤트로만 받음).
스크린숏은 HD_S5_SHOTS 가 있을 때만 그 폴더에.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_edit import fit_view
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("motion", "helper")
SHOTS = os.environ.get("HD_S5_SHOTS")

LAYOUT = {"id": "L1", "no": 1, "screen": "new-ab", "targets": [{"path": "(새 화면)", "text": "빈 레이아웃", "rect": None}], "path": "(새 화면)",
          "text": "빈 레이아웃", "rect": None, "intent": "change", "sent": False, "edit": "new-screen", "op": "new", "to": "", "value": "쿠폰",
          "purpose": "쿠폰을 고른다", "x": 900, "y": 0, "replies": [], "note": '새 화면 "쿠폰"(new-ab)을 빈 레이아웃으로 만들기'}

# 셸 붙이는 줄 흉내: view-motion 에 넘기는 getView/setView/pane 을 잡아 mountAll ctx.view 로
VIEW_HOOK = r"""
(() => {
  const HD = window.HD = window.HD || {};
  let vm, ma, cap = null;
  Object.defineProperty(HD, 'viewMotion', {configurable: true, get() { return vm; },
    set(v) { vm = Object.assign({}, v, {mount(c) { cap = c; return v.mount(c); }}); }});
  Object.defineProperty(HD, 'mountAll', {configurable: true, get() { return ma; },
    set(f) { ma = function (c) { if (cap) c.view = {get: cap.getView, set: cap.setView, pane: cap.pane}; return f(c); }; }});
})();
"""


@pytest.fixture()
def live(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-s5-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    (out / ".hd-canvas.json").write_text(json.dumps({"version": 1, "rev": 1, "updated": "2026-10-25T00:00:00Z", "state": {
        "notes": [LAYOUT], "note-seq": {"new-ab": 1}}}, ensure_ascii=False), encoding="utf-8")
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    post(srv, "/hello", {"agent": {"id": "t-agent", "name": "테스트 AI", "kind": "other", "listen": True}, "lease": 300})
    post(srv, "/api/attach", {"agent": "t-agent"})
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script(VIEW_HOOK)
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.wait_for_selector('#livechip[data-mode="live"]', timeout=8000)
    pg.srv = srv
    yield pg
    pg.close()
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def post(srv, path, body):
    base = srv.url.split("/index.html")[0]
    req = urllib.request.Request(base + path, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": srv.token})
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200, r.status
        return json.loads(r.read() or b"{}")


def shot(pg, name, sel=None):
    if not SHOTS:
        return
    Path(SHOTS).mkdir(parents=True, exist_ok=True)
    (pg.locator(sel) if sel else pg).screenshot(path=str(Path(SHOTS) / name))


ANIMS = "s => [...document.querySelector(s + ' .hd-gen-sheen').getAnimations()].map(a => ({state: a.playState, t: a.currentTime}))"
FRAME = '.card.draft[data-id="new-ab"] .hd-gen'
SLOT = '.hd-gen-slot[data-id="coupon"]'


def sheen(pg, sel):
    return pg.evaluate("s => { const e = document.querySelector(s + ' .hd-gen-sheen'); if (!e) return null; const c = getComputedStyle(e);"
                       " return {name: c.animationName, op: +c.opacity, shown: c.display !== 'none'}; }", sel)


def test_sent_blank_layout_shimmers_then_the_real_card_cross_fades_in(live):
    pg = live
    fit_view(pg)
    pg.wait_for_selector('.card.draft[data-id="new-ab"]')
    assert pg.query_selector(FRAME) is None, "보내기 전에는 빈 레이아웃 그대로"
    pg.evaluate("document.querySelector('#nsend').click()")
    pg.wait_for_selector(FRAME + '[data-state="pending"]', timeout=6000)
    assert "만드는 중" in pg.text_content(FRAME) and "테스트 AI" in pg.text_content(FRAME), pg.text_content(FRAME)
    a = sheen(pg, FRAME)
    assert a["shown"] and "hd-gen-sweep" in a["name"] and "hd-gen-breath" in a["name"], a
    shot(pg, "1-shimmer-a.png", '.card.draft[data-id="new-ab"]')
    t0 = pg.evaluate(ANIMS, FRAME)
    assert len(t0) == 2 and all(x["state"] == "running" for x in t0), t0   # 쓸기 + 숨쉬기가 도는 중
    pg.wait_for_timeout(1000)
    shot(pg, "1-shimmer-b.png", '.card.draft[data-id="new-ab"]')
    pg.wait_for_function("([s, t]) => { const e = document.querySelector(s + ' .hd-gen-sheen'); return e && e.getAnimations()[0] && e.getAnimations()[0].currentTime > t; }",
                         arg=[FRAME, t0[0]["t"]], timeout=5000)        # 시간이 흐른다(부하에서도 — 픽셀이 아니라 애니메이션 시계)
    post(pg.srv, "/api/reply", {"note": "L1", "reply": {"kind": "반영됨", "what": "쿠폰 화면을 완료 화면으로 만듦", "screens": ["done"], "captured": True}})
    pg.wait_for_selector('.card.draft[data-id="new-ab"]', state="detached", timeout=6000)
    pg.wait_for_function("document.querySelector('#toast') && !document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('새 화면이 생겼어요')", timeout=4000)
    assert pg.query_selector("#toast .hd-gen-view"), "[보기]"
    assert pg.query_selector('.card[data-id="done"]:not(.draft)')
    pg.wait_for_selector(".hd-gen-slot", state="detached", timeout=2000)   # 겹쳐 바꾼 틀 그림자는 0.3초 뒤 걷힘
    assert pg.query_selector(".hd-gen") is None
    shot(pg, "2-arrived-toast.png")
    pg.click("#toast .hd-gen-view")
    pg.wait_for_timeout(700)
    box = pg.evaluate("() => { const r = document.querySelector('.card[data-id=\"done\"] .phone').getBoundingClientRect(), p = document.querySelector('#screens').getBoundingClientRect();"
                      " return {cx: (r.left + r.right) / 2 - p.left, w: p.width}; }")
    assert abs(box["cx"] - box["w"] / 2) < 40, box


def test_progress_on_a_missing_screen_frames_it_then_failure_shows_reason_and_clear(live):
    pg = live
    fit_view(pg)
    post(pg.srv, "/progress", {"agent": "t-agent", "text": "쿠폰 화면 만드는 중", "screen": "coupon"})
    pg.wait_for_selector(SLOT + ' .hd-gen[data-state="pending"]', timeout=6000)
    assert "만드는 중" in pg.text_content(SLOT) and "테스트 AI" in pg.text_content(SLOT)
    pg.wait_for_timeout(900)                                            # 카메라 0.5초
    inside = pg.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect(), p = document.querySelector('#screens').getBoundingClientRect();"
                         " return r.left >= p.left - 1 && r.right <= p.right + 1 && r.top >= p.top - 1 && r.bottom <= p.bottom + 1; }", SLOT)
    assert inside, "틀이 판 창 안으로"
    assert "hd-gen-sweep" in sheen(pg, SLOT)["name"]
    pg.emulate_media(reduced_motion="reduce")
    assert sheen(pg, SLOT)["name"] == "none", "움직임 줄이기 = 반짝임 없음"
    pg.emulate_media(reduced_motion="no-preference")
    post(pg.srv, "/bye", {"id": "t-agent"})
    pg.wait_for_selector(SLOT + ' .hd-gen[data-state="failed"]', timeout=6000)
    assert "만들지 못했어요" in pg.text_content(SLOT) and "AI 연결이 끊겼어요" in pg.text_content(SLOT)
    assert sheen(pg, SLOT)["shown"] is False, "실패면 반짝임 멈춤"
    shot(pg, "3-failed.png", SLOT)
    pg.click(SLOT + " .hd-gen-clear")
    pg.wait_for_selector(SLOT, state="detached", timeout=2000)
