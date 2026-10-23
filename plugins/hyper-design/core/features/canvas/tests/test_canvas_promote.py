"""빈 레이아웃 승격(#241 R2 · task 23) — 도우미로 연 캔버스, `hd reply` 와 같은 길(POST /api/reply)로 빈 레이아웃 메모에 반영됨 답 (Playwright).

빈 레이아웃(메모 하나 · 들어오는 잇기 · 폴더) → 답 screens=[done] → 새로고침 없이 빈 카드가 사라지고 done 카드가 그 자리에,
메모는 done 으로(묶음에 '옮겨 왔어요' 줄) · 잇기 도착 = done · 폴더 자리 = done · 알림 [되돌리기] 한 번 = 빈 카드·자리·잇기 그대로.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_edit import fit_view
from test_canvas_annotations import PAY, DONE, show_sent

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

LAYOUT = {"id": "L1", "no": 1, "screen": "new-ab", "targets": [{"path": "(새 화면)", "text": "빈 레이아웃", "rect": None}], "path": "(새 화면)",
          "text": "빈 레이아웃", "rect": None, "intent": "change", "sent": True, "edit": "new-screen", "op": "new", "to": "", "value": "쿠폰",
          "purpose": "쿠폰을 고른다", "x": 900, "y": 0, "replies": [], "note": '새 화면 "쿠폰"(new-ab)을 빈 레이아웃으로 만들기'}
LMEMO = {"id": "L1m", "no": 2, "screen": "new-ab", "targets": [{"path": "body", "text": "쿠폰", "rect": None}], "path": "body", "text": "쿠폰",
         "rect": None, "note": "쿠폰 목록과 적용 버튼", "intent": "change", "sent": True, "replies": []}
LINK = {"id": "K1", "no": 1, "screen": "pay", "targets": [{"path": "button.pay", "text": "지금 결제하기", "rect": None}], "path": "button.pay",
        "text": "지금 결제하기", "rect": None, "note": '이 요소를 누르면 "쿠폰"(new-ab) 화면으로 가게 연결', "intent": "change", "sent": True,
        "edit": "link", "op": "link", "to": "new-ab", "replies": []}
FOLDERS = {"v": 1, "folders": [{"id": "f1", "name": "쿠폰 묶음", "ids": ["new-ab"], "open": True}]}


@pytest.fixture()
def live(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-promote-"))
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
    (out / ".hd-canvas.json").write_text(json.dumps({"version": 1, "rev": 1, "updated": "2026-10-23T00:00:00Z", "state": {
        "notes": [LAYOUT, LMEMO, LINK], "note-seq": {"new-ab": 2, "pay": 1}, "folders": FOLDERS}}, ensure_ascii=False), encoding="utf-8")
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.out, pg.srv = out, srv
    yield pg
    pg.close()
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def reply(pg, note, body):
    base = pg.srv.url.split("/index.html")[0]
    req = urllib.request.Request(base + "/api/reply", data=json.dumps({"note": note, "reply": body}, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": pg.srv.token})
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200


def phone(pg, sid):
    return pg.evaluate("id => { const c = [...document.querySelectorAll('.card')].find(c => c.dataset.id === id); if (!c) return null;"
                       " const r = c.querySelector('.phone').getBoundingClientRect(); return {x: r.left, y: r.top}; }", sid)


def notes(pg):
    return {n["id"]: n for n in pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]')")}


@pytest.mark.area("notes", "helper")
def test_reflected_blank_layout_becomes_the_screen_in_place_and_undo_restores(live):
    pg = live
    fit_view(pg)
    pg.wait_for_selector('.card.draft[data-id="new-ab"]')
    at, was = phone(pg, "new-ab"), phone(pg, "done")
    assert abs(at["x"] - was["x"]) > 20 or abs(at["y"] - was["y"]) > 20, "처음엔 따로 놓여 있다"
    pg.evaluate("window.__hdStay = 1")
    reply(pg, "L1", {"kind": "반영됨", "what": "쿠폰 화면을 완료 화면으로 만듦", "screens": ["done"], "captured": True})
    pg.wait_for_selector('.card.draft[data-id="new-ab"]', state="detached", timeout=5000)
    assert pg.evaluate("window.__hdStay") == 1, "새로고침 없이"
    now = phone(pg, "done")
    assert abs(now["x"] - at["x"]) < 2 and abs(now["y"] - at["y"]) < 2, (now, at)
    assert "빈 레이아웃 '쿠폰' 자리에 완료이 들어왔어요" in pg.text_content("#toast")
    ns = notes(pg)
    assert ns["L1m"]["screen"] == "done" and ns["L1m"]["no"] == 2 and ns["K1"]["to"] == "done" and ns["L1"]["screen"] == "done" and "edit" not in ns["L1"]
    assert pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-folders:'))))")["folders"][0]["ids"] == ["done"]
    pg.keyboard.press("h")
    show_sent(pg, True)                                # 옮겨 온 L1m 은 보낸 메모(AI 차례)라 숨김 — 보낸 메모 보기로 본다(task 29)
    pg.click('.card[data-id="done"] .nbadge')
    pg.wait_for_selector("#thread:not([hidden])")
    assert pg.text_content('#thread li[data-id="L1m"] .thmv') == "빈 레이아웃 '쿠폰'에서 옮겨 왔어요", "묶음 줄이 옮겨 온 것을 말한다"
    pg.keyboard.press("Escape")
    show_sent(pg, False)
    pg.click("#undo")
    pg.wait_for_selector('.card.draft[data-id="new-ab"]', timeout=3000)
    back, home = phone(pg, "new-ab"), phone(pg, "done")
    assert abs(back["x"] - at["x"]) < 2 and abs(back["y"] - at["y"]) < 2 and abs(home["x"] - was["x"]) < 2 and abs(home["y"] - was["y"]) < 2
    ns = notes(pg)
    assert ns["L1"]["stay"] == "done", "되돌린 승격은 다시 걸리지 않게"
    assert ns["L1"]["edit"] == "new-screen" and ns["L1"]["screen"] == "new-ab" and ns["L1m"]["screen"] == "new-ab" and ns["K1"]["to"] == "new-ab"
