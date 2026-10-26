"""R24·R25 — 브라우저(Playwright) + 같은 프로세스 도우미. 실제 Paseo·Claude 에 보내지 않는다(에이전트 = 테스트의 HTTP hello/reply,
터미널 대화 = 테스트가 끼운 가짜 주소·이벤트, Paseo = 없는 경로, HD_HOME = 임시).

(R24) 대화 패널은 AI 답을 다 보인다 — 긴 답·줄바꿈·``` 코드 덩이(고정폭 pre)·복사, 새 줄이 와도 있던 줄 요소는 그대로.
규칙은 test_canvas_unit_chat_full.py(unit).
"""
import os, tempfile, time
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_chat_log import served, call, open_page, note_saved  # noqa: F401
import router  # noqa: E402

SHOTS = Path(os.environ.get("HD_SHOTS_R24", Path(tempfile.gettempdir()) / "claude" / "r24-impl"))


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


LONG = ("긴 답의 첫 문단이에요. 터미널처럼 다 보여야 해요.\n\n"
        + "\n".join("%d. 이 줄은 답의 %d번째 줄 — 잘리면 안 되는 글이에요." % (i, i) for i in range(1, 61))
        + "\n\n```js\nfunction pay() {\n  return 'ok';\n}\n```\n마지막 줄: `pay()` 를 불러요. 끝-표시")


@pytest.mark.area("chat", "dock")
def test_panel_shows_whole_long_reply_with_code_and_copy(served, ctx, monkeypatch):
    out, srv = served

    def fake(s, q, b):                                   # 터미널 대화(S3b 모양) — 긴 assistant 답 하나
        now = int(time.time() * 1000)
        return 200, {"entries": [{"id": "a1", "role": "assistant", "text": LONG, "at": now - 60000}], "cursor": "c1", "source": "claude"}
    monkeypatch.setitem(router.ROUTES["GET"], "/api/agents/transcript", fake)
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-1", "name": "클로드", "kind": "claude"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/attach", {"agent": "ag-1"})[0] == 200
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    try:
        pg.wait_for_selector("#pTalk .tk-term[data-id='a1'] .tk-md", timeout=15000)
        txt = pg.inner_text("#pTalk .tk-term[data-id='a1'] .tk-md")
        assert "60. 이 줄은 답의 60번째 줄" in txt and "끝-표시" in txt and "…" not in txt, "터미널 답은 끝까지"
        assert "\n2. 이 줄은" in txt, "줄바꿈 그대로"
        pre = pg.locator("#pTalk .tk-term[data-id='a1'] pre.tk-code")
        assert pre.count() == 1 and "return 'ok';" in pre.inner_text()
        assert "monospace" in pg.evaluate("getComputedStyle(document.querySelector('#pTalk pre.tk-code')).fontFamily")
        assert pg.locator("#pTalk .tk-term[data-id='a1'] .tk-p code").inner_text() == "pay()"
        assert pg.evaluate("getComputedStyle(document.querySelector('#pTalk .tk-list')).userSelect") == "text", "글을 골라 복사할 수 있다"
        # 캔버스 요청 → 긴 답(agent.reply) = 턴의 답 줄도 전체, 줄바꿈 그대로
        pg.evaluate("document.querySelector('#pTalk .tk-term[data-id=\"a1\"]').__keep = 1")
        pg.click("#hdchat textarea"); pg.keyboard.type("결제 화면 설명해 줘"); pg.keyboard.press("Enter")
        pg.wait_for_selector("#pTalk .tk-turn", timeout=15000)
        nid = note_saved(pg, srv)
        detail = "결제 화면은 세 부분이에요.\n- 금액\n- 버튼\n" + "설명 " * 300 + "\n답-끝"   # 요약 칸은 프로토콜이 짧게(140) — 긴 설명은 detail(≤2000)
        code, res = call(srv, "POST", "/api/reply", {"note": nid, "reply": {"kind": "반영됨", "what": "설명을 남겼어요", "detail": detail,
                                                                          "screens": ["pay"], "captured": False, "by": "ag-1"}})
        assert code == 200, res
        pg.wait_for_function("[...document.querySelectorAll('#pTalk .tk-l[data-kind=\"reply\"]')].some(l => l.innerText.includes('답-끝'))", timeout=15000)
        rt = pg.inner_text("#pTalk .tk-l[data-kind='reply']")
        assert rt.startswith("설명을 남겼어요\n\n결제 화면은 세 부분이에요.\n- 금액\n- 버튼") and "답-끝" in rt and "…" not in rt, "답 줄 = 요약 + 설명 전체 · 줄바꿈 그대로"
        assert pg.evaluate("document.querySelector('#pTalk .tk-term[data-id=\"a1\"]').__keep") == 1, "새 줄이 와도 있던 줄 요소는 다시 만들지 않는다"
        # 복사 단추 = 그 답 글 그대로
        pg.hover("#pTalk .tk-term[data-id='a1'] .tk-md")
        pg.click("#pTalk .tk-term[data-id='a1'] .tk-copy")
        pg.wait_for_function("document.getElementById('toast') && document.getElementById('toast').textContent.includes('복사했어요')", timeout=5000)
        pg.evaluate("document.querySelector('#pTalk .tk-term[data-id=\"a1\"]').scrollIntoView({block: 'start'})")
        shot(pg, "r24-long-reply-panel.png")
        pg.evaluate("document.querySelector('#pTalk pre.tk-code').scrollIntoView({block: 'start'})")
        shot(pg, "r24-long-reply-code-and-reply.png")
    finally:
        pg.close()
    assert not errors, errors


PAY_BOX = """() => { const c = document.querySelector('.card[data-id="pay"] .phone').getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect();
  const z = parseFloat(document.getElementById('stage').dataset.zoom); return {x: (c.left - s.left) / z, y: (c.bottom - s.top) / z, w: c.width / z}; }"""


@pytest.mark.area("chat", "tools")
def test_selected_board_note_becomes_chip_and_goes_into_the_request(served, ctx):
    out, srv = served
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    try:
        b = pg.evaluate(PAY_BOX)
        rev = call(srv, "GET", "/api/state")[1].get("rev", 0)
        note = {"x": int(b["x"]), "y": int(b["y"]) + 90, "w": 260, "text": "결제 버튼을 더 눈에 띄게\n색은 진하게", "at": 1}
        assert call(srv, "PUT", "/api/state", {"rev": rev, "state": {"board-notes": {"bn1": note}}})[0] == 200
        pg.wait_for_selector(".bnote[data-id='bn1']", timeout=15000)
        pg.keyboard.press("Escape"); pg.keyboard.press("v")
        pg.click(".bnote[data-id='bn1']")
        chip = "#hdchat .ch-chip.note"
        pg.wait_for_selector(chip, timeout=5000)
        assert pg.inner_text(chip + " span").startswith('노트 "결제 버튼을 더 눈에 띄게')
        assert pg.is_enabled("#hdchat .ch-send"), "노트만 있어도 보낼 수 있다"
        shot(pg, "r25-note-chip-in-dock.png")
        pg.click("#hdchat textarea"); pg.keyboard.type("이 노트대로 고쳐 줘"); pg.keyboard.press("Enter")
        nid = note_saved(pg, srv)
        n = next(x for x in call(srv, "GET", "/api/state")[1]["state"]["notes"] if x["id"] == nid)
        assert n["note"] == "이 노트대로 고쳐 줘\n\n노트:\n- 결제 버튼을 더 눈에 띄게\n  색은 진하게 (가까운 화면: 결제)", n["note"]
        # × = 그 노트를 요청에서 뺀다
        pg.click(chip + " button")
        assert pg.locator(chip).count() == 0
    finally:
        pg.close()
    assert not errors, errors
