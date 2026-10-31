"""프로젝트 고르기 창 · 머리 홈 단추·제목(#246 → task 44) — 도우미로 연 캔버스 (Playwright).

임시 HD_HOME 에 프로젝트 두 개(지금 캔버스 · out 이 없어진 것) + 이 프로세스 안 도우미의 표지(write_marker).
첫 테스트는 진짜 /api/projects 를 쓴다(지금 = 열림·지금 표시 · 없어진 것 = '폴더 없음', 누르면 까닭). 나머지는 task 42 가 만드는 라우트
(/api/new·/api/home·제목·썸네일이 든 /api/projects)를 `page.route` 로 흉내 낸다(mock_hub). 프로젝트를 고르면 이 탭이 받은 주소로 간다.
file:// 로 열면(도우미 없음) 단추·창·홈 단추가 없고 'hd' 표시 + 폴더 이름 제목(옛 '전체 화면 한눈에 보기' 아님).
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("menu", "helper")


@pytest.fixture(scope="module")
def served():
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-projects-"))
    out = tmp / "cur" / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    home = tmp / "hd-home"
    home.mkdir()
    (home / "projects.json").write_text(json.dumps({"version": 1, "projects": [
        {"name": "cur", "out": str(out.resolve()), "kind": "run", "created": "2026-10-20T10:00:00+09:00", "last_opened": "2026-10-23T09:00:00+09:00"},
        {"name": "gone", "out": str(tmp / "gone" / "out"), "kind": "run", "created": "2026-10-01T10:00:00+09:00", "last_opened": "2026-10-02T11:30:00+09:00"},
    ]}, ensure_ascii=False), encoding="utf-8")
    old = os.environ.get("HD_HOME")
    os.environ["HD_HOME"] = str(home)                 # hd_client·helper 가 부를 때마다 읽는다 — 진짜 ~/.hyper-design 은 건드리지 않는다
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    marker = helper.write_marker(out, srv)            # 떠 있는 표지 = '열림' · /api/open 이 이 도우미를 다시 쓴다(새 도우미를 띄우지 않음)
    yield out, srv
    marker.unlink(missing_ok=True)
    srv.shutdown(); srv.server_close()
    if old is None:
        os.environ.pop("HD_HOME", None)
    else:
        os.environ["HD_HOME"] = old
    shutil.rmtree(tmp, ignore_errors=True)


def project_rows(out, extra=()):
    """task 42 모양의 /api/projects 줄 — 지금 캔버스(cur, 제목 '결제 흐름') + extra."""
    rows = [{"name": "cur", "title": "결제 흐름", "out": out.resolve().as_posix(), "state": "running", "url": "http://x/", "pid": 1,
             "created": "2026-10-20T10:00:00+09:00", "last_opened": "2026-10-23T09:00:00+09:00", "starred": False, "trashed": None, "thumb": None}]
    return rows + [dict({"out": "/tmp/" + r["name"] + "/out", "state": "off", "url": None, "pid": None, "created": "2026-10-01T10:00:00+09:00",
                         "last_opened": "2026-10-02T11:30:00+09:00", "starred": False, "trashed": None, "thumb": None}, **r) for r in extra]


def mock_hub(pg, srv, rows, tabs=None, fail=None):
    """task 42 라우트 흉내(page.route) — 받은 요청은 calls 에 [(method, path, body)] 로. /api/open·/api/new·/api/home 은 같은 도우미 주소에 표시를 붙여 준다
    (그 주소로 이 탭이 가면 캔버스가 다시 열린다 — 어디로 갔는지 URL 로 본다). fail = {path: (status, error)} 는 그 라우트를 실패로."""
    calls, state = [], {"tabs": list(tabs or [])}
    fail = fail or {}

    def handle(route):
        q = route.request
        path = "/" + q.url.split("://", 1)[1].split("/", 1)[1].split("?", 1)[0]
        body = json.loads(q.post_data) if q.post_data else None
        calls.append((q.method, path, body))
        if path in fail:
            st, err = fail[path]
            return route.fulfill(status=st, content_type="application/json", body=json.dumps({"error": err}, ensure_ascii=False))
        if path == "/api/projects":
            res = rows
        elif path == "/api/tabs":
            if q.method == "PUT":
                state["tabs"] = list(body["tabs"])
            res = {"tabs": state["tabs"]}
        elif path == "/api/open":
            res = {"name": body["name"], "url": srv.url + "&to=" + body["name"]}
        elif path == "/api/new":
            res = {"name": "new-1", "url": srv.url + "&to=new-1"}
        elif path == "/api/home":
            res = {"url": srv.url + "&to=home"}
        elif path == "/api/project":
            res = {"row": dict(next(r for r in rows if r["name"] == body["name"]), **{k: v for k, v in body.items() if k != "name"})}
        elif path in ("/api/reveal",):
            res = {"ok": True}
        elif path == "/api/pick-folder":
            res = {"cancel": True}
        else:
            return route.continue_()
        return route.fulfill(status=200, content_type="application/json", body=json.dumps(res, ensure_ascii=False))
    pg.route("**/api/*", handle)
    return calls, state


def _open(ctx, url, setup=None):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    if setup:
        setup(pg)
    pg.goto(url)
    pg.wait_for_function("window.__hdReady !== undefined")
    return pg, errors


def cards(pg):
    return pg.eval_on_selector_all("#ppick .pk-card:not(.pk-skel)", "els => els.map(e => ({name: e.dataset.name || e.dataset.act, state: e.dataset.state || null, "
                                   "cur: e.getAttribute('aria-current'), text: e.innerText.replace(/\\s+/g, ' ').trim()}))")


def test_picker_lists_real_projects_marks_current_and_missing(served, ctx):
    out, srv = served
    pg, errors = _open(ctx, srv.url)
    try:
        assert pg.is_visible("#pbtn") and pg.text_content("#pbtn").startswith("프로젝트"), "도우미로 열면 위쪽 줄에 '프로젝트' 단추"
        pg.click("#pbtn")
        assert pg.get_attribute("#ppick .pk", "role") == "dialog"
        pg.wait_for_selector("#ppick .pk-card[data-name='gone']")
        cs = cards(pg)
        assert [c["name"] for c in cs] == ["new", "folder", "cur", "gone"], "+ 새 프로젝트 · 폴더 열기 · 받은 차례 그대로(최근 연 것부터)"
        cur, gone = cs[2], cs[3]
        assert cur["state"] == "open" and cur["cur"] == "true" and "지금" in cur["text"], cur
        assert gone["state"] == "missing", gone
        posts = []
        pg.on("request", lambda q: posts.append(q.url) if q.method == "POST" else None)
        pg.click("#ppick .pk-card[data-name='gone']")                      # 못 여는 카드 — 까닭을 알리고 요청은 없다
        pg.wait_for_function("document.querySelector('#toast').textContent.includes('out 폴더가 없어')")
        assert not posts, posts
        url = pg.url
        pg.click("#ppick .pk-card[data-name='cur']")                       # 지금 것 = 창만 닫는다(다시 열지 않음)
        pg.wait_for_selector("#ppick", state="hidden")
        assert pg.url == url
    finally:
        pg.close()
    assert not errors, errors


def test_picker_search_thumbs_and_opens_in_this_tab(served, ctx):
    out, srv = served
    rows = project_rows(out, [{"name": "laundry", "title": "세탁 앱", "thumb": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>"},
                              {"name": "old", "title": "버린 것", "trashed": "2026-10-20T00:00:00+09:00"}])
    holder = {}
    pg, errors = _open(ctx, srv.url, lambda p: holder.update(calls=mock_hub(p, srv, rows)[0]))
    try:
        pg.click("#pbtn")
        pg.wait_for_selector("#ppick .pk-card[data-name='laundry']")
        assert [c["name"] for c in cards(pg)] == ["new", "folder", "cur", "laundry"], "휴지통 프로젝트는 고르기 창에 없다"
        assert pg.text_content("#ppick .pk-card[data-name='cur'] .pk-ttl") == "결제 흐름", "카드 제목 = 프로젝트 제목"
        assert pg.query_selector("#ppick .pk-card[data-name='laundry'] .pk-th img") is not None, "썸네일 주소가 있으면 그림"
        assert pg.query_selector("#ppick .pk-card[data-name='cur'] .pk-th img") is None
        assert pg.text_content("#ppick .pk-card[data-name='cur'] .pk-th .pk-ini") == "결", "썸네일이 없으면 빈 상자 대신 제목 첫 글자(U3 F20)"
        pg.fill("#ppick .pk-q", "세탁")
        assert [c["name"] for c in cards(pg)] == ["new", "folder", "laundry"], "검색 = 제목·이름 부분 일치"
        with pg.expect_navigation(url=lambda u: "to=laundry" in u):
            pg.click("#ppick .pk-card[data-name='laundry']")
        assert ("POST", "/api/open", {"name": "laundry"}) in holder["calls"], "이 탭이 POST /api/open 이 준 주소로 간다(새 탭 없음)"
        assert ctx.pages == [pg], "새 탭을 열지 않는다"
    finally:
        pg.close()
    assert not errors, errors


def test_open_failure_shows_helper_line(served, ctx):
    """도우미가 오류를 답하면 그 한 줄을 토스트로 · 카드는 다시 누를 수 있고 창은 열어 둔다(조용히 삼키지 않음)."""
    out, srv = served
    rows = project_rows(out, [{"name": "laundry", "title": "세탁 앱"}])
    pg, errors = _open(ctx, srv.url, lambda p: mock_hub(p, srv, rows, fail={"/api/open": (500, "빌드 실패(build_ref.py 1): 일부러")}))
    try:
        url = pg.url
        pg.click("#pbtn")
        pg.wait_for_selector("#ppick .pk-card[data-name='laundry']")
        pg.click("#ppick .pk-card[data-name='laundry']")
        pg.wait_for_function("document.querySelector('#toast').textContent.includes('빌드 실패(build_ref.py 1): 일부러')")
        pg.wait_for_function("!document.querySelector(\"#ppick .pk-card[data-name='laundry']\").hasAttribute('aria-busy')")
        assert pg.is_visible("#ppick") and pg.url == url, "창은 열어 두고 이 탭은 그대로"
    finally:
        pg.close()
    assert not errors, errors


def test_new_project_asks_name_and_goes_there(served, ctx):
    out, srv = served
    rows = project_rows(out, [{"name": "n1", "title": "새 프로젝트 1"}])
    holder = {}
    pg, errors = _open(ctx, srv.url, lambda p: holder.update(calls=mock_hub(p, srv, rows)[0]))
    try:
        pg.click("#pbtn")
        pg.wait_for_selector("#ppick .pk-card[data-name='n1']")
        pg.click("#ppick .pk-new")
        assert pg.input_value("#ppick .pk-name") == "새 프로젝트 2", "기본 이름 = 쓰지 않은 가장 작은 번호"
        pg.keyboard.press("Escape")                                         # 이름 묻기만 거둔다 — 창은 그대로
        assert pg.query_selector("#ppick .pk-name") is None and pg.is_visible("#ppick")
        pg.click("#ppick .pk-new")
        pg.fill("#ppick .pk-name", "  세탁   앱 ")
        with pg.expect_navigation(url=lambda u: "to=new-1" in u):
            pg.keyboard.press("Enter")
        assert ("POST", "/api/new", {"title": "세탁 앱"}) in holder["calls"]
    finally:
        pg.close()
    assert not errors, errors


def test_header_home_button_and_project_title(served, ctx):
    out, srv = served
    holder = {}
    pg, errors = _open(ctx, srv.url, lambda p: holder.update(calls=mock_hub(p, srv, project_rows(out))[0]))
    try:
        pg.wait_for_function("document.querySelector('#title').textContent === '결제 흐름'")
        assert pg.evaluate("document.title") == "결제 흐름", "페이지 제목 = 프로젝트 제목"
        assert pg.query_selector("header .hdname .app") is None and pg.is_visible("#hhome"), "'hd' 표시 자리가 홈 단추"
        assert "홈" in pg.get_attribute("#hhome", "title")
        assert "전체 화면 한눈에 보기" not in pg.inner_text("header")
        with pg.expect_navigation(url=lambda u: "to=home" in u):
            pg.click("#hhome")
        assert ("GET", "/api/home", None) in holder["calls"]
    finally:
        pg.close()
    assert not errors, errors


def test_home_failure_is_told(served, ctx):
    out, srv = served
    pg, errors = _open(ctx, srv.url, lambda p: mock_hub(p, srv, project_rows(out), fail={"/api/home": (500, "홈 서버를 띄우지 못했어요")}))
    try:
        url = pg.url
        pg.click("#hhome")
        pg.wait_for_function("document.querySelector('#toast').textContent.includes('홈 서버를 띄우지 못했어요')")
        assert pg.url == url and pg.get_attribute("#hhome", "aria-busy") is None
    finally:
        pg.close()
    assert not errors, errors


def test_home_wait_is_told(served, ctx):
    """F17(10-31): 허브가 처음 뜨는 몇 초 동안 회색 아이콘만이 아니라 기다림 토스트 — 답이 오면(실패) 그 까닭으로 바뀐다."""
    out, srv = served
    held = []
    pg, errors = _open(ctx, srv.url, lambda p: (mock_hub(p, srv, project_rows(out)), p.route("**/api/home", lambda r: held.append(r))))
    try:
        pg.click("#hhome")
        pg.wait_for_function("(() => { const t = document.getElementById('toast'); return !t.hidden && t.textContent.includes('홈을 여는 중'); })()", timeout=3000)
        assert pg.get_attribute("#hhome", "aria-busy") == "true"
        pg.wait_for_timeout(2700)
        assert pg.is_visible("#toast") and "홈을 여는 중" in pg.text_content("#toast"), "기다리는 동안 토스트가 남는다(보통 토스트 2.6초보다 길게)"
        held[0].fulfill(status=500, content_type="application/json", body=json.dumps({"error": "홈 서버를 띄우지 못했어요"}, ensure_ascii=False))
        pg.wait_for_function("document.querySelector('#toast').textContent.includes('홈 서버를 띄우지 못했어요')")
    finally:
        pg.close()
    assert not errors, errors


def test_file_url_keeps_look_without_old_title(served, ctx):
    out, srv = served
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    try:
        for sel in ("#pbtn", "#ppick", "#hhome", "#ptabs"):
            assert pg.query_selector(sel) is None, f"file:// 로 열면 {sel} 가 없다"
        assert pg.is_visible("#wbtn") and pg.is_visible("header .hdname .app"), "다른 것은 그대로('hd' 표시 포함)"
        assert pg.text_content("#title") == "cur" and pg.evaluate("document.title") == "cur", "옛 기본 문구 대신 폴더 이름(out 이면 그 위)"
    finally:
        pg.close()
    assert not errors, errors


def test_one_page_load_asks_projects_once(served, ctx):
    """보드 전환 S2: 머리 제목·탭 바·주소 복사가 한 페이지 열기에 GET /api/projects 하나를 나눠 쓴다(modules/project-list.js) ·
    고르기 창은 열 때마다 새로 받는다."""
    out, srv = served
    holder = {}
    pg, errors = _open(ctx, srv.url, lambda p: holder.update(calls=mock_hub(p, srv, project_rows(out, [{"name": "laundry", "title": "세탁 앱"}]))[0]))
    try:
        pg.wait_for_function("document.querySelector('#title').textContent === '결제 흐름'")
        pg.wait_for_selector("#ptabs .pt-tab[data-name='cur']")
        pg.wait_for_timeout(500)                                            # 늦게 붙는 쪽(주소 복사)도 다 불렀을 때
        asked = lambda: [c for c in holder["calls"] if c[:2] == ("GET", "/api/projects")]
        assert len(asked()) == 1, holder["calls"]
        pg.click("#pbtn")
        pg.wait_for_selector("#ppick .pk-card[data-name='laundry']")
        assert len(asked()) == 2, "고르기 창 = 열 때 새로"
    finally:
        pg.close()
    assert not errors, errors
