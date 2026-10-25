"""프로젝트 상태 파일(#228) View — modules/view-state-sync.js 브라우저 테스트(도우미로 연 페이지)."""
import json

import pytest

from test_canvas_v2 import browser  # noqa: F401
from test_canvas_helper import out, _serve, _req  # noqa: F401
from test_canvas_edit import fit_view


@pytest.mark.area("helper", "notes")
def test_helper_memo_survives_reload_within_write_delay(browser, out):   # 300ms 쓰기 모음 안에 새로고침해도 메모가 남는다 — 닫을 때 보내기를 잃어도(쓰기 대기 표시로 다시 올림)
    import time
    from test_canvas_edit import fit_view, visible_cover
    srv = _serve(out)
    f = out / ".hd-canvas.json"
    errors, dropped, gate = [], [], {"old": True}

    def state():
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def drop_old_puts(route):                                           # 옛 페이지의 PUT(닫을 때 보내기 포함)이 새 페이지 GET 보다 늦게(또는 못) 닿는 경우를 고정
        if route.request.method == "PUT" and gate["old"]:
            dropped.append(1)
            return route.abort()
        return route.continue_()
    api = srv.url.split("/index.html")[0] + "/api/state"
    assert _req(api, "PUT", {"rev": 0, "state": {"hidden": []}}, srv.token) == (200, {"rev": 1}), "파일이 이미 있음(올리기 길이 아님)"
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        pg = c.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.route("**/api/state", drop_old_puts)
        fit_view(pg)
        pg.keyboard.press("m")
        cov = visible_cover(pg)
        pg.mouse.click(cov["x"], cov["y"])
        pg.wait_for_selector("#pop:not([hidden])")
        pg.fill("#pnote", "새로고침 직전 메모")
        pg.click("#padd")
        pg.on("framenavigated", lambda fr: fr == pg.main_frame and gate.update(old=False))
        pg.reload()                                                     # 300ms 가 지나기 전에
        pg.wait_for_function("window.__hdReady !== undefined")
        assert dropped, "옛 페이지의 PUT 은 버려졌다"
        assert pg.locator("#nlist li").count() == 1 and "새로고침 직전 메모" in pg.text_content("#nlist"), "보내지 못한 메모가 남는다"
        t0 = time.time()
        while time.time() - t0 < 5 and not any(n.get("note") == "새로고침 직전 메모" for n in (state().get("state") or {}).get("notes") or []):
            time.sleep(0.1)
        assert [n["note"] for n in state()["state"]["notes"]] == ["새로고침 직전 메모"], "다시 올려 파일에도 쓴다"
        t0 = time.time()
        while time.time() - t0 < 5 and pg.evaluate("Object.keys(localStorage).some(k => k.startsWith('hd-unsent:'))"):
            time.sleep(0.1)
        assert not pg.evaluate("Object.keys(localStorage).some(k => k.startsWith('hd-unsent:'))"), "파일에 닿으면 쓰기 대기 표시를 지운다"
    finally:
        c.close()
        srv.shutdown(); srv.server_close()
    assert not errors, errors


from test_canvas_v2 import ctx  # noqa: F401,E402
from test_canvas_replies_live import served, live, reply, file_notes  # noqa: F401,E402


@pytest.mark.area("helper", "notes", "tools")
def test_pending_card_move_survives_ai_reply(live):   # #269 — 모아 둔 카드 옮기기가 PUT 되기 전에 hd reply 가 rev 를 올려도(409) 옮기기와 답이 둘 다 파일에 남는다
    import time
    from test_canvas_edit import drag, visible_cover
    pg, puts = live, []

    def reply_first(route):                                             # 첫 PUT 이 닿기 직전에 AI 답 = 그 PUT 은 409
        if route.request.method == "PUT":
            puts.append(1)
            if len(puts) == 1:
                reply(pg, "m1", {"kind": "반영됨", "what": "버튼 키움", "screens": ["pay"], "captured": True})
        return route.continue_()
    pg.route("**/api/state", reply_first)
    pg.evaluate("window.__hdStay = 1")
    fit_view(pg)
    pg.keyboard.press("v")
    cov = visible_cover(pg)
    drag(pg, cov, 40, 0)
    f = pg.out / ".hd-canvas.json"
    t0, st = time.time(), {}
    while time.time() - t0 < 6:
        st = json.loads(f.read_text(encoding="utf-8"))["state"]
        if st.get("card-pos") and any(n.get("replies") for n in st.get("notes") or []):
            break
        pg.wait_for_timeout(100)                                        # route 처리는 Playwright 호출 안에서만 돈다(time.sleep 아님)
    assert st.get("card-pos", {}).get(cov["id"]), "옮긴 자리가 파일에 남는다"
    assert [len(n.get("replies") or []) for n in file_notes(pg) if n["id"] == "m1"] == [1], "AI 답도 파일에 남는다"
    assert len(puts) >= 2, "409 뒤 합쳐 다시 보냈다"
    assert pg.evaluate("window.__hdStay") == 1, "잃은 것이 없으니 다시 불러오지 않는다"


from test_canvas_replies_live import memo, seed, T_BTN, T_LEAD  # noqa: E402


def _seed(out, notes):
    """앞 테스트 탭이 닫히며 보낸 PUT 이 도우미에서 파일을 바꾸는 중이면(Windows 잠금) 잠깐 뒤 다시."""
    import time
    for i in range(30):
        try:
            return seed(out, notes)
        except PermissionError:
            time.sleep(0.1)
    seed(out, notes)


def _open(c, srv, errors, routes=()):
    pg = c.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    for pat, fn in routes:
        pg.route(pat, fn)
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    return pg


def _wait(pg, cond, ms=5000):
    t = 0
    while t < ms and not cond():
        pg.wait_for_timeout(100); t += 100
    return cond()


@pytest.mark.area("helper", "notes")
def test_done_notes_archived_then_removed_once(browser, served):
    """#273 — 열 때 30일 넘은 완료 메모만 POST /api/archive(도우미가 아직 없으면 mock) → {ok} 뒤에만 notes 에서 한 번 저장으로 뺀다. 묻기는 ?since=rev."""
    out, srv = served
    old = memo("m1", 1, T_BTN, "오래전 완료")
    old["replies"] = [{"kind": "반영됨", "what": "고침", "screens": ["pay"], "at": "2026-01-01T00:00:00Z"}]
    _seed(out, [old, memo("m2", 2, T_LEAD, "작업 중")])
    posts, gets, errors = [], [], []

    def arch(route):
        posts.append(json.loads(route.request.post_data))
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True, "count": 1}))
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        pg = _open(c, srv, errors, [("**/api/archive", arch)])
        pg.on("request", lambda r: "/api/state" in r.url and r.method == "GET" and gets.append(r.url))
        f = out / ".hd-canvas.json"
        ids = lambda: [n["id"] for n in json.loads(f.read_text(encoding="utf-8"))["state"]["notes"]]
        assert _wait(pg, lambda: ids() == ["m2"]), ids()
        assert [[n["id"] for n in p["notes"]] for p in posts] == [["m1"]], "완료 + 30일 넘은 것만, 한 번"
        assert _wait(pg, lambda: bool(gets)) and all("since=" in u for u in gets), gets
        pg.wait_for_timeout(2500)
        assert len(posts) == 1, "한 시간에 한 번"
    finally:
        c.close()
    assert not errors, errors


@pytest.mark.area("helper", "notes")
def test_archive_failure_keeps_notes(browser, served):
    out, srv = served
    old = memo("m1", 1, T_BTN, "오래전 완료")
    old["replies"] = [{"kind": "확인", "at": "2026-01-01T00:00:00Z"}]
    _seed(out, [old])
    errors, posts = [], []
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        pg = _open(c, srv, errors, [("**/api/archive", lambda r: (posts.append(1), r.fulfill(status=404, body="{}")))])
        assert _wait(pg, lambda: bool(posts))
        pg.wait_for_timeout(500)
        st = json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))
        assert [n["id"] for n in st["state"]["notes"]] == ["m1"] and st["rev"] == 1, "{ok} 없으면 아무것도 빼지 않는다"
    finally:
        c.close()
    assert not errors, errors


@pytest.mark.area("helper", "notes", "tools")
def test_too_big_toasts_once_and_waits_for_next_change(browser, served):
    """#273 — 413 = 도우미의 {error} 글을 한 번만 알리고, 다음 변경까지 다시 보내지 않는다."""
    from test_canvas_edit import drag, visible_cover
    out, srv = served
    _seed(out, [memo("m2", 2, T_LEAD, "작업 중")])
    puts, errors = [], []
    msg = "상태가 너무 커요(2.1 MB, 한도 2 MB) — 완료 메모를 보관으로 옮기세요"

    def big(route):
        if route.request.method != "PUT":
            return route.continue_()
        puts.append(1)
        route.fulfill(status=413, content_type="application/json", body=json.dumps({"error": msg}, ensure_ascii=False))
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        pg = _open(c, srv, errors, [("**/api/state", big)])
        pg.evaluate("""() => { window.__toasts = []; const t = document.getElementById('toast');
            new MutationObserver(rs => rs.forEach(() => window.__toasts.push(t.textContent))).observe(t, {childList: true}); }""")   # toast() 한 번 = 글 바꾸기 한 번
        fit_view(pg)
        pg.keyboard.press("v")
        cov = visible_cover(pg)
        drag(pg, cov, 40, 0)
        assert _wait(pg, lambda: len(puts) >= 1)
        pg.wait_for_timeout(4500)                                       # 묻기 두 번 지나도 다시 보내지 않는다
        assert len(puts) == 1, puts
        drag(pg, visible_cover(pg), 30, 0)                              # 다음 변경 = 다시 보냄, 알림은 한 번 그대로
        assert _wait(pg, lambda: len(puts) >= 2)
        pg.wait_for_timeout(300)
        assert [t for t in pg.evaluate("window.__toasts") if "MB" in t] == [msg], "도우미의 글 그대로, 두 번째 413 에는 다시 띄우지 않는다"
    finally:
        c.close()
    assert not errors, errors


@pytest.mark.area("helper", "notes", "tools")
def test_second_tab_is_read_only_until_take(browser, served):
    """#274 — 같은 out 을 연 두 탭: 새 탭은 '다른 탭에서 열려 있어요 — 여기서 편집하기' 줄 + PUT 없음. 누르면 그 탭이 쓰고 먼저 탭이 읽기만."""
    from test_canvas_edit import drag, visible_cover
    out, srv = served
    _seed(out, [memo("m2", 2, T_LEAD, "작업 중")])
    errors, puts = [], {"a": 0, "b": 0}

    def count(name):
        def fn(route):
            if route.request.method == "PUT":
                puts[name] += 1
            return route.continue_()
        return fn
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        a = _open(c, srv, errors, [("**/api/state", count("a"))])
        a.wait_for_timeout(300)
        b = _open(c, srv, errors, [("**/api/state", count("b"))])
        b.wait_for_selector("#hd-tab-lock:not([hidden])")
        assert "다른 탭에서 열려 있어요" in b.text_content("#hd-tab-lock")
        assert not a.locator("#hd-tab-lock").count() or a.locator("#hd-tab-lock").is_hidden(), "먼저 연 탭은 그대로 편집"
        a.evaluate("window.__hdStay = 1"); b.evaluate("window.__hdStay = 1")
        fit_view(b)
        b.keyboard.press("v")
        drag(b, visible_cover(b), 40, 0)                                # 읽기만인 탭의 편집 = 처음부터 막힘(V 가 안 먹어 손으로 판만 움직임) — 파일로 가지 않음
        b.wait_for_timeout(800)
        assert puts["b"] == 0, "읽기만인 탭은 PUT 하지 않는다"
        b.click("#hd-tab-lock button")                                  # 여기서 편집하기 — 막았으니 버린 쓰기가 없어 다시 불러오지 않는다
        a.wait_for_selector("#hd-tab-lock:not([hidden])")
        b.wait_for_timeout(400)
        assert b.evaluate("window.__hdStay") == 1, "버린 쓰기가 없으면 다시 불러오지 않는다"
        assert b.locator("#hd-tab-lock").is_hidden(), "가져간 탭이 쓴다"
        b.keyboard.press("v")
        before = puts["a"]
        drag(b, visible_cover(b), 40, 0)
        assert _wait(b, lambda: puts["b"] >= 1), "이제 이 탭이 쓴다"
        a.keyboard.press("v")                                           # 먼저 탭은 이제 읽기만 — V 도 끌기도 막힘
        drag(a, visible_cover(a), 30, 0)
        a.wait_for_timeout(800)
        assert puts["a"] == before, "가져간 뒤 먼저 탭은 PUT 하지 않는다"
    finally:
        c.close()
    assert not errors, errors


@pytest.mark.area("helper", "notes", "tools")
def test_read_only_tab_blocks_edits_up_front_and_keeps_draft(browser, served):
    """#274 후속 — 읽기만인 탭은 편집을 받아 놓고 버리지 않는다: 편집 도구·추가 단추는 흐리고 aria-disabled,
    누르거나 키를 쳐도 바뀌지 않고 '여기서 편집하기' 줄을 가리킨다. 열어 둔 메모 칸의 글은 남아 있다가 가져오면 그대로 추가된다."""
    from test_canvas_edit import visible_cover, tool
    out, srv = served
    _seed(out, [memo("m2", 2, T_LEAD, "작업 중")])
    errors, puts = [], {"a": 0, "b": 0}

    def count(name):
        def fn(route):
            if route.request.method == "PUT":
                puts[name] += 1
            return route.continue_()
        return fn
    toasts = """() => { window.__toasts = []; const t = document.getElementById('toast');
        new MutationObserver(() => window.__toasts.push(t.textContent)).observe(t, {childList: true, characterData: true, subtree: true}); }"""
    file_texts = lambda: [n.get("note") for n in json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"].get("notes", [])]
    c = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        a = _open(c, srv, errors, [("**/api/state", count("a"))])
        a.wait_for_timeout(300)
        a.evaluate("window.__hdStay = 1")
        fit_view(a)
        a.keyboard.press("m")                                           # 쓰는 탭에서 메모 칸을 열고 글을 쓴다
        cov = visible_cover(a)
        a.mouse.click(cov["x"], cov["y"])
        a.wait_for_selector("#pop:not([hidden])")
        a.fill("#pnote", "초안 남김")
        b = _open(c, srv, errors, [("**/api/state", count("b"))])
        b.wait_for_selector("#hd-tab-lock:not([hidden])")
        b.evaluate("window.__hdStay = 1"); b.evaluate(toasts)
        mv = b.locator('#tools [data-tool="move"]')
        assert mv.get_attribute("aria-disabled") == "true"
        assert float(mv.evaluate("e => getComputedStyle(e).opacity")) < 0.5, "흐리게 보인다"
        assert b.locator('#tools [data-tool="hand"]').get_attribute("aria-disabled") is None, "손(화면 이동)은 그대로"
        assert b.locator("#padd").get_attribute("aria-disabled") == "true"
        b.keyboard.press("v")
        mv.click(force=True)
        assert tool(b) == ["hand"], "읽기만인 탭은 편집 도구로 바뀌지 않는다"
        assert any("여기서 편집하기" in t for t in b.evaluate("window.__toasts")), "편집 시도 = 줄을 가리킨다"
        assert _wait(b, lambda: b.evaluate("!!(document.activeElement && document.activeElement.closest('#hd-tab-lock'))"), 1000), "줄의 단추로 초점"
        b.click("#hd-tab-lock button")                                  # B 가 가져감 — 버린 쓰기가 없으니 다시 불러오지 않는다
        a.wait_for_selector("#hd-tab-lock:not([hidden])")
        assert b.evaluate("window.__hdStay") == 1, "막았으니 버린 것이 없다 — 다시 불러오지 않음"
        assert a.evaluate("document.documentElement.dataset.hdTab") == "reader"
        assert tool(a) == ["hand"], "읽기만이 되면 편집 도구는 손으로"
        before = puts["a"]
        a.locator("#padd").click(force=True)                            # 읽기만인 탭의 추가 = 막힘, 글은 칸에
        a.focus("#pnote"); a.keyboard.press("Control+Enter")
        a.wait_for_timeout(500)
        assert a.is_visible("#pop") and a.input_value("#pnote") == "초안 남김", "쓴 글은 버리지 않는다"
        assert "초안 남김" not in file_texts() and puts["a"] == before
        a.click("#hd-tab-lock button")                                  # 다시 가져오면 그 칸 그대로 추가
        b.wait_for_selector("#hd-tab-lock:not([hidden])")
        assert a.evaluate("window.__hdStay") == 1
        assert a.locator("#padd").get_attribute("aria-disabled") is None, "쓰는 탭이 되면 막기를 걷는다"
        assert a.locator("#hd-tab-lock").is_hidden(), "쓰는 탭에는 줄이 없다"
        a.click("#padd")
        assert _wait(a, lambda: "초안 남김" in file_texts()), file_texts()
    finally:
        c.close()
    assert not errors, errors
