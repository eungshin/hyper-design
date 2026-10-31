"""Model — hd verify(V2) 결과 → 종료 코드 · 한 줄 요약. 순수(파일·소켓·시계 없음 — tests/test_hd_verify.py).

결과 = 도우미 POST /api/verify 의 답(canvas verify_desk.py · 페이지 modules/twin.js result): status match · differ · no-pair · error · no-canvas · timeout.
종료 코드: 0 일치 · 1 다름 · 2 검증 못 함(그 밖 전부 — 캔버스 안 열림 · 짝 없음 · 시간 넘김 · 페이지 오류 · 모양이 틀린 답).
"""
CODES = {"match": 0, "differ": 1}


def _n(res, k):
    v = res.get(k)
    return len(v) if isinstance(v, list) else 0


def outcome(res):
    """결과 → (종료 코드, 한 줄)."""
    if not isinstance(res, dict):
        return 2, "검증 못 함: 도우미 답의 모양이 틀려요"
    st, sid = res.get("status"), res.get("screen") or "?"
    pair = "%s ↔ %s" % (sid, res.get("app"))
    if st == "match":
        return 0, "%s · 앱과 일치 (항목 %s)" % (pair, res.get("match"))
    if st == "differ":
        return 1, "%s · 다름 %s — 앱에 없음 %d · 앱에만 %d · 스타일 %d · 확실하지 않음 %d" % (
            pair, res.get("count"), _n(res, "missing"), _n(res, "extra"), _n(res, "style"), _n(res, "unsure"))
    return 2, "%s · 검증 못 함: %s" % (sid, res.get("why") or "모르는 결과(%s)" % (st,))


def unreachable(screen, err):
    """도우미에 닿지 못함(떠 있는 캔버스 없음 · 옛 도우미 · 시간 넘김) → 결과 모양(status error) — 종료 코드 2."""
    return {"status": "error", "screen": screen, "app": None, "why": str(err)}
