"""캔버스 모듈(canvas/*.js) — Model·ViewModel 순수 함수 단위 테스트(node). 브라우저 없음.

graph.js · route.js · labels.js · focus.js · prefs.js 를 순서대로 node 에서 읽어 확인한다.
D 는 runs/gym-v2/out 임시 복사본을 build_canvas.py 로 만든 index.html 의 hd-data 에서 꺼낸다.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "canvas"
REPO = SCRIPTS.parents[3]
GYM = REPO / "runs" / "gym-v2" / "out"
PURE = ["graph", "route", "labels", "focus", "prefs"]
NODE = shutil.which("node")

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const [dir, names, inPath] = [process.argv[2], process.argv[3].split(','), process.argv[4]];
for (const n of names) vm.runInThisContext(fs.readFileSync(dir + '/' + n + '.js', 'utf8'), {filename: n + '.js'});
const HD = globalThis.HD, F = HD.focus, out = {};
const input = JSON.parse(fs.readFileSync(inPath, 'utf8'));

// 1. graph.fromData
const g = HD.graph.fromData(input.D);
out.flow = HD.graph.edgesFrom(g, null, 'flow').length;
out.flowKinds = [...new Set(g.edges.map(e => e.kind))];
out.screens = g.screens.length;
out.sameAsArrows = JSON.stringify(g.edges.map(e => [e.from, e.to, e.label])) === JSON.stringify((input.D.arrows || []).map(a => [a.from, a.to, a.label || '']));

// 2. addLinks 교체 · groupByTarget
const L1 = [{to: 'b', path: 'p1', text: 't1', rect: {x: 0, y: 0, w: 1, h: 1}}, {to: 'c', path: 'p2', text: 't2', rect: {x: 0, y: 5, w: 1, h: 1}}];
const L2 = [{to: 'c', path: 'q1', text: 'u1', rect: {x: 0, y: 0, w: 1, h: 1}}, {to: 'b', path: 'q2', text: 'u2', rect: {x: 0, y: 1, w: 1, h: 1}},
            {to: 'c', path: 'q3', text: 'u3', rect: {x: 0, y: 2, w: 1, h: 1}}];
let g2 = HD.graph.addLinks(g, 'a', L1);
g2 = HD.graph.addLinks(g2, 'a', L2);
g2 = HD.graph.addLinks(g2, 'z', L1);
const la = HD.graph.edgesFrom(g2, 'a', 'link');
out.linkCountA = la.length;
out.linkPathsA = la.map(e => e.via.path);
out.linkCountZ = HD.graph.edgesFrom(g2, 'z', 'link').length;
out.flowAfter = HD.graph.edgesFrom(g2, null, 'flow').length;
out.groups = HD.graph.groupByTarget(la).map(x => [x.to, x.k, x.edges.map(e => e.via.path)]);

// 3. focus.reduce 와 cycleNext
out.cycle = {};
for (const n of [1, 3, 5]) {
  const links = []; for (let i = 0; i < n; i++) links.push({to: 't' + i, path: 'p' + i, text: 'x' + i, rect: {x: 0, y: i, w: 1, h: 1}});
  const m = F.assignColors(links, '', F.LINK_COLORS); m.from = 'src';
  let s = F.reduce(F.reduce(F.initial(), {type: 'focus', id: 'src'}), {type: 'links', links: m});
  const got = [F.deriveView(m, s).stage], want = [F.deriveView(m, s).stage];
  let w = want[0];
  for (let i = 0; i < 2 * n + 3; i++) {
    s = F.reduce(s, {type: 'cycle'}); got.push(F.deriveView(m, s).stage);
    w = F.cycleNext(w, n); want.push(w);
  }
  out.cycle[n] = {got, want};
}
{
  const links = [0, 1, 2].map(i => ({to: 't' + i, path: 'p' + i, text: 'x' + i, rect: {x: 0, y: i, w: 1, h: 1}}));
  const m = F.assignColors(links, '', F.LINK_COLORS); m.from = 'src';
  let s = F.reduce(F.reduce(F.initial(0.5), {type: 'focus', id: 'src'}), {type: 'links', links: m});
  s = F.reduce(s, {type: 'cycle'});                       // 단계 2
  const t = F.reduce(s, {type: 'toggle', k: 0});
  out.toggle = {on: t.on, visible: F.deriveView(m, t).visible, before: F.deriveView(m, s).visible, hover: t.hover};
  const t2 = F.reduce(t, {type: 'cycle'});
  out.cycleClearsManual = t2.on === null;
  const h = F.reduce(t, {type: 'hover', k: 1});
  out.hoverSame = F.reduce(h, {type: 'hover', k: 1}) === h;
  const x = F.reduce(h, {type: 'exitFocus'});
  out.exit = {focusId: x.focusId, links: x.links, stage: x.stage, on: x.on, hover: x.hover, sat: x.sat};
  const i0 = F.initial(); out.cycleNoLinksSame = F.reduce(i0, {type: 'cycle'}) === i0;
  out.sat = [F.reduce(i0, {type: 'setSat', v: '5'}).sat, F.reduce(i0, {type: 'setSat', v: '0'}).sat, F.reduce(i0, {type: 'setSat', v: '0.5'}).sat];
}

// 4. prefs
const mk = o => k => (k in o ? o[k] : null);
out.prefs = {
  migrate: HD.prefs.load(mk({'hd-arrows': '0', 'hd-link-sat': '0.5'})),
  fresh: HD.prefs.load(mk({})),
  badLegacy: HD.prefs.load(mk({'hd-arrows': 'x', 'hd-link-sat': '9'})),
  badJson: HD.prefs.load(mk({'hd-canvas-prefs': '{bad', 'hd-arrows': '0'})),
  badFields: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 1, arrows: 'no', sat: 5}), 'hd-arrows': '0', 'hd-link-sat': '0.5'})),
  stored: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 1, arrows: false, sat: 1.1}), 'hd-arrows': '1'})),
  throws: HD.prefs.load(() => { throw new Error('denied'); }),
};
const writes = {};
HD.prefs.save({v: 1, arrows: false, sat: 0.5}, (k, v) => { writes[k] = v; });
out.prefs.writes = writes;
console.log(JSON.stringify(out));
"""


def gym_data():
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-mod-"))
    try:
        out = tmp / "out"
        shutil.copytree(GYM, out)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8", env=env)
        assert r.returncode == 0, r.stderr
        html = (out / "index.html").read_text(encoding="utf-8")
        m = re.search(r'<script id="hd-data" type="application/json">(.*?)</script>', html, re.S)
        assert m, "hd-data 없음"
        D = json.loads(m.group(1).replace("<\\!--", "<!--"))
        screens = json.loads((out / "screens.json").read_text(encoding="utf-8"))
        assert "<!-- hd-modules -->" not in html and "data-hd-module=\"view-links\"" in html
        return D, screens, html
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="module")
def res():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음 — canvas/*.js 단위 테스트는 node 로 돌린다")
    if not GYM.exists():
        pytest.skip(f"fixture 없음: {GYM}")
    D, screens, html = gym_data()
    tmp = Path(tempfile.mkdtemp(prefix="hd-canvas-mod-js-"))
    try:
        (tmp / "h.js").write_text(HARNESS, encoding="utf-8")
        (tmp / "in.json").write_text(json.dumps({"D": D}, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "h.js"), str(MOD), ",".join(PURE), str(tmp / "in.json")], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out["_branches"] = sum(len(s.get("branches") or []) for s in screens["screens"])
    out["_html"] = html
    return out


def test_graph_from_data(res):
    assert res["flow"] == res["_branches"] == 9
    assert res["flowKinds"] == ["flow"] and res["sameAsArrows"]
    assert res["screens"] == 28


def test_add_links_replaces_and_groups(res):
    assert res["linkCountA"] == 3 and res["linkPathsA"] == ["q1", "q2", "q3"]   # 두 번째 답이 첫 답을 바꿔 낌
    assert res["linkCountZ"] == 2 and res["flowAfter"] == 9
    assert res["groups"] == [["c", 0, ["q1", "q3"]], ["b", 1, ["q2"]]]


def test_focus_reducer(res):
    for n in ("1", "3", "5"):
        assert res["cycle"][n]["got"] == res["cycle"][n]["want"], n
    assert res["cycle"]["3"]["got"][:6] == [1, 2, 3, 0, 1, 2]
    assert res["cycle"]["1"]["got"] == [0] * len(res["cycle"]["1"]["got"])
    t = res["toggle"]
    assert t["before"] == [False, True, False]
    assert t["on"] == {"0": True, "1": True, "2": False} and t["visible"] == [True, True, False] and t["hover"] is None
    assert res["cycleClearsManual"] and res["hoverSame"] and res["cycleNoLinksSame"]
    assert res["exit"] == {"focusId": None, "links": None, "stage": 1, "on": None, "hover": None, "sat": 0.5}
    assert res["sat"] == [1.2, 0.7, 0.5]


def test_prefs(res):
    p = res["prefs"]
    assert p["migrate"] == {"v": 1, "arrows": False, "sat": 0.5}
    assert p["fresh"] == {"v": 1, "arrows": True, "sat": 0.7}
    assert p["badLegacy"] == {"v": 1, "arrows": True, "sat": 0.7}
    assert p["badJson"] == {"v": 1, "arrows": False, "sat": 0.7}
    assert p["badFields"] == {"v": 1, "arrows": True, "sat": 0.7}
    assert p["stored"] == {"v": 1, "arrows": False, "sat": 1.1}
    assert p["throws"] == {"v": 1, "arrows": True, "sat": 0.7}
    assert list(p["writes"]) == ["hd-canvas-prefs"] and json.loads(p["writes"]["hd-canvas-prefs"]) == {"v": 1, "arrows": False, "sat": 0.5}


FORBIDDEN = re.compile(r"\bdocument\b|\bwindow\.|querySelector|\.style\b|localStorage|postMessage")


@pytest.mark.parametrize("name", PURE)
def test_purity(name):
    src = (MOD / f"{name}.js").read_text(encoding="utf-8")
    assert "globalThis.HD = globalThis.HD || {}" in src
    hits = FORBIDDEN.findall(src)
    assert not hits, f"{name}.js: {hits}"


def test_single_file_output(res):
    html = res["_html"]
    for n in ["graph", "route", "labels", "focus", "prefs", "view-links"]:
        assert f'data-hd-module="{n}"' in html
    order = [html.index(f'data-hd-module="{n}"') for n in ["graph", "route", "labels", "focus", "prefs", "view-links"]]
    assert order == sorted(order) and order[-1] < html.index("// ── Canvas shell")
    assert not re.search(r"<script[^>]+\bsrc=", html), "외부 스크립트 참조 없음"
