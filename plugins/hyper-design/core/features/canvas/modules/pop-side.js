/* Model — 메모 창 자동 자리(R27 F09, FigJam 메모 쓰기 창처럼 대상 옆): 대상 상자 오른쪽 → 왼쪽 → 아래 → 위 중 들어가는 첫 자리. DOM·저장소를 쓰지 않는다.
   beside(target, size, areas, gap?) → {x, y, side}
     target = {x, y, w, h}(화면 px — 카드·요소·누른 점) · size = {w, h}(창 크기) · areas = [{x, y, w, h}, …] 차례로(판 자리 → 화면 전체) · gap 기본 12
     · 앞 area 에 들어가는 옆자리가 있으면 그것, 없으면 다음 area · 어디에도 없으면 마지막 area 에서 가장 넓은 쪽(side = 그 쪽, 안으로 자름 — 대상을 덮을 수 있음)
     · 옆(오른쪽·왼쪽)은 대상 위쪽 끝에, 아래·위는 대상 왼쪽 끝에 맞추고 area 안으로 자른다. 깨진 값(숫자 아님) = 첫 area 왼쪽 위(side 'none')
   under(anchor, size, view, avoid?, gap?) → {x, y}   (F6 — 메모 묶음 창처럼 배지 아래에 붙는 창)
     anchor = {left, right, top, bottom}(배지·핀 화면 px) · view = {x, y, w, h}(창이 들어갈 곳) · avoid = [{left, top, right, bottom}, …](덮으면 안 되는 상자 — 왼쪽 도구 막대)
     · 배지 아래, 오른쪽 끝을 배지에 맞추고 view 안으로 · 아래 자리가 모자라면 배지 위 · 피할 상자와 겹치면 그 오른쪽(틈 gap), 안 들어가면 왼쪽, 둘 다 안 되면 그대로
     · gap 기본 6 · 깨진 anchor·size = view 왼쪽 위(던지지 않음) · 깨진 피할 상자는 건너뜀
   HD.popSide = {GAP, beside, under} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var GAP = 12;

function num(v) { return typeof v === 'number' && isFinite(v); }
function box(b) { return !!b && num(b.x) && num(b.y) && num(b.w) && num(b.h); }
function clip(v, lo, hi) { return Math.round(hi < lo ? lo : Math.max(lo, Math.min(hi, v))); }

function spots(t, s, a, g) {                          // 네 옆자리와 그쪽 남는 폭(room) — 들어가면 fits
  var R = a.x + a.w, B = a.y + a.h;
  var ys = clip(t.y, a.y, B - s.h), xs = clip(t.x, a.x, R - s.w);
  return [
    {side: 'right', x: t.x + t.w + g, y: ys, room: R - (t.x + t.w + g), need: s.w},
    {side: 'left', x: t.x - g - s.w, y: ys, room: (t.x - g) - a.x, need: s.w},
    {side: 'below', x: xs, y: t.y + t.h + g, room: B - (t.y + t.h + g), need: s.h},
    {side: 'above', x: xs, y: t.y - g - s.h, room: (t.y - g) - a.y, need: s.h}];
}

function beside(target, size, areas, gap) {
  var g = num(gap) ? gap : GAP, list = (areas || []).filter(box);
  if (!box(target) || !size || !num(size.w) || !num(size.h) || !list.length) {
    var f = list[0] || {x: 8, y: 8};
    return {x: Math.round(f.x), y: Math.round(f.y), side: 'none'};
  }
  for (var i = 0; i < list.length; i++) {
    var a = list[i], ss = spots(target, size, a, g);
    for (var k = 0; k < ss.length; k++) {
      if (ss[k].room >= ss[k].need && inside(ss[k], size, a)) return {x: Math.round(ss[k].x), y: Math.round(ss[k].y), side: ss[k].side};
    }
  }
  var last = list[list.length - 1], best = spots(target, size, last, g).sort(function (p, q) { return (q.room / q.need) - (p.room / p.need); })[0];
  return {x: clip(best.x, last.x, last.x + last.w - size.w), y: clip(best.y, last.y, last.y + last.h - size.h), side: best.side};
}
function inside(p, s, a) { return p.x >= a.x && p.y >= a.y && p.x + s.w <= a.x + a.w && p.y + s.h <= a.y + a.h; }

function edges(b) { return !!b && num(b.left) && num(b.right) && num(b.top) && num(b.bottom); }
function under(anchor, size, view, avoid, gap) {
  var g = num(gap) ? gap : 6, v = box(view) ? view : {x: 8, y: 8, w: 0, h: 0};
  if (!edges(anchor) || !size || !num(size.w) || !num(size.h)) return {x: Math.round(v.x), y: Math.round(v.y)};
  var R = v.x + v.w, B = v.y + v.h, w = size.w, h = size.h;
  var x = clip(anchor.right - w, v.x, R - w), y = anchor.bottom + g;
  if (y + h > B) y = Math.max(v.y, anchor.top - g - h);
  (avoid || []).filter(edges).forEach(function (a) {
    if (!(x < a.right && a.left < x + w && y < a.bottom && a.top < y + h)) return;   // 겹치지 않으면 그대로
    if (a.right + g + w <= R) x = a.right + g;
    else if (a.left - g - w >= v.x) x = a.left - g - w;
  });
  return {x: Math.round(x), y: Math.round(y)};
}

HD.popSide = {GAP: GAP, beside: beside, under: under};
})();
