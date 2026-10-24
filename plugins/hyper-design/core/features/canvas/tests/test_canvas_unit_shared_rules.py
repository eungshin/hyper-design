"""공유 규칙 fixture(task 41) — Python 쪽. 브라우저 없음.

#275 요소 경로: tests/fixtures/paths.json 을 helper.select(편집이 고치는 요소)가 그대로 따르는지.
#276 화면 링크: tests/fixtures/links.json 을 build_canvas(_Links + link_target · 판의 선)와 helper._link_to(끊기·잇기)가 따르는지.
같은 fixture 를 palette.js(미리보기·고르기)는 test_canvas_shared_rules.py(브라우저)에서 읽는다 — 세 곳이 한 표를 본다.
helper._link_to 는 build_canvas.link_target 하나로 푼다(task 40) — 링크 칸은 모두 그대로 통과해야 한다.
"""
import json, re, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import build_canvas  # noqa: E402
import helper  # noqa: E402  — 읽기만(select · _link_to)

PATHS = json.loads((HERE / "fixtures" / "paths.json").read_text(encoding="utf-8"))["cases"]
LINKS = json.loads((HERE / "fixtures" / "links.json").read_text(encoding="utf-8"))["cases"]


def doc(body):
    return "<!doctype html><html><head></head><body>" + body + "</body></html>"


def body_elements(tree):
    body = next(n for n in tree.walk() if n.tag == "body")
    return list(tree.walk(body))


def helper_resolve(html, path):
    """helper.select → body 아래 요소 번호 | 'ambiguous' | 'none'."""
    tree = helper.Tree(doc(html))
    try:
        n = helper.select(tree, path)
    except ValueError as e:
        m = re.search(r"요소 (\d+)개", str(e))
        return "ambiguous" if m and int(m.group(1)) > 1 else "none"
    els = body_elements(tree)
    return els.index(n) if n in els else "none"


@pytest.mark.parametrize("c", PATHS, ids=[c["name"] for c in PATHS])
def test_helper_select_follows_paths_fixture(c):
    assert helper_resolve(c["html"], c["path"]) == c["expect"]


def _attr(c):
    return c.get("attr", "href")


def _ids(cases):
    return [f'{_attr(c)}={c["href"]}' for c in cases]


def build_side(c):
    """화면 원문 → _Links 가 뽑은 링크 → link_target (판의 선·연결 목록이 쓰는 길)."""
    p = build_canvas._Links()
    p.feed('<a %s="%s">x</a>' % (_attr(c), c["href"].replace("&", "&amp;").replace('"', "&quot;"))); p.close()
    assert len(p.out) == 1, p.out
    return build_canvas.link_target(p.out[0][0])


@pytest.mark.parametrize("c", LINKS, ids=_ids(LINKS))
def test_build_canvas_follows_links_fixture(c):
    assert build_side(c) == c["to"]


@pytest.mark.parametrize("c", LINKS, ids=_ids(LINKS))
def test_helper_link_to_follows_links_fixture(c):
    assert helper._link_to({_attr(c): c["href"]}) == c["to"]


def test_screen_links_drops_self_and_unknown(tmp_path):
    """규칙 위의 거름(부르는 쪽): 자기 자신·없는 화면은 판의 선이 되지 않는다."""
    (tmp_path / "a.html").write_text('<a href="a.html">me</a><a href="sub/../b.html">b</a><a href="zz.html">z</a>', encoding="utf-8")
    assert build_canvas.screen_links(tmp_path, {"id": "a", "file": "a.html"}, {"a", "b"}) == [{"to": "b", "text": "b"}]
