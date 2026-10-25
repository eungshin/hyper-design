"""Edge — 프로젝트 상태 파일 <out>/.hd-canvas.json(#228): rev · 합쳐 쓰기(409) · 자물쇠 없는 읽기(#271) · 깨진 파일 옮기기 · 페이지 스냅숏.

상태: 파일 하나(주인 = StateStore, 쓰기는 세션 자물쇠 안). 합쳐 쓸 때 notes.changed 를 버스에 낸다.
부르는 곳: session.ProjectSession(StateStore) · router(GET/PUT /api/state, STATE_MAX) · busy(claim·release) · send_queue(reply) · note_archive(sweep) · helper(예전 이름).
오류 탐지: 깨진 파일은 .hd-canvas.json.corrupt-<시각> 으로 옮기고 [hd] 한 줄 뒤 빈 상태(도우미는 멈추지 않음) · 모양이 틀린 PUT 은 400, rev 가 다르면 409.
"""
import datetime, json, os, pathlib, shutil, sys, threading, time

import events as EV  # 바뀐 것 알림(notes.changed)
from out_io import REPLACE_TRIES, _now, _replace  # out_io 가 hd 폴더를 sys.path 에 넣는다

import helper_model  # noqa: E402  — since 가 같으면 몸통 없이(state_reply)


STATE_FILE = ".hd-canvas.json"



STATE_MAX = 2 * 1024 * 1024                          # PUT 본문 한도(넘으면 413)



def _state_ok(doc):
    return isinstance(doc, dict) and type(doc.get("rev")) is int and doc["rev"] >= 0 and isinstance(doc.get("state"), dict)



def state_load(out):
    """상태 파일 → {rev, state}. 없으면 {rev:0, state:{}}. 깨졌으면 .hd-canvas.json.corrupt-<시각> 으로 옮기고 한 줄 남긴 뒤 빈 상태(도우미는 멈추지 않는다)."""
    p = pathlib.Path(out) / STATE_FILE
    if not p.is_file():
        return {"rev": 0, "state": {}}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        doc = None
    if _state_ok(doc):
        return {"rev": doc["rev"], "state": doc["state"]}
    bad = p.with_name(STATE_FILE + ".corrupt-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    try:
        os.replace(p, bad)
        print("[hd] 깨진 상태 파일을 옮기고 빈 상태로 시작해요: " + bad.name, file=sys.stderr, flush=True)
    except OSError as e:
        print("[hd] 깨진 상태 파일을 옮기지 못했어요(빈 상태로 시작): %s" % e, file=sys.stderr, flush=True)
    return {"rev": 0, "state": {}}



def _state_write(out, doc):                          # 같은 폴더 임시 파일 → os.replace(원자적), 바로 앞 것 하나는 .bak
    p = pathlib.Path(out) / STATE_FILE
    tmp = p.with_name(STATE_FILE + ".tmp-%d" % os.getpid())
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    if p.is_file():
        shutil.copy2(p, p.with_name(STATE_FILE + ".bak"))
    _replace(tmp, p)



def state_peek(out):
    """자물쇠 없는 읽기(GET /api/state · index.html 스냅숏, #271) → {rev, state} | None(못 읽음·깨짐 — 그때만 자물쇠 안에서 state_load).
    쓰기는 임시 파일 + os.replace 라 반쯤 쓴 파일을 읽을 일은 없다. 깨진 파일을 옮기는 일(쓰기)은 하지 않는다."""
    p = pathlib.Path(out) / STATE_FILE
    for _ in range(REPLACE_TRIES):
        if not p.is_file():
            return {"rev": 0, "state": {}}
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except PermissionError:                       # Windows: 바로 그 순간 os.replace 중
            time.sleep(0.02); continue
        except (OSError, ValueError):
            return None
        return {"rev": doc["rev"], "state": doc["state"]} if _state_ok(doc) else None
    return None



def state_put(out, body):
    """PUT 본문 {rev, state:{이름: 값 | null(지움)}} → (code, 답). rev 가 파일과 같을 때만 합쳐 rev+1 로 쓴다 · 다르면 409 {rev, state}."""
    if not isinstance(body, dict) or type(body.get("rev")) is not int or not isinstance(body.get("state"), dict):
        return 400, {"error": "{rev: 정수, state: {}} 가 아니에요"}
    cur = state_load(out)
    if body["rev"] != cur["rev"]:
        return 409, cur
    state = dict(cur["state"])
    for k, v in body["state"].items():
        if v is None:
            state.pop(k, None)
        else:
            state[k] = v
    return 200, {"rev": _state_save(out, cur["rev"] + 1, state)}



def _state_save(out, rev, state):
    _state_write(out, {"version": 1, "rev": rev, "updated": _now(), "state": state})
    return rev



def state_inject(out, lock=None):                    # 페이지에 끼워 넣을 동기 스냅숏(window.__hdState) — </script> 가 끊지 않게 < 를 이스케이프
    snap = state_peek(out)                           # 자물쇠 없이(#271) — 깨졌을 때만 자물쇠 안에서 state_load(옮기기)
    if snap is None:
        with lock or threading.Lock():
            snap = state_load(out)
    return "<script>window.__hdState=%s;</script>" % json.dumps(snap, ensure_ascii=False).replace("<", "\\u003c")



class StateStore:
    """<out>/.hd-canvas.json — 읽기는 자물쇠 없이(#271, 깨졌을 때만 자물쇠 안에서 옮김), 쓰기(PUT 합치기·rev+1)는 세션 자물쇠 안에서."""

    def __init__(self, out, lock, bus=None):
        self.out, self.lock, self.bus = out, lock, bus

    def load(self):
        return state_load(self.out)

    def snapshot(self):
        snap = state_peek(self.out)
        if snap is None:
            with self.lock:
                snap = state_load(self.out)
        return snap

    def get(self, since):
        return helper_model.state_reply(self.snapshot(), since)   # ?since=rev 가 같으면 몸통 없이(#273 — 2초 읽기)

    def put(self, body):
        with self.lock:                              # rev 비교와 쓰기 사이에 끼어들지 않게
            code, res = state_put(self.out, body)
            if code == 200:
                EV.emit(self.bus, "notes.changed", rev=res["rev"])
            return code, res

    def inject(self):
        return state_inject(self.out, self.lock)
