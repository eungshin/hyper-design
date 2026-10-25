"""Service — 고른 터미널의 새 대화 줄을 이벤트로(S3b): TranscriptPump. 소스 종류를 모른다(TranscriptSource 인터페이스와 넣어 준 factory 만).

  TranscriptPump(publish, resolve, allowed, factory)
    watch(aid) / unwatch(aid)   지켜볼 에이전트(고르거나 붙인 것만 — allowed). 처음 붙을 때 커서 = 지금 끝(END) → 그 뒤 새 줄만 이벤트
    tick()                      1초마다(세션 Ticker): 지켜보는 에이전트마다 read(cursor) → 새 줄이 있으면 publish('agent.transcript', agent, entries)
    http_get(q)                 GET /api/agents/transcript?agent=<id>&since=<cursor> → (200, {entries, cursor, source[, error]}) — 지난 기록(since 없음 = 처음부터)
  pump_for(session)             ProjectSession 에 붙일 펌프 하나(main 이 부른다 — contract/transcripts.md '붙이는 줄')
상태(주인 = 이 객체, 자물쇠 하나): 지켜보는 에이전트 → (소스, 소스 열쇠, 커서, 마지막 오류). 디스크에 쓰지 않는다.
오류 탐지: 한 에이전트의 읽기가 실패해도 [hd] 한 줄(같은 오류는 한 번) 뒤 다른 에이전트는 계속. 고르지 않은 에이전트 = 403, 깨진 커서 = 400.
"""
import sys, threading, time

import transcript_parse as TP
import transcripts as TS

EVERY = 1.0                                          # 초 — 세션 Ticker 간격
MAX_WATCH = 8                                        # 동시에 지켜보는 에이전트 수(넘으면 가장 오래 지켜본 것을 뺀다)
EVENT = "agent.transcript"


def _key(record):
    """소스를 다시 만들어야 하나 — 종류·세션·작업 폴더가 바뀌면."""
    rec = record if isinstance(record, dict) else {}
    return (TS.kind_of(record), rec.get("session"), rec.get("cwd"))


class TranscriptPump:
    """publish(type, **data) · resolve(aid) → presence 항목 | {id} | None · allowed(aid) → 이 프로젝트에서 고르거나 붙인 에이전트인가 ·
    factory(record) → TranscriptSource(기본 transcripts.source_for)."""

    def __init__(self, publish, resolve, allowed, factory=None, clock=time.monotonic):
        self.publish, self.resolve, self.allowed, self.clock = publish, resolve, allowed, clock
        self.factory = factory or TS.source_for
        self.watched = {}                            # aid → {"src", "key", "cursor", "err", "next"} — 넣은 차례 = 오래된 차례
        self.lock = threading.Lock()

    def _source(self, aid):
        """지금 항목에 맞는 소스(바뀌었으면 새로 — 커서도 처음부터). 항목이 없으면 None."""
        record = self.resolve(aid)
        if not record:
            return None, None
        key = _key(record)
        w = self.watched.get(aid)
        if w is not None and w["key"] == key:
            return w["src"], key
        return self.factory(record), key

    def watch(self, aid):
        """aid 를 지켜보기 시작(이미 보면 그대로) → True | False(고르지 않은 에이전트 · 모르는 id). 커서는 첫 tick 에서 지금 끝(END)."""
        if not aid or not self.allowed(aid):
            return False
        with self.lock:
            if aid in self.watched:
                return True
            src, key = self._source(aid)
            if src is None:
                return False
            while len(self.watched) >= MAX_WATCH:
                self.watched.pop(next(iter(self.watched)))
            self.watched[aid] = {"src": src, "key": key, "cursor": TP.END, "err": None, "next": 0.0}
            return True

    def unwatch(self, aid):
        with self.lock:
            return self.watched.pop(aid, None) is not None

    def watching(self):
        with self.lock:
            return list(self.watched)

    @staticmethod
    def _log(aid, err):
        print("[hd] 터미널 대화 기록을 읽지 못했어요(%s): %s" % (aid, err), file=sys.stderr, flush=True)

    def _due(self, now):
        """자물쇠 안: 고르기가 풀린 것은 빼고, 이번 차례에 읽을 (aid, 소스, 커서)들. 소스가 바뀌었으면(종류·세션) 새 소스 + END."""
        due = []
        for aid in list(self.watched):
            if not self.allowed(aid):
                self.watched.pop(aid)
                continue
            w = self.watched[aid]
            src, key = self._source(aid)
            if src is None or now < w["next"]:
                continue                             # 잠깐 사라짐(presence 잊음) · 아직 차례 아님
            if key != w["key"]:
                w.update(src=src, key=key, cursor=TP.END, err=None)
            w["next"] = now + getattr(w["src"], "every", EVERY)
            due.append((aid, w["src"], w["cursor"]))
        return due

    def tick(self):
        """지켜보는 에이전트마다 새 줄 → 이벤트. 읽기(파일·CLI)는 자물쇠 밖에서. → 낸 줄 수."""
        with self.lock:
            due = self._due(self.clock())
        sent = 0
        for aid, src, cursor in due:
            try:
                entries, new = src.read(cursor)
                err = None
            except (TS.TranscriptUnavailable, ValueError) as e:
                entries, new, err = [], cursor, str(e)
            with self.lock:
                w = self.watched.get(aid)
                if w is None or w["src"] is not src or w["cursor"] != cursor:
                    continue                         # 그 사이 빠졌거나 바뀜 — 이 결과는 버린다
                if err is not None:
                    if err != w["err"]:
                        self._log(aid, err)
                    w["err"] = err
                    continue
                w["cursor"], w["err"] = new, None
            if entries and cursor != TP.END:
                self.publish(EVENT, agent=aid, entries=entries)
                sent += len(entries)
        return sent

    def http_get(self, q):
        """GET /api/agents/transcript?agent=&since= → (code, 답). 고른 에이전트면 지켜보기도 시작(그 뒤 새 줄은 이벤트로)."""
        aid = (q.get("agent") or [None])[0]
        since = (q.get("since") or [""])[0]
        if not aid:
            return 400, {"error": "agent: 없어요"}
        if not self.watch(aid):
            return 403, {"error": "고르거나 붙인 터미널만 대화 기록을 읽을 수 있어요: %s" % aid, "reason": "not-selected"}
        with self.lock:
            w = self.watched.get(aid)
            src = w["src"] if w else None
        if src is None:
            return 403, {"error": "고르거나 붙인 터미널만 대화 기록을 읽을 수 있어요: %s" % aid, "reason": "not-selected"}
        try:
            entries, cursor = src.read(since or None)
        except ValueError as e:
            return 400, {"error": str(e)}
        except TS.TranscriptUnavailable as e:
            return 200, {"entries": [], "cursor": since, "source": src.kind, "error": str(e)}
        res = {"entries": entries, "cursor": cursor, "source": src.kind}
        if getattr(src, "why", None):
            res["error"] = src.why
        return 200, res


def pump_for(session, paseo=None):
    """ProjectSession → 펌프. 고른 것 = 붙인 에이전트(queue.agent) 또는 이 프로젝트에 접속(hello)한 에이전트.
    claude 기록 파일은 저장소·out 폴더 이름으로 먼저 찾는다."""
    def resolve(aid):
        return session.presence.get(aid) or ({"id": aid} if aid == session.queue.agent else None)

    def allowed(aid):
        return aid == session.queue.agent or session.presence.get(aid) is not None

    env = TS.default_env((session.queue.repo, session.out), paseo=paseo)
    return TranscriptPump(session.events.publish, resolve, allowed, lambda r: TS.source_for(r, env))
