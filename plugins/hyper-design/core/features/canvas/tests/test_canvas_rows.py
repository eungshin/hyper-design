"""판 줄 맞추기(51-1, FINDINGS D) — 줄의 화면을 다 지우면 줄과 제목이 새로고침 없이 바로 없어지고, 되돌리면 제자리로 돌아온다. 레이어 패널도 같은 줄."""
import os, pathlib, shutil, subprocess, sys, tempfile, threading

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")                   # 눈으로 볼 때만: 스크린숏 폴더

ROWS = "() => [...document.querySelectorAll('#rows .flow .glabel')].map(g => g.textContent)"
LAYER_ROWS = "() => [...document.querySelectorAll('#pLayers .ly-r[data-kind=\"row\"] .ly-name')].map(n => n.textContent)"


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-rows-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.area("tools", "layers")
def test_emptied_row_and_heading_go_at_once_and_undo_brings_them_back(ctx, out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("window.__hdStay = 1")
        from test_canvas_edit import fit_view
        fit_view(pg)
        first = pg.evaluate(ROWS)
        assert first[0] == "로그인" and len(first) == 4, first
        assert pg.evaluate(LAYER_ROWS) == first
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-1-before.png"))
        pick = lambda sid: pg.evaluate("(id) => { const r = document.querySelector('.card[data-id=\"' + id + '\"] .cover').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }", sid)
        pg.mouse.click(*pick("login")); pg.wait_for_timeout(150)
        pg.keyboard.down("Shift"); pg.mouse.click(*pick("login--done")); pg.keyboard.up("Shift"); pg.wait_for_timeout(150)
        pg.keyboard.press("Delete")
        pg.wait_for_function("!document.querySelector('.card[data-id=\"login\"]') && !document.querySelector('.card[data-id=\"login--done\"]')", timeout=20000)
        pg.wait_for_timeout(100)
        assert pg.evaluate(ROWS) == first[1:], "화면을 다 지운 줄 = 제목째 바로 없어진다"
        assert pg.evaluate(LAYER_ROWS) == first[1:], "레이어 패널도 같은 줄"
        if SHOTS:
            fit_view(pg)
            pg.screenshot(path=os.path.join(SHOTS, "51-1-after.png"))
        pg.click("#undo")
        pg.wait_for_function("!!document.querySelector('.card[data-id=\"login\"]') && !!document.querySelector('.card[data-id=\"login--done\"]')", timeout=20000)
        pg.wait_for_timeout(100)
        assert pg.evaluate(ROWS) == first, "되돌리면 줄이 제자리로"
        assert pg.evaluate("() => [...document.querySelectorAll('#rows .flow')][0].querySelectorAll('.card').length") == 2
        assert pg.evaluate(LAYER_ROWS) == first
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


# ---------------------------------------------------------------- 줄 = 섹션(51-4, Figma F16·F17)
SET, TRY = "설정 — 하는 일·언어·쓰는 방향", "체험 — 실제 키로 해 봐야 다음"
PICKED = "() => [...document.querySelectorAll('#rows .card.picked')].map(c => c.dataset.id)"
FLOW_IDS = "() => [...document.querySelectorAll('#rows .flow')].map(f => [...f.querySelectorAll('.card')].map(c => c.dataset.id))"


def _open(ctx, out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("window.__hdStay = 1")
    from test_canvas_edit import fit_view
    fit_view(pg)
    return srv, pg, errors


def _head(pg, name):
    return pg.locator("#rows .flow > .glabel", has_text=name).first


def _sj(out):
    import json
    return json.loads((out / "screens.json").read_text(encoding="utf-8"))


def _wait(fn, timeout=20.0):
    import time
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.1)
    return False


@pytest.mark.area("tools", "layers")
def test_heading_click_picks_row_and_double_click_renames_in_place_with_one_undo(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        before = (out / "screens.json").read_bytes()
        _head(pg, SET).click()
        pg.wait_for_timeout(150)
        assert sorted(pg.evaluate(PICKED)) == ["job", "language", "usage"], "제목 누르기 = 그 줄 카드 모두 고르기"
        assert pg.is_visible("#selbar"), "여러 장 고르기 막대"
        if SHOTS:
            _head(pg, "로그인").hover(); pg.wait_for_timeout(100)   # 고른 줄 카드는 설명을 펼쳐 아래 줄 제목을 덮는다 — 위 줄에 올린다
            pg.screenshot(path=os.path.join(SHOTS, "51-4-hover-and-picked.png"))
        # Esc = 그대로(쓰지 않음)
        _head(pg, SET).dblclick()
        pg.wait_for_function("document.activeElement && document.activeElement.classList.contains('glabel')")
        pg.keyboard.press("Control+A"); pg.keyboard.type("아무거나")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(200)
        assert pg.evaluate(ROWS)[1] == SET and (out / "screens.json").read_bytes() == before, "Esc = 취소"
        # Enter = 저장
        _head(pg, SET).dblclick()
        pg.wait_for_function("document.activeElement && document.activeElement.classList.contains('glabel')")
        pg.keyboard.press("Control+A"); pg.keyboard.type("설정")
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-4-rename-in-place.png"))
        pg.keyboard.press("Enter")
        assert _wait(lambda: _sj(out)["groups"][1] == "설정"), _sj(out)["groups"]
        d = _sj(out)
        assert [s["group"] for s in d["screens"] if s["id"] in ("job", "language", "usage")] == ["설정"] * 3, "줄 화면마다 group 도 같이"
        pg.wait_for_function("[...document.querySelectorAll('#rows .flow .glabel')][1].textContent === '설정'")
        assert pg.evaluate(ROWS)[1] == "설정" and pg.evaluate(LAYER_ROWS)[1] == "설정", "판과 레이어 패널"
        pg.click("#undo")
        assert _wait(lambda: (out / "screens.json").read_bytes() == before), "되돌리기 한 번 = 이름·화면 group 모두 그대로"
        pg.wait_for_function("[...document.querySelectorAll('#rows .flow .glabel')][1].textContent === %r" % SET)
        assert pg.evaluate(LAYER_ROWS)[1] == SET
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "layers")
def test_ctrl_backspace_on_heading_merges_row_into_the_row_above_with_one_undo(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        before = (out / "screens.json").read_bytes()
        first = pg.evaluate(ROWS)
        ids0 = pg.evaluate(FLOW_IDS)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "51-4-dissolve-before.png"))
        _head(pg, TRY).click()
        pg.wait_for_timeout(150)
        pg.keyboard.press("Control+Backspace")
        assert _wait(lambda: TRY not in _sj(out)["groups"]), "줄만 걷기 = groups 에서 이름만 뺀다"
        d = _sj(out)
        assert len(d["screens"]) == 12, "화면은 하나도 지우지 않는다"
        assert [s["id"] for s in d["screens"] if s["group"] == SET] == ids0[1] + ids0[2], "위 줄 화면 뒤에"
        pg.wait_for_function("document.querySelectorAll('#rows .flow').length === 3")
        assert pg.evaluate(ROWS) == [first[0], first[1], first[3]]
        assert pg.evaluate(FLOW_IDS)[1] == ids0[1] + ids0[2], "판에서도 위 줄 끝에 붙는다"
        assert pg.evaluate(LAYER_ROWS) == [first[0], first[1], first[3]]
        if SHOTS:
            fit_after = __import__("test_canvas_edit").fit_view; fit_after(pg)
            pg.screenshot(path=os.path.join(SHOTS, "51-4-dissolve-after.png"))
        pg.click("#undo")
        assert _wait(lambda: (out / "screens.json").read_bytes() == before), "되돌리기 한 번"
        pg.wait_for_function("document.querySelectorAll('#rows .flow').length === 4")
        assert pg.evaluate(ROWS) == first and pg.evaluate(FLOW_IDS) == ids0, "줄과 카드가 제자리로"
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


# ---------------------------------------------------------------- S1c 셸 후속(51-4 알려진 한계 · 고른 줄 설명이 아래 줄 제목을 덮음)
CARD_LEFT = "(id) => { const c = document.querySelector('.card[data-id=\"' + id + '\"]'); return c ? [c.style.left, c.style.top, c.classList.contains('moved')] : null; }"


def _drag_card(pg, sid, dx, dy):
    pg.keyboard.press("v")
    b = pg.locator(f'.card[data-id="{sid}"] .cover').bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    pg.mouse.move(x, y); pg.mouse.down()
    for i in range(1, 6):
        pg.mouse.move(x + dx * i / 5, y + dy * i / 5)
    pg.mouse.up()
    pg.wait_for_timeout(200)


@pytest.mark.area("tools", "layers")
def test_rename_row_keeps_moved_card_position_after_reload(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        _drag_card(pg, "job", 60, 40)
        moved = pg.evaluate(CARD_LEFT, "job")
        assert moved[2] and moved[0], f"카드를 옮겼다 {moved}"
        pg.keyboard.press("Escape")
        _head(pg, SET).dblclick()
        pg.wait_for_function("document.activeElement && document.activeElement.classList.contains('glabel')")
        pg.keyboard.press("Control+A"); pg.keyboard.type("설정")
        pg.keyboard.press("Enter")
        assert _wait(lambda: _sj(out)["groups"][1] == "설정"), _sj(out)["groups"]
        pg.wait_for_timeout(1500)                          # 상태 저장(.hd-canvas.json)
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_function("[...document.querySelectorAll('#rows .flow .glabel')][1].textContent === '설정'")
        assert pg.evaluate(CARD_LEFT, "job") == moved, "줄 이름을 바꿔도 옮긴 카드 자리는 새로고침 뒤 그대로"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "layers")
def test_dissolve_row_keeps_moved_card_position_after_reload(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        sid = pg.evaluate("(n) => [...document.querySelectorAll('#rows .flow')].find(f => f.querySelector('.glabel').textContent === n).querySelector('.card').dataset.id", TRY)
        _drag_card(pg, sid, 50, 30)
        moved = pg.evaluate(CARD_LEFT, sid)
        assert moved[2], moved
        pg.keyboard.press("Escape")
        _head(pg, TRY).click()
        pg.wait_for_timeout(150)
        pg.keyboard.press("Control+Backspace")
        assert _wait(lambda: TRY not in _sj(out)["groups"])
        pg.wait_for_timeout(1500)
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.wait_for_function("document.querySelectorAll('#rows .flow').length === 3")
        assert pg.evaluate(CARD_LEFT, sid) == moved, "줄만 걷어도 옮긴 카드 자리는 새로고침 뒤 그대로"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "layers")
def test_picked_row_descriptions_do_not_cover_next_row_heading(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        _head(pg, SET).click()
        pg.wait_for_timeout(200)
        covered = pg.evaluate("""(n) => { const g = [...document.querySelectorAll('#rows .flow > .glabel')].find(x => x.textContent === n);
            const r = g.getBoundingClientRect(), out = [];
            for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) { const e = document.elementFromPoint(r.left + r.width * fx, r.top + r.height / 2);
              if (!e || !g.contains(e)) out.push(e ? e.className : null); }
            return out; }""", TRY)
        assert covered == [], f"고른 줄 카드 설명이 아래 줄 제목을 덮는다: {covered}"
        _head(pg, TRY).hover()
        pg.wait_for_timeout(100)
        bg = pg.evaluate("(n) => getComputedStyle([...document.querySelectorAll('#rows .flow > .glabel')].find(x => x.textContent === n)).backgroundColor", TRY)
        assert bg not in ("rgba(0, 0, 0, 0)", "transparent"), "아래 줄 제목에 올리면 hover 바탕"
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "s1c-row-heading-over.png"))
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
