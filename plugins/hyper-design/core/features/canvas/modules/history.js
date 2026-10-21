/* ViewModel — 기록 시간줄 하나(E2·E8): 한 일을 순서대로, 어디까지 했는지(at), 어디부터 되돌릴 수 없는지(lock). DOM·저장소를 쓰지 않는다.
   상태 {rows:[{label, status, at, op?}], at, lock}
     rows   : 한 일. status = canvas(화면에만) · pending(반영 대기) · sent(AI 에 보냄) · file(파일에 씀). op = {undo(), redo()} — 이번 세션 것만
     at     : 해 둔 줄 수(rows[0..at-1] = 한 것, 나머지 = 되돌린 것 — 다시 하기)
     lock   : 이 앞(rows[0..lock-1])으로는 되돌릴 수 없다 — 보낸 자리·지난 세션·50단계 넘은 것
   의도 → 새 상태(원래 상태는 건드리지 않음):
     record{row}  새 줄(되돌린 줄은 버림)      go{to}  at = to(lock..rows.length 안으로)
     sent         해 둔 반영 대기 줄 = AI 에 보냄, lock = at      applied  해 둔 반영 대기 줄 = 파일에 씀, lock = at
   HD.history = {initial(saved), reduce, steps(s, to) → {undo:[row…], redo:[row…]}, canUndo, canRedo, saved(s), STATUS, MAX_UNDO, KEEP} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MAX_UNDO = 50, KEEP = 200;
var STATUS = {canvas: '화면에만', pending: '반영 대기', sent: 'AI에 보냄', file: '파일에 씀'};

function initial(saved) {                            // 지난 세션 줄은 보이기만(되돌리기 함수가 없다)
  var rows = (Array.isArray(saved) ? saved : []).filter(function (r) { return r && r.label; }).slice(-KEEP)
    .map(function (r) { return {label: String(r.label), status: STATUS[r.status] ? r.status : 'sent', at: r.at || ''}; });
  return {rows: rows, at: rows.length, lock: rows.length};
}
function mark(s, from, to) {
  var rows = s.rows.map(function (r, i) { return i < s.at && r.status === from ? {label: r.label, status: to, at: r.at, op: r.op} : r; });
  return {rows: rows, at: s.at, lock: s.at};
}
function reduce(s, a) {
  if (!a) return s;
  switch (a.type) {
    case 'record':
      var rows = s.rows.slice(0, s.at).concat([a.row]), at = rows.length, lock = Math.max(s.lock, at - MAX_UNDO);
      if (rows.length > KEEP) { var cut = rows.length - KEEP; rows = rows.slice(cut); at -= cut; lock = Math.max(0, lock - cut); }
      return {rows: rows, at: at, lock: lock};
    case 'go':
      var to = Math.max(s.lock, Math.min(s.rows.length, a.to | 0));
      return to === s.at ? s : {rows: s.rows, at: to, lock: s.lock};
    case 'sent': return mark(s, 'pending', 'sent');
    case 'applied': return mark(s, 'pending', 'file');
  }
  return s;
}
// at → to 로 가려면 되돌릴 줄(새것부터) · 다시 할 줄(옛것부터)
function steps(s, to) {
  to = Math.max(s.lock, Math.min(s.rows.length, to | 0));
  return {undo: to < s.at ? s.rows.slice(to, s.at).reverse() : [], redo: to > s.at ? s.rows.slice(s.at, to) : []};
}
function canUndo(s) { return s.at > s.lock; }
function canRedo(s) { return s.at < s.rows.length; }
function saved(s) { return s.rows.slice(0, s.at).map(function (r) { return {label: r.label, status: r.status, at: r.at}; }); }   // 되돌린 줄은 남기지 않는다

HD.history = {initial: initial, reduce: reduce, steps: steps, canUndo: canUndo, canRedo: canRedo, saved: saved, STATUS: STATUS, MAX_UNDO: MAX_UNDO, KEEP: KEEP};
})();
