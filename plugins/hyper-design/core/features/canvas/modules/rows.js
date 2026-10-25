/* Model — 판 줄 맞추기 계획: 지금 줄 + 새 데이터 줄 이름 → 걷을 줄·끼울 줄(51-1). DOM 을 쓰지 않는다.
   HD.rows = {plan(have, want) → {remove: [이름], insert: [{group, before: 이름|null}]}}
   have = 지금 판의 줄 [{group, n}](n = 그 줄 카드 수, 빈 레이아웃 포함) · want = 새 데이터의 줄 이름(nd.rows 차례).
   걷기 = 카드 0 이면서 want 에 없는 줄(Figma F18 빈 그룹은 없어진다) · 카드가 남은 줄은 want 에 없어도 둔다.
   끼우기 = want 에 있고 판에 없는 줄 — want 에서 그 뒤에 오는 남은 줄 앞(없으면 끝, before null). 차례대로 끼우면 want 차례가 된다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function plan(have, want) {
  have = Array.isArray(have) ? have : []; want = Array.isArray(want) ? want : [];
  var inWant = {}, kept = {}, remove = [], insert = [];
  want.forEach(function (g) { inWant[g] = 1; });
  have.forEach(function (r) {
    if (!r) return;
    if (!(r.n > 0) && !inWant[r.group]) remove.push(r.group); else kept[r.group] = 1;
  });
  want.forEach(function (g, i) {
    if (kept[g]) return;
    var before = null;
    for (var j = i + 1; j < want.length; j++) if (kept[want[j]]) { before = want[j]; break; }
    insert.push({group: g, before: before});
  });
  return {remove: remove, insert: insert};
}

HD.rows = {plan: plan};
})();
