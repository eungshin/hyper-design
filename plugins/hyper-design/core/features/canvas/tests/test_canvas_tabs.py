"""아래쪽 프로젝트 탭 바(task 44, Xmind 시트 바) — 도우미로 연 캔버스 (Playwright).

도우미·임시 HD_HOME 은 test_canvas_projects 의 served 를 쓰고, task 42 라우트(/api/tabs·/api/project·/api/reveal·/api/open·/api/home)는
mock_hub(page.route)로 흉내 낸다. 탭 = GET /api/tabs 차례 + 지금 프로젝트(없으면 끝에 더하고 PUT 으로 남김) · 누르면 이 탭이 그 프로젝트로 ·
두 번 눌러 이름 바꾸기 · 메뉴(닫기·다른 탭 닫기·폴더 열기·홈) · 끌어 차례 바꾸기 · Ctrl+Shift+[ ] · 넘치면 ◀ ▶ ·
떠나기 직전의 상태 쓰기(카드 옮김)는 잃지 않는다.
"""
import json, time

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_projects import served, mock_hub, project_rows, _open  # noqa: F401

pytestmark = pytest.mark.area("menu", "helper")

EXTRA = [{"name": "laundry", "title": "세탁 앱"}, {"name": "gym", "title": "헬스장 예약"}]


def tab_list(pg):
    return pg.eval_on_selector_all("#ptabs .pt-tab", "els => els.map(e => [e.dataset.name, e.querySelector('.pt-name, .pt-in') ? "
                                   "(e.querySelector('.pt-name') || {}).textContent : '', e.getAttribute('aria-selected')])")


def opened(pg, served, tabs, rows=None, fail=None):
    out, srv = served
    holder = {}
    pg_, errors = _open(pg, srv.url, lambda p: holder.update(zip(("calls", "state"), mock_hub(p, srv, rows or project_rows(out, EXTRA), tabs, fail))))
    pg_.wait_for_selector("#ptabs .pt-tab")
    return pg_, errors, holder["calls"], holder["state"]


def test_tabs_follow_served_order_add_current_and_open_in_this_tab(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["gym", "nope", "laundry"])
    try:
        assert tab_list(pg) == [["gym", "헬스장 예약", "false"], ["laundry", "세탁 앱", "false"], ["cur", "결제 흐름", "true"]], \
            "받은 차례 · 모르는 이름은 빼고 · 지금 프로젝트는 끝에 더해 고른 탭으로"
        pg.wait_for_function("document.body.classList.contains('has-ptabs')")
        assert ("PUT", "/api/tabs", {"tabs": ["gym", "laundry", "cur"]}) in calls, "더한 차례를 남긴다"
        box, pane = pg.locator("#ptabs").bounding_box(), pg.locator("#screens").bounding_box()
        assert box["x"] - pane["x"] <= 16, "판 아래 왼쪽(S1b — 가운데는 대화창)"
        with pg.expect_navigation(url=lambda u: "to=laundry" in u):
            pg.click("#ptabs .pt-tab[data-name='laundry']")
        assert ("POST", "/api/open", {"name": "laundry"}) in calls and ctx.pages == [pg]
    finally:
        pg.close()
    assert not errors, errors


def test_rename_current_tab_in_place_updates_header(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["laundry", "cur"])
    try:
        pg.wait_for_function("document.querySelector('#title').textContent === '결제 흐름'")
        pg.dblclick("#ptabs .pt-tab[data-name='cur'] .pt-name")
        assert pg.evaluate("document.activeElement.className") == "pt-in"
        pg.keyboard.press("Escape")                                         # 취소 — 요청 없음
        pg.dblclick("#ptabs .pt-tab[data-name='cur'] .pt-name")
        pg.fill("#ptabs .pt-in", "   ")
        pg.keyboard.press("Enter")                                          # 빈 값 = 무시
        pg.dblclick("#ptabs .pt-tab[data-name='cur'] .pt-name")
        pg.fill("#ptabs .pt-in", " 결제  다시 ")
        pg.keyboard.press("Enter")
        pg.wait_for_function("document.querySelector('#title').textContent === '결제 다시'")
        assert [c for c in calls if c[1] == "/api/project"] == [("POST", "/api/project", {"name": "cur", "title": "결제 다시"})], "취소·빈 값은 보내지 않는다"
        assert tab_list(pg)[1][1] == "결제 다시" and pg.evaluate("document.title") == "결제 다시", "탭·머리·페이지 제목이 같이"
    finally:
        pg.close()
    assert not errors, errors


def test_rename_failure_reverts_and_tells(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["cur"], fail={"/api/project": (400, "이름이 너무 길어요")})
    try:
        pg.dblclick("#ptabs .pt-tab[data-name='cur'] .pt-name")
        pg.fill("#ptabs .pt-in", "새 이름")
        pg.keyboard.press("Enter")
        pg.wait_for_function("document.querySelector('#toast').textContent.includes('이름이 너무 길어요')")
        assert tab_list(pg) == [["cur", "결제 흐름", "true"]]
    finally:
        pg.close()
    assert not errors, errors


def test_menu_close_others_reveal_and_home(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["laundry", "cur", "gym"])
    try:
        pg.click("#ptabs .pt-tab[data-name='laundry']", button="right")
        assert pg.is_visible("#ptmenu")
        assert pg.eval_on_selector_all("#ptmenu .wm-row", "els => els.map(e => e.textContent)") == ["이름 바꾸기", "탭 닫기", "다른 탭 닫기", "폴더 열기", "홈"]
        pg.click("#ptmenu [data-do='close']")
        pg.wait_for_function("document.querySelectorAll('#ptabs .pt-tab').length === 2")
        assert state["tabs"] == ["cur", "gym"] and pg.url.find("to=") < 0, "다른 탭을 닫으면 바에서만 빠지고 여기 남는다"
        pg.hover("#ptabs .pt-tab[data-name='cur']")
        pg.click("#ptabs .pt-tab[data-name='cur'] .pt-more")                # ▾ 도 같은 메뉴
        pg.click("#ptmenu [data-do='reveal']")
        pg.wait_for_function("1")
        pg.click("#ptabs .pt-tab[data-name='cur']", button="right")
        pg.click("#ptmenu [data-do='others']")
        pg.wait_for_function("document.querySelectorAll('#ptabs .pt-tab').length === 1")
        assert state["tabs"] == ["cur"]
        pg.click("#ptabs .pt-tab[data-name='cur']", button="right")
        assert pg.is_disabled("#ptmenu [data-do='close']") and pg.is_disabled("#ptmenu [data-do='others']"), "하나뿐이면 닫을 수 없다"
        with pg.expect_navigation(url=lambda u: "to=home" in u):
            pg.click("#ptmenu [data-do='home']")
        assert ("POST", "/api/reveal", {"name": "cur"}) in calls and ("GET", "/api/home", None) in calls
    finally:
        pg.close()
    assert not errors, errors


def test_closing_current_tab_goes_to_neighbour(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["laundry", "cur", "gym"])
    try:
        pg.click("#ptabs .pt-tab[data-name='cur']", button="right")
        with pg.expect_navigation(url=lambda u: "to=gym" in u):
            pg.click("#ptmenu [data-do='close']")
        put = calls.index(("PUT", "/api/tabs", {"tabs": ["laundry", "gym"]}))   # 흉내 주소는 같은 캔버스라 다시 연 페이지가 cur 를 또 더한다 — 차례로 본다
        assert put < calls.index(("POST", "/api/open", {"name": "gym"})), "지금 탭을 닫으면 저장한 뒤 오른쪽 탭으로"
    finally:
        pg.close()
    assert not errors, errors


def test_drag_reorders_and_saves(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["laundry", "gym", "cur"])
    try:
        a = pg.locator("#ptabs .pt-tab[data-name='cur']").bounding_box()
        b = pg.locator("#ptabs .pt-tab[data-name='laundry']").bounding_box()
        pg.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
        pg.mouse.down()
        pg.mouse.move(a["x"] + a["width"] / 2 - 10, a["y"] + a["height"] / 2, steps=3)
        pg.mouse.move(b["x"] + 4, b["y"] + b["height"] / 2, steps=8)
        pg.mouse.up()
        pg.wait_for_function("document.querySelector('#ptabs .pt-tab').dataset.name === 'cur'")
        assert [t[0] for t in tab_list(pg)] == ["cur", "laundry", "gym"] and state["tabs"] == ["cur", "laundry", "gym"]
        assert pg.url.find("to=") < 0, "끌기는 열기가 아니다"
    finally:
        pg.close()
    assert not errors, errors


def test_shortcut_next_previous_tab(served, ctx):
    pg, errors, calls, state = opened(ctx, served, ["laundry", "cur", "gym"])
    try:
        with pg.expect_navigation(url=lambda u: "to=gym" in u):
            pg.keyboard.press("Control+Shift+BracketRight")
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_selector("#ptabs .pt-tab")
        with pg.expect_navigation(url=lambda u: "to=laundry" in u):
            pg.keyboard.press("Control+Shift+BracketLeft")
    finally:
        pg.close()
    assert not errors, errors


def test_overflow_shows_arrows(served, ctx):
    out, srv = served
    many = [{"name": f"p{i}", "title": f"아주 긴 프로젝트 이름 {i}번"} for i in range(24)]
    pg, errors, calls, state = opened(ctx, served, [m["name"] for m in many], rows=project_rows(out, many))
    try:
        pg.wait_for_function("!document.querySelector('#ptabs .pt-arrow[data-dir=\"1\"]').hidden")
        assert pg.is_visible("#ptabs .pt-arrow[data-dir='-1']")
        assert pg.evaluate("document.querySelector('#ptabs .pt-strip').scrollLeft") > 0, "지금 탭(끝)이 보이게 밀어 둔다"
        assert pg.is_disabled("#ptabs .pt-arrow[data-dir='1']") and not pg.is_disabled("#ptabs .pt-arrow[data-dir='-1']"), "끝이면 그쪽 화살표는 끈다"
        pg.click("#ptabs .pt-arrow[data-dir='-1']")
        pg.wait_for_function("!document.querySelector('#ptabs .pt-arrow[data-dir=\"1\"]').disabled")
        box, chat, pane = (pg.locator(s).bounding_box() for s in ("#ptabs", "#hdchat", "#screens"))
        assert box["x"] - pane["x"] <= 16 and (box["x"] + box["width"] <= chat["x"] - 11 or box["y"] + box["height"] <= chat["y"]), \
            "넘쳐도 바는 판 아래 왼쪽에서 가운데 대화창 앞까지(아주 좁으면 대화창이 위로 비킨다)"
    finally:
        pg.close()
    assert not errors, errors


def test_leaving_by_tab_keeps_pending_state_write(served, ctx):
    """카드를 옮긴 직후(300ms 모으기 전) 다른 탭으로 가도 옮긴 자리가 상태 파일에 남는다 — 떠날 때 view-state-sync 가 keepalive 로 마저 보낸다."""
    from test_canvas_edit import drag, visible_cover, fit_view
    out, srv = served
    pg, errors, calls, state = opened(ctx, served, ["laundry", "cur"])
    try:
        fit_view(pg)
        pg.keyboard.press("v")
        cov = visible_cover(pg)
        pg.mouse.move(cov["x"], cov["y"])
        pg.mouse.down()
        pg.mouse.move(cov["x"] + 60, cov["y"] + 20, steps=6)
        pg.mouse.up()
        with pg.expect_navigation(url=lambda u: "to=laundry" in u):
            pg.click("#ptabs .pt-tab[data-name='laundry']")
        f, st, t0 = out / ".hd-canvas.json", {}, time.time()
        while time.time() - t0 < 5:
            if f.exists():
                st = json.loads(f.read_text(encoding="utf-8"))["state"]
                if (st.get("card-pos") or {}).get(cov["id"]):
                    break
            pg.wait_for_timeout(100)
        assert (st.get("card-pos") or {}).get(cov["id"]), "옮긴 자리가 파일에 남는다"
    finally:
        pg.close()
    assert not errors, errors
