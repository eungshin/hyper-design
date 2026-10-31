"""공용 셸 저장소(보드 전환 1단계 P1a) — shell_store.py 규칙(순수) · ShellStore(임시 폴더, 빌드는 가짜) · Prebuilder · 허브 registry 의 미리 만들기 ·
cache_policy 의 공용 셸 주소. git·하위 프로세스·서버 없음(진짜 --shell 빌드와 허브 라우트는 test_canvas_shell_route.py)."""
import sys, threading, time
from pathlib import Path

import pytest

CANVAS = Path(__file__).resolve().parents[1]
FEATURES = CANVAS.parent
sys.path[:0] = [str(CANVAS), str(FEATURES / "hd"), str(FEATURES / "home")]
import build_ref as BR  # noqa: E402
import cache_policy as CP  # noqa: E402
import code_stamp as CS  # noqa: E402
import hd_client as C  # noqa: E402
import registry as RG  # noqa: E402
import shell_store as SS  # noqa: E402

HEX = "0123456789abcdef"
STAMP = "g:" + HEX
SHA = HEX + "0" * 24


# ---------------------------------------------------------------- 규칙(순수)
def test_stamp_hex_takes_git_stamps_only():
    assert SS.stamp_hex(STAMP) == HEX
    for bad in (None, "", "w:" + HEX, "g:" + HEX.upper(), "g:" + HEX[:15], "g:" + HEX + "0", "g:../" + HEX, 5):
        assert SS.stamp_hex(bad) is None, bad


def test_route_parses_shell_address_and_refuses_escapes():
    assert SS.route("/v1/shell/%s/hd-shell.js" % STAMP) == (STAMP, "hd-shell.js")
    assert SS.route("/v1/shell/g%%3A%s/hd-shell.css" % HEX) == (STAMP, "hd-shell.css"), "주소 인코딩된 ':' 도"
    for bad in ("/v1/shell/%s/skeleton.html" % STAMP, "/v1/shell/%s/.hd-ok" % STAMP, "/v1/shell/%s/../x/hd-shell.js" % STAMP,
                "/v1/shell/..%%2F%s/hd-shell.js" % STAMP, "/v1/shell/%s/hd-shell.js/x" % STAMP, "/v1/shell/w:%s/hd-shell.js" % HEX,
                "/v1/shell/%s" % STAMP, "/v1/p/x/hd-shell.js", "/v1/shell/%s/..%%2Fhd-shell.js" % STAMP, None):
        assert SS.route(bad) is None, bad


def test_url_is_the_shared_hub_address():
    assert SS.url(STAMP, "hd-shell.js") == "/v1/shell/%s/hd-shell.js" % STAMP
    assert SS.route(SS.url(STAMP, "hd-shell.css")) == (STAMP, "hd-shell.css")


def test_pick_tree_and_mode():
    other = "f" * 40
    assert SS.pick_tree([other, SHA, "shell", SHA + ".tmp-3"], HEX) == SHA
    assert SS.pick_tree([other], HEX) is None
    assert SS.has_mode('if sys.argv[1] == "--shell":') and not SS.has_mode("def main(): ...")


def test_shell_address_is_immutable_and_misses_are_not_stored():
    p = SS.url(STAMP, "hd-shell.js")
    assert CP.header(p) == CP.IMMUTABLE and CP.header(SS.url(STAMP, "hd-shell.css"), 304) == CP.IMMUTABLE
    assert CP.header(p, 404) == CP.NO_STORE, "아직 없는 도장 404 가 1년 남지 않게"
    assert CP.header("/v1/sessions") == CP.NO_STORE and CP.header("/v1/p/a/") == CP.NO_STORE, "다른 /v1/ 은 그대로"


# ---------------------------------------------------------------- ShellStore(임시 폴더 · 가짜 빌드)
SKEL = CS.stamp_page("<!doctype html><html><head><!-- hd-shell-css --></head><body>"
                     '<noscript id="hd-links"></noscript><script id="hd-data" type="application/json">{}</script><!-- hd-modules --></body></html>', STAMP)


def tree(root, sha=SHA, mode=True):
    """build_ref 캐시 나무 흉내 — <root>/<sha>/features/canvas/build_canvas.py + .hd-ok."""
    d = root / sha / "features" / "canvas"
    d.mkdir(parents=True)
    (d / "build_canvas.py").write_text('MODE = "--shell"\n' if mode else "def main(): pass\n", encoding="utf-8")
    (root / sha / BR.OK).write_text(sha, encoding="utf-8")
    return d / "build_canvas.py"


class FakeRun:
    def __init__(self, skel=SKEL, code=0, delay=0.0):
        self.calls, self.skel, self.code, self.delay = [], skel, code, delay

    def __call__(self, script, dest, stamp):
        self.calls.append((Path(script), Path(dest), stamp))
        time.sleep(self.delay)
        if self.code == 0:
            (dest / "hd-shell.js").write_text("/* js */", encoding="utf-8")
            (dest / "hd-shell.css").write_text("/* css */", encoding="utf-8")
            (dest / "skeleton.html").write_text(self.skel, encoding="utf-8")
        return self.code, "끝"


def store(tmp_path, run, head=None):
    return SS.ShellStore(root=tmp_path / "trees" / "shell", trees=tmp_path / "trees", run=run, head=head or (lambda: None))


def test_get_is_none_until_made_then_shape(tmp_path):
    script = tree(tmp_path / "trees")
    run = FakeRun()
    s = store(tmp_path, run)
    assert s.get(STAMP) is None, "get 은 만들지 않는다"
    assert not run.calls
    hit = s.ensure(STAMP)
    assert hit == s.get(STAMP) and set(hit) == {"dir", "js", "css", "skeleton"}
    assert hit["dir"] == tmp_path / "trees" / "shell" / SHA and (hit["dir"] / BR.OK).is_file()
    assert hit["js"] == "/v1/shell/%s/hd-shell.js" % STAMP and hit["css"] == "/v1/shell/%s/hd-shell.css" % STAMP
    assert hit["skeleton"] == SKEL
    assert run.calls[0][0] == script and run.calls[0][2] == STAMP, "그 도장의 코드 사본으로, 도장을 넘겨"
    assert run.calls[0][1].name == "%s.tmp-%d" % (SHA, __import__("os").getpid()), "임시 이름에 만들고 이름 바꾸기"
    assert s.file(STAMP, "hd-shell.js").read_text(encoding="utf-8") == "/* js */"
    assert s.file(STAMP, "skeleton.html") is None and s.file("g:" + "f" * 16, "hd-shell.js") is None
    assert SS.ShellStore(root=tmp_path / "trees" / "shell").get(STAMP)["skeleton"] == SKEL, "다른 프로세스(새 저장소)도 같은 폴더를 쓴다"


def test_same_stamp_twice_builds_once(tmp_path):
    tree(tmp_path / "trees")
    run = FakeRun()
    s = store(tmp_path, run)
    assert s.ensure(STAMP) and s.ensure(STAMP)
    assert len(run.calls) == 1


def test_two_concurrent_requests_build_once_and_both_get_it(tmp_path):
    tree(tmp_path / "trees")
    run = FakeRun(delay=0.2)
    s = store(tmp_path, run)
    got = []
    ts = [threading.Thread(target=lambda: got.append(s.ensure(STAMP))) for _ in range(2)]
    [t.start() for t in ts]
    [t.join(10) for t in ts]
    assert len(run.calls) == 1, "같은 도장 동시 두 요청 = 한 번만 만듦"
    assert len(got) == 2 and all(g and g["skeleton"] == SKEL for g in got)


def test_loser_of_a_rename_race_uses_the_winner(tmp_path):
    """다른 프로세스가 먼저 다 만든 폴더가 있으면(이름 바꾸기 실패) 제 임시 폴더를 지우고 그것을 쓴다."""
    tree(tmp_path / "trees")
    root = tmp_path / "trees" / "shell"

    def run(script, dest, stamp):
        FakeRun()(script, dest, stamp)
        win = root / SHA                                  # 그 사이 다른 프로세스가 끝냄
        win.mkdir(parents=True)
        for n in ("hd-shell.js", "hd-shell.css", "skeleton.html"):
            (win / n).write_text((dest / n).read_text(encoding="utf-8"), encoding="utf-8")
        (win / BR.OK).write_text(stamp, encoding="utf-8")
        return 0, ""
    s = store(tmp_path, run)
    assert s.ensure(STAMP)["dir"] == root / SHA
    assert [p.name for p in root.iterdir()] == [SHA], "늦은 쪽 임시 폴더는 지움"


def test_snapshot_without_shell_mode_is_none_and_not_retried(tmp_path, capsys):
    tree(tmp_path / "trees", mode=False)
    run = FakeRun()
    s = store(tmp_path, run)
    assert s.ensure(STAMP) is None and s.ensure(STAMP) is None
    assert not run.calls, "옛 사본(--shell 전 커밋) = 만들지 않음 → 부르는 쪽은 예전 길"
    assert capsys.readouterr().err.count("[hd]") == 1


@pytest.mark.parametrize("run", [FakeRun(code=2), FakeRun(skel=CS.stamp_page("<html><head></head></html>", "g:" + "f" * 16))],
                         ids=["build_fails", "stamp_differs"])
def test_failed_build_is_none_one_line_and_no_folder(tmp_path, capsys, run):
    tree(tmp_path / "trees")
    s = store(tmp_path, run)
    assert s.ensure(STAMP) is None and s.get(STAMP) is None
    assert "[hd] 공용 셸" in capsys.readouterr().err
    assert not [p for p in (tmp_path / "trees" / "shell").iterdir()], "만들다 만 폴더를 남기지 않음"


def test_missing_tree_uses_head_only_when_it_is_that_stamp(tmp_path):
    trees = tmp_path / "trees"
    trees.mkdir()
    script = tree(tmp_path / "elsewhere")
    run = FakeRun()
    assert store(tmp_path, run, head=lambda: ("f" * 40, script)).ensure(STAMP) is None, "HEAD 가 다른 도장 = 쓰지 않음"
    assert not run.calls
    assert store(tmp_path, run, head=lambda: (SHA, script)).ensure(STAMP)["skeleton"] == SKEL
    assert run.calls[0][0] == script


def test_w_stamps_are_not_built(tmp_path):
    run = FakeRun()
    s = store(tmp_path, run)
    assert s.ensure("w:" + HEX) is None and s.get("w:" + HEX) is None and not run.calls


def test_old_shell_folders_are_pruned_by_the_build_ref_rule(tmp_path):
    import os
    root = tmp_path / "trees" / "shell"
    old = []
    for i, c in enumerate("abcd"):                       # 오래된 다 만든 폴더 넷(GRACE 보다 오래)
        d = root / (c * 40)
        d.mkdir(parents=True)
        (d / BR.OK).write_text("x", encoding="utf-8")
        t = time.time() - 10_000 + i
        os.utime(d / BR.OK, (t, t))
        old.append(d)
    tree(tmp_path / "trees")
    store(tmp_path, FakeRun()).ensure(STAMP)
    left = sorted(p.name for p in root.iterdir())
    assert left == sorted([SHA] + [c * 40 for c in "bcd"]), "새 도장 + 최근 KEEP(3) — 가장 오래된 것만 지움"


# ---------------------------------------------------------------- 미리 만들기
class FakeStore:
    def __init__(self):
        self.calls = []

    def ensure(self, stamp):
        self.calls.append(stamp)


def test_prebuilder_runs_each_new_stamp_once_in_one_thread():
    fs = FakeStore()
    pb = SS.Prebuilder(fs)
    assert pb.want(STAMP) is True
    assert pb.want(STAMP) is False, "같은 도장 두 번 안 함"
    assert pb.want("w:" + HEX) is False and pb.want(None) is False
    assert pb.want("g:" + "f" * 16) is True
    assert pb.wait(5)
    assert fs.calls == [STAMP, "g:" + "f" * 16]


def test_prebuilder_survives_a_failing_store(capsys):
    class Bad:
        def ensure(self, stamp):
            raise RuntimeError("터짐")
    pb = SS.Prebuilder(Bad())
    pb.want(STAMP)
    assert pb.wait(5)
    assert "[hd] 공용 셸 미리 만들기" in capsys.readouterr().err


class FakePrebuild:
    def __init__(self):
        self.wanted = []

    def want(self, stamp):
        self.wanted.append(stamp)


def test_registry_prebuilds_when_it_measures_a_new_stamp(monkeypatch):
    """허브가 지금 도장을 잴 때(current_code — 열기·페이지 2초 · 칩 30초) 그 도장의 셸을 미리 만든다. 기억한 도장(재지 않음)은 다시 부르지 않는다."""
    now = [STAMP]
    monkeypatch.setattr(C.CP, "current", lambda ref="HEAD": now[0])
    pb = FakePrebuild()
    reg = RG.ProjectRegistry(lambda: 0, lambda: "", prebuild=pb)
    assert pb.wanted == [STAMP], "뜰 때 잰 도장"
    clock = [100.0]
    reg.clock = lambda: clock[0]
    reg.current_code()
    clock[0] = 101.0
    reg.current_code()
    assert pb.wanted == [STAMP, STAMP], "기억 안 = 재지 않음 = 다시 부르지 않음"
    now[0] = "g:" + "f" * 16                             # 커밋 — 새 도장
    clock[0] = 140.0
    assert reg.stale_info() is not None
    assert pb.wanted[-1] == "g:" + "f" * 16, "새 도장을 알아채면 그 도장으로"


def test_registry_alone_does_not_prebuild(monkeypatch):
    """허브(make_hub)가 넘길 때만 — registry 를 바로 만드는 unit 테스트는 뒤 git·빌드를 띄우지 않는다."""
    monkeypatch.setattr(C.CP, "current", lambda ref="HEAD": STAMP)
    assert RG.ProjectRegistry(lambda: 0, lambda: "").prebuild is None
