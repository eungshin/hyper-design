"""카드 글 상자 = 제목 + 본문 한 칸(R21, K1) · 판의 카드 아래 글은 제목만, 고르면 본문 — 브라우저.

사용자 요청(R21): 제목 아래 설명·정책으로 나뉜 칸 대신 자유 글 한 칸(줄바꿈·빈 줄·다 지우기 가능).
옛 데이터의 정책 줄은 본문 끝 '- ' 줄로 보이고, 본문을 고쳐 저장하면 purpose 로 접혀 들어가며 policies 는 빈 목록 →
도우미가 screens.json 에 쓰고, 다시 열어도 같은 글. 다 지우면 빈 본문.
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


def _job_in_file(o):
    return next(s for s in json.loads((o / "screens.json").read_text(encoding="utf-8"))["screens"] if s["id"] == "job")


def _select(pg, sid="job"):
    pg.evaluate(CLICK, sid)
    pg.wait_for_function("(id) => document.querySelector('.card[data-id=\"' + id + '\"]').classList.contains('picked')", arg=sid, timeout=3000)


def _body_on_card(pg):
    el = pg.locator(CARD + " > .cbody > .fdesc")
    return el.first.inner_text() if el.count() else None


def _empty(pg):
    from test_canvas_baseline import empty_point
    return empty_point(pg)


def _reload_shows(pg, want):
    """새로고침 → 카드 본문. 도우미는 쓴 뒤 확인(뒤 빌드) 중이면 있던 페이지를 준다(contract '로컬 도우미') — 새 페이지가 나올 때까지 몇 번."""
    got = None
    for _ in range(20):
        reload(pg)
        zoom_to(pg, "job", 200)
        _select(pg)
        got = _body_on_card(pg)
        if got == want:
            break
        pg.wait_for_timeout(500)
    return got


def _save_and_send(pg, notes):
    e = _empty(pg)
    pg.mouse.click(e["x"], e["y"])                    # 밖을 누르면 저장
    wait_notes(pg, notes)
    pg.evaluate("window.__hdLastHelper = null")
    pg.click("#nsend")
    pg.wait_for_function("window.__hdLastHelper && window.__hdLastHelper.apply", timeout=20000)


@pytest.mark.area("helper", "tools", "notes")
def test_card_text_is_title_plus_one_free_body(ctx, out):
    job = _job_in_file(out)
    assert job["purpose"] and len(job["policies"]) == 3, job
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg, errors = _open(ctx, srv.url)
    try:
        zoom_to(pg, "job", 200)
        _select(pg)
        merged = job["purpose"] + "\n" + "\n".join("- " + p for p in job["policies"])
        assert _body_on_card(pg) == merged, "옛 정책 줄은 본문 끝 '- ' 줄로 보인다"
        pg.dblclick(CARD + " .ftitle")
        box = pg.locator(CARD + " .capbox")
        body = box.locator('[data-f="purpose"]')
        assert box.locator("[contenteditable=true]").count() == 2, "제목 + 본문, 두 칸뿐"
        assert box.locator('[data-f="policies"], .capfoot').count() == 0, "정책 칸·긴 안내 줄 없음"
        assert body.inner_text() == merged
        body.click()
        pg.keyboard.press("Control+a")
        pg.keyboard.type("첫 줄")
        pg.keyboard.press("Enter")                    # Enter = 줄바꿈
        pg.keyboard.press("Enter")                    # 빈 줄도 남는다
        pg.keyboard.type("- 셋째 줄")
        pg.keyboard.press("Shift+Enter")
        pg.keyboard.type("끝")
        want = "첫 줄\n\n- 셋째 줄\n끝"
        _save_and_send(pg, 2)
        f = _job_in_file(out)
        assert f["purpose"] == want and f["policies"] == [], f
        assert _reload_shows(pg, want) == want, "다시 열어도 같은 글"
        pg.dblclick(CARD + " .fdesc")                 # 다 지우기 → 빈 본문
        pg.keyboard.press("Control+a")
        pg.keyboard.press("Delete")
        assert body.inner_text().strip() == "" and body.get_attribute("data-ph") == "설명", "빈 본문엔 안내 글 하나"
        _save_and_send(pg, 1)
        assert _job_in_file(out)["purpose"] == ""
        assert _reload_shows(pg, None) is None, "빈 본문 = 카드 아래 글 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools")
def test_board_shows_title_only_until_card_is_selected(ctx, out):
    pg, errors = _open(ctx, (out / "index.html").resolve().as_uri())
    zoom_to(pg, "job", 200)
    vis = lambda: {k: pg.locator(CARD + " " + s).first.is_visible() for k, s in (("title", ".ftitle"), ("desc", ".fdesc"))}
    assert vis() == {"title": True, "desc": False}, "고르지 않은 카드 = 제목만"
    assert not pg.locator(CARD + " .capmark").is_visible()
    _select(pg)
    assert vis() == {"title": True, "desc": True}, "고르면 본문"
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.querySelector('.card[data-id=\"job\"]').classList.contains('picked')", timeout=3000)
    assert vis() == {"title": True, "desc": False}, "고르기를 풀면 다시 제목만"
    _select(pg)                                       # 설명을 고치면 접힌 카드에도 작은 표시
    pg.dblclick(CARD + " .fdesc")
    pg.keyboard.press("Control+a")
    pg.keyboard.type("새 설명")
    pg.keyboard.press("Control+Enter")
    wait_notes(pg, 2)                                 # 본문 + 옛 정책 줄 접기(policies [])
    pg.keyboard.press("Escape")
    pg.wait_for_function("!document.querySelector('.card[data-id=\"job\"]').classList.contains('picked')", timeout=3000)
    assert not pg.locator(CARD + " .fdesc").is_visible() and pg.locator(CARD + " .capmark").is_visible(), "반영 대기가 접혀서 안 보이면 안 된다"
    assert not errors, errors
    pg.close()
