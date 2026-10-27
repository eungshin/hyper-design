"""블록 기본(task 49a) — 브라우저. 판: 고른 카드를 이동(V)으로 한 번 더 누르면 요소 막대 · 복제·Alt+↓ 가 도우미로 바로 파일에, 되돌리기 = 되살리기.
글자 고치기는 도우미가 있으면 바로 파일에. 크게 보기: 글자(T)·이동(고르기) 도구가 켜지고, 오른쪽 클릭 = 요소 메뉴, 고르면 요소 막대(도우미 없으면 반영 대기 미리보기).
앱 카드(file = 개발 서버 주소): 막대의 편집은 모두 AI 요청(메모 창에 요청 글), 파일은 그대로. 규칙은 test_canvas_unit_blocks.py(unit)."""
import functools, http.server, json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, swap_done, swap_mark, zoom_to  # noqa: F401
from test_canvas_edit import NOTES_JS, notes_of, wait_notes
from test_canvas_text_remove import _open, _frame, _serve, inline_type, out  # noqa: F401

SHOTS = Path(os.environ.get("HD_SHOTS_49A", Path(tempfile.gettempdir()) / "claude" / "t49a"))
H1 = "h1.title"
TILE2 = ".tile-grid > button:nth-of-type(2)"
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def _xy(pg, sel, sid="job"):
    """sid 카드를 키워 sel 요소 가운데의 판 좌표."""
    ph = zoom_to(pg, sid, 420)
    fr = _frame(pg, sid)
    fr.wait_for_selector(sel, state="attached", timeout=5000)
    r = fr.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left + b.width / 2, y: b.top + b.height / 2}; }", sel)
    sc = ph["width"] / pg.evaluate("JSON.parse(document.getElementById('hd-data').textContent).card?.w || 375")
    return ph["x"] + r["x"] * sc, ph["y"] + r["y"] * sc


def _pick_element(pg, xy):
    """이동(V): 카드 고르기 → 잠시 뒤(두 번 누르기 아님) 한 번 더 = 그 자리 요소 → 요소 막대."""
    pg.keyboard.press("v")
    pg.mouse.click(*xy)
    pg.wait_for_selector("#selbar:not([hidden]), #elbar:not([hidden])", timeout=8000)   # R27 F06: 요소를 고른 채면 카드 막대 대신 요소 막대
    pg.wait_for_timeout(600)
    pg.mouse.click(*xy)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)


def _act(pg, act):
    """요소 동작 하나를 뜻(data-act)으로 — 막대 아이콘에 있으면 막대에서, 아니면 막대 [⋯] 가 여는 요소 메뉴에서(R17 시안 A)."""
    if pg.is_visible('#elbar [data-act="%s"]' % act):
        pg.click('#elbar [data-act="%s"]' % act)
    else:
        pg.click('#elbar [data-act="more"]')
        if act in ("insert", "swap"):                 # R30: 부품 ▸ 옆 목록 안
            pg.click('#cmenu:not([hidden]) button[data-act="part"]')
            pg.click('#cmsub:not([hidden]) button[data-act="%s"]' % act)
        else:
            pg.click('#cmenu:not([hidden]) button[data-act="%s"]' % act)


def _bar(pg):
    return pg.evaluate("[...document.querySelectorAll('#elbar button[data-act]')].map(b => [b.dataset.act, b.textContent, b.getAttribute('aria-disabled') !== 'true', !!b.dataset.ask])")


def _frame_until(pg, js, mark, arg=None, sid="job"):
    """쓴 뒤 그 카드의 교체(48a: 숨은 둘째 틀에 싣고 → 페이드 → 옛 틀 치움)가 끝나면(swap_done, mark = 쓰기 전 swap_mark) 그 카드의 지금 틀에서 js 가 참이 될 때까지."""
    swap_done(pg, sid, mark)
    _frame(pg, sid).wait_for_function(js, arg=arg, timeout=5000)


def _logged(pg):
    """도우미가 답해 기록 줄(파일에 씀)이 생길 때까지 — 그 전에 되돌리면 앞 단계를 되돌린다."""
    pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hs').textContent === '파일에 씀'", timeout=20000)


def _job(o):
    return (o / "screens" / "job.html").read_text(encoding="utf-8")


def _wait_file(pg, o, ok, what):
    for _ in range(200):
        try:
            if ok(_job(o)):
                return
        except PermissionError:                          # Windows: 도우미가 막 쓰는(되살리는) 중이면 잠깐 못 읽는다
            pass
        pg.wait_for_timeout(100)
    raise AssertionError(what)


@pytest.mark.area("helper", "tools")
def test_board_element_bar_duplicate_writes_file_and_undo_restores(ctx, out):
    before = _job(out)
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        xy = _xy(pg, H1)
        _pick_element(pg, xy)
        bar = _bar(pg)
        assert [b[0] for b in bar] == ["grip", "memo", "text", "ai", "more"], ("R17 시안 A: 손잡이 + 메모·글자·AI + ⋯ — 나머지는 ⋯ 메뉴", bar)
        assert all(b[2] and not b[3] for b in bar), bar
        assert pg.is_visible("#elbar .eb-grip"), "끌기 손잡이"
        assert pg.is_hidden("#selbar"), "R27 F06: 요소 막대가 뜨면 카드 막대는 숨김 — 막대 하나만"
        e = pg.evaluate("(() => { const a = document.querySelector('#elbar').getBoundingClientRect(), b = document.querySelector('.elbox.sel').getBoundingClientRect(); return {bar: a.bottom, box: b.top, l: a.left, bl: b.left}; })()")
        assert e["bar"] <= e["box"] + 1 or e["bar"] > e["box"], e   # 막대는 고른 테두리 바로 옆(위 또는 아래)
        shot(pg, "board-elbar.png")
        m = swap_mark(pg)
        _act(pg, "dup")
        _wait_file(pg, out, lambda s: s.count('<h1 class="title">하는 일이 무엇인가요?</h1>') == 2, "복제가 파일에 바로 써지지 않았다")
        assert pg.evaluate("(" + NOTES_JS + ").length") == 0, "반영 대기로 남지 않는다"
        assert pg.is_hidden("#elbar"), "바뀐 카드의 고른 요소는 풀린다"
        _frame_until(pg, "(s) => document.querySelectorAll(s).length === 2", m, H1)
        pg.wait_for_timeout(500)
        shot(pg, "board-duplicate-after.png")
        _logged(pg)
        pg.click("#undo")
        _wait_file(pg, out, lambda s: s == before, "되돌리기 = 되살리기")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools")
def test_alt_arrow_moves_element_in_file_and_undo_restores(ctx, out):
    before = _job(out)
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        xy = _xy(pg, TILE2)
        _pick_element(pg, xy)
        shot(pg, "board-move-before.png")
        m = swap_mark(pg)
        pg.keyboard.press("Alt+ArrowUp")
        _wait_file(pg, out, lambda s: s.index("대학원생·연구원") < s.index("대학생<"), "Alt+↑ 가 앞 형제와 자리를 바꾸지 않았다")
        assert "</button>\n          <button" in _job(out), "형제 사이 줄바꿈·들여쓰기는 그대로"
        _frame_until(pg, "() => document.querySelector('.tile-grid > button').textContent.indexOf('대학원생') >= 0", m)
        pg.wait_for_timeout(500)
        shot(pg, "board-move-after.png")
        _logged(pg)
        pg.keyboard.press("Control+z")
        _wait_file(pg, out, lambda s: s == before, "되돌리기 = 되살리기")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "tools")
def test_text_edit_writes_at_once_with_helper(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        xy = _xy(pg, H1)
        pg.keyboard.press("t")
        pg.mouse.click(*xy)
        inline_type(pg, _frame(pg), H1, "바로 바뀐 제목")   # 그 자리에서(49c)
        _wait_file(pg, out, lambda s: '<h1 class="title">바로 바뀐 제목</h1>' in s, "글자가 [보내기] 없이 바로 써지지 않았다")
        assert pg.evaluate("(" + NOTES_JS + ").length") == 0, "반영 대기로 남지 않는다"
        _logged(pg)
        pg.keyboard.press("Control+z")
        _wait_file(pg, out, lambda s: '<h1 class="title">하는 일이 무엇인가요?</h1>' in s, "되돌리기 = 되살리기")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def _modal(pg):
    pg.keyboard.press("0")
    pg.evaluate("document.querySelector('.card[data-id=\"job\"] .pres').click()")
    pg.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    mf = next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")
    mf.wait_for_selector(H1, timeout=5000)
    return mf


@pytest.mark.area("modal", "tools")
def test_large_view_text_tool_context_menu_and_element_bar(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    mf = _modal(pg)
    st = dict((t, d) for t, d in pg.evaluate("[...document.querySelectorAll('#tools [data-tool]')].map(b => [b.dataset.tool, b.getAttribute('aria-disabled')])"))
    assert st["text"] is None and st["move"] is None and st["annotate"] is None, st
    pg.click('#tools [data-tool="text"]')                   # 글자 도구: 한 번 누르면 그 자리에서 고친다(더블클릭 아니어도)
    mf.click(H1)
    mf.wait_for_function("(s) => document.querySelector(s).isContentEditable", arg=H1, timeout=3000)   # 그 자리에서(49c)
    pg.keyboard.press("Escape")
    mf.wait_for_function("(s) => !document.querySelector(s).isContentEditable", arg=H1, timeout=3000)
    mf.click(H1, button="right")                            # 오른쪽 클릭 = 판과 같은 요소 메뉴
    pg.wait_for_selector("#cmenu:not([hidden])", timeout=3000)
    items = pg.evaluate("[...document.querySelectorAll('#cmenu button')].map(b => b.dataset.act)")
    assert {"text", "remove", "dup", "memo", "chain", "part", "addr"} <= set(items) and len(items) <= 10, items   # R30: 넣기·바꾸기 = 부품 ▸ · R27 F05: 위/아래·상위·AI 는 키(Alt+↑↓ · Shift+Enter)·막대 아이콘
    assert "link" not in items and "retarget" not in items, "크게 보기에서는 판에서 도착을 고르는 항목이 없다"
    pg.click('#cmenu button[data-act="dup"]')
    wait_notes(pg, 1)
    assert notes_of(pg)[0]["edit"] == "duplicate"
    mf.wait_for_function("(s) => document.querySelectorAll(s).length === 2", arg=H1, timeout=3000)   # 도우미 없음 = 반영 대기 미리보기(점선 복사본)
    pg.click('#tools [data-tool="move"]')                   # 이동 = 요소 고르기 → 요소 막대
    mf.click(".lead")
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    assert pg.get_attribute("#elbar", "data-where") == "modal"
    shot(pg, "modal-elbar.png")
    pg.keyboard.press("Alt+ArrowDown")                    # ↓ 는 막대에서 빠지고 단축키로(49c)
    wait_notes(pg, 2)
    assert notes_of(pg)[1]["edit"] == "move" and notes_of(pg)[1]["op"] == "down", notes_of(pg)
    mf.wait_for_function("() => document.querySelector('.lead').nextElementSibling === null || document.querySelector('.lead').previousElementSibling.classList.contains('tile-grid')", timeout=3000)
    pg.keyboard.press("Control+z")
    pg.keyboard.press("Control+z")
    wait_notes(pg, 0)
    assert not errors, errors
    pg.close()


# ---------------------------------------------------------------- 앱 카드: 편집 = AI 요청
class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture()
def app_out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-blocks-app-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    dev = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(o)))
    threading.Thread(target=dev.serve_forever, daemon=True).start()
    sj = o / "screens.json"
    data = json.loads(sj.read_text(encoding="utf-8"))
    for s in data["screens"]:
        if s["id"] == "job":
            s["file"] = "http://127.0.0.1:%d/screens/job.html" % dev.server_address[1]
    sj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    try:
        yield o
    finally:
        dev.shutdown(); dev.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.area("tools", "notes")
def test_app_card_bar_turns_edits_into_ai_requests(ctx, app_out):
    before = _job(app_out)
    pg, errors = _open(ctx, (app_out / "index.html").resolve().as_uri())
    xy = _xy(pg, H1)
    _pick_element(pg, xy)
    bar = _bar(pg)
    assert [b[0] for b in bar if b[3]] == ["text"], ("앱 카드 = 막대의 글자는 AI 요청(메모·AI·⋯ 는 아님)", bar)
    shot(pg, "board-elbar-app.png")
    _act(pg, "dup")
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.input_value("#pnote").startswith("요소 복제"), pg.input_value("#pnote")
    pg.click("#padd")
    wait_notes(pg, 1)
    n = notes_of(pg)[0]
    assert not n.get("edit") and n["note"].startswith("요소 복제"), "편집 메모가 아니라 AI 요청 메모"
    assert _job(app_out) == before, "앱 카드 파일은 건드리지 않는다"
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_backspace_on_a_picked_element_removes_the_element_not_the_card(ctx, out):
    """요소를 고른 채 Backspace = 그 요소 지우기(Figma 처럼 Delete 와 같다) — 전에는 고른 카드 전체가 지워졌다(51 조사)."""
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        _pick_element(pg, _xy(pg, H1))
        pg.keyboard.press("Backspace")
        _wait_file(pg, out, lambda s: '<h1 class="title">' not in s, "Backspace 로 요소가 지워지지 않았다")
        assert pg.locator('.card[data-id="job"]').count() == 1, "카드는 남는다"
        assert (out / "screens" / "job.html").is_file(), "화면 파일은 남는다"
    finally:
        srv.shutdown(); srv.server_close()


@pytest.mark.area("tools", "notes")
def test_icon_bar_tip_ai_request_and_more_menu(ctx, out):
    """R17 시안 A: 막대 아이콘에 올리면 이름·단축키 꼬리말 · [AI] = 메모 창에 바꿔 달라는 글 · [⋯] = 묶음·단축키가 있는 요소 메뉴,
    그 메뉴의 상위 고르기 = 막대의 상위 길(부모가 골라짐). 도구 꼬리말 = '선택 V'. 스크린샷 = HD_SHOTS_49A."""
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    pg.hover('#tools [data-tool="move"]')
    pg.wait_for_selector("#ttip:not([hidden])", timeout=2000)
    assert pg.text_content("#ttip").startswith("선택V"), pg.text_content("#ttip")
    shot(pg, "r17-tool-tip.png")
    xy = _xy(pg, H1)
    _pick_element(pg, xy)
    pg.hover('#elbar [data-act="text"]')
    pg.wait_for_selector("#eltip:not([hidden])", timeout=2000)
    assert pg.text_content("#eltip") == "글자 고치기Enter", pg.text_content("#eltip")
    shot(pg, "r17-bar-tip.png")
    pg.click('#elbar [data-act="ai"]')
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.input_value("#pnote").startswith("바꿔 주세요"), pg.input_value("#pnote")
    assert pg.get_attribute('#pintent [data-intent="change"]', "aria-pressed") == "true", "의도 = 바꾸기"
    pg.keyboard.press("Escape")
    _pick_element(pg, xy)
    path0 = pg.get_attribute("#elbar", "data-path")
    pg.click('#elbar [data-act="more"]')
    pg.wait_for_selector("#cmenu:not([hidden]) button[data-act]", timeout=3000)
    assert pg.locator("#cmenu .cmh.sub").count() == 0, "R27 F05: 묶음 = 구분선(회색 소제목 없음)"
    keys = dict(pg.evaluate("[...document.querySelectorAll('#cmenu button[data-act]')].map(b => [b.dataset.act, (b.querySelector('kbd') || {}).textContent || ''])"))
    assert list(keys)[0] == "chain" and keys["dup"] == "Ctrl+D" and keys["remove"] == "Del" and keys["memo"] == "" and "parent" not in keys, keys
    pg.wait_for_timeout(300)                              # 메뉴 열림 움직임이 끝난 뒤
    shot(pg, "r17-more-menu.png")
    pg.hover('#cmenu button[data-act="chain"]')        # R27 F05: 상위 고르기 = 레이어 고르기 ▸ 둘째 줄(상자가 다른 첫 조상) · 키 Shift+Enter
    pg.wait_for_selector("#cmsub:not([hidden]) button:nth-of-type(2)", timeout=4000)
    pg.click("#cmsub button:nth-of-type(2)")
    pg.wait_for_function("(p) => { const b = document.querySelector('#elbar'); return !b.hidden && b.dataset.path && b.dataset.path !== p; }", arg=path0, timeout=5000)
    assert "h1" not in pg.get_attribute("#elbar", "data-path"), ("메뉴의 상위 고르기 = 감싼 요소", path0, pg.get_attribute("#elbar", "data-path"))
    assert not errors, errors
    pg.close()
