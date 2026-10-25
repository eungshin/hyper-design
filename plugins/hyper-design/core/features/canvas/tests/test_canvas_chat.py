"""하단 대화창 v0(S1) — 브라우저. 도우미로 연 캔버스(받는 곳 없음 = 대기열 .hd-queue, 실제 Paseo 없음).

카드 칩: 카드를 고르면 [결제] 칩 → 글 + Enter = 메모 하나 + 바로 보내기(위쪽 [보내기]와 같은 길) → 대기열 파일에 지금 요청문 형식, 입력창 비움, 상태 줄.
요소 칩: 고른 카드를 이동(V)으로 한 번 더 = 요소 막대 → [BUTTON "지금 결제하기"] 칩 → 보낸 요청문의 path 가 그 요소.
규칙(칩·범위·메모 초안·상태 말)은 test_canvas_unit_chat.py(unit).
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, zoom_to  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("chat")
SHOTS = Path(os.environ.get("HD_SHOTS_S1", Path(tempfile.gettempdir()) / "claude" / "tS1"))


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def _serve(ctx, setup=None):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-chat-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.out, pg.calls = out, []
    if setup:
        setup(pg)
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")

    def done():
        pg.close()
        srv.shutdown(); srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)
    return pg, errors, done


@pytest.fixture()
def live(ctx):
    pg, errors, done = _serve(ctx)
    yield pg
    done()
    assert not errors, errors


AGENTS = [{"id": "ag-run", "name": "결제 고치는 에이전트", "status": "running", "cwd": "/r"},
          {"id": "ag-idle", "name": "쉬는 에이전트", "status": "idle", "cwd": "/r/sub"}]


def mock_hub(pg, tabs=("cur", "laundry")):
    """도우미 라우트 흉내(page.route): 탭·프로젝트 목록과 보낼 곳(/api/agents · /api/attach · /api/forward).
    실제 Paseo·실제 ~/.hyper-design 은 건드리지 않는다 — 받은 요청은 pg.calls 에 (method, path?query, body)."""
    state = {"agent": None}
    rows = [{"name": "cur", "title": "결제 흐름", "out": pg.out.resolve().as_posix(), "state": "running", "url": "http://x/", "pid": 1,
             "created": "2026-10-20T10:00:00+09:00", "last_opened": "2026-10-23T09:00:00+09:00", "starred": False, "trashed": None, "thumb": None},
            {"name": "laundry", "title": "레이아웃", "out": "/tmp/laundry/out", "state": "off", "url": None, "pid": None,
             "created": "2026-10-01T10:00:00+09:00", "last_opened": "2026-10-02T11:30:00+09:00", "starred": False, "trashed": None, "thumb": None}]

    def handle(route):
        q = route.request
        full = "/" + q.url.split("://", 1)[1].split("/", 1)[1]
        path = full.split("?", 1)[0]
        body = json.loads(q.post_data) if q.post_data else None
        pg.calls.append((q.method, full, body))
        if path == "/api/tabs":
            res = {"tabs": list(tabs)}
        elif path == "/api/projects":
            res = rows if tabs else []
        elif path == "/api/agents":
            res = {"skipped": True, "agents": []} if "auto=1" in full else {"agents": AGENTS, "current": state["agent"], "repo": "/r"}
        elif path == "/api/attach":
            state["agent"] = body.get("agent")
            res = {"agent": state["agent"]}
        elif path == "/api/forward":
            res = {"via": "paseo" if state["agent"] else "queue", "agent": state["agent"], "path": "mock"}
        else:
            return route.continue_()
        return route.fulfill(status=200, content_type="application/json", body=json.dumps(res, ensure_ascii=False))

    pg.route("**/api/**", handle)


@pytest.fixture()
def hub(ctx):
    pg, errors, done = _serve(ctx, mock_hub)
    yield pg
    done()
    assert not errors, errors


@pytest.fixture()
def hub_notabs(ctx):
    pg, errors, done = _serve(ctx, lambda p: mock_hub(p, tabs=()))
    yield pg
    done()
    assert not errors, errors


def queued(pg):
    pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
    assert pg.evaluate("window.__hdLastHelper.forward.via") == "queue"
    q = list((pg.out / ".hd-queue").glob("*.txt"))
    assert len(q) == 1, q
    return q[0].read_text(encoding="utf-8")


def chips(pg):
    return pg.locator("#hdchat .ch-chip").all_text_contents()


def card_click(pg, sid):
    b = pg.locator(f'.card[data-id="{sid}"] .cover').bounding_box()
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + 30)


def test_card_chip_send_makes_memo_and_forwards(live):
    pg = live
    pg.keyboard.press("0")
    pg.wait_for_selector("#hdchat .ch-box")
    box, tabs = pg.locator("#hdchat").bounding_box(), pg.locator("#ptabs").bounding_box() if pg.is_visible("#ptabs") else None
    vw = pg.viewport_size
    assert box["y"] + box["height"] <= vw["height"] and abs((box["x"] + box["width"] / 2) - vw["width"] / 2) < vw["width"] * 0.3, "판 아래 가운데"
    if tabs:
        assert box["x"] >= tabs["x"] + tabs["width"] or box["y"] + box["height"] <= tabs["y"], "아래 프로젝트 탭을 가리지 않는다"
    assert pg.get_attribute("#hdchat textarea", "placeholder") == "무엇을 바꾸거나 만들까요?"
    assert chips(pg) == ["모든 화면"], "고른 것이 없으면 모든 화면"
    shot(pg, "s1-empty.png")

    pg.keyboard.press("v")
    card_click(pg, "pay")
    pg.wait_for_function("document.querySelectorAll('#hdchat .ch-chip').length && document.querySelector('#hdchat .ch-chip').textContent.startsWith('결제')")
    assert [c.replace("×", "") for c in chips(pg)] == ["결제"]
    pg.click("#hdchat textarea")
    pg.keyboard.type("버튼을 더 크게")
    pg.keyboard.press("Shift+Enter")
    pg.keyboard.type("색은 그대로")
    assert pg.input_value("#hdchat textarea") == "버튼을 더 크게\n색은 그대로", "Shift+Enter = 줄바꿈"
    shot(pg, "s1-chips.png")
    pg.keyboard.press("Enter")
    text = queued(pg)
    assert "1. screen=pay · path=body · no=1" in text and "요청: 버튼을 더 크게" in text and "범위: 이 화면 전체" in text, text
    assert pg.input_value("#hdchat textarea") == "", "보내면 입력창을 비운다"
    pg.wait_for_function("(() => { const l = document.querySelector('#hdchat .ch-line'); return l && !l.hidden && /보냄|대기열/.test(l.textContent); })()", timeout=5000)
    line = pg.text_content("#hdchat .ch-line")
    assert pg.evaluate("document.querySelector('#hdchat .ch-line').classList.contains('pulse')"), "새 줄 = 맥박 한 번"
    assert "버튼을 더 크게" in line and ("보냄" in line or "대기열" in line), line
    assert pg.evaluate("document.querySelector('.card[data-id=\"pay\"]').classList.contains('picked')"), "보낸 뒤에도 고른 카드·캔버스 그대로"
    # 칩 빼기 = 모든 화면으로 넓어짐
    pg.click("#hdchat .ch-chip button")
    assert chips(pg) == ["모든 화면"]
    shot(pg, "s1-after-send.png")


def test_element_chip_puts_element_path_in_request(live):
    pg = live
    ph = zoom_to(pg, "pay", 420)
    fr = None
    for _ in range(100):
        f = pg.query_selector('.card[data-id="pay"] .phone iframe')
        fr = f and f.content_frame()
        if fr and fr.url.split("?")[0].endswith("/pay.html"):
            break
        pg.wait_for_timeout(100)
    fr.wait_for_selector("button.pay", state="attached", timeout=5000)
    r = fr.evaluate("() => { const b = document.querySelector('button.pay').getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }")
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    xy = (ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc)
    pg.keyboard.press("v")
    pg.mouse.click(*xy)
    pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(*xy)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    pg.wait_for_selector("#hdchat .ch-chip.el", timeout=3000)
    el = pg.locator("#hdchat .ch-chip.el")
    assert el.text_content().replace("×", "") == 'BUTTON "지금 결제하기"'
    path = el.get_attribute("data-key").split(":", 2)[2]
    shot(pg, "s1-element-chip.png")
    assert "button.pay" in path
    pg.click("#hdchat textarea")
    pg.keyboard.type("문구를 '결제하기'로")
    pg.click("#hdchat .ch-send")
    text = queued(pg)
    assert f"screen=pay · path={path}" in text and "요청: 문구를 '결제하기'로" in text and "범위:" not in text, text
    assert text.count("screen=") == 1, "요소 칩이 있으면 그 화면의 화면 메모는 따로 나가지 않는다"


def _rect(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); if (!e || !e.offsetParent && getComputedStyle(e).position !== 'fixed' || e.hidden) return null;"
                       " const r = e.getBoundingClientRect(); return r.width && r.height ? {l: r.left, t: r.top, r: r.right, b: r.bottom} : null; }", sel)


def _hit(a, b):
    return a and b and a["l"] < b["r"] and b["l"] < a["r"] and a["t"] < b["b"] and b["t"] < a["b"]


TS1B = Path(os.environ.get("HD_SHOTS_S1B", Path(tempfile.gettempdir()) / "claude" / "ts1b"))


def shot1b(pg, name):
    TS1B.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(TS1B / name))


def _size(pg, width):
    pg.set_viewport_size({"width": width, "height": 900 if width < 2000 else 1600})
    pg.evaluate("dispatchEvent(new Event('resize'))")
    pg.wait_for_timeout(150)


@pytest.mark.parametrize("width", [1280, 2880])
def test_tabs_bottom_left_chat_centred_no_hint(hub, width):
    """S1b: 아래 왼쪽 단축키 안내(#khint)는 없다 · 프로젝트 탭 바는 판 아래 왼쪽 · 대화창은 판(도크 왼쪽) 가운데 그대로 · 서로 가리지 않는다."""
    pg = hub
    _size(pg, width)
    pg.wait_for_selector("#ptabs .pt-tab")
    pg.wait_for_timeout(150)
    assert pg.locator("#khint").count() == 0, "단축키 안내 줄은 지웠다"
    chat, tabs, pane = _rect(pg, "#hdchat"), _rect(pg, "#ptabs"), _rect(pg, "#screens")
    assert chat and tabs and pane, (chat, tabs, pane)
    assert tabs["l"] - pane["l"] <= 16 and pane["b"] - tabs["b"] <= 16, f"탭 바는 판 아래 왼쪽 {tabs} {pane}"
    assert abs((chat["l"] + chat["r"]) / 2 - (pane["l"] + pane["r"]) / 2) <= 2, f"대화창은 판 가운데 {chat} {pane}"
    assert not _hit(chat, tabs), f"대화창이 탭을 가린다 {chat} {tabs}"
    assert chat["b"] <= pg.viewport_size["height"]
    assert abs(chat["b"] - tabs["b"]) <= 4, "자리가 있으면 같은 아래 줄 — 대화창이 탭 위로 올라가지 않는다"
    assert pg.is_hidden("#ptabs .pt-arrow[data-dir='1']"), "탭 두 개는 ◀ ▶ 없이 다 보인다(대화창이 폭을 줄여 자리를 준다)"
    shot1b(pg, f"s1b-shown-tabs-{width}.png")


@pytest.mark.parametrize("width", [1280, 2880])
def test_chat_centred_without_tabs(hub_notabs, width):
    pg = hub_notabs
    _size(pg, width)
    pg.wait_for_timeout(300)
    assert _rect(pg, "#ptabs") is None and pg.locator("#khint").count() == 0
    chat, pane = _rect(pg, "#hdchat"), _rect(pg, "#screens")
    assert abs((chat["l"] + chat["r"]) / 2 - (pane["l"] + pane["r"]) / 2) <= 2 and pane["b"] - chat["b"] <= 16, (chat, pane)
    shot1b(pg, f"s1b-shown-notabs-{width}.png")


@pytest.mark.parametrize("width", [1280, 2880])
def test_hide_chat_button_and_window_menu_persist(hub, width):
    """S1b: 대화창 숨기기 단추 · 창 메뉴 '대화창' 체크(보이기/숨기기) · 새로고침 뒤에도 그대로 · 숨기면 자리를 차지하지 않는다.
    Tab(패널 모두 숨기기)은 대화창도 숨기고 다시 Tab 이면 돌아온다 — 대화창 설정은 그대로."""
    pg = hub
    _size(pg, width)
    pg.wait_for_selector("#ptabs .pt-tab")
    narrow = _rect(pg, "#ptabs")
    assert pg.is_visible("#hdchat .ch-hide")
    pg.click("#hdchat .ch-hide")
    pg.wait_for_selector("#hdchat", state="hidden")
    assert _rect(pg, "#hdchat") is None, "숨기면 자리도 없다"
    pg.click("#wbtn")
    row = pg.locator('#wmenu [data-w="chat"]')
    assert row.get_attribute("aria-checked") == "false" and "대화창" in row.text_content()
    assert pg.locator('#wmenu [data-w="hint"]').count() == 0, "판 아래 안내 항목은 없다(지웠다)"
    shot1b(pg, f"s1b-hidden-menu-{width}.png")
    assert _rect(pg, "#ptabs")["r"] >= narrow["r"], "탭 바는 대화창 자리까지 쓸 수 있다"
    pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.wait_for_timeout(300)
    assert pg.is_hidden("#hdchat"), "숨김은 새로고침 뒤에도"
    pg.click("#wbtn")
    pg.click('#wmenu [data-w="chat"]')
    pg.wait_for_selector("#hdchat .ch-box", state="visible")
    assert pg.get_attribute('#wmenu [data-w="chat"]', "aria-checked") == "true"
    pg.keyboard.press("Escape")
    pg.mouse.click(5, 300)
    pg.keyboard.press("Tab")
    pg.wait_for_selector("#hdchat", state="hidden")
    pg.keyboard.press("Tab")
    pg.wait_for_selector("#hdchat .ch-box", state="visible")


@pytest.mark.parametrize("width", [1280, 2880])
def test_chat_target_chip_opens_same_picker(hub, width):
    """S1b: 대화창 [보내기] 옆 받는 곳 칩 = 위쪽 받는 곳 칩과 같은 글 · 누르면 같은 메뉴(#amenu, 가짜 /api/agents) ·
    고르면 두 칩이 함께 바뀐다(진실 하나 = 도우미 attach → view-sync). 실제 Paseo 에는 보내지 않는다(라우트 흉내)."""
    pg = hub
    _size(pg, width)
    chip = pg.locator("#hdchat .ch-agent")
    pg.wait_for_selector("#hdchat .ch-agent:not([hidden])")
    assert "받는 곳 없음" in chip.text_content() and "받는 곳 없음" in pg.text_content("#aichip")
    chip.click()
    pg.wait_for_selector("#amenu .ag-row[data-id='ag-run']")
    m, c = _rect(pg, "#amenu"), _rect(pg, "#hdchat .ch-agent")
    assert m["b"] <= c["t"] + 1 and m["t"] >= 0, f"메뉴는 칩 위로 펼친다 {m} {c}"
    assert pg.get_attribute("#hdchat .ch-agent", "aria-expanded") == "true"
    shot1b(pg, f"s1b-agent-picker-{width}.png")
    pg.click("#amenu .ag-row[data-id='ag-run']")
    pg.wait_for_selector("#amenu", state="hidden")
    pg.wait_for_function("document.querySelector('#hdchat .ch-agent').textContent.includes('결제 고치는 에이전트')")
    assert "결제 고치는 에이전트" in pg.text_content("#aichip"), "위쪽 칩도 같이"
    assert ("POST", "/api/attach", {"agent": "ag-run"}) in pg.calls
    pg.click("#aichip")                                  # 위쪽 칩으로 바꿔도 대화창 칩이 따라온다
    pg.wait_for_selector("#amenu .ag-row.ag-none")
    pg.click("#amenu .ag-row.ag-none")
    pg.wait_for_function("document.querySelector('#hdchat .ch-agent').textContent.includes('받는 곳 없음')")
    assert not [x for x in pg.calls if x[1].startswith("/api/forward")], "고르기만 — 보내지 않는다"
