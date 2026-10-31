"""Edge — 공용 셸 저장소(보드 전환 1단계 P1a): 코드 도장 하나에 셸 한 벌을 한 번만 만들고 모든 프로젝트가 같이 쓴다.

- 폴더 = `<build_ref 캐시 뿌리>/shell/<core 나무 sha>/` — hd-shell.js · hd-shell.css · skeleton.html · 다 만든 표시 `.hd-ok`.
  이름이 나무 sha(40~64 hex)라 오래된 폴더 정리는 build_ref.prune 그 규칙 그대로(최근 KEEP 개 · GRACE 초 안 것은 남김, 만들다 만 `.tmp-<pid>` 는 GRACE 뒤).
- 만들기(ensure) = 그 도장의 코드 사본(build_ref 캐시 나무 `<캐시 뿌리>/<sha>/`)의 `build_canvas.py --shell <임시 폴더>` 를 하위 프로세스로 —
  지금 작업 트리가 아니라 그 도장의 코드로(개발 중 안전장치 R10 그대로). 사본이 캐시에 없고 그 도장이 지금 HEAD 면 build_ref.cached 로 푼다.
  `<sha>.tmp-<pid>` 에 만들고 이름을 바꾼다(동시에 둘이 만들면 늦은 쪽이 제 것을 지움). 이 프로세스 안에서는 도장마다 자물쇠 하나 — 같은 도장 두 번 안 만듦.
- 사본의 build_canvas.py 에 `--shell` 모드가 없으면(이 모드 전 커밋) 만들지 않고 None — 부르는 쪽은 예전 길(디스크 index.html). 이 프로세스에서 다시 묻지 않는다.
- 이음매(P1b): get(stamp) -> {"dir": Path, "js": url, "css": url, "skeleton": str} | None — 다 만든 폴더만, 만들지 않는다(페이지를 막지 않게).
  url = 허브 공용 주소 `/v1/shell/<도장>/hd-shell.js|css`(immutable — cache_policy). skeleton = 템플릿에서 셸 본 스크립트를 뺀 뼈대
  (hd-code meta 있음 · `<!-- hd-shell-css -->` · `<!-- hd-modules -->` · 빈 hd-data `{}` · 빈 `<noscript id="hd-links">` 자리는 그대로 — 끼우는 쪽이 채운다).
- 미리 만들기(Prebuilder): want(stamp) = 아직 안 본 도장이면 뒤 스레드 하나가 차례로 ensure(허브 registry 가 새 도장을 잴 때 부른다).
- 도장 모양: 'g:<나무 sha 앞 16>' 만(build_ref 캐시 나무가 있는 저장소 판). 'w:'(설치본·작업 트리 내용 도장)는 None — 예전 길.
규칙(도장 → hex · 주소 → (도장, 파일) · 주소 만들기)은 순수 함수(tests/test_canvas_unit_shell_store.py), 파일·프로세스는 ShellStore.
오류 탐지: 만들기 실패(사본 없음 · 빌드 실패 · 결과 도장이 다름 · 파일 못 씀)는 `[hd]` 한 줄 뒤 None — 페이지는 예전 길로 늘 열린다.
"""
import os, pathlib, re, shutil, subprocess, sys, threading, urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_ref as BR  # noqa: E402  — 캐시 뿌리 · 나무 사본 · 정리 규칙(prune)
import code_stamp as CS  # noqa: E402

FILES = ("hd-shell.js", "hd-shell.css")                 # 공용 주소로 내주는 파일(그 밖은 404)
SKELETON = "skeleton.html"
OK = BR.OK
PREFIX = "/v1/shell/"
MODE = "--shell"                                         # 사본의 build_canvas.py 가 이 글을 품어야 그 모드가 있다고 본다
TIMEOUT = 180
_STAMP = re.compile(r"^g:([0-9a-f]{16})$")


def stamp_hex(stamp):
    """도장 → 나무 sha 앞 16 hex | None('g:' 도장이 아님 — 'w:' · 빈 값 · 다른 모양). 순수."""
    m = _STAMP.match(stamp or "") if isinstance(stamp, str) else None
    return m.group(1) if m else None


def url(stamp, name):
    """허브 공용 주소 `/v1/shell/<도장>/<파일>`. 순수."""
    return PREFIX + urllib.parse.quote(stamp, safe=":") + "/" + name


def route(path):
    """요청 경로(물음 뺀 것) → (도장, 파일) | None — `/v1/shell/` 아래가 아니거나 도장·파일 이름이 틀림(경로 탈출 포함). 순수."""
    if not isinstance(path, str) or not path.startswith(PREFIX):
        return None
    parts = urllib.parse.unquote(path[len(PREFIX):]).split("/")
    if len(parts) != 2 or parts[1] not in FILES or stamp_hex(parts[0]) is None:
        return None
    return parts[0], parts[1]


def pick_tree(names, hex16):
    """캐시 뿌리 이름들 → 그 도장(앞 16)의 나무 sha 이름 | None. 순수(다 풀었나는 부르는 쪽이 본다)."""
    hits = sorted(n for n in names if BR.SHA.match(n) and n.startswith(hex16))
    return hits[0] if hits else None


def has_mode(src):
    """사본 build_canvas.py 글 → `--shell` 모드가 있나. 순수."""
    return MODE in (src or "")


def run_shell(script, dest, stamp):
    """사본의 build_canvas.py --shell dest(HD_CODE_STAMP=stamp) → (종료 코드, 끝 줄). Edge."""
    env = {k: v for k, v in os.environ.items() if k != "HD_CODE_STAMP"}
    env["HD_CODE_STAMP"] = stamp
    try:
        r = subprocess.run([sys.executable, str(script), MODE, str(dest)], env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT, creationflags=BR.NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)
    tail = (r.stderr or r.stdout or "").strip().splitlines()
    return r.returncode, tail[-1] if tail else ""


def head_tree():
    """지금 HEAD 의 core 나무 사본 → (나무 sha, 사본의 build_canvas.py) | None(저장소 아님 · 캐시를 못 씀). build_ref.cached 그대로."""
    code, prefix = BR.git("rev-parse", "--show-prefix")
    if code != 0:
        return None
    script = BR.cached("HEAD", prefix.strip())
    if script is None:
        return None
    try:
        return script.resolve().relative_to(BR.cache_root().resolve()).parts[0], script
    except (ValueError, IndexError):
        return None


class ShellStore:
    """도장별 셸 폴더들. root = 셸 뿌리(기본 `<build_ref 캐시 뿌리>/shell`), trees = 나무 사본 뿌리(기본 build_ref 캐시 뿌리),
    run(script, dest, stamp) = 하위 프로세스 빌드 · head = 지금 HEAD 나무 풀기(테스트가 바꿔 끼움)."""

    def __init__(self, root=None, trees=None, run=None, head=None):
        self._root, self._trees = root, trees
        self.run, self.head = run or run_shell, head or head_tree
        self._lock = threading.Lock()
        self._locks = {}                                 # 나무 sha 앞 16 → 자물쇠(이 프로세스 안 같은 도장 만들기는 하나씩)
        self._done = {}                                  # 도장 → get 답(읽은 뼈대 기억)
        self._nope = set()                               # 이 프로세스에서 다시 만들지 않을 도장(--shell 없는 사본 · 실패)

    def root(self):
        return pathlib.Path(self._root) if self._root else BR.cache_root() / "shell"

    def trees(self):
        return pathlib.Path(self._trees) if self._trees else BR.cache_root()

    # ------------------------------------------------------------ 읽기(이음매)
    def get(self, stamp):
        """다 만든 셸 → {"dir", "js", "css", "skeleton"} | None(아직 없음 · 'g:' 도장 아님). 만들지 않는다."""
        hex16 = stamp_hex(stamp)
        if hex16 is None:
            return None
        hit = self._done.get(stamp)
        if hit is not None and (hit["dir"] / OK).is_file():
            return hit
        d = self._find(hex16)
        if d is None:
            return None
        try:
            skeleton = (d / SKELETON).read_text(encoding="utf-8")
            (d / OK).touch()                             # 쓴 때 = 정리 규칙의 시각(build_ref 와 같게)
        except OSError:
            return None
        if CS.page_stamp(skeleton) != stamp:
            return None
        hit = {"dir": d, "js": url(stamp, FILES[0]), "css": url(stamp, FILES[1]), "skeleton": skeleton}
        self._done[stamp] = hit
        return hit

    def file(self, stamp, name):
        """공용 주소가 내줄 파일 → Path | None(다 만든 폴더 · 아는 파일 이름만)."""
        if name not in FILES:
            return None
        hit = self.get(stamp)
        p = hit["dir"] / name if hit else None
        return p if p is not None and p.is_file() else None

    def _find(self, hex16):
        try:
            names = [p.name for p in self.root().iterdir()]
        except OSError:
            return None
        name = pick_tree([n for n in names if (self.root() / n / OK).is_file()], hex16)
        return self.root() / name if name else None

    # ------------------------------------------------------------ 만들기
    def ensure(self, stamp):
        """그 도장의 셸을 (없으면) 만들고 get 답 | None. 같은 도장은 이 프로세스에서 하나씩 · 다 만들었으면 다시 만들지 않는다."""
        hex16 = stamp_hex(stamp)
        if hex16 is None:
            return None
        with self._lock:
            lock = self._locks.setdefault(hex16, threading.Lock())
        with lock:
            hit = self.get(stamp)
            if hit is not None or stamp in self._nope:
                return hit
            try:
                return self._make(stamp, hex16)
            except OSError as e:
                print("[hd] 공용 셸(%s)을 만들지 못했어요(%s) — 예전 길(프로젝트마다 셸)로" % (stamp, e), file=sys.stderr, flush=True)
                self._nope.add(stamp)
                return None

    def _tree(self, hex16):
        """그 도장의 나무 사본 → (sha, build_canvas.py) | None."""
        trees = self.trees()
        try:
            names = [p.name for p in trees.iterdir() if (p / OK).is_file()]
        except OSError:
            names = []
        sha = pick_tree(names, hex16)
        if sha is not None:
            script = BR.find_script(trees / sha, "") or next(iter(sorted((trees / sha).glob("**/features/canvas/build_canvas.py"))), None)
            if script is not None:
                return sha, script
        got = self.head()                                # 캐시에 없으면 지금 HEAD 를 풀어 본다(그 도장일 때만 쓴다)
        return got if got is not None and got[0].startswith(hex16) else None

    def _make(self, stamp, hex16):
        tree = self._tree(hex16)
        if tree is None:
            print("[hd] 공용 셸: 도장 %s 의 코드 사본이 없어요 — 예전 길로" % stamp, file=sys.stderr, flush=True)
            self._nope.add(stamp)
            return None
        sha, script = tree
        if not has_mode(script.read_text(encoding="utf-8", errors="replace")):
            print("[hd] 공용 셸: 도장 %s 의 build_canvas.py 에 --shell 이 없어요(그 전 커밋) — 예전 길로" % stamp, file=sys.stderr, flush=True)
            self._nope.add(stamp)
            return None
        root = self.root()
        root.mkdir(parents=True, exist_ok=True)
        part = root / ("%s.tmp-%d" % (sha, os.getpid()))
        shutil.rmtree(part, ignore_errors=True)
        part.mkdir(parents=True)
        code, tail = self.run(script, part, stamp)
        bad = self._check(part, stamp) if code == 0 else "종료 코드 %d: %s" % (code, tail)
        if bad:
            shutil.rmtree(part, ignore_errors=True)
            print("[hd] 공용 셸(%s)을 만들지 못했어요(%s) — 예전 길로" % (stamp, bad), file=sys.stderr, flush=True)
            self._nope.add(stamp)
            return None
        (part / OK).write_text(stamp, encoding="utf-8")
        try:
            part.rename(root / sha)
        except OSError:                                  # 다른 프로세스가 먼저 만들었다 — 그것을 쓴다
            shutil.rmtree(part, ignore_errors=True)
        self._tidy(root, sha)
        return self.get(stamp)

    @staticmethod
    def _check(d, stamp):
        """만든 폴더 → 틀린 까닭 글 | None(맞음)."""
        for n in (*FILES, SKELETON):
            if not (d / n).is_file() or (d / n).stat().st_size == 0:
                return "%s 이 없어요" % n
        have = CS.page_stamp((d / SKELETON).read_text(encoding="utf-8", errors="replace"))
        return None if have == stamp else "뼈대 도장이 달라요: %s" % have

    @staticmethod
    def _tidy(root, keep):
        ents = []
        for p in root.iterdir():
            if p.name == keep:
                continue
            try:
                ok = p / OK
                ents.append((p.name, (ok if ok.exists() else p).stat().st_mtime))
            except OSError:
                continue
        for name in BR.prune(ents):
            shutil.rmtree(root / name, ignore_errors=True)


class Prebuilder:
    """미리 만들기 — want(stamp) 가 아직 안 본 도장을 줄에 넣고 뒤 스레드 하나가 차례로 store.ensure. 같은 도장은 두 번 넣지 않는다."""

    def __init__(self, store):
        self.store = store
        self._lock = threading.Lock()
        self._seen, self._queue, self._worker = set(), [], None

    def want(self, stamp):
        """→ 새로 줄에 넣었나('g:' 도장 아님 · 이미 본 도장 = 아니)."""
        if stamp_hex(stamp) is None:
            return False
        with self._lock:
            if stamp in self._seen:
                return False
            self._seen.add(stamp)
            self._queue.append(stamp)
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._drain, name="hd-shell-prebuild", daemon=True)
                self._worker.start()
        return True

    def _drain(self):
        while True:
            with self._lock:
                if not self._queue:
                    self._worker = None
                    return
                stamp = self._queue.pop(0)
            try:
                self.store.ensure(stamp)
            except Exception as e:                       # noqa: BLE001 — 미리 만들기 실패는 예전 길로(허브는 멈추지 않는다)
                print("[hd] 공용 셸 미리 만들기가 멈췄어요(%s): %s" % (stamp, e), file=sys.stderr, flush=True)

    def wait(self, timeout=None):
        """줄이 빌 때까지(테스트용) → 다 비었나."""
        w = self._worker
        if w is not None:
            w.join(timeout)
        return self._worker is None or not self._worker.is_alive()


STORE = ShellStore()
PREBUILD = Prebuilder(STORE)


def get(stamp):
    """이음매(P1b) — 다 만든 공용 셸 {"dir": Path, "js": url, "css": url, "skeleton": str} | None(없으면 부르는 쪽은 예전 길)."""
    return STORE.get(stamp)
