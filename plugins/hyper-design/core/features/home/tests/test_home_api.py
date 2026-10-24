"""허브(home_server) API — 이 프로세스 안 서버, 임시 HD_HOME, 썸네일 그리기·폴더 고르기·탐색기·띄우기는 가짜. 브라우저 없음.
페이지·정적 파일 · 토큰/Host · /api/projects 모양과 썸네일(낡음 → 다시 그림 → /thumb) · 제목·별표·휴지통 · forget · 탭 · 폴더 고르기 · 새 프로젝트."""
import json, os, pathlib, sys, threading, time, urllib.error, urllib.request

import pytest

HOME = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HOME), str(HOME.parent / "hd")]
import hd_client as C  # noqa: E402
import home_api as A  # noqa: E402
import home_client as H  # noqa: E402
import home_server as S  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\nfake"


def make_out(root, name, title=None, index=True):
    out = pathlib.Path(root) / name / "out"
    out.mkdir(parents=True)
    (out / "screens.json").write_text(json.dumps({"title": title, "groups": [], "screens": []} if title else {"screens": []}), encoding="utf-8")
    if index:
        (out / "index.html").write_text("<html><head></head><body>c</body></html>", encoding="utf-8")
    return out


class Hub:
    def __init__(self, srv):
        self.srv = srv
        self.base = "http://127.0.0.1:%d" % srv.server_address[1]

    def req(self, path, body=None, method=None, token=True, host=None, raw=False):
        h = {"Content-Type": "application/json"}
        if token:
            h["X-HD-Token"] = self.srv.token
        if host:
            h["Host"] = host
        r = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                                   method=method or ("GET" if body is None else "POST"), headers=h)
        try:
            with urllib.request.urlopen(r, timeout=20) as res:
                data = res.read()
                return res.status, (data if raw else json.loads(data)), res.headers
        except urllib.error.HTTPError as e:
            data = e.read()
            return e.code, (data if raw else json.loads(data)), e.headers


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HD_HOME", str(home))
    rendered, picks, revealed, opened = [], [], [], []

    def renderer(index_html, png):
        rendered.append(pathlib.Path(index_html))
        pathlib.Path(png).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(png).write_bytes(PNG)

    def fake_open(name, agent=None):
        e = next(x for x in C.load_projects()["projects"] if x["name"] == name)
        opened.append(name)
        return e, {"url": "http://127.0.0.1:1/index.html?hd=x", "pid": 1, "agent": agent}, False

    monkeypatch.setattr(H, "reveal", lambda out: revealed.append(out))
    monkeypatch.setattr(C, "open_project", fake_open)
    srv = S.make_hub(0, renderer=renderer, picker=lambda: picks.pop(0) if picks else None)
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    hub = Hub(srv)
    hub.home, hub.root, hub.rendered, hub.picks, hub.revealed, hub.opened = home, tmp_path / "w", rendered, picks, revealed, opened
    yield hub
    srv.shutdown(); srv.server_close()


def register(*outs):
    for o in outs:
        C.register(C.abs_out(o))


def test_page_static_and_guards(env):
    code, body, hd = env.req("/", raw=True, token=False)
    assert code == 200 and b"window.__hdToken=" in body and env.srv.token.encode() in body, "페이지는 토큰 없이 · 토큰을 끼워 줌"
    for f in ("home.js", "home.css", "home-model.js"):
        if (HOME / f).is_file():
            code, _, h = env.req("/" + f, raw=True, token=False)
            assert code == 200 and h["Content-Type"].startswith(("text/javascript", "text/css")), f
    for bad in ("/home_api.py", "/../hd/hd.py", "/.secret.js", "/nope.js"):
        assert env.req(bad, raw=True, token=False)[0] == 404, bad
    assert env.req("/api/projects", token=False)[0] == 403
    assert env.req("/api/tabs", host="evil.example:80")[0] == 403, "Host 검사"
    assert env.req("/api/tabs", {"tabs": []}, method="PUT", token=False)[0] == 403
    code, res, _ = env.req("/api/nope", {})
    assert code == 404 and res["error"]
    assert env.req("/api/home")[0] == 404, "/api/home 은 도우미만"


def test_projects_rows_thumbs_and_thumb_route(env):
    a = make_out(env.root, "a", title="세탁 앱")
    b = make_out(env.root, "b", index=False)
    register(a, b)
    (pathlib.Path(b) / "screens.json").unlink()                     # b = 없어진 out
    code, rows, _ = env.req("/api/projects")
    assert code == 200 and {r["name"] for r in rows} == {"a", "b"}
    r = next(x for x in rows if x["name"] == "a")
    assert set(r) >= {"name", "title", "out", "state", "url", "pid", "created", "last_opened", "starred", "trashed", "thumb"}
    assert r["title"] == "세탁 앱" and r["state"] == "off" and r["thumb"] is None and r["starred"] is False and r["trashed"] is None
    assert next(x for x in rows if x["name"] == "b")["state"] == "missing"
    assert env.srv.thumbs.done.wait(10)
    assert [p.parent.name for p in env.rendered] == ["out"] and env.rendered[0] == pathlib.Path(a) / "index.html", "낡은 것만(없어진 out 은 아님)"
    code, rows, _ = env.req("/api/projects")
    t = next(x for x in rows if x["name"] == "a")["thumb"]
    assert t.startswith("%s/thumb/a.png?t=" % env.base)
    code, png, h = env.req(t[len(env.base):], raw=True, token=False)
    assert code == 200 and png == PNG and h["Content-Type"] == "image/png", "썸네일은 토큰 없이"
    assert env.srv.thumbs.done.wait(10) and len(env.rendered) == 1, "새것이면 다시 그리지 않는다"
    future = time.time() + 100
    (pathlib.Path(a) / ".hd-canvas.json").write_text("{}", encoding="utf-8"); os.utime(pathlib.Path(a) / ".hd-canvas.json", (future, future))
    env.req("/api/projects")
    assert env.srv.thumbs.done.wait(10) and len(env.rendered) == 2, "상태 파일이 더 새로우면 다시 그린다"
    assert env.req("/thumb/zzz.png", raw=True, token=False)[0] == 404
    assert env.req("/thumb/..%2Fprojects.json", raw=True, token=False)[0] == 404


def test_project_title_star_trash_forget_and_tabs(env):
    a, b = make_out(env.root, "a"), make_out(env.root, "b")
    register(a, b)
    code, res, _ = env.req("/api/tabs", {"tabs": ["b", "ghost", "a", "b"]}, method="PUT")
    assert code == 200 and res["tabs"] == ["b", "a"], "모르는 이름·겹침은 버린다"
    assert env.req("/api/tabs")[1] == {"tabs": ["b", "a"]}
    assert json.loads((env.home / "tabs.json").read_text(encoding="utf-8")) == {"version": 1, "tabs": ["b", "a"]}
    assert env.req("/api/tabs", {"tabs": "a"}, method="PUT")[0] == 400
    code, res, _ = env.req("/api/project", {"name": "a", "title": "  새 이름 ", "starred": True})
    assert code == 200 and res["row"]["title"] == "새 이름" and res["row"]["starred"] is True and "thumb" in res["row"]
    for bad in ({"name": "a", "title": ""}, {"name": "a", "starred": "y"}, {"name": "a"}, {}):
        code, res, _ = env.req("/api/project", bad)
        assert code == 400 and res["error"], bad
    assert env.req("/api/project", {"name": "zz", "starred": True})[0] == 404
    code, res, _ = env.req("/api/forget", {"name": "a"})
    assert code == 409 and "휴지통" in res["error"], "휴지통에 없는 것은 못 뺀다"
    code, res, _ = env.req("/api/project", {"name": "a", "trashed": True})
    assert code == 200 and res["row"]["trashed"]
    assert env.req("/api/tabs")[1]["tabs"] == ["b"], "휴지통에 넣으면 탭에서 빠진다"
    assert env.req("/api/project", {"name": "a", "trashed": False})[1]["row"]["trashed"] is None
    env.req("/api/project", {"name": "a", "trashed": True})
    assert env.req("/api/forget", {"name": "a"}) [:2] == (200, {"ok": True})
    assert [e["name"] for e in C.load_projects()["projects"]] == ["b"] and pathlib.Path(a).is_dir(), "링크만 — 파일은 그대로"
    assert env.req("/api/forget", {"name": "a"})[0] == 404


def test_open_reveal_pick_folder(env):
    a = make_out(env.root, "a")
    register(a)
    code, res, _ = env.req("/api/open", {"name": "a"})
    assert code == 200 and res["url"].startswith("http://") and env.opened == ["a"]
    assert env.req("/api/tabs")[1]["tabs"] == ["a"], "열면 탭 끝에"
    assert env.req("/api/open", {})[0] == 400
    assert env.req("/api/reveal", {"name": "a"})[:2] == (200, {"ok": True}) and env.revealed == [str(a)]
    assert env.req("/api/reveal", {"name": "zz"})[0] == 404
    assert env.req("/api/pick-folder", {})[1] == {"cancel": True}, "취소"
    plain = env.root / "plain"; plain.mkdir()
    env.picks.append(str(plain))
    code, res, _ = env.req("/api/pick-folder", {})
    assert code == 400 and "캔버스 폴더가 아니에요" in res["error"]
    c = make_out(env.root, "c-proj")
    env.picks.append(str(c.parent))                                  # 그 위 폴더를 골라도 out/ 을 찾는다
    code, res, _ = env.req("/api/pick-folder", {})
    assert code == 200 and res == {"name": "c-proj"}
    assert any(C.abs_out(e["out"]) == C.abs_out(c) for e in C.load_projects()["projects"])


def test_new_project_makes_empty_canvas(env):
    code, res, _ = env.req("/api/new", {})
    assert code == 200 and res["name"] == "새-프로젝트-1" and res["title"] == "새 프로젝트 1" and res["url"]
    out = env.home / "projects" / "새-프로젝트-1" / "out"
    assert json.loads((out / "screens.json").read_text(encoding="utf-8")) == {"title": "새 프로젝트 1", "groups": [], "screens": []}
    code, res, _ = env.req("/api/new", {"title": "  "})
    assert res["title"] == "새 프로젝트 2"
    code, res, _ = env.req("/api/new", {"title": "My App"})
    assert res["name"] == "my-app" and env.opened == ["새-프로젝트-1", "새-프로젝트-2", "my-app"]
    (env.home / "projects" / "other").mkdir()
    code, res, _ = env.req("/api/new", {"title": "Other"})
    assert res["name"] == "other-2", "이미 있는 폴더와도 겹치지 않는다"
    assert env.req("/api/new", {"title": 3})[0] == 400 and env.req("/api/new", {"title": "x" * 81})[0] == 400
    assert env.req("/api/tabs")[1]["tabs"] == ["새-프로젝트-1", "새-프로젝트-2", "my-app", "other-2"]
    rows = env.req("/api/projects")[1]
    assert {r["title"] for r in rows} == {"새 프로젝트 1", "새 프로젝트 2", "My App", "Other"}


def test_broken_tabs_file_is_reported_and_empty(env, capsys):
    a = make_out(env.root, "a"); register(a)
    env.home.mkdir(parents=True, exist_ok=True)
    (env.home / "tabs.json").write_text("{broken", encoding="utf-8")
    assert env.req("/api/tabs")[1] == {"tabs": []}
    assert "탭 파일을 읽지 못했어요" in capsys.readouterr().err
