"""Model(순수) — 터미널 대화 기록(transcript) 한 형식씩 읽기(S3b): 바이트·글 → 대화 줄(entry). 파일·하위 프로세스·시계를 모른다(unit).

entry = {id: 바뀌지 않는 글, role: 'user'|'assistant'|'tool', text: 글(tool = 한 줄 요약 'Edit screens/home.html'), at: ISO-8601 | ''}
  parse_claude(data, max_entries)  Claude Code 세션 jsonl 조각 → (entries, 먹은 바이트). 끝의 덜 쓴 줄(줄바꿈 없음)은 먹지 않는다 — 다음에 다시
  parse_paseo(text)                `paseo logs <id> --json` 출력 → entries(모양을 너그럽게 읽는다 — contract/transcripts.md '빚')
  tool_summary(name, input)        도구 부르기 → 한 줄 요약
  claude_cursor / paseo_cursor      불투명 커서 글 ↔ 값(깨진 커서 = ValueError — 부르는 쪽이 400)
상태 없음. 쓰는 곳 = transcripts.py(ClaudeTranscript · PaseoTranscript).
"""
import datetime, hashlib, json, re

TEXT_MAX = 4000                                      # 줄 하나의 글 최대(넘으면 자르고 '…')
TOOL_MAX = 120                                       # 도구 요약 한 줄 최대
ENTRIES_MAX = 100                                    # read() 한 번에 내는 줄 최대
ROLES = ("user", "assistant", "tool")

# 사용자 차례지만 사람이 한 말이 아닌 것(훅·알림·명령 출력) — 이 꼬리표로 시작하는 글은 버린다
SKIP_TAGS = ("system-reminder", "task-notification", "local-command-stdout", "local-command-stderr", "local-command-caveat",
             "user-prompt-submit-hook", "bash-stdout", "bash-stderr")
SKIP_ORIGINS = ("task_notification",)               # turnOrigin — 일꾼 알림(사람이 아님)
_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
_CMD = re.compile(r"<command-name>\s*(.*?)\s*</command-name>", re.S)
_ARGS = re.compile(r"<command-args>\s*(.*?)\s*</command-args>", re.S)


def cap(text, limit=TEXT_MAX):
    text = text if isinstance(text, str) else ""
    return text if len(text) <= limit else text[:limit - 1] + "…"


def entry(id_, role, text, at):
    """대화 줄 하나(모양 하나 — 모든 형식이 이것으로 낸다)."""
    assert role in ROLES, role
    return {"id": str(id_), "role": role, "text": cap(text, TOOL_MAX if role == "tool" else TEXT_MAX), "at": at or ""}


def _one_line(s):
    return " ".join(str(s).split())


def tool_summary(name, inp):
    """도구 이름 + 가장 말해 주는 인자 하나 → 한 줄('Edit screens/home.html' · 'Bash 테스트 돌리기'). 모르는 도구 = 이름만."""
    name = name if isinstance(name, str) and name else "tool"
    inp = inp if isinstance(inp, dict) else {}
    for key in ("file_path", "notebook_path", "path"):
        if isinstance(inp.get(key), str) and inp[key]:
            parts = re.split(r"[\\/]+", inp[key].rstrip("\\/"))
            return cap(_one_line("%s %s" % (name, "/".join(parts[-2:]))), TOOL_MAX)
    for key in ("description", "command", "pattern", "url", "query", "prompt", "skill"):
        if isinstance(inp.get(key), str) and inp[key].strip():
            return cap(_one_line("%s %s" % (name, inp[key].strip().splitlines()[0])), TOOL_MAX)
    return cap(name, TOOL_MAX)


def _user_text(text):
    """사용자 글 한 덩이 → 보일 글 | None(사람이 한 말이 아님). 슬래시 명령은 '/이름 인자' 로."""
    if not isinstance(text, str):
        return None
    m = _CMD.search(text)
    if m:
        a = _ARGS.search(text)
        return (m.group(1) + (" " + a.group(1) if a and a.group(1) else "")).strip() or None
    head = text.lstrip()
    if head.startswith("<") and any(head.startswith("<" + t) for t in SKIP_TAGS + ("command-message",)):
        return None
    text = _REMINDER.sub("", text).strip()
    return text or None


def claude_entries(d, line_id):
    """Claude Code jsonl 한 줄(dict) → entries. 사용자 말 · 어시스턴트 글 · 도구 부르기만. 생각·시스템·첨부·도구 결과·곁가지(sidechain)는 버린다."""
    if not isinstance(d, dict) or d.get("isSidechain") or d.get("isMeta"):
        return []
    kind, msg = d.get("type"), d.get("message")
    if kind not in ("user", "assistant") or not isinstance(msg, dict):
        return []
    at = d.get("timestamp") if isinstance(d.get("timestamp"), str) else ""
    base = d.get("uuid") if isinstance(d.get("uuid"), str) and d.get("uuid") else line_id
    content = msg.get("content")
    blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content if isinstance(content, list) else []
    out = []
    if kind == "user":
        if d.get("turnOrigin") in SKIP_ORIGINS:
            return []
        for i, b in enumerate(blocks):
            if isinstance(b, dict) and b.get("type") == "text":
                t = _user_text(b.get("text"))
                if t:
                    out.append(entry("%s:%d" % (base, i), "user", t, at))
        return out
    for i, b in enumerate(blocks):
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text" and isinstance(b.get("text"), str) and b["text"].strip():
            out.append(entry("%s:%d" % (base, i), "assistant", b["text"].strip(), at))
        elif b.get("type") == "tool_use":
            out.append(entry("%s:%d" % (base, i), "tool", tool_summary(b.get("name"), b.get("input")), at))
    return out


def parse_claude(data, max_entries=ENTRIES_MAX, start=0):
    """jsonl 바이트 조각(파일의 start 바이트부터) → (entries, 먹은 바이트).
    줄바꿈으로 끝난 줄만 먹는다(끝의 덜 쓴 줄은 다음 read 에서). 깨진 줄은 건너뛰고 먹는다(멈추지 않음).
    max_entries 에 닿으면 그 줄까지만 먹는다(남은 줄은 다음 read). 줄 id 가 없으면 파일 자리('c<바이트>')."""
    entries, pos = [], 0
    while len(entries) < max_entries:
        nl = data.find(b"\n", pos)
        if nl < 0:
            break
        raw, line_at, pos = data[pos:nl], start + pos, nl + 1
        if not raw.strip():
            continue
        try:
            d = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        entries.extend(claude_entries(d, "c%d" % line_at))
    return entries, pos


# ---------------------------------------------------------------- Paseo(`paseo logs <id> --json`)
_TEXT_KEYS = ("text", "content", "message", "body")
_AT_KEYS = ("timestamp", "at", "time", "createdAt", "created_at", "ts")
_LIST_KEYS = ("entries", "events", "items", "logs", "timeline", "data")


def _iso(v):
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        sec = v / 1000 if v > 1e11 else v
        return datetime.datetime.fromtimestamp(sec, datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return ""


def _text_of(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in _TEXT_KEYS:
            if k in v:
                return _text_of(v[k])
        return ""
    if isinstance(v, list):
        return "\n".join(t for t in (_text_of(b) if not (isinstance(b, dict) and b.get("type") in ("thinking", "reasoning", "tool_use", "tool_result")) else "" for b in v) if t)
    return ""


def _paseo_role(it):
    role = it.get("role") if isinstance(it.get("role"), str) else ""
    kind = next((it[k] for k in ("type", "kind", "event") if isinstance(it.get(k), str)), "").lower()
    if role in ("user", "assistant") and "tool" not in kind:
        return role
    if "tool" in kind:
        return "tool"
    if any(w in kind for w in ("thinking", "reasoning", "error", "permission", "status", "system")):
        return None
    if "user" in kind:
        return "user"
    if any(w in kind for w in ("assistant", "agent", "text", "message")):
        return "assistant"
    return None


def paseo_item(it):
    """Paseo 기록 항목 하나 → entry | None(모르는 종류·빈 글)."""
    if not isinstance(it, dict):
        return None
    role = _paseo_role(it)
    if role is None:
        return None
    at = next((_iso(it[k]) for k in _AT_KEYS if k in it), "")
    if role == "tool":
        call = it.get("call") if isinstance(it.get("call"), dict) else it
        name = next((call[k] for k in ("name", "tool", "toolName", "tool_name") if isinstance(call.get(k), str)), None)
        inp = next((call[k] for k in ("input", "args", "arguments", "params") if isinstance(call.get(k), dict)), None)
        text = tool_summary(name, inp)
    else:
        text = next((_text_of(it[k]) for k in _TEXT_KEYS if k in it), "").strip()
        if not text:
            return None
    iid = next((it[k] for k in ("id", "uuid", "eventId") if isinstance(it.get(k), (str, int)) and not isinstance(it.get(k), bool)), None)
    if iid is None:                                  # 바뀌지 않는 id = 시각·역할·글의 해시(같은 기록을 다시 읽어도 같다)
        iid = "p" + hashlib.sha1(("%s|%s|%s" % (at, role, text)).encode("utf-8")).hexdigest()[:16]
    return entry(iid, role, text, at)


def parse_paseo(text):
    """`paseo logs --json` 출력(JSON 목록 · {entries|events|…: 목록} · JSON 줄들) → entries(시각 차례 그대로). 깨진 줄은 건너뛴다."""
    text = text or ""
    try:
        doc = json.loads(text)
        items = doc if isinstance(doc, list) else next((doc[k] for k in _LIST_KEYS if isinstance(doc, dict) and isinstance(doc.get(k), list)), [doc])
    except ValueError:
        items = []
        for line in text.splitlines():
            try:
                items.append(json.loads(line))
            except ValueError:
                continue
    return [e for e in (paseo_item(it) for it in items) if e]


# ---------------------------------------------------------------- 커서(불투명 글 — 바깥은 그대로 돌려줄 뿐)
END = "end"                                          # read(END) = 줄 없이 지금 끝의 커서(펌프가 처음 붙을 때 — 새 줄만 이벤트로)


def claude_cursor(s):
    """'' | None → 0 · 'c1:<바이트>' → 정수 · END → END · 그 밖 ValueError."""
    if s in (None, ""):
        return 0
    if s == END:
        return END
    if isinstance(s, str) and s.startswith("c1:") and s[3:].isdigit():
        return int(s[3:])
    raise ValueError("since: 이 터미널의 커서가 아니에요")


def claude_cursor_str(offset):
    return "c1:%d" % offset


def paseo_cursor(s):
    """'' | None → (None, ()) · 'p1:<시각>\\t<id,id>' → (시각, 그 시각에 이미 낸 id들) · END → END · 그 밖 ValueError."""
    if s in (None, ""):
        return None, ()
    if s == END:
        return END
    if isinstance(s, str) and s.startswith("p1:") and "\t" in s:
        at, ids = s[3:].split("\t", 1)
        return at, tuple(i for i in ids.split(",") if i)
    raise ValueError("since: 이 터미널의 커서가 아니에요")


def paseo_cursor_str(at, ids):
    return "p1:%s\t%s" % (at, ",".join(ids))


def paseo_after(entries, at, seen, max_entries=ENTRIES_MAX):
    """커서(at, seen) 뒤의 새 줄만(at 보다 이르면 버리고, 같은 시각이면 seen 에 없는 것만) 앞에서 max_entries 개 → (새 줄, 새 커서 글)."""
    new = [e for e in entries if at is None or e["at"] > at or (e["at"] == at and e["id"] not in seen)][:max_entries]
    if not new:
        return [], paseo_cursor_str(at, seen) if at is not None else ""
    last = new[-1]["at"]
    same = [e["id"] for e in new if e["at"] == last]
    keep = list(seen) + same if last == at else same
    return new, paseo_cursor_str(last, keep)
