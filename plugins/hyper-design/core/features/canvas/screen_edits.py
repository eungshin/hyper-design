"""Edge — 화면 편집 적용(out 안만 · 원본 남김 · 다시 빌드): apply_edits(편집 종류 → EDIT_OPS 파서 하나) · 화면 지우기(delete_screens) · 부품 견본 목록.

상태 없음(파일만 — 쓰기 한 번은 write_record._Writes). HTML 고치기는 html_edit, 판 글은 board_text, 카드 복제는 screen_copy, 줄 비우기는 board_rows(모두 순수).
새 편집 종류 = 파서 함수 하나 + EDIT_OPS 한 줄(apply_edits 는 고치지 않는다).
부르는 곳: history.History(apply · apply_async · delete) · builder.Builder(parts) · helper(예전 이름) · 테스트(apply_edits 를 바로).
오류 탐지: 받을 수 없는 편집은 그 하나만 failed{id, reason 한국어}(나머지는 씀) · 모두 거절이면 쓰지도 빌드하지도 않는다 · 빌드가 깨지면 되돌림(write_record).
"""
import json, pathlib, posixpath, shutil

import board_text as BT  # 판 글 고치기·지우기 계획(순수 Model, t51-9)
import screen_copy as SC  # 카드 바로 복제 계획(순수 Model, 51-6)
import specimen_parts  # 부품 견본 → 넣을 뼈대(순수 Model, task 49b)
from board_rows import emptied_groups
from html_edit import Tree, _link_to, _patch, _path_of, _relink, edit_html, edit_one
from out_io import _inside, _screen_files, _write_json, _write_text
from write_record import _Writes


POLICY_MAX_LINES, POLICY_MAX_CHARS = 50, 500



def _policies(v):
    """policies 편집 값 검사 — 글 목록, 50줄 이하, 줄마다 500자 이하. 앞뒤 빈칸을 자르고 빈 줄은 버린다. 아니면 ValueError(한국어)."""
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise ValueError("정책 줄은 글 목록이어야 해요")
    v = [x.strip() for x in v if x.strip()]
    if len(v) > POLICY_MAX_LINES:
        raise ValueError("정책 줄이 %d줄을 넘어요(%d줄)" % (POLICY_MAX_LINES, len(v)))
    for i, x in enumerate(v):
        if len(x) > POLICY_MAX_CHARS:
            raise ValueError("정책 %d번째 줄이 %d자를 넘어요" % (i + 1, POLICY_MAX_CHARS))
    return v



def _cannot(e):                                      # 표에 없는 종류·op = 터미널로(캔버스가 AI 요청으로 돌린다)
    return ValueError("바로 쓸 수 없는 편집(터미널로): %s/%s" % (e.get("edit"), e.get("op")))



def _op_text(e, ctx):                              # old = 고치기 전 화면에 보이던 글 — 스크립트가 그린 글이면 html_edit 이 스크립트 문자열을 고친다
    v = str(e.get("value", ""))
    return ("text", {"value": v, "old": e["old"]} if isinstance(e.get("old"), str) else v)



def _op_remove(e, ctx):
    return ("remove", None)



def _op_duplicate(e, ctx):                           # 블록(task 49a)
    return ("duplicate", None)



def _op_move(e, ctx):
    if e.get("op") in ("up", "down"):
        return ("move", e["op"])
    if e.get("op") == "to":                          # 끌기 한 번 = 쓰기 하나(49c) — to = 형제 요소 사이 새 자리(0부터)
        to = e.get("to")
        if not isinstance(to, int) or isinstance(to, bool):
            raise ValueError("옮길 자리(to)가 정수가 아니에요: %r" % (to,))
        return ("move", to)
    raise _cannot(e)



def _op_attr(e, ctx):                                # 속성 칸(task 49b) — op = 속성 이름, value = 새 값(허용 목록은 _attr_patch)
    return ("attr", {"name": str(e.get("op") or ""), "value": e.get("value")})



def _op_part(e, ctx):                                # 부품 넣기·바꾸기(task 49b) — value = 견본 key, 뼈대는 여기서 뽑는다(캔버스가 보낸 마크업은 쓰지 않음)
    if ctx["parts"] is None:
        ctx["parts"] = _parts_html(ctx["out"])
    if ctx["parts"] is None:
        raise ValueError("부품 견본(components.html)이 없어요")
    return (e.get("edit"), specimen_parts.markup(ctx["parts"], str(e.get("value") or "")))



def _op_link(e, ctx):
    if e.get("op") == "link" and e.get("to") in ctx["files"]:
        return ("link", e["to"])
    if e.get("op") in ("cut", "untrigger"):
        return ("cut", None)
    raise _cannot(e)



EDIT_OPS = {"text": _op_text, "remove": _op_remove, "duplicate": _op_duplicate, "move": _op_move, "attr": _op_attr,
            "insert": _op_part, "replace": _op_part, "link": _op_link}



def apply_edits(out, edits, stamp=None, build=None):
    out = pathlib.Path(out).resolve()
    sj = out / "screens.json"
    data = json.loads(sj.read_text(encoding="utf-8"))
    files = _screen_files(data)
    applied, failed, html_ops, json_ops, owner, paths = [], [], {}, [], {}, {}
    ctx = {"out": out, "files": files, "parts": None}   # parts = 부품 견본 글(넣기·바꾸기가 처음 부를 때 한 번 읽음)
    board = []                                       # 판 글(t51-9) — 화면이 아니라 screens.json story·people · decisions.json
    clones = []                                      # 카드 바로 복제(51-6) — screens.json 항목 + 화면 파일 하나 더
    for e in edits:
        eid, sid, kind = e.get("id"), e.get("screen"), e.get("edit")
        if kind == "board":
            board.append(e); continue
        if kind == "clone":
            clones.append(e); continue
        try:
            if sid not in files:
                raise ValueError("없는 화면: %s" % sid)
            if kind == "policies":                  # 정책 목록 통째로(task 31)
                json_ops.append((eid, sid, "policies", _policies(e.get("value"))))
                continue
            if kind in ("title", "purpose", "policy"):
                if kind == "policy" and not isinstance(e.get("index"), int):
                    raise ValueError("정책 줄 번호가 없어요")
                v = str(e.get("value", ""))
                if kind == "policy" and (e.get("op") == "delete" or not v.strip()):   # 비운 정책 줄 = 그 줄 지우기(#243)
                    kind = "policy-delete"
                json_ops.append((eid, sid, kind if kind not in ("policy", "policy-delete") else (kind, e["index"]), v))
                continue
            parse = EDIT_OPS.get(kind) if isinstance(kind, str) else None
            if parse is None:
                raise _cannot(e)
            op = parse(e, ctx)
            f = (out / files[sid])
            if not _inside(out, f) or not f.is_file():
                raise ValueError("out 밖이거나 없는 파일: %s" % files[sid])
            html_ops.setdefault(f, []).append((eid, e.get("path") or "", op[0], op[1])); owner[f] = sid
        except ValueError as err:
            failed.append({"id": eid, "reason": str(err)})
    if not html_ops and not json_ops and not board and not clones:
        return {"applied": applied, "failed": failed, "stamp": None, "changed": []}
    w, changed = _Writes(out, stamp, build), set()
    for f, ops in html_ops.items():                 # 한 화면 안에서 하나가 실패하면 그 하나만 빼고 다시
        src = f.read_text(encoding="utf-8")
        good = []
        for o in ops:                               # 앞서 된 것과 함께 되는지 — 겹치면 나중 것만 실패
            try:
                edit_html(src, [(g[1], g[2], g[3]) for g in good] + [(o[1], o[2], o[3])]); good.append(o)
            except ValueError as err:
                failed.append({"id": o[0], "reason": str(err)})
        if good:
            new = edit_html(src, [(o[1], o[2], o[3]) for o in good])
            if len(good) == 1 and good[0][2] not in ("link", "cut"):   # 요소 편집 하나 = 그 요소의 새 경로(캔버스가 쓴 뒤 다시 고른다, task 49b)
                at = edit_one(src, good[0][1], good[0][2], good[0][3])[1]
                if at:
                    paths[good[0][0]] = at
            w.keep(f); _write_text(f, new)
            applied += [o[0] for o in good]; changed.add(owner[f])
    sj_dirty = bool(json_ops)
    if board:                                        # 판 글: 하나씩 계획(앞 것 위에) — 거절은 그 하나만
        dj = out / "decisions.json"
        try:
            dec = json.loads(dj.read_text(encoding="utf-8")) if dj.is_file() else None
        except (OSError, ValueError):
            dec = None
        dec_dirty = False
        for e in board:
            try:
                r = BT.plan(data, dec, {"op": e.get("op"), "to": e.get("to"), "value": e.get("value")})
            except BT.BoardError as err:
                failed.append({"id": e.get("id"), "reason": str(err)}); continue
            if r["screens"] is not None:
                data, sj_dirty = r["screens"], True
            if r["decisions"] is not None:
                dec, dec_dirty = r["decisions"], True
            applied.append(e.get("id"))
        if dec_dirty:
            raw = dj.read_text(encoding="utf-8")
            w.keep(dj); _write_json(dj, dec, raw)
    for e in clones:                                 # 카드 복제: 하나씩 계획(앞 것 위에) — 거절은 그 하나만
        try:
            src = next((x for x in data.get("screens") or [] if isinstance(x, dict) and x.get("id") == e.get("screen")), None)
            local = bool(src) and not SC.is_app(SC.file_of(src))
            folder = posixpath.dirname(SC.file_of(src)) if local else ""
            d = out / folder                         # 새 이름이 그 폴더의 있는 파일을 덮지 않게(plan 의 files)
            have = {posixpath.join(folder, p.name) if folder else p.name for p in d.iterdir()} if local and _inside(out, d) and d.is_dir() else set()
            r = SC.plan(data, e.get("screen"), want=e.get("to"), title=e.get("value"), files=have)
            sf, df = out / r["src_file"], out / r["file"]
            if not _inside(out, sf) or not sf.is_file() or not _inside(out, df):
                raise SC.CopyError("out 밖이거나 없는 파일: %s" % r["src_file"], "missing")
        except SC.CopyError as err:
            failed.append({"id": e.get("id"), "reason": str(err)}); continue
        w.keep(df); df.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(sf, df)
        data, sj_dirty = r["data"], True
        applied.append(e.get("id")); changed.add(r["id"])
    if json_ops:
        by = {s["id"]: s for s in data["screens"]}
        drop = {}                                   # 화면 → 지울 정책 줄 번호(원래 번호) — 바꾸기를 다 한 뒤 큰 번호부터
        for eid, sid, kind, v in json_ops:
            if isinstance(kind, tuple):                 # 정책 줄 i
                pol = by[sid].setdefault("policies", [])
                if not 0 <= kind[1] < len(pol):
                    failed.append({"id": eid, "reason": "없는 정책 줄: %d" % kind[1]}); continue
                if kind[0] == "policy-delete":
                    drop.setdefault(sid, set()).add(kind[1])
                else:
                    pol[kind[1]] = v
            elif kind == "policies":                # 목록 통째로 — 앞선 옛 줄 지우기는 이 목록에 닿지 않는다
                by[sid]["policies"] = list(v); drop.pop(sid, None)
            else:
                by[sid][kind] = v
            applied.append(eid); changed.add(sid)
        for sid, idx in drop.items():
            for i in sorted(idx, reverse=True):
                del by[sid]["policies"][i]
    if sj_dirty:
        raw = sj.read_text(encoding="utf-8")
        w.keep(sj); _write_json(sj, data, raw)
    if not applied:                                 # 모두 거절(겹침·허용 밖 속성 등) — 쓴 것이 없으니 다시 빌드·기록도 없다
        return {"applied": [], "failed": failed, "stamp": None, "changed": [], "paths": {}}
    changed = sorted(changed)
    err = w.commit(changed)
    if err:                                         # 다시 빌드가 깨지면 원본으로 되돌렸다
        return {"applied": [], "failed": failed + [{"id": i, "reason": err} for i in applied], "stamp": None, "changed": []}
    return {"applied": applied, "failed": failed, "history": str(w.hist), "stamp": w.stamp, "changed": changed, "paths": paths}



def apply_token(out, name, value, stamp=None, build=None):
    """POST /api/token(R55) — out/tokens.css 첫 :root 의 선언 하나만 바꾼다(규칙 token_edit). 쓰기 한 번 = .hd-history 원본 + manifest → restore 로 되돌림.
    → {name, value(정리한 값), old, stamp, changed:[]} | {error, reason:'invalid'|'missing'}(쓰지 않음) | {error: BUILD_FAIL…}(되돌림)."""
    import token_edit as TE                          # 순수 Model(R55) — 이 함수만 쓴다
    out = pathlib.Path(out).resolve()
    f = out / "tokens.css"
    if not f.is_file():
        return {"error": "tokens.css 가 없어요", "reason": "missing"}
    raw = f.read_bytes().decode("utf-8")
    have = TE.decls(raw)
    v, why = TE.check(name, value, list(have))
    if why:
        return {"error": why, "reason": "invalid"}
    w = _Writes(out, stamp, build)
    w.keep(f)
    f.write_bytes(TE.rewrite(raw, name, v).encode("utf-8"))   # 줄 끝·인코딩 그대로(바이트로)
    err = w.commit([])
    if err:
        return {"error": err}
    return {"name": name, "value": v, "old": have[name], "stamp": w.stamp, "changed": [], "history": str(w.hist)}



def apply_component(out, selector, prop, index, frm, to, stamp=None, build=None):
    """POST /api/component(R55 phase C) — out/components.css 그 규칙·속성·자리의 var(--from) 하나만 var(--to) 로(규칙 component_edit, 같은 묶음 토큰만).
    쓰기 한 번 = .hd-history 원본 + manifest → restore 로 되돌림. → {selector, prop, index, from, to, stamp, changed:[]} | {error, reason:'invalid'|'missing'} | {error: BUILD_FAIL…}."""
    import component_edit as CE                      # 순수 Model(R55 phase C)
    import token_edit as TE
    out = pathlib.Path(out).resolve()
    f, tok = out / "components.css", out / "tokens.css"
    if not f.is_file() or not tok.is_file():
        return {"error": "components.css 또는 tokens.css 가 없어요", "reason": "missing"}
    raw = f.read_bytes().decode("utf-8")
    why = CE.check(raw, list(TE.decls(tok.read_text(encoding="utf-8"))), selector, prop, index, frm, to)
    if why:
        return {"error": why, "reason": "invalid"}
    w = _Writes(out, stamp, build)
    w.keep(f)
    f.write_bytes(CE.rewrite(raw, selector, prop, index, frm, to).encode("utf-8"))   # 줄 끝·인코딩 그대로(바이트로)
    err = w.commit([])
    if err:
        return {"error": err}
    return {"selector": CE.norm(selector), "prop": prop, "index": index, "from": frm, "to": to, "stamp": w.stamp, "changed": [], "history": str(w.hist)}


def component_slots(out, classes, tag=""):
    """POST /api/component-slots(R55 phase C, 읽기만) — 고른 요소(클래스·태그)를 겨누는 components.css 규칙과 바꿀 칸 + 고를 수 있는 토큰
    → {rules:[…component_edit.slots], tokens:{이름: {value, label, family}}} | {error, reason:'missing'|'invalid'}."""
    import component_edit as CE
    import token_edit as TE
    out = pathlib.Path(out).resolve()
    f, tok = out / "components.css", out / "tokens.css"
    if not f.is_file() or not tok.is_file():
        return {"error": "components.css 또는 tokens.css 가 없어요", "reason": "missing"}
    if not isinstance(classes, list) or not all(isinstance(c, str) for c in classes) or len(classes) > 40:
        return {"error": "classes 는 글 목록이에요", "reason": "invalid"}
    html = _parts_html(out) or ""
    rules = CE.slots(f.read_text(encoding="utf-8"), classes, str(tag or ""), CE.titles(html))
    toks = {n: {"value": v, "label": TE.label(n), "family": CE.family(n)} for n, v in TE.decls(tok.read_text(encoding="utf-8")).items() if CE.family(n)}
    return {"rules": rules, "tokens": toks}


def _parts_html(out):                              # 이 프로젝트의 부품 견본(Components 탭 = out/components.html) 글 | None
    f = pathlib.Path(out) / "components.html"
    return f.read_text(encoding="utf-8") if f.is_file() else None



def parts_of(out):
    """GET /api/parts — 부품 고르기 목록 {parts:[{key, title, ok}]}(ok = 뼈대를 뽑을 수 있음, 아니면 캔버스가 AI 요청으로)."""
    src = _parts_html(out)
    if src is None:
        return {"parts": [], "error": "부품 견본(components.html)이 없어요"}
    return {"parts": specimen_parts.parts(src)}



def delete_screens(out, ids, stamp=None, build=None):
    """화면 지우기(2.2 D3) — screens.json 에서 빼고(그리로 가는 branches 도), 화면 파일은 기록으로 옮기고, 다른 화면에서 오는 링크는 끊는다."""
    out = pathlib.Path(out).resolve()
    sj = out / "screens.json"
    raw = sj.read_text(encoding="utf-8")
    data = json.loads(raw)
    files = _screen_files(data)
    gone = [i for i in dict.fromkeys(ids) if i in files]
    failed = [{"id": i, "reason": "없는 화면: %s" % i} for i in ids if i not in files]
    if not gone:
        return {"deleted": [], "cut": [], "failed": failed, "stamp": None, "changed": []}
    w, cut, changed = _Writes(out, stamp, build), [], set(gone)
    for sid, rel in files.items():                  # 오는 링크 끊기(E10)
        f = out / rel
        if sid in gone or not _inside(out, f) or not f.is_file():
            continue
        src = f.read_text(encoding="utf-8")
        tree, patches = Tree(src), []
        for n in tree.walk():
            to = _link_to(n.attrs)
            if to in gone and to != sid:
                path = _path_of(n)
                patches.append(_relink(src, n, "cut", None, path)); cut.append({"screen": sid, "path": path, "to": to})
        if patches:
            w.keep(f); _write_text(f, _patch(src, patches)); changed.add(sid)
    kept = [s for s in data["screens"] if s["id"] not in gone]
    if "groups" in data:
        data["groups"] = emptied_groups(data["groups"], data["screens"], kept)
    data["screens"] = kept
    for s in data["screens"]:
        br = s.get("branches")
        if br and any(b.get("to") in gone for b in br):
            s["branches"] = [b for b in br if b.get("to") not in gone]; changed.add(s["id"])
    w.keep(sj); _write_json(sj, data, raw)
    for i in gone:
        f = out / files[i]
        if _inside(out, f) and f.is_file():
            w.move(f)
    changed = sorted(changed)
    err = w.commit(changed)
    if err:
        return {"deleted": [], "cut": [], "failed": failed + [{"id": i, "reason": err} for i in gone], "stamp": None, "changed": []}
    return {"deleted": gone, "cut": cut, "failed": failed, "stamp": w.stamp, "changed": changed}
