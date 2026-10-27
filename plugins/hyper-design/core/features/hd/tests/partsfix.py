"""hd parts 테스트 바탕 — 임시 git 저장소(가짜 build.py: ui/src/a.js 를 읽어 {out} 에 HTML) · parts.json 이 든 out · hd 자식 프로세스(임시 HD_HOME)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

HD_PY = hdfix.HD / "hd.py"
GIT = shutil.which("git")


def hd(home, *args):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=hdfix.env(home), timeout=120)
    return r.returncode, r.stdout, r.stderr


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def make_repo(tmp_path):
    if not GIT:
        pytest.skip("git 이 PATH 에 없음")
    repo = tmp_path / "app"
    (repo / "ui" / "src").mkdir(parents=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "ui" / "src" / "a.js").write_text("one\n", encoding="utf-8")
    (repo / "build.py").write_text(
        "import os, pathlib, sys\n"
        "src = pathlib.Path('ui/src/a.js').read_text(encoding='utf-8').strip()\n"
        "if os.environ.get('FAIL_BUILD'):\n"
        "    print('boom: build failed', file=sys.stderr); sys.exit(3)\n"
        "pathlib.Path(sys.argv[1]).write_text('<html><body><p>' + src + '</p></body></html>', encoding='utf-8')\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "one")
    return repo


def make_out(tmp_path, repo, stamp=None, post=None):
    out = tmp_path / "proj" / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "mock-a.html").write_text("<html><body>old</body></html>", encoding="utf-8")
    (out / "screens" / "tabs.html").write_text('<html><body><iframe src="mock-a.html"></iframe></body></html>', encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": [], "screens": [{"id": "tabs", "file": "screens/tabs.html"}]}), encoding="utf-8")
    part = {"file": "screens/mock-a.html", "repo": str(repo), "watch": ["ui/src"], "build": [sys.executable, "build.py", "{out}"],
            "stamp": stamp, "dirty": False, "built_at": None}
    if post:
        part["post"] = post
    (out / "parts.json").write_text(json.dumps({"version": 1, "parts": [part]}, indent=1), encoding="utf-8")
    return out


def parts_json(out):
    return json.loads((out / "parts.json").read_text(encoding="utf-8"))
