"""커밋된 캔버스 코드로 빌드한다 — 다른 세션이 작업 트리의 캔버스를 고치는 중이어도 실사용 빌드가 깨지지 않게(R10).

python3 build_ref.py <out_dir> [--ref HEAD]

- 이 파일이 있는 저장소에서 `git archive <ref> <core 폴더>`를 임시 폴더에 풀고, 그 사본의 build_canvas.py <out> 를 돌린다.
  끝나면 임시 폴더를 지우고 그 종료 코드로 끝난다. 작업 트리의 캔버스 모듈은 읽지 않는다.
- git 저장소가 아니면(설치본 등) 경고 한 줄 뒤 작업 트리의 build_canvas.py 로 빌드한다.
"""
import argparse, io, pathlib, shutil, subprocess, sys, tarfile, tempfile

HERE = pathlib.Path(__file__).resolve().parent
CORE = HERE.parents[1]                                   # .../core
REL = HERE.relative_to(CORE)                             # features/canvas
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: 창 없는 도우미(pythonw)가 부르면 자식(git·빌드)이 콘솔 창을 띄웠다 닫는다


def git(*args, binary=False):
    """git -C CORE … → (종료 코드, 출력). git 이 없으면 (127, '')."""
    try:
        r = subprocess.run(["git", "-C", str(CORE), *args], capture_output=True, text=not binary, creationflags=NO_WINDOW)
    except OSError:
        return 127, b"" if binary else ""
    return r.returncode, (r.stdout if r.returncode == 0 else r.stderr)


def run_build(script, out):
    return subprocess.run([sys.executable, str(script), str(out)], creationflags=NO_WINDOW).returncode


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
    code, data = git("archive", "--format=tar", a.ref, ":(top)" + prefix, binary=True)  # 경로는 저장소 뿌리 기준
    if code != 0:
        print(f"[build_ref] git archive {a.ref} 실패: {data.decode('utf-8', 'replace').strip()}", file=sys.stderr)
        return 1
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-build-ref-"))
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(tmp, filter="data")
            else:
                t.extractall(tmp)
        # 하위 폴더에서 돈 git archive 는 core 를 뿌리로 푼다(판에 따라 전체 경로일 수도 있어 둘 다 본다)
        script = next((p for p in (tmp / REL / "build_canvas.py", tmp / prefix / REL / "build_canvas.py") if p.is_file()), None)
        if script is None:
            print(f"[build_ref] {a.ref} 에 build_canvas.py 가 없어요: {prefix}{REL.as_posix()}", file=sys.stderr)
            return 1
        return run_build(script, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
