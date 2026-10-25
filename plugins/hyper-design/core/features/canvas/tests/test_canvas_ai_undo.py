"""48c AI 되돌리기 — 에이전트가 화면을 claim 한 동안 그 파일을 고치면 도우미가 쓰기 전 모습을 .hd-history 에 남기고 'AI 반영 · <화면>' 한 줄을 낸다.
캔버스 기록 패널의 그 줄 되돌리기 = 옛 파일이 돌아오고 카드가 다시 실린다(직접 쓰기처럼 그 뒤 바뀌면 409). 도우미는 이 프로세스 안(make_server), 작업 트리 빌드."""
import json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401

CANVAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANVAS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("helper")

OLD = "<!doctype html><html><head><meta charset='utf-8'></head><body><main><h1>예전 제목</h1><p>본문</p></main></body></html>"
NEW = OLD.replace("예전 제목", "AI 가 고친 제목")


def make_out(root):
    out = Path(root) / "proj" / "out"
    (out / "screens").mkdir(parents=True)
    (out / "screens" / "home.html").write_text(OLD, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["g"], "screens": [
        {"id": "home", "file": "screens/home.html", "title": "홈", "group": "g", "purpose": "", "policies": []}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(CANVAS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    return out


@pytest.fixture
def served(tmp_path, monkeypatch):
    monkeypatch.setenv("HD_HOME", str(tmp_path / "hd-home"))
    out = make_out(tmp_path)
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    srv.base = srv.url.split("/index.html")[0]
    yield out, srv
    srv.shutdown(); srv.server_close()


def call(srv, path, body=None, method=None):
    r = urllib.request.Request(srv.base + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                               method=method or ("GET" if body is None else "POST"), headers={"X-HD-Token": srv.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=60) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def wait_write(srv, since=0, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        w = call(srv, "/api/ai-writes?since=%d" % since)[1]["writes"]
        if w:
            return w
        time.sleep(0.2)
    return []


def ai_edit(out, srv, text=NEW):
    assert call(srv, "/api/claim", {"screen": "home", "by": "agent"})[0] == 200
    time.sleep(1.2)                                   # 지켜보기 기준(1초) 뒤에 바뀌게
    (out / "screens" / "home.html").write_text(text, encoding="utf-8")


@pytest.mark.slow
def test_claim_change_release_gives_one_restorable_row(served):
    out, srv = served
    f = out / "screens" / "home.html"
    assert call(srv, "/api/ai-writes")[1] == {"seq": 0, "writes": []}
    ai_edit(out, srv)
    rows = wait_write(srv)
    assert [(r["screen"], r["label"]) for r in rows] == [("home", "AI 반영 · 홈")], "바뀐 것을 보면 한 줄"
    time.sleep(1.2)
    f.write_text(NEW.replace("본문", "본문 둘"), encoding="utf-8")   # 덮개 안에서 또 고침 = 같은 줄, 되살리기 기준만 새로
    assert call(srv, "/api/release", {"screen": "home"})[1]["released"] is True
    rows = call(srv, "/api/ai-writes?since=0")[1]["writes"]
    assert len(rows) == 1, "덮개 하나 = 줄 하나"
    stamp = rows[0]["stamp"]
    assert (out / ".hd-history" / stamp / "screens" / "home.html").read_text(encoding="utf-8") == OLD, "직접 쓰기와 같은 모양으로 쓰기 전 모습"
    code, res = call(srv, "/api/restore", {"stamp": stamp, "keep": True, "notify": True})
    assert code == 200 and f.read_text(encoding="utf-8") == OLD and res["redo"], res
    assert call(srv, "/api/restore", {"stamp": stamp, "keep": True})[0] == 409, "되살린 뒤 같은 줄을 또 = 그 뒤 바뀜(409)"
    code, again = call(srv, "/api/restore", {"stamp": res["redo"], "keep": True, "notify": True})
    assert code == 200 and "본문 둘" in f.read_text(encoding="utf-8"), "다시 하기 = AI 버전으로"


@pytest.mark.slow
def test_claim_without_change_leaves_nothing(served):
    out, srv = served
    assert call(srv, "/api/claim", {"screen": "home"})[0] == 200
    hist = [d.name for d in (out / ".hd-history").iterdir()]
    assert len(hist) == 1, "claim 때 쓰기 전 모습 하나"
    assert call(srv, "/api/release", {"screen": "home"})[0] == 200
    assert call(srv, "/api/ai-writes?since=0")[1]["writes"] == [] and not (out / ".hd-history" / hist[0]).exists(), "안 바뀌었으면 줄도 기록도 없다"


def test_history_row_undo_puts_old_file_back_and_card_swaps(served, ctx):
    out, srv = served
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    h1 = "() => { const f = document.querySelector('.card[data-id=\"home\"] .phone iframe'); try { return f.contentDocument.querySelector('h1').textContent; } catch (e) { return null; } }"
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_function("(" + h1 + ")() === '예전 제목'", timeout=15000)
        ai_edit(out, srv)
        assert wait_write(srv), "도우미가 AI 반영 줄을 낸다"
        call(srv, "/api/release", {"screen": "home"})
        pg.wait_for_function("(" + h1 + ")() === 'AI 가 고친 제목'", timeout=15000)
        pg.wait_for_function("[...document.querySelectorAll('#hlist li .hl')].some(e => e.textContent === 'AI 반영 · 홈')", timeout=10000)
        pg.click("#undo")
        pg.wait_for_function("(" + h1 + ")() === '예전 제목'", timeout=15000)
        assert (out / "screens" / "home.html").read_text(encoding="utf-8") == OLD, "옛 파일이 돌아온다"
    finally:
        pg.close()
    assert not errors, errors
