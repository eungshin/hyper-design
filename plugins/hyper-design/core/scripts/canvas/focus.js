/* ViewModel — 연결 보기 상태 하나 + 순수 리듀서, 그리고 상태 → 보일 것(deriveView). DOM 없음.
   상태 {focusId, links, stage, on, hover, sat}
     focusId : Shift+클릭한 화면 id(없으면 null)   links : 그 화면의 색 링크 모델(assignColors 결과 + from/titles…)
     stage   : 색 단계(1..n, 0 = 전체)            on    : 범례 체크(수동, 다음 Shift+클릭 전까지)
     hover   : 마우스가 올라간 쌍 k               sat   : 채도 배율
   의도 {type:'focus', id} · {type:'exitFocus'} · {type:'cycle'} · {type:'toggle', k} · {type:'hover', k} · {type:'setSat', v} · {type:'links', links} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var LINK_COLORS = ['#C46F3E', '#B08F33', '#4F9563', '#3C918B', '#5B7DB5', '#8466AE', '#B85B83', '#B9514F'];   // 저채도 8색(색상각이 서로 다름)

function hueOf(hx) {
  var m = /^#?([0-9a-f]{6})$/i.exec(String(hx || '').trim()); if (!m) return null;
  var v = parseInt(m[1], 16), r = (v >> 16 & 255) / 255, g = (v >> 8 & 255) / 255, b = (v & 255) / 255;
  var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  if (d < 0.08) return null;                       // 회색 계열은 색상각이 없다
  var h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
}
function hueGap(a, b) { var d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; }
function satHex(hx, s) {                           // 채도만 s 배(HSL)
  var m = /^#?([0-9a-f]{6})$/i.exec(String(hx || '').trim()); if (!m || s == null) return hx;
  var v = parseInt(m[1], 16), r = (v >> 16 & 255) / 255, g = (v >> 8 & 255) / 255, b = (v & 255) / 255;
  var mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn, h = 0, sa = 0;
  if (d) { sa = d / (1 - Math.abs(2 * l - 1)); h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h = (h * 60 + 360) % 360; }
  sa = Math.max(0, Math.min(1, sa * s));
  var c = (1 - Math.abs(2 * l - 1)) * sa, x = c * (1 - Math.abs((h / 60) % 2 - 1)), o = l - c / 2;
  var q = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return '#' + q.map(function (t) { return ('0' + Math.max(0, Math.min(255, Math.round((t + o) * 255))).toString(16)).slice(-2); }).join('');
}
// 링크마다 색: 같은 대상 = 같은 색, 문서에 처음 나온 순서, 앱 강조색 ±30° 는 건너뜀, 모자라면 번호
function assignColors(links, accentHex, palette) {
  palette = palette || LINK_COLORS;
  var ah = hueOf(accentHex);
  var pal = palette.filter(function (c) { var h = hueOf(c); return ah == null || h == null || hueGap(h, ah) >= 30; });
  if (!pal.length) pal = palette.slice();
  var order = [];
  (links || []).forEach(function (l) { if (order.indexOf(l.to) < 0) order.push(l.to); });
  var numbered = order.length > pal.length, targets = {};
  order.forEach(function (t, i) { targets[t] = {color: pal[i % pal.length], n: numbered ? i + 1 : 0, ci: i}; });
  return {order: order, targets: targets, items: (links || []).map(function (l) {
    var g = targets[l.to];
    return {to: l.to, path: l.path, text: l.text, rect: l.rect, color: g.color, n: g.n, ci: g.ci};
  })};
}
// 같은 카드를 Shift+클릭할 때마다: 색1 → 색2 → … → 전체(0) → 색1. 색이 하나뿐이면 늘 전체.
function cycleNext(stage, n) {
  if (!(n > 1)) return 0;
  if (stage == null || stage === 0) return 1;
  return stage >= n ? 0 : stage + 1;
}
// 실제로 보이는 단계 · 쌍마다 보임(deriveView 와 같은 규칙)
function stageOf(m, ui) {
  if (!m || !m.items || !m.items.length) return 0;
  var n = m.order.length;
  return n <= 1 ? 0 : ui.stage == null ? 1 : ui.stage > n ? 0 : ui.stage;
}
function visibleOf(m, ui) {
  if (!m || !m.items || !m.items.length) return [];
  var stage = stageOf(m, ui);
  return m.items.map(function (it, k) { return ui.on ? !!ui.on[k] : stage === 0 || it.ci === stage - 1; });
}

// Model + UI 상태(단계·체크·마우스·채도) → 보일 것. DOM 없음.
function deriveView(m, ui) {
  ui = ui || {};
  var out = {pairs: [], legend: null, rings: {}, dimCards: [], stage: 0, nColors: 0, visible: []};
  if (!m || !m.items || !m.items.length) return out;
  var n = m.order.length, stage = stageOf(m, ui);
  var sat = ui.sat == null ? 0.7 : ui.sat, hv = ui.hover == null ? null : ui.hover;
  var title = function (id) { return (m.titles && m.titles[id]) || id; };
  var col = m.items.map(function (it) { return satHex(it.color, sat); });
  var vis = visibleOf(m, ui);
  if (hv != null && !vis[hv]) hv = null;
  out.stage = stage; out.nColors = n; out.visible = vis;
  out.legend = {title: title(m.from) + ' · ' + (stage === 0 ? '전체 ' + m.items.length + '개' : stage + '/' + n + ' ' + title(m.order[stage - 1])),
    rows: m.items.map(function (it, k) { return {k: k, color: col[k], from: title(m.from), text: it.text || '(링크)', to: title(it.to), checked: vis[k], emph: hv === k}; })};
  var hvTo = hv == null ? null : m.items[hv].to;
  m.items.forEach(function (it, k) {
    if (vis[k] && !out.rings[it.to]) out.rings[it.to] = {color: col[k], n: it.n, emph: hvTo === it.to, dim: hvTo != null && hvTo !== it.to};
  });
  m.order.forEach(function (t) { if (!out.rings[t]) out.dimCards.push(t); });
  var g = m.geom, placed = [], idx = 0;
  var list = m.items.map(function (it, k) { return k; }).filter(function (k) { return vis[k]; });
  if (g) list.sort(function (a, b) { return (m.items[a].rect.y - m.items[b].rect.y) || a - b; });
  list.forEach(function (k) {
    var it = m.items[k];
    var p = {k: k, from: m.from, to: it.to, color: col[k], n: it.n, text: it.text, chip: null, path: null, emph: hv === k, dim: hv != null && hv !== k};
    if (g) {
      var S = g.src, sz = (g.chips && g.chips[k]) || {w: 120, h: 30};
      var lim = S.limit == null ? Infinity : S.limit;
      var c = HD.labels.placeChip(S, it.rect, sz, placed);
      placed.push(c); p.chip = c;
      var T = g.targets && g.targets[it.to];
      var gx = Math.min(S.x + S.w + 14 + 12 * idx, lim - 10);   // 세로선은 오른쪽 틈에서만(쌍마다 12px 엇갈림)
      if (T) p.path = HD.route.routeCurve({x: S.x + S.w, y: c.y + c.h / 2, dir: 'right'}, {x: T.x + T.w / 2, y: T.y - 10}, {apex: idx * 16, k: idx, gx: gx});
      idx++;
    }
    out.pairs.push(p);
  });
  return out;
}

// ---------- 상태 하나 + 리듀서(새 상태를 돌려준다. 바뀐 게 없으면 같은 객체)
function initial(sat) {
  return {focusId: null, links: null, stage: 1, on: null, hover: null, sat: sat == null ? 0.7 : sat};
}
function assign(s, patch) {
  var o = {}, k;
  for (k in s) o[k] = s[k];
  for (k in patch) o[k] = patch[k];
  return o;
}
function reduce(s, it) {
  s = s || initial();
  var t = it && it.type;
  if (t === 'focus' || t === 'exitFocus') {          // focus(id): 그 화면으로, 색 1 부터 · exitFocus: 연결 보기 끝
    return assign(s, {focusId: t === 'focus' ? (it.id || null) : null, links: null, stage: 1, on: null, hover: null});
  }
  if (t === 'links') return assign(s, {links: it.links || null});   // 그 화면의 hd-links 답(모델) 도착
  if (t === 'cycle') {                               // 같은 카드 Shift+클릭: 다음 색 → … → 전체 → 색1
    if (!s.links) return s;
    return assign(s, {stage: cycleNext(stageOf(s.links, s), s.links.order.length), on: null, hover: null});
  }
  if (t === 'toggle') {                              // 범례 체크(수동): 다음 Shift+클릭 전까지 그대로
    var on = {}, i;
    if (s.on) { for (i in s.on) on[i] = s.on[i]; } else visibleOf(s.links, s).forEach(function (x, j) { on[j] = x; });
    on[it.k] = !on[it.k];
    return assign(s, {on: on, hover: null});
  }
  if (t === 'hover') return it.k === s.hover ? s : assign(s, {hover: it.k});
  if (t === 'setSat') return assign(s, {sat: Math.max(0.2, Math.min(1.2, +it.v || 0.7))});
  return s;
}

HD.focus = {LINK_COLORS: LINK_COLORS, hueOf: hueOf, satHex: satHex, assignColors: assignColors, cycleNext: cycleNext,
            stageOf: stageOf, visibleOf: visibleOf, deriveView: deriveView, initial: initial, reduce: reduce};
})();
