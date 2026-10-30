"""Foundation 토큰 고치기(R55) — 브라우저. 같은 프로세스 도우미 · 임시 HD_HOME · dayfine 고정본 복사본.

Foundation 탭 → 손(H)으로 견본 누르기 = 아무 창도 없음 → 선택(V) → 주 색 견본 → #E11D48 → 판 카드의 주 단추가 그 색 →
Ctrl+Z 로 원래 색 · Ctrl+Shift+Z 로 다시 → 새로고침해도 저장한 색. 문서 탭 도구 막대는 손·선택만.
눈으로 볼 때: HD_SHOTS=<폴더> 면 고른 견본+속성 창 · 바꾼 뒤 카드 · 되돌린 뒤 카드를 찍는다."""
import os, pathlib, re, shutil, subprocess, sys, tempfile, threading

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")
NEW = "#E11D48"
pytestmark = pytest.mark.area("dsedit")


@pytest.fixture()
def served(monkeypatch):
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-dsedit-"))
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


def brand_in_file(out):
    return re.search(r"--c-brand:\s*([^;]+);", (out / "tokens.css").read_text(encoding="utf-8")).group(1).strip()


def foundation(pg):
    return next(f for f in pg.frames if f.url.split("?")[0].endswith("/foundation.html"))


def card_button(pg, want=None, timeout=8000):
    """job 카드 안 주 단추(.btn.primary) 바탕색 — want 가 오면 그 색이 될 때까지 기다린다."""
    end = timeout / 100
    v = None
    for _ in range(int(end)):
        fr = [f for f in pg.frames if "/screens/job.html" in f.url]
        if fr:
            try:
                v = fr[0].evaluate("(() => { const b = document.querySelector('.btn.primary'); return b ? getComputedStyle(b).backgroundColor : null; })()")
            except Exception:
                v = None
            if v and (want is None or v == want):
                return v
        pg.wait_for_timeout(100)
    return v


def shot(pg, name, card=False):
    if SHOTS:
        os.makedirs(SHOTS, exist_ok=True)
        pg.screenshot(path=os.path.join(SHOTS, name))
        if card:                                     # 판 배율이 작아 카드 하나를 크게 한 장 더(Ctrl+휠로 그 카드에 다가가 찍고 전체 보기로 돌아옴)
            b = pg.locator('.card[data-id="job"] .phone').bounding_box()
            pg.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
            pg.keyboard.down("Control")
            for _ in range(3):
                pg.mouse.wheel(0, -200); pg.wait_for_timeout(60)
            pg.keyboard.up("Control"); pg.wait_for_timeout(300)
            pg.locator('.card[data-id="job"] .phone').screenshot(path=os.path.join(SHOTS, name.replace(".png", "-job-card.png")))
            pg.keyboard.press("0"); pg.wait_for_timeout(200)


def test_pick_brand_swatch_change_colour_undo_and_reload(ctx, served):  # noqa: F811
    out, srv = served
    old = brand_in_file(out)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.keyboard.press("0"); pg.wait_for_timeout(300)
        before = card_button(pg)
        assert before == "rgb(27, 27, 27)", before
        assert pg.locator('#tools [data-tool="trigger"]').is_visible(), "판에서는 도구가 다 보인다"

        pg.click('.tab[data-tab="foundation"]')
        pg.wait_for_function("() => { const f = document.querySelector('#foundation iframe.doc'); try { return !!f.contentDocument.querySelector('.sw[data-var=\"--c-brand\"]'); } catch (e) { return false; } }")
        fd = foundation(pg)
        assert pg.locator("#foundation #tools").is_visible(), "Foundation 탭에도 도구 막대"
        shown = pg.evaluate("[...document.querySelectorAll('#tools .tb')].filter(b => b.offsetWidth).map(b => b.dataset.tool)")
        assert shown == ["hand", "move"], shown

        # 손 = 그냥 보기: 견본을 눌러도 창이 없다
        fd.click('.sw[data-var="--c-brand"] .chip'); pg.wait_for_timeout(300)
        assert pg.locator("#dsInsp").is_hidden(), "손(H) 누르기는 아무것도 열지 않는다"

        pg.keyboard.press("v")
        assert pg.get_attribute('#tools [data-tool="move"]', "aria-pressed") == "true"
        fd.click('.sw[data-var="--c-brand"] .chip')
        pg.wait_for_selector("#dsInsp:not([hidden])")
        assert "--c-brand" in pg.text_content("#dsInsp .di-title")
        assert pg.input_value("#dsInsp .di-val").upper() == old.upper()
        box, sw = pg.locator("#dsInsp").bounding_box(), pg.locator("#foundation iframe.doc").bounding_box()
        assert box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= 1440 and box["y"] + box["height"] <= 1000, "창은 화면 안"
        tb, fr = pg.locator("#tools").bounding_box(), pg.locator("#foundation iframe.doc").bounding_box()
        assert tb["x"] + tb["width"] <= fr["x"], "도구 막대가 견본을 가리지 않는다"
        assert fd.evaluate("[...document.querySelectorAll('[data-hd-pick]')].some(d => d.style.display === 'block' && d.style.position === 'absolute')"), "고른 견본에 테두리"
        shot(pg, "1-picked-swatch-inspector.png")

        # 틀린 값 = 그 칸이 원래 값으로, 쓰지 않음
        pg.fill("#dsInsp .di-val", "#E11D48; color:red"); pg.keyboard.press("Enter"); pg.wait_for_timeout(200)
        assert pg.input_value("#dsInsp .di-val").upper() == old.upper() and pg.text_content("#dsInsp .di-msg")
        assert brand_in_file(out) == old

        pg.fill("#dsInsp .di-val", NEW.lower()); pg.keyboard.press("Enter")
        pg.wait_for_function("() => !document.getElementById('toast').hidden")
        assert brand_in_file(out) == NEW, "tokens.css 에 썼다"
        fd.wait_for_function("() => document.querySelector('.sw[data-var=\"--c-brand\"] .val').textContent.trim().toUpperCase() === '#E11D48'")
        pg.keyboard.press("Escape")
        assert pg.locator("#dsInsp").is_hidden()

        pg.click('.tab[data-tab="screens"]')
        assert card_button(pg, "rgb(225, 29, 72)") == "rgb(225, 29, 72)", "판 카드의 주 단추가 새 색"
        assert pg.locator('#tools [data-tool="trigger"]').is_visible(), "판으로 돌아오면 도구가 다 보인다"
        shot(pg, "2-card-after-change.png", card=True)

        pg.keyboard.press("Control+z")
        assert card_button(pg, before) == before, "Ctrl+Z = 원래 색"
        assert brand_in_file(out) == old
        shot(pg, "3-card-after-undo.png", card=True)
        pg.keyboard.press("Control+Shift+z")
        assert card_button(pg, "rgb(225, 29, 72)") == "rgb(225, 29, 72)", "다시 하기"
        assert brand_in_file(out) == NEW

        pg.reload(); pg.wait_for_function("window.__hdReady !== undefined")
        pg.keyboard.press("0"); pg.wait_for_timeout(300)
        assert card_button(pg, "rgb(225, 29, 72)") == "rgb(225, 29, 72)", "새로고침해도 저장한 색"
    finally:
        pg.close()
    assert not errors, errors
