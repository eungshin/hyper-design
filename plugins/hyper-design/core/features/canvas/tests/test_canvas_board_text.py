"""판 글 = 고를 수 있는 글 레이어(t51-9, Figma F1·F9·F10·F12·F14·F15 · FINDINGS 틈 #22) — 브라우저.

사용자 보고: "HTML 을 처음 만들 때 생긴 판 위 글은 고르거나 지울 수 없다". 판 글 = 카드 iframe 밖 글 전부:
위 소개(안내 줄 · 제목·요약 · 아이디어 · 사람 · 정한 것 · 시장 관례), 아래 끝 글, 카드 아래 글(제목·본문 — R21), DS 카드, 줄 제목.
이동 도구(V)로 누르면 고르기(파란 상자 + 이름표), 올리면 얇은 테두리, Esc·빈 곳 = 풀기, Enter·두 번 = 그 자리 고치기(고른 채 남음),
Delete·Backspace = 파일에서 빼기(되돌리기 한 줄). 카드 제목은 비울 수 없음(토스트) · 본문 = 비우기(합쳐 보이던 옛 정책 줄까지).
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, reload  # noqa: F401
from test_canvas_edit import fit_view, notes_of

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")                   # 눈으로 볼 때만: 스크린숏 폴더
SEL = "() => { const b = document.getElementById('btsel'); return b && !b.hidden ? b.dataset.label : null; }"
SELECTED = "() => window.HD && HD.__btSelected ? HD.__btSelected() : null"


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-boardtext-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def _sj(o):
    return json.loads((o / "screens.json").read_text(encoding="utf-8"))


def _wait(fn, timeout=20.0):
    import time
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.1)
    return False


def _open(ctx, url):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    pg.evaluate("window.__hdStay = 1")
    fit_view(pg)
    return pg, errors


def _helper(ctx, o):
    srv = helper.make_server(o, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg, errors = _open(ctx, srv.url)
    return srv, pg, errors


def _show(pg, sel):
    """그 글이 화면 안에 오게 판을 옮긴다(글 위를 실제 마우스로 누르기 위해)."""
    pg.evaluate("(s) => document.querySelector(s).scrollIntoView({block: 'center'})", sel)
    pg.wait_for_timeout(100)


def _click(pg, sel, **kw):
    box = pg.locator(sel).first.bounding_box()
    assert box, sel
    x, y = box["x"] + min(40, box["width"] / 2), box["y"] + min(20, box["height"] / 2)
    if kw.get("dbl"):
        pg.mouse.dblclick(x, y)
    else:
        pg.mouse.click(x, y)
    pg.wait_for_timeout(150)


@pytest.mark.area("tools", "layers")
def test_move_click_selects_intro_section_and_delete_removes_it_from_file_with_one_undo(ctx, out):
    srv, pg, errors = _helper(ctx, out)
    try:
        assert _sj(out)["story"].get("ideas"), "고정본에 아이디어가 있다"
        pg.keyboard.press("v")
        _click(pg, ".story .ideas .idea")
        assert pg.evaluate(SEL) == "소개 · 아이디어", "V 로 누르기 = 그 판 글 고르기(파란 상자 + 이름표)"
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "t51-9-selected.png"))
        pg.keyboard.press("Escape")
        assert pg.evaluate(SEL) is None, "Esc = 풀기"
        _click(pg, ".story .ideas .idea")
        assert pg.evaluate(SEL) == "소개 · 아이디어"
        pg.keyboard.press("Delete")
        pg.wait_for_function("!document.querySelector('#intro .ideas')", timeout=5000)
        assert _wait(lambda: "ideas" not in _sj(out)["story"]), "파일(screens.json)에서도 빠짐"
        assert _sj(out)["story"].get("headline"), "같은 소개의 다른 칸은 그대로"
        assert pg.locator(".card").count() > 0, "카드는 그대로"
        pg.wait_for_function("document.getElementById('toast').textContent.includes('파일에 썼어요')", timeout=5000)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "t51-9-deleted-toast.png"))
        pg.keyboard.press("Control+z")
        pg.wait_for_function("!!document.querySelector('#intro .ideas')", timeout=10000)
        assert _wait(lambda: _sj(out)["story"].get("ideas")), "되돌리기 한 번 = 파일도 제자리"
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "layers")
def test_hover_outline_layers_rows_and_in_place_edit_stays_selected(ctx, out):
    srv, pg, errors = _helper(ctx, out)
    try:
        pg.keyboard.press("v")
        box = pg.locator(".story .sum").bounding_box()
        pg.mouse.move(box["x"] + 30, box["y"] + 10)
        pg.wait_for_timeout(100)
        assert pg.evaluate("() => { const b = document.getElementById('bthov'); return !!b && !b.hidden; }"), "올리면 얇은 테두리(51-3)"
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "t51-9-hover.png"))
        # 레이어 패널 = 판 글이 따로따로
        pg.click('#dock .dk-tab[data-p="layers"]')
        ids = pg.evaluate("() => [...document.querySelectorAll('#lyTree [data-kind=\"text\"]')].map(r => r.dataset.ly)")
        for want in ("@intro-story", "@intro-ideas", "@intro-people", "@intro-decisions"):
            assert want in ids, (want, ids)
        pg.hover('#lyTree [data-ly="@intro-people"] .ly-name')
        assert pg.evaluate("() => document.getElementById('intro-people').classList.contains('lyhov-t')"), "레이어 줄 올리기 = 판 강조"
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "t51-9-layers.png"))
        pg.mouse.move(700, 500)
        # 두 번 누르기 = 그 자리 고치기 → Enter 저장 → 파일 · 고른 채
        _click(pg, ".story .sum", dbl=True)
        assert pg.evaluate("() => document.activeElement && document.activeElement.matches('.story .sum[contenteditable]')"), "그 자리 고치기"
        pg.keyboard.press("Control+a")
        pg.keyboard.type("새 요약 한 줄")
        pg.keyboard.press("Enter")
        assert _wait(lambda: _sj(out)["story"].get("summary") == "새 요약 한 줄"), _sj(out)["story"].get("summary")
        pg.wait_for_function("document.querySelector('.story .sum').textContent === '새 요약 한 줄'", timeout=5000)
        assert pg.evaluate(SEL) == "소개 · 제목·요약", "고친 뒤에도 골라진 채(F14)"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "notes")
def test_caption_description_delete_clears_and_title_delete_is_refused(ctx, out):
    srv, pg, errors = _helper(ctx, out)
    try:
        pg.keyboard.press("v")
        _show(pg, '.card[data-id="job"]')
        _click(pg, '.card[data-id="job"] .cover')
        pg.wait_for_selector('.card[data-id="job"].picked')
        assert pg.locator('.card[data-id="job"] .fdesc').is_visible()
        _click(pg, '.card[data-id="job"] .ftitle')
        assert pg.evaluate(SEL) == "카드 제목"
        n0 = len(notes_of(pg))
        pg.keyboard.press("Delete")
        pg.wait_for_function("document.getElementById('toast').textContent.includes('제목은 비울 수 없어요')", timeout=3000)
        assert pg.locator('.card[data-id="job"]').count() == 1, "카드가 지워지지 않는다"
        assert len(notes_of(pg)) == n0, "제목 = 쓰지 않음"
        _click(pg, '.card[data-id="job"] .fdesc')
        assert pg.evaluate(SEL) == "카드 설명"
        pg.keyboard.press("Backspace")
        pg.wait_for_function("() => { const n = JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.startsWith('hd-notes:'))) || '[]');"
                             " return n.some(x => x.screen === 'job' && x.edit === 'purpose' && x.value === '')"
                             " && n.some(x => x.screen === 'job' && x.edit === 'policies' && x.value.length === 0); }", timeout=3000)
        assert pg.locator('.card[data-id="job"]').count() == 1
        pg.wait_for_function("!document.querySelector('.card[data-id=\"job\"] .fdesc')", timeout=3000)   # 본문 = 비우기(반영 대기) — 빈 본문은 그리지 않는다
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "notes")
def test_without_helper_delete_queues_pending_edit_and_undo_brings_it_back(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    try:
        pg.keyboard.press("v")
        _click(pg, ".people li")
        assert pg.evaluate(SEL) == "소개 · 사람"
        pg.keyboard.press("Delete")
        pg.wait_for_function("!document.querySelector('#intro .people')", timeout=3000)
        ns = [n for n in notes_of(pg) if n.get("edit") == "board"]
        assert len(ns) == 1 and ns[0]["op"] == "delete" and ns[0]["to"] == "people", ns
        assert _sj(out).get("people"), "도우미 없이 = 파일은 그대로(반영 대기)"
        pg.keyboard.press("Control+z")
        pg.wait_for_function("!!document.querySelector('#intro .people')", timeout=3000)
        assert not [n for n in notes_of(pg) if n.get("edit") == "board"]
    finally:
        pg.close()
    assert not errors, errors
