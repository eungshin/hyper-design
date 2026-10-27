"""R29 — 대화창 '/memo': 보내기 전 메모를 대화 글과 한 요청으로(브라우저 + 같은 프로세스 도우미, 받는 곳 없음 = 대기열 · 실제 Paseo 없음 · HD_HOME 임시).
규칙(명령 고르기·함께 보낼 메모·칩 이름)은 test_canvas_unit_chat_cmd.py(unit)."""
import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_chat_log import served, call, open_page  # noqa: F401


def memo(mid, sid, no, note, sent=False, replies=None):
    return {"id": mid, "screen": sid, "no": no, "targets": [{"path": "body", "text": ""}], "path": "body", "text": "", "rect": None,
            "note": note, "intent": "change", "sent": sent, "replies": replies or [], "scope": "screen"}


def notes(srv):
    return {n["id"]: n for n in call(srv, "GET", "/api/state")[1]["state"].get("notes") or []}


@pytest.mark.area("chat", "notes")
def test_slash_memo_sends_unsent_memos_with_the_chat_text_once(served, ctx):
    out, srv = served
    rev = call(srv, "GET", "/api/state")[1].get("rev", 0)
    seed = [memo("m1", "pay", 1, "결제 버튼을 더 크게"), memo("m2", "done", 1, "완료 문구를 짧게"),
            memo("m3", "pay", 2, "이미 끝난 메모", True, [{"kind": "반영됨", "what": "했어요", "at": "2026-10-27T00:00:00Z"}])]
    assert call(srv, "PUT", "/api/state", {"rev": rev, "state": {"notes": seed}})[0] == 200
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    try:
        ta = "#hdchat textarea"
        pg.click(ta)
        # '/' 아닌 글·Esc = 보통 글 그대로
        pg.keyboard.type("/m x")
        assert pg.is_hidden("#hdchat .ch-cmds"), "빈칸을 치면 명령 목록이 닫힌다"
        pg.fill(ta, ""); pg.keyboard.type("/")
        pg.wait_for_selector("#hdchat .ch-cmds li[data-cmd='memo']", timeout=5000)
        pg.keyboard.press("Escape")
        assert pg.is_hidden("#hdchat .ch-cmds") and pg.input_value(ta) == "/", "Esc = 목록만 닫고 글은 그대로"
        pg.fill(ta, ""); pg.keyboard.type("/me")
        pg.wait_for_selector("#hdchat .ch-cmds li[data-cmd='memo'][aria-selected='true']", timeout=5000)
        assert "/memo" in pg.inner_text("#hdchat .ch-cmds")
        pg.keyboard.press("Enter")
        chip = "#hdchat .ch-chip.memos"
        pg.wait_for_selector(chip, timeout=5000)
        assert pg.inner_text(chip + " span") == "메모 2건" and pg.input_value(ta) == "", "고르면 친 '/me' 는 지우고 칩 하나"
        assert pg.evaluate("getComputedStyle(document.querySelector('#hdchat .ch-chip.memos')).backgroundColor") == "rgb(236, 236, 232)", "요소 칩과 같은 밝은 칩"
        pg.hover(chip)
        pg.wait_for_selector("#hdchat .ch-tip:not([hidden])", timeout=3000)
        tip = pg.inner_text("#hdchat .ch-tip")
        assert "결제 — 결제 버튼을 더 크게" in tip and "완료 — 완료 문구를 짧게" in tip and "이미 끝난" not in tip, tip
        pg.click(ta); pg.keyboard.type("이 메모들도 같이 반영해 줘"); pg.keyboard.press("Enter")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        req = pg.evaluate("window.__hdLastSend")
        assert req.startswith("[hyper-design 수정 요청]"), "위쪽 [보내기]와 같은 요청문"
        assert "요청: 이 메모들도 같이 반영해 줘" in req and "결제 버튼을 더 크게" in req and "완료 문구를 짧게" in req, req
        assert "이미 끝난 메모" not in req, "완료한 메모는 싣지 않는다"
        assert pg.locator(chip).count() == 0, "보낸 뒤 메모 N건 칩은 빠진다"
        for _ in range(50):                               # 보낸 메모 = 위쪽 [보내기]처럼 '보냄'(AI 작업 중)으로 저장
            ns = notes(srv)
            if ns.get("m1", {}).get("sent") and ns.get("m2", {}).get("sent"):
                break
            pg.wait_for_timeout(200)
        assert ns["m1"]["sent"] and ns["m2"]["sent"], ns
        assert ns["m3"]["replies"][-1]["kind"] == "반영됨", "끝난 메모는 그대로"
        # 다시 /memo = 보낼 메모가 없음 → 토스트, 칩 없음(두 번 가지 않는다)
        pg.click(ta); pg.keyboard.type("/"); pg.wait_for_selector("#hdchat .ch-cmds li", timeout=5000); pg.keyboard.press("Enter")
        pg.wait_for_function("document.getElementById('toast') && document.getElementById('toast').textContent.includes('보낼 메모가 없어요')", timeout=5000)
        assert pg.locator(chip).count() == 0
    finally:
        pg.close()
    assert not errors, errors
