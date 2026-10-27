"""실행 도구(hd_testrun.py): 겹친 -n 실행의 잠금 판단 · 깨진 것 혼자 다시 나누기 — 브라우저 없이."""
import io, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hd_testrun as t  # noqa: E402

ME = 4242


def test_free_lock_is_taken():
    assert t.decide(False, None, False, 0, ME) == "take"


def test_live_owner_means_wait():
    assert t.decide(True, {"pid": 1}, True, 10, ME) == "wait"


def test_dead_owner_is_cleared():
    assert t.decide(True, {"pid": 1}, False, 10, ME) == "clear"


def test_hand_made_lock_waits_until_stale():
    assert t.decide(True, None, False, 60, ME) == "wait"                 # 손으로 mkdir 한 세션이 아직 돌 수 있다
    assert t.decide(True, None, False, t.STALE_SEC + 1, ME) == "clear"


def test_own_lock_is_mine():
    assert t.decide(True, {"pid": ME}, True, 10, ME) == "mine"


def test_wait_line_names_the_other_run():
    line = t.wait_line({"cwd": "C:/wt/a", "start": "2026-10-27T10:00:00"}, 5)
    assert line == "[hd-test] 다른 실행 중: C:/wt/a 2026-10-27T10:00:00 — 기다림"


def test_classify_splits_real_and_flaky():
    real, flaky = t.classify(["a", "b", "c", "a"], ["b"], True)
    assert real == ["b"] and flaky == ["a", "c"]
    assert t.summary_line(real, flaky) == "진짜 실패 1 · 혼자 통과(부하로 보임) 2"


def test_classify_without_rerun_keeps_all_real():
    assert t.classify(["a", "b"], [], False) == (["a", "b"], [])


def test_acquire_waits_then_takes_after_owner_dies(tmp_path, monkeypatch):
    lock = tmp_path / "hd-testrun.lock"
    lock.mkdir()
    (lock / "owner.json").write_text(json.dumps({"pid": 999999, "cwd": "X", "start": "S"}), encoding="utf-8")
    alive = {"v": True}
    monkeypatch.setattr(t, "pid_alive", lambda pid: alive["v"])
    out, naps = io.StringIO(), []

    def nap(_):
        naps.append(1)
        if len(naps) == 2:
            alive["v"] = False                          # 다른 실행이 죽었다
    me = t.acquire(["-n", "4"], lock=lock, out=out, sleep=nap)
    assert out.getvalue().count("기다림") == 1          # 한 줄만
    assert len(naps) == 2
    assert json.loads((lock / "owner.json").read_text(encoding="utf-8"))["pid"] == os.getpid() == me["pid"]
    t.release(lock)
    assert not lock.exists()


def test_release_leaves_someone_elses_lock(tmp_path):
    lock = tmp_path / "hd-testrun.lock"
    lock.mkdir()
    (lock / "owner.json").write_text(json.dumps({"pid": 1}), encoding="utf-8")
    t.release(lock)
    assert lock.exists()


def test_this_process_is_alive_and_bogus_pid_is_not():
    assert t.pid_alive(os.getpid())
    assert not t.pid_alive(0)


def test_stale_refs_finds_removed_selectors(tmp_path):
    import stale_refs as s
    diff = "\n".join(["+++ b/modules/view-x.js", "-  el.classList.add('oldpill'); q('#gonebox'); el.dataset.polKey = 1",
                      "+  el.classList.add('newpill')", "+++ b/canvas.css", "-.oldbar { color: #fff }"])
    gone = s.removed_tokens(diff)
    assert {(".", "oldpill"), ("#", "gonebox"), ("data-", "pol-key"), (".", "oldbar")} <= gone
    assert ("#", "fff") not in gone
    assert not s.still_used((".", "oldpill"), "el.classList.add('newpill')")
    f = tmp_path / "test_x.py"
    f.write_text("page.locator('.oldpill')\npage.locator('.oldpillar')\n", encoding="utf-8")
    assert [h[1] for h in s.test_hits((".", "oldpill"), [f])] == [1]


def test_wait_line_shows_note_of_hand_made_lock():
    assert t.wait_line(None, 125, "r34-stalehub Tue Oct 27") == "[hd-test] 다른 실행 중: (r34-stalehub Tue Oct 27, 손으로 잡은 잠금, 2분 전) — 기다림"
