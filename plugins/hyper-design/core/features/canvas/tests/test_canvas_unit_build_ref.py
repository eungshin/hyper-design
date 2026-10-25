"""build_ref.py(R10) — 커밋된 캔버스 코드로 빌드. 브라우저 없음.

- 임시 git 저장소: 작업 트리의 build_canvas.py 가 깨져 있어도 커밋된 판으로 빌드된다 · 없는 ref 는 실패.
- git 저장소가 아니면 경고 한 줄 뒤 작업 트리의 build_canvas.py 로.
- 이 저장소 HEAD 로 실제 결과 폴더 사본을 빌드 → index.html (fixture 가 없으면 건너뜀).
셋 다 하위 프로세스(git·python 빌드)를 띄운다 — slow 표시로 unit 에서 빠진다(`-m slow` · 전체 실행에서 돈다).
"""
import os, shutil, subprocess, sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

HERE = Path(__file__).resolve().parent
CANVAS = HERE.parent
REPO = CANVAS.parents[4]
BUILD_REF = CANVAS / "build_ref.py"
FIXTURE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")

STUB_OK = "import sys, pathlib\npathlib.Path(sys.argv[1], 'index.html').write_text('{}', encoding='utf-8')\n"
STUB_BAD = "raise AssertionError('캔버스 모듈이 없다')\n"


def run(script, *args, env=ENV):
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", env=env)


def plant(root, stub):
    """root/plugins/hyper-design/core/features/canvas/ 에 build_ref.py 와 가짜 build_canvas.py."""
    d = root / "plugins" / "hyper-design" / "core" / "features" / "canvas"
    d.mkdir(parents=True)
    shutil.copyfile(BUILD_REF, d / "build_ref.py")
    (d / "build_canvas.py").write_text(stub, encoding="utf-8")
    return d


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


@pytest.mark.skipif(not shutil.which("git"), reason="git 없음")
def test_builds_from_committed_code_not_working_tree(tmp_path):
    root = tmp_path / "repo"
    d = plant(root, STUB_OK)
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "c")
    (d / "build_canvas.py").write_text(STUB_BAD, encoding="utf-8")      # 다른 세션이 고치는 중(미커밋)
    out = tmp_path / "out"
    out.mkdir()
    r = run(d / "build_ref.py", out)
    assert r.returncode == 0, r.stderr
    assert (out / "index.html").read_text(encoding="utf-8") == "{}"
    r = run(d / "build_ref.py", out, "--ref", "no-such-ref")
    assert r.returncode != 0 and "git archive" in r.stderr


def test_not_a_repo_falls_back_to_working_tree_with_warning(tmp_path):
    d = plant(tmp_path / "plain", STUB_OK)
    out = tmp_path / "out"
    out.mkdir()
    env = dict(ENV, GIT_CEILING_DIRECTORIES=str(tmp_path))              # 위쪽 저장소를 찾지 않게
    r = run(d / "build_ref.py", out, env=env)
    assert r.returncode == 0, r.stderr
    assert "git 저장소가 아니에요" in r.stderr
    assert (out / "index.html").exists()


@pytest.mark.skipif(not FIXTURE.exists(), reason=f"fixture 없음: {FIXTURE}")
def test_real_run_builds_from_head(tmp_path):
    out = tmp_path / "out"
    shutil.copytree(FIXTURE, out, ignore=shutil.ignore_patterns("index.html", ".hd-*"))
    r = run(BUILD_REF, out)
    assert r.returncode == 0, r.stderr
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'id="hd-data"' in html


def test_children_open_no_console_window(monkeypatch):
    """창 없는 도우미(pythonw)가 부르면 build_ref 도 pythonw — 그 자식(git·빌드)이 콘솔 창을 띄웠다 닫으면 편집마다 깜빡인다."""
    sys.path.insert(0, str(CANVAS))
    import build_ref
    seen = []

    def fake_run(args, **kw):
        seen.append(kw.get("creationflags", 0))
        return subprocess.CompletedProcess(args, 0, b"" if not kw.get("text") else "", "")
    monkeypatch.setattr(build_ref.subprocess, "run", fake_run)
    build_ref.git("rev-parse", "--show-prefix")
    build_ref.run_build(CANVAS / "build_canvas.py", "out")
    assert seen == [getattr(subprocess, "CREATE_NO_WINDOW", 0)] * 2


STUB_MARK = "import sys, pathlib\npathlib.Path(sys.argv[1], 'index.html').write_text('%s', encoding='utf-8')\n"


@pytest.mark.skipif(not shutil.which("git"), reason="git 없음")
def test_extracted_ref_is_reused_while_the_tree_sha_is_the_same(tmp_path):
    """49d: 다시 빌드마다 git archive + 풀기를 하지 않는다 — 풀어 둔 core 나무를 나무 sha 로 캐시(HD_BUILD_REF_CACHE)에 두고 sha 가 같으면 그대로 쓴다.
    ref 가 움직이면(core 가 바뀐 새 커밋) 새로 풀어 새 코드로 빌드한다."""
    root = tmp_path / "repo"
    d = plant(root, STUB_MARK % "one")
    git(root, "init", "-q"); git(root, "add", "."); git(root, "commit", "-q", "-m", "c1")
    cache = tmp_path / "cache"
    env = dict(ENV, HD_BUILD_REF_CACHE=str(cache))
    out = tmp_path / "out"; out.mkdir()
    r = run(d / "build_ref.py", out, env=env)
    assert r.returncode == 0, r.stderr
    assert (out / "index.html").read_text(encoding="utf-8") == "one"
    ents = [p for p in cache.iterdir() if p.is_dir()]
    assert len(ents) == 1 and (ents[0] / ".hd-ok").exists(), list(cache.iterdir())
    cached = next(ents[0].rglob("build_canvas.py"))
    cached.write_text(STUB_MARK % "cached", encoding="utf-8")            # 다시 풀면 사라질 표시 — 남아 있으면 캐시를 다시 쓴 것
    r = run(d / "build_ref.py", out, env=env)
    assert r.returncode == 0, r.stderr
    assert (out / "index.html").read_text(encoding="utf-8") == "cached", "같은 sha = 풀어 둔 나무를 다시 쓴다"
    (d / "build_canvas.py").write_text(STUB_MARK % "two", encoding="utf-8")
    git(root, "commit", "-q", "-am", "c2")
    r = run(d / "build_ref.py", out, env=env)
    assert r.returncode == 0, r.stderr
    assert (out / "index.html").read_text(encoding="utf-8") == "two", "ref 가 움직이면 새로 푼다"
    assert len([p for p in cache.iterdir() if p.is_dir()]) == 2
