"""Model — 완료 메모 보관 고르기(서버 쪽, task 47-5a). modules/archive.js(HD.archive.pickArchive · without)와 같은 규칙 — 순수(시계·파일 없음).

완료 = hd_model.status 'done'(annotation.js 와 같은 규칙). 끝난 시각 = 마지막 답의 at(ISO). 보내기 전·AI 작업 중·결정 필요·일부·id 없는 메모는 고르지 않는다.
pick(notes, now_ms) → 끝난 지 KEEP_DAYS 일 넘은 완료 + 완료가 KEEP_DONE 개를 넘으면 가장 오래 전에 끝난 것부터(시각 모름 = 가장 오래됨). 목록 차례.
without(notes, archived) → 보관한 것과 id·내용이 그대로 같은 메모만 뺀 목록(그 사이 다시 연 메모는 남긴다).
쓰는 곳 = session.Archive.sweep(세션 시계가 한 시간마다 — 전에는 캔버스 탭이 이벤트·focus 때만).
"""
import datetime, json, math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "hd"))
import hd_model  # noqa: E402

KEEP_DAYS, KEEP_DONE, DAY = 30, 200, 86_400_000


def _has_id(n):
    return isinstance(n.get("id"), (str, int)) and not isinstance(n.get("id"), bool)


def done_at(n):
    """마지막 답의 at → ms | nan(모름)."""
    rs = n.get("replies")
    r = rs[-1] if isinstance(rs, list) and rs else None
    at = r.get("at") if isinstance(r, dict) else None
    if not isinstance(at, str):
        return math.nan
    try:
        t = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
    except ValueError:
        return math.nan
    if t.tzinfo is None:
        t = t.astimezone()
    return t.timestamp() * 1000


def pick(notes, now_ms):
    if not isinstance(notes, list):
        return []
    done = [(i, n, done_at(n)) for i, n in enumerate(notes) if isinstance(n, dict) and _has_id(n) and hd_model.status(n) == "done"]
    chosen = {i for i, n, at in done if not math.isnan(at) and now_ms - at > KEEP_DAYS * DAY}
    if len(done) > KEEP_DONE:                         # 새것 먼저 — 시각 모름은 맨 뒤, 같으면 목록 뒤쪽이 새것
        order = sorted(done, key=lambda d: (-(d[2] if not math.isnan(d[2]) else -math.inf), -d[0]))
        chosen |= {i for i, n, at in order[KEEP_DONE:]}
    return [n for i, n, at in done if i in chosen]


def _key(n):
    return "%s:%s" % (type(n["id"]).__name__, n["id"])


def without(notes, archived):
    gone = {_key(n): json.dumps(n, sort_keys=True, ensure_ascii=False) for n in archived or [] if isinstance(n, dict) and _has_id(n)}
    return [n for n in notes or [] if not (isinstance(n, dict) and _has_id(n) and gone.get(_key(n)) == json.dumps(n, sort_keys=True, ensure_ascii=False))]
