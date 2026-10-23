"""Model — 프로젝트 목록(링크만) 규칙. 순수: 파일·네트워크·시계를 쓰지 않는다(tests/test_hd_projects.py 의 순수성 검사).

목록 = $HD_HOME/projects.json = {version:1, projects:[{name, out, kind:'run', created, last_opened}]} — 어디 있는지만 적는다(복사 없음).
상태는 <out>/.hd-canvas.json 에 이미 있으므로 링크 하나로 다시 열 수 있다.
- 이름: slug(글자·숫자·'-', 소문자), 목록 안에서 하나뿐. 같은 out 을 두 번 넣으면 같은 항목(이름만 바뀔 수 있음)
- 경로 비교는 key(): 역슬래시 → '/', 끝 '/' 없앰, 드라이브 문자로 시작하면(Windows) 대소문자 무시. 경로를 절대경로로 푸는 일은 Client 가 한다
- 지우기는 forget(이름) 뿐 — 링크만 지운다. out 폴더가 없어진 항목도 저절로 지우지 않는다(목록에 '없음')
"""

VERSION = 1
KIND = "run"


class ProjectError(Exception):
    """규칙 위반 — 사용자에게 그대로 보일 한 줄."""


def empty():
    return {"version": VERSION, "projects": []}


def key(path):
    p = str(path).replace("\\", "/")
    while len(p) > 1 and p.endswith("/") and not p.endswith(":/"):
        p = p[:-1]
    return p.casefold() if len(p) >= 2 and p[1] == ":" else p


def slug(text):
    """'My Run v2!' → 'my-run-v2' · 한글 그대로 · 빈 글 → ''."""
    out, dash = [], False
    for c in str(text or "").strip().lower():
        if c.isalnum():
            out.append(c); dash = False
        elif not dash and out:
            out.append("-"); dash = True
    return "".join(out).strip("-")


def _entry_ok(e):
    return isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"] == slug(e["name"]) and e["name"] \
        and isinstance(e.get("out"), str) and e["out"]


def parse(doc):
    """읽은 JSON → (목록, 경고 | None, 깨짐 bool). 모양이 틀리면 (empty(), 이유, True) — Client 가 파일을 옆으로 옮긴다.
    항목 하나만 틀리면 그것만 빼고 (목록, 경고, False) — 파일은 그대로."""
    if not isinstance(doc, dict) or doc.get("version") != VERSION or not isinstance(doc.get("projects"), list):
        return empty(), "목록 파일 모양이 아니에요(version %s)" % (doc.get("version") if isinstance(doc, dict) else "?"), True
    good, seen_n, seen_o = [], set(), set()
    for e in doc["projects"]:
        if not _entry_ok(e) or e["name"] in seen_n or key(e["out"]) in seen_o:
            continue
        seen_n.add(e["name"]); seen_o.add(key(e["out"]))
        good.append({"name": e["name"], "out": e["out"], "kind": e.get("kind") or KIND,
                     "created": e.get("created"), "last_opened": e.get("last_opened")})
    bad = len(doc["projects"]) - len(good)
    return {"version": VERSION, "projects": good}, ("항목 %d개를 건너뜀(모양이 틀리거나 겹침)" % bad if bad else None), False


def find(reg, ref):
    """이름 또는 경로 → 항목 | None. 이름이 먼저."""
    ps = reg["projects"]
    for e in ps:
        if e["name"] == ref:
            return e
    k = key(ref)
    return next((e for e in ps if key(e["out"]) == k), None)


def by_out(reg, out):
    k = key(out)
    return next((e for e in reg["projects"] if key(e["out"]) == k), None)


def _free_name(reg, base, out):
    taken = {e["name"] for e in reg["projects"] if key(e["out"]) != key(out)}
    if base not in taken:
        return base
    i = 2
    while "%s-%d" % (base, i) in taken:
        i += 1
    return "%s-%d" % (base, i)


def save(reg, out, now, name=None, default_name="project"):
    """링크 넣기·고치기 → (새 목록, 항목, 새로 넣었나). 원래 목록은 고치지 않는다.
    같은 out 이 있으면 그 항목(name 을 주면 이름만 바꿈). 없으면 새 항목 — 이름은 name, 없으면 default_name 의 slug(겹치면 -2, -3…).
    name 이 slug 로 비거나 다른 out 이 이미 쓰면 ProjectError."""
    if name is not None:
        n = slug(name)
        if not n:
            raise ProjectError("이름은 글자·숫자·'-' 로: %r" % name)
        other = next((e for e in reg["projects"] if e["name"] == n and key(e["out"]) != key(out)), None)
        if other:
            raise ProjectError("이름 '%s' 은 이미 다른 프로젝트예요: %s" % (n, other["out"]))
    ps = [dict(e) for e in reg["projects"]]
    new = {"version": VERSION, "projects": ps}
    cur = next((e for e in ps if key(e["out"]) == key(out)), None)
    if cur:
        if name is not None:
            cur["name"] = slug(name)
        return new, cur, False
    e = {"name": slug(name) if name is not None else _free_name(reg, slug(default_name) or "project", out),
         "out": str(out), "kind": KIND, "created": now, "last_opened": now}
    ps.append(e)
    return new, e, True


def touch(reg, out, now):
    """out 의 last_opened = now → 새 목록(없으면 그대로)."""
    ps = [dict(e, last_opened=now) if key(e["out"]) == key(out) else dict(e) for e in reg["projects"]]
    return {"version": VERSION, "projects": ps}


def forget(reg, name):
    """이름 → (새 목록, 지운 항목 | None). 링크만 — 파일은 Client 도 건드리지 않는다."""
    hit = next((e for e in reg["projects"] if e["name"] == name), None)
    return {"version": VERSION, "projects": [dict(e) for e in reg["projects"] if e is not hit]}, hit


def ordered(reg):
    """최근에 연 것부터(last_opened 없으면 맨 뒤), 같으면 이름 순."""
    ps = list(reg["projects"])
    ps.sort(key=lambda e: e["name"])
    ps.sort(key=lambda e: e.get("last_opened") or "", reverse=True)
    return ps


def rows(reg, alive, exists):
    """목록 + 살아 있는 표지 + out 이 있는지 → 줄 객체 [{name, out, state:'running'|'off'|'missing', url, pid, last_opened}].
    alive = 표지 목록, exists = {key(out): bool}."""
    live = {key(m["out"]): m for m in alive if isinstance(m, dict) and m.get("out")}
    out = []
    for e in ordered(reg):
        m = live.get(key(e["out"]))
        st = "running" if m else ("off" if exists.get(key(e["out"])) else "missing")
        out.append({"name": e["name"], "out": e["out"], "state": st, "url": m.get("url") if m else None,
                    "pid": m.get("pid") if m else None, "last_opened": e.get("last_opened")})
    return out


STATE_WORD = {"running": None, "off": "꺼짐", "missing": "없음"}


def format_rows(rs):
    """줄 객체 → `name · out · url|꺼짐|없음 · 연 때`."""
    if not rs:
        return "(저장한 프로젝트 없음 — hd save 로 넣으세요)"
    return "\n".join("%s · %s · %s · %s" % (r["name"], r["out"], r["url"] or STATE_WORD[r["state"]], r["last_opened"] or "-") for r in rs)


def link_line(e):
    return "%s → %s" % (e["name"], e["out"])
