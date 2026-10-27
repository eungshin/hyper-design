"""Client — hd parts: 앱 부품 목록 <out>/parts.json 보기(--check) · 다시 빌드(--rebuild) · 경고 한 줄(hd notes · hd wait). 규칙은 canvas/part_stamp(순수), 읽기·재기는 canvas/parts_file.

parts.json 을 쓰는 곳은 이 모듈 하나. 도우미·캔버스는 읽기만 하고 빌드하지 않는다(빌드 약 35초 — 도우미 스레드에서 돌리지 않음).
다시 빌드(rebuild) = 자물쇠 파일 <out>/parts.json.lock(O_EXCL, 남의 것은 지우지 않음 — LOCK_STALE 넘게 묵은 것만 넘겨받음) 안에서 부품마다:
  지금 도장(커밋된 나무) · 미커밋 여부를 먼저 잼(미커밋이면 [hd] 경고 후 그대로 빌드 → dirty: true) → build argv 를 cwd = repo 로
  ({out} = <out>/.hd-parts/ 안 임시 경로, env 값에도) → post 단계 → 결과를 file 에 임시 파일 + os.replace → parts.json 을 다시 읽어 그 항목만 고쳐 같은 방법으로 씀.
  빌드가 실패하면(종료 코드 · 결과 없음 · 시간 넘음) 파일·기록은 그대로, 마지막 출력 한 줄과 함께 HdError.
부르는 곳: hd.py(cmd_parts · cmd_notes · cmd_wait).
오류 탐지: 깨진 parts.json · 틀린 항목은 '[hd]' 한 줄씩(parts_file) · 고른 부품이 없거나 빌드 실패 · 자물쇠가 잡혀 있으면 HdError 한 줄(종료 코드 1).
"""
import datetime, json, os, pathlib, shutil, subprocess, sys, time, uuid

import hd_client as C  # noqa: F401  — canvas 폴더를 sys.path 에 넣는다(code_probe · part_stamp · parts_file)
import part_stamp as PS  # noqa: E402
import parts_file as PF  # noqa: E402
from out_io import _write_bytes  # noqa: E402  — 임시 파일 + os.replace(Windows 에서 읽는 중이면 잠깐 다시)

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOCK = "parts.json.lock"
LOCK_STALE = 1800.0                                  # 이보다 묵은 자물쇠 = 죽은 빌드 — 넘겨받는다(한 줄)
BUILD_TIMEOUT = 900.0
TMP_DIR = ".hd-parts"                                # 빌드 결과 임시 자리(out 안 점 폴더 — 정적 경로·화면 지켜보기 밖)


def check(out, sel=None):
    """부품마다 보고 줄(part_stamp.row). sel = 파일 · 이름(없으면 전부). 고른 것이 없으면 HdError."""
    parts = PF.read(out)
    picked = PS.select(parts, sel)
    if sel not in (None, "", "*") and not picked:
        raise C.HdError("parts.json 에 그 부품이 없어요: %s (있는 것: %s)" % (sel, ", ".join(p["file"] for p in parts) or "없음"))
    return PF.check(out, picked)


def format_rows(rows):
    """사람용 줄: '<file> · 낡음|최신|모름[ · 미커밋 변경 포함] · 빌드 <시각>[ · 지금 미커밋 변경 있음]'."""
    if not rows:
        return "(앱 부품 없음 — out/parts.json)"
    lines = []
    for r in rows:
        bits = [r["file"], r["label"], "빌드 %s" % (r["built_at"] or "기록 없음")]
        if r["dirty_now"]:
            bits.append("지금 " + PS.DIRTY_LABEL)
        lines.append(" · ".join(bits))
    return "\n".join(lines)


def warning(out, target):
    """낡은 부품이 있으면 '[hd] …' 한 줄 | None — parts.json 이 없으면 git 을 부르지 않는다."""
    if not (pathlib.Path(out) / PF.PARTS).is_file():
        return None
    try:
        return PS.warn_line(PF.check(out), target)
    except Exception as e:                            # noqa: BLE001 — 경고 줄 때문에 hd notes · wait 가 실패하지 않는다
        return "[hd] 앱 부품을 보지 못했어요(%s)" % e


def warn(out, target):
    """warning 이 있으면 stderr 로 한 줄(--json 출력을 더럽히지 않게)."""
    line = warning(out, target)
    if line:
        print(line, file=sys.stderr, flush=True)
    return line


def _warn(msg):
    print(msg, file=sys.stderr, flush=True)


class Lock:
    """<out>/parts.json.lock — 한 번에 hd parts --rebuild 하나. 잡혀 있으면 HdError, LOCK_STALE 넘게 묵었으면 넘겨받음. 나갈 때 내 것만 지움."""

    def __init__(self, out):
        self.path, self.tag = pathlib.Path(out) / LOCK, "%d-%s" % (os.getpid(), uuid.uuid4().hex[:8])

    def __enter__(self):
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except OSError:
                    continue                          # 그 사이 풀림 — 다시
                if age < LOCK_STALE:
                    raise C.HdError("다른 hd parts 가 빌드 중이에요(%s, %d초 전) — 끝난 뒤 다시 하세요(멈춘 것이면 그 파일을 지우세요)" % (self.path, age)) from None
                _warn("[hd] %d초 묵은 자물쇠를 넘겨받아요: %s" % (age, self.path))
                self.path.unlink(missing_ok=True)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self.tag)
            return self
        raise C.HdError("자물쇠를 잡지 못했어요: %s" % self.path)

    def __exit__(self, *exc):
        try:
            if self.path.read_text(encoding="utf-8") == self.tag:
                self.path.unlink()
        except OSError:
            pass
        return False


def _tail(r):
    lines = ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines()
    err = [ln for ln in (r.stderr or "").strip().splitlines() if ln.strip()]
    return (err or lines or [""])[-1].strip()


def build_one(out, part, now=None):
    """부품 하나 다시 빌드 → {file, stamp, dirty, built_at, bytes}. 실패하면 HdError(파일·기록은 그대로). 자물쇠는 부르는 쪽(rebuild)."""
    out = pathlib.Path(out).resolve()
    target = out / part["file"]
    stamp, dirty = PF.measure(part)                   # 빌드 전에 잰다 — 빌드하는 동안 들어온 커밋이 도장에 섞이지 않게
    if dirty:
        _warn("[hd] %s: 지켜보는 경로(%s)에 커밋하지 않은 변경이 있어요 — 그대로 빌드하고 '%s'(dirty)로 적어요"
              % (part["file"], ", ".join(part["watch"]), PS.DIRTY_LABEL))
    if stamp is None:
        _warn("[hd] %s: 도장을 재지 못했어요(저장소 · 커밋된 경로인지 보세요) — 빌드는 하고 도장 없이 적어요" % part["file"])
    tmpdir = out / TMP_DIR
    tmpdir.mkdir(exist_ok=True)
    tmp = tmpdir / ("%s-%s" % (uuid.uuid4().hex[:8], target.name))
    env = dict(os.environ, **{k: v.replace(PS.OUT_TOKEN, str(tmp)) for k, v in part["env"].items()})
    argv = [a.replace(PS.OUT_TOKEN, str(tmp)) for a in part["build"]]
    argv[0] = shutil.which(argv[0], path=env.get("PATH")) or argv[0]   # Windows: npm → npm.cmd
    try:
        try:
            r = subprocess.run(argv, cwd=part["repo"], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=BUILD_TIMEOUT, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise C.HdError("%s: 빌드를 돌리지 못했어요(%s) — 파일·기록은 그대로" % (part["file"], e)) from e
        if r.returncode != 0 or not tmp.is_file():
            raise C.HdError("%s: 빌드가 실패했어요(종료 코드 %s%s): %s — 파일·기록은 그대로"
                            % (part["file"], r.returncode, "" if tmp.is_file() else " · 결과 파일 없음", _tail(r)))
        html = PS.apply_post(tmp.read_text(encoding="utf-8", errors="replace"), part["post"])
        data = html.encode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        _write_bytes(target, data)
    finally:
        tmp.unlink(missing_ok=True)
        try:
            tmpdir.rmdir()
        except OSError:
            pass                                      # 다른 임시 파일이 남아 있음 — 그대로
    built_at = now or datetime.datetime.now().isoformat(timespec="seconds")
    cur = PF.load(out)                                # 자물쇠 안에서 다시 읽고 그 항목만 고친다(다른 항목 · 모르는 키 · 틀린 항목은 그대로)
    if cur is None:
        raise C.HdError("parts.json 을 다시 읽지 못했어요 — %s 는 새로 썼지만 기록은 못 고쳤어요" % part["file"])
    _write_bytes(out / PF.PARTS, (json.dumps(PS.record(cur, part["file"], stamp, dirty is True, built_at), ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return {"file": part["file"], "stamp": stamp, "dirty": dirty is True, "built_at": built_at, "bytes": len(data)}


def rebuild(out, sel=None, now=None):
    """고른 부품(sel 없음 = 전부)을 자물쇠 안에서 차례로 다시 빌드 → 결과 목록. 하나가 실패하면 거기서 멈춘다(앞의 것은 이미 기록됨)."""
    out = pathlib.Path(out).resolve()
    if PF.load(out) is None:
        raise C.HdError("parts.json 이 없거나 읽지 못했어요: %s" % (out / PF.PARTS))
    parts = PF.read(out)
    picked = PS.select(parts, sel)
    if not picked:
        raise C.HdError("다시 빌드할 부품이 없어요%s (있는 것: %s)" % (": " + sel if sel else "", ", ".join(p["file"] for p in parts) or "없음"))
    with Lock(out):
        return [build_one(out, p, now) for p in picked]
