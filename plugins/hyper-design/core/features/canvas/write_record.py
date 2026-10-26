"""Edge — 쓰기 기록 <out>/.hd-history/<stamp>/(2.2 D4): 쓰기마다 원본 + manifest(_Writes) · 다시 빌드(run_build) · 되살리기(restore, 409 changed-since) · 묘비(tombstone) · 정리(prune #281).

상태: 기록 폴더(쓰기 하나 = stamp 폴더 하나) — 함수만, 객체 상태 없음(_Writes 는 쓰기 한 번 동안만). 고르기(정리할 것)는 helper_model.
부르는 곳: screen_edits(apply · delete) · board_rows(줄 쓰기) · history.History(되살리기 · 되돌리기 · 정리) · builder.Builder(run_build) · home.registry · helper(예전 이름).
오류 탐지: 다시 빌드가 깨지면 원본으로 되돌리고 BUILD_FAIL 글을 답에 · 되살리기 전 파일이 바뀌었으면 아무것도 안 바꾸고 changed-since · 정리·묘비 실패는 [hd] 한 줄.
"""
import datetime, json, os, pathlib, shutil, subprocess, sys

from out_io import _inside, _sha, _stamp, _write_bytes  # out_io 가 hd 폴더를 sys.path 에 넣는다

import helper_model  # noqa: E402  — 정리 고르기(history_prune · queue_prune)

HERE = pathlib.Path(__file__).resolve().parent


BUILD = HERE / "build_canvas.py"



BUILD_FAIL = "캔버스 다시 빌드 실패"                  # 답·이벤트가 다시 빌드 실패를 알아보는 글(앞부분)



NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: 자식 프로세스가 콘솔 창을 띄웠다 닫지 않게(창 없이 뜬 도우미에서 편집마다 깜빡임)



def NO_BUILD(out):                                   # async apply: 쓰기만 하고 빌드는 Rebuilder 가 뒤에서(47-4a)
    return subprocess.CompletedProcess([], 0, "", "")



def run_build(out, script=None):
    """다시 빌드 하나 — script(기본 작업 트리 build_canvas.py) 를 자식 프로세스로. CLI 도우미는 build_ref.py 를 넘긴다(helper.use_ref_build, #278)."""
    return subprocess.run([sys.executable, str(script or BUILD), str(out)], capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=NO_WINDOW)



class _Writes:
    """쓰기 한 번 — 원본을 .hd-history/<stamp>/<relpath> 에 남기고, 끝나면 manifest(쓴 뒤 해시)를 적는다."""
    def __init__(self, out, stamp=None, build=None):
        self.out, self.build = out, build or run_build
        self.stamp = stamp or datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.hist = out / ".hd-history" / self.stamp
        self.before = {}                             # relpath → 쓰기 전에 있었나

    def _dst(self, f):
        rel = f.relative_to(self.out).as_posix()
        dst = self.hist / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        return rel, dst

    def keep(self, f):                               # 쓰기 전 원본 복사(처음 한 번만)
        rel, dst = self._dst(f)
        if rel not in self.before:
            self.before[rel] = f.is_file()
            if self.before[rel]:
                shutil.copy2(f, dst)

    def move(self, f):                               # 지우기 = 기록으로 옮기기
        rel, dst = self._dst(f)
        if rel in self.before:
            f.unlink()
        else:
            self.before[rel] = True; shutil.move(str(f), str(dst))

    def undo(self):
        for rel, had in self.before.items():
            f = self.out / rel
            if had:
                shutil.copy2(self.hist / rel, f)
            elif f.exists():
                f.unlink()

    def commit(self, changed):
        """다시 빌드 → 성공이면 manifest 를 적고 None, 실패면 원본으로 되돌리고 이유."""
        r = self.build(self.out)
        if r.returncode != 0:
            self.undo(); self.build(self.out)
            return BUILD_FAIL + " — 되돌림: " + (r.stderr or "")[-300:]
        files = {rel: {"before": had, "after_sha": _sha(self.out / rel)} for rel, had in sorted(self.before.items())}
        (self.hist / "manifest.json").write_text(json.dumps({"files": files, "changed": changed}, ensure_ascii=False, indent=2), encoding="utf-8")
        prune(self.out)                              # 쓸 때마다 기록이 늘어나므로 그때 오래된 것을 정리(#281)
        return None



REVERTED = "reverted.json"                            # .hd-history/<stamp>/ 묘비 — 뒤 빌드가 깨져 서버가 되돌린 쓰기(47-5a)



def tombstone(out, stamp, ids, reason=None):
    """되돌린 쓰기의 기록을 묘비로: 원본·manifest 를 지우고 reverted.json {ids, reason} 만 남긴다(그 stamp 되살리기 = 200 reverted, 404 아님)."""
    hist = pathlib.Path(out) / ".hd-history" / stamp
    shutil.rmtree(hist, ignore_errors=True)
    try:
        hist.mkdir(parents=True, exist_ok=True)
        (hist / REVERTED).write_text(json.dumps({"ids": list(ids), "reason": reason}, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        print("[hd] 되돌린 쓰기의 표시를 쓰지 못했어요(%s): %s — 그 되돌리기 줄은 '없는 기록'이 돼요" % (e, stamp), file=sys.stderr, flush=True)



def restore(out, stamp, build=None, keep=False):
    """쓰기 하나 되살리기(2.2 D4) — manifest 의 파일이 쓴 직후 그대로일 때만. 아니면 아무것도 안 바꾸고 reason:'changed-since'.
    keep = 되살리기 전 지금 파일을 새 기록으로 남기고 답에 redo(그 stamp) — 그 stamp 를 되살리면 다시 하기(48c AI 반영 줄)."""
    out = pathlib.Path(out).resolve()
    root = out / ".hd-history"
    hist = root / str(stamp or "")
    man = hist / "manifest.json"
    if stamp and hist.resolve().parent == root.resolve() and not man.is_file() and (hist / REVERTED).is_file():
        return {"restored": [], "changed": [], "reverted": True}   # 뒤 빌드가 깨져 이미 되돌린 쓰기(47-5a 묘비) — 되돌릴 것이 없다
    if not stamp or hist.resolve().parent != root.resolve() or not man.is_file():
        return {"error": "없는 기록: %s" % stamp, "reason": "missing"}
    m = json.loads(man.read_text(encoding="utf-8"))
    files = m.get("files") or {}
    for rel, info in files.items():
        f = out / rel
        if not _inside(out, f):
            return {"error": "out 밖 경로: %s" % rel}
        if _sha(f) != info.get("after_sha"):
            return {"error": "그 뒤에 파일이 바뀌어 되돌릴 수 없어요: %s" % rel, "reason": "changed-since", "path": rel}
    now = {rel: (out / rel).read_bytes() if (out / rel).is_file() else None for rel in files}
    w = _Writes(out, build=build) if keep else None
    if w is not None:
        for rel in files:
            w.keep(out / rel)
    for rel, info in files.items():
        f = out / rel
        if info.get("before"):
            f.parent.mkdir(parents=True, exist_ok=True); _write_bytes(f, (hist / rel).read_bytes())
        elif f.exists():
            f.unlink()
    build = build or run_build
    r = build(out)
    if r.returncode != 0:                           # 다시 빌드가 깨지면 되살리기 전으로
        for rel, b in now.items():
            if b is None:
                (out / rel).unlink(missing_ok=True)
            else:
                _write_bytes(out / rel, b)
        build(out)
        if w is not None:
            shutil.rmtree(w.hist, ignore_errors=True)
        return {"error": BUILD_FAIL + " — 되돌림: " + (r.stderr or "")[-300:]}
    res = {"restored": sorted(files), "changed": m.get("changed") or []}
    if w is not None:                                # 다시 하기 = 이 기록을 되살리기(같은 규칙: 그 뒤 파일이 바뀌면 409)
        w.hist.mkdir(parents=True, exist_ok=True)
        man = {rel: {"before": had, "after_sha": _sha(out / rel)} for rel, had in sorted(w.before.items())}
        (w.hist / "manifest.json").write_text(json.dumps({"files": man, "changed": res["changed"], "by": m.get("by")}, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
        res["redo"] = w.stamp
    return res



def prune(out, now=None):
    """<out>/.hd-history/<stamp>/ 가 가장 새 200개 밖이면서 30일보다 오래됐으면 지우고, .hd-queue 의 보냄·걷힘 표시가 붙은 7일 넘은 파일을 지운다.
    그 밖(시각 이름이 아닌 것 — fix 스킬의 fix-components.css 등)은 손대지 않는다. 실패는 [hd] 한 줄(도우미는 멈추지 않음) → {history, queue} 지운 수."""
    out, now = pathlib.Path(out), now or datetime.datetime.now()
    done = {"history": 0, "queue": 0}
    hist, q = out / ".hd-history", out / ".hd-queue"
    try:
        if hist.is_dir():
            names = [d.name for d in hist.iterdir() if d.is_dir()]
            for n in helper_model.history_prune(names, _stamp(now - datetime.timedelta(days=helper_model.HISTORY_DAYS))):
                shutil.rmtree(hist / n); done["history"] += 1
        if q.is_dir():
            names = [f.name for f in q.iterdir() if f.is_file()]
            for n in helper_model.queue_prune(names, _stamp(now - datetime.timedelta(days=helper_model.QUEUE_DAYS))):
                (q / n).unlink(); done["queue"] += 1
    except OSError as e:
        print("[hd] 오래된 기록·대기열을 정리하지 못했어요(%s) — 그대로 둬요" % e, file=sys.stderr, flush=True)
    return done
