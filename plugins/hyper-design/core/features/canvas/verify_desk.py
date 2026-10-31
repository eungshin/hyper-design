"""Service — hd verify 의 도우미 쪽(V2): POST /api/verify {screen} → 'verify.ask' 이벤트 → 열린 캔버스 페이지가 재서 POST /api/verify-result {req, result} → 기다리던 요청이 그 결과로 답한다.

재기·비교는 페이지(palette.js 스냅숏 + modules/twin-diff.js, AI 없음) — 여기는 요청을 잇고 기다리기만. 브라우저를 띄우지 않는다.
- 열린 캔버스(이벤트 흐름 구독자)가 없으면 기다리지 않고 {status: 'no-canvas'} · WAIT(10초) 안에 답이 없으면 {status: 'timeout'}.
- 결과 status 는 페이지가 정한다: match · differ · no-pair · error(모양이 틀리면 error). 늦게 온 답 · 모르는 req = {taken: false}(여러 탭이면 먼저 온 것).
상태: 기다리는 요청 {req: 결과|None} — 주인은 이 객체 하나(자물쇠 + 조건 변수). 부르는 곳: session.ProjectSession(verify) · router ROUTES.
"""
import secrets, threading, time

import events as EV

WAIT = 10.0                                          # 열린 캔버스가 재고 답할 때까지(초) — hd verify 의 '시간 넘김'
SCREEN_MAX = 200
STATUSES = ("match", "differ", "no-pair", "error")


class VerifyDesk:
    def __init__(self, bus, wait=WAIT, clock=time.monotonic):
        self.bus, self.wait, self.clock = bus, wait, clock
        self._cv = threading.Condition()
        self._pending = {}

    def ask(self, body):
        """{screen} → (200, 결과 {status, screen, req?, …}) | (400, {error})."""
        screen = body.get("screen") if isinstance(body, dict) else None
        if not isinstance(screen, str) or not screen.strip() or len(screen) > SCREEN_MAX:
            return 400, {"error": "screen: 화면 id(1–%d자)가 있어야 해요" % SCREEN_MAX}
        screen = screen.strip()
        if self.bus is None or self.bus.count() == 0:
            return 200, {"status": "no-canvas", "screen": screen, "why": "열린 캔버스가 없어요 — hd open 으로 캔버스를 열어 두고 다시 하세요"}
        req = secrets.token_hex(6)
        with self._cv:
            self._pending[req] = None
        try:
            EV.emit(self.bus, "verify.ask", req=req, screen=screen)
            end = self.clock() + self.wait
            with self._cv:
                while self._pending.get(req) is None:
                    left = end - self.clock()
                    if left <= 0:
                        break
                    self._cv.wait(left)
                got = self._pending.get(req)
        finally:
            with self._cv:
                self._pending.pop(req, None)
        if got is None:
            return 200, {"status": "timeout", "screen": screen, "req": req,
                         "why": "열린 캔버스가 %g초 안에 답하지 않았어요 — 캔버스 탭이 보이는지 보고 다시 하세요" % self.wait}
        return 200, dict(got, screen=screen, req=req)

    def answer(self, body):
        """{req, result} → (200, {taken}) | (400, {error}). 결과 status 가 모르는 값이면 error 로 바꿔 넘긴다."""
        req = body.get("req") if isinstance(body, dict) else None
        res = body.get("result") if isinstance(body, dict) else None
        if not isinstance(req, str) or not req or not isinstance(res, dict):
            return 400, {"error": "req(글)와 result(객체)가 있어야 해요"}
        if res.get("status") not in STATUSES:
            res = {"status": "error", "app": res.get("app"), "why": "캔버스가 보낸 결과 모양이 틀려요(status %r)" % (res.get("status"),)}
        with self._cv:
            if req not in self._pending or self._pending[req] is not None:
                return 200, {"taken": False}
            self._pending[req] = res
            self._cv.notify_all()
        return 200, {"taken": True}
