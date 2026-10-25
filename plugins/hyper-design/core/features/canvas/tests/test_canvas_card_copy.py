"""카드 바로 복제(51-6, Figma F19: Ctrl+D = 프레임 복제 → 바로 오른쪽에, 복사본이 골라짐) — 브라우저.

예전: 카드 [복제] = 흰 빈 레이아웃 메모(보내면 AI 가 복제). 사용자 결정: 도우미로 열면 파일째 바로 복제(AI·메모 없음), 새 id·'<제목> 복사',
같은 줄 원본 바로 오른쪽, 쓰기 한 번 = 되돌리기 한 줄, 화면에 먼저 보이고 거절이면 거두고 토스트.
"""
import json, os, shutil, subprocess, sys, tempfile, threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx, reload  # noqa: F401
from test_canvas_edit import fit_view

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
SHOTS = os.environ.get("HD_SHOTS")                   # 눈으로 볼 때만: 스크린숏 폴더
SRC = "job"                                           # '설정' 줄 첫 카드(오른쪽에 language 가 있음)
PICKED = "() => [...document.querySelectorAll('#rows .card.picked')].map(c => c.dataset.id)"
ORDER = "(id) => { const c = document.querySelector('.card[data-id=\"' + id + '\"]'); return c ? [...c.parentNode.children].map(x => x.dataset.id) : null; }"
BOX = "(id) => { const c = document.querySelector('.card[data-id=\"' + id + '\"] .phone'); if (!c) return null; const r = c.getBoundingClientRect(); return [r.x, r.y, r.width]; }"


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-cardcopy-"))
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


def _open(ctx, o):
    srv = helper.make_server(o, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(srv.url)
    pg.wait_for_function("window.__hdReady !== undefined")
    pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
    reload(pg)
    pg.evaluate("window.__hdStay = 1")
    fit_view(pg)
    return srv, pg, errors


def _select(pg, sid):
    pg.keyboard.press("v")
    pg.evaluate("(id) => document.querySelector('.card[data-id=\"' + id + '\"]').scrollIntoView({block: 'center', inline: 'center'})", sid)
    b = pg.locator(f'.card[data-id="{sid}"] .cover').bounding_box()
    pg.mouse.click(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    pg.wait_for_function("(id) => [...document.querySelectorAll('#rows .card.picked')].map(c => c.dataset.id).join() === id", arg=sid)


@pytest.mark.area("tools", "helper")
def test_ctrl_d_copies_card_to_the_right_at_once_and_one_undo_removes_it(ctx, out):
    srv, pg, errors = _open(ctx, out)
    try:
        _select(pg, SRC)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "t51-6-before.png"))
        src_box = pg.evaluate(BOX, SRC)
        pg.keyboard.press("Control+d")
        pg.wait_for_function("!!document.querySelector('.card[data-id=\"job-copy\"]')", timeout=1500)   # 화면에 먼저(쓰기를 기다리지 않음)
        order = pg.evaluate(ORDER, SRC)
        assert order[order.index(SRC) + 1] == "job-copy", f"같은 줄 원본 바로 뒤 {order}"
        box = pg.evaluate(BOX, "job-copy")
        assert box[0] > src_box[0] + src_box[2] - 1 and abs(box[1] - src_box[1]) < 2, f"원본 오른쪽 같은 높이 {src_box} {box}"
        assert pg.evaluate(PICKED) == ["job-copy"], "복사본이 골라짐(Figma)"
        assert pg.locator('.card[data-id="job-copy"] .ftitle').inner_text().strip().endswith(" 복사")
        assert _wait(lambda: (out / "screens/job-copy.html").is_file()), "파일이 생김"
        assert (out / "screens/job-copy.html").read_bytes() == (out / "screens/job.html").read_bytes()
        ids = [s["id"] for s in _sj(out)["screens"]]
        assert ids[ids.index(SRC) + 1] == "job-copy"
        pg.wait_for_function("document.getElementById('toast').textContent.includes('파일에 썼어요')", timeout=5000)
        assert pg.locator(".card.draft").count() == 0, "흰 복제 카드(빈 레이아웃 메모)를 만들지 않음"
        pg.wait_for_function("(() => { const f = document.querySelector('.card[data-id=\"job-copy\"] .phone iframe'); return f && /job-copy\\.html/.test(f.getAttribute('src') || f.getAttribute('data-src') || ''); })()", timeout=10000)
        pg.wait_for_timeout(400)
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "t51-6-after.png"))
        pg.keyboard.press("Escape")
        pg.keyboard.press("Control+z")
        pg.wait_for_function("!document.querySelector('.card[data-id=\"job-copy\"]')", timeout=10000)
        assert _wait(lambda: not (out / "screens/job-copy.html").exists()), "되돌리기 한 번 = 파일도 사라짐"
        assert "job-copy" not in [s["id"] for s in _sj(out)["screens"]]
        if SHOTS:
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(SHOTS, "t51-6-undo.png"))
        assert pg.evaluate("window.__hdStay") == 1, "새로고침 없음"
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()


@pytest.mark.area("tools", "helper")
def test_refused_copy_is_taken_back_with_toast(ctx, out):
    (out / "screens/job-copy.html").write_text("<p>남의 파일</p>", encoding="utf-8")   # 판은 모르는 파일 — 도우미가 덮지 않고 거절
    srv, pg, errors = _open(ctx, out)
    try:
        _select(pg, SRC)
        pg.keyboard.press("Control+d")
        pg.wait_for_function("document.getElementById('toast').textContent.includes('되돌렸어요')", timeout=8000)
        assert pg.locator('.card[data-id="job-copy"]').count() == 0, "거절 = 복사본을 거둔다"
        assert pg.evaluate(PICKED) == [SRC], "원본이 다시 골라짐"
        assert (out / "screens/job-copy.html").read_text(encoding="utf-8") == "<p>남의 파일</p>"
        assert "job-copy" not in [s["id"] for s in _sj(out)["screens"]]
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
