"""Edge — AI 작업 덮개 state.busy(claim · release, 상태 파일 자물쇠 안) + 화면 파일 지켜보기(#254: 1초마다 mtime → 바뀐 화면마다 seq).

상태: 지켜보기 기준(FileWatch: seq · last · at) · 지켜보기 스레드 하나 — 주인 = Busy. 덮개 자체는 상태 파일(state_store)에, 규칙은 hd_model.claim/release.
부르는 곳: session.ProjectSession(Busy, History 의 on_written = absorb) · router(/api/claim · /api/release · /api/files · /api/watch) · helper(예전 이름).
오류 탐지: screens.json 을 못 읽으면 [hd] 한 줄(한 번) 뒤 그 차례를 건너뜀 · 모양이 틀린 claim 은 400, 없는 화면은 404 · 덮개 경고는 stderr 로.
"""
import datetime, json, pathlib, re, sys, threading

import events as EV  # 바뀐 것 알림(claim · release · screen.written by ai · ai.write)
from out_io import _inside, _screen_files  # out_io 가 hd 폴더를 sys.path 에 넣는다
from state_store import _state_save, state_load

import hd_model  # noqa: E402  — 덮개 규칙(claim_error · claim · release)


def _str(v):
    return v if isinstance(v, str) else None


def watch(out, files):
    """화면 파일 바뀐 시각 보기(Q2b) — files = out 기준 상대 경로 목록 → {mtimes:{경로: st_mtime | None}}. 없거나 out 밖이면 None."""
    out = pathlib.Path(out).resolve()
    mtimes = {}
    if not isinstance(files, list):
        return {"mtimes": mtimes}
    for f in files:
        if not isinstance(f, str):
            continue
        try:
            p = out / f
            mtimes[f] = p.stat().st_mtime if _inside(out, p) and p.is_file() else None
        except (OSError, ValueError):
            mtimes[f] = None
    return {"mtimes": mtimes}



def claim_post(out, body, now_ms=None):
    """POST /api/claim 본문 {screen, by?, note?} → (code, 답). 최신 상태 파일 state.busy 에 cli 덮개를 넣고 rev+1."""
    if not isinstance(body, dict):
        return 400, {"error": "{screen, by?, note?} 가 아니에요"}
    sid, by, note = body.get("screen"), body.get("by"), body.get("note")
    err = hd_model.claim_error(sid, by, note)
    if err:
        return 400, {"error": err}
    try:
        files = _screen_files(json.loads((pathlib.Path(out) / "screens.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return 500, {"error": "screens.json 을 읽지 못했어요: %s" % e}
    if sid not in files:
        return 404, {"error": "없는 화면: %s" % sid}
    f = pathlib.Path(out).resolve() / files[sid]
    mtime = f.stat().st_mtime if _inside(pathlib.Path(out).resolve(), f) and f.is_file() else None
    cur = state_load(out)
    busy, warns = hd_model.claim(cur["state"].get("busy"), sid, files[sid], int(now_ms if now_ms is not None else datetime.datetime.now().timestamp() * 1000),
                                 mtime, by, note)
    for w in warns:
        print(w, file=sys.stderr, flush=True)
    rev = _state_save(out, cur["rev"] + 1, dict(cur["state"], busy=busy))
    return 200, {"rev": rev, "screen": sid, "file": files[sid]}



def release_post(out, body):
    """POST /api/release 본문 {screen} → (code, 답). 덮개가 있으면 걷고 rev+1, 없으면 released false(쓰지 않음)."""
    if not isinstance(body, dict) or not isinstance(body.get("screen"), str) or not body["screen"]:
        return 400, {"error": "screen: 화면 id 가 없어요"}
    cur = state_load(out)
    busy, gone, warns = hd_model.release(cur["state"].get("busy"), body["screen"])
    for w in warns:
        print(w, file=sys.stderr, flush=True)
    if not gone:
        return 200, {"rev": cur["rev"], "released": False}
    return 200, {"rev": _state_save(out, cur["rev"] + 1, dict(cur["state"], busy=busy)), "released": True}



WATCH_EVERY = 1.0
TOKENS = "@tokens"                                   # /api/files 바뀐 목록의 토큰 파일 줄(R55)
SHEETS = ((TOKENS, "tokens.css"), ("@components", "components.css"))   # 화면 id 가 아닌 공용 스타일 파일 줄(R55 phase C)



class FileWatch:
    """화면 → mtime 을 받아 바뀐 화면을 seq 로 적는다. tick 은 I/O 가 없다(unit 테스트) — 파일을 보는 일은 scan()."""
    def __init__(self):
        self.seq, self.last, self.at = 0, None, {}       # at: 화면 → 마지막으로 바뀐 seq
        self._lock = threading.Lock()

    def tick(self, mtimes):
        """mtimes = {화면: mtime|None} → 이번에 바뀐 화면 목록(처음 = 기준만, []). 생김·없어짐·시각 바뀜 = 바뀜."""
        with self._lock:
            prev, self.last = self.last, dict(mtimes)
            if prev is None:
                return []
            changed = sorted(k for k in set(prev) | set(mtimes) if prev.get(k) != mtimes.get(k) and k in mtimes)
            if changed:
                self.seq += 1
                for k in changed:
                    self.at[k] = self.seq
            return changed

    def absorb(self, mtimes):
        """도우미가 스스로 쓴 뒤(apply·delete·restore) — 지금 시각을 기준으로만 삼고 알리지 않는다(캔버스가 이미 그 카드를 다시 싣는다)."""
        with self._lock:
            self.last = dict(mtimes)

    def changes(self, since):
        """since 보다 뒤에 바뀐 화면 → {seq, changed}. since < 0 = 기준만."""
        with self._lock:
            if since is None or since < 0:
                return {"seq": self.seq, "changed": []}
            return {"seq": self.seq, "changed": sorted(k for k, s in self.at.items() if s > since)}



def scan(out, cache):
    """screens.json 에 적힌 화면 파일(out 안만) + '@tokens'·'@components'(out/tokens.css·components.css, R55) → {화면: mtime|None} | None(screens.json 을 못 읽음 — [hd] 한 줄). cache = {'sj': (mtime, files)} — screens.json 이 바뀔 때만 다시 읽는다."""
    out = pathlib.Path(out)
    sj = out / "screens.json"
    try:
        m = sj.stat().st_mtime
        if cache.get("sj", (None,))[0] != m:
            cache["sj"] = (m, _screen_files(json.loads(sj.read_text(encoding="utf-8"))))
    except (OSError, ValueError, KeyError, TypeError) as e:
        if not cache.get("warned"):
            print("[hd] 화면 지켜보기: screens.json 을 읽지 못했어요(%s)" % e, file=sys.stderr, flush=True)
            cache["warned"] = True
        return None                                   # 이번 차례는 건너뜀(쓰는 중인 screens.json 이 모든 카드를 '바뀜'으로 만들지 않게)
    cache["warned"] = False
    res = {}
    for sid, rel in cache["sj"][1].items():
        p = out / rel
        try:
            res[sid] = _newest(out, p, cache) if _inside(out, p) and p.is_file() else None
        except (OSError, ValueError):
            res[sid] = None
    for key, name in SHEETS:                          # R55 — 공용 스타일 파일은 자기 줄 '@tokens'·'@components'(화면 id 가 아님): 캔버스가 모든 틀의 그 스타일만 다시 읽는다
        f = out / name
        try:
            res[key] = f.stat().st_mtime if f.is_file() else None
        except OSError:
            res[key] = None
    return res


_DEP = re.compile(r"""<(?:iframe|link|script)\b[^>]*?\b(?:src|href)\s*=\s*["']([^"'#?]+)""", re.I)


def _deps(out, p, cache):
    """화면이 iframe·link·script 로 끌어 쓰는 out 안 파일들(F25) — 화면 mtime 이 바뀔 때만 다시 읽는다. 바깥 주소(scheme·//)는 뺀다."""
    m = p.stat().st_mtime
    hit = cache.setdefault("deps", {}).get(p)
    if hit and hit[0] == m:
        return hit[1]
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    found = []
    for ref in _DEP.findall(text):
        if ":" in ref or ref.startswith("/"):
            continue
        d = (p.parent / ref).resolve()
        if d != p.resolve() and _inside(out, d):
            found.append(d)
    cache["deps"][p] = (m, found)
    return found


def _newest(out, p, cache):
    """화면 파일과 그 화면이 끌어 쓰는 파일 중 가장 늦은 mtime — 안쪽 파일만 바뀌어도 카드를 다시 싣게(F25)."""
    t = p.stat().st_mtime
    for d in _deps(out, p, cache):
        try:
            t = max(t, d.stat().st_mtime)
        except OSError:
            pass
    return t



class Busy:
    """AI 작업 덮개 state.busy(claim · release, 상태 파일 자물쇠 안) + 화면 파일 지켜보기(1초마다 mtime → FileWatch seq)."""

    def __init__(self, out, lock, ai=None, bus=None):
        self.out, self.lock, self.ai, self.bus = out, lock, ai, bus
        self.watch, self.stop = FileWatch(), threading.Event()

    def claim(self, body):
        with self.lock:
            code, res = claim_post(self.out, body)
            if code == 200 and self.ai is not None:
                self.ai.begin(res["screen"], res["file"])   # 48c — AI 가 쓰기 전 모습
            if code == 200:
                EV.emit(self.bus, "claim", screen=res["screen"], rev=res["rev"], by=_str(body.get("by")), note=_str(body.get("note")))
        return code, res

    def release(self, body):
        with self.lock:
            code, res = release_post(self.out, body)
            if code == 200 and self.ai is not None:
                self._ai(body["screen"], self.ai.end)   # 48c — 마지막으로 보고 끝
            if code == 200 and res.get("released"):
                EV.emit(self.bus, "release", screen=body["screen"], rev=res["rev"])
        return code, res

    def mtimes(self, files):
        return watch(self.out, files)

    def files(self, since):
        return self.watch.changes(since)

    def absorb(self):
        m = scan(self.out, {})
        if m is not None:
            self.watch.absorb(m)

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

    def close(self):
        self.stop.set()

    def _loop(self):
        cache = {}
        while not self.stop.wait(WATCH_EVERY if self.watch.last is not None else 0):
            with self.lock:                          # 도우미가 쓰는 중(apply 의 쓰기~빌드)에는 보지 않는다 — 다 쓴 뒤 absorb 가 기준을 옮긴다
                m = scan(self.out, cache)
                if m is not None:
                    changed = self.watch.tick(m)
                    if changed:
                        EV.emit(self.bus, "screen.written", screens=changed, by="ai", rev=self.watch.seq, stamp=None)
                    for sid in changed:
                        if self.ai is not None and not sid.startswith("@"):   # AI 되돌리기 줄은 화면마다(토큰 파일은 아님)
                            self._ai(sid, self.ai.seen)

    def _ai(self, sid, fn):
        """AiUndo.seen · end 를 부르고, 기록 줄이 생기거나(record) 기준이 옮겨지면(update) ai.write — GET /api/ai-writes 의 한 줄 + act."""
        n = len(self.ai.log)
        act = fn(sid)                                # seen → 'record'|'update'|None · end → 끝난 항목(마지막으로 seen 을 부른다)
        act = act if act in ("record", "update") else ("record" if len(self.ai.log) > n else None)
        row = self.ai.log[-1] if len(self.ai.log) > n else self.ai.row(sid)
        if act in ("record", "update") and row is not None:
            EV.emit(self.bus, "ai.write", seq=row["seq"], stamp=row["stamp"], screen=row["screen"], label=row["label"], act=act)
