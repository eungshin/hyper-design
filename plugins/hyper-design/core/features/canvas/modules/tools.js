/* ViewModel — 왼쪽 도구 막대의 도구 규칙(한 곳). DOM·저장소·메시지를 쓰지 않는다.
   도구마다: 키 · 카드 안 요소를 고르는 방식(hit) · 마우스를 올린 요소에 테두리를 그릴지.
     hit: null = 요소를 고르지 않음 · 'click' = 누를 수 있는 요소(링크 → 버튼 → 그 요소) · 'leaf' = 글자를 가진 그 요소 · 'any' = 그 자리 요소
   메모(말풍선 한 칸, 2026-10-29) = 두 모드: P = 요소(el, 누른 요소에 메모) · M = 화면(screen, 누른 카드 화면 전체) — byKey 는 둘 다 'memo', 모드는 modeOfKey.
     누른 곳 memoTarget(mode, inPhone): 카드 제목 줄·테두리 띠(.phone 밖, 카드 안) = 모드와 상관없이 'screen'. 모르는 모드 = 'el'(memoMode).
   hoverOf(tool, {only, typing, mode, edge}) → 마우스를 올린 카드 안에서 다음 클릭이 고를 것을 미리 그릴 방식(51-3, Figma F10): 요소 도구 = hitOf ·
     선택(V) = 그 카드만 골라져 있을 때(only) 'click'(view-elbox pickAt 과 같은 규칙) · 메모 = 'any'(요소) | 'screen'(카드 전체 테두리, 화면 모드 · edge = .phone 밖) ·
     그 카드에서 글자를 고치는 중(typing) = null
   이름표: elLabel(kind) = '<종류> · 요소' · screenLabel(title) = '<화면 이름> · 화면 전체' · 메모 칸 memoTip(mode) → {tip, key, corner, aria}
   HD.tools = {SPEC, ORDER, MEMO, byKey(k), modeOfKey(k), memoMode(m), hitOf(tool, mode?), hoverOf(tool, o), memoTarget(mode, inPhone), LABEL, elLabel, screenLabel, memoTip} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var SPEC = {
  hand:     {key: 'h', hit: null},
  move:     {key: 'v', hit: null},
  trigger:  {key: 'l', hit: 'click'},
  knife:    {key: 'c', hit: null},
  memo:     {key: 'm', alt: 'p', hit: null},       // 모드마다 hit(MEMO) — P = 요소 · M = 화면
  text:     {key: 't', alt: 'e', hit: 'leaf'},     // T = 포토샵과 같게(G4), E 는 보조
  layout:   {key: 'n', hit: null}
};
var ORDER = ['hand', 'move', 'trigger', 'knife', 'memo', 'text', 'layout'];
var MEMO = {el: {key: 'p', hit: 'any', corner: '요소', name: '요소'}, screen: {key: 'm', hit: null, corner: '화면', name: '화면 전체'}};
// 요소 종류(palette.js hd-hit 의 kind) → 테두리 이름표
var LABEL = {text: '글자', button: '버튼', link: '링크', field: '입력칸', box: '영역'};

function byKey(k) { for (var t in SPEC) if (SPEC[t].key === k || SPEC[t].alt === k) return t; return null; }
function modeOfKey(k) { for (var m in MEMO) if (MEMO[m].key === k) return m; return null; }
function memoMode(m) { return Object.prototype.hasOwnProperty.call(MEMO, m) ? m : 'el'; }
function hitOf(tool, mode) { if (tool === 'memo') return MEMO[memoMode(mode)].hit; return (SPEC[tool] || {}).hit || null; }
function memoTarget(mode, inPhone) { return inPhone && memoMode(mode) === 'el' ? 'element' : 'screen'; }
function hoverOf(tool, o) {
  o = o || {};
  if (o.typing) return null;
  if (tool === 'memo') return memoTarget(o.mode, !o.edge) === 'screen' ? 'screen' : 'any';
  if (o.edge) return null;                           // .phone 밖(제목·테두리)은 메모만 미리 그린다
  if (tool === 'move') return o.only ? 'click' : null;
  return hitOf(tool);
}
function elLabel(kind) { return (LABEL[kind] || '영역') + ' · 요소'; }
function screenLabel(title) { return (title ? String(title) : '화면') + ' · 화면 전체'; }
function memoTip(mode) {
  var m = MEMO[memoMode(mode)], K = m.key.toUpperCase();
  return {key: K, corner: m.corner, aria: '메모 · ' + m.name + ' (' + K + ')',
          tip: '메모 · ' + m.name + '|P = 누른 요소에 · M = 누른 화면 전체에 · 카드 제목·테두리는 늘 화면 전체 · Shift = 더하기'};
}

HD.tools = {SPEC: SPEC, ORDER: ORDER, MEMO: MEMO, LABEL: LABEL, byKey: byKey, modeOfKey: modeOfKey, memoMode: memoMode, hitOf: hitOf, hoverOf: hoverOf,
            memoTarget: memoTarget, elLabel: elLabel, screenLabel: screenLabel, memoTip: memoTip};
})();
