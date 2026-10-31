"""V2 — 캔버스 화면 ↔ 앱 카드 맞음 검증(브라우저 + 같은 프로세스 도우미 · HD_HOME 임시 · 받는 곳 없음): 짝 = parts.json(home 이 끌어 쓰는 부품
screens/mock-home.html 을 그대로 싣는 카드 mock-home). 열면 표 '앱과 일치' → 앱 카드 글자 하나를 바꾸면 '다름 1' → hd verify home(자식 프로세스, 브라우저를
새로 띄우지 않음)이 종료 코드 1 과 그 항목. 표 누르기 = 목록 창(줄 누르기 = 두 카드 강조) · Esc = 떠 있는 층(float-stack)이 닫음.
규칙(비교·짝·글)은 test_canvas_unit_twin_diff.py · test_canvas_unit_twin.py, 도우미 쪽 = test_canvas_unit_verify_desk.py, CLI 종료 코드 = hd/tests/test_hd_verify.py."""
import json, os, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

HD_PY = SCRIPTS.parent / "hd" / "hd.py"
pytestmark = pytest.mark.area("helper", "tools")

PAGE = """<!doctype html><html><head><meta charset="utf-8"><script src="../palette.js"></script></head>
<body style="margin:0;font-family:sans-serif"><header><h1 style="margin:16px;color:#111">결제</h1></header>
<main style="padding:16px"><p>카드를 고르세요</p><button style="display:block;width:240px;height:48px;font-size:16px;border-radius:8px">{label}</button>
<a href="done.html">다음</a></main>{embed}</body></html>"""


def write(out, name, label, embed=""):
    (out / "screens" / name).write_text(PAGE.replace("{label}", label).replace("{embed}", embed), encoding="utf-8")


@pytest.fixture()
def served(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-twin-"))
    monkeypatch.setenv("HD_HOME", str(tmp / "home"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    write(out, "home.html", "지금 결제하기", '<iframe src="mock-home.html" style="display:none"></iframe>')   # 캔버스 화면이 앱 부품을 끌어 씀 = 짝 정보
    write(out, "mock-home.html", "지금 결제하기")
    (out / "screens.json").write_text(json.dumps({"groups": ["결제"], "screens": [
        {"id": "home", "file": "screens/home.html", "title": "홈", "group": "결제", "purpose": "디자인"},
        {"id": "mock-home", "file": "screens/mock-home.html", "title": "앱 홈", "group": "결제", "purpose": "앱 빌드 결과"}]},
        ensure_ascii=False), encoding="utf-8")
    (out / "parts.json").write_text(json.dumps({"version": 1, "parts": [
        {"file": "screens/mock-home.html", "repo": str(tmp / "app"), "watch": ["ui"], "build": ["node", "b.mjs", "{out}"],
         "stamp": "g:" + "a" * 16, "dirty": False, "built_at": "2026-10-31T10:00:00"}]}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    srv = helper.make_server(out, 0, paseo=str(tmp / "no-paseo" / "paseo.cmd"))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    marker = helper.write_marker(out, srv)               # hd verify 가 이 도우미를 찾게(이 테스트 프로세스 = 도우미)
    yield out, srv, tmp / "home"
    marker.unlink(missing_ok=True)
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)


def chip(pg, sid):
    return "#rows .card[data-id='%s'] .phone > .tchip" % sid


def chip_is(pg, sid, text, timeout=15000):
    pg.wait_for_function("([s, t]) => { const c = document.querySelector(s); return c && c.textContent === t; }", arg=[chip(pg, sid), text], timeout=timeout)


def hd_verify(home, out, *args):
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, str(HD_PY), "verify", *args], capture_output=True, text=True, encoding="utf-8", timeout=60,
                       env=dict(os.environ, HD_HOME=str(home), PYTHONIOENCODING="utf-8"))
    return r.returncode, r.stdout, r.stderr, time.monotonic() - t0


def test_badge_matches_then_one_changed_text_is_differ_1_and_hd_verify_exits_1(served, ctx):
    out, srv, home = served
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    try:
        chip_is(pg, "home", "앱과 일치")
        assert pg.locator(chip(pg, "mock-home")).count() == 0, "앱 카드 자신에는 표가 없다"

        write(out, "mock-home.html", "결제하기")          # 앱이 바뀜(부품 다시 빌드) — 도우미 지켜보기 → 카드 다시 실림 → 다시 잼
        chip_is(pg, "home", "다름 1")

        pg.click(chip(pg, "home"))
        pg.wait_for_selector("#twinwin:not([hidden]) li", timeout=5000)
        items = pg.eval_on_selector_all("#twinwin li", "ls => ls.map(l => l.textContent)")
        assert items == ["확실하지 않음 · 버튼 '지금 결제하기' ↔ '결제하기' (글자 다름)"], items
        pg.click("#twinwin li")
        app = pg.frame_locator("#rows .card[data-id='mock-home'] .phone iframe").first
        canvas = pg.frame_locator("#rows .card[data-id='home'] .phone iframe").first
        app.locator("div[data-hd-pick]").wait_for(state="attached", timeout=5000)
        canvas.locator("div[data-hd-pick]").wait_for(state="attached", timeout=5000)
        pg.keyboard.press("Escape")
        pg.wait_for_selector("#twinwin", state="hidden", timeout=5000)
        assert app.locator("div[data-hd-pick][style*='ea580c']").count() == 0, "닫으면 강조도 지운다"

        code, stdout, err, secs = hd_verify(home, out, "home", str(out))
        print("hd verify home: %.2f 초" % secs)
        assert code == 1, (code, stdout, err)
        *body, last = stdout.strip().splitlines()
        res = json.loads("\n".join(body))
        assert res["status"] == "differ" and res["app"] == "mock-home" and res["count"] == 1, res
        assert res["unsure"][0]["text"] == "지금 결제하기" and res["unsure"][0]["other"]["text"] == "결제하기"
        assert last.startswith("home ↔ mock-home · 다름 1"), last

        pg.wait_for_timeout(5500)                        # 막 다시 실은 카드는 5초 동안 다시 싣지 않는다(view-busy wrote — 있던 규칙)
        write(out, "mock-home.html", "지금 결제하기")
        chip_is(pg, "home", "앱과 일치")
        code, stdout, _, _ = hd_verify(home, out, "home", str(out))
        assert code == 0 and stdout.strip().splitlines()[-1].startswith("home ↔ mock-home · 앱과 일치"), stdout
        code, stdout, _, _ = hd_verify(home, out, "mock-home", str(out))
        assert code == 2 and "견줄 앱 화면 없음" in stdout, "짝 없는 화면 = 2"
    finally:
        pg.close()
    assert not errors, errors


def test_hd_verify_without_an_open_canvas_is_2_at_once(served):
    out, srv, home = served
    code, stdout, _, secs = hd_verify(home, out, "home", str(out))
    assert code == 2 and "열린 캔버스가 없어요" in stdout and secs < 8, (code, stdout, secs)
