/* ViewModel — 기록 시간줄 하나(E2·E8): 한 일을 순서대로, 어디까지 했는지(at), 어디부터 되돌릴 수 없는지(lock)와 그 까닭, 줄마다 되돌릴 상태 차이(d). DOM·저장소를 쓰지 않는다.
   상태 {rows:[{label, status, at, op?, d?, cut?, old?}], at, lock}
     rows   : 한 일. status = canvas(화면에만) · pending(반영 대기) · sent(AI 에 보냄) · file(파일에 씀). op = {undo(), redo()} — 이번 세션 것만(있으면 이것을 쓴다)
              d = 상태 차이 {이름: {k, e}} — 새로고침 뒤에도 되돌리고 다시 할 수 있는 데이터(TRACK 이름만). cut = 이 줄 뒤에 보냄('sent')·파일에 씀('file') 경계
              old = 크기 한도로 d 를 버린 줄
     at     : 해 둔 줄 수(rows[0..at-1] = 한 것, 나머지 = 되돌린 것 — 다시 하기)
     lock   : 이 앞(rows[0..lock-1])으로는 되돌릴 수 없다 — 줄에서 계산: cut·보낸 줄·되돌릴 데이터가 없는 줄(op 도 d 도 없음, 파일에 쓴 줄은 op 만) 중 마지막 다음
   차이(d): k = obj(키마다) · ids(id 가진 것들의 배열 — 메모, [전, 후, 전 자리, 후 자리]) · set(글자·수 배열 — 숨김·잠금, [전 있음, 후 있음, 전 자리, 후 자리, 값]) · val(통째로 [전, 후])
   의도 → 새 상태(원래 상태는 건드리지 않음):
     record{row}  새 줄(되돌린 줄은 버림)      go{to}  at = to(lock..rows.length 안으로)
     sent         해 둔 반영 대기 줄 = AI 에 보냄, 경계 = at      applied  해 둔 반영 대기 줄 = 파일에 씀, 경계 = at
   HD.history = {initial(saved), reduce, steps(s, to) → {undo:[row…], redo:[row…]}, canUndo, canRedo, saved(s) → 남길 줄(되돌린 줄 뺌, d 는 새것부터 MAX_BYTES 까지),
                 diff(전 값들, 후 값들) → d | null, patch(값들, d, 'before'|'after') → {이름: 새 값}, why(s) → 'sent'|'file'|'old'|'live'|null, REASON, TRACK, STATUS, KEEP, MAX_BYTES} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEEP = 200, MAX_BYTES = 1000000;
var STATUS = {canvas: '화면에만', pending: '반영 대기', sent: 'AI에 보냄', file: '파일에 씀'};
var TRACK = ['notes', 'card-pos', 'link-names', 'hidden', 'locked', 'folders'];   // 되돌릴 상태 이름(state-file NAMES 중) — edit-log(기록 자신)·busy(AI 작업 표시)·note-seq(번호는 다시 쓰지 않음)는 뺀다
var REASON = {sent: 'AI에 보낸 일이라 되돌릴 수 없어요', file: '파일에 쓴 일이라 되돌릴 수 없어요',
              old: '너무 오래된 일이라 되돌릴 수 없어요', live: '다시 열기 전에 한 화면 설정 일이라 되돌릴 수 없어요'};
var has = function (o, k) { return Object.prototype.hasOwnProperty.call(o, k); };
function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
function same(a, b) { return JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b); }
function nul(v) { return v === undefined ? null : v; }

/* ---- 상태 차이 ---- */
function kindOf(v) {
  if (v == null) return 'none';
  if (Array.isArray(v)) {
    if (!v.length) return 'list';
    if (v.every(function (x) { return isObj(x) && (typeof x.id === 'string' || typeof x.id === 'number'); })) return 'ids';
    if (v.every(function (x) { return typeof x === 'string' || typeof x === 'number'; })) return 'set';
    return 'val';
  }
  return isObj(v) ? 'obj' : 'val';
}
function kindPair(a, b) {
  var ka = kindOf(a), kb = kindOf(b);               // 없음 = 어느 것과도, 빈 배열 = ids·set 과 맞는다
  if (ka === 'none') ka = kb;
  if (kb === 'none') kb = ka;
  if (ka === 'list' && (kb === 'ids' || kb === 'set')) ka = kb;
  if (kb === 'list' && (ka === 'ids' || ka === 'set')) kb = ka;
  return ka === kb && (ka === 'obj' || ka === 'ids' || ka === 'set') ? ka : 'val';
}
function byKey(arr, kind) {
  var m = {};
  (Array.isArray(arr) ? arr : []).forEach(function (x, i) { var k = kind === 'ids' ? String(x.id) : String(x); if (!has(m, k)) m[k] = {v: x, i: i}; });
  return m;
}
function diffValue(a, b) {
  if (same(a, b)) return null;
  var k = kindPair(a, b), e = {};
  if (k === 'obj') {
    var A = isObj(a) ? a : {}, B = isObj(b) ? b : {};
    Object.keys(A).concat(Object.keys(B)).forEach(function (key) {
      if (has(e, key)) return;
      var x = has(A, key) ? nul(A[key]) : null, y = has(B, key) ? nul(B[key]) : null;
      if (!same(x, y)) e[key] = [x, y];
    });
  } else if (k === 'ids' || k === 'set') {
    var ma = byKey(a, k), mb = byKey(b, k);
    Object.keys(ma).concat(Object.keys(mb)).forEach(function (key) {
      if (has(e, key)) return;
      var x = ma[key], y = mb[key];
      if (k === 'ids') { if (!same(x && x.v, y && y.v) || (x && y && x.i !== y.i)) e[key] = [x ? x.v : null, y ? y.v : null, x ? x.i : -1, y ? y.i : -1]; }
      else if (!x !== !y) e[key] = [!!x, !!y, x ? x.i : -1, y ? y.i : -1, (x || y).v];
    });
  } else e['*'] = [nul(a), nul(b)];
  return {k: k, e: e};
}
function diff(before, after) {
  var d = {}, any = false;
  TRACK.forEach(function (n) {
    var x = diffValue(before ? before[n] : null, after ? after[n] : null);
    if (x) { d[n] = x; any = true; }
  });
  return any ? d : null;
}
function patchValue(value, dn, side) {
  var s = side === 'before' ? 0 : 1, e = dn.e, keys = Object.keys(e);
  if (dn.k === 'val') return nul(e['*'][s]);
  if (dn.k === 'obj') {
    var o = {}; if (isObj(value)) Object.keys(value).forEach(function (k) { o[k] = value[k]; });
    keys.forEach(function (k) { var t = e[k][s]; if (t === null) delete o[k]; else o[k] = t; });
    return o;
  }
  var arr = Array.isArray(value) ? value.slice() : [], ins = [];
  var at = function (k) { for (var i = 0; i < arr.length; i++) if ((dn.k === 'ids' ? String(arr[i] && arr[i].id) : String(arr[i])) === k) return i; return -1; };
  keys.forEach(function (k) {                          // 빼기·바꾸기 먼저, 넣을 것은 모아 두었다가 제자리 차례로
    var t = e[k][s], i = at(k), want = dn.k === 'ids' ? t !== null : t === true;
    if (!want) { if (i >= 0) arr.splice(i, 1); return; }
    if (dn.k === 'ids' && i >= 0) { arr.splice(i, 1); }   // 자리까지 맞추려고 뺐다가 다시 넣는다
    else if (i >= 0) return;
    ins.push({p: e[k][s + 2], v: dn.k === 'ids' ? t : e[k][4]});
  });
  ins.sort(function (x, y) { return x.p - y.p; }).forEach(function (x) { arr.splice(x.p < 0 ? arr.length : Math.min(x.p, arr.length), 0, x.v); });
  return arr;
}
function patch(values, d, side) {
  var out = {};
  Object.keys(d || {}).forEach(function (n) { out[n] = patchValue(values ? nul(values[n]) : null, d[n], side); });
  return out;
}
function validD(d) {
  if (!isObj(d)) return false;
  return Object.keys(d).every(function (n) {
    var x = d[n];
    if (TRACK.indexOf(n) < 0 || !isObj(x) || !isObj(x.e) || ['obj', 'ids', 'set', 'val'].indexOf(x.k) < 0) return false;
    return Object.keys(x.e).every(function (k) { return Array.isArray(x.e[k]) && x.e[k].length >= 2; });
  });
}

/* ---- 잠금 ---- */
function blocks(r) {                                 // 이 줄 앞으로는 못 간다
  if (r.cut || r.status === 'sent') return true;
  if (r.op) return false;
  return !r.d || r.status === 'file';
}
function lockOf(rows) { for (var i = rows.length - 1; i >= 0; i--) if (blocks(rows[i])) return i + 1; return 0; }
function why(s) {
  if (!s.lock) return null;
  var r = s.rows[s.lock - 1];
  if (r.cut) return r.cut;
  if (r.status === 'sent' || r.status === 'file') return r.status;
  return r.old ? 'old' : 'live';
}

/* ---- 시간줄 ---- */
function initial(saved) {                            // 지난 세션 줄 — d 가 있으면 되돌릴 수 있다
  var rows = (Array.isArray(saved) ? saved : []).filter(function (r) { return r && r.label; }).slice(-KEEP).map(function (r) {
    var o = {label: String(r.label), status: STATUS[r.status] ? r.status : 'sent', at: r.at || ''};
    if (r.d && validD(r.d)) o.d = r.d; else if (r.d) o.bad = 1;
    if (r.cut === 'sent' || r.cut === 'file') o.cut = r.cut;
    if (r.old) o.old = 1;
    return o;
  });
  return {rows: rows, at: rows.length, lock: lockOf(rows)};
}
function copyRow(r, patchObj) { var o = {}; for (var k in r) if (has(r, k)) o[k] = r[k]; for (k in patchObj) o[k] = patchObj[k]; return o; }
function mark(s, from, to) {
  var rows = s.rows.map(function (r, i) {
    var p = {};
    if (i < s.at && r.status === from) p.status = to;
    if (i === s.at - 1) p.cut = to === 'sent' ? 'sent' : 'file';
    return Object.keys(p).length ? copyRow(r, p) : r;
  });
  return {rows: rows, at: s.at, lock: lockOf(rows)};
}
function reduce(s, a) {
  if (!a) return s;
  switch (a.type) {
    case 'record':
      var rows = s.rows.slice(0, s.at).concat([a.row]), at = rows.length;
      if (rows.length > KEEP) { var cut = rows.length - KEEP; rows = rows.slice(cut); at -= cut; }
      return {rows: rows, at: at, lock: lockOf(rows)};
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
function saved(s) {                                  // 되돌린 줄은 남기지 않는다 · d 는 새것부터 MAX_BYTES 까지, 넘으면 옛 줄의 d 를 버리고 old
  var rows = s.rows.slice(0, s.at), out = new Array(rows.length), bytes = 0;
  for (var i = rows.length - 1; i >= 0; i--) {
    var r = rows[i], o = {label: r.label, status: r.status, at: r.at};
    if (r.cut) o.cut = r.cut;
    if (r.d) {
      var n = JSON.stringify(r.d).length;
      if (bytes + n <= MAX_BYTES) { o.d = r.d; bytes += n; } else o.old = 1;
    } else if (r.old) o.old = 1;
    out[i] = o;
  }
  return out;
}

HD.history = {initial: initial, reduce: reduce, steps: steps, canUndo: canUndo, canRedo: canRedo, saved: saved, diff: diff, patch: patch, why: why,
              REASON: REASON, TRACK: TRACK, STATUS: STATUS, KEEP: KEEP, MAX_BYTES: MAX_BYTES};
})();
