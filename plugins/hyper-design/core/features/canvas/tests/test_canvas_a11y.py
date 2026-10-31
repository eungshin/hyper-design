"""접근성 검사(R59) — 크게 보기 '접근성' 단추 → 결과 창(문제 3개·한국어 제목) · 번호 핀이 문제 요소 위(폭 맞추기·200%) · 'AI로 고치기' = 요소 칩 + 요청 글(보내지 않음) ·
Esc 로 걷힘 · 문제 없는 화면 = 토스트 · 카드 우클릭 '접근성 검사' · axe.min.js 없음 = 토스트 (Playwright, file://).

화면 a11y: 회색(#9CA3AF) 작은 글 · 아이콘만 있는 <button> · alt 없는 <img>. 화면 ok: 문제 없음.
규칙(차례·글·경로·요약)은 test_canvas_unit_a11y.py — 여기는 사용자에게 보이는 것만 본다.
HD_A11Y_SHOTS=<폴더> 이면 그 폴더에 스크린샷(폭 맞추기 · 200% · AI로 고치기 뒤 · 문제 없음 토스트)."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx  # noqa: F401

pytestmark = pytest.mark.area("modal")
SHOTS = os.environ.get("HD_A11Y_SHOTS")
HEAD = '<!doctype html><html><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="../tokens.css"><script src="../palette.js"></script></head>'
BAD = (HEAD + '<body style="margin:0;font-family:sans-serif;background:#fff"><main style="padding:24px">'
       '<h1 style="margin:0 0 8px;font-size:24px;color:#111">결제</h1>'
       '<p class="hint" style="margin:0 0 16px;font-size:13px;color:#9CA3AF">이 금액은 부가세 포함이에요</p>'
       '<button class="close" style="display:block;width:44px;height:44px;border:1px solid #333;background:#fff">'
       '<svg width="20" height="20" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" stroke="#111" stroke-width="2"/></svg></button>'
       '<img class="hero" src="hero.png" width="200" height="120" style="display:block;margin-top:420px;background:#ddd">'
       '</main></body></html>')
OK = HEAD + '<body style="margin:0;font-family:sans-serif;background:#fff"><h1 style="margin:16px;color:#111">완료</h1><p style="margin:16px;color:#222">결제가 끝났어요</p></body></html>'
HASH = "(s => { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0; return (h >>> 0).toString(36); })(window.__hdKeyPath || location.pathname)"
ASK = "이 글자 대비를 4.5:1 이상으로 — 지금 #9CA3AF on #FFFFFF"


@pytest.fixture(scope="module")
def apage(ctx):
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-a11y-"))
    out = tmp / "out"
    (out / "screens").mkdir(parents=True)
    (out / "tokens.css").write_text(":root{--c-brand:#2563eb}", encoding="utf-8")
    (out / "screens" / "pay.html").write_text(BAD, encoding="utf-8")
    (out / "screens" / "done.html").write_text(OK, encoding="utf-8")
    (out / "screens.json").write_text(json.dumps({"groups": ["흐름"], "screens": [
        {"id": "pay", "file": "screens/pay.html", "title": "결제", "group": "흐름", "purpose": "문제 셋"},
        {"id": "done", "file": "screens/done.html", "title": "완료", "group": "흐름", "purpose": "문제 없음"}]}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    assert (out / "axe.min.js").is_file(), "빌드가 out/axe.min.js 를 싣는다"
    pg = ctx.new_page()
    errors, warns = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: warns.append(m.text) if m.type in ("warning", "error") else None)
    pg.goto((out / "index.html").resolve().as_uri())
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.out, pg.warns = out, warns
    yield pg
    pg.close()
    shutil.rmtree(tmp, ignore_errors=True)
    assert not errors, errors


def fresh(pg):
    pg.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    pg.reload()
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.keyboard.press("0")
    pg.wait_for_timeout(300)


def open_modal(pg, cid):
    b = pg.locator(f'.card[data-id="{cid}"] .cover').bounding_box()
    pg.mouse.dblclick(b["x"] + b["width"] / 2, b["y"] + min(b["height"] / 2, 6))
    pg.wait_for_selector("#modal:not([hidden])")
    pg.frame_locator("#mframe").locator("body").wait_for()
    pg.wait_for_timeout(400)


def run_check(pg):
    pg.click("#ma11y")
    pg.wait_for_selector("#a11yPanel:not([hidden])", timeout=20000)
    pg.wait_for_timeout(150)


def shot(pg, name):
    if SHOTS:
        Path(SHOTS).mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(SHOTS) / name))


def screen_box(pg, sel):
    """화면 안 요소의 지금 화면(캔버스) 자리 = 크게 보기 iframe 상자 + 요소 자리 × 배율."""
    fr = pg.frame_locator("#mframe").locator(sel).first
    r = fr.evaluate("e => { const b = e.getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }")
    f = pg.evaluate("() => { const f = document.querySelector('#mframe'), b = f.getBoundingClientRect(), m = /scale\\(([\\d.]+)\\)/.exec(f.style.transform); return {x: b.left, y: b.top, s: m ? +m[1] : 1}; }")
    s = f["s"]
    return {"x": f["x"] + r["x"] * s, "y": f["y"] + r["y"] * s, "w": r["w"] * s, "h": r["h"] * s}


def pins_on_elements(pg):
    """번호 핀(과 그 테두리)이 문제 요소 위에 있다 — 줄 차례대로 핀 k 의 테두리 = 그 요소 자리(±2px)."""
    rules = pg.eval_on_selector_all("#a11yPanel li", "els => els.map(e => e.dataset.rule)")
    sel = {"color-contrast": "p.hint", "button-name": "button.close", "image-alt": "img.hero"}
    for k, rule in enumerate(rules):
        want = screen_box(pg, sel[rule])
        box = pg.locator(f'.a11y-box[data-k="{k}"]').bounding_box()
        pin = pg.locator(f'.a11y-pin[data-k="{k}"]').bounding_box()
        assert box and pin, f"{rule}: 핀·테두리가 없다"
        for a in ("x", "y", "width", "height"):
            b = {"width": "w", "height": "h"}.get(a, a)
            assert abs(box[a] - want[b]) <= 2, f"{rule}: 테두리 {a} {box[a]} ≠ 요소 {want[b]}"
        cx, cy = pin["x"] + pin["width"] / 2, pin["y"] + pin["height"] / 2
        assert abs(cx - want["x"]) <= pin["width"] and abs(cy - want["y"]) <= pin["height"], f"{rule}: 핀이 요소 왼쪽 위 모서리에 있지 않다"
    return rules


def chip_pct(pg):
    return int(re.match(r"(\d+)%", pg.locator("#zoom").inner_text()).group(1))


def test_check_lists_problems_pins_follow_zoom_fix_prefills_chat_and_esc_clears(apage):
    pg = apage
    fresh(pg)
    open_modal(pg, "pay")
    assert pg.locator("#modal .mbar #ma11y").is_visible(), "크게 보기 머리 줄에 '접근성' 단추"
    assert pg.evaluate("() => { const b = document.querySelector('#ma11y'); return b.nextElementSibling && b.nextElementSibling.id; }") == "mclose", "닫기 왼쪽"
    run_check(pg)
    rows = pg.locator("#a11yPanel li")
    assert rows.count() == 3
    texts = rows.all_inner_texts()
    assert any('이름 없는 단추 — 화면 읽기 도구가 "단추"라고만 읽어요' in t for t in texts), texts
    assert any("그림에 설명(alt)이 없어요" in t for t in texts), texts
    assert any(re.search(r"글자와 배경 대비가 낮아요 — 지금 2\.\d:1, 4\.5:1 이상 필요", t) for t in texts), texts
    assert all("AI로 고치기" in t for t in texts)
    assert pg.locator("#a11yPanel .a11y-sum").inner_text().startswith("문제 3")
    # 창은 크게 보기 옆, 화면 안
    pw, mw = pg.locator("#a11yPanel").bounding_box(), pg.locator("#mwin").bounding_box()
    assert pw["x"] >= mw["x"] + mw["width"] or pw["x"] + pw["width"] <= mw["x"], "결과 창이 크게 보기 화면을 덮지 않는다(옆)"
    assert pw["y"] >= 0 and pw["y"] + pw["height"] <= 1000
    rules = pins_on_elements(pg)
    assert pg.locator(".a11y-pin").count() == 3
    shot(pg, "1-panel-fit.png")

    # 200% — 핀이 그대로 요소 위(R57 자리 맞춤)
    pg.mouse.move(5, 500)
    for _ in range(20):
        if chip_pct(pg) >= 200:
            break
        pg.keyboard.press("Control+Equal")
        pg.wait_for_timeout(120)
    assert chip_pct(pg) == 200
    pg.wait_for_timeout(200)
    pins_on_elements(pg)
    # 줄에 올리면 그 요소 테두리 강조 + 굴림 칸에 보이게(그림은 아래쪽 — 200% 에서는 처음에 안 보임)
    k = rules.index("image-alt")
    pg.hover(f'#a11yPanel li[data-k="{k}"] .a11y-t')
    pg.wait_for_timeout(200)
    assert pg.locator(f'.a11y-box.hi[data-k="{k}"]').count() == 1
    img, view = screen_box(pg, "img.hero"), pg.locator("#mview").bounding_box()
    assert img["y"] >= view["y"] - 1 and img["y"] + min(img["h"], 40) <= view["y"] + view["height"] + 1, "올린 줄의 요소가 크게 보기 안에 보인다"
    shot(pg, "2-panel-200.png")

    # AI로 고치기 — 대비 줄: 요소 칩 + 요청 글, 보내지 않음
    k = rules.index("color-contrast")
    pg.click(f'#a11yPanel li[data-k="{k}"] .a11y-fix')
    pg.wait_for_timeout(300)
    assert pg.locator("#hdchat textarea").input_value() == ASK
    chips = pg.locator("#hdchat .ch-chip").all_inner_texts()
    assert any("이 금액은 부가세" in c for c in chips), chips
    sent = pg.evaluate("h => { const v = localStorage.getItem('hd-notes:' + h); return v ? JSON.parse(v).length : 0; }", pg.evaluate(HASH))
    assert sent == 0, "보내지 않았다(메모가 생기지 않음)"
    assert not pg.locator("#a11yPanel").is_hidden(), "고치기를 눌러도 결과 창은 남는다"
    shot(pg, "3-after-ai-fix.png")

    # Esc — 입력칸에서 한 번(나가기), 다시 한 번 = 결과 창·핀 걷힘
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)
    assert pg.locator("#a11yPanel").is_hidden() and pg.locator(".a11y-pin").count() == 0
    # 다시 검사 → 닫기(크게 보기)도 걷는다
    if pg.locator("#modal").is_hidden():
        open_modal(pg, "pay")
    run_check(pg)
    pg.click("#mclose")
    pg.wait_for_timeout(200)
    assert pg.locator("#a11yPanel").is_hidden() and pg.locator(".a11y-pin").count() == 0


def test_no_problem_screen_toasts(apage):
    pg = apage
    fresh(pg)
    open_modal(pg, "done")
    pg.click("#ma11y")
    pg.wait_for_function("() => (document.querySelector('#toast').textContent || '').includes('접근성 문제 없음')", timeout=20000)
    assert pg.locator("#toast").inner_text().strip().startswith("접근성 문제 없음 (v1 규칙 8개 기준)")
    assert pg.locator("#a11yPanel").is_hidden() and pg.locator(".a11y-pin").count() == 0
    shot(pg, "4-no-problem-toast.png")


def test_card_menu_opens_large_view_and_checks(apage):
    pg = apage
    fresh(pg)
    b = pg.locator('.card[data-id="pay"] .cover').bounding_box()
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + 4, button="right")
    pg.click('#cmenu [data-act="card-a11y"]')
    pg.wait_for_selector("#modal:not([hidden])")
    pg.wait_for_selector("#a11yPanel:not([hidden])", timeout=20000)
    assert pg.locator("#a11yPanel li").count() == 3


def test_missing_axe_file_toasts_rebuild(apage):
    pg = apage
    axe = pg.out / "axe.min.js"
    keep = axe.with_suffix(".keep")
    axe.rename(keep)
    try:
        fresh(pg)
        open_modal(pg, "pay")
        pg.click("#ma11y")
        pg.wait_for_function("() => (document.querySelector('#toast').textContent || '').includes('접근성 검사 파일이 없어요')", timeout=20000)
        assert pg.locator("#a11yPanel").is_hidden()
        assert any("[hd]" in w and "axe.min.js" in w for w in pg.warns), pg.warns[-5:]
    finally:
        keep.rename(axe)
