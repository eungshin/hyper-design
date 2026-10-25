/* Model — 선 하나의 투명도 단계(tone): 화살촉(채운 marker)에 stroke-opacity 가 닿지 않아 선과 같은 단계의 화살촉을 고르게(#286). DOM 을 쓰지 않는다.
   단계는 셸 CSS(modules/shell.css)의 선 stroke-opacity 규칙과 같은 차례(선 CSS 를 바꾸면 여기도):
     focusing+on = full · hover+(em|pd) = full · focusing = faint(.18) · hover = hov(투명도 × .4) · pd = full · 나머지 base(투명도 --lnop).
   HD.lineTone = {TONES: ['base','hov','faint','full'], tone({focusing, hover, on, em, pd}) → 단계 이름}
     focusing = 판 강조 중(#rows.focusing) · hover = 카드에 올림(#rows.lnhov) · on = 강조된 선 · em = 올린 카드의 선 · pd = 반영 대기 점선 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var TONES = ['base', 'hov', 'faint', 'full'];

function tone(s) {
  s = s || {};
  if (s.focusing && s.on) return 'full';
  if (s.hover && (s.em || s.pd)) return 'full';
  if (s.focusing) return 'faint';
  if (s.hover) return 'hov';
  if (s.pd) return 'full';
  return 'base';
}

HD.lineTone = {TONES: TONES, tone: tone};
})();
