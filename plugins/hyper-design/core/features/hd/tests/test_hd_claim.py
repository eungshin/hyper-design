"""hd claim · release (#254) — 규칙(hd_model.claim·release·claim_error·busy_items) + 도우미 자식 프로세스로 왕복 · 화면 파일 지켜보기(/api/files). 브라우저 없음."""
import json, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path.insert(0, str(hdfix.HD))
import hd_model as M  # noqa: E402

HD_PY = hdfix.HD / "hd.py"


def env(home):
    e = hdfix.env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        e.pop(k, None)
    return e


def hd(home, *args):
    r = subprocess.run([sys.executable, str(HD_PY), *args], capture_output=True, text=True, encoding="utf-8", env=env(home), timeout=60)
    return r.returncode, r.stdout, r.stderr


def busy(out):
    return json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"].get("busy")


def api(url, path):
    base, token = url.split("/index.html?hd=")
    req = urllib.request.Request(base + path, headers={"X-HD-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_claim_model_rules():
    v, w = M.claim(None, "home", "screens/home.html", 5, 1.5, "agent-1", " 버튼 ")
    assert v == {"v": 1, "items": {"home": {"via": "cli", "since": 5, "file": "screens/home.html", "mtime": 1.5, "by": "agent-1", "note": "버튼"}}} and w == []
    q = {"via": "queue", "since": 1, "file": "screens/list.html", "mtime": None}
    v2, _ = M.claim({"v": 1, "items": {"list": q}}, "home", "screens/home.html", 6)
    assert v2["items"]["list"] == q and v2["items"]["home"] == {"via": "cli", "since": 6, "file": "screens/home.html", "mtime": None}, "다른 덮개는 그대로"
    v3, gone, _ = M.release(v2, "home")
    assert gone and v3 == {"v": 1, "items": {"list": q}}
    assert M.release(v3, "home")[1] is False
    v4, w4 = M.claim("broken", "home", "f", 1)
    assert list(v4["items"]) == ["home"] and w4 and w4[0].startswith("[hd]"), "깨진 busy = 비우고 [hd] 한 줄"
    _, w5 = M.busy_items({"v": 1, "items": {"x": {"via": "zz", "file": "f"}, "y": q}})
    assert len(w5) == 1 and "x" in w5[0]
    assert M.claim_error("home") is None and M.claim_error("home", "a-1", "짧은 메모") is None
    assert M.claim_error("") and M.claim_error("home", "a b") and M.claim_error("home", None, "x" * 141) and M.claim_error("home", None, " ")


@pytest.fixture()
def canvas(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    yield out, home, url
    hdfix.stop_helper(p)


def test_claim_writes_busy_release_removes_unknown_screen_fails(canvas):
    out, home, url = canvas
    code, o, err = hd(home, "claim", "home", "--note", "버튼 문구 고치는 중", "--by", "agent-9")
    assert code == 0, err
    assert "home 덮개 씌움" in o
    b = busy(out)["items"]["home"]
    assert b["via"] == "cli" and b["file"] == "screens/home.html" and b["by"] == "agent-9" and b["note"] == "버튼 문구 고치는 중"
    assert b["mtime"] == (out / "screens" / "home.html").stat().st_mtime, "기준 = 씌울 때 파일 시각(바뀌면 캔버스가 걷는다)"
    assert json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"]["notes"], "다른 상태는 그대로"
    code, o, err = hd(home, "claim", "ghost")
    assert code == 1 and err.strip().count("\n") == 0 and "없는 화면" in err, err
    code, o, err = hd(home, "release", "home", "--json")
    assert code == 0 and json.loads(o)["released"] is True, err
    assert busy(out) == {"v": 1, "items": {}}
    code, o, err = hd(home, "release", "home")
    assert code == 0 and "덮개가 없어요" in o


def test_helper_reports_changed_screen_files(canvas):
    out, home, url = canvas
    code, r = api(url, "/api/files")
    assert code == 200 and r["changed"] == [], r
    seq = r["seq"]
    time.sleep(1.2)                                   # 기준을 잡은 뒤에 바꾼다
    f = out / "screens" / "list.html"
    f.write_text(f.read_text(encoding="utf-8") + "<!-- x -->", encoding="utf-8")
    assert hdfix.wait_for(lambda: api(url, "/api/files?since=%d" % seq)[1]["changed"] == ["list"], 5), api(url, "/api/files?since=%d" % seq)
    assert api(url, "/api/files?since=nope")[0] == 400
