"""V1 — 대화창 '/both': 캔버스 화면과 parts.json 으로 이어진 실제 앱에 함께 적용(브라우저 + 같은 프로세스 도우미, 받는 곳 없음 = 대기열 · HD_HOME 임시).
규칙(대상 화면·요청 줄·연결 읽기)은 test_canvas_unit_chat_both.py(unit)."""
import json

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_chat_log import served, call, open_page  # noqa: F401
from test_canvas_chat import card_click

UNLINKED = "이 화면은 앱 부품이 연결되지 않았어요 — hd parts 로 연결해 주세요"


def link_pay(out, repo):
    """pay 화면이 앱 부품 screens/app-pay.html 을 iframe 으로 끌어 쓰게 하고 parts.json 에 적는다(done 은 연결 없음)."""
    (out / "screens" / "app-pay.html").write_text("<html><body>앱 결제</body></html>", encoding="utf-8")
    pay = out / "screens" / "pay.html"
    pay.write_text(pay.read_text(encoding="utf-8").replace("</body>", '<iframe src="app-pay.html"></iframe></body>'), encoding="utf-8")
    (out / "parts.json").write_text(json.dumps({"version": 1, "parts": [
        {"file": "screens/app-pay.html", "repo": str(repo), "watch": ["src/pay"], "build": ["node", "b.mjs", "{out}"],
         "stamp": "g:" + "a" * 16, "dirty": False, "built_at": "2026-10-31T10:00:00"}]}), encoding="utf-8")


def toast_has(pg, text):
    pg.wait_for_function("t => document.getElementById('toast') && document.getElementById('toast').textContent.includes(t)", arg=text, timeout=5000)


def pick(pg, sid):
    pg.keyboard.press("v")
    card_click(pg, sid)
    pg.wait_for_function("t => [...document.querySelectorAll('#hdchat .ch-chip')].some(c => c.textContent.startsWith(t))", arg={"pay": "결제", "done": "완료"}[sid], timeout=5000)


@pytest.mark.area("chat", "notes")
def test_slash_both_mid_sentence_sends_canvas_file_app_path_and_verify_line(served, ctx, tmp_path):
    out, srv = served
    repo = tmp_path / "app"
    repo.mkdir()
    link_pay(out, repo)
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    try:
        pick(pg, "pay")
        ta = "#hdchat textarea"
        pg.click(ta)
        pg.keyboard.type("버튼을 파랗게 /bo")
        pg.wait_for_selector("#hdchat .ch-cmds li[data-cmd='both'][aria-selected='true']", timeout=5000)
        assert "캔버스 화면과 연결된 실제 앱에 함께 적용" in pg.inner_text("#hdchat .ch-cmds")
        pg.keyboard.press("Enter")
        chip = "#hdchat .ch-chip.both"
        pg.wait_for_selector(chip, timeout=5000)
        assert pg.inner_text(chip + " span") == "캔버스+앱" and pg.input_value(ta) == "버튼을 파랗게 ", "명령 낱말만 지우고 칩 하나"
        pg.keyboard.type("해 줘")
        pg.keyboard.press("Enter")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        req = pg.evaluate("window.__hdLastSend")
        assert req.startswith("[hyper-design 수정 요청]"), "위쪽 [보내기]와 같은 요청문"
        assert "요청: 버튼을 파랗게 해 줘" in req and "캔버스: screens/pay.html" in req, req
        assert "앱: " + str(repo) in req and "경로: src/pay" in req, req
        assert "둘 다 고친 뒤 `hd verify pay` 으로 확인" in req, req
        assert pg.locator(chip).count() == 0, "보낸 뒤 칩은 빠진다"
    finally:
        pg.close()
    assert not errors, errors


@pytest.mark.area("chat", "notes")
def test_slash_both_on_unlinked_screen_toasts_and_sends_nothing(served, ctx, tmp_path):
    out, srv = served
    repo = tmp_path / "app"
    repo.mkdir()
    link_pay(out, repo)
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    try:
        pick(pg, "done")
        ta = "#hdchat textarea"
        pg.click(ta)
        pg.keyboard.type("문구를 짧게 /both")
        pg.wait_for_selector("#hdchat .ch-cmds li[data-cmd='both']", timeout=5000)
        pg.keyboard.press("Enter")
        toast_has(pg, UNLINKED)
        assert pg.locator("#hdchat .ch-chip.both").count() == 0, "연결 없는 화면 = 칩 없음"
        assert pg.evaluate("window.__hdLastSend") is None, "아무것도 보내지 않는다"
    finally:
        pg.close()
    assert not errors, errors
