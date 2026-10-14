/* ViewModel — 연결 보기 상태 하나 + 순수 리듀서, 그리고 상태 → 보일 것(deriveView). DOM 없음.
   상태 {focusId, links, stage, on, hover, sat}
     focusId : Shift+클릭한 화면 id(없으면 null)   links : 그 화면의 색 링크 모델(assignColors 결과 + from/titles…)
     stage   : 0 = 전체, 1..n = 대상 그룹 하나       on    : 범례 체크(그룹 k → bool, 수동, 다음 Shift+클릭 전까지)
     hover   : 마우스가 올라간 그룹 k             sat   : 채도 배율
   그룹 = 같은 대상 화면으로 가는 링크 묶음(k = 색 = 처음 나온 순서).
   의도 {type:'focus', id} · {type:'exitFocus'} · {type:'cycle'} · {type:'toggle', k} · {type:'all', on} · {type:'hover', k} · {type:'setSat', v} · {type:'links', links} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var TAG_MAX = 14;                                  // 선 위 태그·범례 제목에서 버튼 글 하나의 최대 글자 수(넘으면 …)
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
// 같은 대상끼리 한 그룹(그룹 k = 색 k = 처음 나온 순서). items 의 번호 목록 · 버튼 글 · 태그 글(A · B (2))
function groupsOf(m) {
  if (!m || !m.items) return [];
  return m.order.map(function (to, k) {
    var idx = [], texts = [];
    m.items.forEach(function (it, i) { if (it.ci === k) { idx.push(i); texts.push(it.text || '(링크)'); } });
    var cnt = idx.length > 1 ? ' (' + idx.length + ')' : '', sh = texts.map(short);
    return {k: k, to: to, items: idx, texts: texts, text: texts.join(' · ') + cnt, tag: sh.join(' · ') + cnt, short: sh.join(' · ')};
  });
}
function short(t) { t = String(t).replace(/\s+/g, ' ').trim(); return t.length > TAG_MAX ? t.slice(0, TAG_MAX - 1).trim() + '…' : t; }
// 같은 카드를 Shift+클릭할 때마다: 전체(0) → 그룹1 → 그룹2 → … → 그룹n → 전체. 그룹이 하나뿐이면 늘 전체.
function cycleNext(stage, n) {
  if (!(n > 1)) return 0;
  if (stage == null || stage === 0) return 1;
  return stage >= n ? 0 : stage + 1;
}
// 실제로 보이는 단계 · 그룹마다 보임(deriveView 와 같은 규칙). 처음(Shift+클릭으로 들어옴)은 전체.
function stageOf(m, ui) {
  if (!m || !m.items || !m.items.length) return 0;
  var n = m.order.length;
  return n <= 1 || ui.stage == null || ui.stage > n ? 0 : ui.stage;
}
function visibleOf(m, ui) {
  if (!m || !m.items || !m.items.length) return [];
  var stage = stageOf(m, ui);
  return m.order.map(function (t, k) { return ui.on ? !!ui.on[k] : stage === 0 || k === stage - 1; });
}

/* Model + UI 상태(단계·체크·마우스·채도) → 보일 것. DOM 없음.
   m.geom(있으면) = {src:{x,y,w,h,sc}, rowTop, cap, left, srcRow, targets:{id:{x,y,w,h,rowTop,cap,row}}, tags:{k:{w,h}}}
   → {groups:[{k,to,color,n,text,paths,pts,tag,lane,emph,dim}], legend:{title, all:'on'|'off'|'mixed', rows}, rings, dimCards, stage, nGroups, visible, groupOf} */
function deriveView(m, ui) {
  ui = ui || {};
  var out = {groups: [], legend: null, rings: {}, dimCards: [], stage: 0, nGroups: 0, visible: [], groupOf: []};
  if (!m || !m.items || !m.items.length) return out;
  var gs = groupsOf(m), n = gs.length, stage = stageOf(m, ui);
  var sat = ui.sat == null ? 0.7 : ui.sat, hv = ui.hover == null ? null : ui.hover;
  var title = function (id) { return (m.titles && m.titles[id]) || id; };
  var col = gs.map(function (g) { return satHex(m.targets[g.to].color, sat); });
  var vis = visibleOf(m, ui), nOn = vis.filter(Boolean).length;
  if (hv != null && !vis[hv]) hv = null;
  out.stage = stage; out.nGroups = n; out.visible = vis;
  out.groupOf = m.items.map(function (it) { return it.ci; });
  var head = title(m.from) + ' · ';
  out.legend = {
    title: head + (ui.on ? '직접 선택 ' + nOn + '/' + n : stage === 0 ? '전체 ' + n + '개' : stage + '/' + n + ' ' + gs[stage - 1].short),
    all: nOn === n ? 'on' : nOn === 0 ? 'off' : 'mixed',
    rows: gs.map(function (g, k) { return {k: k, color: col[k], from: title(m.from), text: g.text, to: title(g.to), checked: vis[k], emph: hv === k, dim: hv != null && hv !== k}; })};
  var hvTo = hv == null ? null : gs[hv].to;
  gs.forEach(function (g, k) {
    if (vis[k]) out.rings[g.to] = {color: col[k], n: m.targets[g.to].n, emph: hvTo === g.to, dim: hvTo != null && hvTo !== g.to};
  });
  m.order.forEach(function (t) { if (!out.rings[t]) out.dimCards.push(t); });
  var geo = m.geom, shown = gs.filter(function (g, k) { return vis[k]; }), planned = {}, tags = {};
  if (geo) {
    var S = geo.src, sc = S.sc || 1;
    var pl = HD.route.plan({src: S, rowTop: geo.rowTop, cap: geo.cap, left: geo.left,
      groups: shown.filter(function (g) { return geo.targets && geo.targets[g.to]; }).map(function (g) {
        var T = geo.targets[g.to];
        return {k: g.k, to: g.to, target: T, sameRow: T.row === geo.srcRow, members: g.items.map(function (i) {
          var r = m.items[i].rect; return {x: S.x + r.x * sc, y: S.y + r.y * sc, w: r.w * sc, h: r.h * sc}; })};
      })});
    pl.forEach(function (p) { planned[p.k] = p; });
    var verts = [];
    pl.forEach(function (p) { p.verticals.forEach(function (v) { verts.push({k: p.k, x: v.x, y0: v.y0, y1: v.y1}); }); });
    HD.labels.placeTags(pl.map(function (p) {
      var sz = (geo.tags && geo.tags[p.k]) || {w: 120, h: 28};
      return {k: p.k, segs: p.laneSegs, w: sz.w, h: sz.h};
    }), verts).forEach(function (t) { tags[t.k] = t; });
  }
  shown.forEach(function (g) {
    var p = planned[g.k] || null;
    out.groups.push({k: g.k, from: m.from, to: g.to, color: col[g.k], n: m.targets[g.to].n, text: g.text, tagText: g.tag, count: g.items.length,
      items: g.items, paths: p ? p.d : [], pts: p ? p.pts : [], lane: p ? p.laneSeg : null, side: p ? p.side : null,
      tag: tags[g.k] || null, emph: hv === g.k, dim: hv != null && hv !== g.k});
  });
  return out;
}

// ---------- 상태 하나 + 리듀서(새 상태를 돌려준다. 바뀐 게 없으면 같은 객체)
function initial(sat) {
  return {focusId: null, links: null, stage: 0, on: null, hover: null, sat: sat == null ? 0.7 : sat};
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
  if (t === 'focus' || t === 'exitFocus') {          // focus(id): 그 화면으로, 전체부터 · exitFocus: 연결 보기 끝
    return assign(s, {focusId: t === 'focus' ? (it.id || null) : null, links: null, stage: 0, on: null, hover: null});
  }
  if (t === 'links') return assign(s, {links: it.links || null});   // 그 화면의 hd-links 답(모델) 도착
  if (t === 'cycle') {                               // 같은 카드 Shift+클릭: 전체 → 그룹1 → … → 그룹n → 전체
    if (!s.links) return s;
    return assign(s, {stage: cycleNext(stageOf(s.links, s), s.links.order.length), on: null, hover: null});
  }
  if (t === 'toggle' || t === 'all') {               // 범례 체크(그룹 k 하나 · 모두 표시, 수동): 다음 Shift+클릭 전까지 그대로
    if (!s.links) return s;
    var on = {}, i, n = s.links.order.length;
    if (s.on) { for (i in s.on) on[i] = s.on[i]; } else visibleOf(s.links, s).forEach(function (x, j) { on[j] = x; });
    if (t === 'all') { for (i = 0; i < n; i++) on[i] = !!it.on; } else on[it.k] = !on[it.k];
    return assign(s, {on: on, hover: null});
  }
  if (t === 'hover') return it.k === s.hover ? s : assign(s, {hover: it.k});
  if (t === 'setSat') return assign(s, {sat: Math.max(0.2, Math.min(1.2, +it.v || 0.7))});
  return s;
}

HD.focus = {LINK_COLORS: LINK_COLORS, hueOf: hueOf, satHex: satHex, assignColors: assignColors, groupsOf: groupsOf, cycleNext: cycleNext,
            stageOf: stageOf, visibleOf: visibleOf, deriveView: deriveView, initial: initial, reduce: reduce};
})();
