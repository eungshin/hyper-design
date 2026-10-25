"""커밋된 캔버스 코드로 빌드한다 — 다른 세션이 작업 트리의 캔버스를 고치는 중이어도 실사용 빌드가 깨지지 않게(R10).

python3 build_ref.py <out_dir> [--ref HEAD]

- 이 파일이 있는 저장소에서 `git archive <ref> <core 폴더>`를 임시 폴더에 풀고, 그 사본의 build_canvas.py <out> 를 돌린다.
  끝나면 임시 폴더를 지우고 그 종료 코드로 끝난다. 작업 트리의 캔버스 모듈은 읽지 않는다.
- git 저장소가 아니면(설치본 등) 경고 한 줄 뒤 작업 트리의 build_canvas.py 로 빌드한다.
- 캐시(49d): 풀어 둔 core 나무를 `<ref>:<core>` 나무 sha 이름으로 `<임시 폴더>/hd-build-ref/`(환경변수 `HD_BUILD_REF_CACHE` 로 바꿈)에 두고,
  sha 가 같으면 git archive·풀기 없이 그 사본으로 빌드한다(편집 한 번의 다시 빌드에서 약 1.5~5초). 다 풀었다는 표시 `.hd-ok` 가 있는 폴더만 다시 쓴다.
  만들 때는 `<sha>.tmp-<pid>` 에 풀고 이름을 바꾼다(동시에 둘이 풀면 늦은 쪽이 제 것을 지움). 쓸 때마다 표시 시각을 새로 하고,
  최근에 쓴 KEEP 개와 GRACE 초 안에 쓴 것 말고는 지운다(prune). 캐시를 쓸 수 없으면(폴더 못 만듦 등) 예전처럼 한 번 쓰고 지우는 임시 폴더로.
- 코드 도장(code_stamp.py): code_probe.current(ref) = 'g:<ref 의 core 나무 sha>' — 빌드에 HD_CODE_STAMP 로 넘겨 index.html 이 품는다.
  재기는 code_probe.current(ref) — 열기(hd open · 허브)·도우미·허브 프로세스가 같은 함수로 '지금 코드'를 잰다. 저장소가 아니면 작업 트리 내용 도장(code_probe.work_stamp).
"""
import argparse, io, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:                            # code_probe(지금 코드 도장 재기) — 다른 폴더에서 불러도
    sys.path.insert(0, str(HERE))
import code_probe as CP  # noqa: E402  — 지금 코드 도장 재기(Edge)
CORE = HERE.parents[1]                                   # .../core
REL = HERE.relative_to(CORE)                             # features/canvas
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: 창 없는 도우미(pythonw)가 부르면 자식(git·빌드)이 콘솔 창을 띄웠다 닫는다
OK = ".hd-ok"                                            # 다 풀었다는 표시(쓸 때마다 시각을 새로 = 마지막으로 쓴 때)
KEEP, GRACE = 3, 600                                     # 남길 sha 수 · 이 초 안에 쓴 것은 지우지 않는다(다른 빌드가 쓰는 중일 수 있음)
SHA = re.compile(r"^[0-9a-f]{40,64}$")
TMP = re.compile(r"^[0-9a-f]{40,64}\.tmp-\d+$")


def prune(entries, keep=KEEP, now=None, grace=GRACE):
    """[(이름, 마지막으로 쓴 시각)] → 지울 이름(오래된 것부터). sha 폴더는 최근 keep 개·grace 안 것을 남기고, 만들다 만 .tmp- 폴더는 grace 가 지난 것만. 다른 이름은 손대지 않는다."""
    now = time.time() if now is None else now
    shas = sorted((e for e in entries if SHA.match(e[0])), key=lambda e: e[1], reverse=True)
    drop = [e for e in shas[keep:] if now - e[1] > grace]
    drop += [e for e in entries if TMP.match(e[0]) and now - e[1] > grace]
    return [n for n, _ in sorted(drop, key=lambda e: e[1])]


def usable(names):
    """캐시 폴더 안 이름들 → 다시 써도 되나(다 풀었다는 표시가 있다)."""
    return OK in names


def git(*args, binary=False):
    """git -C CORE … → (종료 코드, 출력). git 이 없으면 (127, '')."""
    try:
        r = subprocess.run(["git", "-C", str(CORE), *args], capture_output=True, text=not binary, creationflags=NO_WINDOW)
    except OSError:
        return 127, b"" if binary else ""
    return r.returncode, (r.stdout if r.returncode == 0 else r.stderr)


def run_build(script, out, stamp=None):
    env = {k: v for k, v in os.environ.items() if k != "HD_CODE_STAMP"}
    if stamp:
        env["HD_CODE_STAMP"] = stamp                     # 빌드가 index.html 에 적을 도장(없으면 그 빌드의 작업 트리 내용 도장)
    return subprocess.run([sys.executable, str(script), str(out)], env=env, creationflags=NO_WINDOW).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description="커밋된 캔버스 코드로 <out>/index.html 을 만든다")
    ap.add_argument("out")
    ap.add_argument("--ref", default="HEAD")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out).resolve()

    code, prefix = git("rev-parse", "--show-prefix")
    if code != 0:
        print("[build_ref] git 저장소가 아니에요 — 작업 트리의 build_canvas.py 로 빌드합니다", file=sys.stderr)
        return run_build(HERE / "build_canvas.py", out)
    prefix = prefix.strip()                              # 예: plugins/hyper-design/core/
    stamp = CP.current(a.ref)
    script = cached(a.ref, prefix)
    if script is not None:
        return run_build(script, out, stamp)
    code, data = git("archive", "--format=tar", a.ref, ":(top)" + prefix, binary=True)  # 경로는 저장소 뿌리 기준
    if code != 0:
        print(f"[build_ref] git archive {a.ref} 실패: {data.decode('utf-8', 'replace').strip()}", file=sys.stderr)
        return 1
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-build-ref-"))
    try:
        unpack(data, tmp)
        script = find_script(tmp, prefix)
        if script is None:
            print(f"[build_ref] {a.ref} 에 build_canvas.py 가 없어요: {prefix}{REL.as_posix()}", file=sys.stderr)
            return 1
        return run_build(script, out, stamp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def unpack(data, dest):
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        if hasattr(tarfile, "data_filter"):
            t.extractall(dest, filter="data")
        else:
            t.extractall(dest)


def find_script(root, prefix):
    # 하위 폴더에서 돈 git archive 는 core 를 뿌리로 푼다(판에 따라 전체 경로일 수도 있어 둘 다 본다)
    return next((p for p in (root / REL / "build_canvas.py", root / prefix / REL / "build_canvas.py") if p.is_file()), None)


def cache_root():
    return pathlib.Path(os.environ.get("HD_BUILD_REF_CACHE") or pathlib.Path(tempfile.gettempdir()) / "hd-build-ref")


def cached(ref, prefix):
    """ref 의 core 나무 sha 로 풀어 둔 사본의 build_canvas.py — 없으면 풀어 만든다. 캐시를 못 쓰면 None(부르는 쪽이 예전 길로)."""
    code, sha = git("rev-parse", "--verify", "--quiet", f"{ref}:{prefix}".rstrip("/") if prefix else f"{ref}^{{tree}}")
    sha = sha.strip() if code == 0 else ""
    if not SHA.match(sha):
        return None                                      # ref 가 없음 등 — 예전 길이 git archive 오류를 그대로 알린다
    root = cache_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        tidy(root, sha)
        home = root / sha
        if home.is_dir() and usable({p.name for p in home.iterdir()}):
            script = find_script(home, prefix)
            if script is not None:
                (home / OK).touch()
                return script
            shutil.rmtree(home, ignore_errors=True)
        elif home.exists():
            shutil.rmtree(home, ignore_errors=True)      # 풀다 멈춘 것
        code, data = git("archive", "--format=tar", ref, ":(top)" + prefix, binary=True)
        if code != 0:
            return None
        part = root / f"{sha}.tmp-{os.getpid()}"
        shutil.rmtree(part, ignore_errors=True)
        unpack(data, part)
        (part / OK).write_text(sha, encoding="utf-8")
        try:
            part.rename(home)
        except OSError:                                  # 다른 빌드가 먼저 만들었다 — 그것을 쓴다
            shutil.rmtree(part, ignore_errors=True)
        return find_script(home, prefix) if home.is_dir() and usable({p.name for p in home.iterdir()}) else None
    except OSError as e:
        print(f"[build_ref] 캐시를 쓰지 못해 한 번 쓰는 임시 폴더로 빌드해요: {e}", file=sys.stderr)
        return None


def tidy(root, keep_sha):
    ents = []
    for p in root.iterdir():
        if p.name == keep_sha:
            continue
        try:
            ok = p / OK
            ents.append((p.name, (ok if ok.exists() else p).stat().st_mtime))
        except OSError:
            continue
    for name in prune(ents):
        shutil.rmtree(root / name, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
