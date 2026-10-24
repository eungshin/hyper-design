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
