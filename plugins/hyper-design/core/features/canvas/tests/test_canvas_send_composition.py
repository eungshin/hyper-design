"""한 번 보내기가 말하는 것(task 17 · A2b) — 도우미로 연 캔버스에서 [보내기] 뒤 대기열 파일(.hd-queue)을 읽는다 (Playwright).

R7 메모 창 범위 '모든 화면' → 대기열 파일에 '범위: 모든 화면', 묶음 줄에 범위 말.
R5 목적 있는 빈 레이아웃 + 그 화면 메모 하나 → 대기열 파일에 항목 하나로 둘 다.
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_edit import fit_view, add_card_memo
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

LAYOUT = {"id": "L1", "no": 1, "screen": "new-ab", "targets": [{"path": "(새 화면)", "text": "빈 레이아웃", "rect": None}], "path": "(새 화면)",
          "text": "빈 레이아웃", "rect": None, "intent": "change", "sent": False, "edit": "new-screen", "op": "new", "to": "", "value": "쿠폰",
          "purpose": "쿠폰을 고른다", "x": 900, "y": 0, "replies": [],
          "note": '새 화면 "쿠폰"(new-ab)을 빈 레이아웃으로 만들기 — 목적: 쿠폰을 고른다 · 내용은 이 목적과 이 화면에 남긴 메모를 따라 채우기'}
LMEMO = {"id": "L1m", "no": 2, "screen": "new-ab", "targets": [{"path": "body", "text": "쿠폰", "rect": None}], "path": "body", "text": "쿠폰",
         "rect": None, "note": "쿠폰 목록과 적용 버튼", "intent": "change", "sent": False, "replies": []}


@pytest.fixture()
def live(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-send-"))
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
        "notes": [LAYOUT, LMEMO], "note-seq": {"new-ab": 2}}}, ensure_ascii=False), encoding="utf-8")
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


def queued(pg):
    pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
    q = list((pg.out / ".hd-queue").iterdir())
    assert len(q) == 1, q
    return q[0].read_text(encoding="utf-8")


@pytest.mark.area("notes")
def test_scope_all_screens_reaches_the_queue_and_layout_memo_rides_with_layout(live):
    pg = live
    fit_view(pg)
    pg.wait_for_selector('.card[data-id="pay"] .cover')
    b = pg.locator('.card[data-id="pay"] .cover').bounding_box()
    pg.keyboard.press("m")
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    pg.wait_for_selector("#pop:not([hidden])")
    assert pg.get_attribute('#pscope button[data-scope="screen"]', "aria-pressed") == "true", "화면 전체 메모 = 기본 '이 화면'"
    assert pg.eval_on_selector_all("#pscope button", "bs => bs.map(b => b.getAttribute('aria-label'))") == ["이 요소", "이 화면", "모든 화면"]   # R27 F09: 아이콘 + 이름
    pg.click('#pscope button[data-scope="all"]')
    pg.fill("#pnote", "배경을 움직이는 그라데이션으로")
    pg.click("#padd")
    pg.keyboard.press("h")
    pg.click('.card[data-id="pay"] .nbadge')
    pg.wait_for_selector("#thread:not([hidden])")
    assert pg.text_content("#thread li .thsc") == "모든 화면", "묶음 줄에 범위 말"
    pg.keyboard.press("Escape")
    pg.click("#nsend")
    t = queued(pg)
    lines = t.split("\n")
    assert lines[0].endswith(" · 2건"), t
    assert "   범위: 모든 화면" in lines, t
    lay = [i for i, l in enumerate(lines) if l.startswith("1. screen=new-ab")]
    assert lay and "목적: 쿠폰을 고른다" in lines[lay[0] + 2] and lines[lay[0] + 3] == "       - 쿠폰 목록과 적용 버튼", t
    assert sum("쿠폰 목록과 적용 버튼" in l for l in lines) == 1, "메모 본문은 레이아웃 항목에 한 번만"
    pg.wait_for_function("(() => { const s = JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]');"
                         " return s.length === 3 && s.every(n => n.sent); })()", timeout=5000)
