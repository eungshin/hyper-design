"""Model — 코드 도장(이 캔버스 코드가 어느 판인가)과 '다시 쓸까' 규칙. 파일·git·시계를 쓰지 않는다(tests/test_canvas_unit_code_stamp.py).

도장 = 'g:<core 나무 sha 앞 16>'(저장소 — build_ref 가 쓰는 git ref 의 core 나무) | 'w:<내용 해시 16>'(저장소가 아님 — 빌드 입력 파일 내용).
- index.html 은 빌드한 코드의 도장을 <meta name="hd-code" content="…"> 로 품는다(build_canvas).
- 떠 있는 도우미·허브는 자기가 뜰 때의 도장을 표지(code)에 적는다(그 프로세스 안 Python 이 그 판).
- 열기(hd open · 허브 open · 페이지 받기)가 지금 도장과 견줘: 페이지가 옛것이면 다시 빌드, 프로세스가 옛것이면(쉬는 중) 다시 띄움.
"""
import hashlib
import re

META = '<meta name="hd-code" content="%s">'
_META_RE = re.compile(r'<meta\s+name="hd-code"\s+content="([^"<>]*)"\s*/?>', re.I)
_HEX = re.compile(r"^[0-9a-f]{16,64}$")
HUB_NOTICE = "새 버전이 있어요 — 허브를 다시 켜면 반영돼요"
BUSY_NOTICE = "도우미가 옛 코드로 떠 있지만 AI 가 작업 중이라(덮개) 끄지 않아요 — 끝난 뒤 다시 열면 새 코드로 떠요"


def tree_stamp(sha):
    """git 나무 sha → 'g:<앞 16>' | None(sha 모양이 아님)."""
    sha = (sha or "").strip().lower()
    return "g:" + sha[:16] if _HEX.match(sha) else None


def content_stamp(parts):
    """[(이름, bytes)] → 'w:<16>' — 이름 차례와 상관없이 같은 내용이면 같은 도장."""
    h = hashlib.sha256()
    for name, data in sorted(parts, key=lambda p: p[0]):
        h.update(name.encode("utf-8") + b"\0" + hashlib.sha256(data).digest())
    return "w:" + h.hexdigest()[:16]


def stamp_page(html, stamp):
    """index.html 글 → 첫 <head> 바로 뒤에 도장 meta(이미 있으면 바꿈). stamp 가 없으면 그대로."""
    if not stamp:
        return html
    tag = META % stamp.replace('"', "")
    if _META_RE.search(html):
        return _META_RE.sub(lambda m: tag, html, count=1)
    return html.replace("<head>", "<head>" + tag, 1) if "<head>" in html else tag + html


def page_stamp(html):
    """index.html 글 → 품은 도장 | None(도장 전 빌드)."""
    m = _META_RE.search(html or "")
    return m.group(1) or None if m else None


def stale(have, current):
    """지금 도장(current)을 알 때만 판단 — 모르면(git 실패 등) 옛것이라 하지 않는다(헛 빌드·헛 재시작을 막음)."""
    return bool(current) and have != current


def reuse_verdict(page, proc, current, busy=False, movable=True):
    """떠 있는 서버를 다시 쓰기 전 → 'fresh' | 'rebuild'(페이지만 다시 빌드) | 'restart'(옛 프로세스를 끄고 새로 — 새 프로세스 앞에서 빌드)
    | 'busy'(옛 프로세스지만 AI 작업 중 — 프로세스는 그대로·한 번 알림, 페이지는 옛것이면 다시 빌드: page_after).
    page = index.html 의 도장 · proc = 그 서버 프로세스가 뜰 때 도장(옛 도우미는 None = 옛것) · movable = 끄고 다시 띄울 수 있나(허브 안 세션은 아님 — 허브 알림이 따로)."""
    if not current:
        return "fresh"
    if movable and stale(proc, current):
        return "busy" if busy else "restart"
    return "rebuild" if stale(page, current) else "fresh"


def page_after(verdict, page, current):
    """그 판단 뒤 페이지를 다시 빌드하나 — rebuild, 또는 busy 인데 페이지가 옛것(프로세스는 못 바꿔도 화면은 지금 코드)."""
    return verdict == "rebuild" or (verdict == "busy" and stale(page, current))
