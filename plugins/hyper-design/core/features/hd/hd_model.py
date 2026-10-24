"""Model — 메모 답(reply) 규칙·상태·번호·줄 만들기. 순수: 파일·네트워크·시계를 쓰지 않는다(tests/test_hd_model.py 의 순수성 검사).

답 = {kind, by, at, ...칸, detail?} (tasks/PLAN-2026-10-23.md §3). AI 답 다섯 가지, 사람 답 두 가지(캔버스만).
상태는 저장하지 않고 늘 계산한다: 보내지 않음 → draft · 보냄 + 답 없음 → working · 마지막 답 질문 → decide · 일부 → partial ·
  반영됨/대체됨/답변/확인 → done · 다시 → draft.
번호: 메모의 `no`, 없으면 canvas modules/annotation.js 의 migrate 와 같은 규칙(그 화면에서 쓴 가장 큰 번호·note-seq 다음부터 목록 차례).
"""

AGENT_KINDS = ("반영됨", "일부", "대체됨", "답변", "질문")
USER_KINDS = ("확인", "다시")
KINDS = AGENT_KINDS + USER_KINDS
DONE = frozenset(("반영됨", "대체됨", "답변", "확인"))
STATUSES = ("draft", "working", "decide", "partial", "done")
OPEN = frozenset(("working", "decide", "partial"))   # 보냈고 아직 끝나지 않은 것

# 종류마다 칸: 이름 → (모양, 한도). str = 빈 글 아님 · screens = 화면 id 목록(1개 이상) · bool · choices = 2–4개 글
FIELDS = {
    "반영됨": {"what": ("str", 140), "screens": ("screens", None), "captured": ("bool", None)},
    "일부": {"done": ("str", 140), "left": ("str", 140)},
    "대체됨": {"where": ("str", 140)},
    "답변": {"text": ("str", 280)},
    "질문": {"question": ("str", 140), "choices": ("choices", 40)},
    "확인": {},
    "다시": {},
}
OPTIONAL = {"확인": {"answer": ("str", 40)}}   # 있어도 되는 칸: 사람이 질문에 고른 답으로 닫을 때(annotation.js OPTIONAL)
COMMON = {"kind", "by", "at", "detail"}
DETAIL_MAX = 2000
BY_MAX = 40
QUOTE_MAX = 60


def _str(v):
    return isinstance(v, str) and v.strip() != ""


def check_reply(reply, intent, agent=True, known_screens=None):
    """답 하나 검사 → 실패한 칸마다 한 줄 이유 목록(빈 목록 = 통과).
    agent=True 면 사람 답(확인·다시)을 받지 않는다. known_screens 가 있으면 반영됨.screens 의 id 가 그 안에 있어야 한다."""
    if not isinstance(reply, dict):
        return ["reply: 객체가 아니에요"]
    kind = reply.get("kind")
    if kind not in FIELDS:
        return ["kind: 모르는 종류 %r (가능: %s)" % (kind, ", ".join(AGENT_KINDS if agent else KINDS))]
    if agent and kind in USER_KINDS:
        return ["kind: %s 은 사람만 캔버스에서 달아요" % kind]
    errs = []
    if kind == "답변" and intent != "question":
        errs.append("kind: 답변은 질문 메모에만")
    spec, opt = FIELDS[kind], OPTIONAL.get(kind, {})
    for name in sorted(set(reply) - COMMON - set(spec) - set(opt)):
        errs.append("%s: %s 에 없는 칸" % (name, kind))
    for name, (shape, limit) in list(spec.items()) + [(k, v) for k, v in opt.items() if k in reply]:
        v = reply.get(name)
        if name not in reply:
            errs.append("%s: 없어요" % name)
        elif shape == "str":
            if not _str(v):
                errs.append("%s: 빈 글이 아니어야 해요" % name)
            elif len(v) > limit:
                errs.append("%s: %d자 넘음(%d자)" % (name, limit, len(v)))
        elif shape == "bool":
            if not isinstance(v, bool):
                errs.append("%s: true/false 여야 해요" % name)
        elif shape == "screens":
            if not isinstance(v, list) or not v or not all(_str(s) for s in v):
                errs.append("%s: 화면 id 1개 이상" % name)
            elif known_screens is not None and any(s not in known_screens for s in v):
                errs.append("%s: 없는 화면 %s" % (name, ", ".join(s for s in v if s not in known_screens)))
        elif shape == "choices":
            if not isinstance(v, list) or not 2 <= len(v) <= 4 or not all(_str(c) for c in v):
                errs.append("%s: 고를 것 2–4개(빈 글 아님)" % name)
            elif any(len(c) > limit for c in v):
                errs.append("%s: 하나마다 %d자 넘음" % (name, limit))
    if "detail" in reply and not (isinstance(reply["detail"], str) and len(reply["detail"]) <= DETAIL_MAX):
        errs.append("detail: %d자 이하 글" % DETAIL_MAX)
    if "by" in reply and not (_str(reply["by"]) and len(reply["by"]) <= BY_MAX):
        errs.append("by: 1–%d자 이름" % BY_MAX)
    if "at" in reply and not _str(reply["at"]):
        errs.append("at: ISO 시각 글")
    return errs


def stamp(reply, at, by=None):
    """보낼 답 → 저장할 답(새 객체): by(없으면 'agent')·at 을 찍는다."""
    r = dict(reply)
    r["by"] = by or (reply.get("by") if _str(reply.get("by")) else "agent")
    r["at"] = at
    return r


def replies(note):
    r = note.get("replies") if isinstance(note, dict) else None
    return r if isinstance(r, list) else []


def status(note):
    """메모 → draft | working | decide | partial | done (PLAN §3)."""
    if not isinstance(note, dict):
        return "draft"
    rs = replies(note)
    k = rs[-1].get("kind") if rs and isinstance(rs[-1], dict) else None
    if k == "확인":                                     # 사람이 닫은 것은 보냈든 아니든 완료 (annotation.js 와 같은 규칙)
        return "done"
    if not note.get("sent"):
        return "draft"                                  # 다시 열기는 sent 를 내리므로 여기서 draft
    if not rs:
        return "working"
    if k == "질문":
        return "decide"
    if k == "일부":
        return "partial"
    if k in DONE:
        return "done"
    return "working"                                    # 다시 연 뒤 다시 보냄 · 모르는 종류


def _pos(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def numbers(notes, seq=None):
    """메모 목록 → 같은 차례의 번호 목록(화면 없는 메모는 None). annotation.migrate 와 같은 규칙, 메모는 고치지 않는다."""
    s = {}
    if isinstance(seq, dict):
        for k, v in seq.items():
            if _pos(v):
                s[k] = int(v)
    for n in notes:
        if isinstance(n, dict) and n.get("screen") is not None and _pos(n.get("no")):
            sid = str(n["screen"])
            if not s.get(sid, 0) >= n["no"]:
                s[sid] = n["no"]
    out = []
    for n in notes:
        if not isinstance(n, dict) or n.get("screen") is None:
            out.append(None)
        elif _pos(n.get("no")):
            out.append(n["no"])
        else:
            sid = str(n["screen"])
            s[sid] = s.get(sid, 0) + 1
            out.append(s[sid])
    return out


def parse_ref(text):
    """'home#3' → {'screen':'home','no':3} · 그 밖 → 메모 id 글."""
    head, sep, tail = str(text).rpartition("#")
    if sep and head and tail.isdigit() and int(tail) > 0:
        return {"screen": head, "no": int(tail)}
    return str(text)


def find(notes, ref, seq=None):
    """ref(메모 id | {screen, no}) → 목록 안 차례 | None."""
    if isinstance(ref, dict):
        nos = numbers(notes, seq)
        for i, n in enumerate(notes):
            if isinstance(n, dict) and str(n.get("screen")) == str(ref.get("screen")) and nos[i] == ref.get("no"):
                return i
        return None
    for i, n in enumerate(notes):
        if isinstance(n, dict) and n.get("id") is not None and str(n.get("id")) == str(ref):
            return i
    return None


def target(note):
    """메모 → (경로, 인용 글, 대상 수). 여러 요소 메모는 첫 대상."""
    ts = note.get("targets") if isinstance(note.get("targets"), list) and note.get("targets") else [note]
    t = ts[0] if isinstance(ts[0], dict) else {}
    return str(t.get("path") or ""), " ".join(str(t.get("text") or "").split()), len(ts)


def rows(notes, seq=None):
    """메모 목록 → 줄 객체 목록(--json 의 모양)."""
    out = []
    for n, no in zip(notes, numbers(notes, seq)):
        if not isinstance(n, dict):
            continue
        path, quote, k = target(n)
        out.append({"id": n.get("id"), "screen": n.get("screen"), "no": no, "status": status(n), "intent": n.get("intent"),
                    "sent": bool(n.get("sent")), "edit": n.get("edit"), "scope": n.get("scope") or "element", "target": {"path": path, "quote": quote, "count": k},
                    "text": n.get("note") or "", "replies": replies(n)})
    return out


def pick(rs, which="open"):
    """open = 보냈고 끝나지 않음 · sent = 보낸 것 전부 · all = 전부."""
    if which == "all":
        return list(rs)
    if which == "sent":
        return [r for r in rs if r["sent"]]
    return [r for r in rs if r["status"] in OPEN]


def _cut(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def says(r):
    """답 한 줄(사람이 읽는 글). 앞부분은 canvas annotation.says 와 같은 말이고, 캔버스가 따로 보여 주는 것을 터미널에선 뒤에 붙인다:
    반영됨 → ' · 캡처 확인함|안 봄'(캔버스는 annotation.tip 툴팁) · 질문 → ' (a / b)'(캔버스는 고를 것 단추)."""
    if not isinstance(r, dict):
        return ""
    k = r.get("kind")
    lst = lambda a: ", ".join(str(x) for x in a) if isinstance(a, list) else ""
    if k == "반영됨":
        return "반영됨 — %s%s · 캡처 %s" % (r.get("what", ""), " · " + lst(r.get("screens")) if lst(r.get("screens")) else "",
                                          "확인함" if r.get("captured") else "안 봄")
    if k == "일부":
        return "일부 — %s · 남은 것 %s" % (r.get("done", ""), r.get("left", ""))
    if k == "대체됨":
        return "대체됨 → %s" % r.get("where", "")
    if k == "답변":
        return "답변 — %s" % r.get("text", "")
    if k == "질문":
        ch = r.get("choices") if isinstance(r.get("choices"), list) else []
        return "질문 — %s%s" % (r.get("question", ""), " (%s)" % " / ".join(str(c) for c in ch) if ch else "")
    if k == "확인":
        return "완료함" + (" — 고름: %s" % r["answer"] if _str(r.get("answer")) else "")
    if k == "다시":
        return "다시 엶"
    return str(k or "")


SCOPES = {"screen": "이 화면", "all": "모든 화면"}   # n.scope(canvas R7) — 없거나 element 면 요소 메모(표시 안 함)


def scope_word(scope):
    """n.scope → '이 화면' | '모든 화면' | None(element·없음·모르는 값)."""
    return SCOPES.get(scope) if isinstance(scope, str) else None


def format_rows(rs):
    """줄 객체 → 사람이 읽는 글: `screen #no · status · intent · target · text`, 답은 들여 쓴 줄."""
    lines = []
    for r in rs:
        t = r["target"]
        tgt = _cut(t["path"].split(" > ")[-1] if t["path"] else "", 40)
        if t["quote"]:
            tgt += ' "%s"' % _cut(t["quote"], QUOTE_MAX)
        if t["count"] > 1:
            tgt += " +%d" % (t["count"] - 1)
        sw = scope_word(r.get("scope"))
        lines.append("%s #%s · %s · %s · %s%s · %s" % (r["screen"], r["no"], r["status"], r["intent"] or "-", tgt.strip() or "(화면 전체)",
                                                      " · 범위: " + sw if sw else "", " ".join(str(r["text"]).split())))
        for x in r["replies"]:
            lines.append("    ↳ %s  (%s %s)" % (says(x), x.get("by", "?") if isinstance(x, dict) else "?", x.get("at", "") if isinstance(x, dict) else ""))
    return "\n".join(lines) if lines else "(메모 없음)"


def project_name(out_name, parent_name):
    """실행 폴더 이름: out 폴더 이름이 'out' 이면 그 위 폴더, 아니면 out 자기 이름."""
    return parent_name if out_name == "out" else out_name


def format_canvases(cs):
    """[{project, url, agent, open}] → 줄."""
    if not cs:
        return "(떠 있는 캔버스 없음)"
    return "\n".join("%s · %s · %s · 열린 메모 %s" % (c["project"], c["url"], c.get("agent") or "-", c.get("open", "?")) for c in cs)


# ---------------------------------------------------------------- 왕복(round-trip): wait · attach · stop/attach/wait 대상 고르기
AGENT_MAX = 128


def pending(state):
    """상태 파일의 state({notes, note-seq}) → 기다리는 메모 줄 객체(status == working: 보냄 + 답 없음). hd wait 가 쓴다."""
    st = state if isinstance(state, dict) else {}
    notes = st.get("notes") if isinstance(st.get("notes"), list) else []
    return [r for r in rows(notes, st.get("note-seq")) if r["status"] == "working"]


def agent_error(agent):
    """보내기 받을 에이전트 id 검사 → 한 줄 이유 | None(통과). None = 떼기(대기열 파일로)."""
    if agent is None:
        return None
    if not isinstance(agent, str) or agent == "":
        return "agent: 빈 글이 아닌 id 또는 null 이어야 해요"
    if len(agent) > AGENT_MAX:
        return "agent: %d자 넘음(%d자)" % (AGENT_MAX, len(agent))
    if any(c.isspace() for c in agent):
        return "agent: 띄어쓰기·줄바꿈 없는 id 여야 해요"
    return None


def listing(ms):
    return "; ".join("%s (%s)" % (m.get("project"), m.get("out")) for m in ms) or "없음"


def choose(alive, ref=None, keys=(), stale=(), key=str):
    """대상 캔버스 고르기 → (표지, None) | (None, 한 줄 이유).
    ref 없음 → 살아 있는 것이 하나뿐일 때만. ref 있음 → project 이름이 같거나 key(out) 이 keys 안에 있는 살아 있는 것,
    없으면 stale(응답 없는 표지) 중에서. 여럿이면 목록과 함께 이유."""
    def hit(m):
        return isinstance(m, dict) and (m.get("project") == ref or key(m.get("out") or "") in keys)
    if ref is None:
        pool = [m for m in alive if isinstance(m, dict)]
        if not pool:
            return None, "떠 있는 캔버스가 없어요"
    else:
        pool = [m for m in alive if hit(m)] or [m for m in stale if hit(m)]
        if not pool:
            return None, "'%s' 캔버스가 떠 있지 않아요 — 떠 있는 것: %s" % (ref, listing(alive))
    if len(pool) > 1:
        return None, "캔버스가 여럿이에요 — 하나를 고르세요(이름 또는 out 경로): %s" % listing(pool)
    return pool[0], None


# ---------------------------------------------------------------- 덮개(hd claim · release, #254) — 상태 파일 state.busy = canvas modules/busy.js 와 같은 모양
BUSY_VIA = ("paseo", "queue", "cli")                 # canvas HD.busy.VIA 와 같게(drift 는 canvas unit 테스트가 본다)
CLAIM_NOTE_MAX = 140


def claim_error(screen, by=None, note=None):
    """hd claim 인자 검사 → 한 줄 이유 | None."""
    if not isinstance(screen, str) or not screen.strip():
        return "screen: 화면 id 가 없어요"
    if by is not None and agent_error(by):
        return agent_error(by).replace("agent:", "by:", 1)
    if note is not None and (not isinstance(note, str) or not note.strip()):
        return "note: 빈 글이에요"
    if note is not None and len(note) > CLAIM_NOTE_MAX:
        return "note: %d자 넘음(%d자)" % (CLAIM_NOTE_MAX, len(note))
    return None


def busy_items(value):
    """state.busy 값 → (항목 dict, 경고 목록). 없으면 빈 것 · 깨진 값·항목은 버리고 경고 한 줄씩(canvas busy.load 와 같은 규칙)."""
    if value is None:
        return {}, []
    if not isinstance(value, dict) or value.get("v") != 1 or not isinstance(value.get("items"), dict):
        return {}, ["[hd] 상태 파일의 busy 가 깨져 비웠어요"]
    items, warns = {}, []
    for k, it in value["items"].items():
        if not isinstance(it, dict) or it.get("via") not in BUSY_VIA or not isinstance(it.get("file"), str) or not it["file"]:
            warns.append("[hd] busy 항목이 깨져 건너뛰어요: %s" % k)
            continue
        items[k] = it
    return items, warns


def claim(value, screen, file, since, mtime=None, by=None, note=None):
    """덮개 하나 씌우기 → (새 busy 값, 경고). cli 덮개 = {via:'cli', since(ms), file, mtime(기준 — 지금 파일 시각), by?, note?}."""
    items, warns = busy_items(value)
    it = {"via": "cli", "since": since, "file": file, "mtime": mtime}
    if by:
        it["by"] = by
    if note:
        it["note"] = note.strip()
    items = dict(items, **{screen: it})
    return {"v": 1, "items": items}, warns


def release(value, screen):
    """덮개 하나 걷기 → (새 busy 값, 걷었나, 경고)."""
    items, warns = busy_items(value)
    if screen not in items:
        return {"v": 1, "items": items}, False, warns
    items = {k: v for k, v in items.items() if k != screen}
    return {"v": 1, "items": items}, True, warns


# ---------------------------------------------------------------- 한 out 에 도우미 하나(#271) — <out>/.hd-helper.json 풀기 · 띄울지 정하기
def _port(v):
    return v if type(v) is int and 0 < v < 65536 else None


def helper_record(doc):
    """.hd-helper.json 의 객체 → {port, pid, url, token}(모르는 칸 None) | None(객체가 아님).
    살아 있는 동안 = {url, pid, port, token} · 정상 종료 뒤 = {port}(다음에 같은 포트로 뜨게, #270). 옛 모양 {url, pid} 는 url 에서 포트·토큰을 읽는다."""
    if not isinstance(doc, dict):
        return None
    url = doc.get("url") if isinstance(doc.get("url"), str) and doc.get("url") else None
    port, token = _port(doc.get("port")), doc.get("token") if isinstance(doc.get("token"), str) and doc.get("token") else None
    if url and (port is None or token is None):       # http://127.0.0.1:<port>/index.html?hd=<token>
        host = url.split("://", 1)[-1].split("/", 1)[0]
        p = host.rsplit(":", 1)[-1] if ":" in host else ""
        port = port if port is not None else _port(int(p)) if p.isdigit() else None
        q = url.split("?hd=", 1)[1] if "?hd=" in url else url.split("&hd=", 1)[1] if "&hd=" in url else ""
        token = token or q.split("&", 1)[0].split("#", 1)[0] or None
    pid = doc.get("pid") if type(doc.get("pid")) is int and doc.get("pid") > 0 else None
    return {"port": port, "pid": pid, "url": url, "token": token}


def start_verdict(rec, alive, answers):
    """도우미를 띄우기 전 → 'refuse'(그 pid 가 살아 있고 그 주소가 답함 — 같은 out 에 둘째 쓰는 곳을 만들지 않는다) | 'start'.
    기록 없음 · url 없음(정상 종료) · 죽은 pid · 답 없는 주소(pid 번호를 다른 프로그램이 받았거나 멈춘 도우미) = start(기록을 덮어씀)."""
    if not rec or not rec.get("url") or not rec.get("pid"):
        return "start"
    return "refuse" if alive and answers else "start"
