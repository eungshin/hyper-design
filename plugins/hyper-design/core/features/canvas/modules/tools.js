/* ViewModel — 왼쪽 도구 막대의 도구 규칙(한 곳). DOM·저장소·메시지를 쓰지 않는다.
   도구마다: 키 · 카드 안 요소를 고르는 방식(hit) · 마우스를 올린 요소에 테두리를 그릴지.
     hit: null = 요소를 고르지 않음 · 'click' = 누를 수 있는 요소(링크 → 버튼 → 그 요소) · 'leaf' = 글자를 가진 그 요소 · 'any' = 그 자리 요소
   hoverOf(tool, {only, typing}) → 마우스를 올린 카드 안에서 다음 클릭이 고를 요소를 미리 그릴 방식(51-3, Figma F10): 요소 도구 = hitOf ·
     이동(V) = 그 카드만 골라져 있을 때(only) 'click'(셸 pickElAt 과 같은 규칙) · 그 카드에서 글자를 고치는 중(typing) = null
   HD.tools = {SPEC, ORDER, byKey(k), hitOf(tool), hoverOf(tool, o), LABEL} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var SPEC = {
  hand:     {key: 'h', hit: null},
  move:     {key: 'v', hit: null},
  trigger:  {key: 'l', hit: 'click'},
  knife:    {key: 'c', hit: null},
  annotate: {key: 'p', hit: 'any'},
  text:     {key: 't', alt: 'e', hit: 'leaf'},   // T = 포토샵과 같게(G4), E 는 보조
  layout:   {key: 'n', hit: null},
  memo:     {key: 'm', hit: null}
};
var ORDER = ['hand', 'move', 'trigger', 'knife', 'annotate', 'text', 'layout', 'memo'];
// 요소 종류(palette.js hd-hit 의 kind) → 테두리 이름표
var LABEL = {text: '글자', button: '버튼', link: '링크', field: '입력칸', box: '영역'};

function byKey(k) { for (var t in SPEC) if (SPEC[t].key === k || SPEC[t].alt === k) return t; return null; }
function hitOf(tool) { return (SPEC[tool] || {}).hit || null; }
function hoverOf(tool, o) {
  o = o || {};
  if (o.typing) return null;
  if (tool === 'move') return o.only ? 'click' : null;
  return hitOf(tool);
}

HD.tools = {SPEC: SPEC, ORDER: ORDER, LABEL: LABEL, byKey: byKey, hitOf: hitOf, hoverOf: hoverOf};
})();
