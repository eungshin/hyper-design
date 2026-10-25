"""47-5a — 세션이 스스로 하는 일: 완료 메모 보관(서버 시계, 한 시간마다 — 전에는 캔버스 탭의 이벤트·focus 때만) · 시계(Ticker) ·
뒤 빌드가 깨져 되돌린 쓰기의 기록 = 묘비(reverted.json) → 그 stamp 되살리기는 200 reverted(전: 404 '되돌릴 기록이 없어요')."""
import datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "hd" / "tests"))
import hdfix  # noqa: E402
import memo_archive as MA  # noqa: E402
import write_record  # noqa: E402
import session as S  # noqa: E402

DAY = 86_400_000
NOW = 1_800_000_000_000                                # ms


def iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat(timespec="seconds")


def done(i, at_ms, **k):
    return dict({"id": "d%d" % i, "screen": "home", "sent": True, "replies": [{"kind": "반영됨", "at": iso(at_ms)}]}, **k)


# ---------------------------------------------------------------- 고르기(순수 — modules/archive.js 와 같은 규칙)
def test_pick_old_done_notes_only():
    notes = [done(1, NOW - 31 * DAY), done(2, NOW - 29 * DAY),
             {"id": "w", "sent": True, "replies": []},                                   # AI 작업 중
             {"id": "q", "sent": True, "replies": [{"kind": "질문", "at": iso(NOW - 99 * DAY)}]},   # 결정 필요
             {"id": "p", "sent": True, "replies": [{"kind": "일부", "at": iso(NOW - 99 * DAY)}]},   # 일부
             {"id": "x", "sent": False, "replies": [{"kind": "반영됨", "at": iso(NOW - 99 * DAY)}]},  # 다시 열어 보내기 전
             {"sent": True, "replies": [{"kind": "반영됨", "at": iso(NOW - 99 * DAY)}]},            # id 없음 — 뺄 수 없다
             {"id": "h", "replies": [{"kind": "확인", "at": iso(NOW - 40 * DAY)}]}]                 # 사람이 닫음 = 완료
    assert [n.get("id") for n in MA.pick(notes, NOW)] == ["d1", "h"]


def test_pick_over_200_done_takes_the_oldest_and_unknown_time_first():
    notes = [done(i, NOW - i * 1000) for i in range(MA.KEEP_DONE + 2)] + [dict(done(999, NOW), replies=[{"kind": "반영됨"}])]
    got = [n["id"] for n in MA.pick(notes, NOW)]
    assert sorted(got) == sorted(["d%d" % (MA.KEEP_DONE + 1), "d%d" % MA.KEEP_DONE, "d999"]), got


def test_without_keeps_notes_changed_since():
    a, b = done(1, NOW), done(2, NOW)
    assert MA.without([a, b], [a]) == [b]
    assert MA.without([dict(a, sent=False), b], [a]) == [dict(a, sent=False), b], "그 사이 다시 연 메모는 남긴다"


# ---------------------------------------------------------------- 세션: 보관 한 번 · 시계
def test_session_archive_sweep_moves_old_done_notes_once(tmp_path):
    notes = [done(1, NOW - 40 * DAY), {"id": "w", "sent": True, "screen": "home"}]
    out = hdfix.make_out(tmp_path / "w", notes=notes)
    sess = S.ProjectSession(out, build=lambda o: subprocess.CompletedProcess([], 0, "", ""))
    assert sess.archive.sweep(NOW) == 1
    st = json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))
    assert st["rev"] == 4 and [n["id"] for n in st["state"]["notes"]] == ["w"]
    assert [n["id"] for n in sess.archive.get()["notes"]] == ["d1"]
    assert sess.archive.sweep(NOW) == 0, "고를 것이 없으면 쓰지 않는다"
    assert json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["rev"] == 4


def test_session_archive_sweep_publishes_notes_changed(tmp_path):
    out = hdfix.make_out(tmp_path / "w", notes=[done(1, NOW - 40 * DAY)])
    sess = S.ProjectSession(out, build=lambda o: subprocess.CompletedProcess([], 0, "", ""))
    sub = sess.events.subscribe(None)[0]
    sess.archive.sweep(NOW)
    ev = sub.get(0)
    assert ev["type"] == "notes.changed" and ev["rev"] == 4


def test_ticker_runs_each_task_when_due_and_survives_a_failing_task(capsys):
    seen = []
    t = S.Ticker([(1.0, lambda: seen.append("a")), (10.0, lambda: seen.append("b")), (1.0, lambda: 1 / 0)])
    t.step(100.0)
    assert seen == ["a", "b"], "처음 차례에 모두 한 번"
    t.step(100.5)
    assert seen == ["a", "b"]
    t.step(101.0)
    assert seen == ["a", "b", "a"]
    t.step(110.0)
    assert seen == ["a", "b", "a", "a", "b"]
    assert "[hd]" in capsys.readouterr().err, "실패한 일은 [hd] 한 줄(다른 일은 계속)"


def test_session_ticker_sweeps_presence_every_second_and_archives_hourly(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    sess = S.ProjectSession(out, build=lambda o: subprocess.CompletedProcess([], 0, "", ""))
    every = sorted(e for e, _ in sess.ticker.tasks)
    assert every == sorted([S.PRESENCE_EVERY, S.TRP.EVERY, S.ARCHIVE_EVERY]) and S.PRESENCE_EVERY == 1.0 and S.ARCHIVE_EVERY == 3600.0
    assert S.TRP.EVERY == 1.0, "터미널 대화 펌프도 1초마다(S3b)"


# ---------------------------------------------------------------- 되돌린 쓰기의 기록 = 묘비
def test_reverted_async_write_leaves_a_tombstone_and_its_undo_is_a_no_op(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    ok = lambda o: subprocess.CompletedProcess([], 0, "", "")
    sess = S.ProjectSession(out, build=ok)
    code, res = sess.history.apply_async([{"id": "e1", "screen": "home", "edit": "text", "path": "h1", "value": "Broken"}])
    stamp = res["stamp"]
    reverted, kept = sess.history.revert_writes([{"stamp": stamp, "ids": ["e1"], "screens": ["home"]}])
    assert reverted == ["e1"] and kept == []
    assert "<h1>home</h1>" in (out / "screens" / "home.html").read_text(encoding="utf-8")
    hist = out / ".hd-history" / stamp
    assert sorted(p.name for p in hist.iterdir()) == ["reverted.json"], "원본·manifest 는 지우고 묘비만"
    assert json.loads((hist / "reverted.json").read_text(encoding="utf-8"))["ids"] == ["e1"]
    code, r = sess.history.restore(stamp)
    assert code == 200 and r["reverted"] is True and r["restored"] == [] and r["changed"] == [] and "error" not in r
    assert write_record.restore(out, "20000101-000000-000000")["reason"] == "missing", "없는 기록은 그대로 404"
