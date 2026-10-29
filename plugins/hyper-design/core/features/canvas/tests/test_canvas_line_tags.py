"""R46 선 태그 — 한 선에 태그 하나("첫 버튼 글 외 N"), 태그는 제 선에 붙음(카드 옆 목록이 아님),
태그에 올리면 그 선의 트리거 목록 창, 줄에 올리면 화면 안 그 버튼 표시가 진해진다(브라우저 1개 + 도우미).
고정본: dayfine 의 job 화면에 usage 로 가는 버튼 6개(글 5가지 + 같은 글 하나)를 더한다."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from test_canvas_v2 import REPO, SCRIPTS, browser, ctx  # noqa: F401

sys.path.insert(0, str(SCRIPTS))
import helper  # noqa: E402

pytestmark = pytest.mark.area("flow", "links")
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"
TEXTS = ["사용 방법", "도움말", "자주 묻는 질문", "튜토리얼", "가이드 보기", "도움말"]
CLICK = """(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))"""
# 보이는 태그마다: 글 · 화면 가운데 · 제 선(양방향이면 거꾸로 그린 선)에서 태그 상자까지 가장 가까운 화면 거리(상자에 닿으면 0)
TAGS = """() => [...document.querySelectorAll('#rows .alabel')].filter(n => getComputedStyle(n).display !== 'none').map(n => {
  const r = n.getBoundingClientRect(), cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
  const p = [...document.querySelectorAll('#ar path.ln')].find(q => (q.dataset.from === n.dataset.from && q.dataset.to === n.dataset.to) || (q.dataset.from === n.dataset.to && q.dataset.to === n.dataset.from));
  let d = null;
  if (p) { const m = p.getScreenCTM(), L = p.getTotalLength(); d = 1e9;
    for (let s = 0; s <= L; s += 2) { const q = p.getPointAtLength(s), x = m.a * q.x + m.c * q.y + m.e, y = m.b * q.x + m.d * q.y + m.f; d = Math.min(d, Math.hypot(Math.max(r.left - x, 0, x - r.right), Math.max(r.top - y, 0, y - r.bottom))); } }
  return {from: n.dataset.from, to: n.dataset.to, text: n.textContent, cx, cy, l: r.left, t: r.top, r: r.right, b: r.bottom, d};
})"""


@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-ltag-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    f = o / "screens" / "job.html"
    btns = "".join(f'<a href="usage.html" style="display:inline-block;margin:4px;padding:6px 10px">{t}</a>' for t in TEXTS)
    f.write_text(re.sub(r"(<body[^>]*>)", r"\1<div>" + btns + "</div>", f.read_text(encoding="utf-8"), count=1), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def test_one_tag_per_line_on_its_line_with_trigger_list(ctx, out):  # noqa: F811
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url, timeout=120000)
        pg.wait_for_function("window.__hdReady !== undefined", timeout=120000)
        pg.evaluate("document.activeElement && document.activeElement.blur && document.activeElement.blur()")
        pg.click("#zoom"); pg.click('#vmenu [data-z="100"]')
        pg.wait_for_timeout(700)
        pg.evaluate(CLICK, "job")
        pg.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=5000)
        pg.wait_for_function("(document.querySelector('.card[data-id=job] .phone iframe').getAttribute('src') || '').includes('job')", timeout=10000)
        frame = None
        for _ in range(50):
            frame = pg.locator('.card[data-id="job"] .phone iframe').element_handle().content_frame()
            if frame and "job" in frame.url: break
            pg.wait_for_timeout(100)
        frame.wait_for_function("document.querySelectorAll('[data-hd-links]').length >= 6", timeout=10000)
        pg.wait_for_timeout(400)

        tags = pg.evaluate(TAGS)
        mine = [t for t in tags if t["from"] == "job" and t["to"] == "usage"]
        assert len(mine) == 1, ("버튼 6개가 가는 선 하나 = 태그 하나", mine)
        assert re.fullmatch(r"\S 사용 방법 외 5", mine[0]["text"]), mine[0]["text"]
        assert all("·" not in t["text"] for t in tags), "버튼 글을 이어 붙이지 않는다(예전 '사용 방법 · 도움말')"
        on = [t for t in tags if t["d"] is not None and -10 < t["cx"] < 1450 and -10 < t["cy"] < 1010]
        assert on and all(t["d"] <= 3 for t in on), ("보이는 태그는 제 선에 붙는다(카드 옆 목록이 아니라)", [(t["text"], t["d"]) for t in on])

        pg.mouse.move(mine[0]["cx"], mine[0]["cy"])
        pg.wait_for_selector("#ltpop:not([hidden])", timeout=3000)
        pop = pg.evaluate("""() => { const p = document.getElementById('ltpop'), r = p.getBoundingClientRect();
            return {rows: [...p.querySelectorAll('[data-i]')].map(n => n.textContent), head: p.querySelector('.lt-h').textContent, l: r.left, t: r.top, r: r.right, b: r.bottom}; }""")
        assert pop["rows"] == TEXTS, ("트리거마다 한 줄(같은 글 버튼도)", pop["rows"])
        assert "버튼 6개" in pop["head"], pop["head"]
        tg = mine[0]
        assert not (pop["l"] < tg["r"] and pop["r"] > tg["l"] and pop["t"] < tg["b"] and pop["b"] > tg["t"]), ("목록 창은 태그 옆(덮지 않음)", pop, tg)

        row = pg.locator("#ltpop [data-i]").nth(2)
        row.hover()
        frame.wait_for_function("[...document.querySelectorAll('[data-hd-links]')].some(d => d.style.borderTopStyle === 'solid')", timeout=3000)
        lit = frame.evaluate("""() => { const d = [...document.querySelectorAll('[data-hd-links]')].filter(d => d.style.borderTopStyle === 'solid');
            const a = [...document.querySelectorAll('a')].find(a => a.textContent === '자주 묻는 질문').getBoundingClientRect();
            return d.map(x => { const r = x.getBoundingClientRect(); return Math.abs((r.left + r.right) / 2 - (a.left + a.right) / 2) < 2 && Math.abs((r.top + r.bottom) / 2 - (a.top + a.bottom) / 2) < 2; }); }""")
        assert lit == [True], ("올린 줄의 버튼 하나만 진하게", lit)
        assert frame.evaluate("document.querySelectorAll('[data-hd-links]').length") >= 6, "나머지 버튼 표시는 그대로"

        pg.mouse.move(700, 990)
        pg.wait_for_selector("#ltpop", state="hidden", timeout=3000)
        frame.wait_for_function("![...document.querySelectorAll('[data-hd-links]')].some(d => d.style.borderTopStyle === 'solid')", timeout=3000)
        assert not errors, errors
    finally:
        pg.close()
        srv.shutdown()
        srv.server_close()
