"""Session — 프로젝트(out) 하나의 서버 쪽(task 47-2 에서 helper.py 를 쪼갬). 파일 I/O 는 여기, 규칙은 hd_model · helper_model, HTML 고치기는 html_edit.

객체(책임 하나씩 — canvas contract.md 책임 게이트):
  ProjectSession — out 하나: 아래 부품을 만들고 잇는다 · 쓰기 자물쇠 하나 · 토큰 하나 · 페이지(index.html + window.__hdState)
  StateStore     — <out>/.hd-canvas.json: rev · 합쳐 쓰기(409) · 자물쇠 없는 읽기(#271) · 깨진 파일 옮기기
  History        — <out>/.hd-history: 쓰기마다 원본 + manifest(apply · delete) · 되살리기(restore, 409 changed-since) · 정리(prune)
  Queue          — 보낸 메모: 보낼 곳(agent · Paseo 목록 5초 캐시 · 저장소) · 요청문 대기열 파일 + 받는 곳 고르기(send — 접속 중이면 request.sent 이벤트,
                   아니면 AgentAdapter: adapters.py) · 에이전트 답(reply → agent.reply)
  AgentPresence  — 접속한 에이전트(presence.py, 47-5a): hello·맥박·임대 끝 = away·진행 한 줄
  Ticker         — 세션 시계 스레드 하나(47-5a): 1초마다 presence.sweep · 한 시간마다 Archive.sweep(완료 메모 보관)
  Busy           — AI 작업 덮개 state.busy(claim · release) + 화면 파일 지켜보기(1초 mtime → seq — /api/files · /api/watch)
  AiUndo         — 덮개 동안 AI 가 쓴 화면 = 기록 한 줄 'AI 반영 · <화면>' + 되살리기 stamp(48c, GET /api/ai-writes)
  Archive        — <out>/.hd-notes-archive.jsonl 완료 메모 보관(sweep = 서버가 고르고 옮김, 고르기 = memo_archive.py)
  Builder        — 다시 빌드(한 번에 하나 — 동기 apply 의 빌드와 뒤 빌드가 겹치지 않게) · hd-data · 부품 견본 목록
  EventBus       — 바뀐 것 알림(events.py, 47-4a): 부품이 바뀔 때 publish → SSE /events · Rebuilder(rebuild.py) = async apply 의 뒤 빌드
모듈 함수(apply_edits · restore · state_put …)는 helper.py 가 예전 이름 그대로 다시 내보낸다(테스트·hd 가 부름).
"""
import datetime, hashlib, json, os, pathlib, posixpath, secrets, shutil, subprocess, sys, threading, time, urllib.parse

import adapters as AD  # 받는 곳 고르기 · Paseo/Claude/None 어댑터(task 47-5a)
import board_text as BT  # 판 글 고치기·지우기 계획(순수 Model, t51-9)
import build_canvas
import code_stamp as CS  # 코드 도장 — 옛 코드로 구운 index.html 알아보기(순수 Model)
import events as EV  # 바뀐 것 알림(Model, task 47-4a)
import rebuild as RB  # async apply 뒤 빌드 차례(task 47-4a)
import memo_archive as MA  # 완료 메모 보관 고르기(순수 Model, task 47-5a)
import presence as PR  # 접속한 에이전트(task 47-5a)
import screen_copy as SC  # 카드 바로 복제 계획(순수 Model, 51-6)
import specimen_parts  # 부품 견본 → 넣을 뼈대(순수 Model, task 49b)
from html_edit import Tree, _link_to, _patch, _path_of, _relink, edit_html, edit_one

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hd"))
import hd_model  # noqa: E402  — 답·덮개 규칙(순수 Model) 하나를 CLI 와 같이 쓴다
import hd_projects  # noqa: E402  — out 안 규칙(inside)은 hd 와 같은 key 하나(#282)
import helper_model  # noqa: E402  — since·413 글·보관 줄·정리 고르기(순수 Model)

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE / "build_canvas.py"
from adapters import PASEO_DEFAULT, _paseo_args, _paseo_cmd  # noqa: E402,F401  — 예전 이름(helper 가 다시 내보냄)


# ---------------------------------------------------------------- 편집 적용(out 안만 · 원본 남김 · 다시 빌드)
def _inside(out, p):                                 # 규칙은 hd_projects.inside(key: 구분자·끝 '/'·드라이브 대소문자) 하나 — 여기서는 한 번 풀기만
    return hd_projects.inside(str(out), str(pathlib.Path(p).resolve()))


def _sha(p):                                         # 파일 sha256 | None(없음)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


BUILD_FAIL = "캔버스 다시 빌드 실패"                  # 답·이벤트가 다시 빌드 실패를 알아보는 글(앞부분)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: 자식 프로세스가 콘솔 창을 띄웠다 닫지 않게(창 없이 뜬 도우미에서 편집마다 깜빡임)


def NO_BUILD(out):                                   # async apply: 쓰기만 하고 빌드는 Rebuilder 가 뒤에서(47-4a)
    return subprocess.CompletedProcess([], 0, "", "")


def run_build(out, script=None):
    """다시 빌드 하나 — script(기본 작업 트리 build_canvas.py) 를 자식 프로세스로. CLI 도우미는 build_ref.py 를 넘긴다(helper.use_ref_build, #278)."""
    return subprocess.run([sys.executable, str(script or BUILD), str(out)], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=NO_WINDOW)


def _screen_files(data):
    return {s["id"]: s.get("file") or f"screens/{s['id']}.html" for s in data.get("screens", [])}


def _write_json(sj, data, raw):                      # 원래 들여쓰기·끝 줄바꿈을 따라 쓴다
    sj.write_text(json.dumps(data, ensure_ascii=False, indent=2 if '\n  "' in raw else None) + ("\n" if raw.endswith("\n") else ""),
                  encoding="utf-8", newline="")


class _Writes:
    """쓰기 한 번 — 원본을 .hd-history/<stamp>/<relpath> 에 남기고, 끝나면 manifest(쓴 뒤 해시)를 적는다."""
    def __init__(self, out, stamp=None, build=None):
        self.out, self.build = out, build or run_build
        self.stamp = stamp or datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.hist = out / ".hd-history" / self.stamp
        self.before = {}                             # relpath → 쓰기 전에 있었나

    def _dst(self, f):
        rel = f.relative_to(self.out).as_posix()
        dst = self.hist / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        return rel, dst

    def keep(self, f):                               # 쓰기 전 원본 복사(처음 한 번만)
        rel, dst = self._dst(f)
        if rel not in self.before:
            self.before[rel] = f.is_file()
            if self.before[rel]:
                shutil.copy2(f, dst)

    def move(self, f):                               # 지우기 = 기록으로 옮기기
        rel, dst = self._dst(f)
        if rel in self.before:
            f.unlink()
        else:
            self.before[rel] = True; shutil.move(str(f), str(dst))

    def undo(self):
        for rel, had in self.before.items():
            f = self.out / rel
            if had:
                shutil.copy2(self.hist / rel, f)
            elif f.exists():
                f.unlink()

    def commit(self, changed):
        """다시 빌드 → 성공이면 manifest 를 적고 None, 실패면 원본으로 되돌리고 이유."""
        r = self.build(self.out)
        if r.returncode != 0:
            self.undo(); self.build(self.out)
            return BUILD_FAIL + " — 되돌림: " + (r.stderr or "")[-300:]
        files = {rel: {"before": had, "after_sha": _sha(self.out / rel)} for rel, had in sorted(self.before.items())}
        (self.hist / "manifest.json").write_text(json.dumps({"files": files, "changed": changed}, ensure_ascii=False, indent=2), encoding="utf-8")
        prune(self.out)                              # 쓸 때마다 기록이 늘어나므로 그때 오래된 것을 정리(#281)
        return None


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


def apply_edits(out, edits, stamp=None, build=None):
    out = pathlib.Path(out).resolve()
    sj = out / "screens.json"
    data = json.loads(sj.read_text(encoding="utf-8"))
    files = _screen_files(data)
    applied, failed, html_ops, json_ops, owner, parts_html, paths = [], [], {}, [], {}, None, {}
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
            if kind == "text":
                op = ("text", str(e.get("value", "")))
            elif kind == "remove":
                op = ("remove", None)
            elif kind == "duplicate":                   # 블록(task 49a)
                op = ("duplicate", None)
            elif kind == "move" and e.get("op") in ("up", "down"):
                op = ("move", e["op"])
            elif kind == "move" and e.get("op") == "to":   # 끌기 한 번 = 쓰기 하나(49c) — to = 형제 요소 사이 새 자리(0부터)
                to = e.get("to")
                if not isinstance(to, int) or isinstance(to, bool):
                    raise ValueError("옮길 자리(to)가 정수가 아니에요: %r" % (to,))
                op = ("move", to)
            elif kind == "attr":                        # 속성 칸(task 49b) — op = 속성 이름, value = 새 값(허용 목록은 _attr_patch)
                op = ("attr", {"name": str(e.get("op") or ""), "value": e.get("value")})
            elif kind in ("insert", "replace"):         # 부품 넣기·바꾸기(task 49b) — value = 견본 key, 뼈대는 여기서 뽑는다(캔버스가 보낸 마크업은 쓰지 않음)
                if parts_html is None:
                    parts_html = _parts_html(out)
                if parts_html is None:
                    raise ValueError("부품 견본(components.html)이 없어요")
                op = (kind, specimen_parts.markup(parts_html, str(e.get("value") or "")))
            elif kind == "link" and e.get("op") == "link" and e.get("to") in files:
                op = ("link", e["to"])
            elif kind == "link" and e.get("op") in ("cut", "untrigger"):
                op = ("cut", None)
            else:
                raise ValueError("바로 쓸 수 없는 편집(터미널로): %s/%s" % (kind, e.get("op")))
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
            w.keep(f); f.write_text(new, encoding="utf-8", newline="")
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


def _parts_html(out):                                # 이 프로젝트의 부품 견본(Components 탭 = out/components.html) 글 | None
    f = pathlib.Path(out) / "components.html"
    return f.read_text(encoding="utf-8") if f.is_file() else None


def parts_of(out):
    """GET /api/parts — 부품 고르기 목록 {parts:[{key, title, ok}]}(ok = 뼈대를 뽑을 수 있음, 아니면 캔버스가 AI 요청으로)."""
    src = _parts_html(out)
    if src is None:
        return {"parts": [], "error": "부품 견본(components.html)이 없어요"}
    return {"parts": specimen_parts.parts(src)}


def emptied_groups(groups, before, after):
    """지우기로 비게 된 group 이름만 groups 에서 뺀다(51-1, Figma F18 빈 그룹은 없어진다) — 원래 빈 이름·순서는 그대로. groups 가 목록이 아니면 그대로."""
    if not isinstance(groups, list):
        return groups
    name = lambda s: s.get("group") or "기타"           # build_canvas.index_data 와 같은 이름
    had, has = {name(s) for s in before}, {name(s) for s in after}
    return [g for g in groups if not (g in had and g not in has)]


GROUP_MAX = 80                                       # 줄 이름 글자 수 한도(판 제목 한 줄)


class GroupError(ValueError):
    """줄(group) 요청을 받을 수 없다 — 한국어 이유 + reason('invalid' = 400 · 'missing' = 404)."""
    def __init__(self, msg, reason="invalid"):
        super().__init__(msg)
        self.reason = reason


def _gname(s):                                       # build_canvas.index_data 와 같은 이름(group 없음 = '기타')
    return s.get("group") or "기타"


def group_order(data):
    """줄 이름 차례 = build_canvas.index_data 와 같음(groups 먼저, 그다음 화면에만 있는 이름을 화면 차례로)."""
    names = [g for g in (data.get("groups") or []) if isinstance(g, str)]
    for s in data.get("screens") or []:
        if _gname(s) not in names:
            names.append(_gname(s))
    return list(dict.fromkeys(names))


def group_rows(data):                                # 판에 보이는 줄(화면이 하나라도 있는 이름) 차례
    has = {_gname(s) for s in data.get("screens") or []}
    return [g for g in group_order(data) if g in has]


def plan_group_rename(data, frm, to):
    """줄 이름 바꾸기 계획(51-4, Figma F16) — 순수. → {data(새 screens.json), screens(닿은 화면 id), to, same}.
    groups 의 그 항목과 그 줄 화면마다 group 을 함께 바꾼다. 화면에만 있던 이름(예: '기타')이면 지금 줄 차례를 groups 에 적어 자리를 지킨다."""
    names = group_order(data)
    if not isinstance(frm, str) or frm not in names:
        raise GroupError("없는 줄이에요: %s" % (frm,), "missing")
    to = str(to if to is not None else "").strip()
    if not to:
        raise GroupError("줄 이름이 비었어요")
    if len(to) > GROUP_MAX:
        raise GroupError("줄 이름이 %d자를 넘어요" % GROUP_MAX)
    new = json.loads(json.dumps(data))
    if to == frm:
        return {"data": new, "screens": [], "to": to, "same": True}
    if to in names:
        raise GroupError("같은 이름의 줄이 이미 있어요: %s" % to)
    groups = new.get("groups") if isinstance(new.get("groups"), list) else []
    if frm not in groups:
        groups = names
    new["groups"] = [to if g == frm else g for g in groups]
    hit = []
    for s in new.get("screens") or []:
        if _gname(s) == frm:
            s["group"] = to; hit.append(s["id"])
    return {"data": new, "screens": hit, "to": to, "same": False}


def plan_group_dissolve(data, name):
    """줄만 걷기 계획(51-4, Figma F17 · 사용자 결정 ①) — 순수. 그 줄 화면을 위 줄(첫 줄이면 아래 줄)로 옮기고 groups 에서 이름을 뺀다.
    옮긴 화면은 위 줄 화면 뒤(아래 줄이면 앞)에 놓아 빌드가 같은 차례로 그린다. → {data, screens, into, where('above'|'below')}."""
    rows = group_rows(data)
    if not isinstance(name, str) or name not in rows:
        raise GroupError("없는 줄이에요: %s" % (name,), "missing")
    if len(rows) < 2:
        raise GroupError("줄이 하나뿐이라 걷을 수 없어요")
    i = rows.index(name)
    into, where = (rows[i - 1], "above") if i > 0 else (rows[1], "below")
    new = json.loads(json.dumps(data))
    screens = new.get("screens") or []
    moved = [s for s in screens if _gname(s) == name]
    rest = [s for s in screens if _gname(s) != name]
    for s in moved:
        s["group"] = into
    at = [k for k, s in enumerate(rest) if _gname(s) == into]
    k = at[-1] + 1 if where == "above" else at[0]
    new["screens"] = rest[:k] + moved + rest[k:]
    if isinstance(new.get("groups"), list):
        new["groups"] = [g for g in new["groups"] if g != name]
    return {"data": new, "screens": [s["id"] for s in moved], "into": into, "where": where}


def _group_write(out, plan, stamp=None, build=None):
    """줄 계획 하나 → screens.json 쓰기 한 번(원본 + manifest = 되돌리기 한 번). 바뀐 화면 파일은 없다(changed = [])."""
    out = pathlib.Path(out).resolve()
    sj = out / "screens.json"
    raw = sj.read_text(encoding="utf-8")
    try:
        p = plan(json.loads(raw))
    except GroupError as e:
        return {"error": str(e), "reason": e.reason}
    res = {k: v for k, v in p.items() if k not in ("data", "same", "to")}
    if p.get("same"):
        return dict(res, group=p["to"], stamp=None, changed=[])
    w = _Writes(out, stamp, build)
    w.keep(sj); _write_json(sj, p["data"], raw)
    err = w.commit([])
    if err:
        return {"error": err}
    if "to" in p:
        res["group"] = p["to"]
    return dict(res, stamp=w.stamp, changed=[])


def group_rename(out, frm, to, stamp=None, build=None):
    """POST /api/group-rename {from, to} → {group, screens, stamp, changed:[]} | {error, reason}."""
    return _group_write(out, lambda d: plan_group_rename(d, frm, to), stamp, build)


def group_dissolve(out, name, stamp=None, build=None):
    """POST /api/group-dissolve {name} → {group, into, where, screens, stamp, changed:[]} | {error, reason}."""
    r = _group_write(out, lambda d: plan_group_dissolve(d, name), stamp, build)
    if "stamp" in r:
        r["group"] = name
    return r


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
            w.keep(f); f.write_text(_patch(src, patches), encoding="utf-8", newline=""); changed.add(sid)
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


REVERTED = "reverted.json"                            # .hd-history/<stamp>/ 묘비 — 뒤 빌드가 깨져 서버가 되돌린 쓰기(47-5a)


def tombstone(out, stamp, ids, reason=None):
    """되돌린 쓰기의 기록을 묘비로: 원본·manifest 를 지우고 reverted.json {ids, reason} 만 남긴다(그 stamp 되살리기 = 200 reverted, 404 아님)."""
    hist = pathlib.Path(out) / ".hd-history" / stamp
    shutil.rmtree(hist, ignore_errors=True)
    try:
        hist.mkdir(parents=True, exist_ok=True)
        (hist / REVERTED).write_text(json.dumps({"ids": list(ids), "reason": reason}, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        print("[hd] 되돌린 쓰기의 표시를 쓰지 못했어요(%s): %s — 그 되돌리기 줄은 '없는 기록'이 돼요" % (e, stamp), file=sys.stderr, flush=True)


def restore(out, stamp, build=None, keep=False):
    """쓰기 하나 되살리기(2.2 D4) — manifest 의 파일이 쓴 직후 그대로일 때만. 아니면 아무것도 안 바꾸고 reason:'changed-since'.
    keep = 되살리기 전 지금 파일을 새 기록으로 남기고 답에 redo(그 stamp) — 그 stamp 를 되살리면 다시 하기(48c AI 반영 줄)."""
    out = pathlib.Path(out).resolve()
    root = out / ".hd-history"
    hist = root / str(stamp or "")
    man = hist / "manifest.json"
    if stamp and hist.resolve().parent == root.resolve() and not man.is_file() and (hist / REVERTED).is_file():
        return {"restored": [], "changed": [], "reverted": True}   # 뒤 빌드가 깨져 이미 되돌린 쓰기(47-5a 묘비) — 되돌릴 것이 없다
    if not stamp or hist.resolve().parent != root.resolve() or not man.is_file():
        return {"error": "없는 기록: %s" % stamp, "reason": "missing"}
    m = json.loads(man.read_text(encoding="utf-8"))
    files = m.get("files") or {}
    for rel, info in files.items():
        f = out / rel
        if not _inside(out, f):
            return {"error": "out 밖 경로: %s" % rel}
        if _sha(f) != info.get("after_sha"):
            return {"error": "그 뒤에 파일이 바뀌어 되돌릴 수 없어요: %s" % rel, "reason": "changed-since", "path": rel}
    now = {rel: (out / rel).read_bytes() if (out / rel).is_file() else None for rel in files}
    w = _Writes(out, build=build) if keep else None
    if w is not None:
        for rel in files:
            w.keep(out / rel)
    for rel, info in files.items():
        f = out / rel
        if info.get("before"):
            f.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(hist / rel, f)
        elif f.exists():
            f.unlink()
    build = build or run_build
    r = build(out)
    if r.returncode != 0:                           # 다시 빌드가 깨지면 되살리기 전으로
        for rel, b in now.items():
            if b is None:
                (out / rel).unlink(missing_ok=True)
            else:
                (out / rel).write_bytes(b)
        build(out)
        if w is not None:
            shutil.rmtree(w.hist, ignore_errors=True)
        return {"error": BUILD_FAIL + " — 되돌림: " + (r.stderr or "")[-300:]}
    res = {"restored": sorted(files), "changed": m.get("changed") or []}
    if w is not None:                                # 다시 하기 = 이 기록을 되살리기(같은 규칙: 그 뒤 파일이 바뀌면 409)
        w.hist.mkdir(parents=True, exist_ok=True)
        man = {rel: {"before": had, "after_sha": _sha(out / rel)} for rel, had in sorted(w.before.items())}
        (w.hist / "manifest.json").write_text(json.dumps({"files": man, "changed": res["changed"], "by": m.get("by")}, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
        res["redo"] = w.stamp
    return res


def queue_file(out, text):
    """요청문 대기열 파일 <out>/.hd-queue/<stamp>.txt 하나(늘 씀 — 어디로 보내든 기록) → 경로."""
    q = pathlib.Path(out).resolve() / ".hd-queue"
    q.mkdir(exist_ok=True)
    p = q / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".txt")
    p.write_text(text, encoding="utf-8")
    return p


def mark_sent(p):                                    # 보냄 표시 — 7일 뒤 정리(#281). 어댑터(paseo·claude)가 받았을 때만
    try:
        p.with_suffix(".sent").write_text("", encoding="utf-8")
    except OSError as e:
        print("[hd] 대기열 보냄 표시를 쓰지 못했어요(%s): %s" % (e, p), file=sys.stderr, flush=True)


def forward(out, text, agent=None, paseo=None):
    """결정형이 아닌 메모 → 터미널(옛 이름 — 받는 곳 고르기는 Queue.send). 늘 대기열 파일에 쓰고, Paseo 에이전트가 있으면 PaseoAdapter(paseo send)로 넘긴다."""
    p = queue_file(out, text)
    if agent and AD.PaseoAdapter(lambda: _paseo_cmd(paseo)).send(p, text, agent)[0]:
        mark_sent(p)
        return {"via": "paseo", "agent": agent, "path": str(p)}
    return {"via": "queue", "path": str(p)}


# ---------------------------------------------------------------- 보낼 곳 고르기(#214): Paseo 에이전트 목록 · 프로젝트 저장소
AGENTS_TTL = 5.0                                     # GET /api/agents 답을 이만큼(초) 다시 쓴다 — 메뉴를 열 때마다 paseo 를 띄우지 않게
NO_PASEO = "Paseo 를 찾을 수 없어요"


def list_agents(paseo=None):
    """`paseo ls -g --json`(읽기만) → {agents:[{id, name, status, cwd, provider}]} | {agents:[], error:한국어}.
    보관(archived)된 것은 뺀다. 출력은 바이트로 받아 UTF-8 로 푼다(Windows 기본 코드 페이지로 풀면 한글 이름이 깨진다)."""
    cmd = _paseo_cmd(paseo)
    if not cmd or (("/" in cmd or "\\" in cmd) and not pathlib.Path(cmd).exists()):
        return {"agents": [], "error": NO_PASEO}
    try:
        r = subprocess.run(_paseo_args(cmd, ["ls", "-g", "--json"]), capture_output=True, timeout=30, creationflags=NO_WINDOW,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8", NO_COLOR="1"))
    except FileNotFoundError:
        return {"agents": [], "error": NO_PASEO}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"agents": [], "error": "Paseo 목록을 읽지 못했어요: %s" % e}
    if r.returncode != 0:
        why = r.stderr.decode("utf-8", "replace").strip().splitlines()
        return {"agents": [], "error": "Paseo 목록을 읽지 못했어요" + (": " + why[-1][:200] if why else " (종료 코드 %d)" % r.returncode)}
    try:
        rows = json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        return {"agents": [], "error": "Paseo 목록이 JSON 이 아니에요"}
    if not isinstance(rows, list):
        return {"agents": [], "error": "Paseo 목록이 목록이 아니에요"}
    agents = []
    for a in rows:
        if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"]:
            continue
        if a.get("archived") or a.get("status") == "archived" or a.get("archivedAt"):
            continue
        agents.append({k: (a.get(k) if isinstance(a.get(k), str) else None) for k in ("id", "name", "status", "cwd", "provider")})
    return {"agents": agents}


def project_repo(out):
    """이 캔버스의 저장소 뿌리 — 앱 프로젝트면 app.json 의 repo, 아니면 out 위로 처음 만나는 .git 이 있는 폴더. 없으면 None."""
    out = pathlib.Path(out).resolve()
    try:
        app = json.loads((out / "app.json").read_text(encoding="utf-8"))
        if isinstance(app, dict) and isinstance(app.get("repo"), str) and app["repo"]:
            return str(pathlib.Path(app["repo"]))
    except (OSError, ValueError):
        pass                                          # app.json 이 없거나 깨짐 = 정적 프로젝트로 본다
    for d in [out] + list(out.parents):
        if (d / ".git").exists():
            return str(d)
    return None


def agents_get(srv, paseo, now=None, auto=False):
    """GET /api/agents[?auto=1] → {agents, current, repo, error?}. paseo 목록은 AGENTS_TTL 동안 다시 쓴다(current 는 늘 지금 값).
    auto = 캔버스가 열 때 자동으로 고를지 묻는 것 — 이미 붙어 있거나 저장소를 모르면 paseo 를 띄우지 않고 {agents:[], skipped:true}."""
    if auto and (srv.agent or not srv.repo):
        return {"agents": [], "current": srv.agent, "repo": srv.repo, "skipped": True}
    t = time.monotonic() if now is None else now
    with srv.agents_lock:
        hit = srv.agents_cache
        if hit is None or t - hit[0] >= AGENTS_TTL:
            hit = srv.agents_cache = (t, list_agents(paseo))
    connected = srv.presence.list()["agents"] if getattr(srv, "presence", None) is not None else []   # 47-5a: 접속한 에이전트(AgentPresence)
    return dict(hit[1], current=srv.agent, repo=srv.repo, connected=connected)


def watch(out, files):
    """화면 파일 바뀐 시각 보기(Q2b) — files = out 기준 상대 경로 목록 → {mtimes:{경로: st_mtime | None}}. 없거나 out 밖이면 None."""
    out = pathlib.Path(out).resolve()
    mtimes = {}
    if not isinstance(files, list):
        return {"mtimes": mtimes}
    for f in files:
        if not isinstance(f, str):
            continue
        try:
            p = out / f
            mtimes[f] = p.stat().st_mtime if _inside(out, p) and p.is_file() else None
        except (OSError, ValueError):
            mtimes[f] = None
    return {"mtimes": mtimes}


# ---------------------------------------------------------------- 프로젝트 상태 파일(#228): <out>/.hd-canvas.json 이 캔버스 프로젝트별 키의 진실 원천
STATE_FILE = ".hd-canvas.json"
STATE_MAX = 2 * 1024 * 1024                          # PUT 본문 한도(넘으면 413)


def _state_ok(doc):
    return isinstance(doc, dict) and type(doc.get("rev")) is int and doc["rev"] >= 0 and isinstance(doc.get("state"), dict)


def state_load(out):
    """상태 파일 → {rev, state}. 없으면 {rev:0, state:{}}. 깨졌으면 .hd-canvas.json.corrupt-<시각> 으로 옮기고 한 줄 남긴 뒤 빈 상태(도우미는 멈추지 않는다)."""
    p = pathlib.Path(out) / STATE_FILE
    if not p.is_file():
        return {"rev": 0, "state": {}}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = None
    if _state_ok(doc):
        return {"rev": doc["rev"], "state": doc["state"]}
    bad = p.with_name(STATE_FILE + ".corrupt-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    try:
        os.replace(p, bad)
        print("[hd] 깨진 상태 파일을 옮기고 빈 상태로 시작해요: " + bad.name, file=sys.stderr, flush=True)
    except OSError as e:
        print("[hd] 깨진 상태 파일을 옮기지 못했어요(빈 상태로 시작): %s" % e, file=sys.stderr, flush=True)
    return {"rev": 0, "state": {}}


def _state_write(out, doc):                          # 같은 폴더 임시 파일 → os.replace(원자적), 바로 앞 것 하나는 .bak
    p = pathlib.Path(out) / STATE_FILE
    tmp = p.with_name(STATE_FILE + ".tmp-%d" % os.getpid())
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    if p.is_file():
        shutil.copy2(p, p.with_name(STATE_FILE + ".bak"))
    _replace(tmp, p)


def _replace(tmp, p):
    for i in range(REPLACE_TRIES):                   # 읽기는 자물쇠 없이 한다(#271) — Windows 는 읽는 중인 파일을 바꾸지 못해 잠깐 기다렸다 다시
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            if i == REPLACE_TRIES - 1:
                raise
            time.sleep(0.02)


REPLACE_TRIES = 25                                   # 0.02초씩 — 읽기 하나는 수 ms


def state_peek(out):
    """자물쇠 없는 읽기(GET /api/state · index.html 스냅숏, #271) → {rev, state} | None(못 읽음·깨짐 — 그때만 자물쇠 안에서 state_load).
    쓰기는 임시 파일 + os.replace 라 반쯤 쓴 파일을 읽을 일은 없다. 깨진 파일을 옮기는 일(쓰기)은 하지 않는다."""
    p = pathlib.Path(out) / STATE_FILE
    for _ in range(REPLACE_TRIES):
        if not p.is_file():
            return {"rev": 0, "state": {}}
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except PermissionError:                       # Windows: 바로 그 순간 os.replace 중
            time.sleep(0.02); continue
        except (OSError, ValueError):
            return None
        return {"rev": doc["rev"], "state": doc["state"]} if _state_ok(doc) else None
    return None


def state_put(out, body):
    """PUT 본문 {rev, state:{이름: 값 | null(지움)}} → (code, 답). rev 가 파일과 같을 때만 합쳐 rev+1 로 쓴다 · 다르면 409 {rev, state}."""
    if not isinstance(body, dict) or type(body.get("rev")) is not int or not isinstance(body.get("state"), dict):
        return 400, {"error": "{rev: 정수, state: {}} 가 아니에요"}
    cur = state_load(out)
    if body["rev"] != cur["rev"]:
        return 409, cur
    state = dict(cur["state"])
    for k, v in body["state"].items():
        if v is None:
            state.pop(k, None)
        else:
            state[k] = v
    return 200, {"rev": _state_save(out, cur["rev"] + 1, state)}


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _state_save(out, rev, state):
    _state_write(out, {"version": 1, "rev": rev, "updated": _now(), "state": state})
    return rev


def reply_post(out, body):
    """POST /api/reply 본문 {note: id | {screen, no}, reply} → (code, 답). 최신 상태 파일의 그 메모 replies 에 붙이고 rev+1."""
    if not isinstance(body, dict) or not isinstance(body.get("reply"), dict):
        return 400, {"error": "{note, reply: {kind, …}} 가 아니에요", "errors": ["reply: 객체가 아니에요"]}
    ref = body.get("note")
    if isinstance(ref, dict):
        if not isinstance(ref.get("screen"), str) or type(ref.get("no")) is not int:
            return 400, {"error": "note: {screen: 글, no: 정수} 또는 메모 id", "errors": ["note: {screen, no} 모양이 아니에요"]}
    elif not isinstance(ref, str) or not ref:
        return 400, {"error": "note: 메모 id 또는 {screen, no}", "errors": ["note: 없어요"]}
    cur = state_load(out)
    notes = cur["state"].get("notes")
    notes = notes if isinstance(notes, list) else []
    i = hd_model.find(notes, ref, cur["state"].get("note-seq"))
    if i is None:
        return 404, {"error": "없는 메모: %s" % (ref if isinstance(ref, str) else "%s#%s" % (ref["screen"], ref["no"]))}
    note = notes[i]
    if not note.get("sent"):
        return 400, {"error": "note: 아직 보내지 않은 메모(draft)에는 답하지 않아요", "errors": ["note: 보내지 않은 메모"]}
    try:
        known = {s["id"] for s in json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")).get("screens", [])}
    except (OSError, ValueError, KeyError, TypeError):
        known = None                                  # screens.json 을 못 읽으면 화면 id 는 모양만 본다
    errs = hd_model.check_reply(body["reply"], note.get("intent"), agent=True, known_screens=known)
    if errs:
        return 400, {"error": "; ".join(errs), "errors": errs}
    note = dict(note, replies=hd_model.replies(note) + [hd_model.stamp(body["reply"], _now())])
    notes = notes[:i] + [note] + notes[i + 1:]
    rev = _state_save(out, cur["rev"] + 1, dict(cur["state"], notes=notes))
    return 200, {"rev": rev, "status": hd_model.status(note), "note": note.get("id"), "screen": note.get("screen")}


def state_inject(out, lock=None):                    # 페이지에 끼워 넣을 동기 스냅숏(window.__hdState) — </script> 가 끊지 않게 < 를 이스케이프
    snap = state_peek(out)                           # 자물쇠 없이(#271) — 깨졌을 때만 자물쇠 안에서 state_load(옮기기)
    if snap is None:
        with lock or threading.Lock():
            snap = state_load(out)
    return "<script>window.__hdState=%s;</script>" % json.dumps(snap, ensure_ascii=False).replace("<", "\\u003c")


def claim_post(out, body, now_ms=None):
    """POST /api/claim 본문 {screen, by?, note?} → (code, 답). 최신 상태 파일 state.busy 에 cli 덮개를 넣고 rev+1."""
    if not isinstance(body, dict):
        return 400, {"error": "{screen, by?, note?} 가 아니에요"}
    sid, by, note = body.get("screen"), body.get("by"), body.get("note")
    err = hd_model.claim_error(sid, by, note)
    if err:
        return 400, {"error": err}
    try:
        files = _screen_files(json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return 500, {"error": "screens.json 을 읽지 못했어요: %s" % e}
    if sid not in files:
        return 404, {"error": "없는 화면: %s" % sid}
    f = pathlib.Path(out).resolve() / files[sid]
    mtime = f.stat().st_mtime if _inside(pathlib.Path(out).resolve(), f) and f.is_file() else None
    cur = state_load(out)
    busy, warns = hd_model.claim(cur["state"].get("busy"), sid, files[sid], int(now_ms if now_ms is not None else datetime.datetime.now().timestamp() * 1000),
                                 mtime, by, note)
    for w in warns:
        print(w, file=sys.stderr, flush=True)
    rev = _state_save(out, cur["rev"] + 1, dict(cur["state"], busy=busy))
    return 200, {"rev": rev, "screen": sid, "file": files[sid]}


def release_post(out, body):
    """POST /api/release 본문 {screen} → (code, 답). 덮개가 있으면 걷고 rev+1, 없으면 released false(쓰지 않음)."""
    if not isinstance(body, dict) or not isinstance(body.get("screen"), str) or not body["screen"]:
        return 400, {"error": "screen: 화면 id 가 없어요"}
    cur = state_load(out)
    busy, gone, warns = hd_model.release(cur["state"].get("busy"), body["screen"])
    for w in warns:
        print(w, file=sys.stderr, flush=True)
    if not gone:
        return 200, {"rev": cur["rev"], "released": False}
    return 200, {"rev": _state_save(out, cur["rev"] + 1, dict(cur["state"], busy=busy)), "released": True}


# ---------------------------------------------------------------- 화면 파일 지켜보기(#254): 1초마다 mtime → 바뀐 화면마다 seq
WATCH_EVERY = 1.0


class FileWatch:
    """화면 → mtime 을 받아 바뀐 화면을 seq 로 적는다. tick 은 I/O 가 없다(unit 테스트) — 파일을 보는 일은 scan()."""
    def __init__(self):
        self.seq, self.last, self.at = 0, None, {}       # at: 화면 → 마지막으로 바뀐 seq
        self._lock = threading.Lock()

    def tick(self, mtimes):
        """mtimes = {화면: mtime|None} → 이번에 바뀐 화면 목록(처음 = 기준만, []). 생김·없어짐·시각 바뀜 = 바뀜."""
        with self._lock:
            prev, self.last = self.last, dict(mtimes)
            if prev is None:
                return []
            changed = sorted(k for k in set(prev) | set(mtimes) if prev.get(k) != mtimes.get(k) and k in mtimes)
            if changed:
                self.seq += 1
                for k in changed:
                    self.at[k] = self.seq
            return changed

    def absorb(self, mtimes):
        """도우미가 스스로 쓴 뒤(apply·delete·restore) — 지금 시각을 기준으로만 삼고 알리지 않는다(캔버스가 이미 그 카드를 다시 싣는다)."""
        with self._lock:
            self.last = dict(mtimes)

    def changes(self, since):
        """since 보다 뒤에 바뀐 화면 → {seq, changed}. since < 0 = 기준만."""
        with self._lock:
            if since is None or since < 0:
                return {"seq": self.seq, "changed": []}
            return {"seq": self.seq, "changed": sorted(k for k, s in self.at.items() if s > since)}


def scan(out, cache):
    """screens.json 에 적힌 화면 파일(out 안만) → {화면: mtime|None} | None(screens.json 을 못 읽음 — [hd] 한 줄). cache = {'sj': (mtime, files)} — screens.json 이 바뀔 때만 다시 읽는다."""
    out = pathlib.Path(out)
    sj = out / "screens.json"
    try:
        m = sj.stat().st_mtime
        if cache.get("sj", (None,))[0] != m:
            cache["sj"] = (m, _screen_files(json.loads(sj.read_text(encoding="utf-8"))))
    except (OSError, ValueError, KeyError, TypeError) as e:
        if not cache.get("warned"):
            print("[hd] 화면 지켜보기: screens.json 을 읽지 못했어요(%s)" % e, file=sys.stderr, flush=True)
            cache["warned"] = True
        return None                                   # 이번 차례는 건너뜀(쓰는 중인 screens.json 이 모든 카드를 '바뀜'으로 만들지 않게)
    cache["warned"] = False
    res = {}
    for sid, rel in cache["sj"][1].items():
        p = out / rel
        try:
            res[sid] = p.stat().st_mtime if _inside(out, p) and p.is_file() else None
        except (OSError, ValueError):
            res[sid] = None
    return res


# ---------------------------------------------------------------- 정리(#281): 오래된 기록·처리된 대기열 — 고르기는 helper_model, 여기는 지우기만
def _stamp(dt):
    return dt.strftime("%Y%m%d-%H%M%S-%f")


def prune(out, now=None):
    """<out>/.hd-history/<stamp>/ 가 가장 새 200개 밖이면서 30일보다 오래됐으면 지우고, .hd-queue 의 보냄·걷힘 표시가 붙은 7일 넘은 파일을 지운다.
    그 밖(시각 이름이 아닌 것 — fix 스킬의 fix-components.css 등)은 손대지 않는다. 실패는 [hd] 한 줄(도우미는 멈추지 않음) → {history, queue} 지운 수."""
    out, now = pathlib.Path(out), now or datetime.datetime.now()
    done = {"history": 0, "queue": 0}
    hist, q = out / ".hd-history", out / ".hd-queue"
    try:
        if hist.is_dir():
            names = [d.name for d in hist.iterdir() if d.is_dir()]
            for n in helper_model.history_prune(names, _stamp(now - datetime.timedelta(days=helper_model.HISTORY_DAYS))):
                shutil.rmtree(hist / n); done["history"] += 1
        if q.is_dir():
            names = [f.name for f in q.iterdir() if f.is_file()]
            for n in helper_model.queue_prune(names, _stamp(now - datetime.timedelta(days=helper_model.QUEUE_DAYS))):
                (q / n).unlink(); done["queue"] += 1
    except OSError as e:
        print("[hd] 오래된 기록·대기열을 정리하지 못했어요(%s) — 그대로 둬요" % e, file=sys.stderr, flush=True)
    return done


# ---------------------------------------------------------------- 완료 메모 보관(#273): <out>/.hd-notes-archive.jsonl — 한 줄 = 메모 하나
ARCHIVE_FILE = ".hd-notes-archive.jsonl"


def archive_post(out, body):
    """POST /api/archive 본문 {notes:[…]} → (code, 답). 줄마다 메모 하나를 덧붙인다(있던 것 + 새 줄을 임시 파일에 쓰고 os.replace — 반쯤 쓴 파일이 남지 않게). 쓰기 자물쇠 안에서 부른다."""
    p = pathlib.Path(out) / ARCHIVE_FILE
    old = p.read_bytes() if p.is_file() else b""
    have = {n.get("id") for n in helper_model.archive_notes(old.decode("utf-8", errors="replace").splitlines(), cap=10 ** 9)[0]}
    lines, err = helper_model.archive_lines(body, have)
    if err:
        return 400, {"error": err}
    if lines:
        if old and not old.endswith(b"\n"):
            old += b"\n"
        tmp = p.with_name(ARCHIVE_FILE + ".tmp-%d" % os.getpid())
        tmp.write_bytes(old + "".join(x + "\n" for x in lines).encode("utf-8"))
        _replace(tmp, p)
    return 200, {"ok": True, "count": len(lines)}


def archive_get(out):
    """GET /api/archive → {notes:[…]} — 마지막 2000 줄, 새것이 뒤. 깨진 줄은 건너뛰고 [hd] 한 줄."""
    p = pathlib.Path(out) / ARCHIVE_FILE
    if not p.is_file():
        return {"notes": []}
    notes, bad = helper_model.archive_notes(p.read_text(encoding="utf-8", errors="replace").splitlines())
    if bad:
        print("[hd] 보관 파일에 깨진 줄 %d개를 건너뛰었어요: %s" % (bad, p), file=sys.stderr, flush=True)
    return {"notes": notes}


def keypath(out):                                    # file:// 로 열었을 때의 location.pathname — 캔버스 저장 키를 같게
    return urllib.parse.urlparse((pathlib.Path(out).resolve() / "index.html").as_uri()).path


# ---------------------------------------------------------------- 객체(task 47-2): out 하나 = ProjectSession 하나
def _code(r):                                        # restore·apply·delete 답 → 상태 코드(이유 = 409·404, 그 밖 오류 = 500)
    return {"changed-since": 409, "missing": 404, "invalid": 400}.get(r.get("reason"), 500 if "error" in r else 200)


def _emit(bus, type_, **data):                       # 버스가 없으면(부품만 따로 쓰는 테스트) 알리지 않는다
    return bus.publish(type_, **data) if bus is not None else None


def _str(v):
    return v if isinstance(v, str) else None


class Builder:
    """다시 빌드 · hd-data · 부품 목록 — out 하나. run(out) = 빌드 하나(기본 작업 트리, CLI 도우미는 build_ref — helper 가 넘긴다)."""

    def __init__(self, out, run=None):
        self.out, self._run, self.lock = out, run or run_build, threading.Lock()

    def run(self, out):                              # 빌드 하나씩(동기 apply 의 빌드 · 뒤 빌드 · 되돌린 뒤 빌드가 같은 index.html 을 쓴다)
        with self.lock:
            return self._run(out)

    def build(self):
        return self.run(self.out)

    def data(self):
        return build_canvas.index_data(self.out, json.loads((self.out / "screens.json").read_text(encoding="utf-8")))

    def parts(self):
        return parts_of(self.out)


class StateStore:
    """<out>/.hd-canvas.json — 읽기는 자물쇠 없이(#271, 깨졌을 때만 자물쇠 안에서 옮김), 쓰기(PUT 합치기·rev+1)는 세션 자물쇠 안에서."""

    def __init__(self, out, lock, bus=None):
        self.out, self.lock, self.bus = out, lock, bus

    def load(self):
        return state_load(self.out)

    def snapshot(self):
        snap = state_peek(self.out)
        if snap is None:
            with self.lock:
                snap = state_load(self.out)
        return snap

    def get(self, since):
        return helper_model.state_reply(self.snapshot(), since)   # ?since=rev 가 같으면 몸통 없이(#273 — 2초 읽기)

    def put(self, body):
        with self.lock:                              # rev 비교와 쓰기 사이에 끼어들지 않게
            code, res = state_put(self.out, body)
            if code == 200:
                _emit(self.bus, "notes.changed", rev=res["rev"])
            return code, res

    def inject(self):
        return state_inject(self.out, self.lock)


class History:
    """<out>/.hd-history — 화면 파일 쓰기(apply · delete)마다 원본 + manifest, 되살리기(restore). 쓰기는 하나씩, 끝나면 on_written(지켜보기 기준 옮김).
    쓰기마다 screen.written(by human) · 다시 빌드가 깨지면 build.failed. apply_async = 쓰기만 하고 바로 답, 빌드는 rebuilder(47-4a)."""

    def __init__(self, out, lock, builder, on_written=None, bus=None, seq=None):
        self.out, self.lock, self.builder, self.on_written = out, lock, builder, on_written
        self.bus, self.seq, self.rebuilder = bus, seq or (lambda: 0), None

    def _written(self, r, ids, stamp):
        """쓰기 답 → 이벤트(자물쇠 안에서). 쓴 것이 있으면 screen.written, 다시 빌드가 깨져 되돌렸으면 build.failed. → screen.written 이벤트 | None."""
        if r.get("changed") and (r.get("stamp") or "restored" in r):
            return _emit(self.bus, "screen.written", screens=list(r["changed"]), by="human", rev=self.seq(), stamp=stamp)
        broke = [f for f in r.get("failed") or [] if str(f.get("reason", "")).startswith(BUILD_FAIL)]
        if broke or str(r.get("error", "")).startswith(BUILD_FAIL):
            _emit(self.bus, "build.failed", reason=broke[0]["reason"] if broke else r["error"], reverted=[f["id"] for f in broke] or list(ids),
                  kept=[], stamps=[], ids=[f["id"] for f in broke] or list(ids), screens=[], repaired=None)
        return None

    def _write(self, fn, ids=(), key="stamp"):
        with self.lock:
            try:
                r = fn()
            finally:
                if self.on_written:
                    self.on_written()                # 스스로 쓴 화면 파일은 '바뀜'으로 알리지 않는다(캔버스가 그 카드를 이미 다시 싣는다)
            self._written(r, ids, r.get(key))
        return _code(r), r

    def apply(self, edits):
        return self._write(lambda: apply_edits(self.out, edits, build=self.builder.run))

    def apply_async(self, edits):
        """{edits, async:true} — 화면 파일만 쓰고(원본·manifest 는 같음) 바로 답 {accepted, failed, stamp, changed, paths, rev, async}.
        rev = 이 쓰기의 screen.written 이벤트 id(쓴 것이 없으면 지금 newest). 빌드는 rebuilder 가 뒤에서 하나씩(build.* 이벤트)."""
        ev = None
        with self.lock:
            try:
                r = apply_edits(self.out, edits, build=NO_BUILD)
            finally:
                if self.on_written:
                    self.on_written()
            if r["applied"]:
                ev = self._written(r, (), r.get("stamp"))
                if self.rebuilder is not None:
                    self.rebuilder.submit({"stamp": r["stamp"], "ids": list(r["applied"]), "screens": list(r["changed"])})
        rev = ev["id"] if ev else (self.bus.last if self.bus is not None else 0)
        return 200, {"accepted": r["applied"], "failed": r["failed"], "stamp": r["stamp"], "changed": r["changed"],
                     "paths": r.get("paths") or {}, "rev": rev, "async": True}

    def revert_writes(self, writes):
        """뒤 빌드가 깨졌다 — 아직 빌드로 확인 안 된 쓰기들을 새것부터 되살리기(빌드 없이)로 되돌리고 그 기록을 지운다 → (되돌린 편집 id, 못 되돌린 편집 id)."""
        reverted, kept = [], []
        with self.lock:
            try:
                for w in reversed(writes):
                    r = restore(self.out, w["stamp"], build=NO_BUILD)
                    if "restored" in r:
                        reverted[:0] = w["ids"]
                        tombstone(self.out, w["stamp"], w["ids"], "뒤 빌드 실패")   # 캔버스 되돌리기 줄이 '없는 기록' 대신 아무 일 없음(47-5a)
                    else:
                        kept[:0] = w["ids"]
                        print("[hd] 뒤 빌드 실패 — 쓰기 %s 를 되돌리지 못했어요(%s)" % (w["stamp"], r.get("error")), file=sys.stderr, flush=True)
            finally:
                if self.on_written:
                    self.on_written()
        return reverted, kept

    def delete(self, ids):
        return self._write(lambda: delete_screens(self.out, ids, build=self.builder.run), ids)

    def group_rename(self, frm, to):                 # 줄 이름 바꾸기(51-4) — screens.json 쓰기 한 번, 되돌리기 = restore
        return self._write(lambda: group_rename(self.out, frm, to, build=self.builder.run))

    def group_dissolve(self, name):                  # 줄만 걷기(51-4) — 그 줄 화면은 위 줄(첫 줄이면 아래 줄)로
        return self._write(lambda: group_dissolve(self.out, name, build=self.builder.run))

    def restore(self, stamp, keep=False, notify=False):
        """notify = 되살린 화면 파일을 지켜보기가 '바뀜'으로 알리게(그 카드를 캔버스가 다시 싣는다 — 48c 기록 패널의 AI 줄 되돌리기)."""
        if notify:
            with self.lock:
                r = restore(self.out, stamp, build=self.builder.run, keep=keep)
                self._written(r, (), r.get("redo"))
            return _code(r), r
        return self._write(lambda: restore(self.out, stamp, build=self.builder.run, keep=keep), key="redo")

    def prune(self):
        return prune(self.out)


NOTES_MAX = 200                                      # /api/forward notes(메모 id) 개수 한도


def check_send(body):
    """POST /api/forward 본문 {text, to?, notes?} → ((text, to | None, notes), None) | (None, 한국어 오류)."""
    to = body.get("to")
    err = hd_model.agent_error(to)
    if err:
        return None, "to: " + err
    notes = body.get("notes", [])
    if not isinstance(notes, list) or len(notes) > NOTES_MAX or not all(isinstance(n, str) and n for n in notes):
        return None, "notes: 메모 id 글 목록(%d개까지)이어야 해요" % NOTES_MAX
    return (str(body.get("text") or ""), to, list(notes)), None


class Queue:
    """보낸 메모 — 보낼 곳(agent, attach 로 바뀜 · Paseo 목록 5초 캐시 · 저장소 repo) · 요청문 보내기(send: 대기열 파일 + 받는 곳 고르기) · 에이전트 답(reply).
    받는 곳(adapters.choose): 접속 중이고 이벤트를 읽는 에이전트 = request.sent 이벤트(터미널 없음) · 아니면 어댑터(paseo · claude · queue).
    칸 이름 agent · repo · agents_cache · agents_lock · presence 는 agents_get 이 읽는다."""

    def __init__(self, out, lock, agent=None, paseo=None, on_attach=None, bus=None, presence=None, config=None):
        self.out, self.lock, self.paseo, self.on_attach, self.bus, self.presence = out, lock, paseo, on_attach, bus, presence
        self.agent = agent or None
        self.repo = project_repo(out)
        self.agents_cache, self.agents_lock = None, threading.Lock()
        cfg = config or {}
        self.adapters = {"paseo": AD.PaseoAdapter(lambda: _paseo_cmd(self.paseo)),
                         "claude": AD.ClaudeCliAdapter(lambda: cfg.get("claude_cmd") or shutil.which("claude"),
                                                       enabled=bool(cfg.get("claude_wake")), cwd=self.repo or str(out)),
                         "queue": AD.NoneAdapter()}

    def forward(self, text):                         # 옛 이름(받는 곳 = 붙은 에이전트, 메모 id 없음)
        return self.send({"text": text})[1]

    def send(self, body):
        """POST /api/forward {text, to?, notes?} → (code, {via, path, agent?, event}). 늘 대기열 파일을 쓰고 request.sent 를 낸다."""
        got, err = check_send(body)
        if err:
            return 400, {"error": err}
        text, to, notes = got
        target = to or self.agent
        entry = self.presence.get(target) if (target and self.presence is not None) else None
        how = AD.choose(target, entry, {k: a.ready() for k, a in self.adapters.items()})
        p = queue_file(self.out, text)
        via = how
        if how in ("paseo", "claude"):
            ok, why = self.adapters[how].send(p, text, entry or target)
            if ok:
                mark_sent(p)
            else:
                print("[hd] %s 로 넘기지 못해 대기열 파일로 남겨요(%s): %s" % (how, why, p.name), file=sys.stderr, flush=True)
                via = "queue"
        ev = _emit(self.bus, "request.sent", to=target, via=via, notes=notes, text=text, path=str(p))
        res = {"via": via, "path": str(p)}
        if via != "queue":
            res["agent"] = target
        if ev is not None:
            res["event"] = ev["id"]
        return 200, res

    def agents(self, auto=False):
        return agents_get(self, self.paseo, auto=auto)

    def attach(self, body):
        """{agent: id|null} → (code, 답). 받은 agent 를 두고 on_attach(agent)(표지 고쳐 쓰기)."""
        if not isinstance(body, dict) or "agent" not in body:
            return 400, {"error": "agent: 없어요({agent: id 또는 null})"}
        err = hd_model.agent_error(body["agent"])
        if err:
            return 400, {"error": err}
        with self.lock:
            self.agent = body["agent"]
            if self.on_attach:
                self.on_attach(self.agent)
        print("[hd] 보내기 → %s" % (self.agent or "대기열 파일"), file=sys.stderr, flush=True)
        return 200, {"agent": self.agent}

    def reply(self, body):
        with self.lock:
            code, res = reply_post(self.out, body)
            if code == 200:
                _emit(self.bus, "notes.changed", rev=res["rev"])
                by = body["reply"].get("by")                # 47-5a: 에이전트가 답했다(캔버스 대화창 · 접속 칩)
                _emit(self.bus, "agent.reply", note=_str(res.get("note")), kind=str(body["reply"].get("kind")), screen=_str(res.get("screen")),
                      agent=_str(by), status=res["status"])
            return code, res


class Busy:
    """AI 작업 덮개 state.busy(claim · release, 상태 파일 자물쇠 안) + 화면 파일 지켜보기(1초마다 mtime → FileWatch seq)."""

    def __init__(self, out, lock, ai=None, bus=None):
        self.out, self.lock, self.ai, self.bus = out, lock, ai, bus
        self.watch, self.stop = FileWatch(), threading.Event()

    def claim(self, body):
        with self.lock:
            code, res = claim_post(self.out, body)
            if code == 200 and self.ai is not None:
                self.ai.begin(res["screen"], res["file"])   # 48c — AI 가 쓰기 전 모습
            if code == 200:
                _emit(self.bus, "claim", screen=res["screen"], rev=res["rev"], by=_str(body.get("by")), note=_str(body.get("note")))
        return code, res

    def release(self, body):
        with self.lock:
            code, res = release_post(self.out, body)
            if code == 200 and self.ai is not None:
                self._ai(body["screen"], self.ai.end)   # 48c — 마지막으로 보고 끝
            if code == 200 and res.get("released"):
                _emit(self.bus, "release", screen=body["screen"], rev=res["rev"])
        return code, res

    def mtimes(self, files):
        return watch(self.out, files)

    def files(self, since):
        return self.watch.changes(since)

    def absorb(self):
        m = scan(self.out, {})
        if m is not None:
            self.watch.absorb(m)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def close(self):
        self.stop.set()

    def _loop(self):
        cache = {}
        while not self.stop.wait(WATCH_EVERY if self.watch.last is not None else 0):
            with self.lock:                          # 도우미가 쓰는 중(apply 의 쓰기~빌드)에는 보지 않는다 — 다 쓴 뒤 absorb 가 기준을 옮긴다
                m = scan(self.out, cache)
                if m is not None:
                    changed = self.watch.tick(m)
                    if changed:
                        _emit(self.bus, "screen.written", screens=changed, by="ai", rev=self.watch.seq, stamp=None)
                    for sid in changed:
                        if self.ai is not None:
                            self._ai(sid, self.ai.seen)

    def _ai(self, sid, fn):
        """AiUndo.seen · end 를 부르고, 기록 줄이 생기거나(record) 기준이 옮겨지면(update) ai.write — GET /api/ai-writes 의 한 줄 + act."""
        n = len(self.ai.log)
        act = fn(sid)                                # seen → 'record'|'update'|None · end → 끝난 항목(마지막으로 seen 을 부른다)
        act = act if act in ("record", "update") else ("record" if len(self.ai.log) > n else None)
        row = self.ai.log[-1] if len(self.ai.log) > n else self.ai.row(sid)
        if act in ("record", "update") and row is not None:
            _emit(self.bus, "ai.write", seq=row["seq"], stamp=row["stamp"], screen=row["screen"], label=row["label"], act=act)


class AiUndo:
    """48c AI 되돌리기 — 덮개(claim) 동안 그 화면 파일의 쓰기 전 모습을 .hd-history/<stamp>/ 에 남기고(직접 쓰기와 같은 모양),
    바뀐 것을 보면 manifest(되살리기 기준 = 지금 파일) + 기록 줄 하나 'AI 반영 · <화면>'. 또 바뀌면 같은 줄의 기준만, release 로 끝.
    아무것도 안 바뀌고 끝나면 남긴 모습을 지운다. 규칙은 helper_model.ai_*(순수), 여기는 파일만. 세션 자물쇠 안에서 부른다."""

    def __init__(self, out):
        self.out, self.track, self.log = out, {}, []

    def begin(self, screen, rel):
        if screen in self.track:
            return
        f = self.out / rel
        if not _inside(self.out, f):
            return
        stamp = _stamp(datetime.datetime.now())
        hist = self.out / ".hd-history" / stamp
        try:
            (hist / rel).parent.mkdir(parents=True, exist_ok=True)
            if f.is_file():
                shutil.copy2(f, hist / rel)
        except OSError as e:
            print("[hd] AI 쓰기 전 화면을 남기지 못했어요(%s) — 이 화면의 AI 반영은 되돌릴 수 없어요: %s" % (e, rel), file=sys.stderr, flush=True)
            return
        self.track = helper_model.ai_begin(self.track, screen, stamp, rel, _sha(f), f.is_file())

    def seen(self, screen):
        e = self.track.get(screen)
        if e is None:
            return None
        self.track, act = helper_model.ai_seen(self.track, screen, _sha(self.out / e["rel"]))
        if act is None:
            return None
        e = self.track[screen]
        man = {"files": {e["rel"]: {"before": e["existed"], "after_sha": e["after"]}}, "changed": [screen], "by": "ai"}
        try:
            (self.out / ".hd-history" / e["stamp"] / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as x:
            print("[hd] AI 반영 기록을 쓰지 못했어요(%s): %s" % (x, screen), file=sys.stderr, flush=True)
            return None
        if act == "record":
            self.log.append({"seq": len(self.log) + 1, "stamp": e["stamp"], "screen": screen,
                             "label": helper_model.ai_label(screen, self._title(screen)), "at": _now()})
        return act

    def end(self, screen):
        self.seen(screen)
        self.track, e = helper_model.ai_end(self.track, screen)
        if e is not None and not e["logged"]:          # 안 바뀌었다 — 남긴 모습은 쓸 데가 없다
            shutil.rmtree(self.out / ".hd-history" / e["stamp"], ignore_errors=True)
        return e

    def since(self, since):
        return helper_model.ai_since(self.log, since)

    def row(self, screen):                           # 그 화면을 지금 추적 중인 기록 줄 | None
        e = self.track.get(screen)
        return next((x for x in reversed(self.log) if e and x["stamp"] == e["stamp"]), None)

    def _title(self, screen):
        try:
            return next((x.get("title") for x in json.loads((self.out / "screens.json").read_text(encoding="utf-8")).get("screens", [])
                         if x.get("id") == screen), None)
        except (OSError, ValueError, AttributeError):
            return None


class Archive:
    """<out>/.hd-notes-archive.jsonl — 완료 메모 덧붙이기(자물쇠 안) · 마지막 2000 줄 읽기 · sweep = 서버가 고르고 옮기기(47-5a, Ticker 가 한 시간마다)."""

    def __init__(self, out, lock, bus=None):
        self.out, self.lock, self.bus = out, lock, bus

    def post(self, body):
        with self.lock:
            return archive_post(self.out, body)

    def get(self):
        return archive_get(self.out)

    def sweep(self, now_ms=None):
        """오래된·넘친 완료 메모(memo_archive.pick)를 보관 파일로 옮기고 상태에서 뺀다(rev+1 · notes.changed) → 옮긴 수.
        캔버스 탭도 같은 일을 한다(view-state-sync) — 보관 파일은 id 로 겹치지 않고, 캔버스는 notes.changed 로 다시 읽는다."""
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        with self.lock:
            cur = state_load(self.out)
            notes = cur["state"].get("notes")
            picks = MA.pick(notes, now_ms)
            if not picks:
                return 0
            code, res = archive_post(self.out, {"notes": picks})
            if code != 200:
                print("[hd] 완료 메모를 보관하지 못했어요: %s" % res.get("error"), file=sys.stderr, flush=True)
                return 0
            rev = _state_save(self.out, cur["rev"] + 1, dict(cur["state"], notes=MA.without(notes, picks)))
            _emit(self.bus, "notes.changed", rev=rev)
        print("[hd] 완료 메모 %d개를 보관으로 옮겼어요(%s)" % (len(picks), ARCHIVE_FILE), file=sys.stderr, flush=True)
        return len(picks)


PRESENCE_EVERY = 1.0                                 # 접속 임대 끝 보기(초)
ARCHIVE_EVERY = 3600.0                               # 완료 메모 보관(초) — 캔버스 탭의 '한 시간에 한 번'과 같은 규칙, 탭이 없어도
TICK = 0.5


class Ticker:
    """세션 시계 — 일(간격 초, fn)마다 처음 한 번, 그 뒤 간격마다. step(now) 는 I/O 가 없다(unit), 스레드는 start()·close().
    한 일이 실패해도 [hd] 한 줄 뒤 다른 일은 계속."""

    def __init__(self, tasks, clock=time.monotonic):
        self.tasks, self.clock = list(tasks), clock
        self.next = [None] * len(self.tasks)
        self.stop = threading.Event()

    def step(self, now):
        for i, (every, fn) in enumerate(self.tasks):
            if self.next[i] is None or now >= self.next[i]:
                self.next[i] = now + every
                try:
                    fn()
                except Exception as e:                # noqa: BLE001 — 세션 시계는 멈추지 않는다(한 줄 남김)
                    print("[hd] 세션 시계 일이 실패했어요(%s): %s" % (getattr(fn, "__name__", fn), e), file=sys.stderr, flush=True)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def close(self):
        self.stop.set()

    def _loop(self):
        while not self.stop.is_set():
            self.step(self.clock())
            self.stop.wait(TICK)


class ProjectSession:
    """프로젝트(out) 하나 — 부품 객체를 만들고 잇는다. 쓰기 자물쇠 하나(상태 파일·화면 파일·보관 파일 쓰기는 한 번에 하나) · 토큰 하나.
    open() = 시작 정리(깨진 상태 파일 옮기기 · 오래된 기록 정리) · start() = 지켜보기 시작 · close() = 멈춤."""

    def __init__(self, out, token=None, agent=None, paseo=None, build=None, on_attach=None, name=None, config=None, code=None):
        self.out = pathlib.Path(out).resolve()
        self.code = code                             # () → 지금 코드 도장 | None — 있으면 페이지를 줄 때 옛 도장 index.html 을 다시 빌드(CLI 도우미·허브가 넘김)
        self._gave_up = None                         # 다시 빌드해도 그 도장이 안 나온 도장 — 같은 도장으로 매번 빌드하지 않게
        self.token = token or secrets.token_urlsafe(18)
        self.lock = threading.Lock()
        self.events = EV.EventBus(name or hd_model.project_name(self.out.name, self.out.parent.name))
        self.builder = Builder(self.out, build)
        self.store = StateStore(self.out, self.lock, self.events)
        self.ai = AiUndo(self.out)
        self.busy = Busy(self.out, self.lock, self.ai, self.events)
        self.history = History(self.out, self.lock, self.builder, self.busy.absorb, self.events, lambda: self.busy.watch.seq)
        self.rebuilder = RB.Rebuilder(lambda: self.builder.run(self.out), self.history.revert_writes, self.events.publish)
        self.history.rebuilder = self.rebuilder
        self.config = config if config is not None else AD.config_from_env(os.environ)   # 47-5a: claude 깨우기 · 새 에이전트 열기(기본 꺼짐)
        self.presence = PR.AgentPresence(self.events.publish)
        self.queue = Queue(self.out, self.lock, agent, paseo, on_attach, self.events, self.presence, self.config)
        self.spawner = AD.PaseoSpawner(lambda: _paseo_cmd(paseo), enabled=bool(self.config.get("allow_spawn")))
        self.archive = Archive(self.out, self.lock, self.events)
        self.ticker = Ticker([(PRESENCE_EVERY, self.presence.sweep), (ARCHIVE_EVERY, self.archive.sweep)])

    def open(self):
        state_load(self.out)                         # 깨진 상태 파일을 옮겨 둔다(멈추지 않음)
        self.history.prune()                         # 오래된 기록·처리된 대기열 정리(#281, 실패해도 한 줄)
        return self

    def start(self):
        self.busy.start()
        self.ticker.start()
        return self

    def spawn(self, body):
        """POST /agents/spawn {kind} — 기본 꺼짐(HD_ALLOW_SPAWN=1). 일하는 폴더 = 저장소(없으면 out)."""
        return self.spawner.spawn(body, self.queue.repo or str(self.out), self.events.project)

    def close(self):
        self.ticker.close()
        self.busy.close()
        self.rebuilder.close()                        # 다음 뒤 빌드는 시작하지 않는다(돌고 있는 것은 끝까지) — 남은 쓰기는 다음 열기의 빌드가 담는다
        if self.rebuilder.pending():
            print("[hd] 닫는 중 — 아직 빌드하지 않은 쓰기 %d개(화면 파일에는 있어요)" % self.rebuilder.pending(), file=sys.stderr, flush=True)
        self.events.close()                           # 열린 흐름(SSE)이 끝난다

    def page_code(self):
        """index.html 이 품은 코드 도장 | None(도장 전 빌드 · 못 읽음)."""
        try:
            with open(self.out / "index.html", encoding="utf-8", errors="replace") as f:
                return CS.page_stamp(f.read(8192))       # 도장은 <head> 바로 뒤
        except OSError:
            return None

    def refresh(self, current):
        """index.html 이 지금 코드(current)로 구운 것이 아니면 다시 빌드 → 'fresh' | 'rebuilt' | 'failed'.
        다시 빌드해도 그 도장이 안 나오면(빌드 실패 · 다른 빌더) 그 도장으로는 다시 하지 않는다 — [hd] 한 줄."""
        if not current or current == self._gave_up or self.page_code() == current:
            return "fresh"
        r = self.builder.run(self.out)
        if getattr(r, "returncode", 1) == 0 and self.page_code() == current:
            print("[hd] 옛 코드로 구운 캔버스를 지금 코드로 다시 빌드했어요: %s" % self.out, file=sys.stderr, flush=True)
            return "rebuilt"
        self._gave_up = current
        tail = ((getattr(r, "stdout", "") or "") + (getattr(r, "stderr", "") or "")).strip().splitlines()[-1:]
        print("[hd] 캔버스를 지금 코드로 다시 빌드하지 못했어요 — 있던 index.html 로 보여요%s" % (": " + tail[0] if tail else ""),
              file=sys.stderr, flush=True)
        return "failed"

    def page(self):
        """index.html + <head> 에 window.__hdHelper·__hdKeyPath·__hdOut·__hdAgent(attach 로 바뀌므로 줄 때마다)·__hdState → bytes.
        code 가 있으면 주기 전에 옛 도장 index.html 을 다시 빌드(F5 · 즐겨찾기로 열어도 지금 코드)."""
        if self.code is not None:
            try:
                self.refresh(self.code())
            except Exception as e:                    # noqa: BLE001 — 도장 재기·빌드 실패로 페이지를 못 주지는 않는다(한 줄 남김)
                print("[hd] 코드 도장을 견주지 못했어요(%s) — 있던 index.html 로 보여요" % e, file=sys.stderr, flush=True)
        snap = self.store.inject()
        inject = '<script>window.__hdHelper=%s;window.__hdKeyPath=%s;window.__hdOut=%s;' % (
            json.dumps(True), json.dumps(keypath(self.out)), json.dumps(self.out.as_posix()))
        inject += "window.__hdAgent=%s;</script>" % json.dumps(self.queue.agent)
        return (self.out / "index.html").read_text(encoding="utf-8").replace("<head>", "<head>" + inject + snap, 1).encode("utf-8")
