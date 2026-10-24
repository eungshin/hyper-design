"""허브·도우미 통합 — 자식 프로세스(`hd home` · helper.py), 임시 HD_HOME. 브라우저 없음, 실제 바탕 화면·12270·12279 를 건드리지 않는다.
hd home: 기록(home.json) 쓰기·다시 쓰기·정상 종료 때 지움 · 도우미의 새 라우트(같은 JSON) · /api/home 이 허브를 띄움 ·
진짜 빈 캔버스(새 프로젝트 → build_ref → 도우미 → index.html) · 바탕 화면 바로 가기와 아이콘."""
import json, os, pathlib, signal, subprocess, sys, time, urllib.error, urllib.request

import pytest

HOME = pathlib.Path(__file__).resolve().parents[1]
HD = HOME.parent / "hd"
sys.path[:0] = [str(HOME), str(HD), str(HD / "tests")]
import hd_client as C  # noqa: E402
import hdfix  # noqa: E402
import shortcut  # noqa: E402

HD_PY = HD / "hd.py"
WIN = sys.platform == "win32"


def env(home):
    e = hdfix.env(home)
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        e.pop(k, None)
    e["HD_HUB_PORT"] = "0"                                            # 떼어 띄운 허브도 12270 을 쓰지 않게
    return e


def start_hub(home):
    p = subprocess.Popen([sys.executable, str(HD_PY), "home", "--no-browser", "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", env=env(home), creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if WIN else 0)
    url = p.stdout.readline().strip()
    assert url.startswith("http://127.0.0.1:") and "/?hd=" in url, (url, p.stderr.read() if p.poll() is not None else "")
    return p, url


def call(base, token, path, body=None, method=None, timeout=60):
    r = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                               method=method or ("GET" if body is None else "POST"),
                               headers={"X-HD-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def split(url):
    if "/index.html?hd=" in url:
        return url.split("/index.html?hd=")
    return url.split("/?hd=")


def test_hd_home_record_reuse_and_clean_exit(tmp_path):
    home = tmp_path / "home"
    p, url = start_hub(home)
    try:
        rec = json.loads((home / "home.json").read_text(encoding="utf-8"))
        assert rec["url"] == url and rec["pid"] == p.pid and rec["token"] in url
        base, token = split(url)
        assert call(base, token, "/api/tabs") == (200, {"tabs": []})
        r = subprocess.run([sys.executable, str(HD_PY), "home", "--no-browser", "--json", "--port", "0"], capture_output=True, text=True,
                           encoding="utf-8", env=env(home), timeout=30)
        d = json.loads(r.stdout)
        assert r.returncode == 0 and d["reused"] is True and d["url"] == url, "떠 있으면 그 허브를 다시 쓴다(둘째를 띄우지 않음)"
    finally:
        assert hdfix.stop_helper(p)
    assert not (home / "home.json").exists(), "정상 종료 때 기록을 지운다"
    (home / "home.json").write_text(json.dumps({"url": "http://127.0.0.1:1/?hd=x", "pid": 999999, "port": 1, "token": "x"}), encoding="utf-8")
    p, url2 = start_hub(home)
    try:
        assert json.loads((home / "home.json").read_text(encoding="utf-8"))["pid"] == p.pid, "죽은 기록은 덮어쓴다"
    finally:
        hdfix.stop_helper(p)


def test_helper_serves_same_routes_and_home_spawns_hub(tmp_path):
    home = tmp_path / "home"
    out = hdfix.make_out(tmp_path / "w")
    p, url = hdfix.start_helper(out, home, extra_env={"HD_HUB_PORT": "0"})
    hub_pid = None
    try:
        base, token = split(url)
        code, rows = call(base, token, "/api/projects")
        assert code == 200 and rows[0]["name"] == "proj-a" and rows[0]["state"] == "running" and rows[0]["thumb"] is None
        assert set(rows[0]) >= {"title", "created", "starred", "trashed", "thumb"}
        assert call(base, token, "/api/tabs", {"tabs": ["proj-a", "x"]}, method="PUT") == (200, {"tabs": ["proj-a"]})
        assert call(base, token, "/api/tabs") == (200, {"tabs": ["proj-a"]})
        code, res = call(base, token, "/api/project", {"name": "proj-a", "title": "프로젝트 A"})
        assert code == 200 and res["row"]["title"] == "프로젝트 A"
        assert call(base, token, "/api/forget", {"name": "proj-a"})[0] == 409
        assert call(base, token, "/api/state", {"rev": 0, "state": {}}, method="PUT")[0] in (200, 409), "PUT /api/state 그대로"
        code, res = call(base, token, "/api/home")                      # 허브가 없으니 떼어 띄운다
        assert code == 200 and "/?hd=" in res["url"], res
        hub_pid = json.loads((home / "home.json").read_text(encoding="utf-8"))["pid"]
        hb, ht = split(res["url"])
        assert call(hb, ht, "/api/tabs") == (200, {"tabs": ["proj-a"]}), "허브와 도우미가 같은 탭"
        code, rows = call(base, token, "/api/projects")
        assert code == 200 and rows[0]["title"] == "프로젝트 A"
        assert call(base, token, "/api/home") == (200, {"url": res["url"]}), "떠 있으면 같은 주소"
    finally:
        hdfix.stop_helper(p)
        if hub_pid:
            C.kill_pid(hub_pid)


def test_new_project_real_empty_canvas_opens(tmp_path, monkeypatch):
    """진짜 빌드(build_ref → git HEAD 의 build_canvas)와 진짜 도우미 — 화면 0개인 캔버스도 뜬다."""
    home = tmp_path / "home"
    monkeypatch.setenv("HD_HOME", str(home))                          # C.markers · C.stop 이 같은 임시 HD_HOME 을 보게
    p, url = start_hub(home)
    try:
        base, token = split(url)
        code, res = call(base, token, "/api/new", {"title": "빈 캔버스"}, timeout=120)
        assert code == 200, res
        assert res["name"] == "빈-캔버스" and "/index.html?hd=" in res["url"]
        with urllib.request.urlopen(res["url"], timeout=10) as r:
            html = r.read().decode("utf-8")
        assert r.status == 200 and "hd-data" in html
        out = home / "projects" / "빈-캔버스" / "out"
        assert (out / "index.html").is_file()
        rows = call(base, token, "/api/projects")[1]
        assert rows[0]["name"] == "빈-캔버스" and rows[0]["state"] == "running" and rows[0]["title"] == "빈 캔버스"
    finally:
        for m in C.markers():                                         # 이 테스트가 띄운 도우미(임시 HD_HOME)만
            C.stop(m)
        hdfix.stop_helper(p)


@pytest.mark.skipif(not WIN, reason="바로 가기는 Windows 만")
def test_shortcut_to_temp_desktop(tmp_path):
    home, desk = tmp_path / "home", tmp_path / "Desktop"
    desk.mkdir()
    r = subprocess.run([sys.executable, str(HD_PY), "home", "--shortcut", "--desktop", str(desk), "--json"], capture_output=True, text=True,
                       encoding="utf-8", env=env(home), timeout=60)
    assert r.returncode == 0, r.stderr
    lnk = desk / "Hyper Design.lnk"
    assert json.loads(r.stdout) == {"shortcut": str(lnk)} and lnk.is_file()
    s = shortcut.read_shortcut(lnk)
    assert s["target"].lower().endswith(("pythonw.exe", "python.exe")) and str(HD_PY) in s["args"] and s["args"].endswith(" home")
    assert pathlib.Path(s["workdir"]) == home and pathlib.Path(s["icon"].rsplit(",", 1)[0]) == home / "hd.ico"
    ico = (home / "hd.ico").read_bytes()
    assert ico[:6] == b"\x00\x00\x01\x00\x01\x00" and b"\x89PNG" in ico[:40]
    r = subprocess.run([sys.executable, str(HD_PY), "home", "--shortcut", "--desktop", str(tmp_path / "nope")], capture_output=True,
                       text=True, encoding="utf-8", env=env(home), timeout=60)
    assert r.returncode == 1 and "바탕 화면 폴더가 없어요" in r.stderr


def test_icon_failure_never_fails(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert shortcut.make_icon(blocker / "hd.ico") is None, "아이콘을 못 만들면 None(바로 가기는 아이콘 없이)"
    assert "아이콘을 만들지 못했어요" in capsys.readouterr().err
