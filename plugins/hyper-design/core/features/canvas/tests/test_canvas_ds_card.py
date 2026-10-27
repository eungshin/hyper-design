"""판 위 디자인 시스템 카드(S6, contract/ds-card.md) — 브라우저.

카드는 화면과 같은 tokens.css 를 읽는다: 테마 패널에서 바탕 테마를 고르거나 내 테마 색을 고치면 카드 색 칸과 화면이 함께 바뀐다.
누르면 Foundation 탭 · 레이어 패널 눈으로 숨김(새로고침 뒤에도) · tokens.css 가 없으면 카드 없음, 오류 없음.
"""
import os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, reload  # noqa: F401

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
PRIMARY = '[data-row="primary"] .strip i[data-i="3"]'      # 가운데 단계 = --c-brand 그대로
LIGHT = '[data-row="primary"] .strip i[data-i="0"]'        # 밝은 단계 = --c-brand 를 흰색과 섞은 것


def build(tmp, drop_tokens=False):
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    if drop_tokens:
        for f in o.glob("tokens*.css"):
            f.unlink()
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    return o


def open_page(ctx, o):
    p = ctx.new_page()
    p.errors, p.logs = [], []
    p.on("pageerror", lambda e: p.errors.append(str(e)))
    p.on("console", lambda m: p.logs.append(m.text) if m.type in ("error", "warning") else None)
    p.goto((o / "index.html").resolve().as_uri())
    p.wait_for_function("window.__hdReady !== undefined")
    p.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(p)
    return p


@pytest.fixture(scope="module")
def made():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-dscard-"))
    yield build(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def rgb(hx):
    h = hx.lstrip("#")
    return "rgb(%d, %d, %d)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def brand_of(css_file):
    return re.search(r"--c-brand:\s*(#[0-9A-Fa-f]{6})", css_file.read_text(encoding="utf-8")).group(1)


def swatch(pg, sel, want=None):
    """카드 iframe 안 색 칸의 계산된 배경색 — 바뀔 때까지 잠깐 기다린다(토큰 파일을 새로 받는 동안)."""
    loc = pg.frame_locator("#dscard iframe").locator(sel)
    v = None
    for _ in range(40):
        v = loc.evaluate("e => getComputedStyle(e).backgroundColor")
        if want is None or v == want:
            break
        pg.wait_for_timeout(50)
    return v


def screen_brand(pg, want):
    fr = [f for f in pg.frames if "/screens/" in f.url]
    assert fr, "불러온 화면 iframe 이 없다"
    v = None
    for _ in range(40):
        v = fr[0].evaluate("getComputedStyle(document.documentElement).getPropertyValue('--c-brand').trim().toUpperCase()")
        if v == want.upper():
            break
        pg.wait_for_timeout(50)
    return v


@pytest.mark.area("dscard", "theme")
def test_card_follows_theme_with_screens_and_opens_foundation(ctx, made):
    pg = open_page(ctx, made)
    try:
        pg.wait_for_selector("#dscard iframe")
        assert pg.evaluate("document.querySelector('#dscard').nextElementSibling === document.getElementById('rows')"), "화면 줄 위 자기 줄"
        assert pg.locator("#rows #dscard, .card#dscard").count() == 0, "화면 카드(.card)가 아니다 — 보내기·메모 핀·연결·교체 대상 밖"
        base = brand_of(made / "tokens.css")
        assert swatch(pg, PRIMARY, rgb(base)) == rgb(base), "카드 = 프로젝트 tokens.css 의 --c-brand"
        for k in ("headline", "body", "label"):
            assert pg.frame_locator("#dscard iframe").locator(f'[data-type="{k}"]').count() == 1
        assert pg.frame_locator("#dscard iframe").locator("[data-btn]").count() == 3
        assert pg.frame_locator("#dscard iframe").locator("[data-input]").count() == 1

        # 테마 패널: 다른 바탕 테마 → 카드도 그 파일의 색
        pg.click("#wbtn"); pg.click('#wmenu [data-w="theme"]'); pg.keyboard.press("Escape")
        pg.click('#dock .dk-tab[data-p="theme"]')
        second = pg.evaluate("document.querySelectorAll('#thList [data-th]')[1].dataset.th")
        pg.click(f'#thList [data-th="{second}"] .th-name')
        other = brand_of(made / f"tokens-{second}.css")
        assert swatch(pg, PRIMARY, rgb(other)) == rgb(other), "바탕 테마를 고르면 카드도 그 토큰 파일로"

        # 내 테마 주 색 고치기 → 카드 칸·섞은 단계·화면이 함께
        light_before = swatch(pg, LIGHT)
        pg.click("#thNew")
        pg.fill('#thEdit [data-role="brand"] .th-hex', "#D81B60"); pg.keyboard.press("Enter")
        assert swatch(pg, PRIMARY, rgb("#D81B60")) == rgb("#D81B60"), "테마 색을 고치면 카드 색 칸이 바로"
        assert swatch(pg, LIGHT) != light_before, "단계 띠도 같은 변수에서 섞여 함께 바뀐다"
        assert screen_brand(pg, "#D81B60") == "#D81B60", "화면도 같은 값"

        # 누르면 Foundation 탭
        pg.click("#dock .dk-tab[data-p='layers']")
        # 첫 카메라는 화면 줄에서 연다(R27 F03) — 카드는 그 위, 0(전체 보기)로 보인다
        pg.evaluate("document.activeElement && document.activeElement.blur()"); pg.keyboard.press("0"); pg.wait_for_timeout(300)
        pg.locator("#dscard .dsh b").click()
        assert pg.evaluate("document.body.dataset.tab") == "foundation"
        pg.click('.tab[data-tab="screens"]')
        assert not pg.errors, pg.errors
        assert not [l for l in pg.logs if "[hd]" in l], pg.logs
    finally:
        pg.close()


@pytest.mark.area("dscard", "layers")
def test_card_hides_from_layers_and_no_tokens_means_no_card(ctx, made):
    pg = open_page(ctx, made)
    try:
        pg.wait_for_selector("#dscard iframe")
        pg.click('#dock .dk-tab[data-p="layers"]')
        pg.click('#lyTree [data-ly="@dscard"] .ly-eye')
        assert pg.is_hidden("#dscard"), "레이어 눈 = 숨김"
        assert pg.is_visible("#thid"), "왼쪽 [숨긴 것]에 셈"
        reload(pg)
        assert pg.is_hidden("#dscard"), "새로고침 뒤에도 숨김"
        pg.click('#dock .dk-tab[data-p="layers"]')
        pg.click('#lyTree [data-ly="@dscard"] .ly-eye')
        assert pg.is_visible("#dscard")
        assert not pg.errors, pg.errors
    finally:
        pg.close()

    tmp = Path(tempfile.mkdtemp(prefix="hd-dscard-none-"))
    try:
        pg = open_page(ctx, build(tmp, drop_tokens=True))
        assert pg.locator("#dscard").count() == 0, "tokens.css 가 없으면 카드 없음"
        assert pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).tokens") is None
        pg.click('#dock .dk-tab[data-p="layers"]')
        assert pg.locator('#lyTree [data-ly="@dscard"]').count() == 0, "레이어에도 없음"
        assert not pg.errors, pg.errors
        assert not [l for l in pg.logs if "[hd]" in l], pg.logs
        pg.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
