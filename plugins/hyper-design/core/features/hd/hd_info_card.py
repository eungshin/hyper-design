"""Model — 정보 카드(R47) Python 미러: canvas modules/info-card.js 와 같은 규칙. 순수(I/O·시계 없음).

data = {notes: state['board-notes'], links: state['board-links'], groups: {화면 id: 줄 이름}(screens.json screens[].group)}.
ends · reach · collect · para · text · for_screen · counts — 뜻은 info-card.js 머리 주석, 사례는 canvas contract/info-card-cases.json(JS·Python 둘 다 돈다).
글자 수는 코드 포인트(len) — JS 쪽도 Array.from 으로 같은 수를 센다.
"""
import re

HEAD = "유의(정보 카드):"
MAX = 1200
PARA = 300
DEPTH = 4


def _cut(s, n):
    return s[:n - 1] + "…" if len(s) > n else s


def para(t):
    """첫 문단 한 줄(빈칸 하나로), PARA 자 넘으면 …"""
    s = re.sub(r"\r\n?", "\n", "" if t is None else str(t))
    for p in re.split(r"\n[ \t]*\n", s):
        p = " ".join(p.split())
        if p:
            return _cut(p, PARA)
    return ""


def _live(notes, nid):
    n = notes.get(nid) if isinstance(notes, dict) else None
    return isinstance(n, dict) and n.get("hidden") is not True and bool(para(n.get("text")))


def _note_of(end):
    return end[5:] if isinstance(end, str) and end.startswith("note:") and len(end) > 5 else None


def _edges(links):
    out = []
    if not isinstance(links, dict):
        return out
    for l in links.values():
        f = _note_of(l.get("from")) if isinstance(l, dict) else None
        to = l.get("to") if isinstance(l, dict) else None
        if f and isinstance(to, str) and to and to != l.get("from"):
            out.append((f, to))
    return out


def ends(data, screen_id):
    s = str(screen_id)
    groups = (data or {}).get("groups")
    g = groups.get(s) if isinstance(groups, dict) else None
    return ["screen:" + s] + (["folder:" + g] if isinstance(g, str) and g else [])


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf")) else 0


def reach(data, targets):
    data = data or {}
    notes = data.get("notes") if isinstance(data.get("notes"), dict) else {}
    es, want, seen, out, frontier = _edges(data.get("links")), set(targets or []), set(), [], []
    for f, to in es:
        if to in want and f not in seen and _live(notes, f):
            seen.add(f)
            frontier.append(f)
    d = 1
    while frontier and d <= DEPTH:
        nxt = []
        for nid in frontier:
            n = notes[nid]
            out.append({"id": nid, "text": para(n.get("text")), "depth": d, "at": _num(n.get("at"))})
            for f, to in es:
                t = _note_of(to)
                other = t if f == nid else f if t == nid else None
                if other and other not in seen and _live(notes, other):
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
        d += 1
    return sorted(out, key=lambda x: (x["depth"], x["at"], x["id"]))


def collect(data, screen_id):
    return reach(data, ends(data, screen_id))


def text(lst):
    ls = ["- " + n["text"] for n in (lst or [])]
    n = len(ls)
    if not n:
        return ""
    for k in range(n, -1, -1):
        b = "\n".join([HEAD] + ls[:k]) + ("\n…(%d개 더)" % (n - k) if k < n else "")
        if len(b) <= MAX:
            return b
    return ""


def for_screen(data, screen_id):
    return text(collect(data, screen_id))


def cards_for(state, groups, screens):
    """상태 파일 state + {화면 id: 줄} + 화면 목록 → {화면 id: 카드 글}(빈 카드는 뺌) — hd notes 가 화면마다 한 번 보인다."""
    st = state if isinstance(state, dict) else {}
    data = {"notes": st.get("board-notes"), "links": st.get("board-links"), "groups": groups if isinstance(groups, dict) else {}}
    out = {}
    for s in screens or []:
        if s not in out:
            t = for_screen(data, s)
            if t:
                out[s] = t
    return out


def counts(data, screen_ids, group_names):
    out = {"screens": {}, "folders": {}}
    for s in screen_ids or []:
        c = len(collect(data, s))
        if c:
            out["screens"][s] = c
    for g in group_names or []:
        c = len(reach(data, ["folder:" + g]))
        if c:
            out["folders"][g] = c
    return out
