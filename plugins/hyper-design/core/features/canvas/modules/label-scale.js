/* Model — 판 위 이름표(카드 제목·줄 제목·메모 배지·선 태그·AI 수정 중 칩)를 화면에서 늘 같은 크기로 두는 배율 규칙(R27 F01, Figma 프레임 이름처럼). DOM 을 쓰지 않는다.
   판은 #stage 의 scale(z) 로 커지고 작아진다 — 이름표는 CSS 변수 --lz = 1/z 를 곱해 그 배율을 되돌린다(크기는 화면 px 로 고정, 판 배치는 그대로).
   HD.labelScale = {inv(z) → 1/z | null(z 가 0 보다 큰 수가 아님), fmt(v) → 소수 4자리 글, put(old, next, exact) → 새 값을 쓸지, STEP}
     put: exact(확대·이동이 멈춘 뒤) = 글이 다르면 · 아니면(확대 중, 한 프레임에 한 번) old 와 STEP(3%) 넘게 다를 때만 — #rows 아래 전체 스타일 다시 계산을 줄인다.
     old 가 없거나 수가 아니면 늘 쓴다
   stack(rects, gap) → [dy] (R27 F08) — 화면 px 상자 [{l, t, r, b}] 가 서로 겹치지 않게 아래로 밀 거리(입력 차례대로). 위·왼쪽 것부터 자리를 잡고,
     뒤 것은 앞 것과 가로가 겹치는 동안 그 아래 + gap 으로 내려간다. 깨진 상자는 0(움직이지 않음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var STEP = 0.03;

function inv(z) {
  var n = typeof z === 'string' ? parseFloat(z) : z;
  return typeof n === 'number' && isFinite(n) && n > 0 ? 1 / n : null;
}
function fmt(v) { return (+v).toFixed(4); }
function put(old, next, exact) {
  var o = typeof old === 'string' ? parseFloat(old) : old;
  if (typeof next !== 'number' || !isFinite(next) || next <= 0) return false;
  if (typeof o !== 'number' || !isFinite(o) || o <= 0) return true;
  if (exact) return fmt(o) !== fmt(next);
  return Math.abs(next / o - 1) > STEP;
}

function ok(q) { return q && [q.l, q.t, q.r, q.b].every(function (v) { return typeof v === 'number' && isFinite(v); }) && q.r >= q.l && q.b >= q.t; }
function stack(rects, gap) {
  var list = Array.isArray(rects) ? rects : [], g = typeof gap === 'number' && isFinite(gap) && gap >= 0 ? gap : 2, out = list.map(function () { return 0; }), placed = [];
  var order = list.map(function (q, i) { return i; }).filter(function (i) { return ok(list[i]); })
    .sort(function (a, b) { return list[a].t - list[b].t || list[a].l - list[b].l || a - b; });
  order.forEach(function (i) {
    var q = list[i], dy = 0, moved = true, guard = 0;
    while (moved && guard++ <= placed.length) {
      moved = false;
      for (var k = 0; k < placed.length; k++) {
        var p = placed[k];
        if (q.l < p.r && q.r > p.l && q.t + dy < p.b + g && q.b + dy + g > p.t) { dy = p.b + g - q.t; moved = true; }
      }
    }
    out[i] = dy;
    placed.push({l: q.l, r: q.r, t: q.t + dy, b: q.b + dy});
  });
  return out;
}

HD.labelScale = {inv: inv, fmt: fmt, put: put, STEP: STEP, stack: stack};
})();
