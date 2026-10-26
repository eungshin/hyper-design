"""figma-lite 5 — 쓰기는 데이터만 확인(builder.verify), index.html 은 페이지를 줄 때 데이터 도장이 다르면 다시 빌드(session.refresh_data).
도장 모양(code_stamp — 순수) · 입력 도장(board_data.input_stamp) · 쓰기 확인이 깨지면 되돌림 · 페이지 다시 빌드 규칙. 하위 프로세스 없음(가짜 페이지 빌드)."""
import json, pathlib, subprocess, sys, threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "hd" / "tests"))
import board_data as BD  # noqa: E402
import builder as BLD  # noqa: E402
import code_stamp as CS  # noqa: E402
import hdfix  # noqa: E402
import session as S  # noqa: E402

D1, D2 = "d:aaaaaaaaaaaaaaaa", "d:bbbbbbbbbbbbbbbb"
PAGE = "<!doctype html><html><head><meta charset=utf-8></head><body>%s</body></html>"


# ---------------------------------------------------------------- 도장 모양(순수)
def test_data_stamp_round_trip_and_rule():
    a = CS.data_stamp([("screens.json", b"{}"), ("screens/a.html", b"1")])
    assert a.startswith("d:") and len(a) == 18 and a == CS.data_stamp([("screens/a.html", b"1"), ("screens.json", b"{}")])
    once = CS.stamp_inputs(CS.stamp_page(PAGE % "", "g:cccccccccccccccc"), D1)
    assert CS.page_inputs(once) == D1 and CS.page_stamp(once) == "g:cccccccccccccccc", "코드 도장과 함께 <head> 바로 뒤"
    twice = CS.stamp_inputs(once, D2)
    assert CS.page_inputs(twice) == D2 and twice.count("hd-inputs") == 1
    assert CS.page_inputs(PAGE % "") is None and CS.page_inputs(None) is None and CS.stamp_inputs("x", None) == "x"
    assert CS.data_stale(D1, D2) and not CS.data_stale(D1, D1)
    assert not CS.data_stale(None, D2) and not CS.data_stale(D1, None), "도장 없는 페이지(옛 빌드 · 가짜)는 견주지 않는다"


# ---------------------------------------------------------------- 입력 도장(out 파일 읽기)
def test_input_stamp_follows_data_files_only(tmp_path):
    out = hdfix.make_out(tmp_path)
    a = BD.input_stamp(out)
    (out / ".hd-canvas.json").write_text("{}", encoding="utf-8")
    (out / "index.html").write_text("다른 페이지", encoding="utf-8")
    assert BD.input_stamp(out) == a, "상태 파일 · index.html 은 데이터 입력이 아니다"
    f = out / "screens" / "home.html"
    f.write_text(f.read_text(encoding="utf-8").replace("home", "HOME"), encoding="utf-8")
    b = BD.input_stamp(out)
    assert b != a, "화면 파일이 바뀌면"
    m = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    m["screens"][0]["title"] = "새 이름"
    (out / "screens.json").write_text(json.dumps(m), encoding="utf-8")
    assert BD.input_stamp(out) != b, "screens.json 이 바뀌면"
    (out / "screens.json").write_text("{깨짐", encoding="utf-8")
    assert BD.input_stamp(out).startswith("d:"), "깨진 screens.json 도 바이트로(멈추지 않음)"


# ---------------------------------------------------------------- 쓰기 확인 = 데이터만, 깨지면 되돌림
def test_verify_fails_when_the_canvas_data_breaks(tmp_path):
    out = hdfix.make_out(tmp_path)
    assert BLD.verify(out).returncode == 0
    (out / "screens.json").write_text(json.dumps({"screens": [{"title": "id 없음"}]}), encoding="utf-8")
    r = BLD.verify(out)
    assert r.returncode == 1 and "KeyError" in r.stderr, r.stderr


def _counting_build(calls):
    def build(o):                                    # 가짜 페이지 빌드 — 지금 입력의 데이터 도장을 품은 페이지를 쓴다
        calls.append(1)
        (o / "index.html").write_text(CS.stamp_inputs(PAGE % len(calls), BD.input_stamp(o)), encoding="utf-8")
        return subprocess.CompletedProcess([], 0, "", "")
    return build


def test_sync_write_checks_data_not_the_page_and_reverts_when_broken(tmp_path):
    out = hdfix.make_out(tmp_path)
    calls = []
    sess = S.ProjectSession(out, build=_counting_build(calls))
    code, r = sess.history.apply([{"id": "e1", "screen": "home", "edit": "title", "value": "홈"}])
    assert code == 200 and r["applied"] == ["e1"] and calls == [], "쓰기는 index.html 을 굽지 않는다"
    before = (out / "screens.json").read_bytes()
    sess.builder._check = lambda o: subprocess.CompletedProcess([], 1, "", "시험용 확인 실패")
    code, r = sess.history.apply([{"id": "e2", "screen": "home", "edit": "title", "value": "깨짐"}])
    assert not r.get("applied") and "시험용 확인 실패" in json.dumps(r, ensure_ascii=False), r
    assert (out / "screens.json").read_bytes() == before, "확인이 깨진 쓰기는 되돌린다"


def test_page_rebuilds_once_when_data_changed_and_never_for_unstamped_pages(tmp_path):
    out = hdfix.make_out(tmp_path)                   # 가짜 index.html(도장 없음)
    calls = []
    sess = S.ProjectSession(out, build=_counting_build(calls))
    sess.history.apply([{"id": "e1", "screen": "home", "edit": "title", "value": "홈"}])
    assert b"canvas" in sess.page() and calls == [], "도장 없는 페이지는 견주지 않는다"
    sess.builder.build()                              # 도장 있는 페이지
    calls.clear()
    assert sess.refresh_data() == "fresh" and calls == []
    sess.history.apply([{"id": "e2", "screen": "home", "edit": "title", "value": "홈2"}])
    assert calls == []
    sess.page()
    assert calls == [1], "줄 때 데이터가 옛것이면 다시 빌드"
    sess.page()
    assert calls == [1], "한 번만"


def test_page_does_not_wait_for_a_write_and_gives_up_on_a_stamp_the_build_cannot_make(tmp_path):
    out = hdfix.make_out(tmp_path)
    calls = []
    sess = S.ProjectSession(out, build=_counting_build(calls))
    sess.builder.build()
    sess.history.apply([{"id": "e1", "screen": "home", "edit": "title", "value": "홈"}])
    calls.clear()
    with sess.lock:                                   # 쓰기 중
        got = []
        t = threading.Thread(target=lambda: got.append(sess.refresh_data(wait=0.05)))
        t.start(); t.join(5)
    assert got == ["busy"] and calls == [], "쓰기 중이면 있던 페이지(기다리지 않음)"
    sess.builder._run = lambda o: (calls.append(1), subprocess.CompletedProcess([], 0, "", ""))[1]   # 도장을 못 적는 빌드(옛 코드)
    assert sess.refresh_data() == "failed" and sess.refresh_data() == "fresh" and calls == [1], "같은 도장으로 매번 빌드하지 않는다"
