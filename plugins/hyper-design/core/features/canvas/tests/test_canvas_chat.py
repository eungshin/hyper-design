"""하단 대화창 v0(S1) — 브라우저. 도우미로 연 캔버스(받는 곳 없음 = 대기열 .hd-queue, 실제 Paseo 없음).

카드 칩: 카드를 고르면 [결제] 칩 → 글 + Enter = 메모 하나 + 바로 보내기(위쪽 [보내기]와 같은 길) → 대기열 파일에 지금 요청문 형식, 입력창 비움, 상태 줄.
요소 칩: 고른 카드를 이동(V)으로 한 번 더 = 요소 막대 → [BUTTON "지금 결제하기"] 칩 → 보낸 요청문의 path 가 그 요소.
규칙(칩·범위·메모 초안·상태 말)은 test_canvas_unit_chat.py(unit).
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, zoom_to  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("chat")
SHOTS = Path(os.environ.get("HD_SHOTS_S1", Path(tempfile.gettempdir()) / "claude" / "tS1"))


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


@pytest.fixture()
def live(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-chat-"))
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
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.out = out
    yield pg
    pg.close()
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def queued(pg):
    pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
    assert pg.evaluate("window.__hdLastHelper.forward.via") == "queue"
    q = list((pg.out / ".hd-queue").glob("*.txt"))
    assert len(q) == 1, q
    return q[0].read_text(encoding="utf-8")


def chips(pg):
    return pg.locator("#hdchat .ch-chip").all_text_contents()


def card_click(pg, sid):
    b = pg.locator(f'.card[data-id="{sid}"] .cover').bounding_box()
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + 30)


def test_card_chip_send_makes_memo_and_forwards(live):
    pg = live
    pg.keyboard.press("0")
    pg.wait_for_selector("#hdchat .ch-box")
    box, tabs = pg.locator("#hdchat").bounding_box(), pg.locator("#ptabs").bounding_box() if pg.is_visible("#ptabs") else None
    vw = pg.viewport_size
    assert box["y"] + box["height"] <= vw["height"] and abs((box["x"] + box["width"] / 2) - vw["width"] / 2) < vw["width"] * 0.3, "판 아래 가운데"
    if tabs:
        assert box["y"] + box["height"] <= tabs["y"], "아래 프로젝트 탭을 가리지 않는다"
    assert pg.get_attribute("#hdchat textarea", "placeholder") == "무엇을 바꾸거나 만들까요?"
    assert chips(pg) == ["모든 화면"], "고른 것이 없으면 모든 화면"
    shot(pg, "s1-empty.png")

    pg.keyboard.press("v")
    card_click(pg, "pay")
    pg.wait_for_function("document.querySelectorAll('#hdchat .ch-chip').length && document.querySelector('#hdchat .ch-chip').textContent.startsWith('결제')")
    assert [c.replace("×", "") for c in chips(pg)] == ["결제"]
    pg.click("#hdchat textarea")
    pg.keyboard.type("버튼을 더 크게")
    pg.keyboard.press("Shift+Enter")
    pg.keyboard.type("색은 그대로")
    assert pg.input_value("#hdchat textarea") == "버튼을 더 크게\n색은 그대로", "Shift+Enter = 줄바꿈"
    shot(pg, "s1-chips.png")
    pg.keyboard.press("Enter")
    text = queued(pg)
    assert "1. screen=pay · path=body · no=1" in text and "요청: 버튼을 더 크게" in text and "범위: 이 화면 전체" in text, text
    assert pg.input_value("#hdchat textarea") == "", "보내면 입력창을 비운다"
    pg.wait_for_function("(() => { const l = document.querySelector('#hdchat .ch-line'); return l && !l.hidden && /보냄|대기열/.test(l.textContent); })()", timeout=5000)
    line = pg.text_content("#hdchat .ch-line")
    assert pg.evaluate("document.querySelector('#hdchat .ch-line').classList.contains('pulse')"), "새 줄 = 맥박 한 번"
    assert "버튼을 더 크게" in line and ("보냄" in line or "대기열" in line), line
    assert pg.evaluate("document.querySelector('.card[data-id=\"pay\"]').classList.contains('picked')"), "보낸 뒤에도 고른 카드·캔버스 그대로"
    # 칩 빼기 = 모든 화면으로 넓어짐
    pg.click("#hdchat .ch-chip button")
    assert chips(pg) == ["모든 화면"]
    shot(pg, "s1-after-send.png")


def test_element_chip_puts_element_path_in_request(live):
    pg = live
    ph = zoom_to(pg, "pay", 420)
    fr = None
    for _ in range(100):
        f = pg.query_selector('.card[data-id="pay"] .phone iframe')
        fr = f and f.content_frame()
        if fr and fr.url.split("?")[0].endswith("/pay.html"):
            break
        pg.wait_for_timeout(100)
    fr.wait_for_selector("button.pay", state="attached", timeout=5000)
    r = fr.evaluate("() => { const b = document.querySelector('button.pay').getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }")
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    xy = (ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc)
    pg.keyboard.press("v")
    pg.mouse.click(*xy)
    pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(*xy)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    pg.wait_for_selector("#hdchat .ch-chip.el", timeout=3000)
    el = pg.locator("#hdchat .ch-chip.el")
    assert el.text_content().replace("×", "") == 'BUTTON "지금 결제하기"'
    path = el.get_attribute("data-key").split(":", 2)[2]
    shot(pg, "s1-element-chip.png")
    assert "button.pay" in path
    pg.click("#hdchat textarea")
    pg.keyboard.type("문구를 '결제하기'로")
    pg.click("#hdchat .ch-send")
    text = queued(pg)
    assert f"screen=pay · path={path}" in text and "요청: 문구를 '결제하기'로" in text and "범위:" not in text, text
    assert text.count("screen=") == 1, "요소 칩이 있으면 그 화면의 화면 메모는 따로 나가지 않는다"
