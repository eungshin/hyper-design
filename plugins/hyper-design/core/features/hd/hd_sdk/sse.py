"""Model — Server-Sent Events 글 풀기(task 47-4b). 순수(I/O·시계 없음): 줄 → frame → Event. 모양 = canvas tests/protocol/events.json.

frames(lines) → {id, event, data} 차례로 — 빈 줄이 frame 을 끝낸다. `retry:`·주석(`:` 로 시작, `: hb`)·data 없는 frame 은 건너뛴다. data 여러 줄은 \\n 으로 잇는다.
  CR 끝(\\r\\n)도 받는다. 끝나지 않은 마지막 frame 은 내지 않는다(흐름이 끊긴 것 — 다시 붙어 이어 받는다).
event_of(frame) → Event | None(깨진 data) — reset frame 의 data 는 {type:'reset', reason, last} 로 id 가 없다: id = frame id(또는 last).
"""
import json

from .values import Event


def frames(lines):
    fid, kind, data = None, None, []
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        line = line.rstrip("\r\n")
        if not line:
            if data:
                yield {"id": fid, "event": kind or "message", "data": "\n".join(data)}
            fid, kind, data = None, None, []
            continue
        if line.startswith(":"):
            continue
        name, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if name == "id":
            fid = value
        elif name == "event":
            kind = value
        elif name == "data":
            data.append(value)


def event_of(fr):
    try:
        d = json.loads(fr["data"])
    except (ValueError, TypeError, KeyError):
        return None
    if isinstance(d, dict) and d.get("type") == "reset" and "id" not in d:
        fid = fr.get("id")
        last = d.get("last")
        i = int(fid) if isinstance(fid, str) and fid.isdigit() else last if type(last) is int else 0
        return Event(i, "reset", 0, "", {k: v for k, v in d.items() if k != "type"})
    try:
        return Event.from_dict(d)
    except ValueError:
        return None
