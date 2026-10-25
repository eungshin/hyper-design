"""Model — 세션 하나의 바뀐 것 알림(EventBus, task 47-4a): 번호 붙이기 · 고리 버퍼 · 이어 받기(Last-Event-ID) · 구독자 줄 · SSE 글 모양.

소켓 쓰기는 router.SessionHandler._events, 언제 무엇을 내는지는 session.py 의 부품(StateStore · History · Busy · Queue · Rebuilder).
계약 = tests/protocol/events.json(모양 · 이어 받기 · reset). 상태: 고리(_ring) · newest id(_last) · 구독자들(_subs) — 주인은 이 객체 하나.
버스는 세션마다 하나(허브 하나가 아니라): 상태·자물쇠·수명이 세션 것이고, 한 프로젝트가 바빠도 다른 프로젝트의 고리를 밀어내지 않는다.
"""
import collections, json, sys, threading, time

TYPES = ("screen.written", "notes.changed", "claim", "release", "ai.write", "build.started", "build.done", "build.failed",
         "agent.hello", "agent.away", "agent.progress", "agent.reply", "request.sent",   # 47-5a: 접속·보내기
         "agent.transcript")                         # S3b: 터미널 대화 줄(대화 패널이 시간 차례로 섞는다)
COMMON = ("id", "type", "ts", "project")
RING = 256                                           # 이어 받기로 다시 줄 수 있는 최근 이벤트 수
QUEUE_MAX = 512                                      # 구독자 하나가 이만큼 뒤처지면 닫는다(다시 붙어 이어 받기)
MAX_SUBS = 16                                        # 프로젝트 하나에 열린 흐름 수(넘으면 503)
RETRY_FRAME = b"retry: 2000\n\n"                     # EventSource 다시 붙기 간격(캔버스의 2초 폴링과 같음)
HEARTBEAT_FRAME = b": hb\n\n"
CLOSED = object()                                    # Subscription.get → 끝(버스 닫힘 · 뒤처짐)


def parse_last(v):
    """Last-Event-ID · ?since 값 → None(없음) | int | 그대로(정수 아님 — backlog 가 reset unknown)."""
    if v is None or not str(v).strip():
        return None
    s = str(v).strip()
    return int(s) if s.isdigit() else s


class Subscription:
    """흐름 하나의 받은 줄. put 은 버스가(자물쇠 안), get 은 흐름 스레드가."""

    def __init__(self, cap):
        self._q, self._cv, self.cap = collections.deque(), threading.Condition(), cap
        self.closed = self.lagged = False

    def put(self, ev):
        with self._cv:
            if self.closed:
                return
            if len(self._q) >= self.cap:
                self.lagged = self.closed = True
            else:
                self._q.append(ev)
            self._cv.notify_all()

    def close(self):
        with self._cv:
            self.closed = True
            self._cv.notify_all()

    def get(self, timeout):
        """→ 이벤트 | None(timeout 동안 없음) | CLOSED(닫힘 — 남은 것을 다 준 뒤)."""
        with self._cv:
            if not self._q and not self.closed and timeout:
                self._cv.wait(timeout)
            if self._q:
                return self._q.popleft()
            return CLOSED if self.closed else None


class EventBus:
    """publish(type, **data) → 이벤트 {id, type, ts(ms), project, …data}. id 는 start(기본 = 여는 순간의 시계 ms)부터 1씩 —
    같은 프로젝트의 나중 세션은 늘 더 큰 id 라 옛 세션의 Last-Event-ID 는 too-old 가 된다."""

    def __init__(self, project, ring=RING, clock=time.time, start=None, max_subs=MAX_SUBS, queue_max=QUEUE_MAX):
        self.project, self.clock, self.max_subs, self.queue_max = project, clock, max_subs, queue_max
        self._ring = collections.deque(maxlen=ring)
        self._last = (int(clock() * 1000) if start is None else start) - 1
        self._subs = set()
        self._lock = threading.Lock()
        self.closed = False
        self.taps = []                               # (ev) → None — 구독자보다 먼저, 자물쇠 안에서(대화 기록 S3: 이벤트를 받은 탭이 GET /api/chat 하면 이미 있다)

    @property
    def last(self):
        return self._last

    def publish(self, type_, **data):
        if type_ not in TYPES:
            raise ValueError("모르는 이벤트: %s" % type_)
        bad = [k for k in data if k in COMMON]
        if bad:
            raise ValueError("이벤트 칸 이름이 공통 칸과 겹쳐요: %s" % bad)
        with self._lock:
            self._last += 1
            ev = dict({"id": self._last, "type": type_, "ts": int(self.clock() * 1000), "project": self.project}, **data)
            self._ring.append(ev)
            for tap in self.taps:
                try:
                    tap(ev)
                except Exception as e:                # noqa: BLE001 — 탭이 깨져도 알림은 나간다(한 줄 남김)
                    print("[hd] 이벤트 탭이 실패했어요(%s): %s" % (type_, e), file=sys.stderr, flush=True)
            for s in list(self._subs):
                s.put(ev)
                if s.lagged:
                    self._subs.discard(s)
        return ev

    def _backlog(self, want):
        if want is None or want == self._last:
            return [], None
        if not isinstance(want, int) or want > self._last or want < 0:
            return [], "unknown"
        oldest = self._ring[0]["id"] if self._ring else self._last + 1
        if want < oldest - 1:
            return [], "too-old"
        return [e for e in self._ring if e["id"] > want], None

    def backlog(self, want):
        """이어 받기 → (다시 줄 이벤트들, reset 이유 | None). want = parse_last 값."""
        with self._lock:
            return self._backlog(want)

    def subscribe(self, want):
        """→ (Subscription | None(닫힘·가득), 다시 줄 것, reset 이유). 다시 줄 것과 새 이벤트 사이에 빠짐·겹침이 없게 한 자물쇠 안에서."""
        with self._lock:
            back, reset = self._backlog(want)
            if self.closed or len(self._subs) >= self.max_subs:
                return None, back, reset
            sub = Subscription(self.queue_max)
            self._subs.add(sub)
            return sub, back, reset

    def unsubscribe(self, sub):
        with self._lock:
            self._subs.discard(sub)

    def count(self):
        with self._lock:
            return len(self._subs)

    def close(self):
        with self._lock:
            self.closed = True
            subs, self._subs = list(self._subs), set()
        for s in subs:
            s.close()


def reset_event(bus, reason):
    """흐름마다 하나(고리에 넣지 않음) — id = 지금 newest(EventSource 가 이어 받을 곳을 여기로 옮긴다)."""
    last = bus.last
    return {"id": last, "type": "reset", "ts": int(bus.clock() * 1000), "project": bus.project, "reason": reason, "last": last}


def frame(ev):
    """이벤트 → SSE 한 덩어리(id · event · data 한 줄 JSON · 빈 줄)."""
    return ("id: %d\nevent: %s\ndata: %s\n\n" % (ev["id"], ev["type"], json.dumps(ev, ensure_ascii=False))).encode("utf-8")
