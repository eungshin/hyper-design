/* Model — 연결선 모양(순수 기하). 둥근 직각선: 가로·세로만, 꺾이는 곳마다 원호(Q) 하나. 판의 선 길 찾기(plan)는 지금 상자 자리로. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var RADIUS = 18;                                   // 꺾이는 곳 둥근 반지름(짧은 쪽 선의 절반까지 줄어듦)

// 꺾은선 → 꺾는 곳마다 원호(Q) 하나. 반지름은 짧은 쪽 선의 절반까지.
function roundPath(pts, r) {
  var p = [];
  pts.forEach(function (q) {
    var a = [Math.round(q[0] * 10) / 10, Math.round(q[1] * 10) / 10], l = p[p.length - 1];
    if (l && l[0] === a[0] && l[1] === a[1]) return;
    var l2 = p[p.length - 2];
    if (l2 && ((l2[0] === l[0] && l[0] === a[0]) || (l2[1] === l[1] && l[1] === a[1]))) p.pop();   // 한 줄 위의 가운데 점은 뺀다
    p.push(a);
  });
  var f = function (v) { return String(Math.round(v * 10) / 10); };
  var d = 'M' + f(p[0][0]) + ',' + f(p[0][1]);
  for (var i = 1; i < p.length - 1; i++) {
    var a = p[i - 1], c = p[i], n = p[i + 1];
    var l1 = Math.hypot(c[0] - a[0], c[1] - a[1]), l2 = Math.hypot(n[0] - c[0], n[1] - c[1]);
    var rr = Math.min(r, l1 / 2, l2 / 2);
    if (rr < 0.5) { d += ' L' + f(c[0]) + ',' + f(c[1]); continue; }
    var s = [c[0] - (c[0] - a[0]) / l1 * rr, c[1] - (c[1] - a[1]) / l1 * rr];
    var e = [c[0] + (n[0] - c[0]) / l2 * rr, c[1] + (n[1] - c[1]) / l2 * rr];
    d += ' L' + f(s[0]) + ',' + f(s[1]) + ' Q' + f(c[0]) + ',' + f(c[1]) + ' ' + f(e[0]) + ',' + f(e[1]);
  }
  var z = p[p.length - 1];
  return d + ' L' + f(z[0]) + ',' + f(z[1]);
}
/* 둥근 직각 연결선(가로·세로만, 되돌아가는 고리 없음). 끝은 늘 아래로 대상 카드 위 가운데에 들어간다.
   세로선은 카드 사이 틈(gutter)·줄 위 통로·왼쪽 통로에서만 — 카드 상자 안을 세로로 지나지 않는다.
   src.dir 'up'            : 카드 위에서 위로 → 줄 위 통로(lift+apex) → 가로 → 아래로 (꺾임 2)
   src.dir 'up' + o.laneX  : 다른 줄 — 위로 → 왼쪽 통로로 가로 → 통로 따라 세로 → 대상 줄 위에서 가로 → 아래로 (꺾임 4)
   src.dir 'right'         : 출발 카드 오른쪽 가장자리에서 가로로 틈(o.gx)까지 → 틈 따라 세로 → 대상 줄 위 통로 → 가로 → 아래로 (꺾임 3) */
function routeCurve(src, dst, o) {
  o = o || {};
  var r = o.r || RADIUS, lift = o.lift == null ? 44 : o.lift, apex = o.apex || 0, k = o.k || 0;
  var sx = src.x, sy = src.y, tx = dst.x, ty = dst.y, pts;
  if (src.dir === 'up' && o.laneX != null) {
    var sg = sy - lift - apex, tg = ty - lift - apex;
    pts = [[sx, sy], [sx, sg], [o.laneX, sg], [o.laneX, tg], [tx, tg], [tx, ty]];
  } else if (src.dir === 'up') {
    var top = Math.min(sy, ty) - lift - apex;
    pts = [[sx, sy], [sx, top], [tx, top], [tx, ty]];
  } else {
    var gx = o.gx == null ? sx + 18 + 14 * k : o.gx, lane = ty - lift - apex;
    pts = [[sx, sy], [gx, sy], [gx, lane], [tx, lane], [tx, ty]];
  }
  return roundPath(pts, r);
}

/* 판의 선 길 찾기(task 38) — 쪽은 지금 상자 자리로 고른다(DOM 줄이 아니라). 순수 함수: 상자 = {x, y, w, h}(판 좌표).
   sides(s, t)            → {from, to} — 세로 범위 겹침 = 마주 보는 왼·오른쪽, 가로 범위 겹침 = 위·아래, 둘 다 아님 = 틈이 넓은 쪽 축(꺾임 ≤2), 상자가 겹치면 null
   route(s, t, o)         → {pts, d, from, to, mode:'direct'|'over'|'corridor'} — 곧은 길(가운데 틈에서 꺾음)이 다른 상자를 지날 때만 줄 위로 띄운 길, 그것도 막히면 왼쪽 통로
                            o = {boxes:[상자], lane, corridorX}
   plan(boxes, pairs, o)  → [{a, b, pts, d, from, to, mode, lane}|null] — 앞 선과 같은 줄 위에 겹칠 때만 lane 을 올려 띄운다(출발 순서와 상관없음)
                            boxes = {id: 상자}, pairs = [{a, b}], o = {corridorX, only:{id:1}, prev:[plan 결과]} — only 가 있으면 그 카드에 닿은 선만 다시(끌기), 나머지는 prev 그대로
   overlaps(A, B)         → 두 꺾은선이 같은 줄 위에서 겹치는 마디 수 · length(pts) → 꺾은선 길이 */
var SG = 4, TG = 8, PAD = 8, LIFT = 54, STEP = 14, MAXLANE = 8;
function off(lane) { return lane ? (lane % 2 ? 1 : -1) * Math.ceil(lane / 2) * STEP : 0; }
function cx(b) { return b.x + b.w / 2; }
function cy(b) { return b.y + b.h / 2; }
function sides(s, t) {
  var vo = s.y < t.y + t.h && t.y < s.y + s.h, ho = s.x < t.x + t.w && t.x < s.x + s.w;
  if (vo && ho) return null;
  var horiz = vo || (!ho && Math.max(t.x - s.x - s.w, s.x - t.x - t.w) > Math.max(t.y - s.y - s.h, s.y - t.y - t.h));
  if (horiz) return cx(t) < cx(s) ? {from: 'left', to: 'right'} : {from: 'right', to: 'left'};
  return cy(t) < cy(s) ? {from: 'top', to: 'bottom'} : {from: 'bottom', to: 'top'};
}
function simplify(pts) {                           // 같은 점·한 줄 위 가운데 점을 뺀다
  var p = [];
  pts.forEach(function (a) {
    var l = p[p.length - 1];
    if (l && l[0] === a[0] && l[1] === a[1]) return;
    var l2 = p[p.length - 2];
    if (l2 && ((l2[0] === l[0] && l[0] === a[0]) || (l2[1] === l[1] && l[1] === a[1]))) p.pop();
    p.push(a);
  });
  return p;
}
function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
function direct(s, t, sd, lane) {                   // 마주 보는 두 쪽 사이, 가운데 틈에서 꺾음(꺾임 ≤2)
  var k = off(lane);
  if (sd.from === 'left' || sd.from === 'right') {
    var lo = Math.max(s.y, t.y), hi = Math.min(s.y + s.h, t.y + t.h), sy, ty;
    if (lo < hi) { sy = ty = clamp((lo + hi) / 2 + k, lo + 4, hi - 4); }   // 같은 눈의 줄: 곧게
    else { sy = cy(s) + k; ty = cy(t) + k; }
    var sx = sd.from === 'right' ? s.x + s.w + SG : s.x - SG, tx = sd.to === 'left' ? t.x - TG : t.x + t.w + TG, mx = (sx + tx) / 2 + k;
    return [[sx, sy], [mx, sy], [mx, ty], [tx, ty]];
  }
  var l2 = Math.max(s.x, t.x), h2 = Math.min(s.x + s.w, t.x + t.w), px, qx;
  if (l2 < h2) { px = qx = clamp((l2 + h2) / 2 + k, l2 + 4, h2 - 4); }
  else { px = cx(s) + k; qx = cx(t) + k; }
  var py = sd.from === 'bottom' ? s.y + s.h + SG : s.y - SG, qy = sd.to === 'top' ? t.y - TG : t.y + t.h + TG, my = (py + qy) / 2 + k;
  return [[px, py], [px, my], [qx, my], [qx, qy]];
}
function over(s, t, lane) {                         // 줄 위로 띄운 길: 위로 → 가로 → 아래로 대상 위(꺾임 2)
  var k = off(lane), top = Math.min(s.y, t.y) - LIFT - STEP * lane;
  return [[cx(s) + k, s.y - SG], [cx(s) + k, top], [cx(t) + k, top], [cx(t) + k, t.y - TG]];
}
function corridor(s, t, lane, X) {                  // 왼쪽 통로: 위로 → 통로까지 가로 → 세로 → 대상 위에서 가로 → 아래로(꺾임 4)
  var a = 16 + 10 * (lane % 4), x = X - 22 * lane, sx = s.x + 60, tx = t.x + 60;
  return [[sx, s.y - SG], [sx, s.y - a], [x, s.y - a], [x, t.y - a], [tx, t.y - a], [tx, t.y - TG]];
}
function segHits(a, b, r, pad) {
  return Math.max(a[0], b[0]) > r.x - pad && Math.min(a[0], b[0]) < r.x + r.w + pad &&
         Math.max(a[1], b[1]) > r.y - pad && Math.min(a[1], b[1]) < r.y + r.h + pad;
}
function blocked(pts, boxes, s, t) {                // 다른 상자(PAD 만큼 넓힘)나 양 끝 상자 안을 지나는가
  for (var i = 1; i < pts.length; i++) for (var j = 0; j < boxes.length; j++) {
    var b = boxes[j]; if (segHits(pts[i - 1], pts[i], b, b === s || b === t ? 0 : PAD)) return true;
  }
  return false;
}
function route(s, t, o) {
  o = o || {};
  var lane = o.lane || 0, boxes = o.boxes || [], sd = sides(s, t), cands = [];
  if (sd) {
    cands.push([direct(s, t, sd, lane), sd, 'direct']);
    var vo = s.y < t.y + t.h && t.y < s.y + s.h, ho = s.x < t.x + t.w && t.x < s.x + s.w;
    if (!vo && !ho) {                               // 비껴 선 상자: 다른 축도 곧은 길로 해 본다
      var alt = sd.from === 'left' || sd.from === 'right' ? (cy(t) < cy(s) ? {from: 'top', to: 'bottom'} : {from: 'bottom', to: 'top'})
                                                         : (cx(t) < cx(s) ? {from: 'left', to: 'right'} : {from: 'right', to: 'left'});
      cands.push([direct(s, t, alt, lane), alt, 'direct']);
    }
  }
  cands.push([over(s, t, lane), {from: 'top', to: 'top'}, 'over']);
  var pick = null;
  for (var i = 0; i < cands.length && !pick; i++) if (!blocked(cands[i][0], boxes, s, t)) pick = cands[i];
  var X = o.corridorX == null ? Math.min(s.x, t.x) - 56 : o.corridorX;
  if (!pick) pick = [corridor(s, t, lane, X), {from: 'top', to: 'top'}, 'corridor'];
  var pts = simplify(pick[0]);
  return {pts: pts, d: roundPath(pts, RADIUS), from: pick[1].from, to: pick[1].to, mode: pick[2]};
}
function overlaps(A, B) {                           // 같은 줄(가로 또는 세로, 2px 안) 위에서 2px 넘게 겹치는 마디 수
  var n = 0;
  for (var i = 1; i < A.length; i++) for (var j = 1; j < B.length; j++) {
    var a0 = A[i - 1], a1 = A[i], b0 = B[j - 1], b1 = B[j];
    var ah = a0[1] === a1[1], bh = b0[1] === b1[1], av = a0[0] === a1[0], bv = b0[0] === b1[0];
    if (ah && bh && Math.abs(a0[1] - b0[1]) < 2) {
      if (Math.min(Math.max(a0[0], a1[0]), Math.max(b0[0], b1[0])) - Math.max(Math.min(a0[0], a1[0]), Math.min(b0[0], b1[0])) > 2) n++;
    } else if (av && bv && Math.abs(a0[0] - b0[0]) < 2) {
      if (Math.min(Math.max(a0[1], a1[1]), Math.max(b0[1], b1[1])) - Math.max(Math.min(a0[1], a1[1]), Math.min(b0[1], b1[1])) > 2) n++;
    }
  }
  return n;
}
function length(pts) {
  var L = 0;
  for (var i = 1; i < pts.length; i++) L += Math.abs(pts[i][0] - pts[i - 1][0]) + Math.abs(pts[i][1] - pts[i - 1][1]);
  return L;
}
function plan(boxes, pairs, o) {
  o = o || {};
  var list = Object.keys(boxes).map(function (id) { return boxes[id]; }), minX = Infinity;
  list.forEach(function (b) { minX = Math.min(minX, b.x); });
  var X = Math.min(o.corridorX == null ? Infinity : o.corridorX, minX - 56);
  var only = o.only, prev = {}, out = new Array(pairs.length), placed = [];
  (o.prev || []).forEach(function (r) { if (r) prev[r.a + '>' + r.b] = r; });
  pairs.forEach(function (p, i) {                   // 끌기: 움직인 카드에 닿지 않은 선은 예전 것 그대로(먼저 놓아 겹침 비교에 쓴다)
    var r = only && !only[p.a] && !only[p.b] ? prev[p.a + '>' + p.b] : null;
    if (r) { out[i] = r; placed.push(r.pts); }
  });
  pairs.forEach(function (p, i) {
    if (out[i]) return;
    var s = boxes[p.a], t = boxes[p.b];
    if (!s || !t) { out[i] = null; return; }
    var lane = 0, r;
    for (;;) {
      r = route(s, t, {boxes: list, lane: lane, corridorX: X});
      if (lane >= MAXLANE || !placed.some(function (q) { return overlaps(r.pts, q) > 0; })) break;
      lane++;
    }
    r.a = p.a; r.b = p.b; r.lane = lane;
    out[i] = r; placed.push(r.pts);
  });
  return out;
}

HD.route = {RADIUS: RADIUS, roundPath: roundPath, routeCurve: routeCurve, sides: sides, route: route, plan: plan, overlaps: overlaps, length: length};
})();
