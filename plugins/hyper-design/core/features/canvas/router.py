"""Controller — 주소 → 담당 세션 메서드(task 47-2). 토큰·Host·크기 검사와 오류 모양은 SessionHandler 한 곳.

Router.call(method, path, query, body, session) → (code, 답[, after]) | None(모르는 주소). after = 답을 보낸 뒤 부를 것(/api/stop).
세션 주소(ROUTES)는 ProjectSession 의 부품으로, 서버 주소(/api/stop · home_api 의 프로젝트·탭·홈)는 서버가 넘긴 것으로 간다.
SessionHandler = 세션 하나를 내는 HTTP 처리기(helper.py 가 out 하나로, 허브가 /v1/p/<이름>/ 아래로 같은 것을 쓴다).
이벤트 흐름(task 47-4a) GET /events · /api/events = 세션 EventBus 를 SSE 로(_events) — 계약 tests/protocol/events.json.
접속·보내기(task 47-5a) /hello · /beat · /bye · /progress · GET /agents · /agents/spawn(+ 옛 뿌리 /api/… 별칭, GET /api/presence) = 세션 AgentPresence ·
/api/forward {text, to?, notes?} = Queue.send(이벤트 또는 어댑터) — 계약 tests/protocol/presence.json.
허브 옛 코드(R34): 허브 안 세션(session.hub_stale 이 있음)이면 GET /api/state 답에 hubStale {sha, since} | null 을 싣는다(도우미는 싣지 않음 = 모름) ·
POST /api/hub/restart = 서버가 넘긴 on_restart(허브의 [다시 켜기] — 없으면 모르는 주소).
"""
import json, pathlib, select, socket, sys, time, urllib.parse
from http.server import SimpleHTTPRequestHandler

import attach_rules as AR  # 첨부 이미지 본문 한도(R22)
import chat_log as CL
import events as EV
from state_store import STATE_MAX  # out_io 가 hd 폴더를 sys.path 에 넣는다

import helper_model  # noqa: E402  — since 풀기 · 413 글

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "home"))
import home_api  # noqa: E402  — 프로젝트·탭·홈 라우트는 허브(hd home)와 같은 모듈 하나(같은 JSON)

FORBIDDEN = "토큰 또는 주소가 맞지 않아요"
EVENT_PATHS = ("/events", "/api/events")             # /v1/p/<이름>/events · 옛 뿌리 /api/events(세션 토큰) · 도우미 /api/events
V1_GET = ("/agents",)                                # /api 밖 JSON GET 주소(/v1/p/<이름>/agents) — 토큰을 보고 라우터로
HEARTBEAT = 15.0                                     # 이만큼 조용하면 ': hb' 주석(프록시·SDK 가 끊긴 줄 알지 않게)
POLL = 1.0                                           # 이만큼마다 손님이 닫았는지 본다(닫힌 흐름의 스레드가 남지 않게)


def _since_files(q):
    try:
        return int(q.get("since", ["-1"])[0])
    except ValueError:
        return None


def get_state(s, q, body):
    try:
        since = helper_model.parse_since(q.get("since", [None])[0])
    except ValueError as e:
        return 400, {"error": str(e)}
    res = s.store.get(since)
    hub = getattr(s, "hub_stale", None)               # R34 — 허브 안 세션만(2초 읽기에 실어 프로젝트 화면이 '허브 옛 코드' 칩을 띄운다)
    return 200, (dict(res, hubStale=hub()) if hub else res)


def get_ai_writes(s, q, body):
    since = _since_files(q)
    if since is None:
        return 400, {"error": "since: 정수가 아니에요"}
    with s.lock:
        return 200, s.ai.since(since)


def get_files(s, q, body):
    since = _since_files(q)
    if since is None:
        return 400, {"error": "since: 정수가 아니에요"}
    return 200, s.busy.files(since)


def get_chat(s, q, body):                             # S3 대화 기록 — since 뒤 기록(없으면 다)
    try:
        since = CL.parse_since(q.get("since", [None])[0])
    except ValueError as e:
        return 400, {"error": str(e)}
    return 200, s.chat.get(since)


def _obj(fn):                                        # 본문이 JSON 객체여야 하는 주소 — 목록·글이면 400(47-2 2a: 전에는 body.get 에서 연결이 끊겼다)
    def call(s, q, b):
        if not isinstance(b, dict):
            return 400, {"error": "JSON 객체가 아니에요({…} 모양으로 보내 주세요)"}
        return fn(s, q, b)
    return call


ROUTES = {
    "GET": {
        "/api/state": get_state,
        "/api/files": get_files,
        "/api/ai-writes": get_ai_writes,
        "/api/agents": lambda s, q, b: (200, s.queue.agents(auto=q.get("auto", [""])[0] == "1")),
        "/api/archive": lambda s, q, b: (200, s.archive.get()),
        "/api/parts": lambda s, q, b: (200, s.builder.parts()),
        "/api/app-parts": lambda s, q, b: (200, s.parts.status()),     # R30 앱 부품(out/parts.json) 낡음 — {parts, stale:[화면 id]}
        "/agents": lambda s, q, b: (200, s.presence.list()),            # 47-5a 접속한 에이전트(/v1/p/<이름>/agents)
        "/api/presence": lambda s, q, b: (200, s.presence.list()),      # 옛 뿌리 별칭(/api/agents 는 Paseo 목록 + connected)
        "/api/chat": get_chat,                                          # S3 대화 기록(.hd-chat.jsonl)
        "/api/agents/transcript": lambda s, q, b: s.transcripts.http_get(q),   # S3b 터미널 대화(고른 에이전트만, 그 뒤 새 줄은 이벤트)
        "/agents/transcript": lambda s, q, b: s.transcripts.http_get(q),
        "/api/agents/info": lambda s, q, b: s.agent_info.get(q),       # R28 붙은 Paseo 터미널의 모델·생각 깊이·컨텍스트(없으면 {agent:null})
        "/api/image": lambda s, q, b: s.images.read(q),                 # R22 첨부 이미지 읽기(?rel=.hd-attach/<이름>) → {type, data(base64)}
    },
    "POST": {
        "/api/data": lambda s, q, b: (200, s.builder.data()),
        "/api/apply": _obj(lambda s, q, b: s.history.apply_async(b.get("edits") or []) if b.get("async") is True   # 47-4a 고르기: 정확히 true 일 때만
                           else s.history.apply(b.get("edits") or [])),
        "/api/delete": _obj(lambda s, q, b: s.history.delete([str(i) for i in b.get("screens") or []])),
        "/api/group-rename": _obj(lambda s, q, b: s.history.group_rename(b.get("from"), b.get("to"))),   # 줄 = 섹션(51-4)
        "/api/group-dissolve": _obj(lambda s, q, b: s.history.group_dissolve(b.get("name"))),
        "/api/group-move": _obj(lambda s, q, b: s.history.group_move(b.get("ids"), b.get("to"))),      # R31 다른 줄(폴더)로 옮기기
        "/api/token": _obj(lambda s, q, b: s.history.token(b.get("name"), b.get("value"))),   # R55 Foundation 토큰 하나 — tokens.css 쓰기 한 번
        "/api/restore": _obj(lambda s, q, b: s.history.restore(str(b.get("stamp") or ""), keep=b.get("keep") is True, notify=b.get("notify") is True)),
        "/api/reply": lambda s, q, b: s.queue.reply(b),
        "/api/claim": lambda s, q, b: s.busy.claim(b),
        "/api/release": lambda s, q, b: s.busy.release(b),
        "/api/archive": lambda s, q, b: s.archive.post(b),
        "/api/chat": lambda s, q, b: s.chat.post(b),                    # S3 캔버스가 남기는 ask(보낸 글·칩) · undone(턴 되돌림)
        "/api/forward": _obj(lambda s, q, b: s.queue.send(b)),          # 47-5a: to · notes, 이벤트 또는 어댑터
        "/hello": lambda s, q, b: s.presence.hello(b),
        "/api/hello": lambda s, q, b: s.presence.hello(b),
        "/beat": lambda s, q, b: s.presence.beat(b),
        "/api/beat": lambda s, q, b: s.presence.beat(b),
        "/bye": lambda s, q, b: s.presence.bye(b),
        "/api/bye": lambda s, q, b: s.presence.bye(b),
        "/progress": lambda s, q, b: s.presence.progress(b),
        "/api/progress": lambda s, q, b: s.presence.progress(b),
        "/agents/spawn": lambda s, q, b: s.spawn(b),                    # 기본 꺼짐(HD_ALLOW_SPAWN=1)
        "/api/agents/spawn": lambda s, q, b: s.spawn(b),
        "/api/attach": lambda s, q, b: s.queue.attach(b),
        "/api/agents/effort": _obj(lambda s, q, b: s.agent_info.effort(b)),   # R28 생각 깊이 바꾸기 {effort} — paseo agent update --thinking
        "/api/image": lambda s, q, b: s.images.save(b),                 # R22 첨부 이미지 저장 {data} → {path, rel, type, size}(본문 한도 BODY_MAX)
        "/api/watch": lambda s, q, b: (200, s.busy.mtimes(b.get("files") if isinstance(b, dict) else None)),
    },
    "PUT": {
        "/api/state": lambda s, q, b: s.store.put(b),
    },
}
BODY_MAX = {"/api/image": AR.BODY_MAX}              # 본문 한도가 STATE_MAX(2 MB)와 다른 주소 — 이미지 한 장(base64)


class Router:
    """세션 주소 표(ROUTES) + 서버 주소(on_stop · home_ctx) → 담당. home_ctx 가 없으면 프로젝트·탭 주소는 모르는 주소."""

    def __init__(self, home_ctx=None, on_stop=None, on_restart=None):
        self.home_ctx, self.on_stop, self.on_restart = home_ctx, on_stop, on_restart

    def knows(self, method, path):
        if path in ROUTES.get(method, {}):
            return True
        if method == "POST" and path == "/api/stop":
            return self.on_stop is not None
        if method == "POST" and path == "/api/hub/restart":
            return self.on_restart is not None
        home = {"GET": home_api.GET_PATHS, "POST": home_api.POST_PATHS, "PUT": home_api.PUT_PATHS}.get(method, ())
        return self.home_ctx is not None and path in home

    def call(self, method, path, query, body, session):
        fn = ROUTES.get(method, {}).get(path)
        if fn is not None:
            return fn(session, query or {}, body)
        if method == "POST" and path == "/api/stop" and self.on_stop:
            return 200, {"stopping": True}, self.on_stop
        if method == "POST" and path == "/api/hub/restart" and self.on_restart:   # R34 프로젝트 화면의 [다시 켜기] — 홈 화면과 같은 restart
            try:
                self.on_restart()
            except OSError as e:
                return 500, {"error": "허브를 다시 켜지 못했어요: %s" % e}
            return 200, {"restarting": True}
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

    def _given_token(self):                          # 머리글, 없으면 이벤트 흐름의 ?hd=(EventSource 는 머리글을 못 보낸다)
        return self.headers.get("X-HD-Token") or getattr(self, "_query_token", None)

    def _token_ok(self, sess):
        return self._given_token() == sess.token

    # ------------------------------------------------------------ 이벤트 흐름(SSE, 47-4a)
    def _peer_gone(self):
        """손님이 연결을 닫았나 — 읽을 것이 있는데 0 바이트면 닫힘(select 0초 + MSG_PEEK, 막히지 않음)."""
        try:
            r, _, _ = select.select([self.connection], [], [], 0)
            return bool(r) and self.connection.recv(1, socket.MSG_PEEK) == b""
        except (OSError, ValueError):
            return True

    def _events(self, sess, q):
        self._query_token = q.get("hd", [None])[0]
        if not self._token_ok(sess):
            return self._json(403, {"error": FORBIDDEN})
        last = self.headers.get("Last-Event-ID")
        want = EV.parse_last(last if last is not None else q.get("since", [None])[0])
        sub, back, reset = sess.events.subscribe(want)
        if sub is None:
            return self._json(503, {"error": "이 프로젝트에 열린 이벤트 흐름이 너무 많아요(%d) — 안 쓰는 창을 닫으세요" % EV.MAX_SUBS})
        self.close_connection = True
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            self.wfile.write(EV.RETRY_FRAME)
            if reset:
                self.wfile.write(EV.frame(EV.reset_event(sess.events, reset)))
            for ev in back:
                self.wfile.write(EV.frame(ev))
            self.wfile.flush()
            quiet = time.monotonic()
            while True:
                ev = sub.get(POLL)
                if ev is EV.CLOSED:
                    break
                if ev is None:
                    if self._peer_gone():
                        break
                    if time.monotonic() - quiet < HEARTBEAT:
                        continue
                    self.wfile.write(EV.HEARTBEAT_FRAME)
                else:
                    self.wfile.write(EV.frame(ev))
                self.wfile.flush()
                quiet = time.monotonic()
        except OSError:                              # 손님이 끊음(BrokenPipe · ConnectionReset · ConnectionAborted) — 조용히 끝
            pass
        finally:
            sess.events.unsubscribe(sub)
        return None

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "주소가 맞지 않아요"})           # 47-2 2b: 허브처럼 JSON(전에는 HTML)
        u = urllib.parse.urlparse(self.path)
        sess, rest = self.target(u.path)
        if rest in EVENT_PATHS:
            return self._events(sess, urllib.parse.parse_qs(u.query))
        if rest.startswith("/api/") or rest in V1_GET:   # /api 아래는 늘 JSON — 토큰 먼저, 모르는 주소·POST 전용 주소는 404(2b)
            if not self._token_ok(sess):
                return self._json(403, {"error": FORBIDDEN})
            if not self.router.knows("GET", rest):
                return self._json(404, {"error": "모르는 주소"})
            return self._reply(self.router.call("GET", rest, urllib.parse.parse_qs(u.query), None, sess))
        parts = [p for p in rest.split("/") if p]
        if any(p.startswith(".") for p in parts):        # 원본 기록·대기열·상태 파일은 내주지 않는다
            return self.send_error(404)
        if rest in ("/", "/index.html"):
            return self._page(sess)
        return super().do_GET()

    def _drain(self, n):                                 # 거절해도 본문은 다 읽는다 — 안 읽은 채 닫으면 Windows 가 RST 로 끊어 상대가 답 대신 연결 오류를 받는다
        while n > 0:
            chunk = self.rfile.read(min(n, 65536))
            if not chunk:
                break
            n -= len(chunk)

    def _body_call(self, method):
        """POST·PUT 차례(47-2 2c·2d): Host + 토큰(403) → 크기(2 MB 넘으면 413) → 아는 주소(404) → JSON(400) → 담당."""
        try:
            n = max(0, int(self.headers.get("Content-Length") or 0))
        except ValueError:
            n = 0
        path = urllib.parse.urlparse(self.path).path
        sess, rest = self.target(path)
        if not self._host_ok() or not self._token_ok(sess):
            self._drain(n)
            return self._json(403, {"error": FORBIDDEN})
        cap = BODY_MAX.get(rest, STATE_MAX)
        if n > cap:
            self._drain(n)
            return self._json(413, {"error": helper_model.too_big(n, cap)})
        raw = self.rfile.read(n) if n else b""
        if not self.router.knows(method, rest):
            return self._json(404, {"error": "모르는 주소"})
        try:
            body = json.loads(raw or (b"{}" if method == "POST" else b"null"))
        except ValueError:
            return self._json(400, {"error": "JSON 이 아니에요"})
        return self._reply(self.router.call(method, rest, None, body, sess))

    def do_POST(self):
        return self._body_call("POST")

    def do_PUT(self):
        return self._body_call("PUT")
