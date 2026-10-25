"""Edge — 완료 메모 보관 파일 <out>/.hd-notes-archive.jsonl(#273, 한 줄 = 메모 하나): 덧붙이기 · 마지막 2000 줄 읽기 · sweep(서버가 고르고 옮김, 47-5a).

상태: 보관 파일 하나(주인 = Archive, 쓰기는 세션 자물쇠 안). 고르기는 memo_archive.py(순수), 줄 모양·한도는 helper_model.
부르는 곳: session.ProjectSession(Archive · 세션 시계가 한 시간마다 sweep) · router(GET/POST /api/archive) · helper(예전 이름).
오류 탐지: 깨진 줄은 건너뛰고 [hd] 한 줄 · 모양이 틀린 POST 는 400 · sweep 에서 보관 쓰기가 실패하면 [hd] 한 줄 뒤 상태에서 빼지 않는다(0).
"""
import os, pathlib, sys, time

import events as EV  # 바뀐 것 알림(notes.changed)
import memo_archive as MA  # 완료 메모 보관 고르기(순수 Model, task 47-5a)
from out_io import _replace  # out_io 가 hd 폴더를 sys.path 에 넣는다
from state_store import _state_save, state_load

import helper_model  # noqa: E402  — 보관 줄 모양·읽기 한도


ARCHIVE_FILE = ".hd-notes-archive.jsonl"



def archive_post(out, body):
    """POST /api/archive 본문 {notes:[…]} → (code, 답). 줄마다 메모 하나를 덧붙인다(있던 것 + 새 줄을 임시 파일에 쓰고 os.replace — 반쯤 쓴 파일이 남지 않게). 쓰기 자물쇠 안에서 부른다."""
    p = pathlib.Path(out) / ARCHIVE_FILE
    old = p.read_bytes() if p.is_file() else b""
    have = {n.get("id") for n in helper_model.archive_notes(old.decode("utf-8", errors="replace").splitlines(), cap=10 ** 9)[0]}
    lines, err = helper_model.archive_lines(body, have)
    if err:
        return 400, {"error": err}
    if lines:
        if old and not old.endswith(b"\n"):
            old += b"\n"
        tmp = p.with_name(ARCHIVE_FILE + ".tmp-%d" % os.getpid())
        tmp.write_bytes(old + "".join(x + "\n" for x in lines).encode("utf-8"))
        _replace(tmp, p)
    return 200, {"ok": True, "count": len(lines)}



def archive_get(out):
    """GET /api/archive → {notes:[…]} — 마지막 2000 줄, 새것이 뒤. 깨진 줄은 건너뛰고 [hd] 한 줄."""
    p = pathlib.Path(out) / ARCHIVE_FILE
    if not p.is_file():
        return {"notes": []}
    notes, bad = helper_model.archive_notes(p.read_text(encoding="utf-8", errors="replace").splitlines())
    if bad:
        print("[hd] 보관 파일에 깨진 줄 %d개를 건너뛰었어요: %s" % (bad, p), file=sys.stderr, flush=True)
    return {"notes": notes}



class Archive:
    """<out>/.hd-notes-archive.jsonl — 완료 메모 덧붙이기(자물쇠 안) · 마지막 2000 줄 읽기 · sweep = 서버가 고르고 옮기기(47-5a, Ticker 가 한 시간마다)."""

    def __init__(self, out, lock, bus=None):
        self.out, self.lock, self.bus = out, lock, bus

    def post(self, body):
        with self.lock:
            return archive_post(self.out, body)

    def get(self):
        return archive_get(self.out)

    def sweep(self, now_ms=None):
        """오래된·넘친 완료 메모(memo_archive.pick)를 보관 파일로 옮기고 상태에서 뺀다(rev+1 · notes.changed) → 옮긴 수.
        캔버스 탭도 같은 일을 한다(view-state-sync) — 보관 파일은 id 로 겹치지 않고, 캔버스는 notes.changed 로 다시 읽는다."""
        now_ms = int(time.time() * 1000) if now_ms is None else now_ms
        with self.lock:
            cur = state_load(self.out)
            notes = cur["state"].get("notes")
            picks = MA.pick(notes, now_ms)
            if not picks:
                return 0
            code, res = archive_post(self.out, {"notes": picks})
            if code != 200:
                print("[hd] 완료 메모를 보관하지 못했어요: %s" % res.get("error"), file=sys.stderr, flush=True)
                return 0
            rev = _state_save(self.out, cur["rev"] + 1, dict(cur["state"], notes=MA.without(notes, picks)))
            EV.emit(self.bus, "notes.changed", rev=rev)
        print("[hd] 완료 메모 %d개를 보관으로 옮겼어요(%s)" % (len(picks), ARCHIVE_FILE), file=sys.stderr, flush=True)
        return len(picks)
