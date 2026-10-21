/* Model — 연결선 모양(순수 기하). 둥근 직각선: 가로·세로만, 꺾이는 곳마다 원호(Q) 하나. */
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

HD.route = {RADIUS: RADIUS, roundPath: roundPath, routeCurve: routeCurve};
})();
