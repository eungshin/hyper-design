/* Model — 레이어 나무(조각 4, H6·H7). DOM·저장소를 쓰지 않는다.
   나무 = 줄(묶음) 아래 화면들 + 판 글(소개·끝 글). 숨김·잠금·메모 수는 밖에서 받아 줄마다 붙인다.
   build(groups, texts, st) → [{kind: 'row'|'screen'|'text', id, name, row?, hid, lock, memo}]
     groups = [{id, name, screens: [{id, name}]}] · texts = [{id: '@intro', name}] · st = {hidden, locked, memo}(id → 값)
   filter(list, {q, only, folded}) → 보일 줄만
     q = 이름 찾기(화면·줄 이름, 대소문자 무시 — 줄 이름이 맞으면 그 줄 화면 모두) · only = 'hidden'|'locked'|'memo' · folded = {줄 id: 1}
     줄(row)은 아래에 보일 화면이 있을 때만 남는다. 접힌 줄은 남고 그 화면만 빠진다.
   HD.layers = {build, filter} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function build(groups, texts, st) {
  st = st || {};
  var h = st.hidden || {}, l = st.locked || {}, m = st.memo || {}, out = [];
  (groups || []).forEach(function (g) {
    var kids = g.screens.map(function (s) {
      return {kind: 'screen', id: s.id, name: s.name, row: g.id, hid: !!h[s.id], lock: !!l[s.id], memo: m[s.id] || 0};
    });
    out.push({kind: 'row', id: g.id, name: g.name, hid: kids.length > 0 && kids.every(function (k) { return k.hid; }), lock: false, memo: 0});
    out = out.concat(kids);
  });
  (texts || []).forEach(function (t) { out.push({kind: 'text', id: t.id, name: t.name, hid: !!h[t.id], lock: false, memo: 0}); });
  return out;
}

function keep(x, only) {
  if (only === 'hidden') return x.hid;
  if (only === 'locked') return x.lock;
  if (only === 'memo') return x.memo > 0;
  return true;
}
function filter(list, o) {
  o = o || {};
  var q = String(o.q || '').trim().toLowerCase(), folded = o.folded || {}, rowHit = {};
  var has = function (s) { return !q || String(s).toLowerCase().indexOf(q) >= 0; };
  list.forEach(function (x) { if (x.kind === 'row' && q && has(x.name)) rowHit[x.id] = 1; });
  var shown = list.filter(function (x) { return x.kind !== 'row' && keep(x, o.only) && (has(x.name) || (x.row && rowHit[x.row])); });
  var live = {}; shown.forEach(function (x) { if (x.row) live[x.row] = 1; });
  var out = [];
  list.forEach(function (x) {
    if (x.kind === 'row') { if (live[x.id]) out.push(x); return; }
    if (shown.indexOf(x) < 0 || (x.row && folded[x.row])) return;
    out.push(x);
  });
  return out;
}

HD.layers = {build: build, filter: filter};
})();
