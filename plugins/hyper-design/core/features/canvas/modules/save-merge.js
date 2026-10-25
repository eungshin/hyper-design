/* Model — 저장 충돌(409) 합치기(#269): 보내지 못한 이름이 서버에서 안 바뀌었으면 서버의 나머지를 받고 내 값을 지켜 다시 보낸다. DOM·저장소를 쓰지 않는다.
   AI 답(hd reply)·덮개(hd claim)는 파일 rev 를 늘 올린다 — 그 사이 캔버스가 모아 둔 변경(카드 옮기기·메모 고치기)이 409 를 받아도 잃지 않게.
   resolve(dirty, base, local, server) → {ok:true, state, adopt:[이름]} | {ok:false, lost:[이름]}
     dirty  = 보내지 못한 이름들 · base = 내가 마지막으로 안 서버 상태 · local = 지금 내 상태 · server = 409 답의 state
     이름마다: 서버가 base 그대로 = 내 값 · 둘이 같은 값 = 그대로 · notes = mergeNotes(id 마다 칸끼리) · busy = mergeBusy(카드마다, 실패 없음) · 그 밖 = 잃음
     state = 서버 상태 + 지킨 이름(다시 보낼 것) · adopt = 내 상태와 달라진 이름(화면이 다시 읽을 것)
   mergeNotes(base, local, server) → {ok, notes} — id 마다: 한쪽만 바꿈 = 그쪽 · 둘 다 바꿈 = 칸마다 같은 규칙, 둘 다 늘린 배열(replies)은 앞이 같으면 이어 붙임 ·
     내가 지운 메모를 서버가 바꿈(또는 반대) = 실패 · id 없는 메모 = 실패. 차례 = 내 차례, 서버에만 새로 온 메모는 뒤에
   mergeBusy(base, local, server) → {v:1, items} — AI 작업 표시(busy.js 상태)를 카드 id 마다: 한쪽만 바꿈 = 그쪽 · 둘 다 바꿈 = 더 새것 —
     둘 다 있으면 since 가 큰 쪽(같으면 서버) · 한쪽이 걷음(없음)이면 남은 쪽 덮개의 since 가 base 의 since 보다 크면(새로 덮음) 그 덮개, 아니면 걷기.
     칩을 걷는 순간 hd claim 이 와도(409) 다른 카드의 새 덮개와 내 걷기가 둘 다 남는다. 깨진·없는 값 = 빈 상태
   lostText(names) → 사람 말('카드 자리, 메모') · LABEL
   HD.saveMerge = {resolve, mergeNotes, mergeBusy, lostText, LABEL} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var LABEL = {notes: '메모', 'card-pos': '카드 자리', 'edit-log': '기록', 'link-names': '연결 이름', hidden: '숨김', locked: '잠금',
             folders: '폴더', busy: 'AI 작업 표시', 'note-seq': '메모 번호'};
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };
function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
function same(a, b) { return JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b); }
function copy(o) { var r = {}; for (var k in o) if (has(o, k)) r[k] = o[k]; return r; }
var FAIL = {};

function three(b, l, s) {                              // 값 하나 — 합친 값 | FAIL
  if (same(b, s)) return l;
  if (same(b, l) || same(l, s)) return s;
  if (Array.isArray(b) && Array.isArray(l) && Array.isArray(s) && same(l.slice(0, b.length), b) && same(s.slice(0, b.length), b))
    return b.concat(l.slice(b.length), s.slice(b.length));          // 둘 다 뒤에 늘림(답 줄)
  return FAIL;
}
function fields(b, l, s) {                             // 메모 하나 — 칸마다 three
  var r = {}, keys = {};
  [b, l, s].forEach(function (o) { Object.keys(o).forEach(function (k) { keys[k] = 1; }); });
  for (var k in keys) {
    var v = three(b[k], l[k], s[k]);
    if (v === FAIL) return FAIL;
    if (v !== undefined) r[k] = v;
  }
  return r;
}
function index(list) {                                 // id → 메모 | null(id 없는 것이 있음)
  var m = {};
  for (var i = 0; i < list.length; i++) {
    var n = list[i];
    if (!isObj(n) || (typeof n.id !== 'string' && typeof n.id !== 'number')) return null;
    m[n.id] = n;
  }
  return m;
}
function mergeNotes(base, local, server) {
  var B = Array.isArray(base) ? base : [], L = Array.isArray(local) ? local : [], S = Array.isArray(server) ? server : [];
  var bi = index(B), li = index(L), si = index(S);
  if (!bi || !li || !si) return {ok: false, notes: null};
  var out = [], i, id, v;
  for (i = 0; i < L.length; i++) {
    id = L[i].id;
    if (!has(bi, id)) { if (has(si, id) && !same(si[id], L[i])) return {ok: false, notes: null}; out.push(L[i]); continue; }   // 내가 새로 만듦
    if (!has(si, id)) { if (!same(bi[id], L[i])) return {ok: false, notes: null}; continue; }                              // 서버가 지움 — 내가 안 바꿨으면 지움
    v = fields(bi[id], L[i], si[id]);
    if (v === FAIL) return {ok: false, notes: null};
    out.push(v);
  }
  for (i = 0; i < S.length; i++) {
    id = S[i].id;
    if (has(li, id)) continue;
    if (!has(bi, id)) { out.push(S[i]); continue; }                                             // 서버에 새로 옴
    if (!same(bi[id], S[i])) return {ok: false, notes: null};                                    // 내가 지운 메모를 서버가 바꿈
  }
  return {ok: true, notes: out};
}

function busyItems(v) { return isObj(v) && isObj(v.items) ? v.items : {}; }
function since(it) { return isObj(it) && typeof it.since === 'number' && isFinite(it.since) ? it.since : -Infinity; }
function mergeBusy(base, local, server) {
  var B = busyItems(base), L = busyItems(local), S = busyItems(server), ids = {}, items = {};
  [B, L, S].forEach(function (o) { Object.keys(o).forEach(function (k) { ids[k] = 1; }); });
  Object.keys(ids).forEach(function (id) {
    var b = B[id], l = L[id], s = S[id], v;
    if (same(b, s)) v = l;
    else if (same(b, l) || same(l, s)) v = s;
    else if (l && s) v = since(l) > since(s) ? l : s;                           // 둘 다 다시 덮음 — 더 새 덮개(같으면 서버)
    else { var kept = l || s; v = since(kept) > since(b) ? kept : undefined; }  // 한쪽이 걷음 — 남은 쪽이 새로 덮은 것이면 그것, 아니면 걷기
    if (v) items[id] = v;
  });
  return {v: 1, items: items};
}

function resolve(dirty, base, local, server) {
  base = base || {}; local = local || {}; server = server || {};
  var state = copy(server), lost = [];
  (dirty || []).forEach(function (n) {
    if (same(base[n], server[n]) || same(local[n], server[n])) {
      if (has(local, n) && local[n] != null) state[n] = local[n]; else delete state[n];
      return;
    }
    if (n === 'busy') { state[n] = mergeBusy(base[n], local[n], server[n]); return; }
    if (n === 'notes') {
      var m = mergeNotes(base[n], local[n], server[n]);
      if (m.ok) { state[n] = m.notes; return; }
    }
    lost.push(n);
  });
  if (lost.length) return {ok: false, lost: lost};
  var all = {}, adopt = [];
  Object.keys(local).concat(Object.keys(state)).forEach(function (n) { all[n] = 1; });
  Object.keys(all).forEach(function (n) { if (!same(local[n], state[n])) adopt.push(n); });
  return {ok: true, state: state, adopt: adopt};
}

function lostText(names) { return (names || []).map(function (n) { return LABEL[n] || n; }).join(', '); }

HD.saveMerge = {resolve: resolve, mergeNotes: mergeNotes, mergeBusy: mergeBusy, lostText: lostText, LABEL: LABEL};
})();
