"""정보 카드(R47 phase B) — 브라우저 + 같은 프로세스 도우미(받는 곳 없음 = 대기열 · 실제 Paseo 없음 · HD_HOME 임시).
판 메모가 화면에 이어져 있으면 대화창으로 보낸 요청문에 '유의(정보 카드):' 가 그 화면마다 한 번 · 레이어 줄에 '카드 N'.
연결(board-links)은 상태 파일에만 심는다 — 주인은 view-board-links(BL.map, 판에서 끌어 잇기는 test_canvas_board_links.py). 규칙은 test_canvas_unit_info_card.py(unit)."""


import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_chat_log import served, call, open_page  # noqa: F401
from test_canvas_chat_memo import memo

LINKS = {"l1": {"from": "note:a", "to": "screen:pay", "at": "2026-10-29T00:00:00Z"},
         "l2": {"from": "note:b", "to": "note:a", "at": "2026-10-29T00:00:00Z"}}
BOARD = {"a": {"x": -400, "y": 0, "w": 280, "text": "결제 버튼은 화면에 하나만", "at": 1},
         "b": {"x": -400, "y": 200, "w": 280, "text": "금액은 굵게\n\n이 문단은 빠진다", "at": 2}}


@pytest.mark.area("chat", "notes")
def test_chat_send_carries_the_screen_card_once_and_layers_show_the_badge(served, ctx):
    out, srv = served
    rev = call(srv, "GET", "/api/state")[1].get("rev", 0)
    seed = [memo("m1", "pay", 1, "결제 버튼을 더 크게"), memo("m2", "pay", 2, "금액 글씨 키우기"), memo("m3", "done", 1, "완료 문구를 짧게")]
    assert call(srv, "PUT", "/api/state", {"rev": rev, "state": {"notes": seed, "board-notes": BOARD, "board-links": LINKS}})[0] == 200
    pg, errors = open_page(ctx, srv)
    try:
        pg.set_viewport_size({"width": 1440, "height": 1000})
        pg.wait_for_function("document.querySelector('[data-ly=\"pay\"] .ly-card')", timeout=10000)
        assert pg.inner_text("[data-ly='pay'] .ly-card") == "카드 2", "사슬(바로 + 이어진 메모) 수"
        assert pg.locator("[data-ly='done'] .ly-card").count() == 0, "이어진 메모가 없는 화면은 배지 없음"
        ta = "#hdchat textarea"
        pg.click(ta); pg.keyboard.type("/me")
        pg.wait_for_selector("#hdchat .ch-cmds li[data-cmd='memo'][aria-selected='true']", timeout=5000)
        pg.keyboard.press("Enter")
        pg.wait_for_selector("#hdchat .ch-chip.memos", timeout=5000)
        pg.click(ta); pg.keyboard.type("같이 반영해 줘"); pg.keyboard.press("Enter")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        req = pg.evaluate("window.__hdLastSend")
        assert req.count("유의(정보 카드):") == 1, req
        lines = req.split("\n")
        i = lines.index("   유의(정보 카드):")
        assert " screen=pay " in lines[i - 1] and lines[i - 1][:1].isdigit(), "pay 의 첫 항목 머리 바로 아래"
        assert lines[i + 1:i + 3] == ["   - 결제 버튼은 화면에 하나만", "   - 금액은 굵게"], req
        assert lines[i + 3].startswith('   text="'), req
        assert "이 문단은 빠진다" not in req, "메모는 첫 문단만"
    finally:
        pg.close()
    assert not errors, errors
