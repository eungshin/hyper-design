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
