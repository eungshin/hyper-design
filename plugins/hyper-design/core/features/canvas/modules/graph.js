/* Model — 링크 그래프 하나. 화면(노드) + 연결(간선).
   kind:'flow' = screens.json branches(기획 갈래), kind:'link' = 화면 안 링크(빌드가 화면 파일에서 뽑은 D.links, 연결 보기에서는 hd-links 답으로 바꿔 끼움).
   overview(g, pend) = 판에 늘 그리는 선(화면 쌍마다 하나).
   순수 함수만(DOM 없음). */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

// D(캔버스 데이터) → {screens:[{id,title,row,group,file,state}], edges:[{from,to,kind:'flow',label}]}
function fromData(D) {
  D = D || {};
  var screens = [];
  (D.rows || []).forEach(function (row, ri) {
    (row.screens || []).forEach(function (s) {
      screens.push({id: s.id, title: s.title, row: ri, group: row.group, file: s.file, state: !!s.state});
    });
  });
  var edges = (D.arrows || []).map(function (a) { return {from: a.from, to: a.to, kind: 'flow', label: a.label || ''}; });
  Object.keys(D.links || {}).forEach(function (from) {
    (D.links[from] || []).forEach(function (l) { edges.push({from: from, to: String(l.to), kind: 'link', label: l.text || ''}); });
  });
  return {screens: screens, edges: edges};
}

// hd-links 답(links:[{to,path,text,rect}])을 그 화면의 kind:'link' 간선으로 — 그 화면의 예전 link 간선은 바꿔 끼운다.
function addLinks(g, screenId, links) {
  var keep = (g.edges || []).filter(function (e) { return !(e.kind === 'link' && e.from === screenId); });
  var add = (links || []).map(function (l) {
    return {from: screenId, to: l.to, kind: 'link', label: l.text, via: {path: l.path, text: l.text, rect: l.rect}};
  });
  return {screens: g.screens, edges: keep.concat(add)};
}

// id 에서 나가는 간선(id 가 null 이면 전부), kind 로 거른다.
function edgesFrom(g, id, kind) {
  return (g.edges || []).filter(function (e) { return (id == null || e.from === id) && (!kind || e.kind === kind); });
}

// 같은 대상끼리 묶는다 → [{to, edges:[...], k}] (k = 처음 나온 순서)
function groupByTarget(edges) {
  var out = [], at = {};
  (edges || []).forEach(function (e) {
    if (!(e.to in at)) { at[e.to] = out.length; out.push({to: e.to, edges: [], k: out.length}); }
    out[at[e.to]].edges.push(e);
  });
  return out;
}

// 판에 늘 그리는 선 — 화면 쌍마다 하나(E7·D6c). pend = edits.overviewPending(메모): {add:[{from,to}], drop:{'a>b':n}, cutIn:{id:1}}
// → [{a, b, ab, ba, pend, plan, labels, lab:{ab, ba}}]  a = 처음 나온 방향의 출발 · ab/ba = 그 방향 연결이 있나 · pend = 반영 대기로만 있는 선(점선)
//   labels = 두 방향 버튼 글 · lab.ab / lab.ba = 방향마다 버튼 글(선 태그는 방향마다 하나, 출발 카드 옆)
//   plan = 화면 안 링크도 반영 대기도 없는 screens.json 갈래(기획 갈래 — 얇은 회색 실선, D8)
function overview(g, pend) {
  pend = pend || {}; var drop = pend.drop || {}, cutIn = pend.cutIn || {};
  var real = {}, lab = {}, wait = {}, pairs = [], at = {};
  function pair(a, b) {
    var k = a < b ? a + '|' + b : b + '|' + a;
    if (!(k in at)) { at[k] = pairs.length; pairs.push({a: a, b: b, ab: false, ba: false, pend: false, plan: false, labels: [], lab: {ab: [], ba: []}}); }
    return pairs[at[k]];
  }
  (g.edges || []).forEach(function (e) {
    if (e.kind !== 'link' || e.from === e.to) return;
    var k = e.from + '>' + e.to; real[k] = (real[k] || 0) + 1;
    if (e.label && (lab[k] = lab[k] || []).indexOf(e.label) < 0) lab[k].push(e.label);
  });
  Object.keys(drop).forEach(function (k) { if (real[k]) real[k] -= drop[k]; });
  Object.keys(real).forEach(function (k) { var to = k.slice(k.indexOf('>') + 1); if (cutIn[to]) real[k] = 0; });
  (pend.add || []).forEach(function (x) { if (x.from !== x.to) wait[x.from + '>' + x.to] = 1; });
  var dirs = Object.keys(real).filter(function (k) { return real[k] > 0; }).concat(Object.keys(wait));
  dirs.forEach(function (k) {
    var i = k.indexOf('>'), from = k.slice(0, i), to = k.slice(i + 1), p = pair(from, to);
    var dir = p.a === from ? 'ab' : 'ba'; p[dir] = true;
    (lab[k] || []).forEach(function (t) { if (p.labels.indexOf(t) < 0) p.labels.push(t); p.lab[dir].push(t); });
  });
  pairs.forEach(function (p) { p.pend = !(real[p.a + '>' + p.b] > 0) && !(real[p.b + '>' + p.a] > 0); });
  (g.edges || []).forEach(function (e) {
    if (e.kind !== 'flow' || e.from === e.to) return;
    var k = e.from < e.to ? e.from + '|' + e.to : e.to + '|' + e.from;
    if (k in at || cutIn[e.to]) return;
    var p = pair(e.from, e.to); p.ab = true; p.plan = true; if (e.label) p.labels.push(e.label);
  });
  return pairs;
}

HD.graph = {fromData: fromData, addLinks: addLinks, edgesFrom: edgesFrom, groupByTarget: groupByTarget, overview: overview};
})();
