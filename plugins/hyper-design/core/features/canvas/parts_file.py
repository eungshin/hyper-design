"""Edge — 앱 부품 목록 <out>/parts.json 읽기 · 지금 도장 재기(git) · 낡은 부품을 끌어 쓰는 화면 고르기(60초 캐시). 규칙은 part_stamp(순수 Model).

- read(out) = 고른 부품 목록. 파일이 없으면 [](조용히) · 깨진 JSON · 모양이 틀린 항목은 stderr 에 '[hd]' 한 줄씩(projects.json 과 같은 규칙).
- check(out) = 부품마다 part_stamp.row(지금 도장 = code_probe.tree_shas → part_stamp.tree_of, 지금 미커밋 = code_probe.dirty).
  같은 (저장소, 경로들) 은 한 번만 잰다. 재지 못하면 'unknown' — 낡았다고 하지 않는다.
- PartsWatch(out).status() = {parts: [row], stale: [화면 id]} — 도우미 GET /api/app-parts. EVERY(60초)보다 자주 git 을 부르지 않는다(캐시),
  화면 → 끌어 쓰는 파일은 busy._deps(F25, iframe·link·script) 그대로.
쓰기는 하지 않는다 — parts.json 을 쓰는 곳은 hd parts(hd/hd_parts.py) 하나. 빌드도 하지 않는다(도우미 스레드에서 35초 빌드를 돌리지 않게).
부르는 곳: session.ProjectSession(parts) · router(/api/app-parts) · hd_parts(hd parts --check · hd notes · hd wait 경고 줄).
"""
import json, pathlib, sys, threading, time

import code_probe as CP
import part_stamp as PS
from busy import _deps
from out_io import _inside, _screen_files

PARTS = "parts.json"
EVERY = 60.0


def _warn(msg):
    print(msg, file=sys.stderr, flush=True)


def load(out):
    """<out>/parts.json → 객체 | None(없음). 깨진 JSON 이면 '[hd]' 한 줄 뒤 None."""
    p = pathlib.Path(out) / PARTS
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        _warn("[hd] parts.json 을 읽지 못했어요(%s) — 부품을 보지 않아요" % e)
        return None


def read(out, warn=_warn):
    """고른 부품 목록(없으면 []) — 모양이 틀린 항목은 warn 한 줄씩."""
    data = load(out)
    if data is None:
        return []
    parts, warns = PS.parse(data)
    for w in warns:
        warn(w)
    return parts


def measure(part, memo=None):
    """부품 → (지금 도장 | None, 지금 미커밋 bool | None). memo 가 있으면 같은 (저장소, 경로들) 은 한 번만."""
    k = (part["repo"], tuple(part["watch"]))
    if memo is not None and k in memo:
        return memo[k]
    pairs = CP.tree_shas(part["repo"], part["watch"])
    got = (PS.tree_of(pairs) if pairs else None, CP.dirty(part["repo"], part["watch"]))
    if memo is not None:
        memo[k] = got
    return got


def check(out, parts=None):
    """부품마다 보고 줄(part_stamp.row) — parts 를 주지 않으면 read(out)."""
    memo = {}
    return [PS.row(p, *measure(p, memo)) for p in (read(out) if parts is None else parts)]


def screen_deps(out):
    """{화면 id: [out 상대 경로 — 화면 파일 + 끌어 쓰는 파일]} | {}(screens.json 을 못 읽음)."""
    out = pathlib.Path(out).resolve()
    try:
        files = _screen_files(json.loads((out / "screens.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    res, cache = {}, {}
    for sid, rel in files.items():
        p = out / rel
        try:
            if not (_inside(out, p) and p.is_file()):
                continue
            res[sid] = [p.resolve().relative_to(out).as_posix()] + [d.relative_to(out).as_posix() for d in _deps(out, p, cache)]
        except (OSError, ValueError):
            continue
    return res


class PartsWatch:
    """도우미 쪽 앱 부품 보기 — status() 는 EVERY 초 동안 지난 답을 다시 쓴다(git 을 매초 부르지 않게). 상태: 지난 답 · 그 시각."""

    def __init__(self, out, every=EVERY, clock=time.monotonic):
        self.out, self.every, self.clock = pathlib.Path(out), every, clock
        self._lock = threading.Lock()
        self._last, self._at = None, None

    def status(self):
        with self._lock:
            now = self.clock()
            if self._last is not None and now - self._at < self.every:
                return self._last
            rows = check(self.out)
            stale = {r["file"] for r in rows if r["stale"]}
            self._last = {"parts": rows, "stale": PS.stale_screens(screen_deps(self.out), stale) if stale else []}
            self._at = now
            return self._last
