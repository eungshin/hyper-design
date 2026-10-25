"""블록 기본(task 49a) — 브라우저. 판: 고른 카드를 이동(V)으로 한 번 더 누르면 요소 막대 · 복제·Alt+↓ 가 도우미로 바로 파일에, 되돌리기 = 되살리기.
글자 고치기는 도우미가 있으면 바로 파일에. 크게 보기: 글자(T)·이동(고르기) 도구가 켜지고, 오른쪽 클릭 = 요소 메뉴, 고르면 요소 막대(도우미 없으면 반영 대기 미리보기).
앱 카드(file = 개발 서버 주소): 막대의 편집은 모두 AI 요청(메모 창에 요청 글), 파일은 그대로. 규칙은 test_canvas_unit_blocks.py(unit)."""
import functools, http.server, json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, zoom_to  # noqa: F401
from test_canvas_edit import NOTES_JS, notes_of, wait_notes
from test_canvas_text_remove import _open, _frame, _serve, out  # noqa: F401

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
    pg.wait_for_selector("#selbar:not([hidden])", timeout=8000)
    pg.wait_for_timeout(600)
    pg.mouse.click(*xy)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)


def _bar(pg):
    return pg.evaluate("[...document.querySelectorAll('#elbar button')].map(b => [b.dataset.act, b.textContent, b.getAttribute('aria-disabled') !== 'true', !!b.dataset.ask])")


def _frame_until(pg, js, arg=None, sid="job"):
    """쓴 뒤 카드가 새 버전(?v=)으로 바뀌어(48a: 숨은 둘째 틀에 싣고 → 페이드 → 옛 틀 치움) 그 카드에 틀이 하나만 남고, 그 틀에서 js 가 참이 될 때까지.
    옛 틀 핸들을 잡지 않고 매번 카드의 지금 iframe 을 다시 찾는다."""
    sel = '.card[data-id="%s"] .phone iframe' % sid
    for _ in range(250):
        try:
            fs = pg.query_selector_all(sel)
            if len(fs) == 1 and "?v=" in (fs[0].get_attribute("src") or ""):
                fr = fs[0].content_frame()
                if fr and fr.evaluate(js, arg):
                    return
        except Exception:                                # 틀이 막 떨어짐·아직 없음
            pass
        pg.wait_for_timeout(100)
    raise AssertionError("카드가 새 파일로 다시 실리지 않았다: " + js)


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
        assert [b[0] for b in bar] == ["text", "remove", "dup", "up", "down", "memo"], bar
        assert [b[1] for b in bar] == ["글자", "지우기", "복제", "↑", "↓", "메모"] and all(b[2] and not b[3] for b in bar), bar
        e = pg.evaluate("(() => { const a = document.querySelector('#elbar').getBoundingClientRect(), b = document.querySelector('.elbox.sel').getBoundingClientRect(); return {bar: a.bottom, box: b.top, l: a.left, bl: b.left}; })()")
        assert e["bar"] <= e["box"] + 1 or e["bar"] > e["box"], e   # 막대는 고른 테두리 바로 옆(위 또는 아래)
        shot(pg, "board-elbar.png")
        pg.click('#elbar [data-act="dup"]')
        _wait_file(pg, out, lambda s: s.count('<h1 class="title">하는 일이 무엇인가요?</h1>') == 2, "복제가 파일에 바로 써지지 않았다")
        assert pg.evaluate("(" + NOTES_JS + ").length") == 0, "반영 대기로 남지 않는다"
        assert pg.is_hidden("#elbar"), "바뀐 카드의 고른 요소는 풀린다"
        _frame_until(pg, "(s) => document.querySelectorAll(s).length === 2", H1)
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
        pg.keyboard.press("Alt+ArrowUp")
        _wait_file(pg, out, lambda s: s.index("대학원생·연구원") < s.index("대학생<"), "Alt+↑ 가 앞 형제와 자리를 바꾸지 않았다")
        assert "</button>\n          <button" in _job(out), "형제 사이 줄바꿈·들여쓰기는 그대로"
        _frame_until(pg, "() => document.querySelector('.tile-grid > button').textContent.indexOf('대학원생') >= 0")
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
        pg.wait_for_selector("#tedit:not([hidden])", timeout=3000)
        pg.fill("#tedit textarea", "바로 바뀐 제목")
        pg.press("#tedit textarea", "Enter")
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
    pg.wait_for_selector("#tedit:not([hidden])", timeout=3000)
    pg.press("#tedit textarea", "Escape")
    mf.click(H1, button="right")                            # 오른쪽 클릭 = 판과 같은 요소 메뉴
    pg.wait_for_selector("#cmenu:not([hidden])", timeout=3000)
    items = pg.evaluate("[...document.querySelectorAll('#cmenu button')].map(b => b.childNodes[0].textContent)")
    assert {"글자 고치기", "요소 지우기", "요소 복제", "위로 옮기기", "아래로 옮기기", "요소에 메모"} <= set(items), items
    assert "잇기" not in items and "도착 바꾸기" not in items, "크게 보기에서는 판에서 도착을 고르는 항목이 없다"
    pg.locator("#cmenu button", has_text="요소 복제").first.click()
    wait_notes(pg, 1)
    assert notes_of(pg)[0]["edit"] == "duplicate"
    mf.wait_for_function("(s) => document.querySelectorAll(s).length === 2", arg=H1, timeout=3000)   # 도우미 없음 = 반영 대기 미리보기(점선 복사본)
    pg.click('#tools [data-tool="move"]')                   # 이동 = 요소 고르기 → 요소 막대
    mf.click(".lead")
    pg.wait_for_selector("#elbar:not([hidden])", timeout=8000)
    assert pg.get_attribute("#elbar", "data-where") == "modal"
    shot(pg, "modal-elbar.png")
    pg.click('#elbar [data-act="down"]')
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
    assert [b[3] for b in bar] == [True, True, True, True, True, False], ("앱 카드 = 편집 단추는 모두 AI 요청", bar)
    shot(pg, "board-elbar-app.png")
    pg.click('#elbar [data-act="dup"]')
    pg.wait_for_selector("#pop:not([hidden])", timeout=3000)
    assert pg.input_value("#pnote").startswith("요소 복제"), pg.input_value("#pnote")
    pg.click("#padd")
    wait_notes(pg, 1)
    n = notes_of(pg)[0]
    assert not n.get("edit") and n["note"].startswith("요소 복제"), "편집 메모가 아니라 AI 요청 메모"
    assert _job(app_out) == before, "앱 카드 파일은 건드리지 않는다"
    assert not errors, errors
    pg.close()
