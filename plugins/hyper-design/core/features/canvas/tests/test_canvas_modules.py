"""캔버스 모듈(modules/*.js) — Model·ViewModel 순수 함수 단위 테스트(node). 브라우저 없음.

graph.js · route.js · style.js · camera.js · prefs.js 를 순서대로 node 에서 읽어 확인한다.
D 는 runs/gym-v2/out 임시 복사본을 build_canvas.py 로 만든 index.html 의 hd-data 에서 꺼낸다.
"""
import colorsys, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
REPO = SCRIPTS.parents[4]
GYM = REPO / "runs" / "gym-v2" / "out"
sys.path.insert(0, str(SCRIPTS))
from build_canvas import MODULES as ALL_MODULES   # 빌드가 끼워 넣는 순서 그대로 — 따로 적어 두면 어긋난다
sys.path.pop(0)
# 층 표(책임 게이트) — view-* 가 아닌 모듈은 모두 여기 있어야 한다. 순수성 검사는 이 표의 Model·ViewModel 전부
LAYER = {"graph": "Model", "route": "Model", "style": "Model", "camera": "Model", "edits": "Model", "notes": "Model", "layers": "Model", "theme": "Model", "viewport": "Model", "busy": "Model", "line-ends": "Model", "caption": "Model", "align": "Model", "folders": "Model",
         "tools": "ViewModel", "dock": "ViewModel", "prefs": "ViewModel", "selection": "ViewModel", "history": "ViewModel"}
PURE = [n for n in ALL_MODULES if n in LAYER]
NODE = shutil.which("node")

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const [dir, names, inPath] = [process.argv[2], process.argv[3].split(','), process.argv[4]];
for (const n of names) vm.runInThisContext(fs.readFileSync(dir + '/' + n + '.js', 'utf8'), {filename: n + '.js'});
const HD = globalThis.HD, out = {};
const input = JSON.parse(fs.readFileSync(inPath, 'utf8'));

// 1. graph.fromData
const g = HD.graph.fromData(input.D);
out.flow = HD.graph.edgesFrom(g, null, 'flow').length;
out.flowKinds = [...new Set(g.edges.map(e => e.kind))];
out.linkEdges = HD.graph.edgesFrom(g, null, 'link').length; out.linkData = Object.values(input.D.links || {}).reduce((n, l) => n + l.length, 0);
out.screens = g.screens.length;
out.sameAsArrows = JSON.stringify(g.edges.filter(e => e.kind === 'flow').map(e => [e.from, e.to, e.label])) === JSON.stringify((input.D.arrows || []).map(a => [a.from, a.to, a.label || '']));

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

// 4. prefs (v2: 색 프리셋 · 랜덤 · 쌍 색 · 굵기 · 움직임, v1 sat 는 버림)
const mk = o => k => (k in o ? o[k] : null);
const RS = ['#AA3344', '#33AA44', '#3344AA', '#AAAA33', '#33AAAA', '#AA33AA'];
out.prefs = {
  migrate: HD.prefs.load(mk({'hd-arrows': '0', 'hd-link-sat': '0.5'})),
  fresh: HD.prefs.load(mk({})),
  badJson: HD.prefs.load(mk({'hd-canvas-prefs': '{bad', 'hd-arrows': '0'})),
  v1: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 1, arrows: false, sat: 1.1}), 'hd-arrows': '1'})),
  v2: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 2, arrows: false, preset: 'random', rand: RS, custom: {'a>b': '#ABCDEF'}, width: 4.5, motion: false})})),
  stored: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 3, lines: false, op: 0.3, preset: 'deep', custom: {}, width: 4, motion: true})})),
  badFields: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 3, lines: 'no', op: 9, preset: 'random', rand: [1], custom: {x: '#ABCDEF', 'a>b': 'red', 'c>d': '#123456'}, width: 9, motion: 'x'})})),
  throws: HD.prefs.load(() => { throw new Error('denied'); }),
};
const writes = {};
HD.prefs.save({v: 1, arrows: false, sat: 0.5, width: 5, op: 0.01}, (k, v) => { writes[k] = v; });
out.prefs.writes = writes;

// 5. 카메라 계획(S4)
{
  const C = HD.camera, T = {x: 2000, y: 100, w: 375, h: 812}, from = {x: 300, y: 400};
  const view = {w: 1200, h: 800, z: 0.5, tx: 10, ty: 20}, small = {w: 1200, h: 500, z: 0.9, tx: 0, ty: 0};
  const ease = C.parseEase('cubic-bezier(0.22, 1, 0.36, 1)');
  const fits = C.plan(from, T, view, {centre: 250, glide: 600});
  out.camera = {fits, big: C.plan(from, T, small, {centre: 250, glide: 600}), red: C.plan(from, T, view, {centre: 250, glide: 600, reduced: true}),
                mid: C.at(fits, 700, ease, view), end: C.at(fits, 1e6, ease, view), e: [ease(0), ease(0.25), ease(0.5), ease(1)], ms: [C.ms('250ms'), C.ms('0.6s'), C.ms('x', 9)]};
}
// 6. 선 색(S5): 쌍 색 > 프리셋 · 강조색 건너뛰기(프리셋마다) · 랜덤(시드 RNG)
{
  const S = HD.lineStyle;
  let seed = 7; const rng = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const rs = S.randomSet(rng), rs2 = S.randomSet(rng);
  const pc = {preset: 'deep', rand: null, custom: {'a>b': '#123456'}};
  out.colour = {custom: S.colourOf(pc, 'a', {to: 'b', k: 0}, ''), preset: S.colourOf(pc, 'a', {to: 'c', k: 1}, ''), otherSrc: S.colourOf(pc, 'x', {to: 'b', k: 0}, ''),
                deep: S.PRESETS.deep.c, rand: rs, rand2: rs2, skip: {}};
  for (const k of ['calm', 'vivid', 'pastel', 'deep', 'random']) {
    const p = {preset: k, rand: rs, custom: {}}, acc = S.paletteOf(p)[0];
    out.colour.skip[k] = {acc, cols: [0, 1, 2, 3, 4, 5, 6, 7].map(i => S.colourOf(p, 's', {to: 't' + i, k: i}, acc))};
  }
}
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
        pytest.skip("node 가 PATH 에 없음 — modules/*.js 단위 테스트는 node 로 돌린다")
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
    assert res["flowKinds"] == ["flow", "link"] and res["sameAsArrows"]
    assert res["linkEdges"] == res["linkData"] > 0, "빌드가 화면 파일에서 뽑은 링크(D.links) = 그래프의 link 간선"
    assert res["screens"] == 28


def test_add_links_replaces_and_groups(res):
    assert res["linkCountA"] == 3 and res["linkPathsA"] == ["q1", "q2", "q3"]   # 두 번째 답이 첫 답을 바꿔 낌
    assert res["linkCountZ"] == 2 and res["flowAfter"] == 9
    assert res["groups"] == [["c", 0, ["q1", "q3"]], ["b", 1, ["q2"]]]


DEF = {"v": 3, "lines": True, "op": 0.55, "preset": "calm", "rand": None, "custom": {}, "width": 2.5, "motion": True}


def test_prefs(res):
    """v3: 늘 그리는 선 보이기(lines)·투명도(op, 0.15–1). 주요 흐름(arrows, v2)·sat(v1)·예전 키(hd-arrows)는 버린다(D9)."""
    p = res["prefs"]
    assert p["migrate"] == DEF and p["fresh"] == DEF and p["throws"] == DEF and p["badJson"] == DEF and p["v1"] == DEF
    assert p["v2"] == dict(DEF, preset="random", rand=["#AA3344", "#33AA44", "#3344AA", "#AAAA33", "#33AAAA", "#AA33AA"],
                           custom={"a>b": "#ABCDEF"}, width=4.5, motion=False), "v2 → v3: 색·굵기·움직임은 옮기고 arrows 는 버림"
    assert p["stored"] == dict(DEF, lines=False, op=0.3, preset="deep", width=4)
    assert p["badFields"] == dict(DEF, op=1, custom={"c>d": "#123456"})              # 틀린 값은 기본값, op 는 범위 안으로
    assert list(p["writes"]) == ["hd-canvas-prefs"] and json.loads(p["writes"]["hd-canvas-prefs"]) == dict(DEF, width=5, op=0.15)


def test_camera_plan(res):
    """S4: 키프레임 시간은 늘 커지고, 끝은 정확히 대상 카드 가운데. 대상이 들어가면 배율 그대로, 안 들어가면 그만큼만 축소. reduced → 하나."""
    c = res["camera"]
    T = (2000 + 375 / 2, 100 + 812 / 2)
    for keys, vw, vh in ((c["fits"], 1200, 800), (c["big"], 1200, 500)):
        ts = [k["t"] for k in keys]
        assert ts == sorted(ts) and len(set(ts)) == len(ts) and ts[0] == 0 and ts[-1] == 850, ts
        e = keys[-1]
        assert abs(T[0] * e["z"] + e["tx"] - vw / 2) < 1e-6 and abs(T[1] * e["z"] + e["ty"] - vh / 2) < 1e-6, e
        m = keys[1]                                                                 # 1단계: 출발 요소를 가운데(배율 그대로)
        assert abs(300 * m["z"] + m["tx"] - vw / 2) < 1e-6 and abs(400 * m["z"] + m["ty"] - vh / 2) < 1e-6 and m["z"] == keys[0]["z"]
    assert all(k["z"] == 0.5 for k in c["fits"])                                     # 들어감 → 배율 그대로
    assert abs(c["big"][-1]["z"] - (500 - 48) / 812) < 1e-9 and c["big"][0]["z"] == 0.9   # 안 들어감 → 들어갈 만큼만 축소
    assert len(c["red"]) == 1 and c["red"][0] == dict(c["fits"][-1], t=0)
    assert c["end"] == {k: c["fits"][-1][k] for k in ("z", "tx", "ty")}
    assert c["e"][0] == 0 and c["e"][3] == 1 and 0.5 < c["e"][1] < c["e"][2] < 1    # smooth-out: 앞에서 빠르게
    assert c["ms"] == [250, 600, 9]


def _hue(hx):
    r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l


def test_line_colours(res):
    """S5: colourOf 우선순위 custom > preset · 모든 프리셋(랜덤 포함)에서 강조색 ±30° 건너뜀 · randomSet(시드) 6–8 개 다른 색상각 · 채도/밝기 범위."""
    c = res["colour"]
    assert c["custom"] == "#123456" and c["preset"] == c["deep"][1] and c["otherSrc"] == c["deep"][0]
    for k, v in c["skip"].items():
        ah = _hue(v["acc"])[0]
        for col in v["cols"]:
            gap = abs(_hue(col)[0] - ah) % 360
            assert min(gap, 360 - gap) >= 30, (k, v["acc"], col)
    for rs in (c["rand"], c["rand2"]):
        assert 6 <= len(rs) <= 8 and len(set(rs)) == len(rs)
        hs = [_hue(x) for x in rs]
        assert len({round(h) for h, _, _ in hs}) == len(rs)
        for h, s, l in hs:
            assert 0.33 <= s <= 0.47 and 0.41 <= l <= 0.51, (h, s, l)
    assert c["rand"] != c["rand2"]


FORBIDDEN = re.compile(r"\bdocument\b|\bwindow\.|querySelector|\.style\b|localStorage|postMessage")


@pytest.mark.parametrize("name", PURE)
def test_purity(name):
    src = (MOD / f"{name}.js").read_text(encoding="utf-8")
    assert "globalThis.HD = globalThis.HD || {}" in src
    hits = FORBIDDEN.findall(src)
    assert not hits, f"{name}.js: {hits}"


def test_purity_covers_every_model():
    """Model·ViewModel 파일은 빠짐없이 순수성 검사를 받는다 — view-* 가 아닌 모듈이 층 표에 없으면 실패."""
    on_disk = sorted(p.stem for p in MOD.glob("*.js"))
    assert sorted(ALL_MODULES) == on_disk, "modules/*.js 와 build_canvas.MODULES 가 다르다"
    missing = [n for n in ALL_MODULES if not n.startswith("view-") and n not in LAYER]
    assert not missing, f"층 표(LAYER)에 없는 Model/ViewModel: {missing}"
    assert set(PURE) == set(LAYER)


def test_single_file_output(res):
    html = res["_html"]
    for n in ALL_MODULES:
        assert f'data-hd-module="{n}"' in html
    order = [html.index(f'data-hd-module="{n}"') for n in ALL_MODULES]
    assert order == sorted(order) and order[-1] < html.index("// ── Canvas shell")
    assert "/* hd-motion */" not in html and "--duration-fast: 250ms" in html and html.index("--camera-glide-dur") < html.index("</style>")   # motion.css 인라인
    assert not re.search(r"<script[^>]+\bsrc=", html), "외부 스크립트 참조 없음"


EDITS_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/edits.js', 'utf8'), {filename: 'edits.js'});
const E = globalThis.HD.edits, h = {path: 'a.x', text: 'X', rect: {x: 1, y: 2, w: 3, h: 4}}, out = {};
const notes = [E.note('s1', h, 'link', 'link', 's3'), E.note('s1', {path: 'b.y', text: 'Y', rect: null}, 'cut', 'cut', 's2'),
               E.note('s2', h, 'other', 'link', 's1'), Object.assign(E.note('s4', h, 'gone'), {edit: 'delete'}),
               Object.assign(E.note('s1', h, 'txt'), {edit: 'text', value: 'v'}), {id: 'm', screen: 's1', note: 'memo', intent: 'question'}];
out.pd = E.pendingFor(notes, 's1');
out.direct = notes.map(E.directOf);
out.tally = E.tally(notes);
out.ids = new Set(notes.slice(0, 5).map(n => n.id)).size;
out.field = E.say.field('policy', '새 정책', 1);
const sentLink = Object.assign(E.note('s1', h, 'link', 'link', 's5'), {sent: true});
out.pl = [E.pendingLink(notes, 's1', 'a.x', 's3') === notes[0], E.pendingLink(notes, 's1', 'a.x', 's2'), E.pendingLink(notes, 's1', 'b.y', 's2'),
          E.pendingLink([sentLink], 's1', 'a.x', 's5')];
console.log(JSON.stringify(out));
"""


def test_edits_model():
    """편집 모델: 반영 대기 계산(출발 화면 기준) · 도우미가 바로 쓸 편집 · 화면별 수 · 글귀."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-edits-js-"))
    try:
        (tmp / "e.js").write_text(EDITS_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "e.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    pd = out["pd"]
    assert pd["byPath"] == {"a.x": {"op": "link", "to": "s3"}, "b.y": {"op": "cut"}}, "s1 에서 나가는 편집만(s2 의 것은 빼고)"
    assert [a["to"] for a in pd["adds"]] == ["s3"] and pd["cutIn"] == {"s4": 1}, "삭제한 화면으로 오는 선은 모두 끊긴 것으로"
    assert out["direct"] == [True, True, True, False, True, False], "잇기·끊기·글자는 바로 쓰고, 삭제·메모는 터미널로"
    assert out["tally"] == {"s1": 3, "s2": 1, "s4": 1} and out["ids"] == 5
    assert out["field"] == "정책 2번째 줄을 \"새 정책\"(으)로 바꾸기 (screens.json의 policies[1])"
    assert out["pl"] == [True, None, None, None], "자르면 취소할 편집 = 그 요소·도착의 보내지 않은 잇기만(끊기·보낸 것은 아님)"


DOCK_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/dock.js', 'utf8'), {filename: 'dock.js'});
const K = globalThis.HD.dock, R = K.reduce, out = {};
const tabs = s => s.groups.map(g => g.tabs.join('+') + ':' + g.active).join(' | ');
out.allDefaults = tabs(K.defaults());
const pre = {v: 1, groups: [{tabs: ['links'], active: 'links'}, {tabs: ['show'], active: 'show'}, {tabs: ['notes', 'pending', 'history', 'layers'], active: 'notes'}], closed: ['theme']};
out.oldSaved = tabs(K.normalize(pre));                                        // 정렬 패널 전 저장 상태 → 표시 옆에
out.oldNoShow = tabs(K.normalize(Object.assign({}, pre, {groups: pre.groups.slice(2), closed: ['theme', 'links', 'show']})));   // 표시가 닫혀 있으면 마지막 묶음에
K.PANELS.splice(K.PANELS.indexOf('pending'), 2);   // 아래 배치 동작 확인은 패널 넷으로(모델은 같은 배열을 쓴다)
K.PANELS.splice(K.PANELS.indexOf('align'), 1);
const base = K.normalize({v: 1, groups: [{tabs: ['links', 'show'], active: 'links'}, {tabs: ['notes', 'layers'], active: 'notes'}]});
let s = base;
out.def = tabs(s); out.defaults = tabs(K.defaults());
const s0 = s; s = R(s, {type: 'move', id: 'notes', to: 0}); out.merge = tabs(s); out.pure = tabs(s0);
s = R(s, {type: 'move', id: 'show', to: 'new', at: 1}); out.split = tabs(s);
out.lone = R(s, {type: 'move', id: 'show', to: 'new', at: 0}) === s;
s = R(s, {type: 'close', id: 'layers'}); out.closeHidden = tabs(s) + ' / ' + s.closed.join(',');
s = R(s, {type: 'close', id: 'show'}); out.closeStyle = tabs(s);
s = R(R(s, {type: 'collapse', on: true}), {type: 'activate', id: 'show'}); out.reopen = tabs(s) + ' / ' + s.closed.join(',') + ' / ' + s.collapsed;
out.w = [R(s, {type: 'width', w: 9999}).w, R(s, {type: 'width', w: 10}).w, R(s, {type: 'width', w: 333.4}).w];
out.hs = R(R(s, {type: 'move', id: 'show', to: 'new'}), {type: 'heights', hs: [2, 0.5]}).groups.map(g => g.h);
out.hsBad = R(s, {type: 'heights', hs: [1, 1, 1]}) === s;
out.vis = [K.visible(s), K.visible(R(s, {type: 'collapse', on: true}))];
out.norm = tabs(K.normalize({groups: [{tabs: ['zzz', 'notes', 'notes'], active: 'zzz'}], closed: ['links', 'notes'], w: 'x'}));
out.normClosed = K.normalize({groups: [{tabs: ['zzz', 'notes', 'notes'], active: 'zzz'}], closed: ['links', 'notes']}).closed;
let st = {}; K.save(s, (k, v) => { st[k] = v; });
out.round = tabs(K.load(k => st[k])) === tabs(s);
out.bad = [tabs(K.load(() => '{bad')), tabs(K.load(() => null)), tabs(K.load(() => { throw 1; }))];
const ftabs = s => tabs(s) + ' || ' + s.floats.map(f => f.tabs.join('+') + ':' + f.active + '@' + [f.x, f.y, f.w, f.h].join(',')).join(' | ');
let f = R(base, {type: 'move', id: 'notes', to: 'float', x: 100, y: 50}); out.fOut = ftabs(f);
f = R(f, {type: 'move', id: 'layers', to: 'float', fi: 0}); out.fMerge = ftabs(f);
f = R(f, {type: 'float', fi: 0, w: 50, h: 9000, x: 10.6}); out.fRect = ftabs(f);
f = R(f, {type: 'move', id: 'notes', to: 'new'}); out.fBack = ftabs(f);
f = R(f, {type: 'move', id: 'layers', to: 'float', x: 5, y: 6}); out.fLoneMove = ftabs(f);
f = R(R(f, {type: 'collapse', on: true}), {type: 'move', id: 'show', to: 'float', x: 0, y: 0}); out.fVis = K.visible(f); out.fCol = f.collapsed;
f = R(f, {type: 'activate', id: 'layers'}); out.fTop = f.floats.map(x => x.active); out.fCol2 = f.collapsed;
out.oldHidden = tabs(K.normalize({v: 1, groups: [{tabs: ['links', 'hidden'], active: 'hidden'}], closed: []}));   // 조각 4 전 저장 상태
f = R(f, {type: 'close', id: 'show'}); out.fClose = ftabs(f) + ' / ' + f.closed.join(',');
out.fNorm = ftabs(K.normalize({groups: [{tabs: ['links']}], floats: [{tabs: ['links', 'notes', 'q'], x: 'a', w: 10}]}));
st = {}; K.save(f, (k, v) => { st[k] = v; }); out.fRound = ftabs(K.load(k => st[k])) === ftabs(f);
console.log(JSON.stringify(out));
"""


def test_dock_model():
    """오른쪽 패널 도크 배치: 탭 합치기·떼기·닫기·다시 열기·너비·높이·접기·저장 왕복·틀린 값 복구."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-dock-js-"))
    try:
        (tmp / "d.js").write_text(DOCK_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "d.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert out["allDefaults"] == "links:links | show+align:show | notes+pending+history+layers:notes", "기본: 표시 옆에 정렬, 메모·반영 대기·기록·레이어이 한 묶음"
    assert out["oldSaved"] == "links:links | show+align:show | notes+pending+history+layers:notes", "정렬 패널 전 저장 상태도 그대로 열리고 정렬은 표시 옆에"
    assert out["oldNoShow"] == "notes+pending+history+layers+align:notes", "표시가 닫혀 있으면 정렬은 마지막 묶음에"
    assert out["def"] == "links+show:links | notes+layers:notes"
    assert out["merge"] == "links+show+notes:notes | layers:layers", "합치면 그 묶음 끝에 들어가 활성"
    assert out["pure"] == out["def"], "reduce 는 원래 상태를 바꾸지 않는다"
    assert out["split"] == "links+notes:notes | show:show | layers:layers", "떼면 그 자리에 새 묶음"
    assert out["lone"], "혼자 있는 탭은 떼어도 그대로"
    assert out["closeHidden"] == "links+notes:notes | show:show / theme,layers", "빈 묶음은 없어진다"
    assert out["closeStyle"] == "links+notes:notes"
    assert out["reopen"] == "links+notes+show:show / theme,layers / false", "닫힌 패널을 부르면 마지막 묶음에 다시 열고 편다"
    assert out["w"] == [560, 220, 333]
    assert out["hs"] == [2, 0.5] and out["hsBad"]
    assert out["vis"] == [["show"], []]
    assert out["norm"] == "notes+show+layers:notes", "모르는 패널·겹친 패널은 버리고 빠진 패널은 마지막 묶음에"
    assert out["normClosed"] == ["links", "theme"]          # 테마는 처음엔 닫힌 패널(조각 5)
    assert out["round"] and out["bad"] == [out["defaults"]] * 3
    # 떠 있는 창(D1): 빼기 · 합치기 · 옮기기/크기(최소) · 도크로 되돌리기 · 혼자 뜬 창 옮기기 · 접어도 보임 · 맨 위로 · 닫기 · 복구 · 저장
    assert out["fOut"] == "links+show:links | layers:layers || notes:notes@100,50,280,320", "도크 묶음에서 빼면 판 위 떠 있는 창"
    assert out["fMerge"] == "links+show:links || notes+layers:layers@100,50,280,320", "떠 있는 창에 합치면 빈 도크 묶음은 없어진다"
    assert out["fRect"] == "links+show:links || notes+layers:layers@11,50,200,9000", "최소 너비 200"
    assert out["fBack"] == "links+show:links | notes:notes || layers:layers@11,50,200,9000", "도크 끝에 끌어 넣으면 새 묶음"
    assert out["fLoneMove"].endswith("layers:layers@5,6,200,9000"), "혼자 뜬 창을 다시 빼면 그 창이 옮겨질 뿐"
    assert out["fVis"] == ["layers", "show"] and out["fCol"], "도크를 접어도 떠 있는 창은 보인다"
    assert out["fTop"] == ["show", "layers"] and out["fCol2"], "누른 떠 있는 창이 맨 위로, 도크는 접힌 채"
    assert out["fClose"] == "links:links | notes:notes || layers:layers@5,6,200,9000 / theme,show"
    assert out["oldHidden"].startswith("links+layers+show+notes") and out["oldHidden"].endswith(":layers"), "예전 숨긴 화면 탭은 그 자리의 레이어 탭으로"
    assert out["fNorm"] == "links+show+layers:links || notes:notes@40,40,200,320", "이미 쓴 패널·모르는 패널 버림, 틀린 좌표는 기본값"
    assert out["fRound"]


def test_ui_chrome_colours_are_neutral_tokens():
    """색 위계(H13): 판 바깥 UI(배지·주 버튼·핀·고른 카드·편집 칸)는 --ui-* 무채색 토큰만 쓴다 — 채도 높은 빨강·파랑이 다시 들어오지 않게."""
    tpl = (SCRIPTS / "canvas_template.html").read_text(encoding="utf-8")
    root = re.search(r":root\{([^}]*)\}", tpl)
    assert root and all(f"--ui-{k}:" in root.group(1) for k in ("primary", "mark", "badge", "danger")), "판 바깥 UI 토큰"
    for sel in (".nbadge{", ".nbtn.pri{", ".pin{", ".card.picked .phone{", "#tools .tb .cnt{", ".pchip{", "#tedit textarea{"):
        rule = tpl[tpl.index(sel):tpl.index("}", tpl.index(sel))]
        assert "var(--ui-" in rule, sel
    for hexv in ("#e5484d", "#F59E0B", "#7cc4ff"):
        assert hexv not in tpl, f"채도 높은 판 바깥 색이 남음: {hexv}"


def test_dock_width_is_not_inherited_by_the_board():
    """P4: --dockw 는 상속하지 않는 속성으로 등록하고, 쓰는 칸만 물려받는다 — 도크 너비를 끌 때 판 전체 스타일을 다시 계산하지 않게."""
    tpl = (SCRIPTS / "canvas_template.html").read_text(encoding="utf-8")
    assert re.search(r"@property --dockw\{[^}]*inherits:false", tpl), "--dockw 는 inherits:false"
    users = set(re.findall(r"([#.][\w-]+)\{[^}]*var\(--dockw", tpl))
    taker = re.search(r"^([^{\n]*)\{--dockw:inherit\}", tpl, re.M)
    assert taker, "쓰는 칸이 --dockw 를 물려받는 줄"
    assert users <= set(taker.group(1).split(",")), (users, taker.group(1))


# ── 책임 게이트(contract.md '책임 게이트') — 한 객체가 다시 커지지 않게, 기능 사이는 의도로만
RANK = {"Model": 0, "ViewModel": 1, "View": 2}
NS = {"lineStyle": "style", "lineEnds": "line-ends"}                          # HD 이름 → 모듈 파일(이름이 다른 것만)


def _layer(name):
    return "View" if name.startswith("view-") else LAYER[name]


def _hd_name(name):
    if name.startswith("view-"):
        return "view" + "".join(p.title() for p in name.split("-")[1:])
    return {v: k for k, v in NS.items()}.get(name, name)


@pytest.mark.parametrize("name", ALL_MODULES)
def test_gate_role_and_direction(name):
    """책임: 머리 주석 첫 줄이 층(Model/ViewModel/View)과 맡은 일 하나를 밝힌다.
    협력: 의존은 아래 층으로만(Model → 다른 층 모름, ViewModel → View 모름), View 끼리는 서로 부르지 않는다(셸이 의도로 잇는다)."""
    src = (MOD / f"{name}.js").read_text(encoding="utf-8")
    me = _layer(name)
    assert re.match(r"/\* (Model|ViewModel|View) — \S", src) and src[3:].startswith(me), f"{name}.js 첫 줄 = '/* {me} — 맡은 일'"
    own = _hd_name(name)
    for dep in sorted(set(re.findall(r"\bHD\.(\w+)", src)) - {own}):
        mod = NS.get(dep, dep)
        if dep.startswith("view") and mod not in LAYER:   # viewport(Model) 처럼 이름만 view 로 시작하는 것은 층 표로
            assert False, f"{name}.js → HD.{dep}: View 끼리 직접 부르지 않는다 — ctx 로 받은 함수·의도로"
        assert mod in LAYER, f"{name}.js → HD.{dep}: 모르는 모듈"
        assert RANK[LAYER[mod]] <= RANK[me] and not (me == "Model" and LAYER[mod] != "Model"), f"{name}.js({me}) → {mod}({LAYER[mod]}): 위 층에 기댐"


SEL_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/selection.js', 'utf8'), {filename: 'selection.js'});
const S = globalThis.HD.selection, R = S.reduce, out = {};
let s = S.initial(); const s0 = s;
s = R(s, {type: 'only', id: 'a'}); out.only = s.ids; out.pure = s0.ids.length === 0;
s = R(s, {type: 'toggle', id: 'b'}); out.add = s.ids; out.pr2 = S.primary(s);
s = R(s, {type: 'toggle', id: 'a'}); out.sub = s.ids; out.pr1 = S.primary(s);
out.set = R(s, {type: 'set', ids: ['x', 'y', 'x', 3]}).ids;
out.drop = R({ids: ['a', 'b', 'c']}, {type: 'drop', ids: ['b']}).ids;
out.clearSame = R(S.initial(), {type: 'clear'}).ids.length === 0;
out.has = [S.has({ids: ['3']}, 3), S.has({ids: []}, 'a')];
console.log(JSON.stringify(out));
"""


def test_selection_model():
    """고르기(E15): 누르기 = 그 카드만 · Shift = 더하기/빼기 · 한 장일 때만 연결 강조 대상(primary) · 숨기거나 지운 카드 빼기."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-sel-js-"))
    try:
        (tmp / "s.js").write_text(SEL_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "s.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert out["only"] == ["a"] and out["pure"]
    assert out["add"] == ["a", "b"] and out["pr2"] is None, "여러 장이면 연결 강조 대상 없음"
    assert out["sub"] == ["b"] and out["pr1"] == "b"
    assert out["set"] == ["x", "y", "3"] and out["drop"] == ["a", "c"] and out["clearSame"]
    assert out["has"] == [True, False]


OV_JS = r"""
const fs = require('fs'), vm = require('vm');
for (const n of ['graph', 'style', 'edits']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + n + '.js', 'utf8'), {filename: n + '.js'});
const G = globalThis.HD.graph, E = globalThis.HD.edits, S = globalThis.HD.lineStyle, out = {};
const g = G.fromData({rows: [], arrows: [{from: 'a', to: 'b'}, {from: 'c', to: 'd', label: '갈래'}],
                      links: {a: [{to: 'b', text: '다음'}, {to: 'b', text: '건너뛰기'}], b: [{to: 'a', text: '이전'}], c: [{to: 'a', text: '처음'}]}});
const sum = ps => ps.map(p => [p.a, p.b, p.ab, p.ba, p.pend, p.plan].join(',')).sort();
out.base = sum(G.overview(g, {}));
out.labels = G.overview(g, {}).find(p => p.a === 'a').labels;
const h = {path: 'x', text: 'X', rect: null};
const add = E.note('a', h, '', 'link', 'd'), re = Object.assign(E.note('c', h, '', 'link', 'b'), {was: 'a'});
const cut1 = E.note('a', h, '', 'cut', 'b'), cut2 = E.note('a', h, '', 'cut', 'b'), cutB = E.note('b', h, '', 'cut', 'a');
out.pd = E.overviewPending([add, re, cut1, cutB]);
out.withPend = sum(G.overview(g, E.overviewPending([add, re])));
out.cutOne = sum(G.overview(g, E.overviewPending([cut1])));
out.cutAll = sum(G.overview(g, E.overviewPending([cut1, cut2, cutB])));
out.cutIn = sum(G.overview(g, E.overviewPending([Object.assign(E.note('a', h, ''), {edit: 'delete'})])));
const P = {preset: 'calm', custom: {}}, pal = S.paletteOf(P);
out.rows = [0, 1, 2, 7, 8, 9].map(r => S.rowColor(P, r)); out.pal = pal;
console.log(JSON.stringify(out));
"""


def test_overview_lines_model():
    """늘 그리는 선(E7·D6b·D6c·D8·E14): 쌍마다 하나(양방향 = ab·ba) · 반영 대기 잇기 = pend · 끊기는 그 방향 링크 수만큼 빼야 사라짐 ·
    도착 바꾸기는 예전 도착을 뺌 · 삭제한 화면으로 오는 선은 모두 뺌 · 화면 안 링크 없는 갈래 = plan · 줄 색은 8색을 돌려 이웃 줄이 다름."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-ov-js-"))
    try:
        (tmp / "o.js").write_text(OV_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "o.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert out["base"] == ["a,b,true,true,false,false", "c,a,true,false,false,false", "c,d,true,false,false,true"], "a↔b 하나 · c→a · c→d 는 기획 갈래"
    assert out["labels"] == ["다음", "건너뛰기", "이전"]
    assert out["pd"] == {"add": [{"from": "a", "to": "d"}, {"from": "c", "to": "b"}], "drop": {"c>a": 1, "a>b": 1, "b>a": 1}, "cutIn": {}}
    assert out["withPend"] == ["a,b,true,true,false,false", "a,d,true,false,true,false", "c,b,true,false,true,false", "c,d,true,false,false,true"], \
        "새 잇기 = 점선 쌍 · 도착 바꾸기 = 예전 도착(c→a) 사라짐"
    assert out["cutOne"] == out["base"], "a→b 링크 둘 중 하나만 끊으면 선은 그대로"
    assert out["cutAll"] == ["a,b,true,false,false,true", "c,a,true,false,false,false", "c,d,true,false,false,true"],         "모두 끊으면 화면 안 링크 선은 사라지고, screens.json 갈래(a→b)만 기획 갈래로 남는다"
    assert out["cutIn"] == ["a,b,true,false,false,false", "c,d,true,false,false,true"], "삭제한 a 로 오는 선(b→a·c→a)은 빠지고 a→b 만"
    pal = out["pal"]
    assert out["rows"] == [pal[0], pal[3], pal[6], pal[5], pal[0], pal[3]], "3칸씩 건너뛰어 이웃 줄이 갈리고, 8줄 뒤에 다시 돈다"


HISTORY_MODEL_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/history.js', 'utf8'), {filename: 'history.js'});
const H = globalThis.HD.history, out = {};
let s = H.initial([]);
for (let i = 0; i < 51; i++) s = H.reduce(s, {type: 'record', row: {label: 'move ' + i, status: 'canvas'}});
out.after51 = {at: s.at, lock: s.lock, canUndo: H.canUndo(s), canRedo: H.canRedo(s)};
let u = s; while (H.canUndo(u)) u = H.reduce(u, {type: 'go', to: u.at - 1});
out.undone = {at: u.at, steps: s.at - u.at, canUndo: H.canUndo(u), canRedo: H.canRedo(u)};
const r = H.reduce(u, {type: 'go', to: u.at + 1});
out.redo = {at: r.at, label: r.rows[r.at - 1].label};
const n = H.reduce(u, {type: 'record', row: {label: 'new', status: 'canvas'}});
out.branch = {len: n.rows.length, last: n.rows[n.rows.length - 1].label, canRedo: H.canRedo(n)};
let k = H.initial([]); for (let i = 0; i < H.KEEP + 5; i++) k = H.reduce(k, {type: 'record', row: {label: 'r' + i, status: 'canvas'}});
out.keep = {len: k.rows.length, first: k.rows[0].label};
console.log(JSON.stringify(out));
"""


def test_history_model_caps_undo_at_50():
    """되돌리기 50단계 제한(브라우저에서 끌기 51번으로 확인하던 것을 순수 리듀서로): 51번 기록 → 50번까지만 되돌림,
    가장 오래된 1단계는 잠김, 다시 하기·새 기록이면 되돌린 줄은 버림, 기록은 KEEP 줄까지만."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-hist-js-"))
    try:
        (tmp / "h.js").write_text(HISTORY_MODEL_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "h.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert out["after51"] == {"at": 51, "lock": 1, "canUndo": True, "canRedo": False}
    assert out["undone"] == {"at": 1, "steps": 50, "canUndo": False, "canRedo": True}, "50단계까지만"
    assert out["redo"] == {"at": 2, "label": "move 1"}
    assert out["branch"] == {"len": 2, "last": "new", "canRedo": False}, "되돌린 뒤 새 일 = 되돌린 줄은 버림"
    assert out["keep"]["len"] == 200 and out["keep"]["first"] == "r5"


VIEWPORT_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/viewport.js', 'utf8'), {filename: 'viewport.js'});
const V = globalThis.HD.viewport, out = {};
const c = {z: 0.5, tx: 40, ty: -20}, n = V.zoomAt(c, 300, 200, 1.25);
out.pinned = [(300 - c.tx) / c.z, (200 - c.ty) / c.z, (300 - n.tx) / n.z, (200 - n.ty) / n.z, n.z];
const f = V.fit({x0: 100, y0: 50, x1: 1100, y1: 550}, 532, 532, 32);
out.fit = [f.z, 100 * f.z + f.tx, 1100 * f.z + f.tx, 50 * f.z + f.ty, 550 * f.z + f.ty];
out.clamped = V.fit({x0: 0, y0: 0, x1: 10, y1: 10}, 532, 532, 32, z => Math.min(1.5, z)).z;
let s = V.initial(); out.s0 = s;
out.syncWhenOne = V.reduce(s, {type: 'sync', on: true}) === s;
s = V.reduce(s, {type: 'split', mode: 'lr'}); s = V.reduce(s, {type: 'sync', on: true}); out.lr = s;
out.back = V.reduce(s, {type: 'split', mode: 'one'});
out.bad = V.reduce(s, {type: 'split', mode: 'quad'}) === s;
console.log(JSON.stringify(out));
"""


def test_viewport_model_zoom_fit_and_split():
    """조각 6 카메라·나누기 규칙: 확대해도 마우스 아래 점은 그대로, 전체 보기 = 상자가 가운데 꽉, 배율 한도,
    동시 스크롤은 나눴을 때만, 하나로 돌아가면 동시 스크롤도 꺼짐."""
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-vp-js-"))
    try:
        (tmp / "v.js").write_text(VIEWPORT_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "v.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bx, by, bx2, by2, z = out["pinned"]
    assert abs(bx - bx2) < 1e-9 and abs(by - by2) < 1e-9 and z == 1.25, "마우스 아래 판 점은 그대로"
    fz, l, r_, t, b = out["fit"]
    assert abs(fz - 0.5) < 1e-9 and abs(l - 16) < 1e-6 and abs(r_ - 516) < 1e-6, "가로 꽉 + 여백 16씩"
    assert abs((t + b) / 2 - 266) < 1e-6, "세로 가운데"
    assert out["clamped"] == 1.5
    assert out["s0"] == {"split": "one", "sync": False}
    assert out["syncWhenOne"], "나누지 않았으면 동시 스크롤 없음"
    assert out["lr"] == {"split": "lr", "sync": True}
    assert out["back"] == {"split": "one", "sync": False}
    assert out["bad"]
