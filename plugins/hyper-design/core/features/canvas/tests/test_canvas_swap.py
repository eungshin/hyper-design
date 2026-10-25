"""48a 스며드는 교체 — 화면 파일이 바뀐 카드가 깜빡임 없이 겹쳐 바뀐다(브라우저 1개 + 도우미).

- 새 버전은 숨긴 두 번째 iframe 에 먼저 실리고, 다 실린 뒤 0.2초 겹쳐 바뀐 다음에야 옛 iframe 이 빠진다(흰 깜빡임 없음) · 스크롤 유지
  · 새 틀도 셸에게서 테마(hd-theme-vars, 옛 틀이 받았다면)와 반영 대기(hd-pending)를 받는다 · 칩 "AI 수정 중" → "방금 반영됨 ✓" → 사라짐
- 그 카드를 만지는 중(메모 창 · 크게 보기)이면 미루고 알약 "새 버전 준비됨 · 반영" — 누르면 바로 · 만지기가 끝나면 저절로
규칙 자체는 test_canvas_unit_swap.py(unit)."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, open_screen, zoom_to  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("helper")
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
JOB = '.card[data-id="job"]'

# 카드 틀마다 받은 메시지 수(틀 주소 = location.search 의 v) — 새 틀이 셸의 load 뒤 일을 받았나
COUNT = """if (window !== window.top) { addEventListener('message', e => {
  const t = e.data && e.data.type; if (t !== 'hd-pending' && t !== 'hd-theme-vars') return;
  try { const m = (top.__hdGot = top.__hdGot || {}), k = location.pathname + location.search; (m[k] = m[k] || {})[t] = ((m[k] || {})[t] || 0) + 1; } catch (_) {} }); }"""

# 그 카드 .phone 안 iframe 이 들고 나는 차례(시각 ms) — 새 틀 붙음 · 겹쳐 보이기 시작 · 옛 틀 빠짐
TRACE = """(id) => { const ph = document.querySelector('.card[data-id="' + id + '"] .phone'), log = window.__swapLog = [];
  const old = ph.querySelector('iframe'); old.__old = 1;
  new MutationObserver(ms => ms.forEach(m => {
    m.addedNodes.forEach(n => { if (n.tagName === 'IFRAME') log.push(['add', performance.now(), n.className]); });
    m.removedNodes.forEach(n => { if (n.tagName === 'IFRAME') log.push(['remove', performance.now(), n.__old ? 'old' : 'new']); });
    if (m.type === 'attributes' && m.target.tagName === 'IFRAME' && m.target.classList.contains('hd-swap-in')) log.push(['in', performance.now(), '']);
  })).observe(ph, {childList: true, subtree: true, attributes: true, attributeFilter: ['class']}); }"""


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-swap-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    job = o / "screens" / "job.html"                    # 스크롤이 남는지 보려면 카드보다 긴 화면
    job.write_text(job.read_text(encoding="utf-8").replace("</body>", '<div style="height:2400px"></div></body>'), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def serve(out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def post(srv, path, body):
    req = urllib.request.Request(srv.url.split("/index.html")[0] + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": srv.token})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def touch(f):
    f.write_text(f.read_text(encoding="utf-8") + "\n<!-- AI 가 고침 -->\n", encoding="utf-8")


def open_board(pg, srv):
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    zoom_to(pg, "job", 420)
    pg.wait_for_function("(s) => { const f = document.querySelector(s + ' .phone iframe'); return f && !f.hasAttribute('data-src') && f.contentDocument && f.contentDocument.readyState === 'complete'; }",
                         arg=JOB, timeout=10000)
    pg.wait_for_timeout(300)


def swapped(pg):
    pg.wait_for_function("(s) => { const fs = document.querySelectorAll(s + ' .phone iframe'); return fs.length === 1 && !fs[0].__old && !fs[0].classList.contains('hd-swap-next'); }",
                         arg=JOB, timeout=10000)


def test_changed_card_crossfades_keeps_scroll_and_chip_says_done(ctx, out):
    srv = serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script(COUNT)
    try:
        open_board(pg, srv)
        pg.evaluate("window.__sameLoad = 1")
        old_key = pg.evaluate("(s) => { const w = document.querySelector(s + ' .phone iframe').contentWindow; w.scrollTo(0, 240); return w.location.pathname + w.location.search; }", JOB)
        assert pg.evaluate("(s) => document.querySelector(s + ' .phone iframe').contentWindow.scrollY", JOB) == 240
        post(srv, "/api/claim", {"screen": "job"})        # AI 가 이 카드를 고치는 중
        pg.wait_for_selector(JOB + ' .busy[data-kind="working"]', timeout=8000)
        pg.evaluate(TRACE, "job")
        touch(out / "screens" / "job.html")
        swapped(pg)
        log = pg.evaluate("window.__swapLog")
        # 파일 쓰기가 감시에 두 번 잡히면(비우고 쓰기) 먼저 싣던 새 틀은 버려지고 새로 싣는다 — 옛 틀은 그동안 그대로 보인다.
        # 지키는 것: 옛 틀은 마지막 새 틀이 드러난 뒤에만, 0.2초 겹친 뒤 빠진다
        old_out = [i for i, e in enumerate(log) if e[0] == "remove" and e[2] == "old"]
        assert len(old_out) == 1, f"옛 틀은 한 번만 빠진다: {log}"
        tail = log[:old_out[0] + 1]
        last_add = max(i for i, e in enumerate(tail) if e[0] == "add")
        kinds = [e[0] for e in tail[last_add:]]
        assert kinds == ["add", "in", "remove"] and tail[last_add][2] == "hd-swap-next", log
        assert tail[-1][1] - tail[-2][1] >= 150, f"옛 틀은 0.2초 겹쳐 보인 뒤에야 빠진다: {log}"
        new = pg.evaluate("""(s) => { const f = document.querySelector(s + ' .phone iframe'), w = f.contentWindow;
            return {y: w.scrollY, key: w.location.pathname + w.location.search, op: getComputedStyle(f).opacity, pos: getComputedStyle(f).position}; }""", JOB)
        assert new["y"] == 240, "스크롤 자리 그대로"
        assert new["op"] == "1" and new["pos"] == "static", "새 틀이 그 자리의 보통 틀이 된다"
        assert new["key"] != old_key and "hd-mode=board" in new["key"]
        got = pg.evaluate("window.__hdGot || {}")
        assert got.get(new["key"], {}).get("hd-pending", 0) >= 1, f"새 틀도 셸의 반영 대기를 받는다(ctx.frameLoaded): {got}"
        if got.get(old_key, {}).get("hd-theme-vars"):
            assert got.get(new["key"], {}).get("hd-theme-vars", 0) >= 1, f"옛 틀이 받은 테마를 새 틀도 받는다: {got}"
        pg.wait_for_selector(JOB + ' .busy[data-kind="done"]', timeout=4000)
        assert pg.text_content(JOB + ' .busy[data-kind="done"]').strip() == "방금 반영됨 ✓"
        assert pg.locator(JOB + ' .busy[data-kind="working"]').count() == 0
        pg.wait_for_selector(JOB + " .busy", state="detached", timeout=4000)   # 약 2초 뒤 사라짐
        assert pg.evaluate("window.__sameLoad") == 1, "판은 다시 불러오지 않는다"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "notes")
def test_touched_card_waits_with_pill_then_swaps(ctx, out):
    srv = serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        open_board(pg, srv)
        pg.evaluate("window.__sameLoad = 1")
        # 1) 메모 창이 그 카드에 열려 있음 → 미룸 + 알약 → 알약을 누르면 바로
        pg.keyboard.press("m")
        b = pg.locator(JOB + " .phone").bounding_box()
        pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 3)
        pg.wait_for_selector("#pop:not([hidden])", timeout=4000)
        assert pg.evaluate("(s) => document.querySelector(s).classList.contains('memo-target')", JOB)
        pg.evaluate(TRACE, "job")
        touch(out / "screens" / "job.html")
        pill = JOB + " .swap-pill"
        pg.wait_for_selector(pill, timeout=10000)
        assert pg.text_content(pill) == "새 버전 준비됨 · 반영"
        pg.wait_for_timeout(600)
        assert pg.locator(JOB + " .phone iframe").count() == 2, "만지는 동안은 옛 화면 그대로(새 것은 숨어 기다림)"
        assert pg.evaluate("(s) => getComputedStyle(document.querySelector(s + ' .phone iframe.hd-swap-next')).opacity", JOB) == "0"
        pg.click(pill)
        swapped(pg)
        assert pg.locator(pill).count() == 0
        # 2) 크게 보기가 그 화면 → 미룸 → 닫으면 저절로
        pg.keyboard.press("Escape")
        pg.wait_for_selector("#pop", state="hidden", timeout=4000)
        # 숨은 메모 칸(#pnote)이 아직 포커스를 쥐고 있으면(Chrome 은 다음 그리기 때 놓는다) 'h' 가 입력으로 읽혀 도구가 안 바뀐다 — 48b 탐침으로 찾은 깨짐
        pg.wait_for_function("!document.getElementById('pop').contains(document.activeElement)")
        pg.keyboard.press("h")                            # 메모 도구를 끄고(손: 카드 누르기 = 크게 보기 — V 는 49a 부터 고른 카드 안 요소 고르기)
        assert pg.get_attribute('#tools [data-tool="hand"]', "aria-pressed") == "true"
        open_screen(pg, "job")
        post(srv, "/api/claim", {"screen": "job"})        # AI 덮개 길(방금 다시 실은 카드의 5초 건너뛰기와 상관없이)
        pg.wait_for_selector(JOB + ' .busy[data-kind="working"]', timeout=8000)
        pg.evaluate(TRACE, "job")
        touch(out / "screens" / "job.html")
        pg.wait_for_selector(pill, timeout=10000)
        pg.keyboard.press("Escape")
        pg.wait_for_function("document.getElementById('modal').hidden")
        swapped(pg)
        assert pg.locator(pill).count() == 0
        assert pg.evaluate("window.__sameLoad") == 1
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
