"""서버 하나(task 47-2) — 허브(home_server.make_hub, 이 프로세스 안)가 프로젝트 둘을 제 안 세션으로 열고, 캔버스는 /v1/p/<이름>/ 에서 뜬다 (Playwright).
탭을 눌러 다른 프로젝트로 가도 · 홈 단추로 홈에 가도 주소(origin)가 그대로이고, 옛 '/api/…' 는 페이지 토큰으로 그 세션에 닿는다.
임시 HD_HOME · 작업 트리 build_canvas · 12270/12279 를 쓰지 않는다."""
import json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401

CANVAS = Path(__file__).resolve().parents[1]
FEATURES = CANVAS.parent
sys.path[:0] = [str(CANVAS), str(FEATURES / "hd"), str(FEATURES / "home")]
import hd_client as C  # noqa: E402
import home_server  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.area("helper")

SCREEN = "<!doctype html><html><head><meta charset='utf-8'></head><body><main><h1>{title}</h1><button>다음</button></main></body></html>"


def build(out):                                       # 작업 트리 빌드(허브의 실사용 build_ref 대신) — (코드, 끝 줄)
    r = write_record.run_build(out)
    return r.returncode, (r.stderr or "")[-300:]


def make_out(root, name, title):
    out = root / name / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "home.html").write_text(SCREEN.format(title=title), encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"title": title, "groups": ["g"], "screens": [
        {"id": "home", "file": "screens/home.html", "title": title, "group": "g", "purpose": "", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    return out


@pytest.fixture(scope="module")
def hub():
    tmp = Path(tempfile.mkdtemp(prefix="hd-one-server-"))
    old, old_build = os.environ.get("HD_HOME"), C.build
    os.environ["HD_HOME"] = str(tmp / "hd-home")
    C.build = build
    outs = {n: make_out(tmp, n, t) for n, t in (("alpha", "알파"), ("beta", "베타"))}
    for o in outs.values():
        C.register(C.abs_out(o))
    srv = home_server.make_hub(0, renderer=lambda *a: None, picker=lambda: None, build=lambda o: write_record.run_build(o))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    urls = {n: _post(srv, "/api/open", {"name": n})["url"] for n in outs}
    try:
        yield srv, outs, urls
    finally:
        srv.shutdown(); srv.server_close()
        C.build = old_build
        if old is None:
            os.environ.pop("HD_HOME", None)
        else:
            os.environ["HD_HOME"] = old
        shutil.rmtree(tmp, ignore_errors=True)


def _post(srv, path, body):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (srv.server_address[1], path), data=json.dumps(body).encode("utf-8"), method="POST",
                               headers={"X-HD-Token": srv.token, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=120) as res:
        return json.loads(res.read())


def _open(ctx, url):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(url)
    pg.wait_for_function("window.__hdReady !== undefined")
    return pg, errors


def test_tabs_and_home_stay_on_one_origin(hub, ctx):
    srv, outs, urls = hub
    origin = "http://127.0.0.1:%d" % srv.server_address[1]
    assert all(u.startswith(origin + "/v1/p/") for u in urls.values()), urls
    pg, errors = _open(ctx, urls["alpha"])
    try:
        pg.wait_for_selector("#ptabs .pt-tab[data-name='beta']")
        st = pg.evaluate("t => fetch('/api/state', {headers: {'X-HD-Token': t}}).then(r => r.status)", urls["alpha"].split("hd=")[1])
        assert st == 200, "옛 '/api/state' + 페이지 토큰 = 이 세션"
        with pg.expect_navigation(url=lambda u: "/v1/p/beta/" in u):
            pg.click("#ptabs .pt-tab[data-name='beta']")
        pg.wait_for_function("window.__hdReady !== undefined")
        assert pg.evaluate("location.origin") == origin, "탭을 옮겨도 같은 주소"
        assert pg.evaluate("window.__hdOut").endswith("/beta/out"), "그 프로젝트의 캔버스"
        pg.wait_for_selector("#hhome")
        with pg.expect_navigation(url=lambda u: u.startswith(origin + "/?hd=")):
            pg.click("#hhome")
        assert pg.evaluate("window.__hdHub") is True, "홈도 같은 주소"
    finally:
        pg.close()
    assert not errors, errors
