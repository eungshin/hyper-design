/* Model — 고른 카드 맞추기·분배·늘어놓기 계산(정렬 패널·폴더 늘어놓기). DOM·저장소를 쓰지 않는다.
   상자 boxes = [{id, x, y, w, h}](판 단위 px). 기준 = 고른 상자들을 다 덮는 상자(일러스트 "선택에 맞춤").
   모든 계산은 옮길 양 {id: [mx, my]} 를 돌려준다 — 정수로 반올림, 0 인 것은 뺀다.
   bounds(boxes) → {x, y, w, h}
   align(boxes, how)  how = left|hcenter|right|top|vcenter|bottom · 2개 미만 → {}
   distribute(boxes, axis)  axis = x|y · 위치 순으로 첫·끝은 그대로, 이웃 가장자리 사이 틈을 같게(겹치면 음수 틈) · 3개 미만 → {}
   stack(boxes, axis, gap, cross)  위치 순(같으면 다른 축, 그다음 넣은 순)으로 한 줄(x)·한 칸(y)에 gap 띄워 늘어놓기.
     첫 상자는 그대로. gap: 음수 → 0, 숫자 아님 → 80. cross: 'start'(기본: 줄이면 위, 칸이면 왼쪽을 첫 상자에 맞춤) | 'none'(그대로) · 2개 미만 → {}
   HD.align = {bounds, align, distribute, stack} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var HOWS = ['left', 'hcenter', 'right', 'top', 'vcenter', 'bottom'];
var GAP = 80;

function list(boxes) { return Array.isArray(boxes) ? boxes.filter(function (b) { return b && b.id != null; }) : []; }
function bounds(boxes) {
  var bs = list(boxes), x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  if (!bs.length) return {x: 0, y: 0, w: 0, h: 0};
  bs.forEach(function (b) {
    x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
    x1 = Math.max(x1, b.x + b.w); y1 = Math.max(y1, b.y + b.h);
  });
  return {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
}
// 옮길 양 하나 넣기(반올림 뒤 0 이면 뺌, -0 도 0)
function put(out, id, mx, my) {
  var rx = Math.round(mx) || 0, ry = Math.round(my) || 0;
  if (rx || ry) out[id] = [rx, ry];
}
function align(boxes, how) {
  var bs = list(boxes), out = {}, B;
  if (bs.length < 2 || HOWS.indexOf(how) < 0) return out;
  B = bounds(bs);
  bs.forEach(function (b) {
    var mx = 0, my = 0;
    if (how === 'left') mx = B.x - b.x;
    else if (how === 'hcenter') mx = (B.x + B.w / 2) - (b.x + b.w / 2);
    else if (how === 'right') mx = (B.x + B.w) - (b.x + b.w);
    else if (how === 'top') my = B.y - b.y;
    else if (how === 'vcenter') my = (B.y + B.h / 2) - (b.y + b.h / 2);
    else my = (B.y + B.h) - (b.y + b.h);
    put(out, b.id, mx, my);
  });
  return out;
}
// 위치 순 정렬: 축 좌표 → 다른 축 좌표 → 넣은 순
function order(bs, axis) {
  var p = axis === 'y' ? 'y' : 'x', q = p === 'x' ? 'y' : 'x';
  return bs.map(function (b, i) { return {b: b, i: i}; }).sort(function (a, c) {
    return (a.b[p] - c.b[p]) || (a.b[q] - c.b[q]) || (a.i - c.i);
  }).map(function (o) { return o.b; });
}
function distribute(boxes, axis) {
  var bs = list(boxes), out = {}, p, s, first, last, span, total = 0, gap, cur;
  if (bs.length < 3 || (axis !== 'x' && axis !== 'y')) return out;
  p = axis; s = p === 'x' ? 'w' : 'h';
  bs = order(bs, p); first = bs[0]; last = bs[bs.length - 1];
  span = (last[p] + last[s]) - first[p];
  bs.forEach(function (b) { total += b[s]; });
  gap = (span - total) / (bs.length - 1);
  cur = first[p] + first[s] + gap;
  for (var i = 1; i < bs.length - 1; i++) {
    var d = cur - bs[i][p];
    put(out, bs[i].id, p === 'x' ? d : 0, p === 'y' ? d : 0);
    cur += bs[i][s] + gap;
  }
  return out;
}
function stack(boxes, axis, gap, cross) {
  var bs = list(boxes), out = {}, p, q, s, g, first, cur;
  if (bs.length < 2 || (axis !== 'x' && axis !== 'y')) return out;
  g = typeof gap === 'number' && isFinite(gap) ? Math.max(0, gap) : GAP;
  p = axis; q = p === 'x' ? 'y' : 'x'; s = p === 'x' ? 'w' : 'h';
  bs = order(bs, p); first = bs[0];
  cur = first[p] + first[s] + g;
  for (var i = 1; i < bs.length; i++) {
    var b = bs[i], d = cur - b[p], c = cross === 'none' ? 0 : first[q] - b[q];
    put(out, b.id, p === 'x' ? d : c, p === 'y' ? d : c);
    cur += b[s] + g;
  }
  return out;
}

HD.align = {bounds: bounds, align: align, distribute: distribute, stack: stack};
})();
