"""Edge — Ticker: 세션 시계 스레드 하나(47-5a) — 일(간격 초, fn)마다 처음 한 번, 그 뒤 간격마다.

상태: 일마다 다음 시각(next) · 멈춤 표시(stop) — 주인 = Ticker. step(now) 는 I/O 가 없다(unit), 스레드는 start()·close().
부르는 곳: session.ProjectSession(presence.sweep · Archive.sweep · 터미널 대화 펌프 tick — 간격 상수는 session 이 정한다).
오류 탐지: 한 일이 실패해도 [hd] 한 줄 뒤 다른 일은 계속(세션 시계는 멈추지 않는다).
"""
import sys, threading, time

TICK = 0.5                                           # 시계 한 번 쉬는 시간(초)


class Ticker:
    """세션 시계 — 일(간격 초, fn)마다 처음 한 번, 그 뒤 간격마다. step(now) 는 I/O 가 없다(unit), 스레드는 start()·close().
    한 일이 실패해도 [hd] 한 줄 뒤 다른 일은 계속."""

    def __init__(self, tasks, clock=time.monotonic):
        self.tasks, self.clock = list(tasks), clock
        self.next = [None] * len(self.tasks)
        self.stop = threading.Event()

    def step(self, now):
        for i, (every, fn) in enumerate(self.tasks):
            if self.next[i] is None or now >= self.next[i]:
                self.next[i] = now + every
                try:
                    fn()
                except Exception as e:                # noqa: BLE001 — 세션 시계는 멈추지 않는다(한 줄 남김)
                    print("[hd] 세션 시계 일이 실패했어요(%s): %s" % (getattr(fn, "__name__", fn), e), file=sys.stderr, flush=True)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def close(self):
        self.stop.set()

    def _loop(self):
        while not self.stop.is_set():
            self.step(self.clock())
            self.stop.wait(TICK)
