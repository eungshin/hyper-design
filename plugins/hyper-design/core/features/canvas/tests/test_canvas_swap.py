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

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, open_screen, swap_done, swap_mark, zoom_to  # noqa: F401

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


# 카드·화면 틀·그 안 iframe 의 보이는 높이(소수 둘째 자리) — 교체 앞뒤가 같아야 한다
HEIGHTS = """(s) => { const c = document.querySelector(s), r = (e) => Math.round(e.getBoundingClientRect().height * 100) / 100;
  return {card: r(c), phone: r(c.querySelector('.phone')), frame: r(c.querySelector('.phone iframe'))}; }"""


def seed_size(out, size):
    """카드마다 크기(task 46, 상태 이름 card-size) — 도우미가 index.html 에 끼워 넣는 상태 파일에 job 카드 크기를 미리 둔다."""
    (out / ".hd-canvas.json").write_text(json.dumps({"version": 1, "rev": 1, "updated": "2026-10-25T00:00:00Z",
                                                     "state": {"card-size": {"job": {"w": size[0], "h": size[1]}}}}), encoding="utf-8")


@pytest.mark.parametrize("size", [None, (600, 500)], ids=["default-size", "custom-size"])
def test_changed_card_crossfades_keeps_scroll_and_chip_says_done(ctx, out, size):
    if size:
        seed_size(out, size)
    srv = serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script(COUNT)
    try:
        open_board(pg, srv)
        if size:
            assert pg.get_attribute(JOB, "data-size") == "%d×%d" % size, "카드마다 크기(task 46)가 걸린 카드"
        pg.evaluate("window.__sameLoad = 1")
        h0 = pg.evaluate(HEIGHTS, JOB)
        old_key =pg.evaluate("(s) => { const w = document.querySelector(s + ' .phone iframe').contentWindow; w.scrollTo(0, 240); return w.location.pathname + w.location.search; }", JOB)
        assert pg.evaluate("(s) => document.querySelector(s + ' .phone iframe').contentWindow.scrollY", JOB) == 240
        post(srv, "/api/claim", {"screen": "job"})        # AI 가 이 카드를 고치는 중
        pg.wait_for_selector(JOB + ' .busy[data-kind="working"]', timeout=8000)
        pg.evaluate(TRACE, "job")
        m = swap_mark(pg)
        touch(out / "screens" / "job.html")
        swap_done(pg, "job", m)
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
        assert pg.evaluate(HEIGHTS, JOB) == h0, "교체해도 카드·틀 크기 그대로"
        assert new["y"] == 240, "스크롤 자리 그대로"
        assert new["op"] == "1" and new["pos"] == "static", "새 틀이 그 자리의 보통 틀이 된다"
        assert new["key"] != old_key and "hd-mode=board" in new["key"]
        got = pg.evaluate("window.__hdGot || {}")
        assert got.get(new["key"], {}).get("hd-pending", 0) >= 1, f"새 틀도 셸의 반영 대기를 받는다(ctx.frameLoaded): {got}"
        if got.get(old_key, {}).get("hd-theme-vars"):
            assert got.get(new["key"], {}).get("hd-theme-vars", 0) >= 1, f"옛 틀이 받은 테마를 새 틀도 받는다: {got}"
        pg.wait_for_selector(JOB + ' .busy[data-kind="done"]', timeout=4000)
        assert pg.text_content(JOB + ' .busy[data-kind="done"] .busy-txt').strip() == "방금 반영됨 ✓"
        assert pg.locator(JOB + ' .busy[data-kind="working"]').count() == 0
        pg.wait_for_selector(JOB + " .busy", state="detached", timeout=13000)   # 잠시 뒤 사라짐(전/후 보기가 있으면 10초, 48b)
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
        m = swap_mark(pg)
        touch(out / "screens" / "job.html")
        pill = JOB + " .swap-pill"
        pg.wait_for_selector(pill, timeout=10000)
        assert pg.text_content(pill) == "새 버전 준비됨 · 반영"
        pg.wait_for_timeout(600)
        assert pg.locator(JOB + " .phone iframe").count() == 2, "만지는 동안은 옛 화면 그대로(새 것은 숨어 기다림)"
        assert pg.evaluate("(s) => getComputedStyle(document.querySelector(s + ' .phone iframe.hd-swap-next')).opacity", JOB) == "0"
        pr, ph = pg.locator(pill).bounding_box(), pg.locator(JOB + " .phone").bounding_box()
        assert pr["y"] >= ph["y"] + ph["height"] - 0.5, f"알약은 화면 밖(카드 화면 밑 가장자리 아래) — 화면 안 버튼을 가리지 않는다: {pr} {ph}"
        shot(pg, "4-pill-below-card")
        pg.click(pill)
        swap_done(pg, "job", m)
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
        m = swap_mark(pg)
        touch(out / "screens" / "job.html")
        pg.wait_for_selector(pill, timeout=10000)
        pg.keyboard.press("Escape")
        pg.wait_for_function("document.getElementById('modal').hidden")
        swap_done(pg, "job", m)
        assert pg.locator(pill).count() == 0
        assert pg.evaluate("window.__sameLoad") == 1
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


SHOTS = pathlib.Path(os.environ.get("HD_SHOTS", "")) if os.environ.get("HD_SHOTS") else None
FRAME = "(s) => document.querySelector(s + ' .phone iframe')"


def shot(pg, name):
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(SHOTS / f"{name}.png"))


@pytest.mark.area("helper", "links")
def test_changed_blocks_flash_and_before_after_and_badges_return(ctx, out):
    """48b — 바뀐 글 블록은 외곽선, 새 블록은 떠오름 · 칩 [전/후] 로 옛 화면 겹쳐 보기 · 고른 카드의 링크 번호가 새 틀에도 · 움직임 줄이기 = 강조 없음"""
    srv = serve(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        open_board(pg, srv)
        b = pg.locator(JOB + " .phone").bounding_box()
        pg.mouse.click(b["x"] + 20, b["y"] + b["height"] - 20)    # 손 도구 한 번 = 그 카드 고르기 → 화면 안 링크 번호
        badges = "(s) => { const d = document.querySelector(s + ' .phone iframe').contentDocument; return d.querySelectorAll('[data-hd-links]').length; }"
        pg.wait_for_function(badges, arg=JOB, timeout=6000)
        n_badges = pg.evaluate(badges, JOB)
        pg.wait_for_function("(s) => document.querySelector(s).classList.contains('xp')", arg=JOB, timeout=4000)   # 고른 긴 화면 = 펼침(view-links)
        pg.wait_for_timeout(500)                          # 펼치기 전환(--resize-dur)이 끝난 크기
        h0 = pg.evaluate(HEIGHTS, JOB)
        post(srv, "/api/claim", {"screen": "job"})
        pg.wait_for_selector(JOB + ' .busy[data-kind="working"]', timeout=8000)
        m = swap_mark(pg)
        job = out / "screens" / "job.html"
        job.write_text(job.read_text(encoding="utf-8").replace("하는 일이 무엇인가요?", "무슨 일을 하세요?")
                       .replace('<div class="tile-grid"', '<p class="note">새 안내 한 줄</p><div class="tile-grid"'), encoding="utf-8")
        swap_done(pg, "job", m)
        assert pg.evaluate(HEIGHTS, JOB) == h0, "펼친(고른 긴 화면) 카드도 교체 앞뒤 크기 그대로 — 새 틀이 옛 틀의 인라인 높이를 이어받는다"
        anim = """(s) => { const d = document.querySelector(s + ' .phone iframe').contentDocument;
            const a = (q) => { const el = d.querySelector(q); return el ? el.getAnimations().map(x => Object.keys(x.effect.getKeyframes()[0]).filter(k => !['offset', 'easing', 'composite', 'computedOffset'].includes(k)).sort().join(',')) : null; };
            return {h1: a('h1.title'), note: a('p.note'), lead: a('p.lead'), tile: a('button.tile')}; }"""
        pg.wait_for_function("(s) => document.querySelector(s + ' .phone iframe').contentDocument.querySelector('h1.title').getAnimations().length > 0", arg=JOB, timeout=4000)
        a = pg.evaluate(anim, JOB)                      # 떠오름은 0.3초 — 찍기 전에 읽는다
        pg.wait_for_timeout(100)
        shot(pg, "1-mid-highlight")
        assert a["h1"] == ["outline,outlineOffset"], f"바뀐 글 블록 = 외곽선: {a}"
        assert a["note"] == ["opacity,transform"], f"새 블록 = 떠오름: {a}"
        assert a["lead"] == [] and a["tile"] == [], f"안 바뀐 것은 그대로: {a}"
        pg.wait_for_timeout(1200)
        assert pg.evaluate("(s) => { const d = document.querySelector(s + ' .phone iframe').contentDocument, n = d.querySelector('p.note');"
                           " return [d.querySelector('h1.title').getAnimations().length, getComputedStyle(n).opacity, n.style.cssText]; }", JOB) == [0, "1", ""], \
            "강조가 끝나면 화면 문서에 남는 것이 없다"
        pg.wait_for_function(badges, arg=JOB, timeout=6000)
        assert pg.evaluate(badges, JOB) == n_badges, "고른 카드의 링크 번호가 새 틀에도 돌아온다"
        # 전/후 보기
        chip = JOB + ' .busy[data-kind="done"]'
        cmp = chip + ' [data-act="compare"]'
        assert pg.text_content(cmp) == "전/후" and pg.get_attribute(cmp, "aria-pressed") == "false"
        pg.click(cmp)
        over = JOB + " .phone iframe.hd-swap-before"
        pg.wait_for_selector(over, timeout=3000)
        pg.wait_for_function("(s) => { const f = document.querySelector(s); return f.contentDocument && f.contentDocument.querySelector('h1.title'); }", arg=over, timeout=5000)
        assert pg.evaluate("(s) => document.querySelector(s).contentDocument.querySelector('h1.title').textContent", over) == "하는 일이 무엇인가요?"
        assert pg.get_attribute(cmp, "aria-pressed") == "true" and "바뀌기 전 화면" in pg.text_content(chip)
        assert pg.evaluate("(s) => document.querySelectorAll(s + ' .phone iframe')[0].contentDocument.querySelector('h1.title').textContent", JOB) == "무슨 일을 하세요?", \
            "카드의 틀(첫 iframe)은 새 화면 그대로 — 옛 화면은 위에 겹친 것뿐"
        pg.wait_for_timeout(300)
        shot(pg, "2-before-overlay")
        pg.wait_for_timeout(2200)                       # 보는 동안은 칩이 사라지지 않는다(DONE_MS 2초를 넘겨도)
        assert pg.locator(over).count() == 1 and pg.locator(chip).count() == 1
        pg.click(cmp)
        assert pg.locator(over).count() == 0 and pg.get_attribute(cmp, "aria-pressed") == "false"
        shot(pg, "3-after")
        # 움직임 줄이기 = 숨기기·강조 없음
        pg.emulate_media(reduced_motion="reduce")
        m = swap_mark(pg)
        job.write_text(job.read_text(encoding="utf-8").replace("무슨 일을 하세요?", "하는 일을 골라 주세요"), encoding="utf-8")
        pg.wait_for_function("(s) => document.querySelector(s + ' .phone iframe').contentDocument.querySelector('h1.title').textContent === '하는 일을 골라 주세요'", arg=JOB, timeout=10000)
        swap_done(pg, "job", m)
        pg.wait_for_timeout(900)
        assert pg.evaluate("(s) => { const d = document.querySelector(s + ' .phone iframe').contentDocument; return [d.querySelector('h1.title').textContent, d.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('h1')).length]; }", JOB) \
            == ["하는 일을 골라 주세요", 0]
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
