"""hd parts --rebuild — 자물쇠 · 가짜 build argv(진짜 vite 없음) · post 단계 · 원자적 쓰기 · 미커밋 경고(dirty) · 실패하면 그대로. 임시 git 저장소 · 임시 HD_HOME. 브라우저 없음."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402,F401
from partsfix import HD_PY, git, hd, make_out, make_repo, parts_json  # noqa: E402,F401


def test_rebuild_builds_posts_records_and_then_check_is_fresh(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    tag = '<script src="../palette.js"></script>'
    out = make_out(tmp_path, repo, post=[{"inject_before_body": tag}])
    code, so, se = hd(home, "parts", "--rebuild", str(out), "--json")
    assert code == 0, se
    html = (out / "screens" / "mock-a.html").read_text(encoding="utf-8")
    assert html == "<html><body><p>one</p>" + tag + "</body></html>", html
    rec = parts_json(out)["parts"][0]
    assert rec["stamp"].startswith("g:") and rec["dirty"] is False and rec["built_at"], rec
    assert not (out / "parts.json.lock").exists() and not list(out.glob("parts.json.tmp*")), "자물쇠·임시 파일이 남지 않는다"
    assert not (out / ".hd-parts").exists() or not any((out / ".hd-parts").iterdir()), "빌드 임시 결과가 남지 않는다"
    code, so, se = hd(home, "parts", "--check", str(out), "--json")
    assert json.loads(so)["parts"][0]["state"] == "fresh"
    (repo / "ui" / "src" / "a.js").write_text("two\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "two")
    code, so, se = hd(home, "parts", "--check", str(out), "--json")
    assert json.loads(so)["parts"][0]["state"] == "stale", "지켜보는 경로가 커밋으로 바뀌면 낡음"


def test_rebuild_with_uncommitted_changes_warns_builds_and_records_dirty(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    out = make_out(tmp_path, repo)
    (repo / "ui" / "src" / "a.js").write_text("wip\n", encoding="utf-8")
    code, so, se = hd(home, "parts", "--rebuild", "mock-a", str(out))
    assert code == 0, se
    assert "미커밋 변경 포함" in se and se.count("[hd]") >= 1, se
    assert parts_json(out)["parts"][0]["dirty"] is True
    code, so, se = hd(home, "parts", str(out))
    assert "미커밋 변경 포함" in so, so


def test_failed_build_keeps_the_old_file_and_record(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    out = make_out(tmp_path, repo)
    before = (out / "parts.json").read_bytes()
    env = dict(hdfix.env(home), FAIL_BUILD="1")
    r = subprocess.run([sys.executable, str(HD_PY), "parts", "--rebuild", str(out)], capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    assert r.returncode == 1 and "boom: build failed" in r.stderr, r.stderr
    assert (out / "screens" / "mock-a.html").read_text(encoding="utf-8") == "<html><body>old</body></html>"
    assert (out / "parts.json").read_bytes() == before and not (out / "parts.json.lock").exists()


def test_rebuild_refuses_while_another_holds_the_lock(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    out = make_out(tmp_path, repo)
    (out / "parts.json.lock").write_text("4242", encoding="utf-8")
    code, so, se = hd(home, "parts", "--rebuild", str(out))
    assert code == 1 and "빌드 중" in se, se
    assert (out / "screens" / "mock-a.html").read_text(encoding="utf-8") == "<html><body>old</body></html>"
    assert (out / "parts.json.lock").read_text(encoding="utf-8") == "4242", "남의 자물쇠는 지우지 않는다"
