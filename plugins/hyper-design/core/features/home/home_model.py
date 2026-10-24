"""Model — Home 규칙(구역·검색·정렬·상대 시각·탭 목록·새 프로젝트 이름·썸네일 낡음). 순수: 파일·네트워크·시계를 쓰지 않는다
(tests/test_home_model.py 의 순수성 검사). 시각은 받은 값(iso 글 · 초)만 쓴다.

- 구역: recent(최근 항목: 휴지통 아님, 연 때 최근 것부터, 100개) · all(모든 프로젝트: 휴지통 아님, 제목 순) ·
  starred(별표: 휴지통 아님, 연 때 순) · trash(휴지통: 넣은 때 최근 것부터)
- 검색: 제목·이름에 casefold 부분 일치(빈 검색 = 전부)
- 탭: tabs.json = {version:1, tabs:[name]} — 모르는 이름·겹친 이름은 읽을 때 버린다
- 새 프로젝트: 제목이 없으면 '새 프로젝트 N'(안 쓰인 가장 작은 N) · 이름 = 제목 slug(없으면 project), 겹치면 -2, -3…
"""
import datetime

import hd_projects as P

SECTIONS = ("recent", "all", "starred", "trash")
RECENT_MAX = 100
TABS_VERSION = 1
NEW_TITLE = "새 프로젝트"


# ---------------------------------------------------------------- 구역 · 검색
def section(rows, which):
    """줄 객체(/api/projects) → 그 구역의 줄(차례 포함). 모르는 구역 → ValueError."""
    if which not in SECTIONS:
        raise ValueError("모르는 구역이에요: %s" % which)
    live = [r for r in rows if not r.get("trashed")]
    by_open = lambda rs: sorted(rs, key=lambda r: r.get("last_opened") or "", reverse=True)
    if which == "recent":
        return by_open(live)[:RECENT_MAX]
    if which == "all":
        return sorted(live, key=lambda r: ((r.get("title") or r["name"]).casefold(), r["name"]))
    if which == "starred":
        return by_open([r for r in live if r.get("starred")])
    return sorted([r for r in rows if r.get("trashed")], key=lambda r: r.get("trashed") or "", reverse=True)


def search(rows, q):
    """제목·이름 casefold 부분 일치. 빈 검색 = 그대로."""
    q = (q or "").strip().casefold()
    if not q:
        return list(rows)
    return [r for r in rows if q in (r.get("title") or "").casefold() or q in r["name"].casefold()]


# ---------------------------------------------------------------- 상대 시각
def _parse(iso):
    try:
        return datetime.datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return None


def rel_time(iso, now_iso):
    """iso 시각 + 지금(iso) → '방금 전' · 'N분 전' · 'N시간 전'(같은 날) · '어제' · 'MM-DD'(올해) · 'YYYY-MM-DD'. 못 읽으면 ''."""
    t, now = _parse(iso), _parse(now_iso)
    if t is None or now is None:
        return ""
    if (t.tzinfo is None) != (now.tzinfo is None):
        t, now = t.replace(tzinfo=None), now.replace(tzinfo=None)
    elif t.tzinfo is not None:
        t = t.astimezone(now.tzinfo)
    sec = (now - t).total_seconds()
    if sec < 60:
        return "방금 전"
    if t.date() == now.date():
        return "%d분 전" % (sec // 60) if sec < 3600 else "%d시간 전" % (sec // 3600)
    if (now.date() - t.date()).days == 1:
        return "어제"
    return t.strftime("%m-%d") if t.year == now.year else t.strftime("%Y-%m-%d")


# ---------------------------------------------------------------- 탭 (tabs.json)
def _clean(names, known):
    out = []
    for n in names:
        if isinstance(n, str) and n in known and n not in out:
            out.append(n)
    return out


def tabs_parse(doc, known):
    """읽은 tabs.json → (탭 이름 목록, 경고 | None). 모양이 틀리면 ([], 이유). 모르는 이름·겹침은 조용히 버린다(설계: 읽을 때 버림)."""
    if not isinstance(doc, dict) or doc.get("version") != TABS_VERSION or not isinstance(doc.get("tabs"), list):
        return [], "탭 파일 모양이 아니에요"
    return _clean(doc["tabs"], set(known)), None


def tabs_set(tabs, known):
    """PUT 본문의 tabs → 정리한 목록. 글 목록이 아니면 ValueError(한 줄)."""
    if not isinstance(tabs, list) or not all(isinstance(n, str) for n in tabs):
        raise ValueError("tabs: 이름 목록이어야 해요")
    return _clean(tabs, set(known))


def tabs_add(tabs, name):
    return list(tabs) if name in tabs else list(tabs) + [name]


def tabs_drop(tabs, name):
    return [n for n in tabs if n != name]


def tabs_doc(tabs):
    return {"version": TABS_VERSION, "tabs": list(tabs)}


# ---------------------------------------------------------------- 새 프로젝트
def default_title(titles):
    """쓰인 제목들 → '새 프로젝트 N'(N = 안 쓰인 가장 작은 1 이상)."""
    used = set(titles)
    n = 1
    while "%s %d" % (NEW_TITLE, n) in used:
        n += 1
    return "%s %d" % (NEW_TITLE, n)


def new_name(title, taken):
    """제목 → 목록·폴더 어디에도 없는 이름(slug, 겹치면 -2, -3…)."""
    base = P.slug(title) or "project"
    if base not in taken:
        return base
    i = 2
    while "%s-%d" % (base, i) in taken:
        i += 1
    return "%s-%d" % (base, i)


def empty_manifest(title):
    """빈 캔버스의 screens.json — 화면 없음(캔버스가 빈 상태를 보인다)."""
    return {"title": title, "groups": [], "screens": []}


# ---------------------------------------------------------------- 썸네일
def thumb_stale(png_mtime, src_mtimes):
    """썸네일 mtime(없으면 None) + 원본 mtime 들(.hd-canvas.json · index.html, 없으면 None) → 다시 그려야 하나.
    원본이 하나도 없으면 그릴 것이 없다(False)."""
    srcs = [m for m in src_mtimes if m is not None]
    if not srcs:
        return False
    return png_mtime is None or png_mtime < max(srcs)


def thumb_url(port, name, mtime):
    """허브 썸네일 주소 | None(허브 포트·그림이 없음). ?t= 는 캐시 깨기."""
    if not port or mtime is None:
        return None
    return "http://127.0.0.1:%d/thumb/%s.png?t=%d" % (int(port), name, int(mtime))


def thumb_name(path_tail, known):
    """'/thumb/<name>.png' 의 꼬리 → 알려진 이름 | None(모르는 이름·모양이 틀림 — 경로 밖으로 나가지 못하게)."""
    if not path_tail.endswith(".png"):
        return None
    n = path_tail[:-4]
    return n if n in known and n == P.slug(n) else None
