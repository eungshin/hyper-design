"""49c 바로 반영 편집 — 브라우저(도우미 있음, 크게 보기).

- 글자(T): 고른 요소 하나만 그 자리에서 contenteditable(글꼴·크기 그대로, 글 칸 #tedit 없음) · Esc = 원래 글 · Shift+Enter = 줄바꿈 · Enter = 저장 → 화면은 바로, 파일은 뒤에서.
  쓴 뒤 크게 보기 틀은 다시 싣지 않는다(같은 내용 — 두 번 깜빡임 없음).
- 끌어서 순서 바꾸기: 막대 손잡이 [⠿] 를 끌면 끼울 선 #eldrop · 놓으면 화면 순서가 바로, 파일은 도우미 move op:to 한 번(기록 한 줄, 되돌리기 한 번 — 51-5).
- Alt 끌기(51-5): 끄는 중 '+' 배지 · 놓으면 복사본이 그 자리에(원본은 제자리), 파일도 같게.
- 도우미가 거절(applied:[])하면 먼저 보인 복제를 되돌리고 까닭을 알린다.
규칙은 test_canvas_unit_instant.py(unit). 스크린샷 = HD_SHOTS_49C(기본 %TEMP%/claude/t49c).
"""
import json, os, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import browser, ctx, swap_done, swap_mark  # noqa: F401
from test_canvas_text_remove import _frame, _open, _serve, out  # noqa: F401

SHOTS = Path(os.environ.get("HD_SHOTS_49C", Path(tempfile.gettempdir()) / "claude" / "t49c"))
H1 = "h1.title"
TILE = ".tile-grid > button:nth-of-type(%d)"
TILES_JS = "() => [...document.querySelectorAll('.tile-grid > button')].map(b => b.textContent.replace(/\\d+$/, '').trim())"


SHOTS51 = Path(os.environ.get("HD_SHOTS_51_5", Path(tempfile.gettempdir()) / "claude" / "t51-5"))


def shot51(pg, name):
    SHOTS51.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=str(SHOTS51 / name))


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
        m = swap_mark(pg)
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
        done = swap_done(pg, "job", m)
        assert done[-1].get("silent") is True, ("크게 보기 뒤 판 카드도 같은 내용 = 알약·겹치기 없이 조용히 바꿈", done)
        assert pg.locator('.card[data-id="job"] .swap-pill').count() == 0
        shot(pg, "inline-after.png")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


def _hist(o):
    d = o / ".hd-history"
    return len([x for x in d.iterdir() if x.is_dir()]) if d.is_dir() else 0


def _applies(pg):
    calls = []
    pg.on("request", lambda r: calls.append(json.loads(r.post_data or "{}")) if r.url.endswith("/api/apply") and r.method == "POST" else None)
    return calls


def _grip_drag(pg, mf, to_sel, frac, alt=False, mid=None):
    """손잡이를 눌러 to_sel 칸의 가로 frac 자리로 끌어 놓기 — alt = 놓을 때까지 Alt · mid(pg) = 놓기 직전에 부를 것(스크린샷)."""
    g = pg.locator("#elbar .eb-grip").bounding_box()
    t = _in_modal(pg, mf, to_sel)
    pg.mouse.move(g["x"] + g["width"] / 2, g["y"] + g["height"] / 2)
    pg.mouse.down()
    if alt:
        pg.keyboard.down("Alt")
    pg.mouse.move(t["x"] + t["w"] * frac, t["y"] + t["h"] / 2, steps=10)
    pg.wait_for_selector("#eldrop:not([hidden])", timeout=3000)
    if mid:
        mid(pg)
    pg.mouse.up()
    if alt:
        pg.keyboard.up("Alt")


@pytest.mark.area("helper", "modal", "tools")
def test_drag_two_places_is_one_write_one_history_row_and_one_undo(ctx, out):
    """51-5(F20): 끌어 옮기기 한 번 = 도우미 쓰기 하나(move op:to) = 기록 한 줄 — 되돌리기 한 번에 원래 순서."""
    before = _job(out)
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    calls = _applies(pg)
    try:
        mf = _modal(pg)
        src0 = pg.get_attribute("#mframe", "src")
        _pick(pg, mf, TILE % 1)
        assert not pg.is_visible('#elbar [data-act="up"]') and not pg.is_visible('#elbar [data-act="down"]'), "↑·↓ 는 막대에서 빠졌다"
        h0 = _hist(out)
        def mid(p):
            assert p.get_attribute("#eldrop", "data-slot") == "3", "셋째 칸 오른쪽 반 = 셋째 뒤"
            assert p.is_hidden("#eldrop-copy"), "Alt 없이 = 복제 표시 없음"
            shot(p, "drag-line.png")
        _grip_drag(pg, mf, TILE % 3, 0.8, mid=mid)
        assert pg.is_hidden("#eldrop")
        want = ["대학원생·연구원", "어학 시험 준비", "대학생"]
        assert mf.evaluate(TILES_JS)[:3] == want, "놓으면 화면 순서가 바로"
        _wait_file(pg, out, lambda s: s.index("대학원생·연구원") < s.index("어학 시험 준비") < s.index("대학생<") < s.index("개발자·엔지니어"),
                   "파일 순서가 화면과 같지 않다")
        pg.wait_for_function("document.querySelector('#hlist li.now .hs') && document.querySelector('#hlist li.now .hs').textContent === '파일에 씀'", timeout=20000)
        pg.wait_for_timeout(1500)                          # 쓴 뒤 다시 불러오기 + 같은 내용 견주기
        assert [[(e["edit"], e.get("op"), e.get("to")) for e in c["edits"]] for c in calls] == [[("move", "to", 2)]], ("/api/apply 한 번, move op:to 하나", calls)
        assert _hist(out) == h0 + 1, "기록(.hd-history) 한 줄"
        assert pg.evaluate("[...document.querySelectorAll('#hlist li')].filter(l => (l.textContent || '').indexOf('요소 옮기기') >= 0).length") == 1, "기록 목록에 한 줄"
        assert pg.get_attribute("#mframe", "src") == src0, "다시 싣지 않는다(같은 내용)"
        assert mf.evaluate(TILES_JS)[:3] == want
        shot(pg, "drag-after.png")
        pg.keyboard.press("Control+z")
        _wait_file(pg, out, lambda s: s == before, "되돌리기 한 번 = 원래 순서")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal", "tools")
def test_alt_drag_puts_a_copy_at_the_slot_and_keeps_the_original(ctx, out):
    """51-5(F21): 놓을 때 Alt = 복제해 놓기 — 끄는 중 '+' 배지·copy 커서, 놓으면 복사본이 그 자리에(원본은 제자리), 파일도 같은 순서.
    도우미 쓰기 = duplicate → 복사본 move op:to(한 묶음으로 못 보냄 — 기록 두 줄)."""
    srv = _serve(out)
    pg, errors = _open(ctx, srv.url)
    calls = _applies(pg)
    try:
        mf = _modal(pg)
        _pick(pg, mf, TILE % 1)
        n0 = mf.evaluate("() => document.querySelectorAll('.tile-grid > button').length")

        def mid(p):
            p.wait_for_selector("#eldrop-copy:not([hidden])", timeout=2000)
            assert p.evaluate("document.body.classList.contains('hd-drag-copy')"), "Alt 를 누른 동안 복제 표시"
            assert p.evaluate("getComputedStyle(document.body).cursor") == "copy"
            assert p.get_attribute("#eldrop", "data-slot") == "3"
            shot51(p, "alt-drag-mid.png")
        _grip_drag(pg, mf, TILE % 3, 0.8, alt=True, mid=mid)
        assert pg.is_hidden("#eldrop-copy") and not pg.evaluate("document.body.classList.contains('hd-drag-copy')")
        tiles = mf.evaluate(TILES_JS)
        assert len(tiles) == n0 + 1 and tiles[:4] == ["대학생", "대학원생·연구원", "어학 시험 준비", "대학생"], ("복사본이 셋째 뒤에 바로, 원본은 제자리", tiles)
        _wait_file(pg, out, lambda s: s.count("대학생<") == 2 and s.index("대학생<") < s.index("대학원생·연구원") < s.index("어학 시험 준비") < s.rindex("대학생<") < s.index("개발자·엔지니어"),
                   "파일에 복사본이 그 자리에 없다")
        for _ in range(100):
            if len(calls) == 2:
                break
            pg.wait_for_timeout(100)
        assert [[e["edit"] for e in c["edits"]] for c in calls] == [["duplicate"], ["move"]], calls
        assert calls[1]["edits"][0]["op"] == "to" and calls[1]["edits"][0]["to"] == 3, calls[1]
        pg.wait_for_timeout(1500)
        assert mf.evaluate(TILES_JS)[:4] == ["대학생", "대학원생·연구원", "어학 시험 준비", "대학생"]
        shot51(pg, "alt-drag-after.png")
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
        pg.click('#elbar [data-act="more"]'); pg.click('#cmenu:not([hidden]) button[data-act="dup"]')   # R17: 막대 ⋯ = 요소 메뉴
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
        m = swap_mark(pg)
        _pick(pg, mf, TILE % 2)
        assert "대학원생" in mf.text_content(TILE % 2)
        n0 = _job(out).count("대학원생")                 # 타일 글 + 화면 안 다른 자리
        pg.route("**/api/apply", lambda r: held.append(r))  # 다시 빌드가 느린 도우미 — 답을 잡아 둔다
        shot(pg, "remove-before.png")
        pg.click('#elbar [data-act="more"]'); pg.click('#cmenu:not([hidden]) button[data-act="remove"]')   # R17: 막대 ⋯ = 요소 메뉴
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
        swap_done(pg, "job", m, timeout=15000)
        pg.wait_for_timeout(1500)                          # 크게 보기 틀의 같은 내용 견주기(판 카드 교체와 따로 끝난다)
        done = swap_done(pg, "job", m)
        assert done[-1].get("silent") is True, ("판 카드 = 이미 보이는 내용이라 조용히 바꿈", done)
        assert pg.get_attribute("#mframe", "src") == src0, "크게 보기 틀은 다시 싣지 않는다(두 번 깜빡임 없음)"
        assert mf.evaluate(gone) and _frame(pg).evaluate(gone), "지운 요소가 돌아오지 않는다"
        assert pg.locator('.card[data-id="job"] .swap-pill').count() == 0
        shot(pg, "remove-after.png")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal", "tools")
def test_async_apply_whose_build_fails_reverts_the_optimistic_change(ctx, out):
    """47-4b — 바로 쓰기는 async apply: 도우미는 쓰고 바로 답하고(빌드는 뒤에서), 그 빌드가 깨지면 build.failed{reverted} 이벤트로
    먼저 보인 복제를 거두고 화면을 파일대로 되돌리며 까닭을 알린다."""
    import subprocess as sp
    srv = _serve(out)
    calls = []

    def broken(o):                                       # 뒤 빌드 한 번 실패(되돌린 뒤 다시 빌드는 성공)
        calls.append(1)
        return sp.CompletedProcess([], 1, "", "시험용 빌드 실패") if len(calls) == 1 else sp.CompletedProcess([], 0, "", "")
    pg, errors = _open(ctx, srv.url)
    bodies = []
    pg.on("request", lambda r: bodies.append(r.post_data) if r.url.endswith("/api/apply") else None)
    try:
        pg.wait_for_selector('#livechip[data-mode="live"]', state="attached", timeout=8000)   # 정상 상태 칩은 숨김(R27 F11)
        mf = _modal(pg)
        before = _job(out)
        _pick(pg, mf, TILE % 2)
        srv.session.builder._check = broken   # 쓰기 확인(figma-lite 5: 데이터만)
        pg.click('#elbar [data-act="more"]'); pg.click('#cmenu:not([hidden]) button[data-act="dup"]')   # R17: 막대 ⋯ = 요소 메뉴
        mf.wait_for_function("() => document.querySelectorAll('.tile-grid > button').length === 10", timeout=3000)   # 답을 기다리지 않고 복사본
        pg.wait_for_function("(document.getElementById('toast') || {}).textContent.indexOf('시험용 빌드 실패') >= 0", timeout=10000)
        assert "되돌렸어요" in pg.text_content("#toast")
        assert json.loads(bodies[0])["async"] is True, "캔버스 쓰기는 async"
        _wait_file(pg, out, lambda s: s == before, "도우미가 파일을 되돌렸다")
        for _ in range(60):                                # 크게 보기 틀도 파일대로(9개)
            fr = next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")
            try:
                if fr.evaluate("() => document.querySelectorAll('.tile-grid > button').length") == 9:
                    break
            except Exception:                              # 다시 싣는 중
                pass
            pg.wait_for_timeout(100)
        else:
            raise AssertionError("되돌린 화면이 보이지 않는다")
        assert len(calls) == 2
        SHOTS.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(Path(tempfile.gettempdir()) / "claude" / "t47-4b" / "async-build-failed.png"))
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("helper", "modal", "tools")
def test_drag_whose_async_build_fails_puts_the_order_back(ctx, out):
    """51-5 + 47-4b: 끌어 옮기기 쓰기(move op:to)의 뒤 빌드가 깨지면 build.failed 로 먼저 보인 순서를 거두고 까닭을 알린다."""
    import subprocess as sp
    srv = _serve(out)
    calls = []

    def broken(o):
        calls.append(1)
        return sp.CompletedProcess([], 1, "", "시험용 빌드 실패") if len(calls) == 1 else sp.CompletedProcess([], 0, "", "")
    pg, errors = _open(ctx, srv.url)
    try:
        pg.wait_for_selector('#livechip[data-mode="live"]', state="attached", timeout=8000)   # 정상 상태 칩은 숨김(R27 F11)
        mf = _modal(pg)
        before = _job(out)
        _pick(pg, mf, TILE % 1)
        srv.session.builder._check = broken   # 쓰기 확인(figma-lite 5: 데이터만)
        _grip_drag(pg, mf, TILE % 3, 0.8)
        assert mf.evaluate(TILES_JS)[:3] == ["대학원생·연구원", "어학 시험 준비", "대학생"], "놓으면 화면은 바로"
        pg.wait_for_function("(document.getElementById('toast') || {}).textContent.indexOf('시험용 빌드 실패') >= 0", timeout=10000)
        assert "되돌렸어요" in pg.text_content("#toast")
        _wait_file(pg, out, lambda s: s == before, "도우미가 파일을 되돌렸다")
        for _ in range(60):
            fr = next(f for f in pg.frames if f.parent_frame and f.frame_element().get_attribute("id") == "mframe")
            try:
                if fr.evaluate(TILES_JS)[:3] == ["대학생", "대학원생·연구원", "어학 시험 준비"]:
                    break
            except Exception:                              # 다시 싣는 중
                pass
            pg.wait_for_timeout(100)
        else:
            raise AssertionError("되돌린 순서가 보이지 않는다")
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
