"""Client — 썸네일: 헤드리스 Edge/Chrome 으로 <out>/index.html(file://)을 PNG 로 찍고, 허브가 낡은 것을 뒤에서 하나씩 다시 찍는다.

- 브라우저: msedge.exe(Program Files (x86)/Microsoft/Edge) → 없으면 Chrome. 둘 다 없으면 썸네일 없음(카드는 빈 그림)
- 찍기: --headless=new --screenshot=<png> --window-size=1260,780(42:26) --virtual-time-budget=6000 --hide-scrollbars,
  따로 쓰는 프로필 <HD_HOME>/thumbs/.profile(사용자 브라우저와 섞이지 않게) → 임시 파일에 찍고 os.replace
- 낡음 = 그림이 없거나 max(.hd-canvas.json, index.html 의 mtime) 보다 오래됨 — 규칙은 home_model.thumb_stale
- Thumbs: 일꾼 스레드 하나, 한 번에 하나, 같은 이름은 한 번만 줄 선다. 요청을 막지 않는다. 실패는 [hd] 한 줄(다음 예약 때 다시)
"""
import os, pathlib, shutil, subprocess, sys, threading

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hd"))
import home_model as M  # noqa: E402

SIZE = (1260, 780)
BUDGET_MS = 6000
TIMEOUT = 60
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def warn(msg):
    print("[hd] " + msg, file=sys.stderr, flush=True)


def find_browser():
    """Edge → Chrome 실행 파일 경로 | None."""
    local = os.environ.get("LOCALAPPDATA")
    extra = [os.path.join(local, "Google", "Chrome", "Application", "chrome.exe")] if local else []
    for p in list(CANDIDATES) + extra:
        if os.path.isfile(p):
            return p
    for n in ("msedge", "google-chrome", "chromium", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    return None


def render(browser, index_html, png, profile):
    """index.html → png(덮어씀). 실패하면 RuntimeError(한 줄)."""
    png = pathlib.Path(png)
    png.parent.mkdir(parents=True, exist_ok=True)
    tmp = png.with_name(png.stem + ".tmp.png")
    tmp.unlink(missing_ok=True)
    args = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
            "--user-data-dir=%s" % profile, "--screenshot=%s" % tmp, "--window-size=%d,%d" % SIZE,
            "--virtual-time-budget=%d" % BUDGET_MS, pathlib.Path(index_html).resolve().as_uri()]
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise RuntimeError("%d초 안에 끝나지 않았어요" % TIMEOUT)
    if not tmp.is_file() or tmp.stat().st_size == 0:
        raise RuntimeError("그림이 나오지 않았어요(종료 %s): %s" % (r.returncode, " / ".join(((r.stderr or "").strip().splitlines())[-2:])))
    os.replace(tmp, png)


def _mtime(p):
    try:
        return pathlib.Path(p).stat().st_mtime
    except OSError:
        return None


def stale(row, thumbs_dir):
    """줄 객체(name, out, state) → 다시 찍어야 하나. out 이 없거나(missing) index.html 이 없으면 아니다."""
    if row.get("state") == "missing":
        return False
    out = pathlib.Path(row["out"])
    if not (out / "index.html").is_file():
        return False
    return M.thumb_stale(_mtime(pathlib.Path(thumbs_dir) / ("%s.png" % row["name"])), [_mtime(out / ".hd-canvas.json"), _mtime(out / "index.html")])


class Thumbs:
    """낡은 썸네일을 뒤에서 하나씩 찍는다. renderer(index_html, png) — 테스트가 바꿔 끼운다(기본: 헤드리스 브라우저)."""

    def __init__(self, thumbs_dir, renderer=None):
        self.dir = pathlib.Path(thumbs_dir)
        self.renderer = renderer
        self.lock = threading.Lock()
        self.queue, self.waiting = [], set()
        self.worker = None
        self.done = threading.Event()                      # 줄이 빌 때마다 켜짐(테스트가 기다린다)
        self.done.set()
        self.no_browser_warned = False

    def _default_renderer(self):
        b = find_browser()
        if b is None:
            if not self.no_browser_warned:
                warn("Edge·Chrome 을 찾지 못해 썸네일을 만들지 않아요")
                self.no_browser_warned = True
            return None
        return lambda index_html, png: render(b, index_html, png, self.dir / ".profile")

    def schedule(self, rows):
        """낡은 것을 줄 세운다(이미 줄에 있는 이름은 건너뜀) → 새로 줄 세운 이름들."""
        added = []
        for r in rows:
            if stale(r, self.dir):
                with self.lock:
                    if r["name"] in self.waiting:
                        continue
                    self.waiting.add(r["name"]); self.queue.append((r["name"], r["out"])); added.append(r["name"])
        if added:
            with self.lock:
                self.done.clear()
                if self.worker is None or not self.worker.is_alive():
                    self.worker = threading.Thread(target=self._run, daemon=True)
                    self.worker.start()
        return added

    def _run(self):
        render_fn = self.renderer or self._default_renderer()
        while True:
            with self.lock:
                if not self.queue:
                    self.worker = None
                    self.done.set()
                    return
                name, out = self.queue.pop(0)
            try:
                if render_fn is not None:
                    render_fn(pathlib.Path(out) / "index.html", self.dir / ("%s.png" % name))
            except Exception as e:                         # 그림 하나가 실패해도 일꾼은 계속 — 한 줄 남기고 다음 예약 때 다시
                warn("썸네일을 만들지 못했어요(%s): %s" % (name, e))
            finally:
                with self.lock:
                    self.waiting.discard(name)
