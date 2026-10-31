"""Model — 응답 캐시 규칙 하나(보드 전환 S2): 주소·상태 → Cache-Control · 정적 파일 판 표(ETag) · 같은 판인지. I/O 없음.

머리글은 여기서만 정한다(브리프 이음매 3) — canvas/router.py SessionHandler(도우미·허브 세션)와 home/home_server.py 허브가 header() 를 부른다.
- 페이지(`/` · `/index.html` · 허브 `/home.html`) · `/api/*` · 이벤트 흐름 · `/v1/…` · `/agents` · 모르는 종류(데이터 json 포함) = no-store(늘 새로)
- out 의 정적 파일(js·css·이미지·글꼴·화면 html) = no-cache — 매번 묻고 같은 판이면 304(SessionHandler.send_head)
- out 맨 위 셸 파일(hd-shell.js · hd-shell.css, S3)에 `?v=<도장>` = max-age=31536000, immutable — 도장이 바뀌면 주소가 바뀐다
- 허브 공용 셸 `/v1/shell/<도장>/<파일>`(1단계 P1a, shell_store) = immutable — 주소에 도장이 든다(그 밖 `/v1/…` 은 no-store 그대로)
- 허브 썸네일 `/thumb/…` = max-age=31536000(주소의 ?t= 가 바뀌면 새로 — 예전 그대로)
- 200·304 가 아닌 답(301·403·404·500 …) = 늘 no-store(아직 없는 셸 파일의 404 가 1년 남지 않게)
판 표 = ETag(mtime_ns·크기). Last-Modified 는 초 단위라 같은 초 안에 다시 쓴 화면 파일을 304 로 놓친다(10-31 확인) — 시각만 온 물음은 견주지 않는다.
"""
import posixpath, urllib.parse

NO_STORE = "no-store"
REVALIDATE = "no-cache"
IMMUTABLE = "max-age=31536000, immutable"
THUMB = "max-age=31536000"

PAGES = ("", "/", "/index.html", "/home.html")
NEVER = ("/api/", "/v1/")                               # 이 아래는 늘 JSON·흐름·세션 주소
EVENTS = ("/events", "/agents")
SHELL = ("/hd-shell.js", "/hd-shell.css")
SHARED_SHELL = "/v1/shell/"                             # 허브 공용 셸(도장이 주소에 듦 — 이름 검사는 shell_store.route)
STATIC = frozenset((".js", ".mjs", ".css", ".html", ".htm", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico",
                    ".woff", ".woff2", ".ttf", ".otf"))
CACHED = (200, 304)


def header(raw, status=200):
    """요청 주소(물음 포함, 세션이면 세션 안 경로) · 답 상태 → Cache-Control 값."""
    if status not in CACHED:
        return NO_STORE
    u = urllib.parse.urlsplit(raw or "")
    path = urllib.parse.unquote(u.path)
    if path.startswith(SHARED_SHELL):
        return IMMUTABLE
    if path in PAGES or path in EVENTS or path.startswith(NEVER):
        return NO_STORE
    if path.startswith("/thumb/"):
        return THUMB
    if path in SHELL and urllib.parse.parse_qs(u.query).get("v", [""])[0]:
        return IMMUTABLE
    return REVALIDATE if posixpath.splitext(path)[1].lower() in STATIC else NO_STORE


def etag(mtime_ns, size):
    """정적 파일 판 표 — 고친 시각(나노초)과 크기."""
    return '"%x-%x"' % (int(mtime_ns), int(size))


def same(if_none_match, tag):
    """If-None-Match 머리글이 tag 판을 말하나(약한 W/ · 여러 개 · * 포함)."""
    if not if_none_match or not tag:
        return False
    if if_none_match.strip() == "*":
        return True
    return tag in (t.strip()[2:] if t.strip().startswith("W/") else t.strip() for t in if_none_match.split(","))
