/* Model — 판 줄 맞추기 계획: 지금 줄 + 새 데이터 줄 이름 → 걷을 줄·끼울 줄(51-1). DOM 을 쓰지 않는다.
   HD.rows = {plan(have, want) → {remove: [이름], insert: [{group, before: 이름|null}]}}
   have = 지금 판의 줄 [{group, n}](n = 그 줄 카드 수, 빈 레이아웃 포함) · want = 새 데이터의 줄 이름(nd.rows 차례).
   걷기 = 카드 0 이면서 want 에 없는 줄(Figma F18 빈 그룹은 없어진다) · 카드가 남은 줄은 want 에 없어도 둔다.
   끼우기 = want 에 있고 판에 없는 줄 — want 에서 그 뒤에 오는 남은 줄 앞(없으면 끝, before null). 차례대로 끼우면 want 차례가 된다.
   줄 = 섹션(51-4, Figma F16·F17) — 도우미에 묻기 전 같은 규칙(session.plan_group_rename · plan_group_dissolve 와 같은 글):
   target(names, name) → {into, where: 'above'|'below'} | {error} — 줄만 걷기 때 화면이 갈 줄: 위 줄, 첫 줄이면 아래 줄(사용자 결정 ①)
   checkName(names, from, to) → {name} | {name, same: true} | {error} — 앞뒤 빈칸을 자른 새 이름, 빈 이름·80자 넘음·같은 이름 줄·없는 줄은 이유 */
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

var MAX = 80;                                         // session.GROUP_MAX 와 같다

function target(names, name) {
  names = Array.isArray(names) ? names : [];
  var i = names.indexOf(name);
  if (i < 0) return {error: '없는 줄이에요: ' + name};
  if (names.length < 2) return {error: '줄이 하나뿐이라 걷을 수 없어요'};
  return i > 0 ? {into: names[i - 1], where: 'above'} : {into: names[1], where: 'below'};
}

function checkName(names, from, to) {
  names = Array.isArray(names) ? names : [];
  if (names.indexOf(from) < 0) return {error: '없는 줄이에요: ' + from};
  var n = String(to == null ? '' : to).trim();
  if (!n) return {error: '줄 이름이 비었어요'};
  if (n.length > MAX) return {error: '줄 이름이 ' + MAX + '자를 넘어요'};
  if (n === from) return {name: n, same: true};
  if (names.indexOf(n) >= 0) return {error: '같은 이름의 줄이 이미 있어요: ' + n};
  return {name: n};
}

HD.rows = {plan: plan, target: target, checkName: checkName};
})();
