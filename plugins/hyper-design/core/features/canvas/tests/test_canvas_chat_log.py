"""대화 패널(S3) — 브라우저(Playwright) + 같은 프로세스 도우미. 실제 Paseo·Claude 에 보내지 않고 아무것도 띄우지 않는다
(에이전트 = 테스트의 HTTP hello/progress/reply, Paseo = 없는 경로, HD_HOME = 임시, 터미널 대화 = 테스트가 끼운 가짜 주소·이벤트).

(a) 대화창으로 보냄 → 패널(왼쪽 도크)에 내 요청 · 보냄 · 진행 · AI 반영 · 답 · 끝 ✓ 차례로, 새로고침 뒤에도 그대로 · 턴 누르기 = 카드 강조 · [되돌리기]
(b) 대화 탭을 오른쪽 도크로 끌고 다시 왼쪽으로 — 새로고침해도 그 쪽
(c) 패널이 열려 있으면 입력창은 패널 아래, 닫으면 판 아래 떠 있는 입력창 · 창 메뉴 '대화'로 다시
(d) 받는 곳 터미널의 대화(S3b 모양): 시간 차례로 섞기 · '터미널에서' · 도구 줄 접힘 · 같은 요청 한 번 · 못 읽으면 조용한 한 줄
규칙(턴·상태·줄·섞기)은 test_canvas_unit_chat_log.py, 서버 기록은 test_canvas_unit_chat_log_py.py(unit).
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402
import router  # noqa: E402

pytestmark = pytest.mark.area("chat", "dock")
SHOTS = Path(os.environ.get("HD_SHOTS_S3", Path(tempfile.gettempdir()) / "claude" / "tS3"))


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


@pytest.fixture()
def served(monkeypatch):
    monkeypatch.delenv("HD_ALLOW_SPAWN", raising=False)
    monkeypatch.delenv("HD_CLAUDE_WAKE", raising=False)
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-talk-"))
    monkeypatch.setenv("HD_HOME", str(tmp / "home"))   # 진짜 ~/.hyper-design 을 읽지 않는다
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    srv = helper.make_server(out, 0, paseo=str(tmp / "no-paseo" / "paseo.cmd"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield out, srv
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)


def call(srv, method, path, body=None):
    base = srv.url.split("/index.html")[0].split("?")[0]
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method, headers={"X-HD-Token": srv.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def open_page(ctx, srv, clear=True):
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1440, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    if clear:
        pg.evaluate("localStorage.removeItem('hd-dock')")
        pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.wait_for_selector("#pTalk .tk-list")
    return pg, errors


def texts(pg, sel):
    return pg.eval_on_selector_all(sel, "els => els.map(e => e.innerText.trim())")


def note_saved(pg, srv):
    nid = pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.indexOf('hd-chat-last:') === 0))).ids[0]")
    for _ in range(50):                                  # 캔버스가 보낸 메모를 상태 파일에 저장할 때까지
        st = call(srv, "GET", "/api/state")[1].get("state") or {}
        if any(n.get("id") == nid and n.get("sent") for n in st.get("notes") or []):
            return nid
        pg.wait_for_timeout(200)
    return nid


def test_send_shows_whole_turn_and_survives_reload(served, ctx):
    out, srv = served
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-1", "name": "클로드 작업자", "kind": "claude"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/attach", {"agent": "ag-1"})[0] == 200
    pg, errors = open_page(ctx, srv)
    try:
        lb, sc = pg.locator("#ldock").bounding_box(), pg.locator("#screens").bounding_box()
        assert lb and lb["x"] == 0 and lb["width"] == 340, "대화 패널은 처음에 왼쪽 도크"
        assert abs(sc["x"] - 340) <= 1, "판은 왼쪽 도크 옆에서 시작"
        assert pg.evaluate("!!document.getElementById('hdchat').closest('#pTalk')"), "입력창은 패널 아래"
        assert pg.locator("#tools").bounding_box()["x"] > 340, "도구 막대는 판 안 — 패널에 가리지 않는다"
        pg.click("#hdchat textarea")
        pg.keyboard.type("결제 버튼을 더 크게")
        pg.keyboard.press("Enter")
        pg.wait_for_function("document.querySelector('#pTalk .tk-turn .tk-ask') && document.querySelector('#pTalk .tk-turn .tk-ask').innerText.includes('결제 버튼을 더 크게')", timeout=15000)
        pg.wait_for_function("[...document.querySelectorAll('#pTalk .tk-l')].some(l => l.innerText.includes('보냄 · 클로드 작업자 (실시간)'))", timeout=15000)
        assert pg.get_attribute("#pTalk .tk-turn", "data-state") == "running" and pg.is_visible("#pTalk .tk-turn .tk-ic")
        assert call(srv, "POST", "/api/progress", {"agent": "ag-1", "text": "pay.html 읽는 중", "screen": "pay"})[0] == 200
        pg.wait_for_function("[...document.querySelectorAll('#pTalk .tk-l')].some(l => l.innerText === 'pay.html 읽는 중')", timeout=15000)
        # AI 가 덮개 안에서 파일을 쓴다(claim → 쓰기 → 지켜보기 → release) = AI 반영 줄 + 되돌리기
        nid = note_saved(pg, srv)
        assert call(srv, "POST", "/api/claim", {"screen": "pay", "by": "ag-1", "note": nid})[0] == 200
        f = out / "screens" / "pay.html"
        time.sleep(0.05)
        f.write_text(f.read_text(encoding="utf-8").replace("지금 결제하기", "크게 결제하기"), encoding="utf-8")
        pg.wait_for_function("[...document.querySelectorAll('#pTalk .tk-l')].some(l => l.dataset.kind === 'write')", timeout=15000)
        shot(pg, "s3-panel-left-running.png")
        code, res = call(srv, "POST", "/api/reply", {"note": nid, "reply": {"kind": "반영됨", "what": "버튼을 키웠어요", "screens": ["pay"], "captured": False, "by": "ag-1"}})
        assert code == 200, res
        assert call(srv, "POST", "/api/release", {"screen": "pay"})[0] == 200
        pg.wait_for_function("document.querySelector('#pTalk .tk-turn').dataset.state === 'done'", timeout=15000)
        kinds = pg.eval_on_selector_all("#pTalk .tk-turn .tk-l", "els => els.map(e => e.dataset.kind)")
        assert kinds[:2] == ["sent", "progress"] and "write" in kinds and kinds[-1] == "reply", kinds
        assert "버튼을 키웠어요" in texts(pg, "#pTalk .tk-l[data-kind='reply']")[0]
        assert pg.text_content("#pTalk .tk-turn .tk-ic") == "✓" and pg.is_visible("#pTalk .tk-undo")
        # 다음 요청(대기열 없이 아직 작업 중) — 끝난 턴 + 작업 중 턴
        pg.click("#hdchat textarea")
        pg.keyboard.type("완료 화면 제목 바꾸기")
        pg.keyboard.press("Enter")
        pg.wait_for_function("document.querySelectorAll('#pTalk .tk-turn').length === 2", timeout=15000)
        pg.wait_for_function("document.querySelectorAll('#pTalk .tk-turn')[1].dataset.state === 'running'", timeout=15000)
        shot(pg, "s3-panel-left-done-and-running.png")

        # 턴 누르기 = 닿은 카드 강조
        pg.click("#pTalk .tk-turn[data-state='done'] .tk-ask")
        pg.wait_for_selector(".card[data-id='pay'].tk-hl")

        # 새로고침 = 서버 기록으로 그대로
        pg.reload()
        pg.wait_for_function("document.querySelectorAll('#pTalk .tk-turn').length === 2", timeout=15000)
        assert texts(pg, "#pTalk .tk-turn .tk-ask")[0].startswith("결제 버튼을 더 크게")
        assert "pay.html 읽는 중" in texts(pg, "#pTalk .tk-turn .tk-l")

        # 되돌리기 = 48c 되살리기 → 파일이 돌아온다
        pg.click("#pTalk .tk-turn[data-state='done'] .tk-undo")
        pg.wait_for_function("document.querySelector('#pTalk .tk-turn').dataset.state === 'undone'", timeout=15000)
        assert "지금 결제하기" in f.read_text(encoding="utf-8")

        # 빌드 실패 = 빨간 줄(이벤트는 세션 버스에 바로 — 실제 빌드를 깨지 않는다)
        srv.session.events.publish("build.failed", reason="screens/done.html 을 읽지 못했어요", reverted=[], kept=[], ids=[], stamps=[], screens=["done"], repaired=True)
        pg.wait_for_selector("#pTalk .tk-l[data-tone='red']", timeout=15000)
        assert "빌드 실패" in pg.text_content("#pTalk .tk-l[data-tone='red']")
        assert pg.evaluate("getComputedStyle(document.querySelector('#pTalk .tk-l[data-tone=\"red\"]')).color") != pg.evaluate(
            "getComputedStyle(document.querySelector('#pTalk .tk-l[data-kind=\"sent\"]')).color")
        pg.wait_for_selector("#pTalk .tk-turn[data-state='failed']", timeout=15000)
        assert pg.text_content("#pTalk .tk-turn[data-state='failed'] .tk-st").strip() == "", "실패는 빨간 줄 하나로 — 꼬리 '! 실패' 없음(R27 F04)"
        pg.wait_for_timeout(300)
        assert "빌드가 깨져" not in (pg.text_content("#toast") or "") or pg.is_hidden("#toast"), "대화 패널이 보이면 실패 토스트는 띄우지 않는다(R27 F04)"
        shot(pg, "s3-failed-build-line.png")
        recs = call(srv, "GET", "/api/chat")[1]["records"]
        assert [r["kind"] for r in recs][:2] == ["ask", "sent"] or [r["kind"] for r in recs][:2] == ["sent", "ask"]
        assert (out / ".hd-chat.jsonl").is_file()
    finally:
        pg.close()
    assert not errors, errors


def drag(pg, src, dst_xy):
    b = pg.locator(src).bounding_box()
    pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(b["x"] + 20, b["y"] + 30, steps=4)
    pg.mouse.move(dst_xy[0], dst_xy[1], steps=8)
    pg.mouse.up()


def test_drag_panel_between_sides_and_reload(served, ctx):
    out, srv = served
    pg, errors = open_page(ctx, srv)
    try:
        g0 = pg.locator("#dock .dk-g[data-g='0'] .dk-tabs").bounding_box()
        drag(pg, "#ldock .dk-tab[data-p='talk']", (g0["x"] + g0["width"] - 30, g0["y"] + g0["height"] / 2))
        pg.wait_for_selector("#dock .dk-tab[data-p='talk']")
        assert pg.evaluate("document.getElementById('ldock').classList.contains('empty')"), "왼쪽 도크는 비면 자리를 차지하지 않는다"
        assert pg.locator("#screens").bounding_box()["x"] == 0
        assert pg.evaluate("!!document.getElementById('hdchat').closest('#dock')"), "오른쪽에서도 입력창은 패널 아래"
        shot(pg, "s3-panel-moved-right.png")
        pg.reload()
        pg.wait_for_selector("#dock .dk-tab[data-p='talk']")
        assert pg.locator("#ldock .dk-tab").count() == 0, "새로고침해도 오른쪽"
        # 다시 왼쪽으로 — 끄는 동안만 왼쪽 끝에 놓을 자리
        b = pg.locator("#dock .dk-tab[data-p='talk']").bounding_box()
        pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        pg.mouse.down()
        pg.mouse.move(b["x"] - 40, b["y"] + 40, steps=4)
        assert pg.evaluate("document.body.classList.contains('dk-dragging')") and pg.is_visible("#ldock")
        pg.mouse.move(10, 400, steps=10)
        pg.mouse.up()
        pg.wait_for_selector("#ldock .dk-tab[data-p='talk']")
        pg.reload()
        pg.wait_for_selector("#ldock .dk-tab[data-p='talk']")
        assert pg.evaluate("JSON.parse(localStorage.getItem('hd-dock')).left[0].tabs") == ["talk"]
    finally:
        pg.close()
    assert not errors, errors


def test_composer_moves_with_panel(served, ctx):
    out, srv = served
    pg, errors = open_page(ctx, srv)
    try:
        assert pg.evaluate("!!document.getElementById('hdchat').closest('#pTalk')")
        box, panel = pg.locator("#hdchat").bounding_box(), pg.locator("#ldock").bounding_box()
        assert box["x"] >= panel["x"] and box["x"] + box["width"] <= panel["x"] + panel["width"] + 1, "입력창은 패널 폭 안"
        assert abs((box["y"] + box["height"]) - (panel["y"] + panel["height"])) < 16, "패널 맨 아래"
        assert pg.is_hidden("#hdchat .ch-line") and pg.is_hidden("#hdchat .ch-hide")
        shot(pg, "s3-composer-in-panel.png")
        pg.hover("#ldock .dk-tab[data-p='talk']")
        pg.click("#ldock .dk-tab[data-p='talk'] .dk-x")
        pg.wait_for_function("document.getElementById('hdchat').parentNode === document.body")
        b2, sc = pg.locator("#hdchat").bounding_box(), pg.locator("#screens").bounding_box()
        assert abs((b2["x"] + b2["width"] / 2) - (sc["x"] + sc["width"] / 2)) < 2 and b2["y"] > 700, "닫으면 판 아래 가운데"
        pg.click("#wbtn")
        assert pg.is_enabled("#wmenu .wm-row[data-w='chat']"), "패널을 닫으면 '대화창' 설정이 다시 쓰인다"
        pg.click("#wmenu .wm-row[data-w='talk']")
        pg.wait_for_function("!!document.getElementById('hdchat').closest('#pTalk')")
        assert pg.is_disabled("#wmenu .wm-row[data-w='chat']"), "패널이 열려 있으면 '대화창' 줄은 꺼짐"
        assert pg.locator("#ldock .dk-tab[data-p='talk']").count() == 1, "다시 열면 집 쪽(왼쪽)"
    finally:
        pg.close()
    assert not errors, errors


def test_terminal_transcript_merges_into_timeline(served, ctx, monkeypatch):
    out, srv = served
    asked = []

    def fake(s, q, b):                                   # S3b 가 오기 전 가짜 — 공급자 없이 모양만(계약: entries · cursor · source)
        asked.append((q.get("agent", [None])[0], q.get("since", [None])[0]))
        if q.get("agent", [None])[0] == "ag-none":
            return 200, {"entries": [], "cursor": None, "source": "none"}
        now = int(time.time() * 1000)
        return 200, {"entries": [
            {"id": "e1", "role": "user", "text": "터미널에서 직접 물어본 것", "at": now - 60000},
            {"id": "e2", "role": "tool", "text": "Read screens/pay.html\n(120 lines)", "at": now - 59000},
            {"id": "e3", "role": "assistant", "text": "결제 화면을 읽었어요", "at": now - 58000}], "cursor": "c1", "source": "claude"}
    monkeypatch.setitem(router.ROUTES["GET"], "/api/agents/transcript", fake)
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-1", "name": "클로드", "kind": "claude"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/attach", {"agent": "ag-1"})[0] == 200
    pg, errors = open_page(ctx, srv)
    try:
        pg.wait_for_selector("#pTalk .tk-term[data-id='e3']", timeout=15000)
        assert pg.text_content("#pTalk .tk-term[data-role='user'] .tk-who") == "터미널에서"
        assert pg.evaluate("!document.querySelector('#pTalk .tk-term[data-role=\"tool\"] details').open"), "도구 줄은 접혀 있다"
        assert pg.text_content("#pTalk .tk-term[data-role='tool'] summary").startswith("도구 · Read screens/pay.html")
        pg.click("#pTalk .tk-term[data-role='tool'] summary")
        assert pg.is_visible("#pTalk .tk-term[data-role='tool'] pre")
        # 캔버스에서 보낸 요청 — 터미널에도 찍혀 오면 한 번만
        pg.click("#hdchat textarea"); pg.keyboard.type("결제 버튼 키우기"); pg.keyboard.press("Enter")
        pg.wait_for_selector("#pTalk .tk-turn", timeout=15000)
        now = int(time.time() * 1000)
        srv.session.events.publish("agent.transcript", agent="ag-1", entries=[
            {"id": "e4", "role": "user", "text": "hyper-design 요청: 결제 버튼 키우기", "at": now},
            {"id": "e5", "role": "assistant", "text": "키울게요", "at": now + 1}])
        pg.wait_for_selector("#pTalk .tk-term[data-id='e5']", timeout=15000)
        assert pg.locator("#pTalk .tk-term[data-id='e4']").count() == 0, "같은 요청은 턴 하나로"
        order = pg.eval_on_selector_all("#pTalk .tk-list > li", "els => els.map(e => e.dataset.id || ('t' + e.dataset.turn))")
        assert order.index("e1") < order.index("e3") < order.index([x for x in order if x.startswith("t")][0]) < order.index("e5"), order
        assert pg.is_visible("#pTalk .tk-term[data-role='tool'] pre"), "다시 그려도 펼친 도구 줄은 펼친 채"
        shot(pg, "s3-terminal-transcript.png")
        # 가져올 수 없는 터미널 = 조용한 한 줄
        assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-none", "name": "없음", "kind": "paseo"}, "lease": 300})[0] == 200
        assert call(srv, "POST", "/api/attach", {"agent": "ag-none"})[0] == 200
        pg.evaluate("window.__hdAgent = 'ag-none'")
        pg.wait_for_selector("#pTalk .tk-quiet", timeout=15000)
        assert pg.text_content("#pTalk .tk-quiet") == "이 터미널의 대화는 가져올 수 없어요"
        assert pg.locator("#pTalk .tk-term").count() == 0
    finally:
        pg.close()
    assert not errors, errors
    assert asked and asked[0][0] == "ag-1"


def test_without_helper_the_panel_is_absent(served, ctx):
    """file:// 로 연 캔버스(도우미 없음) — 대화 기록·진행이 없으니 대화 패널은 이 페이지에 없다(저장 배치는 그대로), 입력창은 판 아래(S1)."""
    out, srv = served
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1440, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto((out / "index.html").resolve().as_uri())
        pg.evaluate("localStorage.removeItem('hd-dock')")
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_timeout(300)
        assert pg.evaluate("document.getElementById('ldock').classList.contains('empty')") and pg.locator("#screens").bounding_box()["x"] == 0
        assert pg.evaluate("document.getElementById('hdchat').parentNode === document.body"), "입력창은 판 아래"
        pg.click("#wbtn")
        assert pg.is_disabled("#wmenu .wm-row[data-w='talk']") and pg.is_enabled("#wmenu .wm-row[data-w='chat']")
        pg.click("#wmenu .wm-row[data-w='tools']")          # 다른 창 설정을 바꿔 저장해도
        assert json.loads(pg.evaluate("localStorage.getItem('hd-dock')"))["left"][0]["tabs"] == ["talk"], "저장 배치의 대화 자리는 그대로(도우미로 열면 왼쪽에)"
    finally:
        pg.close()
    assert not errors, errors
