"""Model — 대화 기록(S3)의 한 줄 모양 · 턴 붙이기 · 한도. 파일·시계·네트워크를 쓰지 않는다(tests/test_canvas_unit_chat_log_py.py).

<out>/.hd-chat.jsonl 한 줄 = 기록 하나 {seq, at(ms), turn, kind, …}. 파일 I/O 는 chat_store.ChatLog, 주소는 router(GET/POST /api/chat).
기록은 세션이 이미 내는 이벤트에서 만든다(from_event) — request.sent → sent · agent.progress → progress(터미널에서 에이전트가 알린 줄) ·
agent.reply → reply · ai.write(act record) → write · build.done → built · build.failed → failed. 캔버스가 직접 남기는 것(check_post): ask(보낸 글·칩) · undone(턴 되돌림).
턴(turn) = 요청 하나 = 처음 기록의 seq. 붙이기(assign):
  ask · sent → 메모 id 가 겹치는 턴(없으면 새 턴) · reply → 그 메모의 턴(모르면 마지막 턴) · progress · write → 마지막 턴(없으면 새 턴) ·
  built → 마지막 턴이 열려 있을 때만(OPEN_MS 안 — 사람 편집의 빌드가 지난 턴에 붙지 않게, 아니면 버림) · failed → 열린 마지막 턴, 아니면 새 턴(빨간 줄은 늘 보인다) ·
  undone → 받은 turn 이 있으면 그 턴(없으면 버림). '열림' = 마지막 턴의 마지막 기록(built 빼고)이 OPEN_MS 안.
한도: 턴이 CAP + SLACK 을 넘으면 오래된 턴의 기록을 보관 파일(.hd-chat-archive.jsonl)로(trim) — 메모 보관과 같은 방식.
"""
import json

FILE = ".hd-chat.jsonl"
ARCHIVE = ".hd-chat-archive.jsonl"
CAP = 500                                            # 남길 턴 수
SLACK = 50                                           # 이만큼 넘치면 한 번에 옮긴다(덧붙일 때마다 다시 쓰지 않게)
OPEN_MS = 10 * 60 * 1000                             # 마지막 턴이 '열림'인 시간(빌드 줄 붙이기)
NOTES_MAX = 200
FULL = 51000                                         # 대화 패널은 늘 전문(R24 · login#7) — 이 한도는 터무니없는 글만 막는다. reply = 요약 칸(≤280) + 빈 줄 + detail(hd_model.DETAIL_MAX 50000, R26)
CUT = {"text": FULL, "progress": FULL, "reply": FULL, "reason": FULL, "label": 2000, "chip": 60}   # 예전 text 2000 · progress 300 · reason 300 · label 120 은 패널 글을 잘랐다. chip = 이름표(글 아님)
CHIPS_MAX = 20
KINDS = ("ask", "sent", "progress", "reply", "write", "built", "failed", "undone")


def _s(v, n=None):
    """글이면 앞뒤 공백을 걷고 n 자까지, 아니면 None."""
    if not isinstance(v, str):
        return None
    v = v.strip()
    return (v[:n] if n else v) or None


def _ids(v):
    return [x for x in v if isinstance(x, str) and x][:NOTES_MAX] if isinstance(v, list) else []


def reply_text(reply):
    """POST /api/reply 의 reply → 보일 글(다, R24) | None — 답변 = text · 반영됨 = what · 일부 = done · 질문 = question,
    그리고 자세한 설명 detail 이 있으면 빈 줄 뒤에 붙인다(요약 칸은 프로토콜이 짧게 받고, 긴 설명은 detail — 대화 패널이 다 보인다)."""
    if not isinstance(reply, dict):
        return None
    head = None
    for k in ("text", "what", "done", "question"):
        head = _s(reply.get(k), CUT["reply"])
        if head:
            break
    detail = _s(reply.get("detail"), CUT["reply"])
    if head and detail and detail != head:
        return head + "\n\n" + detail
    return head or detail


def from_event(ev):
    """세션 이벤트 → (kind, 칸들) | None(기록하지 않음). 모양이 틀린 칸은 버린다(기록은 보이기 위한 것 — 진실은 이벤트·파일)."""
    if not isinstance(ev, dict):
        return None
    t = ev.get("type")
    if t == "request.sent":
        return "sent", {"notes": _ids(ev.get("notes")), "to": _s(ev.get("to")), "via": _s(ev.get("via")) or "queue",
                        "text": _s(ev.get("text"), CUT["text"])}
    if t == "agent.progress":
        text = _s(ev.get("text"), CUT["progress"])
        return ("progress", {"agent": _s(ev.get("agent")), "text": text, "screen": _s(ev.get("screen"))}) if text else None
    if t == "agent.reply":
        return "reply", {"note": _s(ev.get("note")), "rkind": _s(ev.get("kind")) or "", "status": _s(ev.get("status")) or "",
                         "screen": _s(ev.get("screen")), "agent": _s(ev.get("agent")), "text": _s(ev.get("text"), CUT["reply"])}
    if t == "ai.write":
        if ev.get("act") != "record" or not _s(ev.get("stamp")):
            return None                              # update = 같은 줄의 되살리기 기준만 옮김(새 줄 아님)
        return "write", {"screen": _s(ev.get("screen")), "label": _s(ev.get("label"), CUT["label"]), "stamp": _s(ev.get("stamp"))}
    if t == "build.done":
        return "built", {"screens": _ids(ev.get("screens"))}
    if t == "build.failed":
        return "failed", {"reason": _s(ev.get("reason"), CUT["reason"]) or "", "screens": _ids(ev.get("screens"))}
    return None


def check_post(body):
    """POST /api/chat 본문 → ((kind, 칸들), None) | (None, 한국어 오류).
    ask = {kind:'ask', text, notes:[메모 id], chips?:[글], screens?:[화면 id], agent?:이름} · undone = {kind:'undone', turn:int}."""
    if not isinstance(body, dict):
        return None, "JSON 객체가 아니에요"
    k = body.get("kind")
    if k == "ask":
        text = _s(body.get("text"), CUT["text"])
        if not text:
            return None, "text: 보낸 글이 없어요"
        notes = body.get("notes", [])
        if not isinstance(notes, list) or len(notes) > NOTES_MAX or not all(isinstance(n, str) and n for n in notes):
            return None, "notes: 메모 id 글 목록(%d개까지)이어야 해요" % NOTES_MAX
        chips = body.get("chips", [])
        if not isinstance(chips, list) or not all(isinstance(c, str) for c in chips):
            return None, "chips: 글 목록이어야 해요"
        return ("ask", {"text": text, "notes": list(notes), "chips": [c[:CUT["chip"]] for c in chips if c.strip()][:CHIPS_MAX],
                        "screens": _ids(body.get("screens")), "agent": _s(body.get("agent"), CUT["label"])}), None
    if k == "undone":
        turn = body.get("turn")
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
            return None, "turn: 1 이상 정수여야 해요"
        return ("undone", {"turn_of": turn}), None
    return None, "kind: ask 또는 undone 이어야 해요"


def empty():
    return {"seq": 0, "notes": {}, "turns": set(), "last": None, "at": None}


def index(records):
    """파일에서 읽은 기록들 → 붙이기 상태(다음 seq · 메모 → 턴 · 있는 턴 · 마지막 턴 · 그 마지막 시각)."""
    idx = empty()
    for r in records:
        _note(idx, r)
    return idx


def _note(idx, r):
    idx["seq"] = max(idx["seq"], r["seq"])
    idx["turns"].add(r["turn"])
    for n in r.get("notes") or []:
        idx["notes"].setdefault(n, r["turn"])
    if r["kind"] != "built" and r["kind"] != "undone" and (idx["last"] is None or r["turn"] >= idx["last"]):
        idx["last"], idx["at"] = r["turn"], r["at"]   # 옛 턴에 늦게 온 답은 마지막 턴을 되돌리지 않는다(턴 id 는 커지기만 한다)


def is_open(idx, at):
    return idx["last"] is not None and idx["at"] is not None and at - idx["at"] <= OPEN_MS


def assign(idx, kind, fields, at):
    """(붙이기 상태, kind, 칸들, 시각 ms) → (기록 | None(버림), 새 상태). 상태는 고쳐 쓴다(세션이 자물쇠 안에서 하나만 가진다)."""
    if kind not in KINDS:
        return None, idx
    seq = idx["seq"] + 1
    f = dict(fields)
    turn = None
    if kind in ("ask", "sent"):
        turn = next((idx["notes"][n] for n in f.get("notes") or [] if n in idx["notes"]), None)
    elif kind == "reply":
        turn = idx["notes"].get(f.get("note")) or idx["last"]
    elif kind in ("progress", "write"):
        turn = idx["last"]
    elif kind == "built":
        if not is_open(idx, at):
            return None, idx
        turn = idx["last"]
    elif kind == "failed":
        turn = idx["last"] if is_open(idx, at) else None
    elif kind == "undone":
        turn = f.pop("turn_of", None)
        if turn not in idx["turns"]:
            return None, idx
    rec = dict({"seq": seq, "at": int(at), "turn": turn or seq, "kind": kind}, **{k: v for k, v in f.items() if v is not None})
    _note(idx, rec)
    return rec, idx


def turn_order(records):
    """처음 나온 차례대로 턴 id 들."""
    seen, out = set(), []
    for r in records:
        if r["turn"] not in seen:
            seen.add(r["turn"])
            out.append(r["turn"])
    return out


def over(records, cap=CAP, slack=SLACK):
    return len(turn_order(records)) > cap + slack


def trim(records, cap=CAP):
    """→ (남길 기록, 보관으로 옮길 기록) — 가장 새 cap 개 턴만 남긴다(기록 차례 그대로)."""
    order = turn_order(records)
    if len(order) <= cap:
        return list(records), []
    old = set(order[:len(order) - cap])
    return [r for r in records if r["turn"] not in old], [r for r in records if r["turn"] in old]


def _ok(r):
    return (isinstance(r, dict) and r.get("kind") in KINDS and all(isinstance(r.get(k), int) and not isinstance(r.get(k), bool) for k in ("seq", "at", "turn")))


def parse_lines(lines):
    """파일 줄들 → (기록들 seq 차례, 깨진 줄 수). 빈 줄은 세지 않는다."""
    recs, bad = [], 0
    for ln in lines:
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            bad += 1
            continue
        if _ok(r):
            recs.append(r)
        else:
            bad += 1
    recs.sort(key=lambda r: r["seq"])
    return recs, bad


def line(rec):
    return json.dumps(rec, ensure_ascii=False, separators=(",", ":"))


def parse_since(v):
    """?since= 값 → None(없음 = 다) | 0 이상 정수. 그 밖 = ValueError(400)."""
    if v is None or v == "":
        return None
    s = str(v).strip()
    if not s.isdigit():
        raise ValueError("since: 0 이상 정수여야 해요")
    return int(s)


def since(records, want, seq):
    """GET /api/chat 답 → {seq, records[, reset]} — want 뒤의 기록. want 가 지금 seq 보다 크면(파일이 새로 시작) 다 + reset."""
    if want is None:
        return {"seq": seq, "records": list(records)}
    if want > seq:
        return {"seq": seq, "records": list(records), "reset": True}
    return {"seq": seq, "records": [r for r in records if r["seq"] > want]}
