"""Edge — 대화 기록 파일 <out>/.hd-chat.jsonl(S3): 버스 탭으로 이벤트 → 기록 한 줄 덧붙이기 · 캔버스가 남기는 ask/undone · since 읽기 · 한도 넘으면 보관.

상태: 기록 파일 하나 + 읽어 둔 기록(recs · idx) — 주인 = ChatLog, 자기 자물쇠 하나(세션 자물쇠·버스는 잡지 않는다).
규칙(모양·턴 붙이기·한도)은 chat_log.py(순수). 부르는 곳: session.ProjectSession(ChatLog · events.taps) · router(GET/POST /api/chat).
오류 탐지: 못 읽으면 [hd] 한 줄 뒤 빈 기록 · 깨진 줄은 건너뛰고 [hd] 한 줄 · 쓰기·보관 실패는 [hd] 한 줄(기록은 메모리에 남음) · 모르는 턴 POST 는 404.
"""
import os, pathlib, sys, threading, time

import chat_log as CL  # 대화 기록 한 줄 모양·턴·한도(순수 Model, S3)
from out_io import _replace


NL = chr(10)                                         # 기록 한 줄 끝(LF — 어느 OS 에서나 같은 파일)



class ChatLog:
    """<out>/.hd-chat.jsonl — 대화 기록(S3). tap(ev) = 버스 탭(구독자보다 먼저): 이벤트 → 기록 한 줄 덧붙이기 · post = 캔버스가 남기는 ask/undone ·
    get(since). 규칙(모양·턴 붙이기·한도)은 chat_log.py, 여기는 파일만. 자기 자물쇠 하나(세션 자물쇠·버스는 잡지 않는다 — 탭은 버스 자물쇠 안에서 불린다).
    한도를 넘으면 오래된 턴을 .hd-chat-archive.jsonl 끝에 붙이고 남은 것을 임시 파일 + os.replace 로."""

    def __init__(self, out, clock=time.time, cap=CL.CAP, slack=CL.SLACK):
        self.out, self.clock, self.cap, self.slack = pathlib.Path(out), clock, cap, slack
        self.lock = threading.Lock()
        self.recs, self.idx = None, None

    @property
    def path(self):
        return self.out / CL.FILE

    def _load(self):
        if self.recs is not None:
            return
        lines = []
        try:
            if self.path.is_file():
                lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            print("[hd] 대화 기록을 읽지 못했어요(%s) — 빈 기록으로 시작해요" % e, file=sys.stderr, flush=True)
        self.recs, bad = CL.parse_lines(lines)
        if bad:
            print("[hd] 대화 기록에 깨진 줄 %d개를 건너뛰었어요: %s" % (bad, self.path), file=sys.stderr, flush=True)
        self.idx = CL.index(self.recs)

    def add(self, kind, fields, at=None):
        """→ 남긴 기록 | None(버림·쓰기 실패)."""
        at = int(self.clock() * 1000) if at is None else at
        with self.lock:
            self._load()
            rec, self.idx = CL.assign(self.idx, kind, fields, at)
            if rec is None:
                return None
            try:
                with open(self.path, "a", encoding="utf-8", newline="") as f:
                    f.write(CL.line(rec) + NL)
            except OSError as e:
                print("[hd] 대화 기록을 쓰지 못했어요(%s): %s" % (e, rec["kind"]), file=sys.stderr, flush=True)
            self.recs.append(rec)
            if CL.over(self.recs, self.cap, self.slack):
                self._trim()
            return rec

    def _trim(self):
        keep, old = CL.trim(self.recs, self.cap)
        try:
            with open(self.out / CL.ARCHIVE, "a", encoding="utf-8", newline="") as f:
                f.write("".join(CL.line(r) + NL for r in old))
            tmp = self.path.with_name(CL.FILE + ".tmp-%d" % os.getpid())
            tmp.write_text("".join(CL.line(r) + NL for r in keep), encoding="utf-8", newline="")
            _replace(tmp, self.path)
        except OSError as e:
            print("[hd] 오래된 대화를 보관으로 옮기지 못했어요(%s) — 그대로 둬요" % e, file=sys.stderr, flush=True)
            return
        self.recs = keep

    def tap(self, ev):
        got = CL.from_event(ev)
        if got is not None:
            self.add(got[0], got[1], ev.get("ts"))

    def post(self, body):
        got, err = CL.check_post(body)
        if err:
            return 400, {"error": err}
        rec = self.add(*got)
        if rec is None:
            return 404, {"error": "그 대화 턴이 없어요", "reason": "unknown"}
        return 200, {"record": rec}

    def get(self, since):
        with self.lock:
            self._load()
            return CL.since(self.recs, since, self.idx["seq"])
