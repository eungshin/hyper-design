"""Model — 도우미(canvas/helper.py)의 순수 규칙: GET /api/state?since · 413 글 · 완료 메모 보관 줄 · .hd-history·.hd-queue 정리 고르기.
파일·시계·네트워크를 쓰지 않는다(tests/test_hd_helper_model.py 의 순수성 검사). 시각은 기록 이름(`%Y%m%d-%H%M%S-%f`)의 글 비교로 — 기준 시각 글은 부르는 쪽이 만든다.
"""
import json
import re

STAMP = re.compile(r"^\d{8}-\d{6}-\d{6}$")            # .hd-history/<stamp>/ · .hd-queue/<stamp>.txt 이름 — 글 차례 = 시각 차례
ARCHIVE_CAP = 2000                                   # GET /api/archive 가 읽는 마지막 줄 수
HISTORY_KEEP = 200                                   # 가장 새 기록 이만큼은 늘 남긴다
HISTORY_DAYS = 30                                    # 그 밖이라도 이보다 새것은 남긴다
QUEUE_DAYS = 7                                       # 보냄·걷힘 표시가 붙은 대기열 파일을 지우는 나이
QUEUE_MARKS = (".sent", ".lifted")                   # <stamp>.txt 옆 표시 파일 — .sent = paseo send 가 받음(helper.forward), .lifted = 다 처리함(누구든 쓸 수 있음)


def parse_since(q):
    """?since= 값 → 정수 | None(없음·빈 글). 0 이상 정수가 아니면 ValueError."""
    if q is None or q == "":
        return None
    if not q.isdigit():
        raise ValueError("since: 0 이상 정수가 아니에요")
    return int(q)


def state_reply(snap, since):
    """{rev, state} 와 since → since 가 rev 와 같으면 몸통 없이 {rev, unchanged:true}, 아니면 snap 그대로(2초 읽기가 전체를 다시 받지 않게)."""
    if since is not None and since == snap["rev"]:
        return {"rev": snap["rev"], "unchanged": True}
    return snap


def too_big(size, limit):
    """413 답 글 — 크기와 고치는 법을 말한다."""
    mb = lambda n: ("%.1f" % (n / 1048576)).rstrip("0").rstrip(".")
    return "상태가 너무 커요(%s MB — 한도 %s MB). 완료 메모를 보관으로 옮기세요" % (mb(size), mb(limit))


def archive_lines(body, have=()):
    """POST /api/archive 본문 {notes:[{…}]} → (JSON 줄 목록, None) | (None, 한국어 오류). 줄 = 메모 하나(한글 그대로, 줄바꿈 없음).
    have = 보관 파일에 이미 있는 id — 그 메모는 다시 쓰지 않는다(보관 뒤 저장이 실패해 같은 메모가 다시 와도 한 줄)."""
    if not isinstance(body, dict) or not isinstance(body.get("notes"), list):
        return None, "{notes: [메모]} 가 아니에요"
    bad = [i for i, n in enumerate(body["notes"]) if not isinstance(n, dict)]
    if bad:
        return None, "notes: %d번째가 객체가 아니에요" % (bad[0] + 1)
    return [json.dumps(n, ensure_ascii=False) for n in body["notes"] if n.get("id") is None or n.get("id") not in have], None


def archive_notes(lines, cap=ARCHIVE_CAP):
    """보관 파일 줄들 → (메모 목록 — 마지막 cap 줄, 새것이 뒤, 깨진 줄 수). 빈 줄은 세지 않고, 깨졌거나 객체가 아닌 줄은 건너뛴다."""
    lines = [x for x in lines if x.strip()][-cap:] if cap > 0 else []
    notes, bad = [], 0
    for x in lines:
        try:
            n = json.loads(x)
        except ValueError:
            n = None
        if isinstance(n, dict):
            notes.append(n)
        else:
            bad += 1
    return notes, bad


def history_prune(names, cutoff, keep=HISTORY_KEEP):
    """.hd-history 안 이름들 → 지울 기록 이름(오래된 것부터). 시각 이름만 보고, 가장 새 keep 개 밖이면서 cutoff(같은 모양 시각 글)보다 앞인 것만."""
    stamps = sorted((n for n in names if STAMP.match(n)), reverse=True)
    return sorted(n for n in stamps[keep:] if n < cutoff)


def queue_prune(names, cutoff):
    """.hd-queue 안 이름들 → 지울 이름. <stamp>.txt 에 보냄·걷힘 표시(<stamp>.sent|.lifted)가 있고 stamp 가 cutoff 보다 앞이면 그 파일과 표시 둘 다."""
    have = set(names)
    gone = []
    for n in sorted(have):
        if not n.endswith(".txt") or not STAMP.match(n[:-4]) or n[:-4] >= cutoff:
            continue
        marks = [n[:-4] + m for m in QUEUE_MARKS if n[:-4] + m in have]
        if marks:
            gone += [n] + marks
    return gone
