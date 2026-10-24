/* Model — 다시 찾은 메모 자리 판정: 핀이 될 대상·자리 키·요소를 찾을 수 없음(#285). DOM 을 쓰지 않는다.
   화면은 hd-locate 에 hd-located {key, rect|null, how} 로 답한다 — how 'none' = 경로가 요소 하나에 맞지 않고(여럿·없음, task 41) 글로도 못 찾음.
   HD.relocate = {pinnable(t) → 핀이 될 대상(path 있고 body·'(새 화면)' 아님), key(id, i) → 'id:i',
                  lost(id, targets, map) → 핀이 될 대상 하나라도 map 의 답이 how 'none' 이면 true(답이 없으면 아직 모름 = false)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function pinnable(t) { return !!(t && t.path && t.path !== 'body' && t.path !== '(새 화면)'); }
function key(id, i) { return id + ':' + i; }
function lost(id, targets, map) {
  if (!map) return false;
  return (targets || []).some(function (t, i) { var a = map[key(id, i)]; return pinnable(t) && !!a && a.how === 'none'; });
}

HD.relocate = {pinnable: pinnable, key: key, lost: lost};
})();
