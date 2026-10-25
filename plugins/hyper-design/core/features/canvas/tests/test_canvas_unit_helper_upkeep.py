"""도우미 살림(wave 45) — #273 GET /api/state?since · 413 글 · POST/GET /api/archive · #278 다시 빌드 = build_ref(HEAD) ·
#281 .hd-history·.hd-queue 정리 · 로그 <out>/.hd-helper.log · #282 _inside = hd_projects.inside. 브라우저 없음.
서버·git 이 드는 것은 slow(unit 에서 빠짐)."""
import datetime, json, os, shutil, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

import pytest

CANVAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANVAS))
import helper  # noqa: E402
import hd_client  # noqa: E402  (helper 가 hd 폴더를 path 에 넣는다)


def tiny_out(root):
    out = root / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens.json").write_text(json.dumps({"screens": [{"id": "a", "file": "screens/a.html", "title": "A"}]}), encoding="utf-8")
    (out / "screens" / "a.html").write_text("<main><h1>A</h1></main>", encoding="utf-8")
    (out / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
    return out


def req(url, method="GET", body=None, token=None, raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode("utf-8"))
    r = urllib.request.Request(url, data=data, method=method, headers={"X-HD-Token": token} if token else {})
    try:
        with urllib.request.urlopen(r, timeout=10) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


@pytest.fixture()
def srv(tmp_path):
    s = helper.make_server(tiny_out(tmp_path), 0)
    import threading
    threading.Thread(target=s.serve_forever, daemon=True).start()
    s.base = s.url.split("/index.html")[0]
    s.out = tmp_path / "out"
    yield s
    s.shutdown(); s.server_close()


# ---------------------------------------------------------------- #273
@pytest.mark.slow
def test_state_since_answers_unchanged_without_body(srv):
    api = srv.base + "/api/state"
    assert req(api + "?since=0", token=srv.token) == (200, {"rev": 0, "unchanged": True})
    assert req(api, "PUT", {"rev": 0, "state": {"notes": [{"id": "n"}]}}, srv.token) == (200, {"rev": 1})
    assert req(api + "?since=0", token=srv.token) == (200, {"rev": 1, "state": {"notes": [{"id": "n"}]}}), "rev 가 다르면 전체"
    assert req(api + "?since=1", token=srv.token) == (200, {"rev": 1, "unchanged": True})
    assert req(api + "?since=x", token=srv.token)[0] == 400
    assert req(api + "?since=1")[0] == 403


@pytest.mark.slow
def test_state_413_says_size_and_fix(srv):
    big = json.dumps({"rev": 0, "state": {"notes": "x" * (2 * 1024 * 1024)}}).encode()
    code, res = req(srv.base + "/api/state", "PUT", token=srv.token, raw=big)
    assert code == 413 and "MB" in res["error"] and "완료 메모를 보관으로 옮기세요" in res["error"], res


@pytest.mark.slow
def test_archive_appends_lines_and_reads_newest_last(srv):
    api = srv.base + "/api/archive"
    assert req(api, token=srv.token) == (200, {"notes": []}), "파일이 없으면 빈 목록"
    assert req(api, "POST", {"notes": [{"id": "a", "note": "한글"}, {"id": "b"}]})[0] == 403
    assert req(api, "POST", {"notes": [{"id": "a", "note": "한글"}, {"id": "b"}]}, srv.token) == (200, {"ok": True, "count": 2})
    assert req(api, "POST", {"notes": [{"id": "c"}]}, srv.token) == (200, {"ok": True, "count": 1})
    f = srv.out / ".hd-notes-archive.jsonl"
    lines = f.read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["id"] for x in lines] == ["a", "b", "c"] and "한글" in lines[0]
    assert req(api, token=srv.token) == (200, {"notes": [{"id": "a", "note": "한글"}, {"id": "b"}, {"id": "c"}]})
    code, res = req(api, "POST", {"notes": [{"id": "d"}, 3]}, srv.token)
    assert code == 400 and res["error"] and len(f.read_text(encoding="utf-8").splitlines()) == 3, "틀린 본문은 아무것도 쓰지 않는다"
    assert not list(srv.out.glob(".hd-notes-archive.jsonl.tmp*")), "임시 파일이 남지 않는다"
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(srv.base + "/.hd-notes-archive.jsonl", timeout=5)


# ---------------------------------------------------------------- #281
def _stamp(dt):
    return dt.strftime("%Y%m%d-%H%M%S-%f")


def test_prune_history_and_queue_only_touches_old_stamps(tmp_path):
    out = tiny_out(tmp_path)
    now = datetime.datetime(2026, 10, 25, 12, 0, 0)
    hist, q = out / ".hd-history", out / ".hd-queue"
    q.mkdir()
    old = [_stamp(now - datetime.timedelta(days=60, minutes=i)) for i in range(205)]
    for s in old:
        (hist / s).mkdir(parents=True)
        (hist / s / "manifest.json").write_text("{}", encoding="utf-8")
    (hist / "fix-components.css").write_text("x", encoding="utf-8")          # fix 스킬이 두는 파일
    (hist / "t1").mkdir()
    o, y = _stamp(now - datetime.timedelta(days=8)), _stamp(now - datetime.timedelta(days=1))
    for s in (o, y):
        (q / (s + ".txt")).write_text("요청", encoding="utf-8"); (q / (s + ".sent")).write_text("", encoding="utf-8")
    (q / (_stamp(now - datetime.timedelta(days=30)) + ".txt")).write_text("표시 없음", encoding="utf-8")
    res = helper.prune(out, now)
    left = sorted(p.name for p in hist.iterdir())
    assert res["history"] == 5 and len([n for n in left if n[0] == "2"]) == 200, res
    assert sorted(old, reverse=True)[:200] == sorted([n for n in left if n[0] == "2"], reverse=True), "가장 새 200개가 남는다"
    assert "fix-components.css" in left and "t1" in left, "그 밖은 손대지 않는다"
    assert res["queue"] == 2 and not (q / (o + ".txt")).exists() and (q / (y + ".txt")).exists() and len(list(q.iterdir())) == 3


def test_prune_without_folders_is_quiet(tmp_path):
    assert helper.prune(tiny_out(tmp_path)) == {"history": 0, "queue": 0}


def test_forward_marks_queue_file_sent_only_when_paseo_took_it(tmp_path, monkeypatch):
    out = tiny_out(tmp_path)
    monkeypatch.setattr(helper.subprocess, "run", lambda args, **kw: subprocess.CompletedProcess(args, 0, "", ""))
    r = helper.forward(out, "메모", agent="a1", paseo="paseo.exe")
    assert r["via"] == "paseo" and Path(r["path"]).with_suffix(".sent").is_file()
    r = helper.forward(out, "메모")
    assert r["via"] == "queue" and not Path(r["path"]).with_suffix(".sent").exists()


def test_spawned_helper_logs_inside_out(tmp_path, monkeypatch):
    out = tiny_out(tmp_path)
    seen = {}

    class FakePopen:
        def __init__(self, args, **kw):
            seen["stdout"] = kw["stdout"].name

    monkeypatch.setattr(hd_client.subprocess, "Popen", FakePopen)
    _, log = hd_client.spawn_helper(out)
    assert Path(log) == out / ".hd-helper.log" and Path(seen["stdout"]) == out / ".hd-helper.log", "로그는 out 안(점 파일이라 내주지 않음)"


# ---------------------------------------------------------------- #282
def test_inside_uses_one_out_key(tmp_path):
    out = tiny_out(tmp_path).resolve()
    assert helper._inside(out, out / "screens" / "a.html")
    assert helper._inside(out, Path(str(out / "screens" / "a.html").replace("\\", "/")))
    assert not helper._inside(out, out.parent / (out.name + "2") / "a.html"), "이름이 앞부분만 같은 옆 폴더"
    assert not helper._inside(out, out / ".." / "x.html")
    if sys.platform == "win32":
        assert helper._inside(out, Path(str(out).upper()) / "screens" / "a.html"), "드라이브 경로는 대소문자 무시"


# ---------------------------------------------------------------- #278
STUB_OK = "import sys, pathlib\npathlib.Path(sys.argv[1], 'index.html').write_text('HEAD', encoding='utf-8')\n"
STUB_BAD = "import sys, pathlib\npathlib.Path(sys.argv[1], 'index.html').write_text('WORKTREE', encoding='utf-8')\n"


def test_cli_helper_rebuilds_with_build_ref(monkeypatch):
    monkeypatch.setattr(helper, "BUILDER", helper.BUILD)
    helper.use_ref_build()
    assert helper.BUILDER == helper.BUILD_REF and helper.BUILD_REF.name == "build_ref.py"


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("git"), reason="git 없음")
def test_rebuild_uses_committed_code_not_half_edited_tree(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    d = root / "plugins" / "hyper-design" / "core" / "features" / "canvas"
    d.mkdir(parents=True)
    shutil.copyfile(helper.BUILD_REF, d / "build_ref.py")
    shutil.copyfile(helper.BUILD_REF.parent / "code_stamp.py", d / "code_stamp.py")
    shutil.copyfile(helper.BUILD_REF.parent / "code_probe.py", d / "code_probe.py")
    (d / "build_canvas.py").write_text(STUB_OK, encoding="utf-8")
    g = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    for args in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "c"]):
        subprocess.run(g + args, check=True, capture_output=True)
    (d / "build_canvas.py").write_text(STUB_BAD, encoding="utf-8")       # 다른 세션이 고치는 중(미커밋)
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(helper, "BUILDER", d / "build_ref.py")
    r = helper._build(out)
    assert r.returncode == 0, r.stderr
    assert (out / "index.html").read_text(encoding="utf-8") == "HEAD", "작업 트리가 아니라 커밋된 코드로"
    plain = tmp_path / "plain" / "canvas"
    plain.mkdir(parents=True)
    shutil.copyfile(helper.BUILD_REF, plain / "build_ref.py")
    shutil.copyfile(helper.BUILD_REF.parent / "code_stamp.py", plain / "code_stamp.py")
    shutil.copyfile(helper.BUILD_REF.parent / "code_probe.py", plain / "code_probe.py")
    (plain / "build_canvas.py").write_text(STUB_BAD, encoding="utf-8")
    monkeypatch.setattr(helper, "BUILDER", plain / "build_ref.py")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert helper._build(out).returncode == 0 and (out / "index.html").read_text(encoding="utf-8") == "WORKTREE", "git 저장소가 아니면 지금처럼"
