"""AI 답이 캔버스에 살아서 온다(task 16 · A2a) — 도우미로 연 캔버스, `hd reply` 와 같은 길(POST /api/reply)로 상태 파일에 답을 쓴다 (Playwright).

(a) 반영됨 → 새로고침 없이 몇 초 안에 핀·배지 수가 빠지고 묶음에 답 줄(올리면 화면·캡처).
(b) 질문 → 위쪽 줄 '결정 필요 1'·카드 배지 강조색 · 고를 것 누르기 = 질문 메모 완료 + 새 메모를 그것만 보냄(대기열 파일).
(c) 받는 AI 가 없으면 칩 '받는 곳 없음', 보낸 메모는 묶음에서 '대기열'.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_edit import fit_view
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

PIN = '.card[data-id="pay"] .npin'
BADGE = '.card[data-id="pay"] .nbadge'
T_BTN = {"path": "button.pay", "text": "지금 결제하기", "quote": {"exact": "지금 결제하기", "prefix": "", "suffix": ""}}
T_LEAD = {"path": "p.lead", "text": "카드를 고르세요", "quote": {"exact": "카드를 고르세요", "prefix": "", "suffix": ""}}


def memo(i, no, t, note):
    return {"id": i, "no": no, "screen": "pay", "targets": [t], "path": t["path"], "text": t["text"], "rect": None,
            "note": note, "intent": "change", "sent": True, "replies": []}


@pytest.fixture()
def live(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-live-"))
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
        "notes": [memo("m1", 1, T_BTN, "버튼을 더 크게"), memo("m2", 2, T_LEAD, "안내 글 색")], "note-seq": {"pay": 2}}}, ensure_ascii=False), encoding="utf-8")
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


def file_notes(pg):
    return json.loads((pg.out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"]["notes"]


def test_agent_reply_shows_live_without_reload(live):
    """(a) 반영됨 → ~3초 안에 핀·배지 수가 빠지고 묶음 '완료' 에 답 줄, 페이지는 그대로(표지가 남음). (c) 칩 '받는 곳 없음'."""
    pg = live
    assert pg.text_content("#aichip") == "받는 곳 없음" and pg.is_visible("#aichip"), "받는 AI 가 없으면 칩이 그렇게 말한다(R4)"
    fit_view(pg)
    pg.wait_for_function(f"document.querySelectorAll('{PIN}').length === 2", timeout=8000)
    assert pg.text_content(BADGE) == "2"
    pg.evaluate("window.__hdStay = 1")
    t0 = time.time()
    reply(pg, "m1", {"kind": "반영됨", "what": "버튼 키움", "screens": ["pay"], "captured": True})
    pg.wait_for_function(f"(() => {{ const b = document.querySelector('{BADGE}'); return b && b.textContent === '1'; }})()", timeout=4000)
    assert time.time() - t0 < 4
    pg.wait_for_function(f"document.querySelectorAll('{PIN}').length === 1", timeout=3000)
    assert pg.evaluate("window.__hdStay") == 1, "새로고침 없이"
    pg.click(BADGE)
    pg.wait_for_selector("#thread:not([hidden])")
    assert pg.text_content('#thread li[data-id="m2"] .ths') == "대기열", "받는 곳 없이 보낸 메모 = 대기열(R4)"
    pg.click("#thread details.thdone summary")
    line = pg.locator('#thread details.thdone li[data-id="m1"] .thr1')
    assert line.text_content() == "반영됨 — 버튼 키움 · pay"
    assert "캡처 확인함" in line.get_attribute("title")
    pg.keyboard.press("Escape")


def test_question_reply_surfaces_and_choice_sends_follow_up(live):
    """(b) 질문 → '결정 필요 1'·배지 강조색 · 고르기 = 질문 메모 완료(확인 + answer) + 새 메모 '질문 "…" → 파랑' 를 대기열로 보냄."""
    pg = live
    fit_view(pg)
    pg.wait_for_selector(BADGE)
    assert pg.is_hidden("#decn")
    reply(pg, "m2", {"kind": "질문", "question": "어느 색?", "choices": ["파랑", "검정"]})
    pg.wait_for_selector("#decn:not([hidden])", timeout=4000)
    assert pg.text_content("#decn") == "결정 필요 1"
    assert "decide" in pg.get_attribute(BADGE, "class") and pg.text_content(BADGE) == "2", "배지 강조색, 수는 열린 메모 수 그대로"
    accent = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--ui-accent').trim()")
    assert accent and pg.evaluate(f"getComputedStyle(document.querySelector('{BADGE}')).backgroundColor") != pg.evaluate("getComputedStyle(document.querySelector('#nsend')).backgroundColor")
    pg.click("#decn")                                   # 메모 패널을 결정 필요만으로
    pg.wait_for_selector("#nlist li")
    assert pg.get_attribute("#ndec", "aria-pressed") == "true" and pg.locator("#nlist li").count() == 1
    pg.click("#ndec")
    assert pg.locator("#nlist li").count() == 2
    pg.click(BADGE)
    pg.wait_for_selector('#thread li[data-id="m2"] button.thc')
    assert pg.text_content('#thread li[data-id="m2"] .ths') == "결정 필요"
    pg.click('#thread li[data-id="m2"] button.thc:has-text("파랑")')
    pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
    q = list((pg.out / ".hd-queue").iterdir())
    assert len(q) == 1 and '질문 "어느 색?" → 파랑' in q[0].read_text(encoding="utf-8"), "고른 답이 새 메모로 그것만 나간다"
    assert "버튼을 더 크게" not in q[0].read_text(encoding="utf-8")
    pg.wait_for_selector("#decn[hidden]", state="attached", timeout=3000)
    for _ in range(40):
        ns = {n["id"]: n for n in file_notes(pg)}
        if len(ns) == 3 and ns["m2"]["replies"][-1].get("answer"):
            break
        time.sleep(0.1)
    assert ns["m2"]["replies"][-1] == {**ns["m2"]["replies"][-1], "kind": "확인", "by": "user", "answer": "파랑"}
    new = [n for i, n in ns.items() if i not in ("m1", "m2")][0]
    assert new["note"] == '질문 "어느 색?" → 파랑' and new["sent"] is True and new["screen"] == "pay" and new["targets"][0]["path"] == "p.lead" and new["no"] == 3
    assert "대기열 파일" in pg.text_content("#toast") and "--paseo-agent" in pg.text_content("#toast"), "받는 곳이 없다고, 붙이는 법까지"
