/* Model — 메모 목록 저장소: 편집·주석 메모 목록 하나와, 바꿀 때마다 어느 화면이 닿았는지(touched — 셸은 그 카드만 다시 그린다). DOM·저장소·메시지를 쓰지 않는다.
   메모 하나의 모양은 edits.js. 셸은 메모를 제자리에서 고치기도 하므로(n.value = …) 비교는 객체가 아니라 commit 때 찍어 둔 글(JSON)로 한다.
   HD.notes = {parse(text) → list, store(list) → S, snapshot(list), touched(prev, next) → [screen id], linesKey(list), pendingOf(list, id, field, index), targets(n)}
   S = {list(), set(next), add(n), remove(pred), find(id), unsent(), commit() → 지난 commit 뒤 바뀐(더함·뺌·고침) 메모의 화면 id} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function parse(text) {                               // 저장해 둔 글 → 목록(깨졌으면 빈 목록)
  try { var v = JSON.parse(text || '[]'); return Array.isArray(v) ? v.filter(function (n) { return n && typeof n === 'object'; }) : []; }
  catch (e) { return []; }
}

// 메모마다 {화면, 글} — id 가 없는 옛 메모는 자리 번호로
function snapshot(list) {
  var s = {};
  (list || []).forEach(function (n, i) { s[n.id != null ? 'i:' + n.id : 'k:' + i] = {screen: String(n.screen == null ? '' : n.screen), sig: JSON.stringify(n)}; });
  return s;
}

// prev → next 에서 더하거나 빼거나 고친 메모의 화면들(한 번씩, 처음 나온 차례). 목록 순서만 바뀐 것은 닿지 않은 것
function touched(prev, next) {
  var a = Array.isArray(prev) ? snapshot(prev) : (prev || {}), b = Array.isArray(next) ? snapshot(next) : (next || {});
  var out = [], seen = {};
  function hit(id) { if (!seen[id]) { seen[id] = 1; out.push(id); } }
  Object.keys(a).forEach(function (k) { if (!b[k] || b[k].sig !== a[k].sig) hit(a[k].screen); });
  Object.keys(b).forEach(function (k) { if (!a[k] || a[k].sig !== b[k].sig) hit(b[k].screen); });
  return out;
}

// 판의 선을 바꾸는 메모(잇기·끊기·도착 바꾸기·들어오는 연결 끊기·삭제·빈 레이아웃)만의 글 — 같으면 저장해도 선을 다시 그릴 일이 없다(글자·이름·설명·메모는 선과 무관)
var LINE_EDITS = {link: 1, 'cut-in': 1, 'delete': 1, 'new-screen': 1};
function linesKey(list) { return JSON.stringify((list || []).filter(function (n) { return LINE_EDITS[n.edit]; })); }

// 그 화면·그 칸(정책은 몇 번째 줄)의 마지막 편집 값(없으면 null)
function pendingOf(list, id, field, index) {
  var v = null;
  (list || []).forEach(function (n) { if (n.screen === id && n.edit === field && (field !== 'policy' || n.index === index)) v = n.value; });
  return v;
}

function targets(n) { return n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text, rect: n.rect}]; }   // 예전 한 요소 메모도 읽는다

function store(initial) {
  var cur = (initial || []).slice(), snap = snapshot(cur);
  return {
    list: function () { return cur; },
    set: function (next) { cur = next.slice(); },
    add: function (n) { cur.push(n); },
    remove: function (pred) { cur = cur.filter(function (n) { return !pred(n); }); },
    find: function (id) { return cur.filter(function (n) { return n.id === id; })[0] || null; },
    unsent: function () { return cur.filter(function (n) { return !n.sent; }); },
    commit: function () { var s = snapshot(cur), t = touched(snap, s); snap = s; return t; }
  };
}

HD.notes = {parse: parse, store: store, snapshot: snapshot, touched: touched, linesKey: linesKey, pendingOf: pendingOf, targets: targets};
})();
