"""부품 쓰는 화면 지도(R58) — 브라우저. 같은 프로세스 도우미 · 임시 HD_HOME · dayfine 고정본 복사본.

Components 탭 → '부가 정보'(info) 머리 칩 '쓰는 화면 3' · 맨 위 목록 → 칩 누르기 → Screens 탭, 그 세 카드만 또렷(나머지 흐림) + 막대 '부가 정보 · 쓰는 화면 3' →
✕ 로 걷힘 → 선택(V)으로 info 부품을 고르면 속성 창 머리에도 '쓰는 화면 3' → 누르면 같은 강조 → Esc 로 걷힘.
눈으로 볼 때: HD_SHOTS=<폴더> 면 Components 칩·목록 · 판 강조를 찍는다."""
import os, pathlib, shutil, subprocess, sys, tempfile, threading

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")
INFO = {"login--done", "language", "keys"}            # dayfine 에서 class="info" 를 가진 화면
pytestmark = pytest.mark.area("dsedit")


@pytest.fixture()
def served(monkeypatch):
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-usage-"))
    monkeypatch.setenv("HD_HOME", str(tmp / "hd-home"))   # 진짜 ~/.hyper-design 을 읽지 않는다
    o = tmp / "out"
    shutil.copytree(DAYFINE, o, ignore=shutil.ignore_patterns(".hd-*"))
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    srv = helper.make_server(o, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield o, srv
    srv.shutdown(); srv.server_close()
    shutil.rmtree(tmp, ignore_errors=True)


def components(pg):
    return next(f for f in pg.frames if f.url.split("?")[0].endswith("/components.html"))


def shot(pg, name):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.screenshot(path=os.path.join(SHOTS, name))


HITS = "[...document.querySelectorAll('#rows .card.use-hit')].map(c => c.dataset.id).sort()"
DIM = "[...document.querySelectorAll('#rows .card:not(.use-hit):not(.hid)')].map(c => +getComputedStyle(c).opacity)"


def board_shows_usage(pg):
    pg.wait_for_function("document.body.dataset.tab === 'screens' && document.querySelectorAll('#rows .card.use-hit').length > 0")
    assert sorted(pg.evaluate(HITS)) == sorted(INFO), "그 부품을 쓰는 세 화면만 강조"
    try:                                              # 흐림은 전환(transition) 뒤에 다 내려온다
        pg.wait_for_function(f"(() => {{ const d = {DIM}; return d.length && Math.max(...d) < 0.5; }})()", timeout=3000)
    except Exception:
        pass
    dim = pg.evaluate(DIM)
    assert dim and max(dim) < 0.5, f"나머지 카드는 흐리게: {dim}"
    bar = pg.locator("#useBar")
    assert bar.is_visible() and "부가 정보 · 쓰는 화면 3" in bar.text_content()
    for id_ in INFO:                                  # 카메라가 그 카드들을 판 안에 담는다
        b, p = pg.locator(f'.card[data-id="{id_}"] .phone').bounding_box(), pg.locator("#screens").bounding_box()
        assert b and b["x"] >= p["x"] - 1 and b["x"] + b["width"] <= p["x"] + p["width"] + 1, id_


def board_cleared(pg):
    pg.wait_for_function("!document.querySelector('#rows .card.use-hit')")
    assert pg.locator("#useBar").is_hidden()
    try:
        pg.wait_for_function(f"(() => Math.min(...{DIM}) > 0.8)()", timeout=3000)
    except Exception:
        pass
    assert min(pg.evaluate(DIM)) > 0.8, "걷으면 흐림도 걷힌다"


def test_components_chip_shows_usages_on_board_and_clears(ctx, served):  # noqa: F811
    out, srv = served
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.keyboard.press("0"); pg.wait_for_timeout(300)
        pg.click('.tab[data-tab="components"]')
        pg.wait_for_function("() => { const f = document.querySelector('#components iframe.doc'); try { return !!f.contentDocument.querySelector('.use-chip'); } catch (e) { return false; } }")
        cd = components(pg)
        chip = cd.locator('.spec[data-key="info"] .use-chip')
        assert chip.text_content() == "쓰는 화면 3"
        assert cd.locator('.use-index .use-link[href="#spec-info"]').is_visible(), "맨 위 목록에 부품과 수"
        assert cd.locator('.spec[data-key="badge"] .use-chip').count() == 0, "배지 섹션은 칩 없음"
        shot(pg, "1-components-chips-index.png")

        chip.click()
        board_shows_usage(pg)
        shot(pg, "2-board-usages.png")
        pg.click("#useBar .ub-x")
        board_cleared(pg)

        # 속성 창 머리(R55)에도 같은 수 — 누르면 같은 강조, Esc 로 걷힘
        pg.click('.tab[data-tab="components"]')
        pg.keyboard.press("v")
        cd.click('.spec[data-key="info"] .spec-stage .info')
        pg.wait_for_selector("#dsInsp:not([hidden]) .di-use")
        assert pg.text_content("#dsInsp .di-use") == "쓰는 화면 3"
        shot(pg, "3-inspector-usage.png")
        pg.click("#dsInsp .di-use")
        board_shows_usage(pg)
        pg.keyboard.press("Escape")
        board_cleared(pg)
    finally:
        pg.close()
    assert not errors, errors
