"""49c 바로 반영 편집 — 브라우저(도우미 있음, 크게 보기).

- 글자(T): 고른 요소 하나만 그 자리에서 contenteditable(글꼴·크기 그대로, 글 칸 #tedit 없음) · Esc = 원래 글 · Shift+Enter = 줄바꿈 · Enter = 저장 → 화면은 바로, 파일은 뒤에서.
  쓴 뒤 크게 보기 틀은 다시 싣지 않는다(같은 내용 — 두 번 깜빡임 없음).
- 끌어서 순서 바꾸기: 막대 손잡이 [⠿] 를 끌면 끼울 선 #eldrop · 놓으면 화면 순서가 바로, 파일은 도우미 move 두 번 뒤 같은 순서.
- 도우미가 거절(applied:[])하면 먼저 보인 복제를 되돌리고 까닭을 알린다.
규칙은 test_canvas_unit_instant.py(unit). 스크린샷 = HD_SHOTS_49C(기본 %TEMP%/claude/t49c).
"""
import json, os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx  # noqa: F401
from test_canvas_text_remove import _frame, _open, _serve, out  # noqa: F401

SHOTS = Path(os.environ.get("HD_SHOTS_49C", Path(tempfile.gettempdir()) / "claude" / "t49c"))
H1 = "h1.title"
TILE = ".tile-grid > button:nth-of-type(%d)"
TILES_JS = "() => [...document.querySelectorAll('.tile-grid > button')].map(b => b.textContent.replace(/\\d+$/, '').trim())"


def shot(pg, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS / name))


def _job(o):
    return (o / "screens" / "job.html").read_text(encoding="utf-8")


def _wait_file(pg, o, ok, what):
    for _ in range(300):
        try:
            if ok(_job(o)):
                return
        except PermissionError:                          # Windows: 도우미가 막 쓰는 중이면 잠깐 못 읽는다
            pass
        pg.wait_for_timeout(100)
    raise AssertionError(what)


def _modal(pg):
    pg.keyboard.press("0")
    pg.evaluate("document.querySelector('.card[data-id=\"job\"] .pres').click()")
    pg.wait_for_function("!document.getElementById('modal').hidden", timeout=3000)
    mf = next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")
    mf.wait_for_selector(H1, timeout=5000)
    pg.wait_for_timeout(300)
    return mf


def _in_modal(pg, mf, sel):
    """크게 보기 틀 안 요소 가운데의 화면 좌표(틀 배율 포함)."""
    r = mf.evaluate("(s) => { const b = document.querySelector(s).getBoundingClientRect(); return {x: b.left, y: b.top, w: b.width, h: b.height}; }", sel)
    f = pg.evaluate("(() => { const f = document.getElementById('mframe'), r = f.getBoundingClientRect(), sc = r.width / f.offsetWidth; return {x: r.left + f.clientLeft * sc, y: r.top + f.clientTop * sc, sc: sc}; })()")
    return {"x": f["x"] + r["x"] * f["sc"], "y": f["y"] + r["y"] * f["sc"], "w": r["w"] * f["sc"], "h": r["h"] * f["sc"]}


def _pick(pg, mf, sel):
    pg.click('#tools [data-tool="move"]')
    mf.click(sel)
    pg.wait_for_selector("#elbar:not([hidden])", timeout=5000)
    pg.wait_for_function("(s) => document.querySelector('#elbar').dataset.path && document.querySelector('#elbar').dataset.where === 'modal'", arg=sel, timeout=3000)


@pytest.mark.area("helper", "modal", "tools")
def test_text_tool_edits_in_place_and_writes_without_reloading_the_view(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal(pg)
        src0 = pg.get_attribute("#mframe", "src")
        font0 = mf.evaluate("(s) => getComputedStyle(document.querySelector(s)).font", H1)
        pg.evaluate("window.__swaps = []; document.addEventListener('hd-swap', e => window.__swaps.push(e.detail))")
        shot(pg, "inline-before.png")
        pg.click('#tools [data-tool="text"]')
        mf.click(H1)
        mf.wait_for_function("(s) => document.querySelector(s).isContentEditable && document.activeElement === document.querySelector(s)", arg=H1, timeout=3000)
        assert pg.is_hidden("#tedit"), "글 칸(팝업)이 뜨지 않는다"
        assert mf.evaluate("[...document.querySelectorAll('[contenteditable]')].length") == 1, "그 요소 하나만 고칠 수 있다(화면 전체 아님)"
        assert mf.evaluate("(s) => getComputedStyle(document.querySelector(s)).font", H1) == font0, "글꼴·크기 그대로"
        pg.keyboard.type("버릴 글")
        pg.keyboard.press("Escape")
        mf.wait_for_function("(s) => !document.querySelector(s).isContentEditable", arg=H1, timeout=3000)
        assert mf.text_content(H1).strip() == "하는 일이 무엇인가요?", "Esc = 원래 글"
        mf.click(H1)
        mf.wait_for_function("(s) => document.querySelector(s).isContentEditable", arg=H1, timeout=3000)
        pg.keyboard.type("바로 고친")
        pg.keyboard.press("Shift+Enter")
        pg.keyboard.type("제목")
        shot(pg, "inline-editing.png")
        pg.keyboard.press("Enter")
        assert mf.evaluate("(s) => document.querySelector(s).innerHTML", H1) == "바로 고친<br>제목", "Enter = 화면은 바로(답을 기다리지 않음)"
        assert '<h1 class="title">하는 일이 무엇인가요?</h1>' in _job(out), "파일은 아직(뒤에서 쓴다)"
        _wait_file(pg, out, lambda s: '<h1 class="title">바로 고친<br>제목</h1>' in s, "글자가 파일에 써지지 않았다")
        pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hs').textContent === '파일에 씀'", timeout=20000)
        pg.wait_for_timeout(1500)                          # 쓴 뒤 다시 불러오기 + 같은 내용 견주기
        assert pg.get_attribute("#mframe", "src") == src0, "같은 내용이면 크게 보기 틀을 다시 싣지 않는다(두 번 깜빡임 없음)"
        assert mf.evaluate("(s) => document.querySelector(s).innerHTML", H1) == "바로 고친<br>제목"
        assert not mf.evaluate("(s) => document.querySelector(s).isContentEditable", H1)
        pg.wait_for_function("window.__swaps.some(d => d.id === 'job' && d.phase === 'done')", timeout=10000)
        done = [d for d in pg.evaluate("window.__swaps") if d["id"] == "job" and d["phase"] == "done"]
        assert done[-1].get("silent") is True, ("크게 보기 뒤 판 카드도 같은 내용 = 알약·겹치기 없이 조용히 바꿈", done)
        assert pg.locator('.card[data-id="job"] .swap-pill').count() == 0
        shot(pg, "inline-after.png")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal", "tools")
def test_drag_grip_moves_an_element_two_places_down_on_screen_and_in_file(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        mf = _modal(pg)
        src0 = pg.get_attribute("#mframe", "src")
        _pick(pg, mf, TILE % 1)
        assert not pg.is_visible('#elbar [data-act="up"]') and not pg.is_visible('#elbar [data-act="down"]'), "↑·↓ 는 막대에서 빠졌다"
        shot(pg, "drag-before.png")
        g = pg.locator("#elbar .eb-grip").bounding_box()
        t3 = _in_modal(pg, mf, TILE % 3)
        pg.mouse.move(g["x"] + g["width"] / 2, g["y"] + g["height"] / 2)
        pg.mouse.down()
        pg.mouse.move(t3["x"] + t3["w"] * 0.8, t3["y"] + t3["h"] / 2, steps=10)
        pg.wait_for_selector("#eldrop:not([hidden])", timeout=3000)
        assert pg.get_attribute("#eldrop", "data-slot") == "3", "셋째 칸 오른쪽 반 = 셋째 뒤"
        shot(pg, "drag-line.png")
        pg.mouse.up()
        assert pg.is_hidden("#eldrop")
        want = ["대학원생·연구원", "어학 시험 준비", "대학생"]
        assert mf.evaluate(TILES_JS)[:3] == want, "놓으면 화면 순서가 바로"
        _wait_file(pg, out, lambda s: s.index("대학원생·연구원") < s.index("어학 시험 준비") < s.index("대학생<") < s.index("개발자·엔지니어"),
                   "파일 순서가 화면과 같지 않다")
        pg.wait_for_timeout(2000)                          # 둘째 쓰기의 다시 불러오기 + 같은 내용 견주기
        assert pg.get_attribute("#mframe", "src") == src0, "중간·마지막 다시 싣기 모두 건너뜀(같은 내용)"
        assert mf.evaluate(TILES_JS)[:3] == want
        pg.wait_for_function("document.querySelector('#elbar') && !document.querySelector('#elbar').hidden", timeout=3000)   # 옮긴 요소가 다시 골라져 있다
        assert "대학생" in mf.evaluate("(p) => { const m = window.__hdRules.find(p); return m ? m.textContent : ''; }", pg.get_attribute("#elbar", "data-path"))
        shot(pg, "drag-after.png")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal", "tools")
def test_refused_apply_reverts_the_optimistic_duplicate_and_says_why(ctx, out):
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    held = []
    try:
        mf = _modal(pg)
        before = _job(out)
        _pick(pg, mf, TILE % 2)
        pg.route("**/api/apply", lambda r: held.append(r))  # 답을 잡아 두었다가 거절로 돌려준다
        shot(pg, "fail-before.png")
        if pg.is_visible('#elbar [data-act="dup"]'):
            pg.click('#elbar [data-act="dup"]')
        else:                                              # 요소 칸보다 넓으면 ⋯ 목록에(polish-1)
            pg.click("#elbar [data-more]"); pg.click('#elpop .ep-act[data-act="dup"]')
        mf.wait_for_function("() => document.querySelectorAll('.tile-grid > button').length === 10", timeout=3000)   # 답을 기다리지 않고 복사본
        for _ in range(50):
            if held:
                break
            pg.wait_for_timeout(100)
        assert held, "도우미에 /api/apply 를 보냈다"
        shot(pg, "fail-pending.png")
        body = json.loads(held[0].request.post_data)
        ids = [e["id"] for e in body["edits"]]
        assert [e["edit"] for e in body["edits"]] == ["duplicate"] and {"id", "screen", "edit", "path"} <= set(body["edits"][0]) <= {"id", "screen", "edit", "op", "to", "path", "value", "index"}, body   # /api/apply 약속 그대로(낙관 표시 opt 는 안 나감)
        held[0].fulfill(status=200, content_type="application/json",
                        body=json.dumps({"applied": [], "failed": [{"id": ids[0], "reason": "시험용 거절: 겹치는 편집"}], "stamp": None, "changed": []}))
        mf.wait_for_function("() => document.querySelectorAll('.tile-grid > button').length === 9", timeout=3000)
        pg.wait_for_function("(document.getElementById('toast') || {}).textContent.indexOf('시험용 거절: 겹치는 편집') >= 0", timeout=3000)
        assert "되돌렸어요" in pg.text_content("#toast")
        assert pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-notes:')).map(k => JSON.parse(localStorage.getItem(k) || '[]').length).reduce((a, b) => a + b, 0)") == 0, \
            "되돌린 편집은 반영 대기로 남지 않는다"
        assert _job(out) == before
        shot(pg, "fail-reverted.png")
    finally:
        pg.unroute("**/api/apply")
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()




@pytest.mark.area("tools")
def test_in_place_edit_shows_one_box_not_the_selection_box_over_it(ctx, out):
    """판에서 요소 [글자] → 그 자리 고치기 중 마우스를 그 글 위에 두어도 캔버스 hover 상자(점선·'글자' 이름표)는 그 카드에 뜨지 않는다 — 화면 안 파란 테두리와 두 칸이 겹쳐 글이 가려졌다(사용자 10-25)."""
    from test_canvas_blocks import _xy, _pick_element, _act
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    try:
        xy = _xy(pg, H1)
        pg.keyboard.press("t")                           # 글자 도구: 판 위 글에 올리면 hover 상자(점선·'글자') → 누르면 그 자리 고치기
        pg.mouse.move(xy[0] - 10, xy[1]); pg.wait_for_timeout(200); pg.mouse.move(*xy); pg.wait_for_timeout(200)
        pg.mouse.click(*xy)
        pg.wait_for_function("() => [...document.querySelectorAll('.card[data-id=job] iframe')].some(f => { try { return f.contentDocument.activeElement && f.contentDocument.activeElement.isContentEditable; } catch (e) { return false; } })", timeout=5000)
        for dx in (-30, 0, 30):                          # 글 위에서 움직임 = hover 다시 그리기 기회
            pg.mouse.move(xy[0] + dx, xy[1]); pg.wait_for_timeout(150)
        shot(pg, "inline-board-one-box.png")
        boxes = pg.evaluate("[...document.querySelectorAll('.card[data-id=\"job\"] .elbox')].filter(b => getComputedStyle(b).display !== 'none' && getComputedStyle(b).visibility !== 'hidden').map(b => b.dataset.label || b.className)")
        assert boxes == [], ("고치는 동안 그 카드에 캔버스 상자가 겹치지 않는다(화면 안 파란 테두리 하나만)", boxes)
    finally:
        srv.shutdown(); srv.server_close()


@pytest.mark.area("helper", "modal", "tools")
def test_remove_hides_the_element_at_once_and_survives_the_swap(ctx, out):
    """49d: 요소 [지우기] = 도우미 답(다시 빌드 수 초)을 기다리지 않고 크게 보기·판 카드에서 바로 사라진다. 답 뒤 크게 보기는 다시 싣지 않고(같은 내용),
    판 카드 교체는 조용히(silent) — 지운 요소는 돌아오지 않는다."""
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    held = []
    gone = "() => ![...document.querySelectorAll('.tile-grid > button')].some(b => b.textContent.indexOf('대학원생') >= 0)"
    try:
        mf = _modal(pg)
        src0 = pg.get_attribute("#mframe", "src")
        pg.evaluate("window.__swaps = []; document.addEventListener('hd-swap', e => window.__swaps.push(e.detail))")
        _pick(pg, mf, TILE % 2)
        assert "대학원생" in mf.text_content(TILE % 2)
        n0 = _job(out).count("대학원생")                 # 타일 글 + 화면 안 다른 자리
        pg.route("**/api/apply", lambda r: held.append(r))  # 다시 빌드가 느린 도우미 — 답을 잡아 둔다
        shot(pg, "remove-before.png")
        if pg.is_visible('#elbar [data-act="remove"]'):
            pg.click('#elbar [data-act="remove"]')
        else:
            pg.click("#elbar [data-more]"); pg.click('#elpop .ep-act[data-act="remove"]')
        mf.wait_for_function(gone, timeout=1000)            # 답을 기다리지 않고
        bf = _frame(pg)
        bf.wait_for_function(gone, timeout=1000)
        for _ in range(50):
            if held:
                break
            pg.wait_for_timeout(100)
        assert held, "도우미에 /api/apply 를 보냈다"
        assert [e["edit"] for e in json.loads(held[0].request.post_data)["edits"]] == ["remove"]
        shot(pg, "remove-pending.png")
        held[0].continue_()
        pg.unroute("**/api/apply")
        _wait_file(pg, out, lambda s: s.count("대학원생") == n0 - 1, "파일에서 지워지지 않았다")
        pg.wait_for_function("window.__swaps.some(d => d.id === 'job' && d.phase === 'done')", timeout=15000)
        pg.wait_for_timeout(1500)                          # 쓴 뒤 다시 불러오기 + 같은 내용 견주기
        done = [d for d in pg.evaluate("window.__swaps") if d["id"] == "job" and d["phase"] == "done"]
        assert done[-1].get("silent") is True, ("판 카드 = 이미 보이는 내용이라 조용히 바꿈", done)
        assert pg.get_attribute("#mframe", "src") == src0, "크게 보기 틀은 다시 싣지 않는다(두 번 깜빡임 없음)"
        assert mf.evaluate(gone) and _frame(pg).evaluate(gone), "지운 요소가 돌아오지 않는다"
        assert pg.locator('.card[data-id="job"] .swap-pill').count() == 0
        shot(pg, "remove-after.png")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
