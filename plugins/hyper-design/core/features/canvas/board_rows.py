"""Edge + Model — 판의 줄(group, 51-4): 차례 · 이름 바꾸기 · 줄만 걷기 · 다른 줄로 옮기기(R31)(계획은 순수, 쓰기는 screens.json 한 번 = 되돌리기 한 번) · 지우기로 빈 줄 빼기.

상태 없음(screens.json 의 groups · 화면마다 group). 줄 이름 차례는 board_data.index_data 와 같다.
부르는 곳: history.History(group_rename · group_dissolve · group_move) · screen_edits.delete_screens(emptied_groups) · 테스트(plan_* 를 바로).
오류 탐지: 받을 수 없는 요청은 GroupError(한국어 + reason 'invalid' 400 · 'missing' 404) → {error, reason} · 빌드가 깨지면 되돌림(write_record).
"""
import json, pathlib

from out_io import _write_json
from write_record import _Writes


def emptied_groups(groups, before, after):
    """지우기로 비게 된 group 이름만 groups 에서 뺀다(51-1, Figma F18 빈 그룹은 없어진다) — 원래 빈 이름·순서는 그대로. groups 가 목록이 아니면 그대로."""
    if not isinstance(groups, list):
        return groups
    name = lambda s: s.get("group") or "기타"           # board_data.index_data 와 같은 이름
    had, has = {name(s) for s in before}, {name(s) for s in after}
    return [g for g in groups if not (g in had and g not in has)]



GROUP_MAX = 80                                       # 줄 이름 글자 수 한도(판 제목 한 줄)



class GroupError(ValueError):
    """줄(group) 요청을 받을 수 없다 — 한국어 이유 + reason('invalid' = 400 · 'missing' = 404)."""
    def __init__(self, msg, reason="invalid"):
        super().__init__(msg)
        self.reason = reason



def _gname(s):                                       # board_data.index_data 와 같은 이름(group 없음 = '기타')
    return s.get("group") or "기타"



def group_order(data):
    """줄 이름 차례 = board_data.index_data 와 같음(groups 먼저, 그다음 화면에만 있는 이름을 화면 차례로)."""
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



def plan_group_move(data, ids, to):
    """다른 줄(폴더)로 옮기기 계획(R31, 레이어 패널 끌어 놓기) — 순수. ids 화면을 줄 to 로: 화면마다 group = to, 차례는 to 줄 화면 뒤
    (옮긴 화면끼리는 원래 차례 — 빌드가 같은 차례로 그린다). 그래서 비게 된 줄 이름은 groups 에서 뺀다(emptied_groups).
    → {data, screens(옮긴 id), to, emptied, same?}. 이미 모두 to 줄이면 same(쓰지 않음). 캔버스 규칙 HD.rowOps.assign 과 같다."""
    rows = group_rows(data)
    if not isinstance(to, str) or to not in rows:
        raise GroupError("없는 폴더예요: %s" % (to,), "missing")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
        raise GroupError("옮길 화면이 없어요")
    new = json.loads(json.dumps(data))
    screens = new.get("screens") or []
    have = {s.get("id") for s in screens}
    unknown = [i for i in ids if i not in have]
    if unknown:
        raise GroupError("없는 화면이에요: %s" % ", ".join(unknown), "missing")
    want = set(ids)
    moved = [s for s in screens if s.get("id") in want and _gname(s) != to]
    if not moved:
        return {"data": new, "screens": [], "to": to, "emptied": [], "same": True}
    rest = [s for s in screens if not (s.get("id") in want and _gname(s) != to)]
    before = [dict(s) for s in screens]                # 옮기기 전 group(아래에서 같은 객체를 고친다)
    for s in moved:
        s["group"] = to
    at = [k for k, s in enumerate(rest) if _gname(s) == to]
    k = at[-1] + 1
    new["screens"] = rest[:k] + moved + rest[k:]
    gone = [g for g in rows if g not in {_gname(s) for s in new["screens"]}]
    if isinstance(new.get("groups"), list):
        new["groups"] = emptied_groups(new["groups"], before, new["screens"])
    return {"data": new, "screens": [s["id"] for s in moved], "to": to, "emptied": gone}



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
        return dict(res, group=p["to"], stamp=None, changed=[])   # same = 쓰지 않음
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



def group_move(out, ids, to, stamp=None, build=None):
    """POST /api/group-move {ids, to} → {group(= to), screens(옮긴 id), emptied, stamp|null(이미 그 줄 = 쓰지 않음), changed:[]} | {error, reason}."""
    return _group_write(out, lambda d: plan_group_move(d, ids, to), stamp, build)
