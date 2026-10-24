"""Controller — Home·프로젝트 API 라우트 하나(허브 home_server 와 캔버스 helper.py 가 같은 JSON 을 내게 둘 다 이것을 부른다).

route(method, path, body, ctx) → (code, 답 객체) | None(이 모듈 주소가 아님). 토큰·Host 검사는 부르는 서버가 먼저 한다.
  GET  /api/projects            → [{name, title, out, state, url, pid, created, last_opened, starred, trashed, thumb}]
  POST /api/open {name, agent?} → {name, out, url, pid, agent, reused} (탭 끝에 더함)
  POST /api/new {title?}        → {name, title, url} — 빈 캔버스를 만들고 띄움(탭 끝에 더함)
  POST /api/project {name, title?, starred?, trashed?} → {row} (휴지통에 넣으면 탭에서 뺌)
  POST /api/forget {name}       → {ok} — 휴지통에 든 링크만(파일은 그대로)
  POST /api/reveal {name}       → {ok} — out 폴더를 탐색기로
  POST /api/pick-folder         → {name} | {cancel:true} — 허브만(ctx.picker)
  GET  /api/tabs · PUT /api/tabs {tabs} → {tabs}
  GET  /api/home                → {url} — 도우미만(허브를 띄우거나 그 주소)
오류 = {error: 한국어 한 줄} + 4xx/5xx. I/O 는 hd_client · home_client, 규칙은 hd_projects · home_model.
"""
import pathlib, sys, traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "hd"))
import hd_client as C  # noqa: E402
import hd_model  # noqa: E402
import home_client as H  # noqa: E402
import home_model as M  # noqa: E402


class Ctx:
    """서버마다 다른 것: hub(허브인가) · agent()(보낼 Paseo 에이전트) · port()(썸네일 주소의 허브 포트) ·
    after_rows(rows)(허브: 낡은 썸네일 그리기 예약) · picker()(허브: 폴더 고르기 → 경로 | None)."""

    def __init__(self, hub, agent=lambda: None, port=lambda: None, after_rows=None, picker=None):
        self.hub, self.agent, self.port, self.after_rows, self.picker = hub, agent, port, after_rows, picker


def thumb_path(name):
    return H.home() / "thumbs" / ("%s.png" % name)


def _mtime(p):
    try:
        return p.stat().st_mtime
    except OSError:
        return None


def with_thumb(row, port):
    return dict(row, thumb=M.thumb_url(port, row["name"], _mtime(thumb_path(row["name"]))))


def _name(body):
    if not isinstance(body, dict) or not isinstance(body.get("name"), str) or not body["name"].strip():
        return None
    return body["name"]


def _tabs_add(name):
    try:
        H.change_tabs(lambda t: M.tabs_add(t, name))
    except OSError as e:                                 # 탭 못 씀 = 열기는 됐으니 한 줄 남기고 계속
        C.warn("탭 목록을 쓰지 못했어요(%s)" % e)


def projects_get(ctx):
    port = ctx.port()
    rows = [with_thumb(r, port) for r in C.project_rows()]
    if ctx.after_rows:
        ctx.after_rows(rows)
    return 200, rows


def open_post(body, agent=None):
    """hd open 과 같은 hd_client.open_project(브라우저 없음) → 탭 끝에 더함."""
    name = _name(body)
    if name is None:
        return 400, {"error": "name: 프로젝트 이름 또는 out 경로가 없어요"}
    a = body.get("agent", agent)
    if hd_model.agent_error(a):
        return 400, {"error": hd_model.agent_error(a)}
    try:
        e, m, reused = C.open_project(name, a)
    except C.NotFound as x:
        return 404, {"error": str(x)}
    except C.HdError as x:
        return 500, {"error": str(x)}
    _tabs_add(e["name"])
    return 200, {"name": e["name"], "out": e["out"], "url": m["url"], "pid": m.get("pid"), "agent": m.get("agent"), "reused": reused}


def new_post(body, agent=None):
    if not isinstance(body, dict):
        return 400, {"error": "JSON 객체가 아니에요"}
    title = body.get("title")
    if title is not None and not isinstance(title, str):
        return 400, {"error": "title: 글이어야 해요"}
    try:
        e = H.create_project(title)
    except C.HdError as x:
        return 400, {"error": str(x)}
    try:
        _, m, _ = C.open_project(e["name"], agent)
    except C.HdError as x:
        return 500, {"error": "프로젝트는 만들었지만 띄우지 못했어요(%s): %s" % (e["name"], x)}
    _tabs_add(e["name"])
    return 200, {"name": e["name"], "title": e.get("title"), "url": m["url"]}


def project_post(body, ctx):
    name = _name(body)
    if name is None:
        return 400, {"error": "name: 프로젝트 이름이 없어요"}
    fields = {k: body[k] for k in ("title", "starred", "trashed") if k in body}
    if not fields:
        return 400, {"error": "바꿀 칸이 없어요(title · starred · trashed)"}
    try:
        row = C.update_project(name, **fields)
    except C.NotFound as x:
        return 404, {"error": str(x)}
    except C.HdError as x:
        return 400, {"error": str(x)}
    if fields.get("trashed") is True:
        H.change_tabs(lambda t: M.tabs_drop(t, name))
    return 200, {"row": with_thumb(row, ctx.port())}


def forget_post(body):
    name = _name(body)
    if name is None:
        return 400, {"error": "name: 프로젝트 이름이 없어요"}
    try:
        C.forget_trashed(name)
    except C.NotFound as x:
        return 404, {"error": str(x)}
    except C.HdError as x:
        return 409, {"error": str(x)}
    return 200, {"ok": True}


def reveal_post(body):
    name = _name(body)
    if name is None:
        return 400, {"error": "name: 프로젝트 이름이 없어요"}
    e = next((x for x in C.load_projects()["projects"] if x["name"] == name), None)
    if e is None:
        return 404, {"error": "모르는 프로젝트예요: %s" % name}
    try:
        H.reveal(e["out"])
    except C.NotFound as x:
        return 404, {"error": str(x)}
    return 200, {"ok": True}


def pick_post(ctx):
    try:
        path = ctx.picker()
    except C.HdError as x:
        return 500, {"error": str(x)}
    if not path:
        return 200, {"cancel": True}
    try:
        e = H.register_folder(path)
    except C.HdError as x:
        return 400, {"error": str(x)}
    return 200, {"name": e["name"]}


def tabs_put(body):
    if not isinstance(body, dict) or "tabs" not in body:
        return 400, {"error": "tabs: 없어요({tabs: [이름]})"}
    try:
        known = H.known_names()
        return 200, {"tabs": H.save_tabs(M.tabs_set(body["tabs"], known))}
    except ValueError as x:
        return 400, {"error": str(x)}


def home_get():
    try:
        return 200, {"url": H.ensure_hub()}
    except C.HdError as x:
        return 500, {"error": str(x)}


def route(method, path, body, ctx):
    """→ (code, 답) | None(모르는 주소 — 부르는 서버가 처리). 예상 못 한 실패(파일 쓰기 등)도 숨기지 않는다: 500 한 줄 + 로그에 추적."""
    try:
        return _route(method, path, body, ctx)
    except Exception as e:
        traceback.print_exc()
        return 500, {"error": "서버 오류(%s): %s" % (type(e).__name__, e)}


def _route(method, path, body, ctx):
    if method == "GET":
        if path == "/api/projects":
            return projects_get(ctx)
        if path == "/api/tabs":
            return 200, {"tabs": H.load_tabs()}
        if path == "/api/home" and not ctx.hub:
            return home_get()
        return None
    if method == "PUT":
        return tabs_put(body) if path == "/api/tabs" else None
    if method != "POST":
        return None
    if path == "/api/open":
        return open_post(body, ctx.agent())
    if path == "/api/new":
        return new_post(body, ctx.agent())
    if path == "/api/project":
        return project_post(body, ctx)
    if path == "/api/forget":
        return forget_post(body)
    if path == "/api/reveal":
        return reveal_post(body)
    if path == "/api/pick-folder" and ctx.hub and ctx.picker:
        return pick_post(ctx)
    return None


GET_PATHS = ("/api/projects", "/api/tabs", "/api/home")
