"""Edge — measure the current code stamp: git tree hash, file-hash fallback when not in git. 도장 모양·규칙은 code_stamp(순수 Model).

- current(ref) = 저장소면 'g:<ref 의 core 나무 sha 앞 16>'(build_ref 가 그 ref 로 빌드하는 코드) · 저장소가 아니면(설치본) 작업 트리 빌드 입력 내용 'w:…'.
  재지 못하면 None(ref 가 없음 · 파일을 못 읽음) — 부르는 쪽은 판단하지 않는다(헛 빌드·헛 재시작을 막음, code_stamp.stale).
- work_stamp() = code_inputs() 내용 도장 — build_canvas 가 HD_CODE_STAMP 없이 빌드할 때 index.html 에 적는 것.
- 앱 부품(parts.json): tree_shas(repo, paths) = 다른 저장소의 HEAD:<경로> 나무 sha 들(도장 모양은 part_stamp.tree_of) · dirty(repo, paths) = 그 경로에 커밋하지 않은 변경이 있나.
  재지 못하면 None — 부르는 쪽은 판단하지 않는다.
부르는 곳: build_ref(빌드에 넘길 도장) · build_canvas(작업 트리 도장) · helper(뜰 때 표지의 code) · hd_client(열기 전 견주기) · parts_file · hd_parts(앱 부품).
오류 탐지: git 이 없거나 실패하면 예외 대신 None/대체 길, 파일을 못 읽으면 stderr 에 '[code_probe]' 한 줄 뒤 None.
"""
import pathlib
import subprocess
import sys

import code_stamp as CS

HERE = pathlib.Path(__file__).resolve().parent
CORE = HERE.parents[1]                                   # .../core
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Windows: 창 없는 도우미(pythonw)가 부르면 git 이 콘솔 창을 띄웠다 닫는다
MODULES_DIR = HERE / "modules"


def code_inputs():
    """도장에 드는 빌드 입력 파일(작업 트리 내용 해시 — 저장소가 아닐 때). 차례는 상관없다(content_stamp 가 이름으로 줄 세움)."""
    return [HERE / "canvas_template.html", *sorted(MODULES_DIR.glob("*.js")), MODULES_DIR / "shell.css", MODULES_DIR / "motion.css",
            HERE / "build_canvas.py", HERE / "code_stamp.py", HERE / "links.py", HERE / "board_data.py", HERE / "code_probe.py", HERE / "page_fill.py",
            CORE / "foundation" / "palette.js"]


def work_stamp():
    """작업 트리 빌드 입력의 내용 도장 'w:…'(없는 파일은 뺌)."""
    return CS.content_stamp([(p.relative_to(CORE).as_posix(), p.read_bytes()) for p in code_inputs() if p.is_file()])


def _git(*args):
    """git -C CORE … → (종료 코드, 출력). git 이 없으면 (127, '')."""
    return _git_in(CORE, *args)


def _git_in(repo, *args):
    """git -C repo … → (종료 코드, 출력). git 이 없거나 폴더가 없으면 (127, '')."""
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=NO_WINDOW)
    except (OSError, ValueError):
        return 127, ""
    return r.returncode, (r.stdout if r.returncode == 0 else r.stderr)


def tree_shas(repo, paths):
    """repo 의 HEAD:<경로> sha 들 → [(경로, sha)] | None(저장소 아님 · 커밋에 없는 경로 · git 없음). 커밋된 것만 본다."""
    paths = list(paths or [])
    if not paths:
        return None
    code, out = _git_in(repo, "rev-parse", *["HEAD:" + p for p in paths])
    shas = out.split() if code == 0 else []
    return list(zip(paths, shas)) if len(shas) == len(paths) else None


def dirty(repo, paths):
    """repo 의 그 경로들에 커밋하지 않은 변경(추적 안 한 파일 포함)이 있나 → bool | None(재지 못함)."""
    code, out = _git_in(repo, "status", "--porcelain", "--", *list(paths or []))
    return bool(out.strip()) if code == 0 else None


def current(ref="HEAD"):
    """지금 빌드가 쓸 캔버스 코드의 도장 — 저장소면 'g:<ref:core 나무 sha 앞 16>', 아니면(설치본) 작업 트리 내용 'w:…'. 재지 못하면 None."""
    code, sha = _git("rev-parse", "--verify", "--quiet", f"{ref}:./")
    if code == 0:
        return CS.tree_stamp(sha)
    code, _ = _git("rev-parse", "--show-prefix")
    if code == 0:
        return None                                      # 저장소인데 ref 가 없음 — 모름(헛 빌드를 하지 않게)
    try:
        return work_stamp()
    except OSError as e:
        print(f"[code_probe] 코드 도장을 재지 못했어요: {e}", file=sys.stderr)
        return None
