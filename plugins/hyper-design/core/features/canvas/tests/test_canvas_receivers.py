"""받는 곳 고르기 · 에이전트 상태 · 진행 줄 · 새 터미널(task 47-5b) — 브라우저(Playwright) + 같은 프로세스 도우미.

에이전트는 테스트가 HTTP 로 hello/bye/progress/reply 만 보낸다(SDK 가 하는 일 그대로) — 실제 Paseo·Claude 에이전트에 아무것도 보내지 않는다.
HD_HOME 은 임시 폴더, Paseo 는 없는 경로(목록 = 'Paseo 를 찾을 수 없어요', 보내기 어댑터 꺼짐), HD_ALLOW_SPAWN 은 지운다(새 터미널 = 403 disabled — 아무것도 띄우지 않음).
행복한 길: 알약 → 메뉴(접속 중 · 자리 비움) → 고르기 → 보내기 → '보냄 · <이름> (실시간)' → 진행 글 → '답 옴'.
꺼진 새 터미널: 메뉴 '새 터미널…' → 확인 창(무엇 · 폴더) → [취소] 는 부르지 않음 · [열기] → 꺼짐 설명(HD_ALLOW_SPAWN=1).
규칙(메뉴 줄·칩 상태·진행 줄·답 풀이)은 test_canvas_unit_receivers.py(unit).
"""
import json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("chat")
SHOTS = Path(os.environ.get("HD_SHOTS_47_5B", Path(tempfile.gettempdir()) / "claude" / "t47-5b"))


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


@pytest.fixture()
def served(monkeypatch):
    monkeypatch.delenv("HD_ALLOW_SPAWN", raising=False)
    monkeypatch.delenv("HD_CLAUDE_WAKE", raising=False)
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-recv-"))
    monkeypatch.setenv("HD_HOME", str(tmp / "home"))   # 탭·프로젝트 목록은 임시 HD_HOME — 진짜 ~/.hyper-design 을 읽지 않는다
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
    srv = helper.make_server(out, 0, paseo=str(tmp / "no-paseo" / "paseo.cmd"))   # 없는 Paseo — 실제 에이전트 목록·보내기 없음
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


def open_page(ctx, srv):
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1280, "height": 800})
    errors, calls = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("request", lambda q: calls.append((q.method, q.url.split("://", 1)[1].split("/", 1)[1].split("?")[0])))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.wait_for_selector("#hdchat .ch-agent:not([hidden])")
    return pg, errors, calls


def rect(pg, sel):
    return pg.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom}; }", sel)


def test_pick_connected_agent_send_progress_reply(served, ctx):
    out, srv = served
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-here", "name": "클로드 작업자", "kind": "claude"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/hello", {"agent": {"id": "ag-away", "name": "코덱스 쉬는 중", "kind": "codex"}, "lease": 300})[0] == 200
    assert call(srv, "POST", "/api/bye", {"id": "ag-away"})[0] == 200
    pg, errors, calls = open_page(ctx, srv)
    try:
        pg.wait_for_function("(document.getElementById('livechip')||{}).dataset && document.getElementById('livechip').dataset.mode === 'live'", timeout=15000)
        pg.click("#hdchat .ch-agent")
        pg.wait_for_selector("#amenu .ag-conn[data-id='ag-away']")
        rows = pg.eval_on_selector_all("#amenu .ag-conn", "els => els.map(e => [e.dataset.id, e.dataset.state, e.innerText])")
        assert [r[:2] for r in rows] == [["ag-here", "here"], ["ag-away", "away"]], rows
        assert "접속 중 · Claude" in rows[0][2] and "자리 비움 · Codex" in rows[1][2]
        assert pg.is_visible("#amenu .ag-none") and pg.is_visible("#amenu .ag-spawn"), "받는 곳 없음 · 새 터미널 줄"
        assert "Paseo 를 찾을 수 없어요" in pg.text_content("#amenu"), "Paseo 가 없다는 것도 말한다(접속한 에이전트는 그대로)"
        m, c = rect(pg, "#amenu"), rect(pg, "#hdchat .ch-agent")
        assert m["b"] <= c["t"] + 1 and abs(m["l"] - c["l"]) <= 1, f"메뉴는 알약 위로, 왼쪽 끝 맞춤 {m} {c}"
        shot(pg, "picker-open.png")

        pg.click("#amenu .ag-conn[data-id='ag-here']")
        pg.wait_for_function("document.getElementById('aichip').textContent === 'AI 연결됨 · 클로드 작업자'")
        assert srv.session.queue.agent == "ag-here"
        pg.wait_for_function("document.getElementById('aichip').dataset.state === 'here'")
        assert pg.text_content("#aistate") == "접속 중"
        assert pg.get_attribute("#hdchat .ch-agent", "data-state") == "here" and "클로드 작업자" in pg.text_content("#hdchat .ch-agent")

        pg.click("#hdchat textarea")
        pg.keyboard.type("결제 버튼을 더 크게")
        pg.keyboard.press("Enter")
        TL = "[...document.querySelectorAll('#pTalk .tk-l')].some(l => l.innerText.includes(%s))"   # 진행은 대화 창 기록(R53 — 입력창 위 상태 줄은 없앴다)
        pg.wait_for_function(TL % "'보냄 · 클로드 작업자 (실시간)'", timeout=15000)
        assert not list((out / ".hd-queue").glob("*.sent")), "이벤트로 받았다 — 어댑터(paseo·claude)를 부르지 않음"
        pg.wait_for_function("document.getElementById('nmsg').textContent.indexOf('보냈어요') >= 0")
        assert "실시간" in pg.text_content("#nmsg") and "보내지 못해" not in pg.text_content("#nmsg"), "접속한 에이전트가 받은 것 — 대기열이라고 하지 않는다"
        assert pg.get_attribute(".card[data-id='pay'] .busy", "data-kind") == "working", "카드 덮개 = AI 수정 중"

        assert call(srv, "POST", "/api/progress", {"agent": "ag-here", "text": "결제 버튼 키우는 중", "screen": "pay"})[0] == 200
        pg.wait_for_function(TL % "'결제 버튼 키우는 중'", timeout=15000)
        pg.wait_for_function("document.getElementById('aistate').textContent === '결제 버튼 키우는 중'")
        pg.mouse.move(640, 300)
        shot(pg, "progress-mid-run.png")

        nid = pg.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.indexOf('hd-chat-last:') === 0))).ids[0]")   # 대화창이 보낸 메모
        for _ in range(50):                              # 캔버스가 보낸 메모를 상태 파일에 저장할 때까지(쓰기는 잠깐 뒤)
            st = call(srv, "GET", "/api/state")[1].get("state") or {}
            if any(n.get("id") == nid and n.get("sent") for n in st.get("notes") or []):
                break
            pg.wait_for_timeout(200)
        code, res = call(srv, "POST", "/api/reply", {"note": nid, "reply": {"kind": "반영됨", "what": "버튼을 키웠어요", "screens": ["pay"], "captured": False, "by": "ag-here"}})
        assert code == 200, res
        pg.wait_for_function(TL % "'버튼을 키웠어요'", timeout=15000)
        assert call(srv, "POST", "/api/bye", {"id": "ag-here"})[0] == 200
        pg.wait_for_function("document.getElementById('aistate').textContent === '자리 비움'", timeout=10000)
        assert pg.get_attribute("#hdchat .ch-agent", "data-state") == "away", "알약 점도 회색"
        assert not [x for x in calls if x[1].endswith("agents/spawn")]
    finally:
        pg.close()
    assert not errors, errors


def test_new_terminal_asks_first_and_explains_disabled(served, ctx):
    out, srv = served
    pg, errors, calls = open_page(ctx, srv)
    try:
        pg.click("#hdchat .ch-agent")
        pg.wait_for_selector("#amenu .ag-spawn")
        assert "접속한 에이전트가 없어요" in pg.text_content("#amenu")
        pg.click("#amenu .ag-spawn")
        pg.wait_for_selector("#hdspawn:not([hidden])")
        assert pg.is_hidden("#amenu")
        txt = pg.text_content("#hdspawn .sp")
        assert "새 터미널 에이전트 열기" in txt and "Paseo" in txt and "실제 AI 에이전트" in txt
        folder = pg.text_content("#hdspawn .sp-dir")
        assert folder and folder != "(알 수 없음)", "어느 폴더에서 뜨는지 보인다"
        pg.click("#hdspawn .sp-no")
        pg.wait_for_selector("#hdspawn", state="hidden")
        assert not [x for x in calls if x[1].endswith("agents/spawn")], "취소 = 부르지 않음"

        pg.click("#hdchat .ch-agent")
        pg.click("#amenu .ag-spawn")
        pg.wait_for_selector("#hdspawn:not([hidden])")
        pg.click("#hdspawn label:has(input[value='codex'])")
        assert "Codex" in pg.text_content("#hdspawn .sp-what")
        shot(pg, "spawn-confirm.png")
        pg.click("#hdspawn .sp-ok")
        pg.wait_for_function("document.getElementById('sp-h').textContent === '새 터미널 열기가 꺼져 있어요'")
        body = pg.text_content("#hdspawn .sp-body")
        assert "HD_ALLOW_SPAWN=1" in body and "hd attach" in body
        assert pg.is_hidden("#hdspawn .sp-ok") and pg.text_content("#hdspawn .sp-no") == "닫기"
        assert pg.text_content("#hdspawn .sp-err") == "", "오류 덤프가 아니라 설명"
        assert [x for x in calls if x[1].endswith("agents/spawn")] == [("POST", "api/agents/spawn")]
        shot(pg, "spawn-disabled.png")
        pg.keyboard.press("Escape")
        pg.wait_for_selector("#hdspawn", state="hidden")
    finally:
        pg.close()
    assert not errors, errors
