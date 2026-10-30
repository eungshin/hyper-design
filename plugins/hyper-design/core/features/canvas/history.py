"""Edge — History: 화면 파일 쓰기(apply · delete · 줄 · 되살리기)를 하나씩 세션 자물쇠 안에서, 끝나면 on_written(지켜보기 기준 옮김) + 이벤트.

상태: 없음(기록은 write_record 의 .hd-history) — 이어 둔 것만: 자물쇠 · builder · 버스 · rebuilder(async apply 의 뒤 빌드, 47-4a).
쓰기마다 screen.written(by human) · 쓰기 확인(builder.check — 데이터만, figma-lite 5)이 깨지면 되돌리고 build.failed. apply_async = 쓰기만 하고 바로 답, 확인은 rebuilder.
index.html 은 쓰기 때 굽지 않는다 — 페이지를 줄 때 데이터 도장이 다르면 session.refresh_data 가.
부르는 곳: session.ProjectSession(History · Rebuilder 의 revert = revert_writes) · router(/api/apply · /api/delete · /api/restore · /api/group-* · /api/token).
오류 탐지: 답의 reason 을 상태 코드로(_code: changed-since 409 · missing 404 · invalid 400 · 그 밖 오류 500) · 뒤 빌드 실패로 못 되돌린 쓰기는 [hd] 한 줄.
"""
import sys

import events as EV  # 바뀐 것 알림(screen.written · build.failed)
from board_rows import group_dissolve, group_move, group_rename
from screen_edits import apply_edits, apply_token, delete_screens
from write_record import BUILD_FAIL, NO_BUILD, prune, restore, tombstone


def _code(r):                                        # restore·apply·delete 답 → 상태 코드(이유 = 409·404, 그 밖 오류 = 500)
    return {"changed-since": 409, "missing": 404, "invalid": 400}.get(r.get("reason"), 500 if "error" in r else 200)



class History:
    """<out>/.hd-history — 화면 파일 쓰기(apply · delete)마다 원본 + manifest, 되살리기(restore). 쓰기는 하나씩, 끝나면 on_written(지켜보기 기준 옮김).
    쓰기마다 screen.written(by human) · 다시 빌드가 깨지면 build.failed. apply_async = 쓰기만 하고 바로 답, 빌드는 rebuilder(47-4a)."""

    def __init__(self, out, lock, builder, on_written=None, bus=None, seq=None):
        self.out, self.lock, self.builder, self.on_written = out, lock, builder, on_written
        self.bus, self.seq, self.rebuilder = bus, seq or (lambda: 0), None

    def _written(self, r, ids, stamp):
        """쓰기 답 → 이벤트(자물쇠 안에서). 쓴 것이 있으면 screen.written, 다시 빌드가 깨져 되돌렸으면 build.failed. → screen.written 이벤트 | None."""
        if r.get("changed") and (r.get("stamp") or "restored" in r):
            return EV.emit(self.bus, "screen.written", screens=list(r["changed"]), by="human", rev=self.seq(), stamp=stamp)
        broke = [f for f in r.get("failed") or [] if str(f.get("reason", "")).startswith(BUILD_FAIL)]
        if broke or str(r.get("error", "")).startswith(BUILD_FAIL):
            EV.emit(self.bus, "build.failed", reason=broke[0]["reason"] if broke else r["error"], reverted=[f["id"] for f in broke] or list(ids),
                  kept=[], stamps=[], ids=[f["id"] for f in broke] or list(ids), screens=[], repaired=None)
        return None

    def _write(self, fn, ids=(), key="stamp"):
        with self.lock:
            try:
                r = fn()
            finally:
                if self.on_written:
                    self.on_written()                # 스스로 쓴 화면 파일은 '바뀜'으로 알리지 않는다(캔버스가 그 카드를 이미 다시 싣는다)
            self._written(r, ids, r.get(key))
        return _code(r), r

    def apply(self, edits):
        return self._write(lambda: apply_edits(self.out, edits, build=self.builder.check))

    def apply_async(self, edits):
        """{edits, async:true} — 화면 파일만 쓰고(원본·manifest 는 같음) 바로 답 {accepted, failed, stamp, changed, paths, rev, async}.
        rev = 이 쓰기의 screen.written 이벤트 id(쓴 것이 없으면 지금 newest). 빌드는 rebuilder 가 뒤에서 하나씩(build.* 이벤트)."""
        ev = None
        with self.lock:
            try:
                r = apply_edits(self.out, edits, build=NO_BUILD)
            finally:
                if self.on_written:
                    self.on_written()
            if r["applied"]:
                ev = self._written(r, (), r.get("stamp"))
                if self.rebuilder is not None:
                    self.rebuilder.submit({"stamp": r["stamp"], "ids": list(r["applied"]), "screens": list(r["changed"])})
        rev = ev["id"] if ev else (self.bus.last if self.bus is not None else 0)
        return 200, {"accepted": r["applied"], "failed": r["failed"], "stamp": r["stamp"], "changed": r["changed"],
                     "paths": r.get("paths") or {}, "rev": rev, "async": True}

    def revert_writes(self, writes):
        """뒤 빌드가 깨졌다 — 아직 빌드로 확인 안 된 쓰기들을 새것부터 되살리기(빌드 없이)로 되돌리고 그 기록을 지운다 → (되돌린 편집 id, 못 되돌린 편집 id)."""
        reverted, kept = [], []
        with self.lock:
            try:
                for w in reversed(writes):
                    r = restore(self.out, w["stamp"], build=NO_BUILD)
                    if "restored" in r:
                        reverted[:0] = w["ids"]
                        tombstone(self.out, w["stamp"], w["ids"], "뒤 빌드 실패")   # 캔버스 되돌리기 줄이 '없는 기록' 대신 아무 일 없음(47-5a)
                    else:
                        kept[:0] = w["ids"]
                        print("[hd] 뒤 빌드 실패 — 쓰기 %s 를 되돌리지 못했어요(%s)" % (w["stamp"], r.get("error")), file=sys.stderr, flush=True)
            finally:
                if self.on_written:
                    self.on_written()
        return reverted, kept

    def delete(self, ids):
        return self._write(lambda: delete_screens(self.out, ids, build=self.builder.check), ids)

    def token(self, name, value):                    # Foundation 토큰 하나(R55) — tokens.css 쓰기 한 번, 되돌리기 = restore
        return self._write(lambda: apply_token(self.out, name, value, build=self.builder.check))

    def group_rename(self, frm, to):                 # 줄 이름 바꾸기(51-4) — screens.json 쓰기 한 번, 되돌리기 = restore
        return self._write(lambda: group_rename(self.out, frm, to, build=self.builder.check))

    def group_dissolve(self, name):                  # 줄만 걷기(51-4) — 그 줄 화면은 위 줄(첫 줄이면 아래 줄)로
        return self._write(lambda: group_dissolve(self.out, name, build=self.builder.check))

    def group_move(self, ids, to):                   # 다른 줄(폴더)로 옮기기(R31) — 레이어 패널 끌어 놓기, 되돌리기 = restore
        return self._write(lambda: group_move(self.out, ids, to, build=self.builder.check))

    def restore(self, stamp, keep=False, notify=False):
        """notify = 되살린 화면 파일을 지켜보기가 '바뀜'으로 알리게(그 카드를 캔버스가 다시 싣는다 — 48c 기록 패널의 AI 줄 되돌리기)."""
        if notify:
            with self.lock:
                r = restore(self.out, stamp, build=self.builder.check, keep=keep)
                self._written(r, (), r.get("redo"))
            return _code(r), r
        return self._write(lambda: restore(self.out, stamp, build=self.builder.check, keep=keep), key="redo")

    def prune(self):
        return prune(self.out)
