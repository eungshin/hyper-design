/* Model — 메모 창(#pop) 자리·크기 규칙(#223): 저장 글 읽기·쓰기, 화면 안으로 맞추기, 가장 작은 크기. DOM·저장소를 쓰지 않는다.
   자리 = {x, y, w, h}(화면 px, 정수). 저장 키는 View 가 가진다(hd-pop, 모든 캔버스 공용).
   parse(text) → {place: 자리|null, bad: 저장 글이 있는데 깨졌나}   없으면 {place:null, bad:false}
   clamp(p, vw, vh) → 자리   크기 = 가장 작은 크기(MIN) 이상·창(여백 MARGIN 양쪽) 이하(창이 MIN 보다 작으면 MIN), 자리 = 창 안
   serialize(p) → 저장 글
   HD.popPlace = {MIN, MARGIN, parse, clamp, serialize} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MIN = {w: 260, h: 160}, MARGIN = 8;

function num(v) { return typeof v === 'number' && isFinite(v); }
function valid(p) { return !!p && typeof p === 'object' && num(p.x) && num(p.y) && num(p.w) && num(p.h); }

function parse(text) {
  if (text == null || text === '') return {place: null, bad: false};
  var v = null;
  try { v = JSON.parse(text); } catch (e) { return {place: null, bad: true}; }
  if (!valid(v)) return {place: null, bad: true};
  return {place: {x: v.x, y: v.y, w: v.w, h: v.h}, bad: false};
}

function fit(size, min, room) { return Math.round(Math.max(min, Math.min(size, room))); }
function clamp(p, vw, vh) {
  var w = fit(p.w, MIN.w, vw - 2 * MARGIN), h = fit(p.h, MIN.h, vh - 2 * MARGIN);
  var x = Math.round(Math.max(MARGIN, Math.min(p.x, vw - MARGIN - w)));
  var y = Math.round(Math.max(MARGIN, Math.min(p.y, vh - MARGIN - h)));
  return {x: x, y: y, w: w, h: h};
}

function serialize(p) { return JSON.stringify({x: Math.round(p.x), y: Math.round(p.y), w: Math.round(p.w), h: Math.round(p.h)}); }

HD.popPlace = {MIN: MIN, MARGIN: MARGIN, parse: parse, clamp: clamp, serialize: serialize};
})();
