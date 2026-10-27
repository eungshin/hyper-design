/* Model — 여러 요소 고르기 규칙(R19): 고른 요소 목록 — 그냥 누르기 = 그 하나, Shift+누르기 = 더하기·빼기, 주인(막대가 붙는 것) = 마지막 것. DOM·저장소를 쓰지 않는다.
   항목은 무엇이든 — 같은지는 keyOf(item) → 문자열(판 = 카드 id + ':' + path, 크게 보기 = 화면 id + ':' + path).
   HD.elPick = {key(screen, path) → 'screen:path', only(item) → [item], toggle(list, item, keyOf) → 새 목록(있으면 빼고, 없으면 끝에 더함 — 끝 = 주인),
     primary(list) → 마지막 것|null, has(list, item, keyOf), keep(list, ok(item)) → ok 인 것만(차례 그대로),
     shift({tool, els, picked, draft}) → 'el'|'card' — 판에서 Shift+누르기가 무엇을 더하나: 선택(V) 도구 · 고른 요소가 하나 이상(els) · 누른 카드가 고른 카드(picked) · 빈 레이아웃 아님
       = 'el'(그 카드 요소 더하기·빼기), 그 밖 = 'card'(카드 여러 장 고르기 E15 그대로). 다른 카드의 요소는 먼저 Shift+누르기로 그 카드를 더한 뒤 같은 길로,
     menuScope({card, elCard}) → 'element'|'card' — 판 카드 오른쪽 클릭 메뉴의 범위(R27 F05, Figma: 메뉴 = 지금 고른 것의 범위):
       그 카드 안 요소를 이미 골랐으면(elCard = 고른 요소의 카드 id) 요소 메뉴, 아니면 카드 메뉴. 요소 메뉴에 카드 항목을 덧붙이지 않는다}
   오류 탐지: keyOf 가 빈 값을 주는 항목(path 없음)은 더하지 않고 목록 그대로 — 화면이 답하지 않은 자리를 고른 것으로 만들지 않는다. 목록이 아니면 빈 목록. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function arr(list) { return Array.isArray(list) ? list : []; }
function key(screen, path) { return String(screen == null ? '' : screen) + ':' + String(path == null ? '' : path); }
function only(item) { return item == null ? [] : [item]; }
function idx(list, k, keyOf) { for (var i = 0; i < list.length; i++) if (keyOf(list[i]) === k) return i; return -1; }
function toggle(list, item, keyOf) {
  list = arr(list);
  var k = item == null ? '' : keyOf(item);
  if (!k) return list.slice();
  var i = idx(list, k, keyOf);
  return i >= 0 ? list.slice(0, i).concat(list.slice(i + 1)) : list.concat([item]);
}
function primary(list) { list = arr(list); return list.length ? list[list.length - 1] : null; }
function has(list, item, keyOf) { return item != null && idx(arr(list), keyOf(item), keyOf) >= 0; }
function keep(list, ok) { return arr(list).filter(function (x) { return !!ok(x); }); }
function shift(o) { o = o || {}; return o.tool === 'move' && (+o.els || 0) > 0 && !!o.picked && !o.draft ? 'el' : 'card'; }

function menuScope(o) { o = o || {}; return o.card != null && o.elCard != null && String(o.card) === String(o.elCard) ? 'element' : 'card'; }

HD.elPick = {key: key, only: only, toggle: toggle, primary: primary, has: has, keep: keep, shift: shift, menuScope: menuScope};
})();
