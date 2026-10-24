"""공유 규칙 fixture(task 41) — palette.js 쪽(브라우저). Python 쪽은 test_canvas_unit_shared_rules.py.

#275 요소 경로: tests/fixtures/paths.json 을 palette.js 가 미리보기·다시 찾기에 쓰는 find/match 가 helper.select 와 같이 푸는지,
         그리고 pathOf 가 만든 경로를 helper.select 가 같은 요소로 되찾는지(모든 요소).
#276 화면 링크: tests/fixtures/links.json 을 palette.js hrefOf + linkTo(=toOf 의 규칙)가 따르는지.
palette.js 는 window.__hdRules = {pathOf, match, find, hrefOf, linkTo} 로 이 규칙들을 내놓는다(테스트·진단용, 읽기만).
"""
import json, sys
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from test_canvas_unit_shared_rules import PATHS, LINKS, doc, helper_resolve  # noqa: E402

PALETTE = HERE.parents[2] / "foundation" / "palette.js"
BASE = "http://hd.test/out/"


@pytest.fixture(scope="module")
def pg():
    with sync_api.sync_playwright() as p:
        b = None
        for kw in ({"channel": "chrome"}, {}):
            try:
                b = p.chromium.launch(**kw)
                break
            except Exception:
                continue
        if b is None:
            pytest.skip("chromium 없음")
        page = b.new_page()
        errors, pages = [], {}
        page.on("pageerror", lambda e: errors.append(str(e)))

        def serve(route):
            url = route.request.url.split("?")[0]
            if url.endswith("/palette.js"):
                route.fulfill(body=PALETTE.read_text(encoding="utf-8"), content_type="text/javascript")
            else:
                route.fulfill(body=pages.get(url, ""), content_type="text/html")
        page.route("http://hd.test/**", serve)

        def load(body, name="a.html"):
            html = doc(body).replace("<head></head>", '<head><script src="../palette.js"></script></head>')
            pages[BASE + name] = html
            page.goto(BASE + name)
            page.wait_for_function("!!window.__hdRules")
        page.load = load
        yield page
        assert not errors, errors
        b.close()


RESOLVE = """(path) => {
  const els = [...document.body.querySelectorAll('*')], R = window.__hdRules, m = R.match(path), f = R.find(path);
  if (f) return els.indexOf(f);
  return m.length > 1 ? 'ambiguous' : 'none';
}"""

ROUND = """() => [...document.body.querySelectorAll('*')].map(el => window.__hdRules.pathOf(el))"""


@pytest.mark.area("modal", "helper")
@pytest.mark.parametrize("c", PATHS, ids=[c["name"] for c in PATHS])
def test_palette_paths_follow_fixture(pg, c):
    pg.load(c["html"])
    assert pg.evaluate(RESOLVE, c["path"]) == c["expect"]
    for i, path in enumerate(pg.evaluate(ROUND)):     # pathOf → 미리보기도 도우미도 같은 그 요소
        assert pg.evaluate(RESOLVE, path) == i, path
        assert helper_resolve(c["html"], path) == i, path


LINK = """([attr, href, here]) => {
  const el = document.createElement('a'); el.setAttribute(attr, href);
  return window.__hdRules.linkTo(window.__hdRules.hrefOf(el), here);
}"""


@pytest.mark.area("links")
def test_palette_links_follow_fixture(pg):
    pg.load("<p>x</p>")
    got = {(c.get("attr", "href"), c["href"]): pg.evaluate(LINK, [c.get("attr", "href"), c["href"], BASE + c["from"]]) for c in LINKS}
    want = {(c.get("attr", "href"), c["href"]): c["to"] for c in LINKS}
    assert got == want
