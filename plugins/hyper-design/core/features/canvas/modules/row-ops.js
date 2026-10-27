/* Model — 폴더(판의 화면 줄 = 섹션) 다루기 규칙(R31): 끌어 놓을 곳 · 다른 폴더로 옮기기 계획 · 제목이 따라갈 자리 · 폴더째 옮기기 계획 · 단축키 · 메뉴 글. DOM·저장소를 쓰지 않는다.
   이름 검사·풀기 대상은 HD.rows.checkName · HD.rows.target 그대로(같은 글을 도우미 board_rows 가 쓴다).
   drop(items, head) → {add?: {id, ids}, take?: [id], assign?: {to, ids}} — 레이어 패널에서 화면 줄을 끌어 놓을 때.
     items = 끈 화면 [{id, row: 'row:<이름>'|'@…', folder?}] · head = 놓은 묶음의 머리 줄 {kind 'folder'|'row', id, name}.
     사용자 폴더(kind folder) = 그 폴더에 없는 것만 넣기 · 판 폴더(id 'row:…') = 사용자 폴더에 든 것은 빼고, 다른 판 폴더 화면은 그 폴더로 옮기기 ·
     그 밖(빈 레이아웃 '@drafts' · 판 메모 '@notes' · 모르는 머리) = 할 일 없음({})
   assign(rows, ids, to) → {to, ids, emptied: [이름]} | {same: true} | {error} — 판 폴더 옮기기 계획(도우미 plan_group_move 와 같은 규칙).
     rows = 판 폴더 차례 [{name, ids}] · 옮길 것 = to 가 아닌 폴더에 있는 ids(rows 차례) · emptied = 그래서 비는 폴더 · 모르는 폴더·화면 = 이유
   titleShift(offs) → {dx, dy} — 폴더 제목이 따라갈 옮긴 거리 = 그 폴더 카드 옮긴 거리(card-pos)의 가장 작은 값(가로·세로 따로, Figma 섹션 이름은 왼쪽 위).
     폴더째 끌면 모두 같이 움직이니 제목도 같이 · 카드 하나를 오른쪽·아래로 옮기면 제목은 그대로 · 깨진 값은 0
   dragPlan(ids, locked, mx, my) → {moves: {id: [mx, my]}} | {error} — 제목 끌기로 폴더째 옮기기(판 px, 정수). 잠긴 화면이 끼면 옮기지 않는다(카드 끌기와 같음)
   key(e) → 'ungroup' | 'delete' | null — 고른 폴더에서: Ctrl/⌘+Shift+G(Figma Ungroup)·Ctrl+Backspace = 폴더만 풀기 · Delete/Backspace = 폴더 지우기
   WORDS = 판 제목 메뉴·레이어 줄 메뉴가 같이 쓰는 글(폴더만 풀기 ≠ 폴더 지우기가 글에 드러나게) · del(n) = '폴더 지우기 — 화면 n개도'
   HD.rowOps = {drop, assign, titleShift, dragPlan, key, WORDS} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ROW = 'row:';
function isRow(id) { return typeof id === 'string' && id.indexOf(ROW) === 0; }

function drop(items, head) {
  items = Array.isArray(items) ? items.filter(function (x) { return x && typeof x.id === 'string'; }) : [];
  if (!head || !items.length) return {};
  if (head.kind === 'folder') {
    var add = items.filter(function (x) { return x.folder !== head.id; }).map(function (x) { return x.id; });
    return add.length ? {add: {id: head.id, ids: add}} : {};
  }
  if (head.kind !== 'row' || !isRow(head.id)) return {};
  var out = {}, take = items.filter(function (x) { return x.folder; }).map(function (x) { return x.id; }),
      move = items.filter(function (x) { return isRow(x.row) && x.row !== head.id; }).map(function (x) { return x.id; });
  if (take.length) out.take = take;
  if (move.length) out.assign = {to: String(head.name != null ? head.name : head.id.slice(ROW.length)), ids: move};
  return out;
}

function assign(rows, ids, to) {
  rows = Array.isArray(rows) ? rows.filter(function (r) { return r && typeof r.name === 'string' && Array.isArray(r.ids); }) : [];
  ids = Array.isArray(ids) ? ids : [];
  var target = rows.filter(function (r) { return r.name === to; })[0];
  if (!target) return {error: '없는 폴더예요: ' + to};
  if (!ids.length) return {error: '옮길 화면이 없어요'};
  var where = {};
  rows.forEach(function (r) { r.ids.forEach(function (id) { if (!(id in where)) where[id] = r.name; }); });
  var unknown = ids.filter(function (id) { return !(id in where); });
  if (unknown.length) return {error: '없는 화면이에요: ' + unknown.join(', ')};
  var want = {}; ids.forEach(function (id) { want[id] = 1; });
  var move = [], emptied = [];
  rows.forEach(function (r) {
    if (r.name === to) return;
    var go = r.ids.filter(function (id) { return want[id]; });
    move = move.concat(go);
    if (go.length && go.length === r.ids.length) emptied.push(r.name);
  });
  if (!move.length) return {same: true};
  return {to: to, ids: move, emptied: emptied};
}

function num(v) { var n = typeof v === 'number' ? v : parseFloat(v); return isFinite(n) ? n : 0; }
function titleShift(offs) {
  offs = Array.isArray(offs) ? offs : [];
  if (!offs.length) return {dx: 0, dy: 0};
  var dx = Infinity, dy = Infinity;
  offs.forEach(function (o) { o = o || {}; dx = Math.min(dx, num(o.dx)); dy = Math.min(dy, num(o.dy)); });
  return {dx: dx, dy: dy};
}

function dragPlan(ids, locked, mx, my) {
  ids = Array.isArray(ids) ? ids : [];
  locked = locked || {};
  if (ids.some(function (id) { return locked[id]; })) return {error: '잠긴 화면이 있어 폴더를 옮기지 않았어요 — 잠금을 먼저 풀어 주세요'};
  var x = Math.round(num(mx)), y = Math.round(num(my)), moves = {};
  if (x || y) ids.forEach(function (id) { moves[id] = [x, y]; });
  return {moves: moves};
}

function key(e) {
  if (!e) return null;
  var k = String(e.key || '').toLowerCase(), mod = !!(e.ctrlKey || e.metaKey);
  if (mod && e.shiftKey && !e.altKey && k === 'g') return 'ungroup';
  if (mod && !e.shiftKey && !e.altKey && k === 'backspace') return 'ungroup';
  if (!mod && !e.altKey && !e.shiftKey && (k === 'delete' || k === 'backspace')) return 'delete';
  return null;
}

var WORDS = {
  pick: '폴더 고르기', rename: '이름 바꾸기', ungroup: '폴더만 풀기 — 화면은 남겨요', ungroupKey: 'Ctrl+Shift+G',
  del: function (n) { return '폴더 지우기 — 화면' + (n > 0 ? ' ' + n + '개' : '') + '도 지워요'; }, delKey: 'Del',
  tip: '폴더 — 누르기 = 폴더 화면 고르기 · 두 번 = 이름 바꾸기 · 끌기 = 폴더째 옮기기'
};

HD.rowOps = {drop: drop, assign: assign, titleShift: titleShift, dragPlan: dragPlan, key: key, WORDS: WORDS};
})();
