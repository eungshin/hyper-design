"""프로젝트 메뉴(#246 view, task 24) — 도우미로 연 캔버스의 위쪽 줄 '프로젝트 ▾' (Playwright).

임시 HD_HOME 에 프로젝트 두 개(지금 캔버스 · out 이 없어진 것) + 이 프로세스 안 도우미의 표지(write_marker) — 그래서 /api/projects 와
/api/open 은 진짜 라우트(가짜 답 없음): 지금 캔버스는 '열림'·'지금', 없어진 것은 못 누르고 까닭을 적고, 누르면 /api/open → 받은 주소가 새 탭.
file:// 로 열면(도우미 없음) 단추가 없다.
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


def _open(ctx, url):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(url)
    pg.wait_for_function("window.__hdReady !== undefined")
    return pg, errors


def test_projects_menu_lists_marks_and_opens(served, ctx):
    out, srv = served
    pg, errors = _open(ctx, srv.url)
    try:
        assert pg.is_visible("#pbtn") and pg.text_content("#pbtn").startswith("프로젝트"), "도우미로 열면 위쪽 줄에 '프로젝트' 단추"
        pg.click("#pbtn")
        pg.wait_for_selector("#pmenu .pj-row[data-name='gone']")
        rows = pg.eval_on_selector_all("#pmenu .pj-row", "els => els.map(e => ({name: e.dataset.name, state: e.dataset.state, "
                                       "cur: e.getAttribute('aria-current'), dis: e.disabled, text: e.innerText}))")
        assert [r["name"] for r in rows] == ["cur", "gone"], "목록 차례 그대로(최근 연 것부터)"
        cur, gone = rows
        assert cur["state"] == "open" and cur["cur"] == "true" and not cur["dis"] and "열림" in cur["text"] and "지금" in cur["text"], cur
        assert "10-23 09:00" in cur["text"], "연 때"
        assert gone["state"] == "missing" and gone["dis"] and "없음" in gone["text"] and "out 폴더가 없어" in gone["text"], gone

        pg.click("#pmenu .pj-row[data-name='gone']", force=True)   # 못 누르는 줄 — 아무 요청도, 새 탭도 없다
        assert pg.get_attribute("#pmenu .pj-row[data-name='gone']", "aria-busy") is None and len(ctx.pages) == 1

        with pg.expect_request(lambda q: q.url.endswith("/api/open") and q.method == "POST") as req, ctx.expect_page() as pop:
            pg.click("#pmenu .pj-row[data-name='cur']")
        assert json.loads(req.value.post_data) == {"name": "cur"}
        tab = pop.value
        tab.wait_for_url(srv.url, timeout=10000)
        assert tab.url == srv.url, "도우미가 준 주소가 새 탭으로"
        pg.wait_for_selector("#pmenu", state="hidden")
        tab.close()
    finally:
        pg.close()
    assert not errors, errors


def test_open_failure_shows_helper_line(served, ctx):
    """도우미가 오류를 답하면 그 한 줄을 토스트로 · 열어 둔 빈 탭은 닫는다(조용히 삼키지 않음) — 실패 답만 가로챈다."""
    out, srv = served
    pg, errors = _open(ctx, srv.url)
    try:
        pg.route("**/api/open", lambda route: route.fulfill(status=500, content_type="application/json",
                                                            body=json.dumps({"error": "빌드 실패(build_ref.py 1): 일부러"}, ensure_ascii=False)))
        pg.click("#pbtn")
        pg.wait_for_selector("#pmenu .pj-row[data-name='cur']")
        with ctx.expect_page() as pop:
            pg.click("#pmenu .pj-row[data-name='cur']")
        tab = pop.value
        pg.wait_for_function("document.querySelector('#toast').textContent.includes('빌드 실패(build_ref.py 1): 일부러')")
        pg.wait_for_function("!document.querySelector(\"#pmenu .pj-row[data-name='cur']\").hasAttribute('aria-busy')")
        if not tab.is_closed():
            tab.wait_for_event("close", timeout=5000)     # 실패하면 열어 둔 빈 탭을 닫는다
        assert pg.is_visible("#pmenu"), "메뉴는 열어 둔다(다시 누를 수 있게)"
    finally:
        pg.close()
    assert not errors, errors


def test_no_projects_entry_without_helper(served, ctx):
    out, srv = served
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    try:
        assert pg.query_selector("#pbtn") is None and pg.query_selector("#pmenu") is None, "file:// 로 열면 단추가 없다"
        assert pg.is_visible("#wbtn"), "다른 것은 그대로"
    finally:
        pg.close()
    assert not errors, errors
