"""보낼 곳 고르기(#214) — 도우미 GET /api/agents + 캔버스 칩 메뉴(Playwright).

가짜 paseo(파이썬 스크립트를 부르는 .cmd/셸): `ls` 는 한글 이름 JSON 을 UTF-8 바이트로 찍고, `send` 는 인자를 로그에 적는다 —
실제 Paseo 에이전트에는 아무것도 보내지 않는다(R53).
도우미: 한글이 깨지지 않음 · 보관된 것 뺌 · Paseo 없음 = 200 {agents:[], error} · current/repo · 5초 캐시.
캔버스: 이 저장소에 실행 중인 에이전트가 하나면 열 때 붙임(토스트) · 칩 ▾ 목록(이 저장소 먼저, 지금 것 체크, 마지막 '받는 곳 없음') ·
고르면 /api/attach → 칩 'AI 연결됨 · <이름>' · 보내기는 가짜 paseo 에 `send <id>`.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401
from test_canvas_annotations import PAY, DONE

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("helper")

FAKE_PY = r'''
import json, sys
here = sys.argv[1]
args = sys.argv[2:]
if args[:1] == ["ls"]:
    sys.stdout.buffer.write(open(here + "/agents.json", "rb").read())
elif args[:1] == ["send"]:
    with open(here + "/paseo.log", "a", encoding="utf-8") as f:
        f.write(" ".join(args) + "\n")
else:
    sys.exit(3)
'''


def fake_paseo(d, agents):
    """d 에 가짜 paseo 를 만들고 그 명령 경로를 돌려준다. agents = ls 가 찍을 목록."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "agents.json").write_bytes(json.dumps(agents, ensure_ascii=False).encode("utf-8"))
    (d / "fake.py").write_text(FAKE_PY, encoding="utf-8")
    if os.name == "nt":
        cmd = d / "paseo.cmd"
        cmd.write_text('@"%s" "%s" "%s" %%*\r\n' % (sys.executable, d / "fake.py", d), encoding="ascii")
    else:
        cmd = d / "paseo"
        cmd.write_text('#!/bin/sh\nexec "%s" "%s" "%s" "$@"\n' % (sys.executable, d / "fake.py", d), encoding="ascii"); cmd.chmod(0o755)
    return str(cmd)


def agents_for(repo):
    return [
        {"id": "ag-run", "shortId": "ag", "name": "결제 화면 고치는 에이전트", "provider": "claude/opus", "status": "running", "cwd": str(repo)},
        {"id": "ag-idle", "name": "한글 이름 쉬는 중", "provider": "codex", "status": "idle", "cwd": str(repo / "sub")},
        {"id": "ag-far", "name": "다른 저장소", "provider": "claude", "status": "running", "cwd": str(repo.parent / "elsewhere")},
        {"id": "ag-arch", "name": "보관됨", "status": "idle", "cwd": str(repo), "archived": True},
        {"id": "ag-closed", "name": "닫힘", "status": "closed", "cwd": str(repo)},
    ]


# ---------------------------------------------------------------- 도우미(브라우저 없음)
def test_list_agents_decodes_korean_and_drops_archived(tmp_path):
    repo = tmp_path / "repo"
    cmd = fake_paseo(tmp_path / "fake", agents_for(repo))
    r = helper.list_agents(cmd)
    assert "error" not in r, r
    names = {a["id"]: a["name"] for a in r["agents"]}
    assert names["ag-run"] == "결제 화면 고치는 에이전트" and names["ag-idle"] == "한글 이름 쉬는 중", "UTF-8 로 풀어 한글이 그대로"
    assert "ag-arch" not in names and "ag-closed" in names, "보관된 것만 뺀다(닫힌 것은 캔버스 Model 이 뺀다)"
    assert set(r["agents"][0]) == {"id", "name", "status", "cwd", "provider", "thinking"}, "R28: thinking = 생각 깊이(대화창 알약)"


def test_list_agents_missing_paseo_is_error_text(tmp_path):
    r = helper.list_agents(str(tmp_path / "없음" / "paseo.cmd"))
    assert r == {"agents": [], "error": "Paseo 를 찾을 수 없어요"}


def test_project_repo_prefers_app_json_then_git(tmp_path):
    (tmp_path / "r" / ".git").mkdir(parents=True)
    out = tmp_path / "r" / "runs" / "out"; out.mkdir(parents=True)
    assert Path(helper.project_repo(out)) == (tmp_path / "r").resolve()
    (out / "app.json").write_text(json.dumps({"kind": "app", "repo": str(tmp_path / "app-repo")}), encoding="utf-8")
    assert Path(helper.project_repo(out)) == tmp_path / "app-repo", "앱 프로젝트는 app.json 의 repo"


def test_auto_query_skips_paseo_without_repo(tmp_path):
    class S:
        agent, repo, agents_cache = None, None, None
    assert helper.agents_get(S, str(tmp_path / "없음.cmd"), auto=True) == {"agents": [], "current": None, "repo": None, "skipped": True},         "저장소를 모르면(임시 폴더 out 등) 자동 물음에 paseo 를 띄우지 않는다"


# ---------------------------------------------------------------- 캔버스(도우미로 열기)
@pytest.fixture(scope="module")
def served():
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-agents-"))
    repo = tmp / "repo"
    (repo / ".git").mkdir(parents=True)
    out = repo / "runs" / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "pay.html").write_text(PAY.replace("{gap}", "").replace("{label}", "지금 결제하기"), encoding="utf-8")
    (out / "screens" / "done.html").write_text(DONE, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "결제", "purpose": "결제한다", "policies": []},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "결제", "purpose": "끝", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    fake = tmp / "fake"
    cmd = fake_paseo(fake, agents_for(repo.resolve()))
    srv = helper.make_server(out, 0, paseo=cmd)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield out, srv, fake
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)


def _get(srv, path):
    base = srv.url.split("/index.html")[0]
    req = urllib.request.Request(base + path, headers={"X-HD-Token": srv.token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _open(ctx, srv, out, notes=None):
    (out / ".hd-canvas.json").write_text(json.dumps({"version": 1, "rev": 1, "updated": "2026-10-24T00:00:00Z", "state": {
        "notes": notes or [], "note-seq": {"pay": len(notes or [])}}}, ensure_ascii=False), encoding="utf-8")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    return pg, errors


def test_api_agents_route_has_current_repo_and_cache(served):
    out, srv, fake = served
    srv.agent = None; srv.agents_cache = None
    d = _get(srv, "/api/agents")
    assert d["current"] is None and Path(d["repo"]) == (out.parent.parent).resolve(), d
    assert [a["id"] for a in d["agents"]][:2] == ["ag-run", "ag-idle"] and "ag-arch" not in [a["id"] for a in d["agents"]]
    first = srv.agents_cache
    srv.agent = "ag-idle"
    d2 = _get(srv, "/api/agents")
    assert srv.agents_cache is first and d2["current"] == "ag-idle", "5초 안은 목록을 다시 쓰고 current 는 지금 값"
    srv.agents_cache = None
    assert _get(srv, "/api/agents?auto=1") == {"agents": [], "current": "ag-idle", "repo": d["repo"], "skipped": True}, "붙어 있으면 자동 물음은 paseo 를 띄우지 않음"
    assert srv.agents_cache is None
    srv.agent = None


def test_canvas_auto_attaches_then_chip_menu_switches_and_send_goes_to_choice(served, ctx):
    out, srv, fake = served
    srv.agent = None; srv.agents_cache = None
    (fake / "paseo.log").unlink(missing_ok=True)
    note = {"id": "m1", "no": 1, "screen": "pay", "targets": [], "path": "button.pay", "text": "지금 결제하기", "rect": None,
            "note": "버튼을 더 크게", "intent": "change", "sent": False, "replies": []}
    pg, errors = _open(ctx, srv, out, [note])
    try:
        pg.wait_for_function("document.getElementById('aichip').textContent.indexOf('결제 화면') >= 0", timeout=15000)
        assert srv.agent == "ag-run", "저장소 안 실행 중 하나 → 열 때 붙임"
        assert pg.evaluate("window.__hdAgent") == "ag-run"
        assert pg.text_content("#aichip") == "AI 연결됨 · 결제 화면 고치는 에이전트"
        assert "보내기 → 결제 화면 고치는 에이전트 (바꾸려면 칩을 누르세요)" in pg.text_content("#toast")

        pg.click("#aichip")
        pg.wait_for_selector("#amenu .ag-row[data-id='ag-idle']")
        rows = pg.eval_on_selector_all("#amenu .ag-row", "els => els.map(e => ({id: e.dataset.id, chk: e.getAttribute('aria-checked'), text: e.innerText}))")
        assert [r["id"] for r in rows] == ["ag-run", "ag-idle", "ag-far", ""], "저장소 안 먼저·실행 중 먼저, 닫힌·보관된 것 없음, 마지막 = 받는 곳 없음"
        assert rows[0]["chk"] == "true" and rows[1]["chk"] == "false"
        assert "sub" in rows[1]["text"] and "받는 곳 없음(대기열 파일만)" in rows[3]["text"]

        pg.click("#amenu .ag-row[data-id='ag-idle']")
        pg.wait_for_function("document.getElementById('aichip').textContent === 'AI 연결됨 · 한글 이름 쉬는 중'")
        assert srv.agent == "ag-idle" and pg.is_hidden("#amenu")

        pg.click("#aibtn")
        pg.wait_for_selector("#amenu .ag-row[data-id='']")
        pg.click("#amenu .ag-row[data-id='']")
        pg.wait_for_function("document.getElementById('aichip').textContent === '받는 곳 없음'")
        assert srv.agent is None and pg.evaluate("window.__hdAgent") is None

        pg.click("#aichip")
        pg.wait_for_selector("#amenu .ag-row[data-id='ag-run']")
        pg.click("#amenu .ag-row[data-id='ag-run']")
        pg.wait_for_function("document.getElementById('aichip').textContent.indexOf('결제 화면') >= 0")
        pg.click("#nsend")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.forward", timeout=20000)
        fw = pg.evaluate("window.__hdLastHelper.forward")
        assert fw["via"] == "paseo" and fw["agent"] == "ag-run", fw
        assert "send ag-run --prompt-file" in (fake / "paseo.log").read_text(encoding="utf-8"), "보내기는 고른 곳(가짜 paseo)으로"
    finally:
        pg.close()
    assert not errors, errors


def test_canvas_does_not_switch_existing_attachment(served, ctx):
    out, srv, fake = served
    srv.agent = "ag-far"; srv.agents_cache = None
    pg, errors = _open(ctx, srv, out)
    try:
        pg.wait_for_function("document.getElementById('aichip').textContent === 'AI 연결됨'")
        pg.wait_for_timeout(800)
        assert srv.agent == "ag-far" and pg.text_content("#aichip") == "AI 연결됨", "붙어 있는 것은 자동으로 바꾸지 않는다"
    finally:
        pg.close()
        srv.agent = None
    assert not errors, errors


def test_attach_failure_toasts_reason_and_keeps_chip(served, ctx):
    out, srv, fake = served
    srv.agent = "ag-far"; srv.agents_cache = None
    pg, errors = _open(ctx, srv, out)
    try:
        pg.click("#aichip")
        pg.wait_for_selector("#amenu .ag-row[data-id='ag-run']")
        pg.evaluate("document.querySelector(\"#amenu .ag-row[data-id='ag-run']\").dataset.id = 'bad id'")   # 띄어쓰기 = 도우미가 400
        pg.click("#amenu .ag-row[data-name]")
        pg.wait_for_function("(document.getElementById('toast')||{}).textContent && document.getElementById('toast').textContent.indexOf('보낼 곳을 바꾸지 못했어요') >= 0")
        assert srv.agent == "ag-far" and pg.text_content("#aichip") == "AI 연결됨", "칩·보낼 곳 그대로"
    finally:
        pg.close()
        srv.agent = None
    assert not errors, errors
