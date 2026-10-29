"""대화 패널(S3) — 브라우저(Playwright) + 같은 프로세스 도우미. 실제 Paseo·Claude 에 보내지 않고 아무것도 띄우지 않는다
(에이전트 = 테스트의 HTTP hello/progress/reply, Paseo = 없는 경로, HD_HOME = 임시, 터미널 대화 = 테스트가 끼운 가짜 주소·이벤트).

(a) 대화창으로 보냄 → 패널(왼쪽 도크)에 내 요청 · 보냄 · 진행 · AI 반영 · 답 · 끝 ✓ 차례로, 새로고침 뒤에도 그대로 · 턴 누르기 = 카드 강조 · [되돌리기]
(b) 대화 창 하나(R53): 머리 줄을 끌어 판 끝 40px 안에 놓으면 붙고(왼쪽 360px), 끝에서 떼면 펼친 창으로 뜨고, 새로고침해도 그 배치
(c) 접힘(입력창만) ↔ 펼침(기록 + 입력창) ↔ 붙음 단추 · 입력창은 늘 창 맨 아래 · 창 메뉴 '대화창' 한 줄로 숨기기·보이기
(d) 받는 곳 터미널의 대화(S3b 모양): 시간 차례로 섞기 · '터미널에서' · 도구 줄 전문(접지 않음) · 같은 요청 한 번 · 못 읽으면 조용한 한 줄
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
        assert lb and lb["x"] == 0 and lb["width"] == 360, "대화 창은 처음에 왼쪽에 붙은 펼친 창(360px — R53 사용자 승인)"
        assert abs(sc["x"] - 360) <= 1, "판은 왼쪽 도크 옆에서 시작"
        assert pg.evaluate("!!document.getElementById('hdchat').closest('#hdtalk.tw-docked')"), "입력창은 같은 창 맨 아래"
        assert pg.locator("#tools").bounding_box()["x"] > 360, "도구 막대는 판 안 — 창에 가리지 않는다"
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


def head_drag(pg, dst_xy, sel="#hdtalk .tw-head"):
    b = pg.locator(sel).bounding_box()
    x0, y0 = b["x"] + min(60, b["width"] / 2), b["y"] + b["height"] / 2
    pg.mouse.move(x0, y0)
    pg.mouse.down()
    pg.mouse.move(x0 + 20, y0 + 20, steps=4)
    pg.mouse.move(dst_xy[0], dst_xy[1], steps=10)
    return lambda: pg.mouse.up()


def frame(pg):
    return pg.evaluate("""() => { const f = document.getElementById('hdtalk'), r = f.getBoundingClientRect(), c = document.getElementById('hdchat').getBoundingClientRect();
      return {cls: f.className, x: r.x, y: r.y, w: r.width, h: r.height, b: r.bottom, chatB: c.bottom,
              inDock: f.closest('#ldock') ? 'left' : f.closest('#dock') ? 'right' : null}; }""")


def saved_side(pg):
    st = json.loads(pg.evaluate("localStorage.getItem('hd-dock')"))
    if any("talk" in g["tabs"] for g in st.get("left", [])):
        return "left"
    if any("talk" in g["tabs"] for g in st["groups"]):
        return "right"
    return "float"


def test_drag_header_docks_at_edges_and_undocks_and_reload(served, ctx):
    """R53 happy path: 붙은 창 머리 줄을 끌어 떼면 펼친 창 → 판 왼쪽 끝 40px 안 = '놓으면 왼쪽에 붙어요' 미리보기 → 놓으면 왼쪽 360px ·
    오른쪽 끝 = 오른쪽 도크 · 새로고침해도 그 배치."""
    out, srv = served
    pg, errors = open_page(ctx, srv)
    try:
        f = frame(pg)
        assert f["inDock"] == "left" and "tw-docked" in f["cls"] and abs(f["w"] - 360) <= 1, f
        assert pg.locator("#ldock .dk-tabs").first.is_hidden(), "혼자 붙은 창 = 탭 줄 대신 창 머리 줄"
        assert abs(pg.locator("#hdtalk .tw-head").bounding_box()["height"] - 36) <= 1, "머리 줄 36px"
        # 떼기 — 판 가운데로 끌면 펼친 창이 따라온다
        up = head_drag(pg, (760, 300))
        assert "tw-expanded" in frame(pg)["cls"] and pg.evaluate("document.getElementById('ldock').classList.contains('empty')"), "떨어지면 왼쪽 도크 자리 없어짐"
        assert pg.is_hidden(".tw-hint"), "가운데 = 붙지 않음"
        up()
        pg.wait_for_timeout(200)
        f = frame(pg)
        assert "tw-expanded" in f["cls"] and f["inDock"] is None and pg.locator("#screens").bounding_box()["x"] == 0, f
        assert abs(f["chatB"] - f["b"]) <= 12, "입력창은 창 맨 아래"
        assert saved_side(pg) == "float"
        shot(pg, "r53-undocked.png")
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_selector("#hdtalk.tw-expanded")
        g = frame(pg)
        assert abs(g["x"] - f["x"]) <= 2 and abs(g["y"] - f["y"]) <= 2 and abs(g["w"] - f["w"]) <= 2, ("새로고침해도 그 자리", f, g)
        # 왼쪽 끝 40px 안 = 미리보기 → 놓으면 왼쪽 360
        up = head_drag(pg, (20, 400))
        assert pg.evaluate("document.body.classList.contains('tw-snap-left')") and pg.is_visible(".tw-hint")
        assert pg.text_content(".tw-hint") == "놓으면 왼쪽에 붙어요"
        z = pg.locator("#ldock").bounding_box()
        assert z and z["x"] == 0 and abs(z["width"] - 360) <= 2, ("미리보기 = 붙을 자리 360px", z)
        shot(pg, "r53-drag-to-dock.png")
        up()
        pg.wait_for_selector("#ldock #hdtalk.tw-docked")
        assert abs(pg.locator("#ldock").bounding_box()["width"] - 360) <= 1 and pg.is_hidden(".tw-hint")
        # 오른쪽 끝 = 오른쪽 도크
        sc = pg.locator("#screens").bounding_box()
        up = head_drag(pg, (sc["x"] + sc["width"] - 10, 400))
        assert pg.evaluate("document.body.classList.contains('tw-snap-right')") and pg.text_content(".tw-hint") == "놓으면 오른쪽에 붙어요"
        up()
        pg.wait_for_selector("#dock #hdtalk.tw-docked")
        assert pg.evaluate("document.getElementById('ldock').classList.contains('empty')")
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_selector("#dock #hdtalk.tw-docked")
        assert saved_side(pg) == "right"
    finally:
        pg.close()
    assert not errors, errors


def test_compact_expanded_docked_buttons_and_window_menu(served, ctx):
    """R53: 붙은 창 접기 = 판 아래 가운데 접힌 창(입력창만 + 알약 + 펼치기) · 펼치기 = 기록 + 입력창 떠 있는 창 · 붙이기 = 왼쪽 ·
    입력창 위 상태 줄·숨김 단추 없음 · 창 메뉴는 '대화창' 한 줄(대화 패널 줄 없음)로 숨기기·보이기."""
    out, srv = served
    pg, errors = open_page(ctx, srv)
    try:
        assert pg.locator("#hdchat .ch-line").count() == 0 and pg.locator("#hdchat .ch-hide").count() == 0
        assert pg.is_visible("#hdtalk .tw-head .tw-dock") and pg.locator("#hdtalk .tw-head button").count() == 2, "머리 줄 단추 = 떼기·접기(닫기 없음)"
        pg.click("#hdtalk .tw-fold")
        pg.wait_for_selector("#hdtalk.tw-compact")
        f, sc = frame(pg), pg.locator("#screens").bounding_box()
        assert abs((f["x"] + f["w"] / 2) - (sc["x"] + sc["width"] / 2)) < 2 and f["b"] > 820, ("접힘 = 판 아래 가운데", f, sc)
        assert pg.is_hidden("#pTalk") and pg.is_visible("#hdtalk .tw-pill") and pg.is_visible("#hdtalk .tw-expand"), "접힘 = 입력창만 + 알약 + 펼치기"
        assert abs(f["chatB"] - f["b"]) <= 1
        shot(pg, "r53-compact.png")
        pg.click("#hdtalk .tw-expand")
        pg.wait_for_selector("#hdtalk.tw-expanded")
        f = frame(pg)
        assert pg.is_visible("#pTalk .tk-list") and f["h"] > 300 and abs(f["chatB"] - f["b"]) <= 12, ("펼침 = 기록 + 입력창", f)
        assert pg.evaluate("getComputedStyle(document.querySelector('#hdtalk')).position") == "fixed"
        pg.click("#hdtalk .tw-fold")
        pg.wait_for_selector("#hdtalk.tw-compact")
        pg.click("#hdtalk .tw-pill")                     # 알약 누르기 = 펼치기
        pg.wait_for_selector("#hdtalk.tw-expanded")
        pg.click("#hdtalk .tw-dock")                     # 붙이기 = 왼쪽
        pg.wait_for_selector("#ldock #hdtalk.tw-docked")
        pg.click("#wbtn")
        assert pg.locator("#wmenu .wm-row[data-w='talk']").count() == 0, "대화 패널 줄은 없다 — '대화창' 한 줄"
        pg.click("#wmenu .wm-row[data-w='chat']")
        pg.wait_for_selector("#hdtalk", state="hidden")
        assert pg.evaluate("document.getElementById('ldock').classList.contains('empty')") and pg.locator("#screens").bounding_box()["x"] == 0, "숨기면 자리도 없다"
        pg.click("#wmenu .wm-row[data-w='chat']")
        pg.wait_for_selector("#ldock #hdtalk.tw-docked")
    finally:
        pg.close()
    assert not errors, errors


def test_narrow_window_hides_model_name(served, ctx):
    """R53: 창 폭 ~460px 아래면 입력창 아래 줄이 좁은 줄(모델 이름 글은 view-agent-info 의 440px 컨테이너 규칙으로 감춤)."""
    out, srv = served
    pg, errors = open_page(ctx, srv)
    try:
        q = "(() => { const t = document.querySelector('#hdchat .ch-tools'); return t ? t.getBoundingClientRect().width : 0; })()"
        assert pg.evaluate(q) <= 440, "붙은 360px 창 = 좁은 줄"
        pg.click("#hdtalk .tw-fold")
        pg.wait_for_selector("#hdtalk.tw-compact")
        assert pg.evaluate(q) > 440, "접힌 640px 창 = 넓은 줄"
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
            {"id": "e2b", "role": "tool", "text": "Bash " + "C:/very/long/path/" * 20 + "\ncommand: " + "x" * 600, "at": now - 58500},
            {"id": "e3", "role": "assistant", "text": "결제 화면을 읽었어요", "at": now - 58000}], "cursor": "c1", "source": "claude"}
    monkeypatch.setitem(router.ROUTES["GET"], "/api/agents/transcript", fake)
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-1", "name": "클로드", "kind": "claude"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/attach", {"agent": "ag-1"})[0] == 200
    pg, errors = open_page(ctx, srv)
    try:
        pg.wait_for_selector("#pTalk .tk-term[data-id='e3']", timeout=15000)
        assert pg.text_content("#pTalk .tk-term[data-role='user'] .tk-who") == "터미널에서"
        assert pg.locator("#pTalk .tk-term[data-role='tool'] details").count() == 0, "도구 줄은 접지 않는다(login#7 — 늘 전문)"
        assert pg.text_content("#pTalk .tk-term[data-role='tool'] .tk-tool-h") == "도구 · Read screens/pay.html"
        assert pg.is_visible("#pTalk .tk-term[data-role='tool'] pre") and pg.text_content("#pTalk .tk-term[data-role='tool'] pre") == "(120 lines)", "입력 전체가 처음부터 보인다"
        assert ("x" * 600) in pg.text_content("#pTalk .tk-term[data-id='e2b'] pre"), "긴 도구 입력도 끝까지"
        assert pg.evaluate("(() => { const l = document.querySelector('#pTalk .tk-list'); return l.scrollWidth <= l.clientWidth + 1; })()"), "긴 경로·글은 줄 안에서 꺾여 가로로 넘치지 않는다"
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
        assert pg.is_visible("#pTalk .tk-term[data-role='tool'] pre"), "다시 그려도 도구 줄 전문은 그대로"
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


def test_jump_to_latest_button_when_scrolled_up(served, ctx, monkeypatch):
    """R50 — 올려 읽는 중이면 목록 오른쪽 아래(입력창 위)에 둥근 ↓ 단추, 새 줄은 당기지 않고 점, 누르면 맨 아래로 가고 단추는 숨는다."""
    out, srv = served

    def fake(s, q, b):
        now = int(time.time() * 1000)
        return 200, {"entries": [{"id": "a%d" % i, "role": "assistant", "text": ("답 %d — " % i) + "긴 줄 " * 40, "at": now - 90000 + i}
                                 for i in range(14)], "cursor": "c1", "source": "claude"}
    monkeypatch.setitem(router.ROUTES["GET"], "/api/agents/transcript", fake)
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-1", "name": "클로드", "kind": "claude"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/attach", {"agent": "ag-1"})[0] == 200
    pg, errors = open_page(ctx, srv)
    pg.set_viewport_size({"width": 1440, "height": 1000})
    gap = "(() => { const l = document.querySelector('#pTalk .tk-list'); return l.scrollHeight - l.scrollTop - l.clientHeight; })()"
    try:
        pg.wait_for_selector("#pTalk .tk-term[data-id='a13']", timeout=15000)
        pg.wait_for_function(gap + " <= 24", timeout=5000)
        assert pg.is_hidden("#pTalk .tk-jump"), "맨 아래 = 단추 없음"
        pg.evaluate("document.querySelector('#pTalk .tk-list').scrollTop = 0")
        pg.wait_for_selector("#pTalk .tk-jump", state="visible", timeout=3000)
        b, lst, foot = (pg.locator(x).bounding_box() for x in ("#pTalk .tk-jump", "#pTalk .tk-list", "#hdchat"))
        assert abs(b["width"] - b["height"]) < 1 and b["width"] >= 28, ("둥근 단추", b)
        assert b["x"] + b["width"] <= lst["x"] + lst["width"] and b["x"] > lst["x"] + lst["width"] / 2, ("목록 오른쪽", b, lst)
        assert b["y"] + b["height"] <= foot["y"], ("입력창을 덮지 않음", b, foot)
        assert pg.evaluate("getComputedStyle(document.querySelector('#pTalk .tk-jump')).borderRadius") == "50%"
        assert pg.is_hidden("#pTalk .tk-dot"), "아직 새 줄 없음 = 점 없음"
        now = int(time.time() * 1000)
        srv.session.events.publish("agent.transcript", agent="ag-1", entries=[{"id": "a99", "role": "assistant", "text": "새 답 — 끝", "at": now}])
        pg.wait_for_selector("#pTalk .tk-term[data-id='a99']", state="attached", timeout=15000)
        assert pg.evaluate("document.querySelector('#pTalk .tk-list').scrollTop") == 0, "올려 읽는 중 = 새 줄이 와도 당기지 않는다"
        pg.wait_for_selector("#pTalk .tk-dot", state="visible", timeout=3000)
        shot(pg, "r50-jump-button-unseen.png")
        pg.click("#pTalk .tk-jump")
        pg.wait_for_function(gap + " <= 24", timeout=5000)
        pg.wait_for_selector("#pTalk .tk-jump", state="hidden", timeout=3000)
        assert pg.is_hidden("#pTalk .tk-dot") and pg.is_visible("#pTalk .tk-term[data-id='a99']"), "맨 아래 = 새 답이 보이고 단추·점은 꺼짐"
    finally:
        pg.close()
    assert not errors, errors


def test_without_helper_the_panel_is_absent(served, ctx):
    """file:// 로 연 캔버스(도우미 없음) — 대화 기록·진행이 없으니 대화 창은 접힌 창(입력창만, 펼치기·알약 없음)으로만, 저장 배치는 그대로."""
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
        assert pg.evaluate("!!document.querySelector('body > #hdtalk.tw-compact.tw-nolog #hdchat')"), "입력창은 판 아래 접힌 창"
        assert pg.is_hidden("#hdtalk .tw-expand") and pg.is_hidden("#hdtalk .tw-pill") and pg.is_hidden("#pTalk"), "기록이 없으니 펼치기 없음"
        pg.click("#wbtn")
        assert pg.locator("#wmenu .wm-row[data-w='talk']").count() == 0 and pg.is_enabled("#wmenu .wm-row[data-w='chat']")
        pg.click("#wmenu .wm-row[data-w='tools']")          # 다른 창 설정을 바꿔 저장해도
        assert json.loads(pg.evaluate("localStorage.getItem('hd-dock')"))["left"][0]["tabs"] == ["talk"], "저장 배치의 대화 자리는 그대로(도우미로 열면 왼쪽에)"
    finally:
        pg.close()
    assert not errors, errors
