/* ViewModel — 판에서 고른 카드(한 장 또는 여러 장). DOM·저장소·메시지를 쓰지 않는다.
   상태 {ids:[id…]} — 고른 순서. 연결 강조는 한 장만 골랐을 때 그 카드(primary).
   의도 → 새 상태(원래 상태는 건드리지 않음):
     only{id}   그 카드만(카드 누르기)          toggle{id}  더하거나 빼기(Shift+클릭)
     set{ids}   이 카드들로(끌어 고르기 등)     drop{ids}   숨기거나 지운 카드 빼기     clear  모두 풀기
   HD.selection = {initial, reduce, has, primary} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function initial() { return {ids: []}; }
function uniq(ids) { var seen = {}; return (ids || []).map(String).filter(function (id) { if (seen[id]) return false; seen[id] = 1; return true; }); }

function reduce(s, a) {
  var ids = s.ids;
  if (!a) return s;
  switch (a.type) {
    case 'only':   return {ids: [String(a.id)]};
    case 'toggle': return {ids: ids.indexOf(String(a.id)) >= 0 ? ids.filter(function (x) { return x !== String(a.id); }) : ids.concat([String(a.id)])};
    case 'set':    return {ids: uniq(a.ids)};
    case 'drop':   var out = uniq(a.ids); return {ids: ids.filter(function (x) { return out.indexOf(x) < 0; })};
    case 'clear':  return ids.length ? {ids: []} : s;
  }
  return s;
}
function has(s, id) { return s.ids.indexOf(String(id)) >= 0; }
function primary(s) { return s.ids.length === 1 ? s.ids[0] : null; }

HD.selection = {initial: initial, reduce: reduce, has: has, primary: primary};
})();
