/* View — 레이어 패널(조각 4, H6·H7). 나무와 거르기는 modules/layers.js(Model), 여기는 그리기와 누르기만.
   줄마다: 눈(숨김) · 이름(누르면 그 카드로 + 고르기) · 메모 수 · 잠금. 묶음 줄은 접기 · 눈(그 줄 화면 모두).
   위: 이름 찾기 + 거르기 아이콘(숨긴 것만 · 잠긴 것만 · 메모 있는 것), 아래 막대: 빈 레이아웃 · 숨기기 · 잠그기 · 삭제(고른 화면).
   숨김·잠금·고르기 상태의 주인은 셸 — 여기는 의도만 보낸다.
   HD.viewLayers.mount(ctx) → {render(), only(f)}
   ctx = {$, esc, root, tree() → {groups, texts}, state() → {hidden, locked, memo}, picked() → [id],
          hide(ids, on), lock(ids, on), reveal(id), addLayout(), del(ids)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var I = {
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  off: '<path d="M3 3l18 18M10.6 6.1A9.7 9.7 0 0112 6c5 0 9 6 9 6a16 16 0 01-2.7 3.3M6.6 6.6C4.3 8.1 3 12 3 12s4 6 9 6a8.6 8.6 0 004.4-1.2M9.9 9.9a3 3 0 004.2 4.2"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
  open: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 017.5-2"/>',
  memo: '<path d="M4 4h16v12H9l-5 4z"/>',
  layout: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M12 9v6M9 12h6"/>',
  del: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'
};
function svg(d) { return '<svg viewBox="0 0 24 24">' + d + '</svg>'; }

function mount(ctx) {
  var $ = ctx.$, esc = ctx.esc, root = ctx.root, L = HD.layers, folded = {}, only = null;
  root.innerHTML =
    '<div class="ly-top"><input id="lyQ" type="search" placeholder="이름 찾기" aria-label="레이어 찾기">' +
    '<span id="lyF" role="group" aria-label="거르기">' +
      '<button type="button" data-f="hidden" aria-pressed="false" title="숨긴 것만">' + svg(I.off) + '</button>' +
      '<button type="button" data-f="locked" aria-pressed="false" title="잠긴 것만">' + svg(I.lock) + '</button>' +
      '<button type="button" data-f="memo" aria-pressed="false" title="메모 있는 것">' + svg(I.memo) + '</button></span></div>' +
    '<div id="lyTree" role="tree" aria-label="레이어"></div>' +
    '<div id="lyBar" role="toolbar" aria-label="고른 화면">' +
      '<button type="button" data-act="layout" title="빈 레이아웃 (N)">' + svg(I.layout) + '</button>' +
      '<button type="button" data-act="hide" title="숨기기">' + svg(I.off) + '</button>' +
      '<button type="button" data-act="lock" title="잠그기 · 풀기">' + svg(I.lock) + '</button>' +
      '<button type="button" data-act="del" title="삭제 (Del)">' + svg(I.del) + '</button></div>';
  var q = $('#lyQ'), tree = $('#lyTree'), fbar = $('#lyF');

  function rowHtml(x, picked) {
    var cls = 'ly-r ' + x.kind + (x.hid ? ' hid' : '') + (x.lock ? ' locked' : '') + (picked[x.id] ? ' on' : '');
    var eye = '<button type="button" class="ly-eye" aria-pressed="' + !x.hid + '" aria-label="' + (x.hid ? '보이기' : '숨기기') + '">' + svg(x.hid ? I.off : I.eye) + '</button>';
    if (x.kind === 'row') {
      return '<div class="' + cls + '" data-ly="' + esc(x.id) + '" data-kind="row" role="treeitem" aria-expanded="' + !folded[x.id] + '">' +
        '<button type="button" class="ly-fold" aria-label="접기">' + (folded[x.id] ? '▸' : '▾') + '</button>' + eye +
        '<span class="ly-name">' + esc(x.name) + '</span></div>';
    }
    return '<div class="' + cls + '" data-ly="' + esc(x.id) + '" data-kind="' + x.kind + '" role="treeitem">' + eye +
      '<span class="ly-name">' + esc(x.name) + '</span>' + (x.memo ? '<span class="ly-cnt" title="메모 ' + x.memo + '건">' + x.memo + '</span>' : '') +
      (x.kind === 'screen' ? '<button type="button" class="ly-lock" aria-pressed="' + x.lock + '" aria-label="' + (x.lock ? '잠금 풀기' : '잠그기') + '">' + svg(x.lock ? I.lock : I.open) + '</button>' : '') +
      '</div>';
  }
  var list = [];
  function render() {
    var t = ctx.tree(), picked = {};
    ctx.picked().forEach(function (id) { picked[id] = 1; });
    list = L.build(t.groups, t.texts, ctx.state());
    var shown = L.filter(list, {q: q.value, only: only, folded: folded});
    tree.innerHTML = shown.length ? shown.map(function (x) { return rowHtml(x, picked); }).join('') : '<p class="dkp-empty">맞는 레이어가 없어요</p>';
    $$f().forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.f === only)); });
  }
  function $$f() { return Array.prototype.slice.call(fbar.querySelectorAll('button[data-f]')); }
  function kids(rowId) { return list.filter(function (x) { return x.row === rowId; }).map(function (x) { return x.id; }); }
  function item(id) { return list.filter(function (x) { return x.id === id; })[0]; }
  function setOnly(f) { only = f || null; render(); }

  q.addEventListener('input', render);
  ['pointerdown', 'keydown', 'wheel'].forEach(function (ev) { q.addEventListener(ev, function (e) { e.stopPropagation(); }); });   // 판 단축키·끌기와 겹치지 않게
  fbar.addEventListener('click', function (e) { var b = e.target.closest('button[data-f]'); if (b) setOnly(only === b.dataset.f ? null : b.dataset.f); });
  tree.addEventListener('click', function (e) {
    var r = e.target.closest('[data-ly]'); if (!r) return;
    var id = r.dataset.ly, x = item(id); if (!x) return;
    if (e.target.closest('.ly-fold')) { if (folded[id]) delete folded[id]; else folded[id] = 1; render(); return; }
    if (e.target.closest('.ly-eye')) { ctx.hide(x.kind === 'row' ? kids(id) : [id], !x.hid); return; }
    if (e.target.closest('.ly-lock')) { ctx.lock([id], !x.lock); return; }
    if (x.kind === 'screen' && !x.hid) ctx.reveal(id);
  });
  $('#lyBar').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act]'); if (!b) return;
    var ids = ctx.picked(), a = b.dataset.act;
    if (a === 'layout') { ctx.addLayout(); return; }
    if (!ids.length) return;
    if (a === 'hide') ctx.hide(ids, true);
    else if (a === 'lock') { var st = ctx.state().locked || {}; ctx.lock(ids, !ids.every(function (id) { return st[id]; })); }
    else if (a === 'del') ctx.del(ids);
  });
  render();
  return {render: render, only: setOnly};
}

HD.viewLayers = {mount: mount};
})();
