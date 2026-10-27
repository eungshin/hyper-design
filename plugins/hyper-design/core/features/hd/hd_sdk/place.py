"""Service — 캔버스 하나의 화면 목록 읽기(layout)와 새 화면 놓기(add): hd screens · hd add. Project 가 부른다(Project.layout · Project.add).

쓰는 곳 하나 규칙(hd contract.md '출력'): 상태 파일(.hd-canvas.json — card-pos · card-size)은 늘 도우미로(PUT /api/state, rev 비교 · 409 면 다시 읽고 다시).
  도우미가 없으면 상태 파일은 손대지 않는다 — 명시한 --at · --size 는 쓰기 전에 거절(띄우는 명령과 함께), 저절로 고른 자리·크기는 [hd] 한 줄로 건너뜀.
화면 파일 · 첨부 · screens.json 은 화면 파일 쓰기와 같이 직접(에이전트가 화면 파일을 고치는 길과 같다).
열린 캔버스에 보이기:
  도우미 있음 → POST /api/apply 의 title 편집 하나(그 화면 제목 = 같은 값) — 도우미가 screens.json 을 다시 쓰고 screen.written(by human)을 내면
               캔버스가 판 데이터를 다시 받아(/api/data) 새 줄·새 카드를 제자리에 그린다(새로고침 없음). 그 뒤 SETTLE 초 쉬고 자리·크기를 PUT
               — 캔버스가 새 카드를 알기 전에 card-pos 를 받으면 모르는 화면의 자리로 버리므로(canvas rows.cleanPos) 순서가 중요하다.
               페이지를 새로 열면 도우미가 데이터 도장을 보고 index.html 을 다시 굽는다(session.refresh_data).
  도우미 없음 → build_ref.py 로 index.html 다시 빌드(hd open 과 같은 길, hd_client.build). 실패하면 [hd] 한 줄(파일은 이미 씀).
"""
import os, pathlib, time

import hd_client as C
import hd_place as L

from . import errors as E
from .transport import client_errors

SETTLE = 1.5                                         # 판 데이터를 다시 받을 틈(초) — env HD_ADD_SETTLE 로 바꿀 수 있다
STATE_TRIES = 3


def _settle():
    try:
        return max(0.0, float(os.environ.get("HD_ADD_SETTLE", SETTLE)))
    except ValueError:
        return SETTLE


def layout(p):
    """→ {project, out, helper, title, groups, screens:[hd_place.rows 줄]}."""
    with client_errors():
        data, _ = C.read_manifest(p.out)
    st = p.state()["state"]
    return {"project": p.name, "out": str(p.out), "helper": p.online, "title": data.get("title") if isinstance(data, dict) else None,
            "groups": [g for g in (data.get("groups") or []) if isinstance(g, str)] if isinstance(data, dict) else [],
            "screens": L.rows(data, st)}


def _assets(src, assets, out):
    """첨부 → [(원본 Path, out 안 '/' 경로, 할 일 'copy'|'same'|'inside')]. 없는 파일 · out 밖 경로 · 다른 내용의 파일(겹침) = 오류 글 목록."""
    items, errs = [], []
    sdir = src.resolve().parent
    for a in assets or ():
        ap = pathlib.Path(a).expanduser()
        if not ap.is_file():
            errs.append("없는 첨부 파일이에요: %s" % a); continue
        ap = ap.resolve()
        try:
            ap.relative_to(out)
            items.append((ap, ap.relative_to(out).as_posix(), "inside")); continue
        except ValueError:
            pass
        rel = L.asset_rel(list(sdir.parts), list(ap.parts))
        dest = (out / rel).resolve()
        try:
            dest.relative_to(out)
        except ValueError:
            errs.append("out 밖으로 가는 첨부예요: %s" % a); continue
        items.append((ap, rel, "same" if dest.is_file() and dest.read_bytes() == ap.read_bytes() else
                      ("clash" if dest.exists() else "copy")))
    return items, errs


def add(p, src, sid=None, title=None, group=None, purpose=None, after=None, at=None, size=None, assets=(), replace=False):
    """HTML 화면 하나를 그 캔버스에 놓는다 → {project, out, id, file, title, group, after, pos, size, assets, replaced, group_added, live, state_rev}.
    at = 'DX,DY' 글 | None · size = 'Desktop' | 'WxH' | None. 쓰기 전에 모두 검사한다(틀리면 아무것도 쓰지 않음)."""
    src = pathlib.Path(src).expanduser()
    if not src.is_file():
        raise E.NotFound("없는 파일이에요: %s" % src)
    out = p.out.resolve()
    try:
        at_v = L.parse_at(at) if at is not None else None
        size_v = L.parse_size(size, C.presets()) if size is not None else None
    except L.PlaceError as e:
        raise E.Invalid(str(e))
    if not p.online and (at_v is not None or size_v is not None):
        raise E.Offline("이 캔버스를 띄운 도우미가 없어요 — 자리·크기(--at · --size)는 도우미로만 써요(상태 파일 쓰는 곳 하나). "
                        "먼저 띄우세요: hd open \"%s\" --no-open" % out, next="")
    with client_errors():
        data, raw = C.read_manifest(out)
    st = p.state()
    text = src.read_text(encoding="utf-8", errors="replace")
    sid = sid if sid is not None else L.default_id(src.stem)
    try:
        f_guess = sid + ".html"
        taken = {f_guess} if (out / f_guess).exists() and (out / f_guess).resolve() != src.resolve() else set()
        pl = L.plan(data, st["state"], sid, title=title, group=group, purpose=purpose, after=after, at=at_v, size=size_v,
                    replace=replace, files=taken, html_title=L.html_title(text))
    except L.PlaceError as e:
        raise E.Invalid(str(e))
    dest = (out / pl["file"]).resolve()
    try:
        dest.relative_to(out)
    except ValueError:
        raise E.Invalid("화면 파일이 out 밖이에요: %s" % pl["file"])
    items, errs = _assets(src, assets, out)
    errs += ["out 에 이미 다른 내용의 파일이 있어요: %s — 바꾸려면 --replace" % rel for _, rel, how in items if how == "clash" and not replace]
    if errs:
        raise E.Invalid("\n  ".join(errs))

    # ---- 쓰기(여기부터) — 화면 파일 · 첨부 · screens.json
    if dest != src.resolve():
        C.copy_in(src, dest)
    for ap, rel, how in items:
        if how in ("copy", "clash"):
            C.copy_in(ap, out / rel)
    C.write_manifest(out, pl["data"], raw)

    res = {"project": p.name, "out": str(out), "id": sid, "file": pl["file"], "title": pl["entry"]["title"], "group": pl["entry"].get("group"),
           "after": after, "replaced": pl["replaced"], "group_added": pl["group_added"], "assets": [rel for _, rel, _ in items],
           "live": p.online, "state_rev": None, "skipped": []}
    if p.online:
        a = p.apply([{"id": "hd-add-%s" % sid, "screen": sid, "edit": "title", "value": pl["entry"]["title"]}])
        if not a.get("applied"):
            C.warn("캔버스에 바로 보이지 못했어요(%s) — 캔버스를 새로고침하면 보여요" % "; ".join(x.get("reason", "") for x in a.get("failed") or []))
        patch = L.state_patch(st["state"], sid, pl["pos"], pl["size"])
        if patch:
            time.sleep(_settle())
            res["state_rev"] = _put_state(p, sid, pl["pos"], pl["size"])
    else:
        res["skipped"] = [n for n, v in (("자리", pl["pos"]), ("크기", pl["size"])) if v != "keep"]   # 저절로 고른 값만 여기 온다(명시한 값은 위에서 거절)
        if res["skipped"]:
            C.warn("도우미가 없어 %s 은 쓰지 않았어요(상태 파일은 도우미만 씀) — 띄운 뒤 hd add … --replace 로 다시: hd open \"%s\" --no-open"
                   % ("·".join(res["skipped"]), out))
        with client_errors():
            code, tail = C.build(out)
        if code != 0:
            C.warn("index.html 을 다시 빌드하지 못했어요(%d) — 화면은 넣었어요: %s" % (code, tail.splitlines()[-1] if tail else ""))
    final = L.rows(pl["data"], _fresh_state(p)) if p.online else L.rows(pl["data"], st["state"])
    row = next(r for r in final if r["id"] == sid)
    res["pos"], res["size"] = row["pos"], row["size"]
    return res


def _fresh_state(p):
    try:
        return p.state()["state"]
    except E.HdError:
        return {}


def _put_state(p, sid, pos, size):
    """card-pos · card-size 를 도우미로(PUT /api/state {rev, state}) — 409(그 사이 캔버스가 씀)면 다시 읽고 다시. → 새 rev | None(바꿀 것 없음)."""
    for _ in range(STATE_TRIES):
        st = p.state()
        patch = L.state_patch(st["state"], sid, pos, size)
        if not patch:
            return None
        code, res = p._need().request("PUT", "/api/state", {"rev": st["rev"], "state": patch})
        if code == 200:
            return res.get("rev")
        if code != 409:
            raise E.from_status(code, res)
    raise E.Conflict("캔버스가 계속 상태를 바꾸고 있어 자리·크기를 쓰지 못했어요(화면은 넣었어요) — 잠시 뒤 다시 hd add … --replace")
