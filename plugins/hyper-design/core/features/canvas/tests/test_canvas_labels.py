"""R27 F01·F08·F12 — 판 이름표는 화면에서 늘 같은 크기(Figma 프레임 이름·FigJam 메모 핀처럼): 카드 제목·줄 제목·메모 배지·AI 수정 중 칩이
전체 보기(작게)와 100% 에서 같은 화면 px, 판 배치(카드 자리)는 배율과 상관없이 그대로 · 칩은 날 id 가 아니라 에이전트 이름 · 고른 카드의 선 태그는 겹치지 않는다(브라우저 1개 + 도우미)."""
import threading

import pytest

from test_canvas_claim_watch import helper, out, post  # noqa: F401
from test_canvas_v2 import browser, ctx  # noqa: F401

pytestmark = pytest.mark.area("helper", "flow")

SIZES = """() => { const h = (q) => { const e = document.querySelector(q); return e ? Math.round(e.getBoundingClientRect().height * 10) / 10 : null; };
  return {title: h('.card[data-id="job"] > .ftitle'), row: h('#rows .flow > .glabel'), badge: h('.card[data-id="job"] .nbadge'), chip: h('.card[data-id="job"] .busy'),
          font: parseFloat(getComputedStyle(document.querySelector('.card[data-id="job"] > .ftitle')).fontSize) * document.querySelector('.card[data-id="job"] > .ftitle').getBoundingClientRect().height
                / document.querySelector('.card[data-id="job"] > .ftitle').offsetHeight,
          layout: [...document.querySelectorAll('.card[data-id]')].map(c => [c.dataset.id, c.offsetLeft, c.offsetTop, c.offsetHeight])}; }"""
CLICK = """(id) => document.querySelector('.card[data-id="' + id + '"] .cover').dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, detail: 1}))"""
TAGS = """() => [...document.querySelectorAll('#rows .alabel')].filter(n => getComputedStyle(n).display !== 'none').map(n => { const r = n.getBoundingClientRect();
  return {l: r.left, t: r.top, r: r.right, b: r.bottom, fs: parseFloat(getComputedStyle(n).fontSize) * r.width / n.offsetWidth}; })"""


def zoom(pg, key):
    pg.evaluate("document.activeElement && document.activeElement.blur && document.activeElement.blur()")   # 단축키가 입력 칸이 아닌 판에 가게
    if key == "100":
        pg.click("#zoom"); pg.click('#vmenu [data-z="100"]')
    else:
        pg.keyboard.press(key)
    pg.wait_for_timeout(700)                              # 카메라 전환 + --lz 정확한 값(멈춘 뒤 150ms)
    return pg.evaluate("+document.getElementById('stage').dataset.zoom")


def test_labels_keep_screen_size_and_chip_names_the_agent(ctx, out):
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        pg.goto(srv.url, timeout=120000)
        pg.wait_for_function("window.__hdReady !== undefined", timeout=120000)
        zoom(pg, "0")
        pg.evaluate(CLICK, "job")                         # 메모 하나 → 카드 메모 배지
        pg.click('#selbar [data-act="memo"]')
        pg.wait_for_selector("#pop:not([hidden])")
        pg.fill("#pnote", "제목을 더 짧게")
        pg.click("#padd")
        pg.keyboard.press("Escape")
        pg.wait_for_selector('.card[data-id="job"] .nbadge', timeout=5000)
        post(srv, "/api/claim", {"screen": "job", "by": "agent-9", "note": "제목 고치는 중"})
        chip = '.card[data-id="job"] .busy .busy-txt'
        pg.wait_for_selector(chip, timeout=15000)
        assert pg.text_content(chip) == "AI 수정 중 · 제목 고치는 중", "날 id(agent-9)는 칩 글에 쓰지 않는다(F12)"
        assert "agent-9" in pg.get_attribute('.card[data-id="job"] .busy', "title"), "id 는 title 에만"
        pg.evaluate("document.body.dispatchEvent(new CustomEvent('hd-agent', {detail: {agent: 'agent-9', name: '온보딩 봇'}}))")
        pg.wait_for_function("(q) => document.querySelector(q).textContent.startsWith('온보딩 봇 수정 중')", arg=chip, timeout=3000)

        zf = zoom(pg, "0")
        small = pg.evaluate(SIZES)
        z1 = zoom(pg, "100")
        big = pg.evaluate(SIZES)
        assert zf < 0.3 and abs(z1 - 1) < 0.05, (zf, z1)
        for k, want in (("title", 16), ("row", 16), ("badge", 18), ("chip", 22)):
            assert small[k] is not None and abs(small[k] - want) <= 1.5 and abs(big[k] - want) <= 1.5, (k, small[k], big[k])
        assert abs(small["font"] - 11) < 0.6 and abs(big["font"] - 11) < 0.6, ("카드 제목 글자 = 화면 11px", small["font"], big["font"])
        assert small["layout"] == big["layout"], "판 배치(카드 자리·높이)는 배율과 상관없이 그대로"
        busy = pg.evaluate("""() => getComputedStyle(document.querySelector('.card[data-id="job"] .phone')).boxShadow""")
        pg.evaluate(CLICK, "job")                         # 고른 카드에서도 AI 수정 중 테두리가 보인다
        pg.wait_for_function("document.getElementById('rows').classList.contains('focusing')", timeout=3000)
        pg.wait_for_timeout(400)
        sel = pg.evaluate("""() => getComputedStyle(document.querySelector('.card[data-id="job"] .phone')).boxShadow""")
        accent = busy.split(")")[0] + ")"
        assert sel.startswith(accent), ("고른 카드의 첫 그림자 = 강조 테두리 색", busy, sel)
        tags = pg.evaluate(TAGS)
        assert len(tags) >= 2, tags
        assert all(abs(t["fs"] - 11) < 0.6 for t in tags), ("선 태그 = 화면 11px", tags)
        for i, a in enumerate(tags):
            for b in tags[i + 1:]:
                assert not (a["l"] < b["r"] and a["r"] > b["l"] and a["t"] < b["b"] and a["b"] > b["t"]), ("보이는 선 태그는 겹치지 않는다(F08)", a, b)
        assert not errors, errors
    finally:
        pg.close()
        srv.shutdown()
        srv.server_close()
