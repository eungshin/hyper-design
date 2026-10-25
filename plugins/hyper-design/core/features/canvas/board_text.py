"""Model — 판 글 고치기·지우기 계획(t51-9): 판 위 소개 글(screens.json story·people · decisions.json core·items)을 캔버스 편집 하나로 바꾼다.
데이터 → 데이터 — 파일·네트워크를 쓰지 않는다(쓰기는 session.apply_edits 의 'board' 편집). 규칙은 modules/board-text.js 와 같다.

편집 = {op: 'set', to: 칸 키, value: 글} | {op: 'delete', to: 묶음 키}
  칸 키 = 판에 보이는 차례(board_data.index_data 의 hd-data 와 같은 자리):
    story.headline · story.summary · story.ideas.N.title|desc · people.N.name|why|win ·
    decisions.core · decisions.items.N.name|how|why(N = 판에 보인 정한 것 차례) · decisions.market.N.name(N = 판에 보인 시장 관례 차례)
  묶음 키 = story(제목·요약) · ideas · people · decisions(core + 판에 나오는 정한 것 전부) · market(시장 관례 전부)
plan(screens, decisions, edit) → {"screens": 새 screens.json | None(그대로), "decisions": 새 decisions.json | None}
  잘못된 요청 = BoardError(한국어 이유, reason 'invalid'|'missing') — 아무것도 바꾸지 않는다.
"""
import copy, re

MAX_CHARS = 2000
LABEL = ("lighten", "cut", "later")                  # build_canvas 의 정한 것 판정(그 밖은 판에 안 나옴)
KEY = re.compile(r"^(story\.(headline|summary)|story\.ideas\.(\d+)\.(title|desc)|people\.(\d+)\.(name|why|win)|"
                 r"decisions\.core|decisions\.items\.(\d+)\.(name|how|why)|decisions\.market\.(\d+)\.name)$")
BLOCKS = ("story", "ideas", "people", "decisions", "market")
LINE = re.compile(r"\.(headline|title|name)$")      # 한 줄 칸 — 빈칸(줄바꿈 포함)을 한 칸으로
NAMED = re.compile(r"\.(title|name)$")              # 비울 수 없는 칸 — 지우려면 묶음을 지운다
SHOWN = {"ideas": 3, "people": 4, "items": 6, "market": 6}   # build_canvas 가 판에 싣는 수


class BoardError(Exception):
    def __init__(self, msg, reason="invalid"):
        super().__init__(msg)
        self.reason = reason


def normalise(key, text):
    s = "" if text is None else str(text)
    if LINE.search(key):
        return re.sub(r"\s+", " ", s).strip()
    return re.sub(r" *\n *", "\n", re.sub(r"[ \t]+", " ", s.replace("\r\n", "\n").replace("\r", "\n"))).strip()


def shown_items(dec):
    """판에 보이는 정한 것 → decisions.json items 번호(차례대로, 전부 — 판은 앞 6개)."""
    its = dec.get("items") or []
    return [i for i, x in enumerate(its) if isinstance(x, dict) and x.get("verdict") in LABEL and x.get("source") != "시장"]


def shown_market(dec):
    """판에 보이는 시장 관례 → items 번호(벗어난 것 먼저, 그다음 따른 것 — build_canvas 와 같은 차례)."""
    its = dec.get("items") or []
    mk = [i for i, x in enumerate(its) if isinstance(x, dict) and x.get("source") == "시장" and str(x.get("id", "")).startswith("M")]
    return sorted(mk, key=lambda i: its[i].get("verdict") == "keep")


def _at(lst, n, what, cap):
    if not isinstance(lst, list) or n >= min(len(lst), cap) or not isinstance(lst[n], dict):
        raise BoardError("판에 없는 %s %d번째 항목이에요 — 화면을 새로 불러와 주세요" % (what, n + 1), "missing")
    return lst[n]


def _need_dec(dec):
    if not isinstance(dec, dict):
        raise BoardError("decisions.json 이 없어요", "missing")


def plan(screens, decisions, edit):
    if not isinstance(screens, dict):
        raise BoardError("screens.json 을 읽지 못했어요", "missing")
    edit = edit if isinstance(edit, dict) else {}
    op, to = edit.get("op"), str(edit.get("to") or "")
    sj, dj = copy.deepcopy(screens), copy.deepcopy(decisions) if isinstance(decisions, dict) else decisions
    if op == "delete":
        return _delete(sj, dj, to)
    if op != "set":
        raise BoardError("모르는 판 글 편집: %r" % op)
    m = KEY.match(to)
    if not m:
        raise BoardError("고칠 수 없는 판 글 칸: %s" % to)
    v = edit.get("value")
    if not isinstance(v, str):
        raise BoardError("판 글은 글이어야 해요")
    v = normalise(to, v)
    if len(v) > MAX_CHARS:
        raise BoardError("판 글이 %d자를 넘어요" % MAX_CHARS)
    if not v and NAMED.search(to):
        raise BoardError("이름은 비울 수 없어요 — 지우려면 그 묶음을 고르고 Delete")
    p = to.split(".")
    if p[0] == "story":
        st = sj.get("story")
        if not isinstance(st, dict):
            raise BoardError("screens.json 에 소개(story)가 없어요", "missing")
        if p[1] == "ideas":
            _at(st.get("ideas"), int(p[2]), "아이디어", SHOWN["ideas"])[p[3]] = v
        else:
            st[p[1]] = v
        return {"screens": sj, "decisions": None}
    if p[0] == "people":
        _at(sj.get("people"), int(p[1]), "사람", SHOWN["people"])[p[2]] = v
        return {"screens": sj, "decisions": None}
    _need_dec(dj)
    if p[1] == "core":
        dj["core"] = v
    else:
        idx = shown_items(dj) if p[1] == "items" else shown_market(dj)
        n = int(p[2])
        if n >= min(len(idx), SHOWN[p[1]]):
            raise BoardError("판에 없는 %s %d번째 항목이에요 — 화면을 새로 불러와 주세요" % ("정한 것" if p[1] == "items" else "시장 관례", n + 1), "missing")
        dj["items"][idx[n]][p[3]] = v
    return {"screens": None, "decisions": dj}


def _delete(sj, dj, to):
    if to not in BLOCKS:
        raise BoardError("지울 수 없는 판 글 묶음: %s" % to)
    if to in ("story", "ideas"):
        st = sj.get("story")
        keys = ("headline", "summary") if to == "story" else ("ideas",)
        if not isinstance(st, dict) or not any(st.get(k) for k in keys):
            raise BoardError("이미 없는 판 글이에요", "missing")
        for k in keys:
            st.pop(k, None)
        if not st:
            sj.pop("story", None)
        return {"screens": sj, "decisions": None}
    if to == "people":
        if not sj.get("people"):
            raise BoardError("이미 없는 판 글이에요", "missing")
        sj.pop("people", None)
        return {"screens": sj, "decisions": None}
    _need_dec(dj)
    drop = set(shown_items(dj) if to == "decisions" else shown_market(dj))
    if not drop and not (to == "decisions" and dj.get("core")):
        raise BoardError("이미 없는 판 글이에요", "missing")
    dj["items"] = [x for i, x in enumerate(dj.get("items") or []) if i not in drop]
    if to == "decisions":
        dj.pop("core", None)
    return {"screens": None, "decisions": dj}
