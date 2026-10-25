"""Server — 허브 `hd home`: HD_HOME 하나에 HTTP 서버 하나(127.0.0.1:12270, 막혔으면 빈 포트). Home 화면·프로젝트 API · 그리고(task 47-2 '서버 하나')
프로젝트마다 이 프로세스 안 ProjectSession(registry.py) — 도우미(helper.py)를 따로 띄우지 않는다.

- `/`(·`/index.html`) = home.html(<head> 에 window.__hdToken · __hdHub 를 끼움) · 같은 폴더의 *.html|css|js|svg|png = 그대로(토큰 없음)
- `/thumb/<name>.png` = <HD_HOME>/thumbs/<name>.png(토큰 없음, 알려진 이름만) · `/api/*` + 허브 토큰 = home_api.route(X-HD-Token · Host 검사)
- `/v1/p/<이름>/` = 그 프로젝트 캔버스 페이지 · out 파일 · `/v1/p/<이름>/api/*`(세션 토큰 또는 허브 토큰 — 도우미와 같은 라우트, canvas/router.py)
- `/api/*` + 세션 토큰 = 그 세션(옛 주소 별칭 — 캔버스 JS 는 그대로 '/api/…' 에 페이지 주소의 ?hd= 토큰을 보낸다)
- 이벤트 흐름(47-4a) `/v1/p/<이름>/events` · 옛 뿌리 `/api/events` — 토큰은 머리글 또는 `?hd=`(EventSource), 처리는 canvas/router.py SessionHandler._events
- `GET /v1/sessions`(허브 토큰) = 열린 세션 표지들 {sessions:[…]}(hd_client.hub_markers — hd ls·notes·reply·claim 이 허브를 거쳐 찾는다)
- 본문 차례(POST·PUT): Host + 토큰(403) → 크기(413) → 아는 주소(404) → JSON(400) → 담당
- 기록 <HD_HOME>/home.json {url, pid, port, token, code} — 살아 있고 답하면 다시 쓰고(브라우저만 엶), 죽었으면 덮어씀. 정상 종료 때 지움(세션도 모두 닫음)
- 코드 도장(canvas/code_stamp.py): 허브가 옛 코드로 떠 있으면 홈 화면에 window.__hdStale(띠 '새 버전이 있어요' + [다시 켜기]) · hd home 이 한 줄.
  스스로 끄지 않는다. POST /api/hub/stop(허브 토큰) = 정상 종료 · POST /api/hub/restart = `hd home --restart --port <지금 포트>` 를 떼어 띄움
  (그것이 이 허브를 /api/hub/stop 으로 끄고 같은 포트로 뜬다 — 옛 허브라 그 주소가 없으면 python pid 만 강제 종료)
- 주소 = http://127.0.0.1:<port>/?hd=<token>
"""
import atexit, json, os, pathlib, re, secrets, signal, subprocess, sys, threading, time, urllib.parse, webbrowser
from http.server import ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hd"))
import hd_client as C  # noqa: E402
import home_api as A  # noqa: E402
import home_client as H  # noqa: E402
import home_model as M  # noqa: E402
import thumb as T  # noqa: E402
import registry as RG  # noqa: E402  — 프로젝트 세션들(task 47-2) — canvas 폴더를 path 에 넣는다
import safe_port  # noqa: E402  — canvas 폴더(registry 가 path 에 넣음)
import router as R  # noqa: E402  — 세션 주소 처리(canvas/router.py)
import code_stamp as CS  # noqa: E402  — 코드 도장(순수 Model, canvas — registry 가 path 에 넣음)

PORT = 12270


def default_port():
    """기본 포트 = env HD_HUB_PORT(테스트가 0 = 빈 포트로) | 12270."""
    v = os.environ.get("HD_HUB_PORT")
    return int(v) if v and v.isdigit() else PORT
PAGE = HERE / "home.html"
STATIC = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml", ".png": "image/png"}
BODY_MAX = 1 << 20
V1 = re.compile(r"^/v1/p/([^/]+)(/.*)?$")


def warn(msg):
    print("[hd] " + msg, file=sys.stderr, flush=True)


class Hub(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"     # Windows 의 SO_REUSEADDR 는 쓰는 중인 포트도 연다 — 막혔는지 알아야 한다
    daemon_threads = True

    def server_close(self):
        reg = getattr(self, "registry", None)
        if reg is not None:                            # 세션마다 지켜보기·별칭 포트를 닫고 .hd-helper.json 을 되돌린다
            reg.close_all()
            if C.LOCAL == reg.markers:
                C.LOCAL = None
        super().server_close()


def bind(handler, port):
    """port 를 열고, 막혔으면(0 이 아닐 때) [hd] 한 줄 뒤 빈 포트로."""
    try:
        return safe_port.open_server(Hub, "127.0.0.1", port, handler)
    except OSError as e:
        if not port:
            raise
        warn("포트 %d 를 쓸 수 없어 빈 포트로 띄워요(%s)" % (port, e))
        return safe_port.open_server(Hub, "127.0.0.1", 0, handler)


HD_PY = HERE.parent / "hd" / "hd.py"
STOP_WAIT = 10.0


def spawn_restart(port):
    """`hd home --restart --no-browser --port <port>` 를 떼어 띄운다(이 허브를 끄고 같은 포트로 새 코드 허브) — 출력은 <HD_HOME>/hub-restart.log."""
    log = H.home() / "hub-restart.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        kw = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    else:
        kw = {"creationflags": 0, "start_new_session": True}
    with open(log, "ab") as f:
        subprocess.Popen([sys.executable, str(HD_PY), "home", "--restart", "--no-browser", "--port", str(int(port))], stdin=subprocess.DEVNULL,
                         stdout=f, stderr=subprocess.STDOUT, close_fds=True, env=dict(os.environ, PYTHONIOENCODING="utf-8"), **kw)


def stop_hub(rec, wait=STOP_WAIT):
    """떠 있는 허브 끄기 → 'route'(POST /api/hub/stop 으로 스스로 끔) | 'kill'(그 주소가 없는 옛 허브 · 답 없음 — python pid 강제 종료) | 'gone' | 'other'."""
    try:
        code, _ = C.call({"port": rec["port"], "token": rec["token"]}, "/api/hub/stop", {}, timeout=3)
    except C.HdError:
        code = None
    end = time.time() + wait
    while code == 200 and time.time() < end:
        if not C.pid_alive(rec["pid"]):
            return "route"
        time.sleep(0.1)
    how = C.kill_pid(int(rec["pid"]))
    while how == "kill" and time.time() < end + wait and C.pid_alive(rec["pid"]):
        time.sleep(0.1)
    return how


def make_hub(port=PORT, renderer=None, picker=None, token=None, page=None, build=None, paseo=None, restarter=None):
    """허브 서버(아직 돌지 않음) → srv(srv.url · srv.token · srv.thumbs · srv.registry). renderer·picker·page·build·restarter 는 테스트가 바꿔 끼운다."""
    token = token or secrets.token_urlsafe(18)
    page = pathlib.Path(page or PAGE)
    thumbs = T.Thumbs(H.home() / "thumbs", renderer)
    picker = picker or H.pick_folder
    hub_port = lambda: srv.server_address[1]
    reg = RG.ProjectRegistry(hub_port, lambda: srv.url, picker=picker, paseo=paseo or os.environ.get("HD_PASEO_CMD"), build=build)
    ctx = A.Ctx(hub=True, port=hub_port, after_rows=thumbs.schedule, picker=picker, opener=reg.open, closer=reg.close)

    class Handler(R.SessionHandler):
        _sess, _cache = None, None

        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(HERE), **k)

        # ---------------------------------------------------- 세션으로 넘기기
        def target(self, path):
            return self._sess, path

        def _token_ok(self, sess):
            return self._given_token() in (sess.token, token)

        def _which(self, path, query=""):
            """→ ('v1', 세션|None, 그 안 경로, 이름) | ('alias', 세션, 경로) | ('hub',)."""
            m = V1.match(path)
            if m:
                name = urllib.parse.unquote(m.group(1))
                return ("v1", reg.get(name), m.group(2) or "", name)
            if path.startswith("/api/"):
                tok = self.headers.get("X-HD-Token")
                if not tok and path in R.EVENT_PATHS:      # EventSource 는 머리글을 못 보낸다 — 세션 토큰은 ?hd= 로
                    tok = urllib.parse.parse_qs(query).get("hd", [None])[0]
                sess = reg.by_token(tok) if tok and tok != token else None
                if sess is not None:
                    return ("alias", sess, path)
            return ("hub",)

        def _enter(self, sess, rest, query):            # 경로·폴더·라우터를 그 세션 것으로
            self._sess, self.router, self.directory = sess, sess.router, str(sess.out)
            self.path = rest + ("?" + query if query else "")

        def _missing(self, name):
            return self._json(404, {"error": "열려 있지 않은 프로젝트예요: %s — 홈에서 다시 여세요" % name})

        # ---------------------------------------------------- 홈
        def end_headers(self):
            self.send_header("Cache-Control", self._cache or "no-store")
            self._cache = None
            R.SimpleHTTPRequestHandler.end_headers(self)

        def _send(self, code, body, ctype, cache=None):
            self._cache = cache
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _api(self, method, path, body):
            res = A.route(method, path, body, ctx)      # 예상 못 한 실패는 route 가 500 한 줄로
            if res is None:
                return self._json(404, {"error": "모르는 주소"})
            return self._json(*res)

        def _home_page(self):
            if not page.is_file():
                return self._send(500, ("<!doctype html><meta charset=utf-8><p>홈 화면 파일이 없어요: %s" % page).encode("utf-8"),
                                  "text/html; charset=utf-8")
            inject = "<script>window.__hdHub=true;window.__hdToken=%s;%s</script>" % (
                json.dumps(token), "window.__hdStale=true;window.__hdStaleText=%s;" % json.dumps(CS.HUB_NOTICE) if reg.stale() else "")
            html = page.read_text(encoding="utf-8")
            html = html.replace("<head>", "<head>" + inject, 1) if "<head>" in html else inject + html
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

        def _thumb(self, tail):
            known = {e["name"] for e in C.load_projects()["projects"]}
            name = M.thumb_name(urllib.parse.unquote(tail), known)
            p = A.thumb_path(name) if name else None
            if p is None or not p.is_file():
                return self._json(404, {"error": "썸네일이 없어요"})
            self._send(200, p.read_bytes(), "image/png", cache="max-age=31536000")   # 주소의 ?t= 가 바뀌면 새로 받는다

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"error": "주소가 맞지 않아요"})
            u = urllib.parse.urlparse(self.path)
            w = self._which(u.path, u.query)
            if w[0] == "v1" and w[1] is None:
                return self._missing(w[3])
            if w[0] == "v1" and w[2] == "":                # /v1/p/<이름> → /v1/p/<이름>/ (화면 파일 상대 주소가 그 아래로)
                self.send_response(301)
                self.send_header("Location", u.path + "/" + ("?" + u.query if u.query else ""))
                self.send_header("Content-Length", "0")
                return self.end_headers()
            if w[0] in ("v1", "alias"):
                self._enter(w[1], w[2], u.query)
                return R.SessionHandler.do_GET(self)
            if u.path in ("/", "/index.html", "/home.html"):
                return self._home_page()
            if u.path.startswith("/thumb/"):
                return self._thumb(u.path[len("/thumb/"):])
            if u.path == "/v1/sessions" or u.path.startswith("/api/"):
                if self.headers.get("X-HD-Token") != token:
                    return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
                if u.path == "/v1/sessions":
                    return self._json(200, {"sessions": reg.markers()})
                return self._api("GET", u.path, None)
            name = u.path.lstrip("/")
            f = HERE / name
            if "/" not in name and "\\" not in name and not name.startswith(".") and f.suffix in STATIC and f.is_file():
                ctype = STATIC[f.suffix] + ("; charset=utf-8" if f.suffix in (".html", ".css", ".js", ".svg") else "")
                return self._send(200, f.read_bytes(), ctype)
            return self._json(404, {"error": "없는 파일"})

        def _length(self):
            try:
                return max(0, int(self.headers.get("Content-Length") or 0))
            except ValueError:
                return 0

        def _hub_body(self, method):
            n = self._length()
            if not self._host_ok() or self.headers.get("X-HD-Token") != token:
                self._drain(n)
                return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
            if n > BODY_MAX:
                self._drain(n)
                return self._json(413, {"error": "본문이 너무 커요"})
            raw = self.rfile.read(n) if n else b""
            path = urllib.parse.urlparse(self.path).path
            if method == "POST" and path == "/api/hub/stop":     # 정상 종료(hd home --restart 가 부름) — 답한 뒤 serve_forever 를 멈춘다
                self._json(200, {"stopping": True})
                threading.Thread(target=srv.shutdown, daemon=True).start()
                return None
            if method == "POST" and path == "/api/hub/restart":  # 홈 화면 [다시 켜기] — 새 허브가 이 허브를 끄고 같은 포트로
                try:
                    (restarter or spawn_restart)(srv.server_address[1])
                except OSError as e:
                    return self._json(500, {"error": "허브를 다시 켜지 못했어요: %s" % e})
                return self._json(200, {"restarting": True})
            if path not in {"POST": A.POST_PATHS, "PUT": A.PUT_PATHS}[method]:
                return self._json(404, {"error": "모르는 주소"})
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return self._json(400, {"error": "JSON 이 아니에요"})
            return self._api(method, path, body)

        def _body(self, method):
            u = urllib.parse.urlparse(self.path)
            w = self._which(u.path)
            if w[0] == "v1" and w[1] is None:
                self._drain(self._length())
                return self._missing(w[3])
            if w[0] in ("v1", "alias"):
                self._enter(w[1], w[2], u.query)
                return self._body_call(method)
            return self._hub_body(method)

        def do_HEAD(self):                              # 예전 허브(BaseHTTPRequestHandler)처럼 HEAD 는 없다 — 홈 폴더의 .py 를 내주지 않게
            return self.send_error(501)

        def do_POST(self):
            return self._body("POST")

        def do_PUT(self):
            return self._body("PUT")

    srv = bind(Handler, port)
    srv.token, srv.thumbs, srv.registry = token, thumbs, reg
    srv.url = "http://127.0.0.1:%d/?hd=%s" % (srv.server_address[1], token)
    C.LOCAL = reg.markers                              # 이 프로세스의 hd_client 는 자기 세션을 HTTP 없이 본다
    return srv


def _stop(signum, frame):                              # SIGTERM·SIGBREAK → Ctrl+C 와 같은 정상 종료(기록 지움)
    raise KeyboardInterrupt


def serve(port=None, no_browser=False, on_url=None, restart=False):
    """hd home 본체 → {url, reused, stale?}. 살아 있는 허브가 있으면 그 주소(브라우저만 — 옛 코드면 stale), 아니면 여기서 띄워 끝날 때까지 돈다.
    restart = 살아 있는 허브를 먼저 끄고(stop_hub) 같은 포트로 띄운다."""
    rec = H.live_hub()
    if rec and restart:
        how = stop_hub(rec)
        warn("떠 있던 허브(pid %s)를 껐어요(%s) — 지금 코드로 다시 띄워요" % (rec["pid"], how))
        port = rec["port"] if port is None else port
        rec = None
    if rec:
        if not no_browser:
            webbrowser.open(rec["url"])
        res = {"url": rec["url"], "pid": rec["pid"], "reused": True}
        if CS.stale(rec.get("code"), C.code_stamp()):
            res["stale"] = True
        return res
    srv = make_hub(default_port() if port is None else port)
    H.write_hub(srv.url, srv.server_address[1], srv.token, srv.registry.code)
    atexit.register(H.clear_hub)
    for name in ("SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    if on_url:
        on_url(srv.url)
    if not no_browser:
        threading.Timer(0.3, lambda: webbrowser.open(srv.url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()                             # 세션도 모두 닫는다(Hub.server_close)
        H.clear_hub()
    return {"url": srv.url, "pid": os.getpid(), "reused": False}
