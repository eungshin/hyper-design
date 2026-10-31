/* Model — 떠 있는 층 목록 하나의 닫기 규칙(U1, 10-31 — Figma·FigJam 관례): Esc·바깥 누르기·같은 것 다시 누르기 = 맨 위 한 층만. DOM·저장소·메시지를 쓰지 않는다.
   층 = {id, open, hit, keep} — 목록은 아래 → 위(쌓임 차례, z 가 작은 것 먼저)로 받는다. 맨 위 = 열린 것 중 마지막.
     hit = 그 누르기가 그 층에 무엇인가: 'inside'(층 안) · 'opener'(그 층을 여는 것 — 배지·핀: 누르기는 그쪽 click 이 정한다, 같은 것이면 닫음)
           · 'outside'(바깥 = 닫기) · 'ignore'(이 층은 이 자리 누르기로 닫히지 않는다 — 크게 보기는 덮개만 바깥, 위 막대·도크는 아님)
     keep = 사람이 쓴 글이 있어 바깥 누르기로 닫지 않는다(쓰던 글을 잃지 않는다). Esc 는 keep 이어도 닫는다 — 글은 층 주인이 stash 로 지켜 다시 열면 되살린다.
   esc(layers) → 닫을 층 id | null · press(layers) → {close: id|null, top: 누르기 때 맨 위 id|null} · top(layers) → id|null
   쓰던 글 자리(stash·take): 닫을 때 글을 그 대상 열쇠로 하나 맡겨 두고, 같은 열쇠로 다시 열면 한 번 돌려준다(빈 글은 맡기지 않는다).
   HD.floatStack = {top, esc, press, stash(slot, key, text) → 새 slot, take(slot, key) → {text|null, slot}} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var HITS = ['inside', 'opener', 'outside', 'ignore'];

function list(layers) { return Array.isArray(layers) ? layers.filter(function (l) { return l && typeof l === 'object' && l.id != null; }) : []; }
function topOf(layers) {
  var ls = list(layers);
  for (var i = ls.length - 1; i >= 0; i--) if (ls[i].open) return ls[i];
  return null;
}
function top(layers) { var t = topOf(layers); return t ? t.id : null; }
function esc(layers) { return top(layers); }
function press(layers) {                              // 맨 위 층 하나만 본다 — 그 아래 층은 이 누르기로 닫히지 않는다
  var t = topOf(layers); if (!t) return {close: null, top: null};
  var hit = HITS.indexOf(t.hit) >= 0 ? t.hit : 'outside';   // 모르는 값 = 바깥(닫기 쪽이 안전 — 떠 있는 것이 남아 겹치지 않게)
  return {close: hit === 'outside' && !t.keep ? t.id : null, top: t.id};
}
function stash(slot, key, text) {
  if (key == null || typeof text !== 'string' || !text.trim()) return slot || null;
  return {key: String(key), text: text};
}
function take(slot, key) {
  if (!slot || key == null || slot.key !== String(key)) return {text: null, slot: slot || null};
  return {text: slot.text, slot: null};
}

HD.floatStack = {top: top, esc: esc, press: press, stash: stash, take: take};
})();
