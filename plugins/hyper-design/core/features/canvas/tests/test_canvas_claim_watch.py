"""#254 hd claim + 도우미가 화면 파일을 지켜봄 — 상태 칩(task 37: 화면을 가리지 않음)이 새로고침 없이 뜨고, 바뀐 화면 카드만 다시 싣는다(브라우저 1개)."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("helper")
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hd-claim-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def post(srv, path, body):
    req = urllib.request.Request(srv.url.split("/index.html")[0] + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": srv.token})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


SRCS = """() => Object.fromEntries([...document.querySelectorAll('.card[data-id]')].map(c => {
  const f = c.querySelector('.phone iframe'); return [c.dataset.id, f ? (f.getAttribute('src') || '') + '|' + (f.getAttribute('data-src') || '') : ''];
}))"""


def touch(f):
    f.write_text(f.read_text(encoding="utf-8") + "\n<!-- AI 가 고침 -->\n", encoding="utf-8")


def test_claim_cover_without_reload_and_only_changed_card_reloads(ctx, out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    cover = '.card[data-id="job"] .busy'
    try:
        pg.goto(srv.url)
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("window.__sameLoad = 1")             # 새로고침되면 사라진다
        assert pg.locator(".busy").count() == 0
        post(srv, "/api/claim", {"screen": "job", "by": "agent-9", "note": "제목 고치는 중"})   # = hd claim job --by agent-9 --note …
        pg.wait_for_selector(cover + '[data-via="cli"]', timeout=8000)
        assert pg.text_content(cover + " .busy-txt") == "agent-9 수정 중 · 제목 고치는 중" and pg.get_attribute(cover, "data-kind") == "working"
        assert pg.locator(".busy").count() == 1 and pg.evaluate("window.__sameLoad") == 1, "그 카드만 · 새로고침 없이"
        assert pg.evaluate("document.querySelector('.card[data-id=\"job\"] .phone').getAttribute('data-busy')") == "working"
        from test_canvas_v2 import open_screen
        open_screen(pg, "job")                             # 크게 보기 = 제목 막대에 같은 칩(덮개 없음)
        pg.wait_for_selector('#modal .mbar .busy[data-kind="working"]', timeout=4000)
        assert pg.text_content("#modal .mbar .busy .busy-txt") == "agent-9 수정 중 · 제목 고치는 중"
        assert pg.locator("#modal .busy").count() == 1, "크게 보기 화면 위에는 덮개가 없다"
        pg.keyboard.press("Escape")
        pg.wait_for_function("document.getElementById('modal').hidden")
        assert pg.locator("#modal .busy").count() == 0, "닫으면 막대 칩도 없다"
        before = pg.evaluate(SRCS)
        touch(out / "screens" / "job.html")               # 끝난 편집 → 덮개가 걷히고 그 카드만 다시
        pg.wait_for_selector(cover, state="detached", timeout=8000)
        pg.wait_for_function("(b) => { const f = document.querySelector('.card[data-id=\"job\"] .phone iframe'); return f && ((f.getAttribute('src') || '') + '|' + (f.getAttribute('data-src') || '')) !== b; }",
                             arg=before["job"], timeout=8000)
        pg.wait_for_timeout(2500)                          # 도우미 알림(1초)·카드 폴링(1초)이 한 바퀴 더 돌아도
        after = pg.evaluate(SRCS)
        assert [k for k in before if before[k] != after[k]] == ["job"], "다른 카드는 다시 싣지 않는다"
        assert pg.evaluate("window.__sameLoad") == 1

        before = after                                     # 덮개 없는 카드: 파일이 바뀌면 그 카드만
        touch(out / "screens" / "usage.html")
        pg.wait_for_function("(b) => { const f = document.querySelector('.card[data-id=\"usage\"] .phone iframe'); return f && ((f.getAttribute('src') || '') + '|' + (f.getAttribute('data-src') || '')) !== b; }",
                             arg=before["usage"], timeout=8000)
        pg.wait_for_timeout(1500)
        after = pg.evaluate(SRCS)
        assert [k for k in before if before[k] != after[k]] == ["usage"]

        post(srv, "/api/claim", {"screen": "job"})       # hd release = 손으로 걷기
        pg.wait_for_selector(cover + '[data-via="cli"]', timeout=8000)
        assert pg.text_content(cover + " .busy-txt") == "AI 수정 중"
        assert post(srv, "/api/release", {"screen": "job"})["released"] is True
        pg.wait_for_selector(cover, state="detached", timeout=8000)
        assert pg.evaluate("window.__sameLoad") == 1
    finally:
        srv.shutdown(); srv.server_close()
    assert not errors, errors
    pg.close()
