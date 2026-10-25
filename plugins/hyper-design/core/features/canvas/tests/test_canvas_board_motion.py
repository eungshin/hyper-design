"""판 위 카드는 움직이지 않는다 · 라이브 카드 상한(task 35, contract/board-motion.md) — 브라우저.

판 카드 iframe 은 `hd-mode=board` 로 실린다(palette.js 가 reduced-motion 을 켬) · 크게 보기(#mframe)는 붙이지 않는다.
상한: 화면 밖 카드는 IDLE 뒤·K 넘을 때 내려가고(data-src 로 돌아감) 다시 보이면 다시 실린다. 테스트는 HD.liveCap.K·IDLE 을 줄여 기다리지 않는다.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
STATE = """() => [...document.querySelectorAll('#rows .card')].filter(c => c.querySelector('.phone iframe')).map(c => {
  const f = c.querySelector('.phone iframe'); return [c.dataset.id, f.getAttribute('src') || '', f.hasAttribute('data-src')]; })"""


@pytest.fixture(scope="module")
def pg(ctx):
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-board-motion-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    p = ctx.new_page()
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)))
    p.goto((o / "index.html").resolve().as_uri())
    p.wait_for_function("window.__hdReady !== undefined")
    p.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(p)
    yield p
    p.close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def _frame(p, sid, board):
    return next(f for f in p.frames if f.url.split("?")[0].endswith("/" + sid + ".html") and (("hd-mode=board" in f.url) == board))


@pytest.mark.area("motion", "modal")
def test_board_cards_load_in_board_mode_large_view_does_not(pg):
    pg.keyboard.press("0")
    pg.wait_for_function("document.querySelector('.card[data-id=\"job\"] .phone iframe').getAttribute('src')", timeout=5000)
    src = pg.get_attribute('.card[data-id="job"] .phone iframe', "src")
    assert "hd-mode=board" in src, src
    fr = _frame(pg, "job", True)
    fr.wait_for_load_state()
    assert fr.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") is True
    assert fr.evaluate("!!document.querySelector('style[data-hd-board]')")
    pg.evaluate("document.querySelector('.card[data-id=\"job\"] .pres').click()")
    pg.wait_for_function("document.getElementById('mframe').getAttribute('src')", timeout=3000)
    msrc = pg.get_attribute("#mframe", "src")
    assert "hd-mode" not in msrc, msrc
    mf = pg.frame_locator("#mframe").locator("body")
    assert mf.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches") is False, "크게 보기는 라이브(앱 그대로)"
    assert mf.evaluate("() => !document.querySelector('style[data-hd-board]')")
    pg.keyboard.press("Escape")


@pytest.mark.area("motion", "modal")
def test_offscreen_cards_unload_over_cap_and_reload_on_return(pg):
    pg.keyboard.press("0")
    pg.wait_for_function("() => [...document.querySelectorAll('#rows .card .phone iframe')].every(f => !f.hasAttribute('data-src'))", timeout=5000)
    n = len(pg.evaluate(STATE))
    assert n > 3
    pg.evaluate("HD.liveCap.K = 1; HD.liveCap.IDLE = 0")                     # 테스트 고리: 15초·10장 대신
    zoom_to(pg, "job", min_h=900)                                              # job 만 보이게 → 나머지는 화면 밖
    pg.wait_for_function("() => [...document.querySelectorAll('#rows .card .phone iframe')].filter(f => f.hasAttribute('data-src')).length >= 3", timeout=8000)
    st = {i: (s, d) for i, s, d in pg.evaluate(STATE)}
    assert not st["job"][1] and "hd-mode=board" in st["job"][0], "보이는 카드는 내리지 않는다"
    gone = [i for i, (s, d) in st.items() if d]
    assert all(st[i][0] == "about:blank" for i in gone), st
    pg.evaluate("HD.liveCap.K = 10; HD.liveCap.IDLE = 15000")
    pg.keyboard.press("0")                                                     # 다시 보이면 다시 싣는다
    pg.wait_for_function("() => [...document.querySelectorAll('#rows .card .phone iframe')].every(f => !f.hasAttribute('data-src') && /hd-mode=board/.test(f.src))", timeout=8000)


@pytest.mark.area("motion", "tools")
def test_cards_below_readable_width_unload_selected_stays_and_reload_on_zoom_in(pg):
    """LOD(figma-lite 1): 화면 위 너비가 HD.liveCap.MINW(120px) 아래인 카드는 iframe 을 내린다(틀·제목만) — 고른 카드는 그대로, 다시 크게 보면 다시 싣는다."""
    pg.keyboard.press("0")
    pg.wait_for_function("() => [...document.querySelectorAll('#rows .card .phone iframe')].every(f => !f.hasAttribute('data-src'))", timeout=8000)
    pg.click('.card[data-id="job"] .cover')                                    # 한 번 = 고르기
    pg.wait_for_function("() => document.querySelector('.card[data-id=\"job\"]').classList.contains('picked')", timeout=2000)
    pr = pg.locator("#screens").bounding_box()
    pg.mouse.move(pr["x"] + 300, pr["y"] + 300)
    for _ in range(30):
        if pg.locator('.card[data-id="job"] .phone').bounding_box()["width"] < 100:
            break
        pg.keyboard.down("Control"); pg.mouse.wheel(0, 120); pg.keyboard.up("Control")
        pg.wait_for_timeout(30)
    assert pg.locator('.card[data-id="job"] .phone').bounding_box()["width"] < 120
    pg.wait_for_function("() => [...document.querySelectorAll('#rows .card .phone iframe')].filter(f => f.hasAttribute('data-src')).length >= 3", timeout=8000)
    st = {i: (s, d) for i, s, d in pg.evaluate(STATE)}
    assert not st["job"][1] and "hd-mode=board" in st["job"][0], "고른 카드는 작아도 그대로 라이브"
    assert all(s == "about:blank" for i, (s, d) in st.items() if d), st
    assert pg.locator(".card .ftitle").first.is_visible(), "작은 카드도 제목은 그대로"
    pg.keyboard.press("Escape")
    pg.mouse.click(pr["x"] + 20, pr["y"] + pr["height"] - 20)                  # 빈 판 = 고르기 풀기
    pg.keyboard.press("0")                                                     # 다시 읽히는 크기 → 다시 싣는다
    pg.wait_for_function("() => [...document.querySelectorAll('#rows .card .phone iframe')].every(f => !f.hasAttribute('data-src') && /hd-mode=board/.test(f.src))", timeout=8000)
