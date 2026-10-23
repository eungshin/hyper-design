"""카드 글 상자의 정책 = 자유 메모 하나(task 31, K1) · 판의 카드 아래 글은 제목만, 고르면 설명·정책 — 브라우저.

사용자 보고: "정책 줄을 지우거나 더하거나 자유롭게 고칠 수 없다". 상자의 정책은 여러 줄 글 한 칸(Enter = 새 줄),
저장하면 줄마다 한 줄 정책 목록 하나(빈 줄 버림) → 카드에 그 목록 · 도우미가 screens.json 에 그 목록 · 되돌리기 한 번 = 원래 목록.
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, reload, zoom_to  # noqa: F401
from test_canvas_edit import notes_of, wait_notes

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
CARD = '.card[data-id="job"]'
CLICK = """(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))"""


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-capnote-"))
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


def _policies_in_file(o):
    return next(s for s in json.loads((o / "screens.json").read_text(encoding="utf-8"))["screens"] if s["id"] == "job")["policies"]


def _select(pg, sid="job"):
    pg.evaluate(CLICK, sid)
    pg.wait_for_function("(id) => document.querySelector('.card[data-id=\"' + id + '\"]').classList.contains('picked')", arg=sid, timeout=3000)


def _card_lines(pg):
    return [t.strip() for t in pg.locator(CARD + " .pol li").all_text_contents()]


def _empty(pg):
    from test_canvas_baseline import empty_point
    return empty_point(pg)


@pytest.mark.area("helper", "tools", "notes")
def test_policy_note_add_delete_insert_saves_one_list(ctx, out):
    old = _policies_in_file(out)
    assert len(old) == 3, old
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg, errors = _open(ctx, srv.url)
    try:
        zoom_to(pg, "job", 200)
        _select(pg)
        pg.dblclick(CARD + " .ftitle")
        box = pg.locator(CARD + " .capbox")
        note = box.locator('[data-f="policies"]')
        assert note.is_visible() and note.get_attribute("contenteditable") == "true", "정책 = 한 칸의 글"
        assert box.locator('[data-f="policies"] li').count() == 0, "고치는 동안 글머리표 없음"
        assert [ln.strip() for ln in note.inner_text().split("\n") if ln.strip()] == old
        note.click()
        pg.keyboard.press("Control+a")                # 첫 줄 지우기 · 가운데 넣기 · 끝에 더하기 — 그냥 글 고치듯
        pg.keyboard.type(old[1])
        pg.keyboard.press("Enter")
        pg.keyboard.type("가운데 새 줄")
        pg.keyboard.press("Enter")
        pg.keyboard.press("Enter")                    # 빈 줄은 버린다
        pg.keyboard.type(old[2])
        pg.keyboard.press("Enter")
        pg.keyboard.type("끝에 더한 줄")
        want = [old[1], "가운데 새 줄", old[2], "끝에 더한 줄"]
        e = _empty(pg)
        pg.mouse.click(e["x"], e["y"])                # 밖을 누르면 저장
        wait_notes(pg, 1)
        n = notes_of(pg)[0]
        assert n["edit"] == "policies" and n["value"] == want, n
        assert "정책 줄 바꾸기: ①" in n["note"], n["note"]
        _select(pg)
        assert _card_lines(pg) == want, "카드에 새 목록이 바로 보인다(반영 대기)"
        pg.keyboard.press("Control+z")                # 되돌리기 한 번 = 원래 목록
        wait_notes(pg, 0)
        _select(pg)
        assert _card_lines(pg) == old
        pg.keyboard.press("Control+y")
        wait_notes(pg, 1)
        pg.click("#nsend")
        pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.apply", timeout=20000)
        assert _policies_in_file(out) == want, "도우미가 screens.json 에 그 목록 그대로"
        pg.wait_for_timeout(300)
        _select(pg)
        assert _card_lines(pg) == want
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_board_shows_title_only_until_card_is_selected(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    zoom_to(pg, "job", 200)
    vis = lambda: {k: pg.locator(CARD + " " + s).first.is_visible() for k, s in (("title", ".ftitle"), ("desc", ".fdesc"), ("pol", "ul.pol"))}
    assert vis() == {"title": True, "desc": False, "pol": False}, "고르지 않은 카드 = 제목만"
    assert not pg.locator(CARD + " .capmark").is_visible()
    _select(pg)
    assert vis() == {"title": True, "desc": True, "pol": True}, "고르면 설명·정책"
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.querySelector('.card[data-id=\"job\"]').classList.contains('picked')", timeout=3000)
    assert vis() == {"title": True, "desc": False, "pol": False}, "고르기를 풀면 다시 제목만"
    _select(pg)                                       # 설명을 고치면 접힌 카드에도 작은 표시
    pg.dblclick(CARD + " .fdesc")
    pg.keyboard.press("Control+a")
    pg.keyboard.type("새 설명")
    pg.keyboard.press("Control+Enter")
    wait_notes(pg, 1)
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.querySelector('.card[data-id=\"job\"]').classList.contains('picked')", timeout=3000)
    assert not pg.locator(CARD + " .fdesc").is_visible() and pg.locator(CARD + " .capmark").is_visible(), "반영 대기가 접혀서 안 보이면 안 된다"
    assert not errors, errors
    pg.close()
