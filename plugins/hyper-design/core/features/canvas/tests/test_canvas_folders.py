"""R31 폴더 = 판의 화면 줄(섹션) 관리 — 판 제목은 폴더로 읽히고(아이콘), 두 번 눌러 이름 바꾸기 · 폴더만 풀기(Ctrl+Shift+G) · 제목을 끌면 폴더째 옮기기,
레이어 패널에서 이름 두 번 누르기 = 이름 바꾸기(고르기로 도크가 움직여도) · 화면 줄을 다른 폴더에 끌어 놓으면 그 폴더로(새로고침 뒤에도)."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, threading, time

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")                   # 눈으로 볼 때만: 스크린숏 폴더
SET, TRY = "설정 — 하는 일·언어·쓰는 방향", "체험 — 실제 키로 해 봐야 다음"
ROWS = "() => [...document.querySelectorAll('#rows .flow > .glabel')].map(g => g.textContent)"
FLOW_IDS = "() => [...document.querySelectorAll('#rows .flow')].map(f => [...f.querySelectorAll('.card')].map(c => c.dataset.id))"
BOX = "(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y)]; }"
TBOX = """(n) => { const r = [...document.querySelectorAll('#rows .flow > .glabel')].find(g => g.textContent === n).getBoundingClientRect();
  return [Math.round(r.x), Math.round(r.y)]; }"""


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-folders-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def _open(ctx, out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.set_viewport_size({"width": 1440, "height": 1000})
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("window.__hdStay = 1")
    from test_canvas_edit import fit_view
    fit_view(pg)
    return srv, pg, errors


def _sj(out):
    return json.loads((out / "screens.json").read_text(encoding="utf-8"))


def _wait(fn, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if fn():
                return True
        except (PermissionError, json.JSONDecodeError):  # Windows: 서버가 screens.json 을 바꿔 끼우는 그 순간
            pass
        time.sleep(0.1)
    return False


def _head(pg, name):
    return pg.locator("#rows .flow > .glabel", has_text=name).first


def _layer_head(pg, name):
    return pg.locator('#lyTree [data-kind="row"]', has=pg.locator(".ly-name", has_text=name)).first


@pytest.mark.area("tools", "layers")
def test_board_folder_title_reads_as_folder_renames_ungroups_with_one_undo_and_drags_the_folder(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        before = (out / "screens.json").read_bytes()
        icon = pg.evaluate("""(n) => { const g = [...document.querySelectorAll('#rows .flow > .glabel')].find(x => x.textContent === n);
          const s = getComputedStyle(g, '::before'); return {w: s.width, mask: (s.maskImage || s.webkitMaskImage || '').slice(0, 20), weight: getComputedStyle(g).fontWeight}; }""", SET)
        assert icon["w"] not in ("auto", "0px") and icon["mask"].startswith("url("), f"제목 앞 폴더 아이콘: {icon}"
        assert int(icon["weight"]) <= 500, "판 글보다 조용한 굵기"
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "after-board-title.png"))
        # 두 번 누르기 = 그 자리 이름 바꾸기, Enter 저장
        _head(pg, SET).dblclick()
        pg.wait_for_function("document.activeElement && document.activeElement.classList.contains('glabel')")
        pg.keyboard.press("Control+A"); pg.keyboard.type("설정")
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "after-board-rename.png"))
        pg.keyboard.press("Enter")
        assert _wait(lambda: _sj(out)["groups"][1] == "설정"), "이름이 파일에"
        renamed = (out / "screens.json").read_bytes()
        # 오른쪽 메뉴: 폴더만 풀기 · 폴더 지우기 — 다른 뜻이 글에 드러난다
        _head(pg, "설정").click(button="right")
        labels = pg.evaluate("[...document.querySelectorAll('.hd-rmenu button span')].map(s => s.textContent)")
        assert any(l.startswith("폴더만 풀기") for l in labels) and any(l.startswith("폴더 지우기") and "화면" in l for l in labels), labels
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "after-board-menu.png"))
        pg.keyboard.press("Escape")
        # Ctrl+Shift+G = 폴더만 풀기(Figma Ungroup) — 화면은 남고 위 폴더로, 골라진 채
        ids0 = pg.evaluate(FLOW_IDS)
        _head(pg, TRY).click()
        pg.wait_for_timeout(150)
        pg.keyboard.press("Control+Shift+G")
        assert _wait(lambda: TRY not in _sj(out)["groups"]), "groups 에서 이름만 뺀다"
        assert len(_sj(out)["screens"]) == 12, "화면은 그대로"
        pg.wait_for_function("document.querySelectorAll('#rows .flow').length === 3")
        assert sorted(pg.evaluate("[...document.querySelectorAll('#rows .card.picked')].map(c => c.dataset.id)")) == sorted(ids0[2]), "푼 화면이 골라진 채"
        pg.click("#undo")
        assert _wait(lambda: (out / "screens.json").read_bytes() == renamed), "되돌리기 한 번"
        pg.wait_for_function("document.querySelectorAll('#rows .flow').length === 4")
        assert pg.evaluate(FLOW_IDS) == ids0
        # 제목을 끌면 폴더째(제목 + 카드) 옮긴다 — 다른 폴더는 그대로, 되돌리기 한 번
        pg.keyboard.press("Escape")
        t0, c0, o0 = pg.evaluate(TBOX, "설정"), pg.evaluate(BOX, '.card[data-id="job"]'), pg.evaluate(BOX, '.card[data-id="login"]')
        b = _head(pg, "설정").bounding_box()
        x, y = b["x"] + 8, b["y"] + b["height"] / 2
        pg.mouse.move(x, y); pg.mouse.down()
        for i in range(1, 6):
            pg.mouse.move(x + 16 * i, y + 8 * i)
        pg.mouse.up()
        pg.wait_for_timeout(250)
        t1, c1, o1 = pg.evaluate(TBOX, "설정"), pg.evaluate(BOX, '.card[data-id="job"]'), pg.evaluate(BOX, '.card[data-id="login"]')
        assert abs((c1[0] - c0[0]) - 80) <= 2 and abs((c1[1] - c0[1]) - 40) <= 2, ("카드가 끈 만큼", c0, c1)
        assert abs((t1[0] - t0[0]) - 80) <= 2 and abs((t1[1] - t0[1]) - 40) <= 2, ("제목도 같이", t0, t1)
        assert o1 == o0, "다른 폴더는 그대로(판을 끌지 않음)"
        pg.click("#undo")
        pg.wait_for_timeout(250)
        assert pg.evaluate(BOX, '.card[data-id="job"]') == c0 and pg.evaluate(TBOX, "설정") == t0, "되돌리기 한 번 = 제자리"
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
        assert before != renamed
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("layers", "tools")
def test_layers_folder_double_click_renames_and_dragging_a_screen_into_another_folder_survives_reload(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        pg.click('#dock .dk-tab[data-p="layers"]')
        pg.wait_for_selector('#lyTree [data-kind="row"]')
        name = _layer_head(pg, SET).locator(".ly-name")
        # 이름 두 번 누르기 = 이름 바꾸기 — 첫 누르기의 고르기로 도크가 움직여도 입력창이 열린다
        name.dblclick()
        pg.wait_for_selector("#lyTree input.ly-rename", timeout=3000)
        pg.fill("#lyTree input.ly-rename", "설정")
        pg.keyboard.press("Enter")
        assert _wait(lambda: _sj(out)["groups"][1] == "설정"), _sj(out)["groups"]
        pg.wait_for_function("[...document.querySelectorAll('#rows .flow > .glabel')][1].textContent === '설정'")
        assert (_layer_head(pg, TRY).locator(".ly-name").get_attribute("title") or "").startswith(TRY), "폴더 줄에 올리면 이름 전체"
        # 화면 줄 → 다른 폴더(첫 폴더 '로그인') 머리 줄에 끌어 놓기 = 그 폴더로(screens.json · 판)
        pg.evaluate("""([c, n]) => { const dt = new DataTransfer(), s = document.querySelector('#lyTree [data-ly="' + c + '"]'),
            t = [...document.querySelectorAll('#lyTree [data-kind="row"]')].find(r => r.querySelector('.ly-name').textContent === n);
          s.dispatchEvent(new DragEvent('dragstart', {bubbles: true, dataTransfer: dt}));
          t.dispatchEvent(new DragEvent('dragover', {bubbles: true, cancelable: true, dataTransfer: dt}));
          t.dispatchEvent(new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: dt})); }""", ["job", "로그인"])
        assert _wait(lambda: [s["group"] for s in _sj(out)["screens"] if s["id"] == "job"] == ["로그인"]), "파일에 폴더가 바뀜"
        pg.wait_for_function("!!document.querySelector('#rows .flow .card[data-id=\"job\"]') && document.querySelector('#rows .flow').contains(document.querySelector('#rows .card[data-id=\"job\"]'))")
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "after-layers-drag.png"))
        pg.wait_for_timeout(1200)
        pg.reload()
        pg.wait_for_function("window.__hdReady !== undefined")
        assert pg.evaluate(FLOW_IDS)[0][-1] == "job", "새로고침 뒤에도 첫 폴더 끝"
        pg.click('#dock .dk-tab[data-p="layers"]')
        kids = pg.evaluate("""() => { const out = []; let cur = null; document.querySelectorAll('#lyTree [data-ly]').forEach(r => {
            if (r.dataset.kind === 'row') cur = r.querySelector('.ly-name').textContent; else if (r.dataset.kind === 'screen') out.push([cur, r.dataset.ly]); }); return out; }""")
        assert ["로그인", "job"] in kids, kids
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


LAYOUT = """(head) => { const rs = [...document.querySelectorAll('#lyTree .ly-r')], i = rs.findIndex(r => r.dataset.kind === 'row' && r.querySelector('.ly-name').textContent === head);
  const h = rs[i], kids = [];
  for (let k = i + 1; k < rs.length && (rs[k].dataset.kind === 'screen' || rs[k].dataset.kind === 'text') && rs[k].dataset.p === h.dataset.ly; k++) kids.push(rs[k]);
  const x = (r, s) => { const e = r.querySelector(s); return e ? Math.round(e.getBoundingClientRect().left) : null; };
  return {headEye: x(h, '.ly-eye'), headIcon: x(h, '.ly-ficon'), headBg: getComputedStyle(h).backgroundColor,
          kids: kids.map(r => ({eye: x(r, '.ly-eye'), name: x(r, '.ly-name'), guide: !!r.querySelector('.ly-ind'), last: r.classList.contains('last'),
                                bg: getComputedStyle(r).backgroundColor, hov: r.classList.contains('grp-hov')}))}; }"""


@pytest.mark.area("layers")
def test_layers_folder_children_read_as_inside_the_folder(ctx, out):
    """레이어 패널 폴더(사용자 10-29, Photoshop·Sketch 참고 목업): 눈 칸은 왼쪽 한 줄(들여써도 일렬) · 폴더 줄은 바탕색 ·
    자식은 폴더 아이콘보다 안쪽 + 세로 안내선(마지막 자식에서 끝) · 폴더 줄에 올리면 그 묶음이 함께 옅게."""
    srv, pg, errors = _open(ctx, out)
    try:
        pg.click('#dock .dk-tab[data-p="layers"]')
        pg.wait_for_selector('#lyTree [data-kind="row"]')
        L = pg.evaluate(LAYOUT, SET)
        assert len(L["kids"]) >= 2, L
        assert all(abs(k["eye"] - L["headEye"]) <= 1 for k in L["kids"]), ("눈 칸은 폴더 줄과 자식 줄이 일렬", L)
        assert all(k["name"] >= L["headIcon"] + 16 for k in L["kids"]), ("자식 이름은 폴더 아이콘보다 안쪽", L)
        assert all(k["guide"] for k in L["kids"]), ("자식마다 세로 안내선", L)
        assert [k["last"] for k in L["kids"]] == [False] * (len(L["kids"]) - 1) + [True], ("안내선은 마지막 자식에서 끝", L)
        assert L["headBg"] not in ("rgba(0, 0, 0, 0)", "transparent"), ("폴더 줄 바탕색", L)
        _layer_head(pg, SET).locator(".ly-name").hover()
        pg.wait_for_timeout(100)
        assert all(k["hov"] for k in pg.evaluate(LAYOUT, SET)["kids"]), "폴더 줄에 올리면 그 묶음이 함께"
        if SHOTS:
            pg.locator("#pLayers").screenshot(path=os.path.join(SHOTS, "layers-folder-children.png"))
        assert not errors, errors
    finally:
        srv.shutdown(); srv.server_close()
        pg.close()
