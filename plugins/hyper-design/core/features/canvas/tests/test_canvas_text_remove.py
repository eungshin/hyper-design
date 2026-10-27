"""글자 고치기가 옛 글을 남기던 버그(task 30, K1) · 글 비우기 · 요소 지우기 — 브라우저.

K1: 두 줄 글을 두 번 고치면(도우미가 파일에 씀) 카드·파일에 마지막 글만. 비우기: 빈 글 저장 = 요소 글이 빔(미리보기), 되돌리기 = 원래 글.
요소 지우기: 요소 메뉴 '요소 지우기' → 카드에서 사라짐(미리보기), 되돌리기 = 다시 보임 · 도우미가 있으면 화면 파일에서 바로 지워지고 되돌리기 = 되살리기.
"""
import os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, reload, swap_done, swap_mark, zoom_to  # noqa: F401
from test_canvas_edit import NOTES_JS, notes_of, wait_notes

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
H1 = "h1.title"
OLD = "하는 일이 무엇인가요?"


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-textrm-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def _open(ctx, url):
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    return pg, errors


def _frame(pg, sid="job"):
    """그 카드의 지금 iframe 의 frame — 보이게 된 카드가 실릴 때까지 잠깐 기다린다(-n 4 부하·48a 교체 중엔 틀이 늦게 생기거나 바뀐다)."""
    sel = '.card[data-id="%s"] .phone iframe' % sid
    for _ in range(100):
        fs = pg.query_selector_all(sel)
        fr = fs[-1].content_frame() if fs else None
        if fr and fr.url.split("?")[0].endswith("/" + sid + ".html"):
            return fr
        pg.wait_for_timeout(100)
    raise AssertionError("카드 iframe 이 실리지 않았다: " + sid)


def _h1_xy(pg):
    """job 카드를 키워 제목(h1) 가운데의 판 좌표."""
    ph = zoom_to(pg, "job", 420)
    fr = _frame(pg)
    fr.wait_for_selector(H1, state="attached", timeout=5000)
    r = fr.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }", H1)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    return ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc


def _edit_text(pg, xy, value):
    pg.keyboard.press("e")                               # 글자 도구: 글자 위를 한 번 누르면 그 요소만 그 자리에서 고친다(49c — 글 칸 없음)
    pg.mouse.click(*xy)
    inline_type(pg, _frame(pg), H1, value)
    assert pg.is_hidden("#tedit")


def inline_type(pg, fr, sel, value):
    """49c 그 자리 글자 고치기: 그 요소가 contenteditable 이 될 때까지 → 글 전체를 바꿔 쓰고(\n = Shift+Enter) Enter."""
    fr.wait_for_function("(s) => { const e = document.querySelector(s); return !!e && e.isContentEditable; }", arg=sel, timeout=3000)
    for i, line in enumerate(value.split("\n")):
        if i:
            pg.keyboard.press("Shift+Enter")
        if line:
            pg.keyboard.type(line)
    if not value:
        pg.keyboard.press("Backspace")                   # 다 지우기 = 글 비우기
    pg.keyboard.press("Enter")


def _pick_el(pg, xy):
    """이동(V): 카드 고르기 → 잠시 뒤 한 번 더 = 그 자리 요소(R27 F05: 요소 메뉴는 요소를 고른 카드 안에서만)."""
    pg.keyboard.press("v")
    pg.mouse.click(*xy)
    pg.wait_for_selector("#selbar:not([hidden]), #elbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(*xy)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)


def _h1_in_file(o):
    s = (o / "screens" / "job.html").read_text(encoding="utf-8")
    i = s.find('<h1 class="title">')
    return None if i < 0 else s[i + len('<h1 class="title">'): s.find("</h1>", i)]


def _wait_h1(pg, o, want):
    for _ in range(200):
        if _h1_in_file(o) == want:
            return
        pg.wait_for_timeout(100)
    assert _h1_in_file(o) == want


def _serve(o):
    srv = helper.make_server(o, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.mark.area("helper", "tools")
def test_editing_a_two_line_text_twice_leaves_only_the_latest(ctx, out):   # K1 — 사용자 보고 1 "이전 입력이 지워지지 않는다"
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        xy = _h1_xy(pg)
        # task 49a: 도우미가 있으면 글자 고치기가 [보내기] 없이 바로 파일에(예전 = 반영 대기 → 보내기). 지키는 것은 같다: 두 번째 고치기 뒤 파일·카드에 마지막 글만
        m = swap_mark(pg)
        _edit_text(pg, xy, "줄1\n줄2")
        _wait_h1(pg, out, "줄1<br>줄2")
        swap_done(pg, "job", m)                          # 바뀐 카드 다시 싣기
        xy = _h1_xy(pg)
        _edit_text(pg, xy, "끝")
        _wait_h1(pg, out, "끝")                          # 두 번째 고치기 뒤 옛 줄(줄2)이 남으면 안 된다
        got = None
        for _ in range(100):                             # 다시 실린 카드에도 마지막 글만
            try:
                got = _frame(pg).evaluate("(s) => document.querySelector(s).textContent.trim()", H1)
            except Exception:                            # 카드를 다시 싣는 중
                got = None
            if got == "끝":
                break
            pg.wait_for_timeout(100)
        assert got == "끝", got
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_clearing_a_text_empties_the_element_and_undo_restores(ctx, out):   # 사용자 보고 2 — 다 지우면 비워진다(강제로 남는 글 없음)
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    xy = _h1_xy(pg)
    fr = _frame(pg)
    _edit_text(pg, xy, "")
    wait_notes(pg, 1)
    n = notes_of(pg)[0]
    assert n["edit"] == "text" and n["value"] == "" and n["note"].startswith("글자 비우기"), n
    fr.wait_for_function("(s) => { const e = document.querySelector(s); return e && e.textContent === ''; }", arg=H1, timeout=3000)
    pg.keyboard.press("Control+z")
    wait_notes(pg, 0)
    fr.wait_for_function("([s, t]) => document.querySelector(s).textContent.trim() === t", arg=[H1, OLD], timeout=3000)
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_element_menu_removes_element_from_card_and_undo_brings_it_back(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    xy = _h1_xy(pg)
    fr = _frame(pg)
    _pick_el(pg, xy)                                     # R27 F05: 요소 메뉴 = 요소를 고른 카드 안에서
    pg.mouse.click(*xy, button="right")
    pg.wait_for_selector('#cmenu:not([hidden]) button[data-act="remove"]', timeout=3000)
    pg.click('#cmenu button[data-act="remove"]')
    wait_notes(pg, 1)
    n = notes_of(pg)[0]
    assert n["edit"] == "remove" and n["path"].endswith("h1.title:nth-of-type(1)"), n
    fr.wait_for_function("(s) => getComputedStyle(document.querySelector(s)).display === 'none'", arg=H1, timeout=3000)
    req = pg.evaluate("HD.edits.request(" + NOTES_JS + ", 'o')")
    assert "   요청: 요소 지우기" in req, req
    pg.keyboard.press("Control+z")
    wait_notes(pg, 0)
    fr.wait_for_function("(s) => getComputedStyle(document.querySelector(s)).display !== 'none'", arg=H1, timeout=3000)
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools")
def test_remove_with_helper_writes_the_file_and_undo_restores_it(ctx, out):
    before = (out / "screens" / "job.html").read_bytes()
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        xy = _h1_xy(pg)
        _pick_el(pg, xy)
        pg.mouse.click(*xy, button="right")
        pg.wait_for_selector('#cmenu:not([hidden]) button[data-act="remove"]', timeout=3000)
        pg.click('#cmenu button[data-act="remove"]')
        pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hs').textContent === '파일에 씀'", timeout=20000)
        assert _h1_in_file(out) is None, "요소가 화면 파일에서 지워졌다"
        assert pg.evaluate("(" + NOTES_JS + ").length") == 0, "반영 대기로 남지 않는다"
        pg.click("#undo")
        pg.wait_for_function("1", timeout=1000)
        for _ in range(100):
            if (out / "screens" / "job.html").read_bytes() == before:
                break
            pg.wait_for_timeout(100)
        assert (out / "screens" / "job.html").read_bytes() == before, "되돌리기 = 되살리기"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "modal")
def test_large_view_text_box_has_remove_element(ctx, out):   # 크게 보기: 두 번 누르면 그 자리 고치기(49c — 글 칸·그 안 '요소 지우기' 없음) · 지우기는 요소 메뉴
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    pg.keyboard.press("0")
    pg.evaluate("document.querySelector('.card[data-id=\"job\"] .pres').click()")
    pg.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    mf = next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")
    mf.wait_for_selector(H1, timeout=5000)
    mf.dblclick(H1)
    mf.wait_for_function("(s) => document.querySelector(s).isContentEditable", arg=H1, timeout=3000)
    assert pg.evaluate("document.getElementById('tedit').hidden"), "글 칸이 뜨지 않는다"
    pg.keyboard.press("Escape")
    mf.wait_for_function("(s) => !document.querySelector(s).isContentEditable", arg=H1, timeout=3000)
    mf.click(H1, button="right")
    pg.click('#cmenu button[data-act="remove"]')
    wait_notes(pg, 1)
    assert notes_of(pg)[0]["edit"] == "remove"
    mf.wait_for_function("(s) => getComputedStyle(document.querySelector(s)).display === 'none'", arg=H1, timeout=3000)
    assert not errors, errors
    pg.close()
