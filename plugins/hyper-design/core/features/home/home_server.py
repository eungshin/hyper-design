"""Server — 허브 `hd home`: HD_HOME 하나에 작은 HTTP 서버 하나(127.0.0.1:12270, 막혔으면 빈 포트). Home 화면과 프로젝트 API 를 낸다.

- `/`(·`/index.html`) = home.html(<head> 에 window.__hdToken · __hdHub 를 끼움) · 같은 폴더의 *.html|css|js|svg|png = 그대로(토큰 없음)
- `/thumb/<name>.png` = <HD_HOME>/thumbs/<name>.png(토큰 없음, 알려진 이름만) · `/api/*` = home_api.route(X-HD-Token · Host 검사)
- 기록 <HD_HOME>/home.json {url, pid, port, token} — 살아 있고 답하면 다시 쓰고(브라우저만 엶), 죽었으면 덮어씀. 정상 종료 때 지움
- 주소 = http://127.0.0.1:<port>/?hd=<token>
"""
import atexit, json, os, pathlib, secrets, signal, sys, threading, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hd"))
import hd_client as C  # noqa: E402
import home_api as A  # noqa: E402
import home_client as H  # noqa: E402
import home_model as M  # noqa: E402
import thumb as T  # noqa: E402

PORT = 12270


def default_port():
    """기본 포트 = env HD_HUB_PORT(테스트가 0 = 빈 포트로) | 12270."""
    v = os.environ.get("HD_HUB_PORT")
    return int(v) if v and v.isdigit() else PORT
PAGE = HERE / "home.html"
STATIC = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml", ".png": "image/png"}
BODY_MAX = 1 << 20


def warn(msg):
    print("[hd] " + msg, file=sys.stderr, flush=True)


class Hub(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"     # Windows 의 SO_REUSEADDR 는 쓰는 중인 포트도 연다 — 막혔는지 알아야 한다
    daemon_threads = True


def bind(handler, port):
    """port 를 열고, 막혔으면(0 이 아닐 때) [hd] 한 줄 뒤 빈 포트로."""
    try:
        return Hub(("127.0.0.1", port), handler)
    except OSError as e:
        if not port:
            raise
        warn("포트 %d 를 쓸 수 없어 빈 포트로 띄워요(%s)" % (port, e))
        return Hub(("127.0.0.1", 0), handler)


def make_hub(port=PORT, renderer=None, picker=None, token=None, page=None):
    """허브 서버(아직 돌지 않음) → srv(srv.url · srv.token · srv.thumbs). renderer·picker·page 는 테스트가 바꿔 끼운다."""
    token = token or secrets.token_urlsafe(18)
    page = pathlib.Path(page or PAGE)
    thumbs = T.Thumbs(H.home() / "thumbs", renderer)
    ctx = A.Ctx(hub=True, port=lambda: srv.server_address[1], after_rows=thumbs.schedule, picker=picker or H.pick_folder)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _host_ok(self):
            p = self.server.server_address[1]
            return (self.headers.get("Host") or "") in ("127.0.0.1:%d" % p, "localhost:%d" % p)

        def _send(self, code, body, ctype, cache="no-store"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _api(self, method, path, body):
            res = A.route(method, path, body, ctx)      # 예상 못 한 실패는 route 가 500 한 줄로
            if res is None:
                return self._json(404, {"error": "모르는 주소"})
            return self._json(*res)

        def _page(self):
            if not page.is_file():
                return self._send(500, ("<!doctype html><meta charset=utf-8><p>홈 화면 파일이 없어요: %s" % page).encode("utf-8"),
                                  "text/html; charset=utf-8")
            inject = "<script>window.__hdHub=true;window.__hdToken=%s;</script>" % json.dumps(token)
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
            if u.path in ("/", "/index.html", "/home.html"):
                return self._page()
            if u.path.startswith("/thumb/"):
                return self._thumb(u.path[len("/thumb/"):])
            if u.path.startswith("/api/"):
                if self.headers.get("X-HD-Token") != token:
                    return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
                return self._api("GET", u.path, None)
            name = u.path.lstrip("/")
            f = HERE / name
            if "/" not in name and "\\" not in name and not name.startswith(".") and f.suffix in STATIC and f.is_file():
                ctype = STATIC[f.suffix] + ("; charset=utf-8" if f.suffix in (".html", ".css", ".js", ".svg") else "")
                return self._send(200, f.read_bytes(), ctype)
            return self._json(404, {"error": "없는 파일"})

        def _body_call(self, method):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            raw = self.rfile.read(min(n, BODY_MAX)) if n else b""   # 거절하기 전에 먼저 읽는다(안 읽고 닫으면 Windows 가 RST)
            if n > BODY_MAX:
                return self._json(413, {"error": "본문이 너무 커요"})
            if not self._host_ok() or self.headers.get("X-HD-Token") != token:
                return self._json(403, {"error": "토큰 또는 주소가 맞지 않아요"})
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                return self._json(400, {"error": "JSON 이 아니에요"})
            return self._api(method, urllib.parse.urlparse(self.path).path, body)

        def do_POST(self):
            return self._body_call("POST")

        def do_PUT(self):
            return self._body_call("PUT")

    srv = bind(Handler, port)
    srv.token, srv.thumbs = token, thumbs
    srv.url = "http://127.0.0.1:%d/?hd=%s" % (srv.server_address[1], token)
    return srv


def _stop(signum, frame):                              # SIGTERM·SIGBREAK → Ctrl+C 와 같은 정상 종료(기록 지움)
    raise KeyboardInterrupt


def serve(port=None, no_browser=False, on_url=None):
    """hd home 본체 → {url, reused}. 살아 있는 허브가 있으면 그 주소(브라우저만), 아니면 여기서 띄워 끝날 때까지 돈다."""
    rec = H.live_hub()
    if rec:
        if not no_browser:
            webbrowser.open(rec["url"])
        return {"url": rec["url"], "pid": rec["pid"], "reused": True}
    srv = make_hub(default_port() if port is None else port)
    H.write_hub(srv.url, srv.server_address[1], srv.token)
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
        srv.server_close()
        H.clear_hub()
    return {"url": srv.url, "pid": os.getpid(), "reused": False}
