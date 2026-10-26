"""그림 카드(R18 1단계) 찍기 Model — modules/snapshot.js 순수 함수 단위 테스트(node). 브라우저 없음.

크기·밀도·4096 상한 · 찍을 수 없는 문서의 까닭(다른 출처·file://·내린 카드·실리는 중) · 요소 지도에 넣을 요소와 모양(palette.js 경로, 정수 상자) ·
계산된 스타일 줄이기(이어받는 속성 = 부모와 다를 때, 나머지 = 기본값과 다를 때) · url 고르기·바꾸기 · @import·@font-face 읽기 · 실린 글꼴만 고르기 · 판 바탕 · 판정.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/snapshot.js', 'utf8'), {filename: 'snapshot.js'});
const S = globalThis.HD.snapshot, out = {};
out.consts = [S.MAX, S.MAX_ELEMENTS];
out.size1 = S.size(375, 812, 1);
out.size2 = S.size(375, 812, 2);
out.size3 = S.size(375, 812, 3);
out.capped = S.size(1440, 3000, 2);
out.cappedMax = S.size(375, 812, 2, 1000);
out.sizeBad = [S.size(0, 812, 1), S.size('x', 812, 1)];
out.reach = [
  S.reach({doc: false, protocol: 'file:'}), S.reach({doc: false, protocol: 'http:'}),
  S.reach({doc: true, frameSrc: '', href: 'about:blank', ready: 'complete'}),
  S.reach({doc: true, frameSrc: 'a.html', href: 'about:blank', ready: 'complete'}),
  S.reach({doc: true, frameSrc: 'a.html', href: 'http://h/a.html', ready: 'interactive'}),
  S.reach({doc: true, frameSrc: 'a.html', href: 'http://h/a.html', ready: 'complete'})];
const P = (o) => S.pickable(Object.assign({tag: 'div', hd: false, w: 10, h: 10, hidden: false, x: 0, y: 0, vw: 375, vh: 812}, o));
out.pick = {div: P({}), html: P({tag: 'html'}), body: P({tag: 'BODY'}), script: P({tag: 'script'}), hd: P({hd: true}), hidden: P({hidden: true}),
            zero: P({w: 0}), below: P({y: 812}), right: P({x: 375}), above: P({y: -10, h: 10}), partly: P({y: -5, h: 10}), svgPath: P({tag: 'path'})};
out.map = S.elementMap([{path: 'a', rect: {x: 1.4, y: 2.6, w: 10.5, h: 3.49}}, {path: null, rect: {}}, {path: 'a', rect: {x: 9, y: 9, w: 9, h: 9}},
                        {path: 'b', rect: {x: 0, y: 0, w: 1, h: 1}}, {path: 'c', rect: {x: 0, y: 0, w: 1, h: 1}}], 2);
const names = ['color', 'width', 'transition-duration', '--x', 'font-size', 'display'];
out.border = S.styleText(['border-top-style', 'border-top-width', 'outline-width'], ['solid', '0px', '0px'], null, ['none', '0px', '0px']);
out.styleChild = S.styleText(names, ['red', '10px', '1s', '3', '16px', 'block'], ['red', '99px', '0s', '1', '14px', 'flex'], ['black', 'auto', '0s', '0', '16px', 'block']);
out.styleRoot = S.styleText(names, ['red', 'auto', '1s', '3', '16px', 'block'], null, ['red', 'auto', '0s', '0', '16px', 'block']);
out.skip = [S.skipProp('--c-bg'), S.skipProp('animation-name'), S.skipProp('transition'), S.skipProp('color')];
out.skipLogical = ['margin-block-start', 'padding-inline-end', 'border-inline-start-width', 'inset-block', 'border-start-end-radius', 'inline-size', 'scroll-margin-top', 'user-select'].filter(n => !S.skipProp(n));
out.keepPhysical = ['margin-top', 'padding-left', 'border-left-width', 'top', 'border-top-right-radius', 'width', 'scrollbar-gutter', 'x', 'd', 'stop-color', 'display', 'content'].filter(n => S.skipProp(n));
const css = 'a{background:url("/x.png")} b{mask:url(\'y.svg\') , url(data:image/png;base64,AA)} c{background-image:url( z.webp )} d{background:url("/x.png")}';
out.urls = S.urls(css);
out.swap = S.swapUrls('a{background:url("/x.png") no-repeat} c{background:url(z.webp)} e{background:url(q.png)}', {'/x.png': 'data:A', 'z.webp': 'data:B'});
out.imports = S.imports("@import url('https://cdn.x/p.min.css'); @import \"rel/a.css\" screen; a{}", 'http://h/out/tokens.css');
const ff = `@font-face{font-family:"Pretendard";font-weight:400;font-style:normal;src:url(./woff2/P-Regular.woff2) format("woff2"),url(./woff/P-Regular.woff) format('woff')}
@font-face { font-family: Pretendard; font-weight: 700; src: url('./woff2/P-Bold.woff2') format('woff2'); }
@font-face{font-family:'Noto';font-style:italic;font-weight:normal;unicode-range:U+0000-00FF, U+0131;src:url(n.woff2)}`;
out.faces = S.fontFaces(ff, 'https://cdn.x/dist/p.css');
out.used = S.usedFaces(out.faces, [{family: '"Pretendard"', weight: 'bold', slant: 'normal', range: 'U+0-10FFFF'},
                                   {family: 'Noto', weight: '400', slant: 'italic', range: 'U+0-FF, U+131'}]).map(f => f.family + ' ' + f.weight);
out.usedNone = S.usedFaces(out.faces, [{family: 'Pretendard', weight: '300', slant: 'normal', range: ''}]).length;
out.faceCss = S.faceCss(out.faces[2], 'data:font/woff2;base64,AA');
out.bg = [S.canvasBg('rgb(1, 2, 3)', 'rgb(4, 5, 6)'), S.canvasBg('rgba(0, 0, 0, 0)', 'rgb(4, 5, 6)'), S.canvasBg('transparent', 'rgba(0, 0, 0, 0)')];
const L = (top, h) => ({top, height: h, width: 10});
out.oneLine = [S.oneLine([L(10, 20), L(12, 16), L(10, 20)]), S.oneLine([L(10, 20), L(30, 20)]), S.oneLine([]), S.oneLine([L(10, 20), {top: 50, height: 0, width: 0}])];
out.skipBackdrop = S.skipProp('backdrop-filter');
out.svg = S.svg(375, 812, 750, 1624, '<div/>');
out.verdict = [S.verdict([]), S.verdict([{kind: 'image', url: 'http://o/a.png', why: 'CORS'}])];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-snapshot-"))
    try:
        (tmp / "s.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "s.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_size_density_and_cap(out):
    assert out["consts"] == [4096, 3000]
    assert out["size1"] == {"w": 375, "h": 812, "density": 1, "scale": 1, "pw": 375, "ph": 812, "capped": False}
    assert (out["size2"]["pw"], out["size2"]["ph"], out["size2"]["scale"]) == (750, 1624, 2)
    assert out["size3"]["density"] == 1, "1·2 말고는 1"
    c = out["capped"]
    assert c["capped"] and c["ph"] == 4096 and c["pw"] == int(1440 * 4096 / 3000), c
    assert out["cappedMax"]["ph"] == 1000 and out["cappedMax"]["capped"]
    assert all(s.get("error") == "size" for s in out["sizeBad"])


def test_reach_names_why_a_card_cannot_be_captured(out):
    file_, cross, blank, unloaded, loading, ok = out["reach"]
    assert file_["code"] == "unreachable" and "file://" in file_["why"]
    assert cross["code"] == "unreachable" and "file://" not in cross["why"]
    assert blank["code"] == "unloaded" and unloaded["code"] == "unloaded"
    assert loading["code"] == "loading"
    assert ok is None


def test_pickable_any_visible_element_inside_the_card(out):
    p = out["pick"]
    assert p["div"] and p["svgPath"] and p["partly"]
    assert not any(p[k] for k in ("html", "body", "script", "hd", "hidden", "zero", "below", "right", "above")), p


def test_element_map_shape(out):
    assert out["map"] == [{"path": "a", "rect": {"x": 1, "y": 3, "w": 11, "h": 3}}, {"path": "b", "rect": {"x": 0, "y": 0, "w": 1, "h": 1}}]


def test_style_text_inherited_vs_default(out):
    # 자식: color 는 부모와 같아 뺌, width 는 기본값(auto)과 달라 씀, font-size 는 부모(14px)와 달라 씀, display 는 기본값과 같아 뺌, 애니메이션·변수는 늘 뺌
    assert out["styleChild"] == "width:10px;font-size:16px"
    # 뿌리: 이어받는 속성은 늘 씀
    assert out["styleRoot"] == "color:red;font-size:16px"
    assert out["skip"] == [True, True, True, False]
    assert out["skipLogical"] == [] and out["keepPhysical"] == [], (out["skipLogical"], out["keepPhysical"])
    # 선 굵기는 기본값과 같아도 쓴다 — 모양만 쓰면 굵기가 medium(3px)로 돌아간다
    assert out["border"] == "border-top-style:solid;border-top-width:0px;outline-width:0px"


def test_urls_found_once_and_swapped(out):
    assert out["urls"] == ["/x.png", "y.svg", "z.webp"]
    assert out["swap"] == 'a{background:url("data:A") no-repeat} c{background:url("data:B")} e{background:url(q.png)}'


def test_imports_and_font_faces(out):
    assert out["imports"] == ["https://cdn.x/p.min.css", "http://h/out/rel/a.css"]
    f = out["faces"]
    assert [x["family"] for x in f] == ["Pretendard", "Pretendard", "Noto"]
    assert f[0]["src"] == [{"url": "https://cdn.x/dist/woff2/P-Regular.woff2", "format": "woff2"}, {"url": "https://cdn.x/dist/woff/P-Regular.woff", "format": "woff"}]
    assert (f[1]["weight"], f[1]["slant"]) == ("700", "normal")
    assert (f[2]["slant"], f[2]["range"]) == ("italic", "U+0000-00FF, U+0131")


def test_only_loaded_faces_are_inlined(out):
    assert out["used"] == ["Pretendard 700", "Noto normal"]
    assert out["usedNone"] == 0
    assert out["faceCss"] == '@font-face{font-family:"Noto";font-weight:normal;font-style:italic;unicode-range:U+0000-00FF, U+0131;src:url("data:font/woff2;base64,AA")}'


def test_canvas_background_like_css(out):
    assert out["bg"] == ["html", "body", None]


def test_svg_wrapper_and_verdict(out):
    assert out["svg"] == ('<svg xmlns="http://www.w3.org/2000/svg" width="750" height="1624" viewBox="0 0 375 812">'
                          '<foreignObject x="0" y="0" width="375" height="812"><div/></foreignObject></svg>')
    ok, bad = out["verdict"]
    assert ok == {"ok": True, "lines": []}
    assert bad["ok"] is False and bad["lines"] == ["image http://o/a.png — CORS"]


def test_one_line_text_keeps_one_line(out):
    # 라이브에서 한 줄(상자 가운데가 모두 첫 상자 높이 안)이면 줄바꿈을 끈다 — 두 줄·빈 것은 그대로, 크기 0 상자는 셈하지 않음
    assert out["oneLine"] == [True, False, False, True]
    assert out["skipBackdrop"] is True
