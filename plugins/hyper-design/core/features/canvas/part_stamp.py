"""Model — 앱 부품(out/parts.json) 도장과 '낡았나' 규칙 · 모양 검사 · post 단계. 파일·git·시계를 쓰지 않는다(tests/test_canvas_unit_part_stamp.py).

앱 부품 = 다른 저장소(앱) 소스로 빌드해 캔버스 화면이 iframe 으로 끌어 쓰는 out 안 HTML(예: screens/mock-settings-tabs.html).
도장 = 'g:<16>' — 지켜보는 경로(watch)의 커밋된 git 나무(HEAD:<경로>). 한 경로면 그 나무 sha 앞 16(code_stamp.tree_stamp 와 같은 모양),
  여럿이면 (경로, sha) 를 이름 차례로 섞은 해시. HEAD 가 아니라 나무라서 앱 저장소의 상관없는 커밋은 부품을 낡게 하지 않는다.
parts.json = {version: 1, parts: [{file, repo, watch, build, env?, post?, stamp, dirty, built_at}]} — 칸 뜻은 canvas contract.md '앱 부품'.
- 낡음 = 적힌 stamp ≠ 지금 도장. 지금 도장을 모르면(git 실패 · 저장소 아님) 'unknown' — 판단하지 않는다(code_stamp.stale 과 같음).
- dirty = 빌드할 때 지켜보는 경로에 커밋하지 않은 변경이 있었음 → "미커밋 변경 포함"(빌드는 막지 않는다).
- 모양이 틀린 항목은 건너뛰고 '[hd] parts.json …' 한 줄(projects.json 과 같은 규칙) — 줄을 내는 일은 부르는 쪽.
부르는 곳: parts_file(읽기·재기 — 도우미 /api/app-parts) · hd_parts(hd parts — parts.json 을 쓰는 유일한 곳).
"""
import hashlib
import re

import code_stamp as CS

VERSION = 1
OUT_TOKEN = "{out}"                                  # build argv · env 값 안 — 빌드 결과를 쓸 임시 경로로 바뀐다(hd_parts)
STALE, FRESH, UNKNOWN = "stale", "fresh", "unknown"
WORDS = {STALE: "낡음", FRESH: "최신", UNKNOWN: "모름"}
DIRTY_LABEL = "미커밋 변경 포함"
POST_STEPS = ("inject_before_body",)
_HEX = re.compile(r"^[0-9a-f]{16,64}$")
_ABS = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/])")
_BODY_END = re.compile(r"</body\s*>", re.I)


def tree_of(pairs):
    """[(경로, git 나무 sha)] → 'g:<16>' | None(비었음 · sha 모양이 아님 = 못 잼)."""
    pairs = list(pairs or [])
    if not pairs:
        return None
    clean = []
    for path, sha in pairs:
        sha = (sha or "").strip().lower()
        if not _HEX.match(sha):
            return None
        clean.append((path, sha))
    if len(clean) == 1:
        return CS.tree_stamp(clean[0][1])
    h = hashlib.sha256()
    for path, sha in sorted(clean):
        h.update(path.encode("utf-8") + b"\0" + sha.encode("ascii") + b"\n")
    return "g:" + h.hexdigest()[:16]


def state(part, current):
    """'stale' | 'fresh' | 'unknown'(지금 도장을 모름)."""
    if not current:
        return UNKNOWN
    return STALE if CS.stale(part.get("stamp"), current) else FRESH


def _rel(v):
    """out·저장소 기준 상대 경로 → '/' 로 고친 글 | None(빈 글 · 절대 경로 · '..' 이 든 경로)."""
    if not isinstance(v, str) or not v.strip() or _ABS.match(v.strip()):
        return None
    v = v.strip().replace("\\", "/")
    segs = [s for s in v.split("/") if s not in ("", ".")]
    return "/".join(segs) if segs and ".." not in segs else None


def _why(p):
    """항목 하나 → (고친 항목, None) | (None, 이유)."""
    if not isinstance(p, dict):
        return None, "객체가 아니에요"
    f = _rel(p.get("file"))
    if f is None:
        return None, "file 은 out 안 상대 경로여야 해요"
    repo = p.get("repo")
    if not isinstance(repo, str) or not _ABS.match(repo):
        return None, "%s: repo 는 절대 경로여야 해요" % f
    watch = p.get("watch")
    ws = [_rel(w) for w in watch] if isinstance(watch, list) else []
    if not ws or None in ws:
        return None, "%s: watch 는 저장소 안 상대 경로 목록이어야 해요" % f
    build = p.get("build")
    if not isinstance(build, list) or not build or not all(isinstance(a, str) and a for a in build):
        return None, "%s: build 는 글 목록(argv)이어야 해요" % f
    env = p.get("env")
    if env is not None and not (isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in env.items())):
        return None, "%s: env 는 {이름: 글} 이어야 해요" % f
    if not any(OUT_TOKEN in a for a in build) and not any(OUT_TOKEN in v for v in (env or {}).values()):
        return None, "%s: build 나 env 에 결과 경로 %s 이 없어요" % (f, OUT_TOKEN)
    post = p.get("post")
    if post is not None:
        ok = isinstance(post, list) and all(isinstance(s, dict) and len(s) == 1 and next(iter(s)) in POST_STEPS
                                            and isinstance(next(iter(s.values())), str) for s in post)
        if not ok:
            return None, "%s: post 단계는 %s 중 하나씩이어야 해요" % (f, " · ".join(POST_STEPS))
    stamp = p.get("stamp")
    out = {"file": f, "repo": repo, "watch": ws, "build": list(build), "env": dict(env or {}), "post": list(post or []),
           "stamp": stamp if isinstance(stamp, str) and stamp else None, "dirty": p.get("dirty") is True,
           "built_at": p.get("built_at") if isinstance(p.get("built_at"), str) else None}
    return out, None


def parse(data):
    """parts.json 객체 → (고른 부품 목록, '[hd] …' 경고 줄들). 파일 전체가 틀리면 ([], [한 줄])."""
    if not isinstance(data, dict) or data.get("version") != VERSION or not isinstance(data.get("parts"), list):
        return [], ["[hd] parts.json 모양이 아니에요({version: %d, parts: [...]}) — 부품을 보지 않아요" % VERSION]
    parts, warns = [], []
    for i, p in enumerate(data["parts"]):
        got, why = _why(p)
        if got is None:
            warns.append("[hd] parts.json %d번째 부품을 건너뛰어요: %s" % (i + 1, why))
        else:
            parts.append(got)
    return parts, warns


def row(part, current, dirty_now):
    """부품 + 지금 도장·지금 미커밋 여부 → 보고 줄 객체(--json · /api/app-parts)."""
    s = state(part, current)
    label = WORDS[s] + (" · " + DIRTY_LABEL if part.get("dirty") else "")
    return {"file": part["file"], "state": s, "stale": s == STALE, "stamp": part.get("stamp"), "current": current,
            "dirty": bool(part.get("dirty")), "dirty_now": dirty_now, "built_at": part.get("built_at"), "label": label}


def select(parts, sel):
    """sel 없음 · '*' = 전부 · out 상대 경로 · 파일 이름 · 확장자 뺀 이름 → 맞는 부품들."""
    if sel in (None, "", "*"):
        return list(parts)
    s = sel.strip().replace("\\", "/")
    names = [(p, p["file"].rsplit("/", 1)[-1]) for p in parts]
    return [p for p, n in names if p["file"] == s or n == s or n.rsplit(".", 1)[0] == s]


def apply_post(html, steps):
    """빌드 결과 글 + post 단계 → 고친 글. inject_before_body = 마지막 </body> 앞에(없으면 끝에), 이미 들어 있으면 그대로."""
    for step in steps or []:
        tag = step.get("inject_before_body")
        if not isinstance(tag, str) or not tag or tag in html:
            continue
        ends = list(_BODY_END.finditer(html))
        html = html[:ends[-1].start()] + tag + html[ends[-1].start():] if ends else html + tag
    return html


def record(data, file, stamp, dirty, built_at):
    """parts.json 객체 → 그 file 항목의 stamp · dirty · built_at 만 바꾼 새 객체(다른 항목 · 모르는 키 · 틀린 항목은 그대로)."""
    parts = []
    for p in data.get("parts", []):
        if isinstance(p, dict) and _rel(p.get("file")) == file:
            p = dict(p, stamp=stamp, dirty=bool(dirty), built_at=built_at)
        parts.append(p)
    return dict(data, parts=parts)


def stale_screens(deps, stale_files):
    """{화면 id: [끌어 쓰는 out 상대 경로(화면 파일 포함)]} + 낡은 부품 파일 집합 → 낡은 부품을 끌어 쓰는 화면 id(이름 차례)."""
    if not deps or not stale_files:
        return []
    return sorted(sid for sid, files in deps.items() if any(f in stale_files for f in files or []))


def warn_line(rows, target):
    """낡은 부품이 있으면 '[hd] …' 한 줄(다시 빌드하는 명령 포함) | None."""
    bad = [r["file"] for r in rows or [] if r.get("stale")]
    if not bad:
        return None
    return "[hd] 낡은 앱 부품 %d개: %s — 다시 빌드: hd parts --rebuild %s" % (len(bad), ", ".join(bad), target)
