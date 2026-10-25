"""판 줄 맞추기(51-1, FINDINGS D) — 줄의 화면을 다 지우면 줄과 제목이 새로고침 없이 바로 없어지고, 되돌리면 제자리로 돌아온다. 레이어 패널도 같은 줄."""
import os, pathlib, shutil, subprocess, sys, tempfile, threading

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")                   # 눈으로 볼 때만: 스크린숏 폴더

ROWS = "() => [...document.querySelectorAll('#rows .flow .glabel')].map(g => g.textContent)"
LAYER_ROWS = "() => [...document.querySelectorAll('#pLayers .ly-r[data-kind=\"row\"] .ly-name')].map(n => n.textContent)"


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-rows-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.area("tools", "layers")
def test_emptied_row_and_heading_go_at_once_and_undo_brings_them_back(ctx, out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("window.__hdStay = 1")
        from test_canvas_edit import fit_view
        fit_view(pg)
        first = pg.evaluate(ROWS)
        assert first[0] == "로그인" and len(first) == 4, first
        assert pg.evaluate(LAYER_ROWS) == first
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-1-before.png"))
        pick = lambda sid: pg.evaluate("(id) => { const r = document.querySelector('.card[data-id=\"' + id + '\"] .cover').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }", sid)
        pg.mouse.click(*pick("login")); pg.wait_for_timeout(150)
        pg.keyboard.down("Shift"); pg.mouse.click(*pick("login--done")); pg.keyboard.up("Shift"); pg.wait_for_timeout(150)
        pg.keyboard.press("Delete")
        pg.wait_for_function("!document.querySelector('.card[data-id=\"login\"]') && !document.querySelector('.card[data-id=\"login--done\"]')", timeout=20000)
        pg.wait_for_timeout(100)
        assert pg.evaluate(ROWS) == first[1:], "화면을 다 지운 줄 = 제목째 바로 없어진다"
        assert pg.evaluate(LAYER_ROWS) == first[1:], "레이어 패널도 같은 줄"
        if SHOTS:
            fit_view(pg)
            pg.screenshot(path=os.path.join(SHOTS, "51-1-after.png"))
        pg.click("#undo")
        pg.wait_for_function("!!document.querySelector('.card[data-id=\"login\"]') && !!document.querySelector('.card[data-id=\"login--done\"]')", timeout=20000)
        pg.wait_for_timeout(100)
        assert pg.evaluate(ROWS) == first, "되돌리면 줄이 제자리로"
        assert pg.evaluate("() => [...document.querySelectorAll('#rows .flow')][0].querySelectorAll('.card').length") == 2
        assert pg.evaluate(LAYER_ROWS) == first
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
