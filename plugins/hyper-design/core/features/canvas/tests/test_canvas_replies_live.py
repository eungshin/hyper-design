"""AI 답이 캔버스에 살아서 온다(task 16 · A2a) — 도우미로 연 캔버스, `hd reply` 와 같은 길(POST /api/reply)로 상태 파일에 답을 쓴다 (Playwright).

(a) 반영됨 → 새로고침 없이 몇 초 안에 핀 상태가 완료로 바뀌고 묶음에 답 줄(올리면 화면·캡처) — 보낸 메모 보기 켜고(task 29), 끄면 둘 다 숨김.
(b) 질문 → 숨어 있던 보낸 메모가 다시 보임(task 29) · 위쪽 줄 '결정 필요 1'·카드 배지 강조색 · 고를 것 누르기 = 질문 메모 완료 + 새 메모를 그것만 보냄(대기열 파일).
(c) 받는 AI 가 없으면 칩 '받는 곳 없음', 보낸 메모는 묶음에서 '대기열'.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_edit import fit_view
from test_canvas_annotations import PAY, DONE, show_sent

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

PIN = '.card[data-id="pay"] .npin'
BADGE = '.card[data-id="pay"] .nbadge'
T_BTN = {"path": "button.pay", "text": "지금 결제하기", "quote": {"exact": "지금 결제하기", "prefix": "", "suffix": ""}}
T_LEAD = {"path": "p.lead", "text": "카드를 고르세요", "quote": {"exact": "카드를 고르세요", "prefix": "", "suffix": ""}}


def memo(i, no, t, note):
    return {"id": i, "no": no, "screen": "pay", "targets": [t], "path": t["path"], "text": t["text"], "rect": None,
            "note": note, "intent": "change", "sent": True, "replies": []}


@pytest.fixture(scope="module")
def served():
    """빌드 + 도우미 서버는 모듈에 한 번 — 테스트마다 상태 파일·대기열을 새로 쓰고 새 페이지를 연다(live)."""
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
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield out, srv
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)


def seed(out, notes):
    """이 테스트의 메모만 상태 파일에(파일 rev>0 = 열 때 파일이 이긴다) · 앞 테스트의 대기열 파일은 치운다."""
    shutil.rmtree(out / ".hd-queue", ignore_errors=True)
    (out / ".hd-canvas.json").write_text(json.dumps({"version": 1, "rev": 1, "updated": "2026-10-23T00:00:00Z", "state": {
        "notes": notes, "note-seq": {"pay": max(n["no"] for n in notes)}}}, ensure_ascii=False), encoding="utf-8")


@pytest.fixture()
def live(served, ctx, request):
    out, srv = served
    seed(out, getattr(request, "param", None) or [memo("m1", 1, T_BTN, "버튼을 더 크게"), memo("m2", 2, T_LEAD, "안내 글 색")])
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.out, pg.srv = out, srv
    yield pg
    pg.close()
    assert not errors, errors


def reply(pg, note, body):
    base = pg.srv.url.split("/index.html")[0]
    req = urllib.request.Request(base + "/api/reply", data=json.dumps({"note": note, "reply": body}, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": pg.srv.token})
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200


def file_notes(pg):
    return json.loads((pg.out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"]["notes"]


@pytest.mark.area("notes", "helper")
def test_agent_reply_shows_live_without_reload(live):
    """(a) 반영됨 → ~3초 안에 그 핀이 완료 상태, 묶음 '완료' 에 답 줄, 페이지는 그대로(표지가 남음). (c) 칩 '받는 곳 없음'.
    보낸 메모는 숨김(task 29)이라 '보낸 메모 보기'를 켜고 본다 — 끄면 둘(대기열·완료) 다 숨는다."""
    pg = live
    assert pg.text_content("#aichip") == "받는 곳 없음" and pg.is_visible("#aichip"), "받는 AI 가 없으면 칩이 그렇게 말한다(R4)"
    show_sent(pg, True)
    fit_view(pg)
    pg.wait_for_function(f"document.querySelectorAll('{PIN}').length === 2", timeout=8000)
    assert pg.text_content(BADGE) == "2"
    pg.evaluate("window.__hdStay = 1")
    long = "".join("%03d 줄 자세한 설명\n" % i for i in range(900))[:9995] + "설명-끝"   # R26: 긴 답 본문(detail ≤50000)은 묶음 답 줄 아래 전체
    reply(pg, "m1", {"kind": "반영됨", "what": "버튼 키움", "screens": ["pay"], "captured": True, "detail": long})
    pg.wait_for_selector(PIN + '[data-id="m1"][data-st="done"]', state="attached", timeout=4000)
    assert pg.locator(PIN).count() == 2 and pg.text_content(BADGE) == "2", "켜져 있으면 완료한 메모도 보인다(흐리게)"
    assert pg.evaluate("window.__hdStay") == 1, "새로고침 없이"
    pg.click(BADGE)
    pg.wait_for_selector("#thread:not([hidden])")
    assert pg.get_attribute('#thread li[data-id="m2"] .ths', "data-q") == "1", "받는 곳 없이 보낸 메모 = 대기열(R4)"
    pg.click("#thread details.thdone summary")
    line = pg.locator('#thread details.thdone li[data-id="m1"] .thr1[data-kind="반영됨"]')
    assert line.count() == 1, "답 줄"
    assert "캡처 확인함" in line.get_attribute("title")
    det = pg.locator('#thread details.thdone li[data-id="m1"] .thdet')
    assert det.count() == 1 and det.text_content() == long, "detail 10,000자 = 답 줄 아래 전체(줄바꿈 그대로)"
    assert len(line.get_attribute("title")) < 400, "툴팁은 앞부분만"
    pg.keyboard.press("Escape")
    show_sent(pg, False)
    pg.wait_for_selector(BADGE, state="detached", timeout=3000)
    assert pg.locator(PIN).count() == 0, "끄면 보낸(대기열)·완료 메모 둘 다 숨는다"


@pytest.mark.area("notes", "helper")
def test_question_reply_surfaces_and_choice_sends_follow_up(live):
    """(b) 질문 → '결정 필요 1'·배지 강조색 · 고르기 = 질문 메모 완료(확인 + answer) + 새 메모 '질문 "…" → 파랑' 를 대기열로 보냄."""
    pg = live
    show_sent(pg, False)
    fit_view(pg)
    pg.wait_for_selector("#nsent:not([disabled])")
    assert pg.locator(BADGE).count() == 0 and pg.is_hidden("#decn"), "보낸 메모(AI 차례)는 숨김(task 29)"
    reply(pg, "m2", {"kind": "질문", "question": "어느 색?", "choices": ["파랑", "검정"]})
    pg.wait_for_selector("#decn:not([hidden])", timeout=4000)
    assert pg.get_attribute("#decn", "data-n") == "1"
    assert "decide" in pg.get_attribute(BADGE, "class") and pg.text_content(BADGE) == "1", "질문 받은 메모는 다시 보인다 — 배지 강조색, 수 = 보이는 메모"
    pg.click(BADGE)
    pg.wait_for_selector('#thread li[data-id="m2"] button.thc')
    assert pg.get_attribute('#thread li[data-id="m2"] .ths', "data-st") == "decide"
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
    assert pg.evaluate("window.__hdLastHelper.forward.via") == "queue" and pg.is_visible("#toast"), "받는 곳이 없으면 대기열로 갔다고 알림"


ASKED = dict(memo("m2", 2, T_LEAD, "안내 글 색"), replies=[{"kind": "질문", "question": "어느 색?", "choices": ["파랑", "검정"], "by": "agent", "at": "2026-10-23T00:00:01Z"}])


@pytest.mark.parametrize("live", [[memo("m1", 1, T_BTN, "버튼을 더 크게"), ASKED]], indirect=True, ids=["asked"])
@pytest.mark.area("notes", "helper")
def test_decide_chip_filters_memo_panel_to_decide_only(live):
    """#232: 위쪽 '결정 필요' 누르기 = 메모 패널을 결정 필요 메모만으로(#ndec 눌림) · #ndec 다시 누르기 = 모두(보낸 메모 보기 켜짐 — task 29)."""
    pg = live
    show_sent(pg, True)
    pg.wait_for_selector("#decn:not([hidden])", timeout=5000)
    pg.click("#decn")
    pg.wait_for_selector("#nlist li")
    assert pg.get_attribute("#ndec", "aria-pressed") == "true" and pg.locator("#nlist li").count() == 1
    pg.click("#ndec")
    assert pg.get_attribute("#ndec", "aria-pressed") == "false" and pg.locator("#nlist li").count() == 2
