"""홈 화면(home.html, task 43) — Playwright. 허브(task 42) 없이 page.route 로 모든 /api/* 를 가짜로 답한다.

home 폴더를 작은 정적 서버로 내주고 `/?hd=tok` 로 연다. 확인: 카드(새 프로젝트 첫 칸·썸네일·상대 시각·실행 점·폴더 없음) ·
누르기 = 고르기 / 두 번·Enter = 열기(같은 탭 이동) · 키보드(화살표·Delete·F2·Ctrl+F) · 우클릭 메뉴 · 별표 · 찾기 · 휴지통(되돌리기·완전히 빼기) ·
없는 폴더 열기 → 목록에서 빼기 · 새 프로젝트 · 폴더 열기 · 스켈레톤 · 실패 띠 · 모든 요청에 X-HD-Token.
"""
import functools, http.server, json, os, threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

HERE = Path(__file__).resolve().parent
HOME = HERE.parent
SHOTS = Path(os.environ.get("HD_HOME_SHOTS", r"C:/Users/eungshin/AppData/Local/Temp/claude"))
TOKEN = "tok-123"
KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 10, 25, 15, 0, 0, tzinfo=KST)   # 페이지 시계도 이 때로 고정(자정 근처에 돌려도 같은 상대 시각)


def iso(**kw):
    return (NOW - timedelta(**kw)).isoformat(timespec="seconds")


THUMB_HTML = """<html><body style="margin:0;width:420px;height:260px;background:#f4f4f1;font:12px system-ui;display:flex;gap:14px;
align-items:center;justify-content:center">{cards}</body></html>"""


def thumb_png(page, hue):
    cards = "".join(
        f'<div style="width:80px;height:170px;border-radius:10px;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,.12);overflow:hidden">'
        f'<div style="height:34px;background:hsl({hue + i * 18},55%,{58 + i * 6}%)"></div>'
        f'<div style="margin:10px 8px;height:8px;border-radius:4px;background:#ddd"></div>'
        f'<div style="margin:6px 8px;height:8px;width:60%;border-radius:4px;background:#e6e6e6"></div>'
        f'<div style="margin:18px 8px;height:22px;border-radius:6px;background:hsl({hue},40%,88%)"></div></div>' for i in range(3))
    page.set_content(THUMB_HTML.format(cards=cards))
    return page.screenshot(clip={"x": 0, "y": 0, "width": 420, "height": 260})


def base_rows(port):
    t = lambda n: f"http://127.0.0.1:{port}/thumb/{n}.png?t=1"   # noqa: E731
    return [
        {"name": "laundry", "title": "세탁 예약 앱", "out": r"C:\runs\laundry\out", "state": "running", "url": "http://127.0.0.1:5001/index.html?hd=a",
         "pid": 11, "created": iso(days=9), "last_opened": iso(minutes=45), "starred": True, "trashed": None, "thumb": t("laundry")},
        {"name": "pay", "title": "결제 흐름 다시 그리기 — 아주 긴 제목이 말줄임으로 잘리는지 보는 카드", "out": r"C:\runs\pay\out", "state": "off", "url": None,
         "pid": None, "created": iso(days=12), "last_opened": iso(hours=3), "starred": False, "trashed": None, "thumb": t("pay")},
        {"name": "onboard", "title": "온보딩", "out": r"C:\runs\onboard\out", "state": "off", "url": None, "pid": None,
         "created": iso(days=20), "last_opened": iso(days=1, hours=1), "starred": False, "trashed": None, "thumb": t("onboard")},
        {"name": "gone", "title": "옮겨진 프로젝트", "out": r"C:\runs\gone\out", "state": "missing", "url": None, "pid": None,
         "created": iso(days=30), "last_opened": iso(days=4), "starred": False, "trashed": None, "thumb": None},
        {"name": "fresh", "title": "새 프로젝트 1", "out": r"C:\hd\projects\fresh\out", "state": "off", "url": None, "pid": None,
         "created": iso(days=2), "last_opened": None, "starred": False, "trashed": None, "thumb": None},
        {"name": "old", "title": "지난 시안", "out": r"C:\runs\old\out", "state": "off", "url": None, "pid": None,
         "created": iso(days=40), "last_opened": iso(days=8), "starred": True, "trashed": iso(hours=2), "thumb": t("old")},
        {"name": "older", "title": "버린 실험", "out": r"C:\runs\older\out", "state": "off", "url": None, "pid": None,
         "created": iso(days=60), "last_opened": iso(days=50), "starred": False, "trashed": iso(days=6), "thumb": None},
    ]


class Api:
    """가짜 허브 — 받은 요청을 calls 에 남기고 rows 를 바꾼다."""

    def __init__(self, port, thumbs):
        self.port, self.thumbs = port, thumbs
        self.rows = base_rows(port)
        self.calls, self.hold, self.held, self.fail_list, self.pick = [], False, [], False, {"cancel": True}

    def row(self, name):
        return next((r for r in self.rows if r["name"] == name), None)

    def handle(self, route, req):
        url = req.url.split("?")[0]
        path = "/" + url.split("/", 3)[3]
        if path.startswith("/thumb/"):
            name = path[len("/thumb/"):-4]
            if name in self.thumbs:
                return route.fulfill(status=200, content_type="image/png", body=self.thumbs[name])
            return route.fulfill(status=404, body="")
        body = json.loads(req.post_data) if req.post_data else None
        self.calls.append({"method": req.method, "path": path, "body": body, "token": req.headers.get("x-hd-token")})
        if req.headers.get("x-hd-token") != TOKEN:
            return self.json(route, {"error": "토큰이 맞지 않아요"}, 403)
        if path == "/api/projects":
            if self.hold:                                   # 답을 붙잡아 둔다 — 테스트가 스켈레톤을 본 뒤 release()
                self.held.append(route)
                return None
            if self.fail_list:
                return self.json(route, {"error": "목록 파일이 깨졌어요"}, 500)
            return self.json(route, self.rows)
        if path == "/api/open":
            r = self.row(body["name"])
            return self.json(route, {"name": r["name"], "url": f"http://127.0.0.1:{self.port}/opened/{r['name']}", "reused": False})
        if path == "/api/new":
            return self.json(route, {"name": "new-one", "url": f"http://127.0.0.1:{self.port}/opened/new-one?title={body.get('title', '')}"})
        if path == "/api/project":
            r = self.row(body["name"])
            if "title" in body:
                r["title"] = body["title"]
            if "starred" in body:
                r["starred"] = body["starred"]
            if "trashed" in body:
                r["trashed"] = iso(seconds=0) if body["trashed"] else None
            return self.json(route, {"row": r})
        if path == "/api/forget":
            r = self.row(body["name"])
            if not r["trashed"]:
                return self.json(route, {"error": "휴지통에 있는 것만 뺄 수 있어요"}, 409)
            self.rows.remove(r)
            return self.json(route, {"ok": True})
        if path == "/api/reveal":
            return self.json(route, {"ok": True})
        if path == "/api/pick-folder":
            if self.pick.get("name"):
                self.rows.append({"name": self.pick["name"], "title": "가져온 캔버스", "out": r"D:\x\out", "state": "off", "url": None, "pid": None,
                                  "created": iso(seconds=1), "last_opened": None, "starred": False, "trashed": None, "thumb": None})
            return self.json(route, self.pick)
        return self.json(route, {"error": "없는 경로"}, 404)

    def release(self):
        held, self.held, self.hold = self.held, [], False
        for r in held:
            if self.fail_list:
                self.json(r, {"error": "목록 파일이 깨졌어요"}, 500)
            else:
                self.json(r, self.rows)

    @staticmethod
    def json(route, data, status=200):
        route.fulfill(status=status, content_type="application/json; charset=utf-8", body=json.dumps(data, ensure_ascii=False))

    def posts(self, path):
        return [c["body"] for c in self.calls if c["method"] == "POST" and c["path"] == path]


@pytest.fixture(scope="module")
def static():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    h = functools.partial(Quiet, directory=str(HOME))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown(); srv.server_close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                b = p.chromium.launch(**kw)
                break
            except Exception as e:  # noqa: BLE001 — 다음 채널로
                last = e
        if b is None:
            pytest.skip(f"브라우저를 못 띄움: {last}")
        yield b
        b.close()


@pytest.fixture(scope="module")
def thumbs(browser):
    pg = browser.new_page()
    out = {n: thumb_png(pg, h) for n, h in (("laundry", 200), ("pay", 28), ("onboard", 150), ("old", 280))}
    pg.close()
    return out


@pytest.fixture
def home(browser, static, thumbs):
    ctx = browser.new_context(viewport={"width": 1280, "height": 820}, locale="ko-KR", timezone_id="Asia/Seoul")
    api = Api(static, thumbs)
    ctx.route("**/api/**", api.handle)
    ctx.route("**/thumb/**", api.handle)
    ctx.route("**/opened/**", lambda route, req: route.fulfill(status=200, content_type="text/html", body="<title>opened</title>열림"))
    pg = ctx.new_page()
    pg.clock.set_fixed_time(NOW)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    def go(section=None, wait=True):
        if section:
            pg.add_init_script(f"localStorage.setItem('hd-home-section', '{section}')")
        pg.goto(f"http://127.0.0.1:{static}/home.html?hd={TOKEN}")
        if wait:
            pg.wait_for_selector("#grid:not([aria-busy]) .card[data-key='new'], #grid:not([aria-busy]) .card[data-key]:not(.sk), #empty:not([hidden])")
        return pg
    yield pg, api, go, errors
    ctx.close()


def cards(pg):
    return pg.eval_on_selector_all("#grid .card[data-key]", "els => els.map(e => ({key: e.dataset.key, sel: e.getAttribute('aria-selected'), "
                                   "missing: e.classList.contains('missing'), name: (e.querySelector('.nm')||{}).textContent, "
                                   "meta: (e.querySelector('.mt')||{}).textContent, dot: !!e.querySelector('.dot'), img: !!e.querySelector('.th img'), "
                                   "star: (e.querySelector('.star')||{getAttribute(){return null}}).getAttribute('aria-pressed')}))")


def test_populated_home_cards_and_screenshot(home):
    pg, api, go, errors = home
    go("all")
    pg.wait_for_function("[...document.querySelectorAll('#grid .th img')].every(i => i.complete && i.naturalWidth > 0)")
    cs = cards(pg)
    assert [c["key"] for c in cs] == ["new", "laundry", "pay", "onboard", "fresh", "gone"], "+ 새 프로젝트가 첫 칸, 휴지통 것은 빼고 최근 것부터"
    by = {c["key"]: c for c in cs}
    assert by["laundry"]["dot"] and by["laundry"]["img"] and by["laundry"]["star"] == "true" and "45분 전" in by["laundry"]["meta"]
    assert "3시간 전" in by["pay"]["meta"] and "어제" in by["onboard"]["meta"]
    assert by["gone"]["missing"] and "폴더 없음" in by["gone"]["meta"] and not by["gone"]["img"]
    assert pg.text_content("#secTitle") == "모든 프로젝트" and pg.get_attribute(".nv[data-sec='all']", "aria-selected") == "true"
    w = pg.eval_on_selector(".card[data-key='laundry']", "e => e.getBoundingClientRect().width")
    assert 170 <= w <= 260, f"카드 폭 ~180px: {w}"
    assert pg.eval_on_selector(".card[data-key='pay'] .nm", "e => e.scrollWidth > e.clientWidth && getComputedStyle(e).textOverflow") == "ellipsis"
    assert pg.get_attribute(".card[data-key='pay'] .nm", "title").startswith("결제 흐름"), "긴 제목은 툴팁"
    assert all(c["token"] == TOKEN for c in api.calls), "모든 API 요청에 X-HD-Token"
    pg.click(".card[data-key='pay']")
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.mouse.move(5, 800)
    pg.screenshot(path=str(SHOTS / "hd-home-populated.png"))
    assert not errors, errors


def test_card_without_thumbnail_shows_initial(home):
    """F20(10-31): 썸네일이 아직 없거나(허브가 뒤에서 한 장 약 20초씩 찍는 중) 못 불러오면 빈 회색 상자 대신 이름 첫 글자."""
    pg, api, go, errors = home
    go("all")
    assert pg.text_content(".card[data-key='fresh'] .th .ph") == "새", "썸네일 없음 = 제목 첫 글자"
    pg.evaluate("document.querySelector(\".card[data-key='onboard'] .th img\").dispatchEvent(new Event('error'))")
    assert pg.text_content(".card[data-key='onboard'] .th .ph") == "온", "그림을 못 불러와도 같은 자리 표시"
    assert not errors, errors


def test_click_selects_double_click_and_enter_open(home):
    pg, api, go, errors = home
    go("recent")
    assert [c["key"] for c in cards(pg)] == ["new", "laundry", "pay", "onboard", "gone"], "최근 = 연 적 있는 것만"
    pg.click(".card[data-key='pay']")
    assert pg.get_attribute(".card[data-key='pay']", "aria-selected") == "true" and api.posts("/api/open") == [], "한 번 누르기 = 고르기만"
    pg.dblclick(".card[data-key='laundry']")
    pg.wait_for_url("**/opened/laundry")
    assert api.posts("/api/open") == [{"name": "laundry"}], "두 번 누르기 = 같은 탭에서 열기"
    go("recent")
    pg.click(".card[data-key='onboard']")
    pg.keyboard.press("Enter")
    pg.wait_for_url("**/opened/onboard")
    assert not errors, errors


def test_keyboard_move_delete_rename_and_search(home):
    pg, api, go, errors = home
    go("all")
    pg.keyboard.press("ArrowRight")
    assert pg.get_attribute(".card[data-key='new']", "aria-selected") == "true", "고른 것이 없으면 첫 칸"
    pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowRight")
    assert pg.get_attribute(".card[data-key='pay']", "aria-selected") == "true"
    pg.keyboard.press("ArrowLeft")
    assert pg.get_attribute(".card[data-key='laundry']", "aria-selected") == "true"
    ncol = pg.evaluate("getComputedStyle(document.querySelector('#grid')).gridTemplateColumns.split(' ').length")
    keys = [c["key"] for c in cards(pg)]
    pg.keyboard.press("ArrowDown")
    want = keys[1 + ncol] if 1 + ncol < len(keys) else keys[-1]       # 아래 줄에 그 열이 없으면 마지막 칸
    assert [c["key"] for c in cards(pg) if c["sel"] == "true"] == [want], "↓ = 다음 줄"
    pg.keyboard.press("ArrowUp")
    assert [c["key"] for c in cards(pg) if c["sel"] == "true"] == [keys[keys.index(want) - ncol]], "↑ = 윗줄 같은 열"
    pg.click(".card[data-key='laundry']")

    pg.keyboard.press("F2")                                          # 이름 바꾸기 — 같은 값·빈 값은 요청 없음
    pg.wait_for_selector(".card[data-key='laundry'] input.ren")
    pg.keyboard.press("Enter")
    assert api.posts("/api/project") == []
    pg.keyboard.press("F2")
    pg.fill(".card[data-key='laundry'] input.ren", "세탁 앱 v2")
    pg.keyboard.press("Enter")
    pg.wait_for_function("document.querySelector(\".card[data-key='laundry'] .nm\").textContent === '세탁 앱 v2'")
    assert api.posts("/api/project") == [{"name": "laundry", "title": "세탁 앱 v2"}]

    pg.keyboard.press("Delete")                                      # 휴지통으로 + 되돌리기 토스트
    pg.wait_for_selector(".card[data-key='laundry']", state="detached")
    assert api.posts("/api/project")[-1] == {"name": "laundry", "trashed": True}
    assert pg.get_attribute(".card[data-key='pay']", "aria-selected") == "true", "지운 자리의 다음 칸을 고른다"
    pg.click(".toast button:has-text('되돌리기')")
    pg.wait_for_selector(".card[data-key='laundry']")
    assert api.posts("/api/project")[-1] == {"name": "laundry", "trashed": False}

    pg.keyboard.press("Control+f")
    assert pg.evaluate("document.activeElement.id") == "q"
    pg.keyboard.type("ONBO")
    assert [c["key"] for c in cards(pg)] == ["new", "onboard"], "대소문자 무시, 이름으로도"
    pg.fill("#q", "없는것")
    assert pg.is_visible("#empty") and "‘없는것’와 맞는 프로젝트가 없어요" in pg.text_content("#empty")
    pg.keyboard.press("Escape")
    assert pg.input_value("#q") == "" and len(cards(pg)) == 6
    assert not errors, errors


def test_context_menu_star_and_reveal(home):
    pg, api, go, errors = home
    go("all")
    pg.click(".card[data-key='pay']", button="right")
    items = pg.eval_on_selector_all("#menu button", "bs => bs.map(b => b.textContent)")
    assert items == ["열기", "이름 바꾸기", "별표", "폴더 열기", "휴지통으로"]
    pg.click("#menu button[data-id='star']")
    pg.wait_for_selector(".card[data-key='pay'] .star[aria-pressed='true']")
    pg.click(".card[data-key='pay']", button="right")
    assert pg.text_content("#menu button[data-id='star']") == "별표 빼기"
    pg.click("#menu button[data-id='reveal']")
    pg.wait_for_function("document.querySelector('#menu').hidden")
    assert api.posts("/api/reveal") == [{"name": "pay"}]
    pg.click(".card[data-key='gone']", button="right")
    assert pg.is_disabled("#menu button[data-id='reveal']"), "폴더 없음 = 폴더 열기 못 누름"
    pg.keyboard.press("Escape")
    assert pg.is_hidden("#menu")
    pg.hover(".card[data-key='onboard']")                             # 카드 위 별 단추
    pg.click(".card[data-key='onboard'] .star")
    pg.wait_for_selector(".card[data-key='onboard'] .star[aria-pressed='true']")
    pg.click(".nv[data-sec='starred']")
    assert [c["key"] for c in cards(pg)] == ["new", "laundry", "pay", "onboard"]
    assert not errors, errors


def test_trash_section_restore_forget_and_screenshot(home):
    pg, api, go, errors = home
    go("trash")
    cs = cards(pg)
    assert [c["key"] for c in cs] == ["old", "older"], "휴지통 — 새 프로젝트 칸 없음, 넣은 때 최근 것부터"
    assert "2시간 전 휴지통으로" in cs[0]["meta"] and cs[0]["star"] is None
    pg.click(".card[data-key='old']")
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.mouse.move(5, 800)
    pg.screenshot(path=str(SHOTS / "hd-home-trash.png"))
    pg.dblclick(".card[data-key='old']")
    assert api.posts("/api/open") == [], "휴지통에서는 두 번 눌러도 열지 않는다"
    pg.click(".card[data-key='old']", button="right")
    assert pg.eval_on_selector_all("#menu button", "bs => bs.map(b => b.textContent)") == ["되돌리기", "목록에서 완전히 빼기"]
    pg.click("#menu button[data-id='restore']")
    pg.wait_for_selector(".card[data-key='old']", state="detached")
    assert api.posts("/api/project")[-1] == {"name": "old", "trashed": False}
    pg.click(".card[data-key='older']")
    pg.keyboard.press("Delete")                                       # 휴지통에서 Delete = 완전히 빼기(묻는다)
    assert pg.is_visible("#dlg") and "파일은 지우지 않아요" in pg.text_content("#dlgText")
    pg.click("#dlgNo")
    assert api.posts("/api/forget") == []
    pg.keyboard.press("Delete")
    pg.click("#dlgYes")
    pg.wait_for_selector("#empty:not([hidden])")
    assert api.posts("/api/forget") == [{"name": "older"}] and pg.text_content("#empty") == "휴지통이 비었어요"
    assert not errors, errors


def test_missing_open_offers_remove_from_list(home):
    pg, api, go, errors = home
    go("all")
    pg.dblclick(".card[data-key='gone']")
    pg.wait_for_selector(".toast.err:has-text('폴더가 없어요')")
    assert api.posts("/api/open") == [], "없는 폴더는 열기 요청을 보내지 않는다"
    pg.click(".toast button:has-text('목록에서 빼기')")
    pg.wait_for_selector(".card[data-key='gone']", state="detached")
    assert api.posts("/api/project") == [{"name": "gone", "trashed": True}] and api.posts("/api/forget") == [{"name": "gone"}]
    assert not errors, errors


def test_new_project_and_pick_folder(home):
    pg, api, go, errors = home
    go("all")
    api.pick = {"cancel": True}
    pg.click("#pickFolder")
    pg.wait_for_timeout(150)
    assert api.posts("/api/pick-folder") == [{}] and not pg.query_selector(".toast"), "취소 = 아무 일 없음"
    api.pick = {"name": "picked"}
    pg.click("#pickFolder")
    pg.wait_for_selector(".card[data-key='picked'][aria-selected='true']")
    api.pick = {"error": "캔버스 폴더가 아니에요"}
    pg.route("**/api/pick-folder", lambda route, req: Api.json(route, {"error": "캔버스 폴더가 아니에요 — index.html 이 없어요"}, 400))
    pg.click("#pickFolder")
    pg.wait_for_selector(".toast.err:has-text('캔버스 폴더가 아니에요')")
    pg.unroute("**/api/pick-folder")

    pg.click(".card[data-key='new']")
    assert pg.is_visible("#dlg") and pg.input_value("#dlgIn") == "새 프로젝트 2", "기본 이름 = 겹치지 않는 '새 프로젝트 N'"
    pg.keyboard.press("Escape")
    assert pg.is_hidden("#dlg") and api.posts("/api/new") == []
    pg.click(".card[data-key='new']")
    pg.fill("#dlgIn", "  가계부  ")
    pg.keyboard.press("Enter")
    pg.wait_for_url("**/opened/new-one*")
    assert api.posts("/api/new") == [{"title": "가계부"}]
    assert not errors, errors


def test_skeleton_then_error_banner_and_retry(home):
    pg, api, go, errors = home
    api.hold, api.fail_list = True, True
    go("all", wait=False)
    pg.wait_for_selector("#grid[aria-busy='true'] .card.sk")
    assert len(pg.query_selector_all(".card.sk")) == 8, "읽는 동안 스켈레톤 카드"
    for _ in range(50):
        if api.held:
            break
        pg.wait_for_timeout(20)
    api.release()
    pg.wait_for_selector("#banner:not([hidden]):has-text('목록 파일이 깨졌어요')")
    assert cards(pg) == [], "실패하면 빈 목록 문구가 아니라 실패 띠"
    api.fail_list = False
    pg.click("#banner button:has-text('다시 시도')")
    pg.wait_for_selector(".card[data-key='laundry']")
    assert pg.is_hidden("#banner")
    assert not errors, errors


def test_empty_sections_and_bad_token(home):
    pg, api, go, errors = home
    api.rows = []
    go("recent")
    assert [c["key"] for c in cards(pg)] == ["new"] and pg.text_content("#empty") == "최근에 연 프로젝트가 없어요"
    pg.click(".nv[data-sec='starred']")
    assert "별표한 프로젝트가 없어요" in pg.text_content("#empty")
    pg.goto(pg.url.replace(TOKEN, "wrong"))
    pg.wait_for_selector("#banner:not([hidden]):has-text('토큰이 맞지 않아요')")
    assert not errors, errors
