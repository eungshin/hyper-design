"""Controller — 주소 → 담당 세션 메서드(task 47-2). 토큰·Host·크기 검사와 오류 모양은 SessionHandler 한 곳.

Router.call(method, path, query, body, session) → (code, 답[, after]) | None(모르는 주소). after = 답을 보낸 뒤 부를 것(/api/stop).
세션 주소(ROUTES)는 ProjectSession 의 부품으로, 서버 주소(/api/stop · home_api 의 프로젝트·탭·홈)는 서버가 넘긴 것으로 간다.
SessionHandler = 세션 하나를 내는 HTTP 처리기(helper.py 가 out 하나로, 허브가 /v1/p/<이름>/ 아래로 같은 것을 쓴다).
"""
import json, pathlib, sys, urllib.parse
from http.server import SimpleHTTPRequestHandler

import session as S

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "home"))
import home_api  # noqa: E402  — 프로젝트·탭·홈 라우트는 허브(hd home)와 같은 모듈 하나(같은 JSON)

FORBIDDEN = "토큰 또는 주소가 맞지 않아요"


def _since_files(q):
    try:
        return int(q.get("since", ["-1"])[0])
    except ValueError:
        return None


def get_state(s, q, body):
    try:
        since = S.helper_model.parse_since(q.get("since", [None])[0])
    except ValueError as e:
        return 400, {"error": str(e)}
    return 200, s.store.get(since)


def get_files(s, q, body):
    since = _since_files(q)
    if since is None:
        return 400, {"error": "since: 정수가 아니에요"}
    return 200, s.busy.files(since)


ROUTES = {
    "GET": {
        "/api/state": get_state,
        "/api/files": get_files,
        "/api/agents": lambda s, q, b: (200, s.queue.agents(auto=q.get("auto", [""])[0] == "1")),
        "/api/archive": lambda s, q, b: (200, s.archive.get()),
        "/api/parts": lambda s, q, b: (200, s.builder.parts()),
    },
    "POST": {
        "/api/data": lambda s, q, b: (200, s.builder.data()),
        "/api/apply": lambda s, q, b: s.history.apply(b.get("edits") or []),
        "/api/delete": lambda s, q, b: s.history.delete([str(i) for i in b.get("screens") or []]),
        "/api/restore": lambda s, q, b: s.history.restore(str(b.get("stamp") or "")),
        "/api/reply": lambda s, q, b: s.queue.reply(b),
        "/api/claim": lambda s, q, b: s.busy.claim(b),
        "/api/release": lambda s, q, b: s.busy.release(b),
        "/api/archive": lambda s, q, b: s.archive.post(b),
        "/api/forward": lambda s, q, b: (200, s.queue.forward(str(b.get("text") or ""))),
        "/api/attach": lambda s, q, b: s.queue.attach(b),
        "/api/watch": lambda s, q, b: (200, s.busy.mtimes(b.get("files") if isinstance(b, dict) else None)),
    },
    "PUT": {
        "/api/state": lambda s, q, b: s.store.put(b),
    },
}


class Router:
    """세션 주소 표(ROUTES) + 서버 주소(on_stop · home_ctx) → 담당. home_ctx 가 없으면 프로젝트·탭 주소는 모르는 주소."""

    def __init__(self, home_ctx=None, on_stop=None):
        self.home_ctx, self.on_stop = home_ctx, on_stop

    def knows(self, method, path):
        return path in ROUTES.get(method, {}) or (self.home_ctx is not None and method == "GET" and path in home_api.GET_PATHS)

    def call(self, method, path, query, body, session):
        fn = ROUTES.get(method, {}).get(path)
        if fn is not None:
            return fn(session, query or {}, body)
        if method == "POST" and path == "/api/stop" and self.on_stop:
            return 200, {"stopping": True}, self.on_stop
        if self.home_ctx is not None:
            return home_api.route(method, path, body, self.home_ctx)   # /api/projects · open · new · project · forget · reveal · tabs · home
        return None


class SessionHandler(SimpleHTTPRequestHandler):
    """세션 하나를 내는 처리기. 하위 클래스가 router 와 target()(→ 세션, 그 세션 안 경로 | None)을 정한다.
    정적 파일(/·/index.html = 세션 페이지, 그 밖 out 파일)은 토큰 없이, 점 경로는 404."""
    router = None

    def target(self, path):                          # → (session, rest) | None
        raise NotImplementedError

    def log_message(self, *a):
        pass

    def _host_ok(self):
        port_ = self.server.server_address[1]
        return (self.headers.get("Host") or "") in ("127.0.0.1:%d" % port_, "localhost:%d" % port_)

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _reply(self, res):
        if res is None:
            return self._json(404, {"error": "모르는 주소"})
        self._json(res[0], res[1])
        if len(res) > 2 and res[2]:
            res[2]()
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _page(self, sess):
        b = sess.page()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if not self._host_ok():
            return self.send_error(403)
        u = urllib.parse.urlparse(self.path)
        sess, rest = self.target(u.path)
        if self.router.knows("GET", rest):
            if self.headers.get("X-HD-Token") != sess.token:
                return self._json(403, {"error": FORBIDDEN})
            return self._reply(self.router.call("GET", rest, urllib.parse.parse_qs(u.query), None, sess))
        parts = [p for p in rest.split("/") if p]
        if any(p.startswith(".") for p in parts):        # 원본 기록·대기열·상태 파일은 내주지 않는다
            return self.send_error(404)
        if rest in ("/", "/index.html"):
            return self._page(sess)
        return super().do_GET()

    def _read(self):
        try:                                            # 본문은 거절하기 전에도 먼저 다 읽는다 — 안 읽은 채 닫으면 Windows 가 RST 로 끊어
            return self.rfile.read(int(self.headers.get("Content-Length") or 0))   # 상대가 403 대신 ConnectionAbortedError 를 받는다
        except ValueError:
            return b""

    def do_POST(self):
        raw = self._read()
        sess, rest = self.target(self.path)
        if not self._host_ok() or self.headers.get("X-HD-Token") != sess.token:
            return self._json(403, {"error": FORBIDDEN})
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            return self._json(400, {"error": "JSON 이 아니에요"})
        return self._reply(self.router.call("POST", rest, None, body, sess))

    def do_PUT(self):                                   # /api/state · /api/tabs — 한도를 넘어도 본문은 다 읽고 답한다(위 do_POST 와 같은 이유)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n > S.STATE_MAX:
            while n > 0:
                chunk = self.rfile.read(min(n, 65536))
                if not chunk:
                    break
                n -= len(chunk)
            return self._json(413, {"error": S.helper_model.too_big(int(self.headers.get("Content-Length") or 0), S.STATE_MAX)})
        raw = self.rfile.read(n)
        sess, rest = self.target(self.path)
        if not self._host_ok() or self.headers.get("X-HD-Token") != sess.token:
            return self._json(403, {"error": FORBIDDEN})
        if rest not in ("/api/state", "/api/tabs"):
            return self._json(404, {"error": "모르는 주소"})
        try:
            body = json.loads(raw or b"null")
        except ValueError:
            return self._json(400, {"error": "JSON 이 아니에요"})
        return self._reply(self.router.call("PUT", rest, None, body, sess))
