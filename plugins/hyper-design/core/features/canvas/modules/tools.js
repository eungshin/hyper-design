/* ViewModel — 왼쪽 도구 막대의 도구 규칙(한 곳). DOM·저장소·메시지를 쓰지 않는다.
   도구마다: 키 · 카드 안 요소를 고르는 방식(hit) · 마우스를 올린 요소에 테두리를 그릴지.
     hit: null = 요소를 고르지 않음 · 'click' = 누를 수 있는 요소(링크 → 버튼 → 그 요소) · 'leaf' = 글자를 가진 그 요소 · 'any' = 그 자리 요소
   HD.tools = {SPEC, ORDER, byKey(k), hitOf(tool), LABEL} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var SPEC = {
  hand:     {key: 'h', hit: null},
  move:     {key: 'v', hit: null},
  trigger:  {key: 'l', hit: 'click'},
  knife:    {key: 'c', hit: null},
  annotate: {key: 'p', hit: 'any'},
  text:     {key: 'e', hit: 'leaf'},
  layout:   {key: 'n', hit: null},
  memo:     {key: 'm', hit: null}
};
var ORDER = ['hand', 'move', 'trigger', 'knife', 'annotate', 'text', 'layout', 'memo'];
// 요소 종류(palette.js hd-hit 의 kind) → 테두리 이름표
var LABEL = {text: '글자', button: '버튼', link: '링크', field: '입력칸', box: '영역'};

function byKey(k) { for (var t in SPEC) if (SPEC[t].key === k) return t; return null; }
function hitOf(tool) { return (SPEC[tool] || {}).hit || null; }

HD.tools = {SPEC: SPEC, ORDER: ORDER, LABEL: LABEL, byKey: byKey, hitOf: hitOf};
})();
