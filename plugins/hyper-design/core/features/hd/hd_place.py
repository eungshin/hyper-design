"""Model — 캔버스 화면 목록 읽기와 새 화면 놓기 계획(hd screens · hd add). 순수: 파일·네트워크·시계를 쓰지 않는다(tests/test_hd_place.py 순수성 검사).

화면 = screens.json 의 screens[] {id, file, title, group, purpose}. 자리·크기 = 상태 파일 state 의
  card-pos  {id: {dx, dy, g}} — 그 카드가 제 자리(줄 안 차례로 흐른 자리)에서 옮긴 거리(판 px), g = 줄 이름(canvas contract/card-pos.md)
  card-size {id: {w, h, preset?}} — CSS px 정수 100~4000(canvas contract/artboard.md)
놓기(plan):
  줄    = --group | --after 화면의 줄 | (--replace) 있던 줄 | screens 마지막 화면의 줄 | 없음. 새 줄이면 groups[] 끝에 넣는다
  차례  = --after 바로 뒤(그 화면의 상태 변형 '<id>--…' 은 건너뜀 — 빌드가 변형을 원래 화면 바로 뒤에 그린다) | 그 줄의 마지막 화면 뒤 | 끝
          — 줄 안 카드는 차례로 흐르니 빈 자리 = 줄 끝(겹치지 않음)
  자리  = --at DX,DY(제 자리에서 옮긴 거리) | --after 화면의 옮긴 거리(그 옆에 붙어 보이게) | (--replace) 그대로 | 없음(제 자리)
  크기  = --size | --after 화면의 크기 | (--replace) 그대로 | 그 줄 화면들이 가장 많이 쓴 크기 | 없음(프로젝트 기본)
  거절  = PlaceError(한국어 한 줄) — 쓰인 id(--replace 없이) · 없는 --after · 다른 줄의 --after · 잘못된 id/크기/자리 · 쓰인 파일
"""
import re

ID_OK = re.compile(r"^[^/\\:*?\"<>|\s.][^/\\:*?\"<>|\s]*$")   # canvas screen_copy.ID_OK 와 같게(테스트가 본다) — 파일 이름이 될 수 있는 한 조각
ID_MAX = 120
TITLE_MAX = 200
SIZE_MIN, SIZE_MAX = 100, 4000                      # canvas artboard.js MIN·MAX
PRESET_RE = re.compile(r"\[\s*'(\w+)'\s*,\s*'([^']+)'\s*,\s*(\d+)\s*,\s*(\d+)\s*\]")
SIZE_RE = re.compile(r"^\s*(\d+)\s*[x×X*]\s*(\d+)\s*$")
AT_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")
TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


class PlaceError(Exception):
    """사용자에게 그대로 보일 한 줄 이유."""


def file_of(s):                                      # board_data.index_data · screen_copy.file_of 와 같은 기본 경로
    return s.get("file") or "screens/%s.html" % s["id"]


def screens_of(data):
    return [s for s in (data.get("screens") if isinstance(data, dict) and isinstance(data.get("screens"), list) else [])
            if isinstance(s, dict) and isinstance(s.get("id"), str)]


# ---------------------------------------------------------------- 크기 · 자리 글
def parse_presets(js_text):
    """canvas modules/artboard.js 글 → {소문자 이름: (이름, w, h)} — 프리셋 표는 그 파일 하나(여기서 다시 적지 않는다)."""
    return {m.group(2).casefold(): (m.group(2), int(m.group(3)), int(m.group(4))) for m in PRESET_RE.finditer(js_text or "")}


def parse_size(text, presets=None):
    """'Desktop' | 'iPhone 16' | '1440x1024' → {w, h, preset?}. 틀리면 PlaceError."""
    t = (text or "").strip()
    m = SIZE_RE.match(t)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if not (SIZE_MIN <= w <= SIZE_MAX and SIZE_MIN <= h <= SIZE_MAX):
            raise PlaceError("--size: 너비·높이는 %d~%d 사이 정수(px)여야 해요: %s" % (SIZE_MIN, SIZE_MAX, t))
        hit = next((p for p in (presets or {}).values() if (p[1], p[2]) == (w, h)), None)
        return {"w": w, "h": h, "preset": hit[0]} if hit else {"w": w, "h": h}
    p = (presets or {}).get(t.casefold())
    if p is None:
        some = ", ".join(sorted(v[0] for v in (presets or {}).values())[:8])
        raise PlaceError("--size: 모르는 크기예요: %s — WxH(예 1440x1024) 또는 프리셋 이름%s" % (t, " (%s …)" % some if some else ""))
    return {"w": p[1], "h": p[2], "preset": p[0]}


def parse_at(text):
    """'DX,DY' → (dx, dy) 판 px(정수로 반올림). 틀리면 PlaceError."""
    m = AT_RE.match(text or "")
    if not m:
        raise PlaceError("--at: DX,DY 숫자 둘이어야 해요(예 --at 200,0 · 음수는 --at=-200,40): %s" % text)
    return int(round(float(m.group(1)))), int(round(float(m.group(2))))


def html_title(text):
    """화면 HTML 의 <title> 글(앞뒤 빈칸·줄바꿈 정리) | None."""
    m = TITLE_TAG.search(text or "")
    t = " ".join(m.group(1).split()) if m else ""
    return t[:TITLE_MAX] or None


def default_id(stem):
    """원본 파일 이름(확장자 뺌) → 화면 id 후보(빈칸 → '-', 소문자 아님 그대로 · 한글 그대로)."""
    return re.sub(r"[/\\:*?\"<>|\s]+", "-", (stem or "").strip()).strip("-.") or "screen"


# ---------------------------------------------------------------- 상태 읽기(깨진 값은 없는 것으로)
def pos_map(state):
    raw = state.get("card-pos") if isinstance(state, dict) else None
    out = {}
    for k, v in (raw.items() if isinstance(raw, dict) else ()):
        if isinstance(v, dict) and _num(v.get("dx")) and _num(v.get("dy")):
            out[k] = {"dx": v["dx"], "dy": v["dy"], "g": v.get("g")}
    return out


def size_map(state):
    raw = state.get("card-size") if isinstance(state, dict) else None
    out = {}
    for k, v in (raw.items() if isinstance(raw, dict) else ()):
        if isinstance(v, dict) and _int(v.get("w")) and _int(v.get("h")):
            out[k] = {"w": v["w"], "h": v["h"]}
            if isinstance(v.get("preset"), str) and v["preset"]:
                out[k]["preset"] = v["preset"]
    return out


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ---------------------------------------------------------------- hd screens
def rows(data, state):
    """screens.json + state → 줄 객체 [{id, title, group, file, purpose, pos:{dx,dy}|None, size:{w,h,preset?}|None}](screens.json 차례).
    pos 는 지금 줄(g)과 같을 때만(캔버스 cleanPos 처럼 — 다른 줄로 간 자리는 캔버스가 버린다)."""
    ps, ss = pos_map(state), size_map(state)
    out = []
    for s in screens_of(data):
        p = ps.get(s["id"])
        if p is not None and p.get("g") is not None and p["g"] != s.get("group"):
            p = None
        out.append({"id": s["id"], "title": s.get("title"), "group": s.get("group"), "file": file_of(s), "purpose": s.get("purpose"),
                    "pos": {"dx": p["dx"], "dy": p["dy"]} if p else None, "size": ss.get(s["id"])})
    return out


def size_label(z):
    if not z:
        return None
    return "%d×%d%s" % (z["w"], z["h"], "(%s)" % z["preset"] if z.get("preset") else "")


def pos_label(p):
    if not p:
        return None
    return "자리 %+g,%+g" % (p["dx"], p["dy"])


def format_rows(rs, groups=()):
    """줄 객체 → 사람용 줄: 줄 이름 머리 + `  id · title · file · 자리 +dx,+dy · W×H(프리셋)`. 줄 차례 = groups[] 다음 그 밖 줄 · 줄 없음."""
    if not rs:
        return "(화면 없음)"
    order = [g for g in groups if isinstance(g, str)]
    for r in rs:
        if r["group"] not in order:
            order.append(r["group"])
    lines = []
    for g in order:
        mine = [r for r in rs if r["group"] == g]
        if not mine:
            continue
        lines.append("[%s]" % (g if g is not None else "줄 없음"))
        for r in mine:
            bits = [r["id"], r["title"] or "-", r["file"]] + [x for x in (pos_label(r["pos"]), size_label(r["size"])) if x]
            lines.append("  " + " · ".join(str(b) for b in bits))
    return "\n".join(lines)


# ---------------------------------------------------------------- hd add
def _check_id(sid):
    if not isinstance(sid, str) or not ID_OK.match(sid) or len(sid) > ID_MAX:
        raise PlaceError("--id: 화면 id 로 쓸 수 없어요(빈칸·/\\:*?\"<>| 없이, 점으로 시작하지 않게, %d자까지): %r" % (ID_MAX, sid))


def _end_of(screens, i, sid):
    """screens[i](= sid) 와 그 뒤에 이어진 상태 변형('<sid>--…')의 마지막 차례."""
    j = i
    while j + 1 < len(screens) and str(screens[j + 1].get("id", "")).startswith(sid + "--"):
        j += 1
    return j


def _common_size(group_ids, sizes):
    seen = {}
    for i in group_ids:
        z = sizes.get(i)
        if z:
            k = (z["w"], z["h"], z.get("preset"))
            seen[k] = seen.get(k, 0) + 1
    if not seen:
        return None
    w, h, preset = max(seen, key=lambda k: seen[k])
    return dict({"w": w, "h": h}, **({"preset": preset} if preset else {}))


def plan(data, state, sid, title=None, group=None, purpose=None, after=None, at=None, size=None, replace=False, files=(), html_title=None):
    """새 화면 하나 놓기 계획 → {data: 새 screens.json, entry, file, replaced, group_added, pos, size, pos_from, size_from}.
      sid    = 화면 id(검사함) · title 기본 = html_title | 있던 제목(--replace) | sid
      at     = (dx, dy) | None · size = {w, h, preset?} | None
      files  = out 안에 이미 있는 파일(out 기준 '/' 경로) — 새 화면 파일 '<sid>.html' 이 겹치면 거절
      pos/size = 이 화면에 쓸 값: dict(쓰기) | None(지우기 — 제 자리·기본 크기) | 'keep'(손대지 않음)
      pos_from/size_from = 'at'|'after'|'keep'|'group'|'none' · 'size' — 어디서 왔나(도우미가 없을 때 명시한 값만 막는 데 쓴다)
    data 는 고치지 않는다(새 객체). 틀리면 PlaceError."""
    if not isinstance(data, dict) or not isinstance(data.get("screens"), list):
        raise PlaceError("screens.json 모양이 아니에요(screens 목록이 없어요)")
    _check_id(sid)
    if title is not None and (not title.strip() or len(title.strip()) > TITLE_MAX):
        raise PlaceError("--title: 1–%d자여야 해요" % TITLE_MAX)
    if group is not None and not group.strip():
        raise PlaceError("--group: 빈 이름이에요")
    screens = [dict(s) if isinstance(s, dict) else s for s in data["screens"]]
    ids = [s.get("id") if isinstance(s, dict) else None for s in screens]
    old_i = ids.index(sid) if sid in ids else None
    if old_i is not None and not replace:
        raise PlaceError("이미 있는 화면 id 예요: %s — 바꾸려면 --replace, 새로 넣으려면 다른 --id" % sid)
    old = screens[old_i] if old_i is not None else None
    ps, ss = pos_map(state), size_map(state)

    anchor = None
    if after is not None:
        if after == sid:
            raise PlaceError("--after 가 넣는 화면 자신이에요: %s" % after)
        if after not in ids:
            raise PlaceError("없는 화면이에요(--after): %s — 있는 화면: %s" % (after, ", ".join(i for i in ids if i) or "없음"))
        anchor = screens[ids.index(after)]
        if group is not None and group.strip() != anchor.get("group"):
            raise PlaceError("--after %s 는 '%s' 줄에 있어요 — --group 을 빼거나 그 줄 이름을 주세요" % (after, anchor.get("group") or "줄 없음"))

    if group is not None:
        g = group.strip()
    elif anchor is not None:
        g = anchor.get("group")
    elif old is not None:
        g = old.get("group")
    else:
        g = next((s.get("group") for s in reversed(screens) if isinstance(s, dict) and s.get("id") != sid), None)

    if old is not None:
        f = file_of(old)
    else:
        f = sid + ".html"
        if f in set(files):
            raise PlaceError("out 에 이미 그 파일이 있어요: %s — 다른 --id 를 주거나(화면이면 --replace)" % f)

    entry = dict(old) if old is not None else {}
    entry.update({"id": sid, "file": f, "title": (title.strip() if title is not None else
                                                  (old or {}).get("title") or html_title or sid)})
    if g is not None:
        entry["group"] = g
    else:
        entry.pop("group", None)
    if purpose is not None:
        entry["purpose"] = purpose.strip()

    rest = [s for k, s in enumerate(screens) if k != old_i]
    rids = [s.get("id") if isinstance(s, dict) else None for s in rest]
    if anchor is not None:
        at_i = _end_of(rest, rids.index(after), after) + 1
    elif old is not None and old.get("group") == g:
        at_i = old_i
    else:
        same = [k for k, s in enumerate(rest) if isinstance(s, dict) and s.get("group") == g and g is not None]
        at_i = same[-1] + 1 if same else len(rest)
        if same:
            at_i = _end_of(rest, same[-1], rest[same[-1]]["id"]) + 1
    new_screens = rest[:at_i] + [entry] + rest[at_i:]

    out = dict(data, screens=new_screens)
    groups = list(data.get("groups") or []) if isinstance(data.get("groups"), list) else []
    group_added = g is not None and g not in groups
    if group_added:
        groups.append(g)
    if group_added or "groups" in data:
        out["groups"] = groups

    if at is not None:
        pos, pos_from = {"dx": at[0], "dy": at[1], "g": g}, "at"
    elif anchor is not None:
        p = ps.get(after)
        pos, pos_from = ({"dx": p["dx"], "dy": p["dy"], "g": g} if p and (p.get("g") in (None, g)) else None), "after"
    elif old is not None and old.get("group") == g:
        pos, pos_from = "keep", "keep"
    else:
        pos, pos_from = None, "none"
    if pos is None and sid not in ps:
        pos = "keep"                                   # 지울 것도 없다

    if size is not None:
        z, size_from = dict(size), "size"
    elif anchor is not None and ss.get(after):
        z, size_from = dict(ss[after]), "after"
    elif old is not None:
        z, size_from = "keep", "keep"
    else:
        z = _common_size([s.get("id") for s in rest if isinstance(s, dict) and s.get("group") == g], ss)
        size_from = "group" if z else "none"
        if z is None:
            z = "keep"
    return {"data": out, "entry": entry, "file": f, "replaced": old is not None, "group_added": group_added,
            "pos": pos, "size": z, "pos_from": pos_from, "size_from": size_from}


def state_patch(state, sid, pos, size):
    """계획의 pos/size → PUT /api/state 의 state 몸통 {card-pos?, card-size?}(바뀐 이름만, 통째 값) | {}(바꿀 것 없음).
    state 는 지금 상태(409 뒤 다시 읽은 것) — 다른 카드의 값은 그대로 둔다."""
    patch = {}
    for name, v in (("card-pos", pos), ("card-size", size)):
        if v == "keep":
            continue
        raw = state.get(name) if isinstance(state, dict) else None
        cur = dict(raw) if isinstance(raw, dict) else {}
        if v is None:
            if sid not in cur:
                continue
            cur.pop(sid)
        else:
            if cur.get(sid) == v:
                continue
            cur[sid] = v
        patch[name] = cur
    return patch


def asset_rel(src_dir_parts, asset_parts):
    """원본 화면 폴더(조각 목록)와 첨부 파일 경로(조각 목록) → out 안에 둘 '/' 경로.
    첨부가 원본 화면 폴더 안이면 그 상대 경로(화면 HTML 의 상대 링크가 그대로 닿게), 아니면 파일 이름만. '..' 은 만들지 않는다."""
    n = len(src_dir_parts)
    if len(asset_parts) > n and [p.casefold() for p in asset_parts[:n]] == [p.casefold() for p in src_dir_parts]:
        return "/".join(asset_parts[n:])
    return asset_parts[-1]
