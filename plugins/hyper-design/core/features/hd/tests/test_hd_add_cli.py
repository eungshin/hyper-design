"""hd screens · hd add 통합 — 도우미(자식 프로세스, HD_HOME 임시)로: 복사 · 등록 · 새 줄 · 자리/크기는 도우미로(PUT /api/state) ·
캔버스가 다시 받을 판 데이터(/api/data)에 새 화면 · 오류는 한 줄 · 도우미가 없으면 빌드하고 상태 파일은 손대지 않음. 브라우저 없음."""
import json, subprocess, sys, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

HD_PY = hdfix.HD / "hd.py"


def hd(home, *args):
    env = dict(hdfix.env(home), HD_ADD_SETTLE="0")
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
    return r.returncode, r.stdout, r.stderr


def hdj(home, *args):
    code, out, err = hd(home, *args, "--json")
    return code, json.loads(out), err


def mock(root, name="mock", title="목업 화면"):
    d = Path(root) / "src"
    (d / "img").mkdir(parents=True, exist_ok=True)
    (d / "img" / "a.png").write_bytes(b"\x89PNG-fake")
    f = d / (name + ".html")
    f.write_text("<html><head><title>%s</title></head><body><img src='img/a.png'><h1>%s</h1></body></html>" % (title, name), encoding="utf-8")
    return f


def manifest(out):
    return json.loads((out / "screens.json").read_text(encoding="utf-8"))


def marker(home):
    return json.loads(next((home / "active").glob("*.json")).read_text(encoding="utf-8"))


def api(m, path, body=None, method="POST"):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (m["port"], path), method=method,
                                 data=None if body is None else json.dumps(body).encode(), headers={"X-HD-Token": m["token"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


@pytest.fixture()
def canvas(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    yield out, home
    hdfix.stop_helper(p)


def test_add_places_screen_through_helper_and_screens_lists_it(canvas, tmp_path):
    out, home = canvas
    src = mock(tmp_path)
    code, r, err = hdj(home, "add", str(src), "--after", "home", "--size", "Desktop", "--asset", str(src.parent / "img" / "a.png"), "--purpose", "비교")
    assert code == 0, err
    assert (r["id"], r["file"], r["title"], r["live"], r["assets"]) == ("mock", "mock.html", "목업 화면", True, ["img/a.png"])
    assert (out / "mock.html").read_bytes() == src.read_bytes() and (out / "img" / "a.png").is_file()
    assert [s["id"] for s in manifest(out)["screens"]] == ["home", "mock", "list"], "--after 바로 뒤"
    st = api(marker(home), "/api/state", method="GET")
    assert st["state"]["card-size"]["mock"] == {"w": 1440, "h": 1024, "preset": "Desktop"} and st["rev"] == r["state_rev"]
    assert st["state"]["notes"] and st["state"]["card-pos"] == {"home": [1, 2]}, "다른 이름·다른 카드 값은 그대로"
    data = api(marker(home), "/api/data", {})
    assert "mock" in [s["id"] for row in data["rows"] for s in row["screens"]], "캔버스가 다시 받는 판 데이터에 새 화면"

    code, r, err = hdj(home, "add", str(mock(tmp_path, "m2", "둘째")), "--group", "새 줄", "--at=200,-40")
    assert code == 0 and r["group_added"] and r["pos"] == {"dx": 200, "dy": -40}, err
    assert manifest(out)["groups"] == ["새 줄"] and manifest(out)["screens"][-1]["group"] == "새 줄"
    assert api(marker(home), "/api/state", method="GET")["state"]["card-pos"]["m2"] == {"dx": 200, "dy": -40, "g": "새 줄"}

    code, d, err = hdj(home, "screens")
    assert code == 0 and d["helper"] is True, err
    assert [(s["id"], s["group"], s["pos"], (s["size"] or {}).get("preset")) for s in d["screens"]] == [
        ("home", None, None, None), ("mock", None, None, "Desktop"), ("list", None, None, None), ("m2", "새 줄", {"dx": 200, "dy": -40}, None)]
    code, text, _ = hd(home, "screens", "proj-a")
    assert text.splitlines()[0] == "proj-a · 화면 4개 · 줄 2개" and "  m2 · 둘째 · m2.html · 자리 +200,-40" in text

    code, r, err = hdj(home, "add", str(mock(tmp_path, "m2", "둘째 v2")), "--id", "m2", "--replace", "--at", "10,5")
    assert code == 0 and r["replaced"] and r["pos"] == {"dx": 10, "dy": 5} and r["title"] == "둘째", "바꿀 때 제목은 그대로(--title 로 바꿈)"
    assert "둘째 v2" in (out / "m2.html").read_text(encoding="utf-8")


def test_add_errors_are_one_line_and_write_nothing(canvas, tmp_path):
    out, home = canvas
    src = mock(tmp_path)
    before = (out / "screens.json").read_text(encoding="utf-8")
    for args, why in (((str(tmp_path / "nope.html"),), "없는 파일이에요"),
                      ((str(src), "--after", "ghost"), "없는 화면이에요(--after): ghost — 있는 화면: home, list"),
                      ((str(src), "--id", "home"), "이미 있는 화면 id 예요: home"),
                      ((str(src), "--size", "Huge"), "--size: 모르는 크기예요: Huge"),
                      ((str(src), "nowhere"), "모르는 캔버스예요: nowhere")):
        code, o, err = hd(home, "add", *args)
        lines = err.strip().splitlines()
        assert code == 1 and len(lines) == 1 and lines[0].startswith("hd: ") and why in lines[0], (args, err)
    assert (out / "screens.json").read_text(encoding="utf-8") == before and not (out / "mock.html").exists()
    code, o, err = hd(home, "screens", "nowhere")
    assert code == 1 and "모르는 캔버스예요: nowhere" in err


def test_add_without_helper_builds_and_leaves_state_file_alone(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    state = (out / ".hd-canvas.json").read_bytes()
    src = mock(tmp_path)
    code, o, err = hd(home, "add", str(src), str(out), "--at", "1,1")
    assert code == 1 and "도우미가 없어요" in err and "hd open" in err and not (out / "mock.html").exists(), err
    code, r, err = hdj(home, "add", str(src), str(out))
    assert code == 0 and r["live"] is False and [s["id"] for s in manifest(out)["screens"]] == ["home", "list", "mock"], err
    assert "mock.html" in (out / "index.html").read_text(encoding="utf-8"), "hd open 과 같은 빌드(build_ref.py)"
    assert (out / ".hd-canvas.json").read_bytes() == state, "도우미가 없으면 상태 파일은 손대지 않는다"
    assert not (home / "projects.json").exists(), "읽고 넣기만 — 프로젝트 목록에 넣지 않는다"
    code, text, err = hd(home, "screens", str(out))
    assert code == 0 and "도우미 꺼짐" in text.splitlines()[0] and "  mock · 목업 화면 · mock.html" in text, err


def _collect_events(m, out_list, ready, stop):
    """도우미 이벤트 흐름을 따로 모은다(열린 탭이 받는 알림 수를 세려고)."""
    import threading  # noqa: F401
    sys.path.insert(0, str(hdfix.HD))
    import hd_sdk as S
    p = S.Project(m)
    for ev in p._events(None, 30, 3, __import__("time").time, __import__("time").sleep, opens=True):
        if ev.type == "open":
            ready.set(); continue
        out_list.append(ev.type)
        if stop.is_set():
            return


def test_add_many_files_one_call_bumps_state_once_and_notifies_once(canvas, tmp_path):
    import threading, time
    out, home = canvas
    fs = [mock(tmp_path, n, n.upper()) for n in ("m1", "m2", "m3")]
    m = marker(home)
    rev0 = api(m, "/api/state", method="GET")["rev"]
    evs, ready, stop = [], threading.Event(), threading.Event()
    t = threading.Thread(target=_collect_events, args=(m, evs, ready, stop), daemon=True)
    t.start()
    assert ready.wait(10), "이벤트 흐름이 열리지 않았어요"
    code, r, err = hdj(home, "add", *map(str, fs), "--to", "proj-a", "--at=0,300", "--size", "390x844")
    assert code == 0, err
    time.sleep(0.6); stop.set()
    assert [x["id"] for x in r["screens"]] == ["m1", "m2", "m3"] and r["live"] is True
    st = api(m, "/api/state", method="GET")
    assert st["rev"] == rev0 + 1 == r["state_rev"], "여러 장이어도 상태 쓰기는 한 번"
    assert {k: st["state"]["card-pos"][k] for k in ("m1", "m2", "m3")} == {k: {"dx": 0, "dy": 300, "g": None} for k in ("m1", "m2", "m3")}
    assert st["state"]["card-size"]["m3"] == {"w": 390, "h": 844}
    assert [s["id"] for s in manifest(out)["screens"]] == ["home", "list", "m1", "m2", "m3"]
    assert evs.count("screen.written") == 1 and evs.count("notes.changed") == 1, evs


def test_add_old_form_canvas_as_second_positional_still_works_with_one_warning(canvas, tmp_path):
    out, home = canvas
    code, r, err = hdj(home, "add", str(mock(tmp_path)), "proj-a")
    assert code == 0 and r["id"] == "mock" and r["live"] is True, err
    warn = [ln for ln in err.strip().splitlines() if ln]
    assert len(warn) == 1 and warn[0].startswith("[hd] ") and "--to proj-a" in warn[0], err
    assert [s["id"] for s in manifest(out)["screens"]] == ["home", "list", "mock"]
