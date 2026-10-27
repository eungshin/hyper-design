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
        detail = "결제 화면은 세 부분이에요.\n- 금액\n- 버튼\n" + "설명 " * 300 + "\n답-끝"   # 요약 칸은 프로토콜이 짧게(140) — 긴 설명은 detail(≤50000, R26)
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


@pytest.fixture()
def plain(tmp_path):
    """도우미 없이(file://) — 대화 패널이 없어 입력창이 판 아래에 떠 있다."""
    import json, subprocess, sys
    from test_canvas_v2 import SCRIPTS
    from test_canvas_annotations import PAY, DONE
    out = tmp_path / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다\n둘째 줄\n셋째 줄", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    return out


@pytest.mark.area("chat", "tools")
def test_caption_edit_box_is_moved_clear_of_the_floating_dock(plain, ctx):
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1440, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto((plain / "index.html").resolve().as_uri())
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_selector("#hdchat:not(.docked) .ch-box")
        dock = pg.locator("#hdchat").bounding_box()
        # 판을 끌어 카드 아래 이름이 떠 있는 입력창 아래에 오게(손 도구)
        pg.keyboard.press("h")
        t = pg.locator(".card[data-id='pay'] > .ftitle").bounding_box()
        sx, sy = t["x"] + t["width"] / 2, t["y"] - 200
        pg.mouse.move(sx, sy); pg.mouse.down()
        pg.mouse.move(dock["x"] + dock["width"] / 2, dock["y"] + dock["height"] / 2 - 200, steps=10); pg.mouse.up()
        t = pg.locator(".card[data-id='pay'] > .ftitle").bounding_box()
        assert t["y"] + t["height"] > dock["y"], "준비: 카드 이름이 입력창 높이에 있다"
        pg.keyboard.press("v")
        pg.dblclick(".card[data-id='pay'] > .ftitle")
        pg.wait_for_selector(".capbox [data-f='title']")
        pg.wait_for_timeout(300)                         # 카드가 골라져 칩 줄이 생기면(입력창이 커짐) 그만큼 더
        box, dock2 = pg.locator(".capbox").bounding_box(), pg.locator("#hdchat").bounding_box()
        assert box["y"] + box["height"] <= dock2["y"] - 8, (box, dock2)
        assert box["y"] >= pg.locator("#screens").bounding_box()["y"], "상자 위 끝은 판 안"
        pg.click(".capbox [data-f='purpose']"); pg.keyboard.press("End")
        for _ in range(4):
            pg.keyboard.press("Enter"); pg.keyboard.type("더 쓴 줄")
        pg.wait_for_timeout(100)
        box, dock2 = pg.locator(".capbox").bounding_box(), pg.locator("#hdchat").bounding_box()
        assert box["y"] + box["height"] <= dock2["y"] - 8, "쓰다가 길어져도 가리지 않게"
        shot(pg, "r25-caption-edit-clear-of-dock.png")
        pg.keyboard.press("Escape")
    finally:
        pg.close()
    assert not errors, errors
