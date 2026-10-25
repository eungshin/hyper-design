/* Model — 끌어서 순서 바꾸기 규칙(task 49c): 형제 상자들 위 포인터 → 끼울 자리(slot) · 끼울 선 · 위/아래 옮기기 목록. DOM·저장소·메시지를 쓰지 않는다.
   rects = 같은 부모의 형제 요소 상자(문서 차례, {x, y, w, h} — 화면 좌표든 틀 좌표든 한 가지로) · slot = 끼울 자리 0..n(k = k번째 형제 앞, n = 맨 뒤)
   HD.reorder = {slot(pt{x, y}, rects) → 0..n | -1(형제 없음), line(slot, rects) → {x, y, w, h, dir:'h'|'v'} | null, target(from, slot) → 옮긴 뒤 자리,
                 moves(from, slot) → ['up'…] | ['down'…] | [](제자리) — 도우미 move op(up|down = 옆 형제와 맞바꿈)를 차례로} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function ok(r) { return !!r && isFinite(r.x) && isFinite(r.y) && isFinite(r.w) && isFinite(r.h) && r.w >= 0 && r.h >= 0; }
function rowMate(a, b) {                              // 같은 줄(가로로 놓인 형제) — 세로로 절반 넘게 겹침
  if (!ok(a) || !ok(b)) return false;
  var ov = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return ov > Math.min(a.h, b.h) / 2;
}
function horiz(rects, i) { return rowMate(rects[i], rects[i - 1]) || rowMate(rects[i], rects[i + 1]); }
function dist(p, r) {                                 // 점과 상자 사이(안이면 0)
  var dx = Math.max(r.x - p.x, 0, p.x - (r.x + r.w)), dy = Math.max(r.y - p.y, 0, p.y - (r.y + r.h));
  return Math.sqrt(dx * dx + dy * dy);
}

// 가장 가까운 형제의 앞쪽 절반이면 그 앞, 뒤쪽 절반이면 그 뒤 — 세로 목록은 y, 가로 줄·격자(같은 줄 형제가 있음)는 x 로 가른다
function slot(pt, rects) {
  if (!pt || !isFinite(pt.x) || !isFinite(pt.y) || !Array.isArray(rects) || !rects.length) return -1;
  var best = -1, bd = Infinity;
  for (var i = 0; i < rects.length; i++) {
    if (!ok(rects[i]) || (!rects[i].w && !rects[i].h)) continue;   // 숨은 형제(0 상자)는 고르지 않는다
    var d = dist(pt, rects[i]);
    if (d < bd) { bd = d; best = i; }
  }
  if (best < 0) return -1;
  var r = rects[best], before = horiz(rects, best) ? pt.x < r.x + r.w / 2 : pt.y < r.y + r.h / 2;
  return before ? best : best + 1;
}

// 끼울 선: 세로 목록 = 두 형제 사이 가로 선(dir 'h') · 가로 줄 = 사이 세로 선(dir 'v'). 두께 2
function line(s, rects) {
  if (!Array.isArray(rects) || !rects.length || !(s >= 0 && s <= rects.length)) return null;
  var a = s > 0 ? rects[s - 1] : null, b = s < rects.length ? rects[s] : null, ref = b || a;
  if (!ok(ref)) return null;
  if (a && b && rowMate(a, b)) return {x: (a.x + a.w + b.x) / 2 - 1, y: Math.min(a.y, b.y), w: 2, h: Math.max(a.h, b.h), dir: 'v'};   // 같은 줄 두 칸 사이
  if (a && horiz(rects, s - 1)) return {x: a.x + a.w + 1, y: a.y, w: 2, h: a.h, dir: 'v'};   // 격자·가로 줄의 줄 끝 = 앞 칸 오른쪽
  if (b && horiz(rects, s)) return {x: b.x - 3, y: b.y, w: 2, h: b.h, dir: 'v'};             // 줄 처음 = 다음 칸 왼쪽
  var y = a && b ? (a.y + a.h + b.y) / 2 : b ? b.y - 2 : a.y + a.h + 2;
  var l = Math.min(a ? a.x : Infinity, b ? b.x : Infinity), r = Math.max(a ? a.x + a.w : -Infinity, b ? b.x + b.w : -Infinity);
  return {x: l, y: y - 1, w: r - l, h: 2, dir: 'h'};
}

function target(from, s) { return s > from ? s - 1 : s; }
function moves(from, s) {
  if (!(from >= 0) || !(s >= 0)) return [];
  var t = target(from, s), out = [];
  for (var i = 0; i < Math.abs(t - from); i++) out.push(t > from ? 'down' : 'up');
  return out;
}

HD.reorder = {slot: slot, line: line, target: target, moves: moves};
})();
