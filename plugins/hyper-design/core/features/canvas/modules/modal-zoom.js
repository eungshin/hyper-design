/* Model — 크게 보기 확대·굴림 규칙(R57 C): 열 때 배율(폭 맞추기, 100% 상한) · 창 크기(내용만큼, 칸까지) · 굴림 범위 · 커서 자리 확대 · 단계 · 휠. DOM·저장소를 쓰지 않는다.
   cw·ch = 화면(카드) CSS px · aw·ah = 창이 쓸 수 있는 칸 · s = 배율 · sb = 굴림 막대 두께(px, 없으면 0) · x·y = 창 안 굴림(scrollLeft·scrollTop)
   MIN 0.1 · MAX 4 · STOPS = Ctrl+= / Ctrl+- 단계(브라우저 배율 단계처럼)
   clamp(s) → MIN~MAX(숫자가 아니면 1)
   fit(cw, ch, aw, ah, sb?) → 열 때 배율 = 폭 맞추기(≤ 1). 다만 화면 전체를 보이는 배율이 폭 맞추기의 TALL(3/4) 이상이면 전체(짧은 화면 — 폰·데스크톱은 지금처럼 한눈에)
   view(cw, ch, s, aw, ah, sb?) → {w, h} 창 크기 = 내용 + (굴리는 쪽 막대) 를 칸까지
   scroll(cw, ch, s, v, x, y) → {x, y} 0 ~ (내용 − 창) 로 자름(정수)
   at(st{cw, ch, s, x, y, aw, ah, sb?}, s2, p{x, y}) → {s, x, y, w, h}   커서 자리 확대 — p = 창 가운데에서 커서까지(창은 칸 가운데에 있고 크기만 바뀐다).
     창이 칸에 꽉 찬 쪽은 커서 밑 내용 점이 그대로, 아직 자라는 쪽은 가운데 기준
   step(s, dir) → 다음 단계(dir 1 = 확대, -1 = 축소, 끝이면 끝) · wheel(s, dy) → 판 Ctrl+휠과 같은 비율(exp(-dy·0.0022)) · pct(s) → '76%'
   HD.modalZoom = {MIN, MAX, STOPS, TALL, clamp, fit, view, scroll, at, step, wheel, pct} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MIN = 0.1, MAX = 4, TALL = 0.75, EPS = 1e-6;
var STOPS = [0.1, 0.25, 0.33, 0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.5, 3, 4];

function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
function clamp(s) { s = num(s, 1); return Math.min(MAX, Math.max(MIN, s)); }
function fit(cw, ch, aw, ah, sb) {
  sb = num(sb, 0);
  var all = Math.min(1, ah / ch, aw / cw), w = Math.min(1, aw / cw);
  if (ch * w > ah + EPS) w = Math.min(1, (aw - sb) / cw);   // 굴리면 막대 자리만큼
  return clamp(all >= TALL * w - EPS ? all : w);
}
function view(cw, ch, s, aw, ah, sb) {
  sb = num(sb, 0);
  var iw = Math.floor(cw * s + EPS), ih = Math.floor(ch * s + EPS), needV = ih > ah;
  var w = Math.min(iw + (needV ? sb : 0), aw), needH = iw > w - (needV ? sb : 0);
  return {w: w, h: Math.min(ih + (needH ? sb : 0), ah)};
}
function scroll(cw, ch, s, v, x, y) {
  var mx = Math.max(0, Math.round(cw * s) - v.w), my = Math.max(0, Math.round(ch * s) - v.h);
  return {x: Math.round(Math.min(mx, Math.max(0, num(x, 0)))), y: Math.round(Math.min(my, Math.max(0, num(y, 0))))};
}
function at(st, s2, p) {
  var s = clamp(s2), v1 = view(st.cw, st.ch, st.s, st.aw, st.ah, st.sb), v2 = view(st.cw, st.ch, s, st.aw, st.ah, st.sb);
  var cx = (num(st.x, 0) + p.x + v1.w / 2) / st.s, cy = (num(st.y, 0) + p.y + v1.h / 2) / st.s;
  var c = scroll(st.cw, st.ch, s, v2, cx * s - (p.x + v2.w / 2), cy * s - (p.y + v2.h / 2));
  return {s: s, x: c.x, y: c.y, w: v2.w, h: v2.h};
}
function step(s, dir) {
  s = clamp(s);
  var i;
  if (dir > 0) { for (i = 0; i < STOPS.length; i++) if (STOPS[i] > s + 1e-3) return STOPS[i]; return MAX; }
  for (i = STOPS.length - 1; i >= 0; i--) if (STOPS[i] < s - 1e-3) return STOPS[i];
  return MIN;
}
function wheel(s, dy) { return clamp(clamp(s) * Math.exp(-num(dy, 0) * 0.0022)); }
function pct(s) { return Math.round(clamp(s) * 100) + '%'; }

HD.modalZoom = {MIN: MIN, MAX: MAX, STOPS: STOPS, TALL: TALL, clamp: clamp, fit: fit, view: view, scroll: scroll, at: at, step: step, wheel: wheel, pct: pct};
})();
