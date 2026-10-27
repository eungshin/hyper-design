"""받는 터미널 정보 · 진짜 이미지 보내기(R28, 시안 A) — 브라우저 한 길.

도우미로 연 캔버스(받는 곳 = 가짜 id 'a1', paseo = 없는 경로 — 실제 Paseo 에이전트에 아무것도 보내지 않는다).
/api/agents/info · /api/agents/effort 는 페이지 쪽에서 가로채 답한다(page.route). /api/forward 는 본문만 적고 도우미로 그대로 넘긴다(없는 paseo → 대기열).
보는 것: 대화창 아래 줄에 모델 'Opus 5.5'(툴팁) · 생각 깊이 'medium ▾' · 고리 34%(툴팁 '컨텍스트 340k / 1M 토큰 · 34% 사용') →
  메뉴에서 high = POST {effort:'high'} → 알약 high · 실패(502) = 토스트 + 알약 그대로 · 이미지 붙여 보내기 = 본문 images 에 그 절대 경로 ·
  받는 곳이 Paseo 가 아니면 줄째 숨김. 규칙은 test_canvas_unit_agent_info.py · 서버는 test_canvas_unit_agent_meta.py.
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY, DONE
from test_canvas_chat import BOTTOM
from test_canvas_attach import give, saved_chip

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("chat")
SHOTS = Path(os.environ.get("HD_SHOTS_R28", Path(tempfile.gettempdir()) / "claude" / "r28-impl"))

INFO = {"agent": "a1", "paseo": True, "name": "클로드", "provider": "claude", "model": "claude-opus-5-5", "modelLabel": "Opus 5.5",
        "effort": "medium", "effortOptions": ["low", "medium", "high", "xhigh", "max"], "context": {"used": 340000, "max": 1000000, "pct": 34}}


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


@pytest.fixture()
def live(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-r28-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다"},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝"}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    srv = helper.make_server(out, 0, agent="a1", paseo=str(tmp / "없음" / "paseo.cmd"))   # 없는 paseo — 넘기기는 실패해 대기열로
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1440, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    state = {"info": dict(INFO), "effort": [], "forward": [], "fail": False}

    def info(route):
        route.fulfill(status=200, content_type="application/json", body=json.dumps(state["info"], ensure_ascii=False))

    def effort(route):
        body = json.loads(route.request.post_data or "{}")
        state["effort"].append(body)
        if state["fail"]:
            route.fulfill(status=502, content_type="application/json", body=json.dumps({"error": "생각 깊이를 바꾸지 못했어요 — not supported"}, ensure_ascii=False))
            return
        state["info"] = dict(state["info"], effort=body["effort"])
        route.fulfill(status=200, content_type="application/json", body=json.dumps(state["info"], ensure_ascii=False))

    def forward(route):
        state["forward"].append(json.loads(route.request.post_data or "{}"))
        route.continue_()
    pg.route("**/api/agents/info*", info)
    pg.route("**/api/agents/effort*", effort)
    pg.route("**/api/forward*", forward)
    pg.add_init_script(BOTTOM)
    pg.goto(srv.url, timeout=90000)                    # 첫 페이지는 데이터 도장 확인 빌드가 들 수 있다(부하 때 30초 넘음)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.out, pg.state = out, state
    yield pg
    pg.close()
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def test_footer_effort_and_real_image_send(live):
    pg, st = live, live.state
    pg.wait_for_selector("#hdchat .hd-ainfo:not([hidden])", timeout=8000)
    f = "#hdchat .hd-ainfo"
    assert pg.text_content(f + " .ai-model").strip() == "Opus 5.5"   # 좁은 대화창이면 글은 감추고 아이콘(툴팁에 이름)
    assert pg.inner_text(f + " .ai-effort").strip() == "medium"
    assert pg.inner_text(f + " .ai-ring").strip() == "34%"
    size = pg.evaluate(f"parseFloat(getComputedStyle(document.querySelector('{f} .ai-model')).fontSize)")
    assert 11 <= size <= 12, "조용한 12px 줄(내용이 먼저)"
    pg.hover(f + " .ai-ring")
    assert pg.inner_text(f + " .ai-tip") == "컨텍스트 340k / 1M 토큰 · 34% 사용"
    shot(pg, "r28-footer-ring-tip.png")
    pg.hover(f + " .ai-model")
    assert pg.inner_text(f + " .ai-tip") in ("모델은 Paseo에서 바꿔요", "Opus 5.5 · 모델은 Paseo에서 바꿔요")
    assert pg.locator(f + " .ai-model button, " + f + " .ai-model[aria-haspopup]").count() == 0, "모델은 보기만(메뉴 없음)"

    pg.click(f + " .ai-effort")
    pg.wait_for_selector(f + " .ai-menu:not([hidden])")
    assert pg.eval_on_selector_all(f + " .ai-menu button", "bs => bs.map(b => b.dataset.opt)") == ["low", "medium", "high", "xhigh", "max"]
    assert pg.get_attribute(f + ' .ai-menu button[data-opt="medium"]', "aria-checked") == "true"
    shot(pg, "r28-footer-effort-menu.png")
    pg.click(f + ' .ai-menu button[data-opt="high"]')
    pg.wait_for_function(f"document.querySelector('{f} .ai-effort').textContent.trim() === 'high'", timeout=5000)
    assert st["effort"] == [{"effort": "high"}]
    assert pg.is_hidden(f + " .ai-menu")

    st["fail"] = True                                  # Paseo 가 거절 = 토스트(까닭) + 알약 그대로
    pg.click(f + " .ai-effort")
    pg.click(f + ' .ai-menu button[data-opt="max"]')
    pg.wait_for_function("document.querySelector('#toast') && /not supported/.test(document.querySelector('#toast').textContent)", timeout=5000)
    assert pg.inner_text(f + " .ai-effort").strip() == "high"
    assert pg.inner_text("#toast").count("생각 깊이를 바꾸지 못했어요") == 1, "까닭은 한 번만"

    give(pg, "#hdchat textarea")                       # 이미지 붙여 보내기 → 본문 images = 그 절대 경로(서버가 paseo send --image)
    saved_chip(pg, "#hdchat")
    pg.click("#hdchat textarea")
    pg.keyboard.type("이 스크린샷처럼 키워 주세요")
    shot(pg, "r28-composer-thumb.png")
    pg.keyboard.press("Enter")
    pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
    body = st["forward"][-1]
    files = sorted((pg.out / ".hd-attach").glob("*.png"))
    assert len(files) == 1 and body.get("images") == [str(files[0].resolve())], body
    assert ("첨부 이미지: " + str(files[0].resolve())) in body["text"], "경로 줄도 그대로(대기열·다른 받는 곳)"

    st["info"] = {"agent": "hello", "paseo": False}    # 받는 곳이 Paseo 가 아니면 줄째 숨김
    pg.evaluate("document.dispatchEvent(new CustomEvent('hd-agent', {detail: {}}))")
    pg.wait_for_selector("#hdchat .hd-ainfo", state="hidden", timeout=5000)
    shot(pg, "r28-footer-hidden.png")
