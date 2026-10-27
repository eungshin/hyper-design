"""parts_file.py(Edge) + code_probe.tree_shas · dirty — 임시 git 저장소로 앱 부품 도장 재기 · 낡음 · 미커밋 · 캐시 · 화면 고르기. 브라우저 없음(git 이 들어 slow)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import code_probe as CP  # noqa: E402
import part_stamp as PS  # noqa: E402
import parts_file as PF  # noqa: E402

pytestmark = pytest.mark.slow
GIT = shutil.which("git")


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
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "one")
    return repo


def make_out(tmp_path, repo, stamp):
    out = tmp_path / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "mock-a.html").write_text("<html><body>a</body></html>", encoding="utf-8")
    (out / "screens" / "tabs.html").write_text('<html><body><iframe src="mock-a.html"></iframe></body></html>', encoding="utf-8")
    (out / "screens" / "home.html").write_text("<html><body>home</body></html>", encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": [], "screens": [
        {"id": "tabs", "file": "screens/tabs.html"}, {"id": "home", "file": "screens/home.html"}]}), encoding="utf-8")
    (out / "parts.json").write_text(json.dumps({"version": 1, "parts": [
        {"file": "screens/mock-a.html", "repo": str(repo), "watch": ["ui/src"], "build": ["node", "b.mjs", "{out}"],
         "stamp": stamp, "dirty": False, "built_at": "2026-10-27T10:00:00"}]}), encoding="utf-8")
    return out


def test_tree_shas_follow_committed_tree_not_head(tmp_path):
    repo = make_repo(tmp_path)
    first = PS.tree_of(CP.tree_shas(repo, ["ui/src"]))
    assert first and first.startswith("g:")
    (repo / "README.md").write_text("y\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "unrelated")
    assert PS.tree_of(CP.tree_shas(repo, ["ui/src"])) == first, "지켜보지 않는 경로의 커밋은 도장을 바꾸지 않는다"
    (repo / "ui" / "src" / "a.js").write_text("two\n", encoding="utf-8")
    assert PS.tree_of(CP.tree_shas(repo, ["ui/src"])) == first and CP.dirty(repo, ["ui/src"]) is True, "커밋 전 변경은 도장에 들지 않고 dirty 로만"
    git(repo, "commit", "-q", "-am", "two")
    assert PS.tree_of(CP.tree_shas(repo, ["ui/src"])) != first and CP.dirty(repo, ["ui/src"]) is False
    assert CP.tree_shas(repo, ["nope"]) is None and CP.tree_shas(tmp_path / "missing", ["ui/src"]) is None, "못 잼 = None"
    assert CP.dirty(tmp_path / "missing", ["ui/src"]) is None


def test_check_reports_fresh_then_stale_and_maps_screens(tmp_path):
    repo = make_repo(tmp_path)
    out = make_out(tmp_path, repo, PS.tree_of(CP.tree_shas(repo, ["ui/src"])))
    rows = PF.check(out)
    assert [(r["file"], r["state"], r["dirty_now"]) for r in rows] == [("screens/mock-a.html", "fresh", False)]
    t = [0.0]
    w = PF.PartsWatch(out, clock=lambda: t[0])
    assert w.status()["stale"] == []
    (repo / "ui" / "src" / "a.js").write_text("two\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "two")
    t[0] = 59.0
    assert w.status()["stale"] == [], "60초 안에는 지난 답(git 을 다시 부르지 않음)"
    t[0] = 61.0
    st = w.status()
    assert st["stale"] == ["tabs"] and st["parts"][0]["state"] == "stale", "낡은 부품을 iframe 으로 끌어 쓰는 화면만"


def test_read_skips_bad_entries_and_broken_file_with_one_line(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    assert PF.read(out) == [] and capsys.readouterr().err == "", "parts.json 이 없으면 조용히"
    (out / "parts.json").write_text("{broken", encoding="utf-8")
    assert PF.read(out) == [] and capsys.readouterr().err.count("[hd]") == 1
    (out / "parts.json").write_text(json.dumps({"version": 1, "parts": [{"file": "x.html"}]}), encoding="utf-8")
    assert PF.read(out) == [] and capsys.readouterr().err.count("[hd] parts.json 1번째") == 1


def test_unmeasurable_repo_is_unknown_not_stale(tmp_path):
    out = make_out(tmp_path, tmp_path / "not-a-repo", "g:" + "a" * 16)
    (tmp_path / "not-a-repo").mkdir()
    rows = PF.check(out)
    assert rows[0]["state"] == "unknown" and rows[0]["stale"] is False
    assert PF.PartsWatch(out).status()["stale"] == []
