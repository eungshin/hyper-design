"""캔버스 모듈(modules/*.js) — Model·ViewModel 순수 함수 단위 테스트(node). 브라우저 없음.

graph.js · route.js · labels.js · style.js · camera.js · focus.js · prefs.js 를 순서대로 node 에서 읽어 확인한다.
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
PURE = ["graph", "route", "labels", "style", "camera", "edits", "tools", "dock", "focus", "prefs", "selection"]
ALL_MODULES = ["graph", "route", "labels", "style", "camera", "edits", "tools", "dock", "focus", "prefs", "selection", "view-links", "view-motion", "view-dock", "view-edge-pan", "view-select"]
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
  let s = F.reduce(F.reduce(F.initial({preset: 'deep'}), {type: 'focus', id: 'src'}), {type: 'links', links: m});
  s = F.reduce(s, {type: 'cycle'});                       // 전체 → 그룹 1
  const t = F.reduce(s, {type: 'toggle', k: 0});
  out.toggle = {on: t.on, visible: F.deriveView(m, t).visible, before: F.deriveView(m, s).visible, hover: t.hover};
  const t2 = F.reduce(t, {type: 'cycle'});
  out.cycleClearsManual = t2.on === null;
  const h = F.reduce(t, {type: 'hover', k: 1});
  out.hoverSame = F.reduce(h, {type: 'hover', k: 1}) === h;
  const x = F.reduce(h, {type: 'exitFocus'});
  out.exit = {focusId: x.focusId, links: x.links, stage: x.stage, on: x.on, hover: x.hover, colors: x.colors, pair: x.pair};
  const i0 = F.initial(); out.cycleNoLinksSame = F.reduce(i0, {type: 'cycle'}) === i0;
  out.styleIntent = F.reduce(i0, {type: 'style', colors: {preset: 'vivid'}}).colors;
  // Ctrl+클릭(연결 보기 밖): pair → 링크 답이 오면 그 그룹 하나만
  const pr = F.reduce(F.reduce(F.initial(), {type: 'pair', id: 'src', to: 't1'}), {type: 'links', links: m});
  out.pair = {focusId: pr.focusId, on: pr.on, visible: F.deriveView(m, pr).visible};
}

// 3b. 순환(전체 먼저) · 모두 표시 · 범례 제목 · 같은 대상 합치기
{
  const links = [{to: 'a', path: 'p0', text: '뒤로', rect: {x: 8, y: 10, w: 40, h: 40}},
                 {to: 'b', path: 'p1', text: '일시정지 신청', rect: {x: 20, y: 300, w: 335, h: 48}},
                 {to: 'c', path: 'p2', text: '연장하기', rect: {x: 20, y: 500, w: 335, h: 48}},
                 {to: 'b', path: 'p3', text: '정지 문의', rect: {x: 20, y: 700, w: 335, h: 48}}];
  const m = F.assignColors(links, '', F.LINK_COLORS); m.from = 'src'; m.titles = {src: '회원권'};
  let s = F.reduce(F.reduce(F.initial(), {type: 'focus', id: 'src'}), {type: 'links', links: m});
  const seq = [];
  const snap = st => { const v = F.deriveView(m, st); return {stage: v.stage, vis: v.visible, title: v.legend.title, all: v.legend.all, rows: v.legend.rows.length}; };
  seq.push(snap(s));
  for (let i = 0; i < 5; i++) { s = F.reduce(s, {type: 'cycle'}); seq.push(snap(s)); }
  out.cycle3 = seq;
  out.groups4 = F.groupsOf(m).map(g => [g.to, g.items, g.text, g.tag]);
  const dup = F.assignColors(['반품 신청', '수리 신청', '수리 신청'].map((x, i) => ({to: 'r', path: 'q' + i, text: x, rect: {x: 0, y: i * 60, w: 300, h: 48}})), '', F.LINK_COLORS);
  out.dupTag = F.groupsOf(dup)[0].tag;
  let t = F.reduce(s, {type: 'toggle', k: 2});          // s = 단계 1(그룹 a 만) → c 도 켬
  out.manual = snap(t);
  out.allOff = snap(F.reduce(t, {type: 'all', on: false}));
  out.allOn = snap(F.reduce(t, {type: 'all', on: true}));
  out.manualThenCycle = snap(F.reduce(t, {type: 'cycle'}));
}
// 3c. 옆면 규칙 · 경로 계획 · 태그 자리
out.side = [0.25, 0.5, 0.8].map(f => [HD.route.sideOf(f * 375, 375, 'R'), HD.route.sideOf(f * 375, 375, 'L')]);
{
  const S = {x: 1000, y: 1000, w: 375, h: 812}, cap = {top: 855, bottom: 896};
  const T = (x, row, rowTop) => ({x, y: rowTop, w: 375, h: 812, rowTop, cap: {top: rowTop - 145, bottom: rowTop - 104}, row});
  const groups = [
    {k: 0, to: 'back', target: T(541, 1, 1000), sameRow: true, members: [{x: 1008, y: 1010, w: 40, h: 40}]},
    {k: 1, to: 'far', target: T(1918, 1, 1000), sameRow: true, members: [{x: 1020, y: 1300, w: 335, h: 48}, {x: 1020, y: 1700, w: 335, h: 48}]},
    {k: 2, to: 'near', target: T(1459, 1, 1000), sameRow: true, members: [{x: 1020, y: 1500, w: 335, h: 48}]},
    {k: 3, to: 'bell', target: T(82, 1, 1000), sameRow: true, members: [{x: 1330, y: 1010, w: 40, h: 40}]},
    {k: 4, to: 'up', target: T(1459, 0, 0), sameRow: false, members: [{x: 1030, y: 1100, w: 300, h: 40}]}];
  const pl = HD.route.plan({src: S, rowTop: 1000, cap, left: 300, groups});
  out.plan = pl.map(p => ({k: p.k, side: p.side, rev: p.rev, gx: p.gx, lane: p.lane, ly: p.ly, pts: p.pts, d: p.d, segs: p.laneSegs, laneX: p.laneX}));
  const verts = [];
  pl.forEach(p => p.verticals.forEach(v => verts.push({k: p.k, x: v.x, y0: v.y0, y1: v.y1})));
  out.verts = verts;
  out.tags = HD.labels.placeTags(pl.map(p => ({k: p.k, segs: p.laneSegs, w: 90, h: 27})), verts);
  out.tagFallback = HD.labels.placeTags([{k: 0, segs: [{a: 0, b: 40, y: 0}], w: 90, h: 27}], []);
}
// 3d. 직선 우선(canvas-edit 3단계): 카드 목록을 주면 같은 줄 · 사이에 카드 없는 이웃은 요소 높이 그대로 곧게 옆면으로
{
  const S = {x: 1000, y: 1000, w: 375, h: 812}, cap = {top: 855, bottom: 896};
  const T = (x, row, rowTop) => ({x, y: rowTop, w: 375, h: 812, rowTop, cap: {top: rowTop - 145, bottom: rowTop - 104}, row});
  const card = x => ({x, y: 1000, w: 375, h: 812});
  const groups = [
    {k: 0, to: 'back', target: T(541, 1, 1000), sameRow: true, members: [{x: 1008, y: 1010, w: 40, h: 40}]},
    {k: 1, to: 'far', target: T(1918, 1, 1000), sameRow: true, members: [{x: 1020, y: 1300, w: 335, h: 48}, {x: 1020, y: 1700, w: 335, h: 48}]},
    {k: 2, to: 'near', target: T(1459, 1, 1000), sameRow: true, members: [{x: 1020, y: 1500, w: 335, h: 48}, {x: 1020, y: 1560, w: 335, h: 48}]},
    {k: 3, to: 'bell', target: T(82, 1, 1000), sameRow: true, members: [{x: 1330, y: 1010, w: 40, h: 40}]},
    {k: 4, to: 'up', target: T(1459, 0, 0), sameRow: false, members: [{x: 1030, y: 1100, w: 300, h: 40}]}];
  const cards = [card(82), card(541), card(1000), card(1459), card(1918), {x: 1459, y: 0, w: 375, h: 812}];
  const pl = HD.route.plan({src: S, rowTop: 1000, cap, left: 300, groups, cards});
  out.planStraight = pl.map(p => ({k: p.k, straight: !!p.straight, side: p.side, pts: p.pts, segs: p.laneSegs, verts: p.verticals, floatAt: p.floatAt || null}));
  const verts = [];
  pl.forEach(p => p.verticals.forEach(v => verts.push({k: p.k, x: v.x, y0: v.y0, y1: v.y1})));
  out.tagsStraight = HD.labels.placeTags(pl.map(p => ({k: p.k, segs: p.laneSegs, w: 90, h: 27})), verts);
  // 되돌아가는 연결(흐름 순서상 앞 화면으로) 표시 · 태그 자리가 없으면 줄 위 빈자리(floatAt)에 떠서 마우스 올릴 때만
  const links = [{to: 'prev', path: 'p0', text: '이전', rect: {x: 8, y: 10, w: 40, h: 40}}, {to: 'next', path: 'p1', text: '다음으로 가기 버튼', rect: {x: 20, y: 700, w: 335, h: 48}}];
  const m = F.assignColors(links, '', F.LINK_COLORS); m.from = 'src'; m.seq = ['prev', 'src', 'next'];
  m.geom = {src: {x: 1000, y: 1000, w: 375, h: 812, sc: 1}, rowTop: 1000, cap, left: 300, srcRow: 1,
            targets: {prev: T(541, 1, 1000), next: T(1459, 1, 1000)}, cards: [card(541), card(1000), card(1459)], tags: {0: {w: 60, h: 27}, 1: {w: 160, h: 27}}};
  const v = F.deriveView(m, F.reduce(F.reduce(F.initial(), {type: 'focus', id: 'src'}), {type: 'links', links: m}));
  out.viewStraight = v.groups.map(g => ({to: g.to, back: !!g.back, straight: g.pts[0].length === 2, tag: g.tag, lineY: g.pts[0][0][1]}));
  // 틈이 TAG_MIN 보다 좁은 이웃(카드 사이 30px) → 줄 위 빈자리로 뜬다
  const m2 = F.assignColors([links[1]], '', F.LINK_COLORS); m2.from = 'src'; m2.seq = ['src', 'next'];
  m2.geom = {src: {x: 1000, y: 1000, w: 375, h: 812, sc: 1}, rowTop: 1000, cap, left: 300, srcRow: 1,
             targets: {next: T(1405, 1, 1000)}, cards: [card(1000), card(1405)], tags: {0: {w: 160, h: 27}}};
  out.narrowGap = F.deriveView(m2, F.reduce(F.reduce(F.initial(), {type: 'focus', id: 'src'}), {type: 'links', links: m2})).groups[0].tag;
}

// 4. prefs (v2: 색 프리셋 · 랜덤 · 쌍 색 · 굵기 · 움직임, v1 sat 는 버림)
const mk = o => k => (k in o ? o[k] : null);
const RS = ['#AA3344', '#33AA44', '#3344AA', '#AAAA33', '#33AAAA', '#AA33AA'];
out.prefs = {
  migrate: HD.prefs.load(mk({'hd-arrows': '0', 'hd-link-sat': '0.5'})),
  fresh: HD.prefs.load(mk({})),
  badJson: HD.prefs.load(mk({'hd-canvas-prefs': '{bad', 'hd-arrows': '0'})),
  v1: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 1, arrows: false, sat: 1.1}), 'hd-arrows': '1'})),
  stored: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 2, arrows: false, preset: 'random', rand: RS, custom: {'a>b': '#ABCDEF'}, width: 4.5, motion: false})})),
  badFields: HD.prefs.load(mk({'hd-canvas-prefs': JSON.stringify({v: 2, arrows: 'no', preset: 'random', rand: [1], custom: {x: '#ABCDEF', 'a>b': 'red', 'c>d': '#123456'}, width: 9, motion: 'x'})})),
  throws: HD.prefs.load(() => { throw new Error('denied'); }),
};
const writes = {};
HD.prefs.save({v: 1, arrows: false, sat: 0.5, width: 5}, (k, v) => { writes[k] = v; });
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
    assert res["flowKinds"] == ["flow"] and res["sameAsArrows"]
    assert res["screens"] == 28


def test_add_links_replaces_and_groups(res):
    assert res["linkCountA"] == 3 and res["linkPathsA"] == ["q1", "q2", "q3"]   # 두 번째 답이 첫 답을 바꿔 낌
    assert res["linkCountZ"] == 2 and res["flowAfter"] == 9
    assert res["groups"] == [["c", 0, ["q1", "q3"]], ["b", 1, ["q2"]]]


def test_focus_reducer(res):
    for n in ("1", "3", "5"):
        assert res["cycle"][n]["got"] == res["cycle"][n]["want"], n
    assert res["cycle"]["3"]["got"][:6] == [0, 1, 2, 3, 0, 1]          # v3: Shift+클릭 = 전체 먼저, 다시 누르면 하나씩 → 전체
    assert res["cycle"]["1"]["got"] == [0] * len(res["cycle"]["1"]["got"])
    t = res["toggle"]
    assert t["before"] == [True, False, False]
    assert t["on"] == {"0": False, "1": False, "2": False} and t["visible"] == [False, False, False] and t["hover"] is None
    assert res["cycleClearsManual"] and res["hoverSame"] and res["cycleNoLinksSame"]
    assert res["exit"] == {"focusId": None, "links": None, "stage": 0, "on": None, "hover": None, "colors": {"preset": "deep"}, "pair": None}
    assert res["styleIntent"] == {"preset": "vivid"}
    assert res["pair"] == {"focusId": "src", "on": {"0": False, "1": True, "2": False}, "visible": [False, True, False]}   # Ctrl+클릭 쌍 하나만


DEF = {"v": 2, "arrows": True, "preset": "calm", "rand": None, "custom": {}, "width": 2.5, "motion": True}


def test_prefs(res):
    p = res["prefs"]
    assert p["migrate"] == dict(DEF, arrows=False)                                   # 예전 키(hd-link-sat 는 버림)
    assert p["fresh"] == DEF and p["throws"] == DEF
    assert p["badJson"] == dict(DEF, arrows=False)
    assert p["v1"] == dict(DEF, arrows=False)                                        # v1 → v2: sat 버림
    assert p["stored"] == {"v": 2, "arrows": False, "preset": "random", "rand": ["#AA3344", "#33AA44", "#3344AA", "#AAAA33", "#33AAAA", "#AA33AA"],
                           "custom": {"a>b": "#ABCDEF"}, "width": 4.5, "motion": False}
    assert p["badFields"] == dict(DEF, custom={"c>d": "#123456"})                     # 틀린 값은 기본값(랜덤인데 rand 없음 → 차분)
    assert list(p["writes"]) == ["hd-canvas-prefs"] and json.loads(p["writes"]["hd-canvas-prefs"]) == dict(DEF, arrows=False, width=5)


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


def test_single_file_output(res):
    html = res["_html"]
    for n in ALL_MODULES:
        assert f'data-hd-module="{n}"' in html
    order = [html.index(f'data-hd-module="{n}"') for n in ALL_MODULES]
    assert order == sorted(order) and order[-1] < html.index("// ── Canvas shell")
    assert "/* hd-motion */" not in html and "--duration-fast: 250ms" in html and html.index("--camera-glide-dur") < html.index("</style>")   # motion.css 인라인
    assert not re.search(r"<script[^>]+\bsrc=", html), "외부 스크립트 참조 없음"


def test_cycle_all_first_and_legend(res):
    """S1: 첫 Shift+클릭 = 전체(그룹 n개), 다시 = 1 … n → 전체. 제목 · 모두 표시 체크 상태."""
    seq = res["cycle3"]
    assert [x["stage"] for x in seq] == [0, 1, 2, 3, 0, 1]
    assert seq[0]["title"] == "회원권 · 전체 3개" and seq[0]["all"] == "on" and seq[0]["vis"] == [True, True, True]
    assert seq[1]["title"] == "회원권 · 1/3 뒤로" and seq[1]["vis"] == [True, False, False] and seq[1]["all"] == "mixed"
    assert seq[2]["title"] == "회원권 · 2/3 일시정지 신청 · 정지 문의"
    assert seq[3]["title"] == "회원권 · 3/3 연장하기"
    assert all(x["rows"] == 3 for x in seq)                          # 범례 줄 = 대상 그룹 하나에 한 줄
    assert res["manual"]["title"] == "회원권 · 직접 선택 2/3" and res["manual"]["vis"] == [True, False, True] and res["manual"]["all"] == "mixed"
    assert res["allOff"]["vis"] == [False] * 3 and res["allOff"]["all"] == "off" and res["allOff"]["title"] == "회원권 · 직접 선택 0/3"
    assert res["allOn"]["vis"] == [True] * 3 and res["allOn"]["all"] == "on"
    assert res["manualThenCycle"]["title"] == "회원권 · 2/3 일시정지 신청 · 정지 문의"   # 수동 선택은 다음 Shift+클릭까지만


def test_same_target_merge(res):
    g = res["groups4"]
    assert [x[0] for x in g] == ["a", "b", "c"] and g[1][1] == [1, 3]
    assert g[1][2] == "일시정지 신청 · 정지 문의 (2)" and g[1][3] == "일시정지 신청 · 정지 문의 (2)"
    assert g[0][2] == "뒤로"
    assert res["dupTag"] == "반품 신청 · 수리 신청 (3)"   # 같은 글 버튼 여럿 → 글은 한 번, 개수는 (n)


def test_side_rule(res):
    assert res["side"] == [["L", "L"], ["R", "L"], ["R", "R"]]       # 25% → 왼쪽 · 50% → 대상 쪽 · 80% → 오른쪽


def segs_of(pts):
    return [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]


def collinear_overlap(s1, s2):
    (a, b), (c, d) = s1, s2
    if a[1] == b[1] == c[1] == d[1]:
        lo, hi = max(min(a[0], b[0]), min(c[0], d[0])), min(max(a[0], b[0]), max(c[0], d[0]))
        return max(0, hi - lo)
    if a[0] == b[0] == c[0] == d[0]:
        lo, hi = max(min(a[1], b[1]), min(c[1], d[1])), min(max(a[1], b[1]), max(c[1], d[1]))
        return max(0, hi - lo)
    return 0


def test_plan_routes(res):
    P = {p["k"]: p for p in res["plan"]}
    back, far, near, bell, up = P[0], P[1], P[2], P[3], P[4]
    assert back["side"] == "L" and back["pts"][0][0][0] == 1008 and back["pts"][0][1][0] < 1000   # 왼쪽 위 뒤로: 왼쪽 옆면으로 나감
    assert near["side"] == far["side"] == "R" and not near["rev"]
    assert near["gx"] == 1375 + 38 and far["gx"] == 1375 + 26                      # 가까운 대상 = 바깥 통로
    assert bell["side"] == "R" and bell["rev"] and bell["gx"] == 1375 + 14          # 반대 방향 = 가장 안쪽
    assert near["lane"] == 0 and far["lane"] == 1
    assert bell["lane"] > max(P[k]["lane"] for k in (0, 1, 2))                      # 반대 방향 = 겹치는 것들 위
    assert up["laneX"] < min(p["gx"] for p in res["plan"]) and len(up["segs"]) == 2
    for p in res["plan"]:
        for pts in p["pts"]:
            for (a, b) in segs_of(pts):
                assert a[0] == b[0] or a[1] == b[1], ("가로·세로만", p["k"], pts)
            corners = len(pts) - 2
            assert corners <= (5 if p["k"] == 4 else 3), (p["k"], pts)
        for d in p["d"]:
            assert set(re.findall(r"[A-Z]", d)) <= {"M", "L", "Q"}
    for p in res["plan"]:                                                          # 서로 다른 그룹은 20px 넘게 겹치지 않는다
        for q in res["plan"]:
            if p["k"] >= q["k"]:
                continue
            for s1 in (s for pts in p["pts"] for s in segs_of(pts)):
                for s2 in (s for pts in q["pts"] for s in segs_of(pts)):
                    assert collinear_overlap(s1, s2) <= 20, (p["k"], q["k"], s1, s2)


def test_plan_straight_neighbours(res):
    """3단계 직선 우선: 카드 목록이 있으면 같은 줄 · 사이에 카드 없는 이웃은 곧은 가로선 한 줄(옆면으로), 나머지는 지금 차선 길."""
    P = {p["k"]: p for p in res["planStraight"]}
    near, back = P[2], P[0]
    for g, edge in ((near, 1459 - 10), (back, 541 + 375 + 10)):
        assert g["straight"] and g["verts"] == [], g
        for pts in g["pts"]:
            assert len(pts) == 2 and pts[0][1] == pts[1][1] and pts[1][0] == edge, pts     # 꺾임 0 · 옆면 10px 앞(위로 들어갈 때와 같은 틈 — 색 고리가 화살촉을 덮지 않게)
    assert [p[0][1] for p in near["pts"]] == [1524, 1584], near["pts"]                   # 요소 높이 그대로(멤버마다)
    assert back["pts"][0][0][0] == 1008 and back["pts"][0][1][0] < 1000                   # 왼쪽 요소는 왼쪽으로
    for k in (1, 3, 4):                                                                    # 사이에 카드(far · bell) · 다른 줄(up) = 차선 길
        assert not P[k]["straight"] and P[k]["verts"], P[k]
    assert near["segs"][0]["a"] == 1375 and near["segs"][0]["b"] == 1459 - 10             # 태그 후보 = 카드 사이 틈 중 선이 지나는 곳
    assert near["floatAt"] and near["floatAt"]["y"] < 1000                                 # 자리 없으면 줄 위 빈자리
    for pts in P[1]["pts"] + P[3]["pts"]:                                                  # 차선 길은 곧은 선과 20px 넘게 겹치지 않는다
        for s1 in segs_of(pts):
            for s2 in (s for q in near["pts"] + back["pts"] for s in segs_of(q)):
                assert collinear_overlap(s1, s2) <= 20, (s1, s2)
    v = {g["to"]: g for g in res["viewStraight"]}
    assert v["prev"]["back"] and not v["next"]["back"], v                                  # 흐름 순서상 앞 화면 = 되돌아가는 연결
    # 곧은 선의 태그 = 카드 사이 틈 칸 안, 선 바로 위(틈 폭에 맞게 줄임 — 말줄임은 화면이) · 멀리 띄우기는 틈이 TAG_MIN 보다 좁을 때만
    for to, lo, hi in (("next", 1375, 1459), ("prev", 916, 1000)):
        t, line_y = v[to]["tag"], v[to]["lineY"]
        assert t["gap"] and not t.get("float"), (to, t)
        assert lo < t["x"] - t["maxW"] / 2 and t["x"] + t["maxW"] / 2 < hi and abs(t["x"] - (lo + hi) / 2) < 0.5, (to, t)   # 틈 가운데, 카드 침범 없음
        above = t["y"] + t["h"] / 2 <= line_y - 2 and line_y - (t["y"] + t["h"] / 2) <= 6
        below = t["y"] - t["h"] / 2 >= line_y + 2 and (t["y"] - t["h"] / 2) - line_y <= 6
        assert (above if to == "next" else below), (to, t, line_y)                     # 선 바로 위 — 카드 맨 위 버튼이라 위에 자리가 없으면 바로 아래
        assert 1000 < t["y"] - t["h"] / 2 and t["y"] + t["h"] / 2 < 1812, (to, t)         # 카드 높이 안(줄 제목·설명 줄 침범 없음)
    assert res["narrowGap"]["float"] and not res["narrowGap"].get("gap"), res["narrowGap"]   # 틈 칸조차 없으면 줄 위 빈자리로


def test_place_tags(res):
    tags, P = res["tags"], {p["k"]: p for p in res["plan"]}
    W, H = 90 + 8, 27 + 8
    for t in tags:
        assert not t["fallback"], t
        seg = [s for s in P[t["k"]]["segs"] if abs(s["y"] - t["y"]) < 0.01][0]
        assert seg["a"] + 10 + 45 <= t["x"] + 1e-6 and t["x"] + 45 <= seg["b"] - 10 + 1e-6, (t, seg)
        for v in res["verts"]:
            if v["k"] == t["k"]:
                continue
            assert not (v["x"] - 3 < t["x"] + W / 2 and t["x"] - W / 2 < v["x"] + 3 and min(v["y0"], v["y1"]) < t["y"] + H / 2 and t["y"] - H / 2 < max(v["y0"], v["y1"])), (t, v)
    for i, a in enumerate(tags):
        for b in tags[i + 1:]:
            assert not (abs(a["x"] - b["x"]) < W and abs(a["y"] - b["y"]) < H), (a, b)
    fb = res["tagFallback"][0]
    assert fb["fallback"] and fb["x"] == 20                                         # 자리가 없으면 50%


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
const base = K.normalize({v: 1, groups: [{tabs: ['links', 'show'], active: 'links'}, {tabs: ['notes', 'hidden'], active: 'notes'}]});
let s = base;
out.def = tabs(s); out.defaults = tabs(K.defaults());
const s0 = s; s = R(s, {type: 'move', id: 'notes', to: 0}); out.merge = tabs(s); out.pure = tabs(s0);
s = R(s, {type: 'move', id: 'show', to: 'new', at: 1}); out.split = tabs(s);
out.lone = R(s, {type: 'move', id: 'show', to: 'new', at: 0}) === s;
s = R(s, {type: 'close', id: 'hidden'}); out.closeHidden = tabs(s) + ' / ' + s.closed.join(',');
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
f = R(f, {type: 'move', id: 'hidden', to: 'float', fi: 0}); out.fMerge = ftabs(f);
f = R(f, {type: 'float', fi: 0, w: 50, h: 9000, x: 10.6}); out.fRect = ftabs(f);
f = R(f, {type: 'move', id: 'notes', to: 'new'}); out.fBack = ftabs(f);
f = R(f, {type: 'move', id: 'hidden', to: 'float', x: 5, y: 6}); out.fLoneMove = ftabs(f);
f = R(R(f, {type: 'collapse', on: true}), {type: 'move', id: 'show', to: 'float', x: 0, y: 0}); out.fVis = K.visible(f); out.fCol = f.collapsed;
f = R(f, {type: 'activate', id: 'hidden'}); out.fTop = f.floats.map(x => x.active); out.fCol2 = f.collapsed;
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
    assert out["def"] == "links+show:links | notes+hidden:notes"
    assert out["merge"] == "links+show+notes:notes | hidden:hidden", "합치면 그 묶음 끝에 들어가 활성"
    assert out["pure"] == out["def"], "reduce 는 원래 상태를 바꾸지 않는다"
    assert out["split"] == "links+notes:notes | show:show | hidden:hidden", "떼면 그 자리에 새 묶음"
    assert out["lone"], "혼자 있는 탭은 떼어도 그대로"
    assert out["closeHidden"] == "links+notes:notes | show:show / hidden", "빈 묶음은 없어진다"
    assert out["closeStyle"] == "links+notes:notes"
    assert out["reopen"] == "links+notes+show:show / hidden / false", "닫힌 패널을 부르면 마지막 묶음에 다시 열고 편다"
    assert out["w"] == [560, 220, 333]
    assert out["hs"] == [2, 0.5] and out["hsBad"]
    assert out["vis"] == [["show"], []]
    assert out["norm"] == "notes+show+hidden:notes", "모르는 패널·겹친 패널은 버리고 빠진 패널은 마지막 묶음에"
    assert out["normClosed"] == ["links"]
    assert out["round"] and out["bad"] == [out["defaults"]] * 3
    assert out["defaults"] == "links:links | show:show | notes+hidden:notes", "기본: 범례 · 선 표시 · 메모 묶음"
    # 떠 있는 창(D1): 빼기 · 합치기 · 옮기기/크기(최소) · 도크로 되돌리기 · 혼자 뜬 창 옮기기 · 접어도 보임 · 맨 위로 · 닫기 · 복구 · 저장
    assert out["fOut"] == "links+show:links | hidden:hidden || notes:notes@100,50,280,320", "도크 묶음에서 빼면 판 위 떠 있는 창"
    assert out["fMerge"] == "links+show:links || notes+hidden:hidden@100,50,280,320", "떠 있는 창에 합치면 빈 도크 묶음은 없어진다"
    assert out["fRect"] == "links+show:links || notes+hidden:hidden@11,50,200,9000", "최소 너비 200"
    assert out["fBack"] == "links+show:links | notes:notes || hidden:hidden@11,50,200,9000", "도크 끝에 끌어 넣으면 새 묶음"
    assert out["fLoneMove"].endswith("hidden:hidden@5,6,200,9000"), "혼자 뜬 창을 다시 빼면 그 창이 옮겨질 뿐"
    assert out["fVis"] == ["hidden", "show"] and out["fCol"], "도크를 접어도 떠 있는 창은 보인다"
    assert out["fTop"] == ["show", "hidden"] and out["fCol2"], "누른 떠 있는 창이 맨 위로, 도크는 접힌 채"
    assert out["fClose"] == "links:links | notes:notes || hidden:hidden@5,6,200,9000 / show"
    assert out["fNorm"] == "links+show+hidden:links || notes:notes@40,40,200,320", "이미 쓴 패널·모르는 패널 버림, 틀린 좌표는 기본값"
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


# ── 책임 게이트(contract.md '책임 게이트') — 한 객체가 다시 커지지 않게, 기능 사이는 의도로만
LAYER = {"graph": "Model", "route": "Model", "labels": "Model", "style": "Model", "camera": "Model", "edits": "Model",
         "tools": "ViewModel", "dock": "ViewModel", "focus": "ViewModel", "prefs": "ViewModel", "selection": "ViewModel"}
RANK = {"Model": 0, "ViewModel": 1, "View": 2}
NS = {"lineStyle": "style"}                          # HD 이름 → 모듈 파일(이름이 다른 것만)
# 템플릿(셸) 위쪽 선언 수 — 조각마다 줄기만 한다. 늘리려면 이 숫자를 고치는 것이 리뷰에 드러난다.
SHELL_MAX = {"var": 85, "function": 115}   # 2.5a: picked·setPicks·togglePick → selection.js·view-select.js


def _layer(name):
    return "View" if name.startswith("view-") else LAYER[name]


def _hd_name(name):
    if name.startswith("view-"):
        return "view" + "".join(p.title() for p in name.split("-")[1:])
    return {v: k for k, v in NS.items()}.get(name, name)


def shell_counts(tpl):
    s = tpl[tpl.index("// ── Canvas shell"):]
    names = []
    for m in re.finditer(r"(?m)^var\s+(.+)$", s):
        depth, cur, parts = 0, "", []
        for ch in m.group(1):
            depth += ch in "([{"
            depth -= ch in ")]}"
            if ch in ",;" and depth == 0:
                parts.append(cur); cur = ""
                if ch == ";": break
            else:
                cur += ch
        parts = [p for p in parts if not re.match(r"\s*\w+\s*=\s*HD\.\w+\.mount\(", p)]   # 모듈을 붙이는 줄(var X = HD.x.mount(…))은 셸이 할 일 — 세지 않는다
        names += [n.group(1) for n in (re.match(r"\s*(\w+)", p) for p in parts) if n]
    return {"var": len(names), "function": len(re.findall(r"(?m)^function\s+\w+", s))}


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
        if dep.startswith("view"):
            assert False, f"{name}.js → HD.{dep}: View 끼리 직접 부르지 않는다 — ctx 로 받은 함수·의도로"
        assert mod in LAYER, f"{name}.js → HD.{dep}: 모르는 모듈"
        assert RANK[LAYER[mod]] <= RANK[me] and not (me == "Model" and LAYER[mod] != "Model"), f"{name}.js({me}) → {mod}({LAYER[mod]}): 위 층에 기댐"


def test_gate_shell_only_shrinks():
    """비대 방지: 템플릿 셸의 위쪽 var·function 수는 SHELL_MAX 를 넘지 않는다(새 기능은 모듈로). 모듈을 붙이는 줄은 세지 않는다."""
    got = shell_counts((SCRIPTS / "canvas_template.html").read_text(encoding="utf-8"))
    for k, mx in SHELL_MAX.items():
        assert got[k] <= mx, f"셸 위쪽 {k} {got[k]} > {mx} — 새 상태·함수는 modules/ 의 주인 모듈로"


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
