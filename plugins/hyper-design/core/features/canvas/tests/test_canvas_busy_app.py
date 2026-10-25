"""#272 앱 카드(file = 개발 서버 주소)의 "AI 수정 중" 칩 걷기 — 브라우저 1개 + 도우미 + 작은 http 서버(가짜 개발 서버).

job 카드의 file 을 http://127.0.0.1:<port>/screens/job.html 로 바꿔 앱 카드처럼 만들고(mtime 없음), 그 카드 iframe 이 보내는 hd-here 로:
HMR(hd-here {hmr:true}) = 걷힘 · 덮개 뒤 다시 실림 = 걷힘 · error 알림 = 그대로 · 판을 새로 고친 뒤 그 카드의 첫 로드 = 그대로.
규칙 자체는 test_canvas_unit_busy_lift.py(unit)."""
import functools
import http.server
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

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, zoom_to  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("helper")
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
CHIP = '.card[data-id="job"] .busy'


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture()
def app_out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-busy-app-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    dev = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(o)))
    threading.Thread(target=dev.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/screens/job.html" % dev.server_address[1]
    sj = o / "screens.json"
    data = json.loads(sj.read_text(encoding="utf-8"))
    for s in data["screens"]:
        if s["id"] == "job":
            s["file"] = url
    sj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    try:
        yield o, url
    finally:
        dev.shutdown(); dev.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


def post(srv, path, body):
    req = urllib.request.Request(srv.url.split("/index.html")[0] + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": srv.token})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def settled(pg, out):
    """판이 걷은 것을 상태 파일에 쓸 때까지(다음 claim 과 겹쳐 409 → 다시 읽기가 되지 않게)."""
    for _ in range(80):
        st = json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"]
        if "job" not in ((st.get("busy") or {}).get("items") or {}):
            return
        pg.wait_for_timeout(100)
    raise AssertionError("걷은 덮개가 상태 파일에 쓰이지 않았다")


def job_frame(pg, url):
    """job 카드 iframe(앱 주소)이 실리면 그 frame. 판은 보이는 카드만 불러오니(위에 DS 카드 줄 등 판 배치에 따라 처음 카메라 밖일 수 있다) 아직 안 실렸으면 그 카드로 카메라를 옮긴다."""
    if pg.evaluate("!!document.querySelector('.card[data-id=\"job\"] iframe[data-src]')"):
        zoom_to(pg, "job", 420)
    pg.wait_for_function("(u) => [...document.querySelectorAll('.card[data-id=\"job\"] iframe')].some(f => (f.src || '').startsWith(u))", arg=url, timeout=8000)
    for _ in range(80):
        f = next((f for f in pg.frames if f.url.startswith(url)), None)
        if f:
            f.wait_for_load_state("load")
            return f
        pg.wait_for_timeout(100)
    raise AssertionError("job 카드 frame 이 없다")


def test_app_card_chip_lifts_on_hmr_or_reload_not_on_first_load(ctx, app_out):
    out, url = app_out
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        fr = job_frame(pg, url)
        pg.wait_for_timeout(300)                           # 카드의 첫 hd-here 가 판에 닿도록

        post(srv, "/api/claim", {"screen": "job", "by": "agent-9"})
        pg.wait_for_selector(CHIP + '[data-via="cli"]', timeout=8000)
        fr.evaluate("parent.postMessage({type: 'hd-here', screen: 'job', error: '/src/x.js: boom'}, '*')")
        pg.wait_for_timeout(600)
        assert pg.locator(CHIP).count() == 1, "감싸개의 error 알림으로는 걷히지 않는다"
        fr.evaluate("parent.postMessage({type: 'hd-here', screen: 'job', hmr: true}, '*')")   # = 감싸개의 vite:afterUpdate 알림
        pg.wait_for_selector(CHIP, state="detached", timeout=4000)
        settled(pg, out)

        post(srv, "/api/claim", {"screen": "job", "by": "agent-9"})
        pg.wait_for_selector(CHIP + '[data-via="cli"]', timeout=8000)
        pg.wait_for_timeout(100)
        fr = job_frame(pg, url)
        fr.evaluate("location.reload()")                   # 덮개 뒤 다시 실림(전체 새로 고침 HMR) = 걷힘
        pg.wait_for_selector(CHIP, state="detached", timeout=6000)
        settled(pg, out)

        post(srv, "/api/claim", {"screen": "job", "by": "agent-9"})
        pg.wait_for_selector(CHIP + '[data-via="cli"]', timeout=8000)
        pg.reload()                                        # 판을 새로 고침 → 그 카드의 첫 로드는 AI 수정이 아니다
        pg.wait_for_function("window.__hdReady !== undefined")
        job_frame(pg, url)
        pg.wait_for_selector(CHIP + '[data-via="cli"]', timeout=8000)
        pg.wait_for_timeout(1500)
        assert pg.locator(CHIP).count() == 1, "판 새로 고침 뒤 첫 로드로는 걷히지 않는다"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def test_app_card_error_shows_once_on_card_not_toast(ctx, app_out):
    """W3 #280 후속 — 감싸개의 hd-here {error} 는 그 카드 화면 밑 한 줄(.cerr) · 같은 글은 한 번(경고도) · 토스트 아님 · 다시 잘 실리면 걷힘."""
    out, url = app_out
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors, warns = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "warning" and "앱 카드 job" in m.text and warns.append(m.text))
    line = '.card[data-id="job"] .cerr'
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        fr = job_frame(pg, url)
        pg.wait_for_timeout(300)
        pg.evaluate("""() => { window.__toasts = []; const t = document.getElementById('toast');
            new MutationObserver(() => window.__toasts.push(t.textContent)).observe(t, {childList: true, characterData: true, subtree: true}); }""")
        for _ in range(3):
            fr.evaluate("parent.postMessage({type: 'hd-here', screen: 'job', error: '/src/twin/stages.js: Failed to fetch'}, '*')")
        pg.wait_for_selector(line, timeout=3000)
        pg.wait_for_timeout(300)
        assert pg.locator(line).count() == 1 and pg.text_content(line) == "⚠ /src/twin/stages.js: Failed to fetch"
        assert pg.get_attribute(line, "role") == "alert"
        assert len(warns) == 1, warns
        assert not [t for t in pg.evaluate("window.__toasts") if "stages" in t], "토스트가 아니다"
        assert pg.evaluate("""() => { const c = document.querySelector('.card[data-id="job"]'), e = c.querySelector('.cerr'), p = c.querySelector('.phone');
            return e.previousElementSibling === p; }"""), "화면 바로 밑"
        fr.evaluate("parent.postMessage({type: 'hd-here', screen: 'job', error: '/src/settings/store.js: nope'}, '*')")
        pg.wait_for_function("(s) => (document.querySelector(s) || {}).textContent === '⚠ /src/settings/store.js: nope'", arg=line, timeout=3000)
        assert len(warns) == 2
        fr.evaluate("parent.postMessage({type: 'hd-here', screen: 'job'}, '*')")   # = 다시 잘 실림(palette.js 로드 알림)
        pg.wait_for_selector(line, state="detached", timeout=3000)
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
