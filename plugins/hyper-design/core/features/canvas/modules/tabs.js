/* Model — 아래쪽 프로젝트 탭 바 규칙(탭 하나 = 프로젝트 하나, Xmind 시트 바): 탭 차례·지금 것 더하기·닫기·끌어 옮기기·이름 검사·이전/다음·넘침 화살표. DOM·저장소를 쓰지 않는다.
   HD.tabs.bar(served, rows, cur) → {tabs:[{name, title, state, current}], names, added, dropped}
     served = GET /api/tabs 의 이름들(차례 그대로) · rows = HD.projects.rows(…).rows · cur = 지금 프로젝트 이름|null.
     모르는·휴지통·겹친·글 아닌 이름은 빼고 dropped 에 센다. 지금 것이 없으면 끝에 더하고 added = true(View 가 PUT 으로 남긴다)
   close(names, name, cur) · others(names, keep, cur) → {ok, names, go, why} — 하나뿐이면 못 닫음. go = 지금 탭이 사라지면 갈 이름(오른쪽, 없으면 왼쪽)
   move(names, name, slot) → names (slot = 원래 목록에서 끼울 자리 0..n) · slot(mids, x) → 끼울 자리(탭 가운데 x 들 기준)
   rename(old, input) → {ok:true, title} | {ok:false, why:'empty'|'same'} — 공백 정리, MAX 자에서 자름
   step(names, cur, dir ±1) → 이름|null(끝에서 돌아감) · arrows(scrollLeft, scrollWidth, clientWidth) → {over, prev, next}
   place(pane{left, right}, chatLeft|null) → {left, max} — 판 아래 왼쪽(판 왼쪽 끝 + GAP). max = 가운데 대화창 왼쪽 끝(chatLeft, 없으면 판 오른쪽 끝)
     앞 GAP 까지의 폭, 적어도 MIN(그보다 좁으면 대화창이 탭 위로 비킨다 — view-chat). 왼쪽 고정이라 바 폭은 받지 않는다 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MAX = 80;

function bar(served, rows, cur) {
  var by = {};
  (Array.isArray(rows) ? rows : []).forEach(function (r) { if (r && typeof r.name === 'string' && !r.trashed) by[r.name] = r; });
  var list = Array.isArray(served) ? served : [], names = [], dropped = 0;
  list.forEach(function (n) {
    if (typeof n !== 'string' || !by[n] || names.indexOf(n) >= 0) { dropped++; return; }
    names.push(n);
  });
  var added = false;
  if (typeof cur === 'string' && cur && by[cur] && names.indexOf(cur) < 0) { names.push(cur); added = true; }
  return {names: names, added: added, dropped: dropped, tabs: names.map(function (n) {
    var r = by[n];
    return {name: n, title: r.title || n, state: r.state || 'off', current: n === cur};
  })};
}

function neighbour(names, i) {                       // i 번째가 빠지면 갈 곳 — 오른쪽, 없으면 왼쪽
  return names[i + 1] != null ? names[i + 1] : (i > 0 ? names[i - 1] : null);
}

function close(names, name, cur) {
  var i = names.indexOf(name);
  if (i < 0) return {ok: false, names: names.slice(), go: null, why: '없는 탭이에요'};
  if (names.length < 2) return {ok: false, names: names.slice(), go: null, why: '탭이 하나뿐이라 닫을 수 없어요'};
  return {ok: true, names: names.filter(function (n) { return n !== name; }), go: name === cur ? neighbour(names, i) : null, why: ''};
}

function others(names, keep, cur) {
  if (names.indexOf(keep) < 0) return {ok: false, names: names.slice(), go: null, why: '없는 탭이에요'};
  if (names.length < 2) return {ok: false, names: names.slice(), go: null, why: '닫을 다른 탭이 없어요'};
  return {ok: true, names: [keep], go: keep !== cur ? keep : null, why: ''};
}

function move(names, name, slot) {
  var i = names.indexOf(name);
  if (i < 0) return names.slice();
  var to = Math.max(0, Math.min(names.length, slot));
  var r = names.slice(); r.splice(i, 1);
  r.splice(to > i ? to - 1 : to, 0, name);
  return r;
}

function slot(mids, x) {
  var n = 0;
  (mids || []).forEach(function (m) { if (x > m) n++; });
  return n;
}

function rename(old, input) {
  var t = String(input == null ? '' : input).replace(/\s+/g, ' ').trim();
  if (!t) return {ok: false, why: 'empty'};
  if (t.length > MAX) t = t.slice(0, MAX).trim();
  if (t === String(old == null ? '' : old).trim()) return {ok: false, why: 'same'};
  return {ok: true, title: t};
}

function step(names, cur, dir) {
  var i = names.indexOf(cur);
  if (i < 0 || names.length < 2) return null;
  return names[(i + (dir < 0 ? -1 : 1) + names.length) % names.length];
}

function arrows(left, scrollW, clientW) {
  var over = scrollW - clientW > 1;
  return {over: over, prev: over && left > 0.5, next: over && scrollW - (left + clientW) > 0.5};   // 반 픽셀 = 배율 반올림 — 끝으로 본다
}

var GAP = 12, MIN = 160;
function place(pane, chat) {
  var lo = pane.left + GAP, hi = pane.right - GAP;
  if (typeof chat === 'number' && isFinite(chat)) hi = Math.min(hi, Math.floor(chat) - GAP);
  return {left: Math.ceil(lo), max: Math.floor(Math.max(MIN, hi - lo))};
}

HD.tabs = {MAX: MAX, place: place, bar: bar, close: close, others: others, move: move, slot: slot, rename: rename, step: step, arrows: arrows};
})();
