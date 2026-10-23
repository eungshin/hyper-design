"""앱 프로젝트 끝까지(slow) — 진짜 Dayfine 앱(C:/Code/dictionary/ui_host/popup, 읽기만)으로:
vite(감싸개, 빈 포트) → app_out --build → 캔버스를 다른 origin(http.server)에서 Playwright 로 연다 →
카드가 무대를 싣고 · 캔버스→카드 postMessage(hd-hit-at, hd-pick+클릭)가 origin 을 넘어 답하고 · 답에 src.file(.svelte) · HMR 웹소켓 연결.
앱 저장소의 git status 가 처음과 같아야 한다(아무것도 쓰지 않음). 앱이나 node·vite·playwright 가 없으면 이유와 함께 건너뛴다."""
import functools, http.server, json, os, shutil, socket, subprocess, sys, threading, time, urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

HERE = Path(__file__).resolve().parent
APP_PY = HERE.parent / "app_out.py"
WRAPPER = HERE.parent / "dayfine.vite.mjs"
UI = Path(os.environ.get("HD_DAYFINE_UI", "C:/Code/dictionary/ui_host/popup"))
VITE = UI / "node_modules" / "vite" / "bin" / "vite.js"
NODE = shutil.which("node")


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def _git_status():
    git = shutil.which("git")
    if not git:
        return None
    r = subprocess.run([git, "-C", str(UI), "status", "--porcelain", "--untracked-files=all", "--", "."], capture_output=True, text=True, encoding="utf-8")
    return sorted(l for l in r.stdout.splitlines() if l.startswith("??"))   # 새 파일만 본다(고친 파일은 다른 세션이 동시에 만들 수 있다)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    if not (UI / "src" / "twin" / "registry.js").is_file():
        pytest.skip(f"Dayfine 앱이 없음: {UI}")
    if not VITE.is_file():
        pytest.skip(f"앱의 node_modules 에 vite 가 없음: {VITE} (npm install 은 앱 저장소 쪽 일 — 여기서 하지 않는다)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright 가 없음")
    before = _git_status()
    port = _free_port()
    dev = f"http://127.0.0.1:{port}"
    log = tmp_path_factory.mktemp("hd-app-vite") / "vite.log"
    lf = open(log, "w", encoding="utf-8")
    proc = subprocess.Popen([NODE, str(VITE), "--mode", "twin", "--config", str(WRAPPER), "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
                            cwd=str(UI), env=dict(os.environ, HD_APP_DIR=str(UI)), stdout=lf, stderr=subprocess.STDOUT)
    srv = None
    try:
        t0 = time.time()
        while True:
            try:
                with urllib.request.urlopen(dev + "/hd-stage/word-header.html", timeout=2) as r:
                    if r.status == 200:
                        break
            except OSError:
                pass
            if proc.poll() is not None or time.time() - t0 > 40:
                lf.flush()
                pytest.fail("vite 가 뜨지 않음:\n" + log.read_text(encoding="utf-8", errors="replace")[-2000:])
            time.sleep(0.3)
        out = tmp_path_factory.mktemp("hd-app-out") / "out"
        r = subprocess.run([sys.executable, str(APP_PY), str(UI), str(out), "--dev-url", dev, "--build"], capture_output=True, text=True,
                           encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        assert r.returncode == 0, r.stdout + r.stderr
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(out)))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            b = p.chromium.launch()
            try:
                yield {"out": out, "dev": dev, "canvas": f"http://127.0.0.1:{srv.server_address[1]}/index.html", "browser": b}
            finally:
                b.close()
    finally:
        if srv:
            srv.shutdown(); srv.server_close()
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        lf.close()
    after = _git_status()
    assert before == after, "앱 폴더에 새 파일이 생겼다(아무것도 쓰면 안 됨)"


ASK = """([stage, msg, click]) => new Promise((res) => {
  const f = [...document.querySelectorAll('iframe')].find((x) => (x.src || '').includes('/hd-stage/' + stage + '.html'));
  if (!f) { res('no-iframe'); return; }
  const want = msg.type === 'hd-hit-at' ? 'hd-hit' : 'hd-picked';
  addEventListener('message', (e) => { if (e.data && e.data.type === want && e.source === f.contentWindow) res(e.data); });
  f.contentWindow.postMessage(msg, '*');
  setTimeout(() => res('timeout'), 4000);
})"""

TARGET = """() => { const e = [...document.querySelectorAll('*')].filter((x) => x.__svelte_meta).find((x) => x.innerText && x.innerText.trim());
  const r = e.getBoundingClientRect(); return {x: r.left + r.width / 2, y: r.top + r.height / 2}; }"""


def test_card_stage_answers_across_origin_with_svelte_source(live):
    pg = live["browser"].new_page(viewport={"width": 1400, "height": 900})
    logs = []
    pg.on("console", lambda m: logs.append(m.text))
    pg.goto(live["canvas"])
    deadline = time.time() + 20
    fr = None
    while time.time() < deadline and not fr:
        fr = next((f for f in pg.frames if "/hd-stage/word-header.html" in f.url), None)
        if not fr:
            pg.wait_for_timeout(200)
    assert fr, [f.url for f in pg.frames]
    fr.wait_for_function("document.querySelectorAll('#hd-stage-root *').length > 0", timeout=20000)
    assert fr.evaluate("location.origin") != pg.evaluate("location.origin")          # 카드는 다른 origin(개발 서버)
    pt = fr.evaluate(TARGET)
    hit = pg.evaluate(ASK, ["word-header", {"type": "hd-hit-at", "x": pt["x"], "y": pt["y"]}, False])
    assert isinstance(hit, dict), hit
    assert hit["screen"] == "word-header" and hit["path"]
    assert hit["src"]["file"].endswith(".svelte") and hit["src"]["file"].startswith("ui_host/popup/src/"), hit["src"]
    assert hit["src"]["line"] > 0 and hit["comp"]
    # 고르기(크게 보기에서 쓰는 메시지): hd-pick 켜고 그 요소를 누르면 hd-picked 에도 src
    pg.evaluate("""() => { const f = [...document.querySelectorAll('iframe')].find((x) => (x.src || '').includes('/hd-stage/word-header.html'));
      window.__picked = null; addEventListener('message', (e) => { if (e.data && e.data.type === 'hd-picked' && e.source === f.contentWindow) window.__picked = e.data; });
      f.contentWindow.postMessage({type: 'hd-pick', on: true}, '*'); }""")
    fr.wait_for_function("document.documentElement.style.cursor === 'crosshair'", timeout=5000)
    fr.evaluate("([x, y]) => document.elementFromPoint(x, y).dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, clientX: x, clientY: y}))",
                [pt["x"], pt["y"]])
    pg.wait_for_function("window.__picked !== null", timeout=5000)
    picked = pg.evaluate("window.__picked")
    assert picked["screen"] == "word-header" and picked["src"]["file"].endswith(".svelte")
    # HMR: 카드 안 vite 클라이언트가 개발 서버 웹소켓에 붙었다(캔버스 origin 과 무관)
    t0 = time.time()
    while "[vite] connected." not in logs and time.time() - t0 < 10:
        pg.wait_for_timeout(200)
    assert "[vite] connected." in logs, logs[:20]


def test_out_folder_is_a_normal_relaunchable_project(live):
    out = live["out"]
    app = json.loads((out / "app.json").read_text(encoding="utf-8"))
    assert app["kind"] == "app" and app["dev_url"] == live["dev"] and "word-header" in app["stages"]
    assert Path(app["ui_dir"]) == UI.resolve() and "--config" in app["dev_cmd"]
    screens = json.loads((out / "screens.json").read_text(encoding="utf-8"))["screens"]
    assert {s["id"] for s in screens} >= set(app["stages"])
    assert (out / "index.html").is_file() and (out / "palette.js").is_file()
