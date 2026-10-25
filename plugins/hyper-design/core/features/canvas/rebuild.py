"""Model + 일꾼 — 비동기 apply 의 뒤 빌드 차례(task 47-4a): 하나씩 · 빠른 쓰기 묶기 · 마지막 것이 이김 · 실패면 아직 안 빌드한 쓰기를 모두 되돌림.

BuildPlan  = 순수 상태 기계(I/O·스레드 없음 — unit 테스트). 상태: pending(아직 빌드로 확인 안 된 쓰기들) · running(일꾼 있음) · dirty(빌드 중 새 쓰기).
Rebuilder  = 일꾼 스레드 하나(일이 있을 때만 뜨고 다 하면 끝남 — 남는 스레드 없음). build() · revert(writes) · emit(type, **data) 는 세션이 넘긴다.
쓰기 하나 = {stamp, ids, screens}(.hd-history stamp · 편집 id · 화면). 이벤트 모양은 tests/protocol/events.json.
"""
import threading

COALESCE = 0.1                                       # 첫 쓰기 뒤 이만큼 기다렸다 빌드(빠른 쓰기를 한 빌드로)


def summary(writes):
    return {"stamps": [w["stamp"] for w in writes], "ids": [i for w in writes for i in w["ids"]],
            "screens": sorted({s for w in writes for s in w["screens"]})}


class BuildPlan:
    def __init__(self):
        self.pending, self.running, self.dirty, self.batch = [], False, False, []

    def submit(self, write):
        """→ 새 일꾼을 띄울지(True = 쉬고 있었다). 돌고 있으면 묶음에 더하고 dirty."""
        self.pending.append(write)
        if self.running:
            self.dirty = True
            return False
        self.running = True
        return True

    def begin(self):
        """→ 이번에 빌드할 쓰기들(아직 확인 안 된 것 전부) | None(할 일 없음 — 일꾼은 끝난다)."""
        if not self.pending:
            self.running = False
            return None
        self.dirty, self.batch = False, list(self.pending)
        return self.batch

    def finish(self, ok):
        """빌드 결과 → ('done', 확인된 쓰기들) | ('again', None)(그 사이 새 쓰기 — 알리지 않고 다시) | ('revert', 되돌릴 쓰기들)."""
        if self.dirty:
            return "again", None
        batch, self.pending = self.batch, []          # dirty 가 아니면 pending == batch(빌드 중 새 쓰기 없음)
        return ("done" if ok else "revert"), batch


def _ok(r):                                          # build() 답 = bool | CompletedProcess
    return r if isinstance(r, bool) else getattr(r, "returncode", 1) == 0


class Rebuilder:
    """submit(쓰기) → 뒤에서 빌드. build.started → build.done | (되돌림 → 다시 빌드 →) build.failed. close() = 다음 빌드를 시작하지 않음."""

    def __init__(self, build, revert, emit, coalesce=COALESCE, reason=None):
        self.build, self.revert, self.emit, self.coalesce = build, revert, emit, coalesce
        self.reason = reason or (lambda: "")
        self.plan, self.mu, self.stop, self.thread = BuildPlan(), threading.Lock(), threading.Event(), None

    def submit(self, write):
        with self.mu:
            if self.plan.submit(write) and not self.stop.is_set():
                self.thread = threading.Thread(target=self._loop, name="hd-rebuild", daemon=True)
                self.thread.start()

    def pending(self):
        with self.mu:
            return len(self.plan.pending)

    def close(self):
        self.stop.set()

    def join(self, timeout=None):
        t = self.thread
        if t is not None:
            t.join(timeout)
        return t is None or not t.is_alive()

    def _why(self, r):
        err = getattr(r, "stderr", None)
        return "캔버스 다시 빌드 실패: " + err[-300:] if isinstance(err, str) and err.strip() else self.reason()

    def _loop(self):
        while not self.stop.wait(self.coalesce):
            with self.mu:
                batch = self.plan.begin()
            if batch is None:
                return
            self.emit("build.started", **summary(batch))
            r = self.build()
            with self.mu:
                verdict, writes = self.plan.finish(_ok(r))
            if verdict == "done":
                self.emit("build.done", **summary(writes))
            elif verdict == "revert":
                why = self._why(r)
                reverted, kept = self.revert(writes)
                repaired = _ok(self.build())
                self.emit("build.failed", reason=why, reverted=reverted, kept=kept, repaired=repaired, **summary(writes))
