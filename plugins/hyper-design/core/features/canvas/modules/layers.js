/* Model — 레이어 나무(조각 4, H6·H7 · 폴더 H17). DOM·저장소를 쓰지 않는다.
   나무 = (사용자 폴더 아래 화면들) + 줄(묶음) 아래 화면들 + 판 글(소개·끝 글). 숨김·잠금·메모 수는 밖에서 받아 줄마다 붙인다.
   build(groups, texts, st, folders?, notes?) → [{kind: 'folder'|'row'|'screen'|'text'|'note', id, name, row?, folder?, count?, hid, lock, memo}]
     notes = 판 메모 줄 [{id: 'note:<id>', name}](R25) — 있으면 맨 끝에 묶음 줄 {kind 'row', id NOTES '@notes', name '판 메모', count} + 메모 줄(kind 'note', row '@notes')
     groups = [{id, name, screens: [{id, name}]}] · texts = [{id: '@intro', name}] · st = {hidden, locked, memo}(id → 값)
     folders = 폴더 상태(modules/folders.js) {v, folders: [{id, name, ids, open}]} — 주면: 사용자 폴더가 맨 앞(폴더 줄 + 그 화면, 화면엔 folder: id),
       그 화면은 원래 줄에서 빠진다. 폴더·줄 줄에 count(그 아래 화면 수), hid = 모두 숨김, lock = 모두 잠금. 안 주면 예전 그대로.
   filter(list, {q, only, folded}) → 보일 줄만
     q = 이름 찾기(화면·줄·폴더 이름, 대소문자 무시 — 줄·폴더 이름이 맞으면 그 아래 화면 모두) · only = 'hidden'|'locked'|'memo'
     folded = {줄·폴더 id: 1}. 줄·폴더는 아래에 보일 화면이 있을 때만 남는다(빈 사용자 폴더는 q·only 가 없을 때만 남는다).
     접힌 줄·폴더는 남고 그 화면만 빠진다.
   rowId(name) → 'row:' + 줄 이름 — 줄(묶음) 줄 id(51-4, 예전 'g'+차례). 줄이 빠지거나 끼어도 접힘이 다른 줄로 옮겨 가지 않는다
   renameRow(folded, from, to) → 새 접힘 표(이름을 바꾼 줄의 접힘이 새 id 로) — 저장하지 않는 상태라 옮길 저장값은 없다
   hoverIds(list, id) → 레이어 줄에 올리면 판에 강조할 id(51-3, Figma F10) — 화면 = 그 하나 · 줄·폴더 = 그 아래 보이는 화면 · 판 글 = 그 id · 숨긴 화면·모르는 id = []
   HD.layers = {NOTES, build, filter, rowId, renameRow, hoverIds} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var NOTES = '@notes';
function all(xs, k) { return xs.length > 0 && xs.every(function (x) { return x[k]; }); }

function build(groups, texts, st, folders, notes) {
  st = st || {};
  var h = st.hidden || {}, l = st.locked || {}, m = st.memo || {}, out = [], withF = !!folders && typeof folders === 'object';
  var fs = withF && Array.isArray(folders.folders) ? folders.folders : [], inF = {}, scr = {};
  fs.forEach(function (f) { (f.ids || []).forEach(function (id) { if (!inF[id]) inF[id] = f.id; }); });
  (groups || []).forEach(function (g) { g.screens.forEach(function (s) { if (!scr[s.id]) scr[s.id] = {s: s, row: g.id}; }); });
  var line = function (s, row) { return {kind: 'screen', id: s.id, name: s.name, row: row, hid: !!h[s.id], lock: !!l[s.id], memo: m[s.id] || 0}; };
  fs.forEach(function (f) {
    var seen = {}, kids = [];
    (f.ids || []).forEach(function (id) {
      if (seen[id] || !scr[id] || inF[id] !== f.id) return;
      seen[id] = 1;
      var k = line(scr[id].s, scr[id].row); k.folder = f.id; kids.push(k);
    });
    out.push({kind: 'folder', id: f.id, name: f.name, open: f.open !== false, count: kids.length, hid: all(kids, 'hid'), lock: all(kids, 'lock'), memo: 0});
    out = out.concat(kids);
  });
  (groups || []).forEach(function (g) {
    var kids = g.screens.filter(function (s) { return !(withF && inF[s.id]); })
      .map(function (s) { return line(s, g.id); });
    var r = {kind: 'row', id: g.id, name: g.name, hid: all(kids, 'hid'), lock: false, memo: 0};
    if (withF) { r.count = kids.length; r.lock = all(kids, 'lock'); }
    out.push(r);
    out = out.concat(kids);
  });
  (texts || []).forEach(function (t) { out.push({kind: 'text', id: t.id, name: t.name, hid: !!h[t.id], lock: false, memo: 0}); });
  if (notes && notes.length) {
    out.push({kind: 'row', id: NOTES, name: '판 메모', count: notes.length, hid: false, lock: false, memo: 0});
    notes.forEach(function (n) { out.push({kind: 'note', id: n.id, name: n.name, row: NOTES, hid: false, lock: false, memo: 0}); });
  }
  return out;
}

function isHead(x) { return x.kind === 'row' || x.kind === 'folder'; }
function parent(x) { return x.folder || x.row; }
function keep(x, only) {
  if (only === 'hidden') return x.hid;
  if (only === 'locked') return x.lock;
  if (only === 'memo') return x.memo > 0;
  return true;
}
function filter(list, o) {
  o = o || {};
  var q = String(o.q || '').trim().toLowerCase(), folded = o.folded || {}, headHit = {};
  var has = function (s) { return !q || String(s).toLowerCase().indexOf(q) >= 0; };
  list.forEach(function (x) { if (isHead(x) && q && has(x.name)) headHit[x.id] = 1; });
  var shown = list.filter(function (x) { return !isHead(x) && keep(x, o.only) && (has(x.name) || (parent(x) && headHit[parent(x)])); });
  var live = {}; shown.forEach(function (x) { if (parent(x)) live[parent(x)] = 1; });
  var bare = !q && !o.only, out = [];
  list.forEach(function (x) {
    if (isHead(x)) { if (live[x.id] || (bare && x.kind === 'folder' && !x.count)) out.push(x); return; }
    if (shown.indexOf(x) < 0 || (parent(x) && folded[parent(x)])) return;
    out.push(x);
  });
  return out;
}

function rowId(name) { return 'row:' + String(name); }
function renameRow(folded, from, to) {
  var out = {}, a = rowId(from), b = rowId(to);
  Object.keys(folded || {}).forEach(function (k) { out[k === a ? b : k] = folded[k]; });
  return out;
}

function hoverIds(list, id) {
  var xs = Array.isArray(list) ? list : [], x = xs.filter(function (y) { return y && y.id === id; })[0];
  if (!x || x.hid || x.kind === 'note' || x.id === NOTES) return [];
  if (x.kind === 'row' || x.kind === 'folder') return xs.filter(function (y) { return y.kind === 'screen' && !y.hid && (y.folder || y.row) === id; }).map(function (y) { return y.id; });
  return [x.id];
}

HD.layers = {NOTES: NOTES, build: build, filter: filter, rowId: rowId, renameRow: renameRow, hoverIds: hoverIds};
})();
