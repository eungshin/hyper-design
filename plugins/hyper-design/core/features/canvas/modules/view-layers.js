/* View — 레이어 패널(조각 4, H6·H7 · 폴더 H17). 나무와 거르기는 modules/layers.js(Model), 폴더 규칙은 modules/folders.js(Model), 여기는 그리기와 누르기만.
   줄마다: 눈(숨김) · 이름(누르면 그 카드로 + 고르기, Shift/Ctrl = 고르기에 넣고 빼기) · 메모 수 · 잠금.
   폴더·줄(묶음) 줄: 접기 · 눈(그 아래 화면 모두) · 폴더 아이콘 · 이름(누르면 그 화면 모두 고르기) · 화면 수 ·
     올리면 [가로로 늘어놓기][세로로 늘어놓기], 사용자 폴더는 [폴더 풀기]도. 사용자 폴더 이름 두 번 누르기 = 이름 바꾸기.
   화면 줄을 끌어 사용자 폴더 줄에 놓으면 그 폴더로, 줄(묶음) 줄에 놓으면 폴더에서 빼기. 폴더는 패널에서만 묶는다(판 카드는 안 움직임).
   위: 이름 찾기 + 거르기 아이콘(숨긴 것만 · 잠긴 것만 · 메모 있는 것), 아래 막대: 폴더로 묶기 · 빈 레이아웃 · 숨기기 · 잠그기 · 삭제(고른 화면).
   숨김·잠금·고르기·폴더 상태의 주인은 셸 — 여기는 의도만 보낸다.
   HD.viewLayers.mount(ctx) → {render(), only(f)} · HD.viewLayers.CSS = 셸에 붙일 폴더 모양(문자열)
   ctx = {$, esc, root, tree() → {groups, texts}, state() → {hidden, locked, memo}, picked() → [id],
          hide(ids, on), lock(ids, on), reveal(id), addLayout(), del(ids),
          folders: {state(), dispatch(a)}, pick(ids, mode 'only'|'toggle'|'add'), arrange(ids, axis 'x'|'y')} — 폴더 셋은 없으면 그 기능만 빠진다 */
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
  del: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  fShut: '<path d="M3 6h7l2 2h9v11H3z"/>',
  fOpen: '<path d="M3 19V6h7l2 2h7v3"/><path d="M3 19l3-8h16l-3 8z"/>',
  fNew: '<path d="M3 6h7l2 2h9v11H3z"/><path d="M12 11v5M9.5 13.5h5"/>',
  fUn: '<path d="M3 6h7l2 2h9v11H3z"/><path d="M10 11.5l4 4M14 11.5l-4 4"/>',
  rowX: '<rect x="2" y="8" width="5" height="8" rx="1"/><rect x="9.5" y="8" width="5" height="8" rx="1"/><rect x="17" y="8" width="5" height="8" rx="1"/>',
  rowY: '<rect x="8" y="2" width="8" height="5" rx="1"/><rect x="8" y="9.5" width="8" height="5" rx="1"/><rect x="8" y="17" width="8" height="5" rx="1"/>'
};
function svg(d) { return '<svg viewBox="0 0 24 24">' + d + '</svg>'; }
var EMPTY = {v: 1, folders: []};

function mount(ctx) {
  var $ = ctx.$, esc = ctx.esc, root = ctx.root, L = HD.layers, folded = {}, only = null, FD = ctx.folders || null;
  root.innerHTML =
    '<div class="ly-top"><input id="lyQ" type="search" placeholder="이름 찾기" aria-label="레이어 찾기">' +
    '<span id="lyF" role="group" aria-label="거르기">' +
      '<button type="button" data-f="hidden" aria-pressed="false" title="숨긴 것만">' + svg(I.off) + '</button>' +
      '<button type="button" data-f="locked" aria-pressed="false" title="잠긴 것만">' + svg(I.lock) + '</button>' +
      '<button type="button" data-f="memo" aria-pressed="false" title="메모 있는 것">' + svg(I.memo) + '</button></span></div>' +
    '<div id="lyTree" role="tree" aria-label="레이어"></div>' +
    '<div id="lyBar" role="toolbar" aria-label="고른 화면">' +
      (FD ? '<button type="button" data-act="folder" title="폴더로 묶기" aria-label="폴더로 묶기">' + svg(I.fNew) + '</button>' : '') +
      '<button type="button" data-act="layout" title="빈 레이아웃 (N)">' + svg(I.layout) + '</button>' +
      '<button type="button" data-act="hide" title="숨기기">' + svg(I.off) + '</button>' +
      '<button type="button" data-act="lock" title="잠그기 · 풀기">' + svg(I.lock) + '</button>' +
      '<button type="button" data-act="del" title="삭제 (Del)">' + svg(I.del) + '</button></div>';
  var q = $('#lyQ'), tree = $('#lyTree'), fbar = $('#lyF'), bar = $('#lyBar');

  function fstate() { var s = FD && FD.state(); return s && Array.isArray(s.folders) ? s : EMPTY; }
  function isFolded(x) { return x.kind === 'folder' ? x.open === false : !!folded[x.id]; }
  function hov(x) {
    var b = '';
    if (ctx.arrange) b += '<button type="button" class="ly-hov" data-arr="x" title="가로로 늘어놓기" aria-label="가로로 늘어놓기">' + svg(I.rowX) + '</button>' +
      '<button type="button" class="ly-hov" data-arr="y" title="세로로 늘어놓기" aria-label="세로로 늘어놓기">' + svg(I.rowY) + '</button>';
    if (x.kind === 'folder' && FD) b += '<button type="button" class="ly-hov" data-act="unfolder" title="폴더 풀기" aria-label="폴더 풀기">' + svg(I.fUn) + '</button>';
    return b;
  }
  function rowHtml(x, picked) {
    var cls = 'ly-r ' + x.kind + (x.hid ? ' hid' : '') + (x.lock ? ' locked' : '') + (picked[x.id] ? ' on' : '') + (x.folder ? ' infolder' : '');
    var eye = '<button type="button" class="ly-eye" aria-pressed="' + !x.hid + '" aria-label="' + (x.hid ? '보이기' : '숨기기') + '">' + svg(x.hid ? I.off : I.eye) + '</button>';
    if (x.kind === 'row' || x.kind === 'folder') {
      var shut = isFolded(x);
      return '<div class="' + cls + '" data-ly="' + esc(x.id) + '" data-kind="' + x.kind + '" data-id="' + esc(x.id) + '" role="treeitem" aria-expanded="' + !shut + '">' +
        '<button type="button" class="ly-fold" aria-label="' + (shut ? '펴기' : '접기') + '">' + (shut ? '▸' : '▾') + '</button>' + eye +
        '<span class="ly-ficon" aria-hidden="true">' + svg(shut ? I.fShut : I.fOpen) + '</span>' +
        '<span class="ly-name"' + (x.kind === 'folder' ? ' title="두 번 눌러 이름 바꾸기"' : '') + '>' + esc(x.name) + '</span>' +
        hov(x) + '<span class="ly-count" title="화면 ' + (x.count || 0) + '개">' + (x.count || 0) + '</span></div>';
    }
    return '<div class="' + cls + '" data-ly="' + esc(x.id) + '" data-kind="' + x.kind + '" role="treeitem"' + (x.kind === 'screen' ? ' draggable="true"' : '') + '>' + eye +
      '<span class="ly-name">' + esc(x.name) + '</span>' + (x.memo ? '<span class="ly-cnt" title="메모 ' + x.memo + '건">' + x.memo + '</span>' : '') +
      (x.kind === 'screen' ? '<button type="button" class="ly-lock" aria-pressed="' + x.lock + '" aria-label="' + (x.lock ? '잠금 풀기' : '잠그기') + '">' + svg(x.lock ? I.lock : I.open) + '</button>' : '') +
      '</div>';
  }
  var list = [], renaming = null;
  function render() {
    renaming = null;
    var t = ctx.tree(), picked = {}, ids = ctx.picked(), fs = fstate(), fold = {};
    ids.forEach(function (id) { picked[id] = 1; });
    list = L.build(t.groups, t.texts, ctx.state(), fs);
    Object.keys(folded).forEach(function (k) { fold[k] = 1; });
    fs.folders.forEach(function (f) { if (f.open === false) fold[f.id] = 1; });
    var shown = L.filter(list, {q: q.value, only: only, folded: fold});
    tree.innerHTML = shown.length ? shown.map(function (x) { return rowHtml(x, picked); }).join('') : '<p class="dkp-empty">맞는 레이어가 없어요</p>';
    $$f().forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.f === only)); });
    var fb = bar.querySelector('[data-act="folder"]'); if (fb) fb.disabled = !ids.length;
  }
  function $$f() { return Array.prototype.slice.call(fbar.querySelectorAll('button[data-f]')); }
  function kids(headId) { return list.filter(function (x) { return x.kind === 'screen' && (x.folder || x.row) === headId; }).map(function (x) { return x.id; }); }
  function seen(headId) { return list.filter(function (x) { return x.kind === 'screen' && !x.hid && (x.folder || x.row) === headId; }).map(function (x) { return x.id; }); }
  function item(id) { return list.filter(function (x) { return x.id === id; })[0]; }
  function setOnly(f) { only = f || null; render(); }
  function send(a) { if (!FD) return; FD.dispatch(a); render(); }

  // 사용자 폴더 이름 바꾸기 — Enter·밖 누르기 = 저장, Esc = 그대로
  function rename(id) {
    var r = tree.querySelector('[data-kind="folder"][data-ly="' + id.replace(/"/g, '\\"') + '"]'), x = item(id);
    if (!r || !x || !FD) return;
    var span = r.querySelector('.ly-name'), inp = document.createElement('input'), done = false;
    inp.className = 'ly-rename'; inp.type = 'text'; inp.value = x.name; inp.setAttribute('aria-label', '폴더 이름');
    span.replaceWith(inp); renaming = id; inp.focus(); inp.select();
    function end(save) {
      if (done) return; done = true; renaming = null;
      if (save) FD.dispatch({type: 'rename', id: id, name: inp.value});
      render();
    }
    inp.addEventListener('keydown', function (e) {
      e.stopPropagation();
      if (e.key === 'Enter') { e.preventDefault(); end(true); } else if (e.key === 'Escape') { e.preventDefault(); end(false); }
    });
    inp.addEventListener('blur', function () { end(true); });
    ['pointerdown', 'click', 'dblclick', 'wheel'].forEach(function (ev) { inp.addEventListener(ev, function (e) { e.stopPropagation(); }); });
  }

  q.addEventListener('input', render);
  ['pointerdown', 'keydown', 'wheel'].forEach(function (ev) { q.addEventListener(ev, function (e) { e.stopPropagation(); }); });   // 판 단축키·끌기와 겹치지 않게
  fbar.addEventListener('click', function (e) { var b = e.target.closest('button[data-f]'); if (b) setOnly(only === b.dataset.f ? null : b.dataset.f); });
  tree.addEventListener('click', function (e) {
    if (e.target.closest('.ly-rename')) return;
    var r = e.target.closest('[data-ly]'); if (!r) return;
    var id = r.dataset.ly, x = item(id); if (!x) return;
    var head = x.kind === 'row' || x.kind === 'folder';
    if (e.target.closest('.ly-fold')) {
      if (x.kind === 'folder') send({type: 'fold', id: id, open: x.open === false});
      else { if (folded[id]) delete folded[id]; else folded[id] = 1; render(); }
      return;
    }
    if (e.target.closest('.ly-eye')) { ctx.hide(head ? kids(id) : [id], !x.hid); return; }
    if (e.target.closest('.ly-lock')) { ctx.lock([id], !x.lock); return; }
    var arr = e.target.closest('[data-arr]');
    if (arr) { if (ctx.arrange && head) ctx.arrange(seen(id), arr.dataset.arr); return; }
    if (e.target.closest('[data-act="unfolder"]')) { if (x.kind === 'folder') send({type: 'remove', id: id}); return; }
    if (head) { if (ctx.pick && e.target.closest('.ly-name')) ctx.pick(seen(id), 'only'); return; }
    if (x.kind !== 'screen' || x.hid) return;
    if ((e.shiftKey || e.ctrlKey || e.metaKey) && ctx.pick) { ctx.pick([id], 'toggle'); return; }
    ctx.reveal(id);
  });
  tree.addEventListener('dblclick', function (e) {
    var n = e.target.closest('.ly-name'), r = n && n.closest('[data-kind="folder"]');
    if (r) { e.preventDefault(); rename(r.dataset.ly); }
  });

  // 끌어 옮기기(HTML5) — 화면 줄 → 사용자 폴더 줄(넣기) · 줄(묶음) 줄(빼기)
  var dragId = null;
  function clearDrop() { Array.prototype.forEach.call(tree.querySelectorAll('.ly-drop'), function (n) { n.classList.remove('ly-drop'); }); }
  function target(e) { var r = e.target.closest && e.target.closest('[data-kind="folder"],[data-kind="row"]'); return r && FD && dragId ? r : null; }
  tree.addEventListener('dragstart', function (e) {
    var r = e.target.closest && e.target.closest('[data-kind="screen"]');
    if (!r) return;
    if (!FD) { e.preventDefault(); return; }   // 폴더가 없으면 끌 곳도 없다
    dragId = r.dataset.ly;
    try { e.dataTransfer.setData('text/plain', dragId); e.dataTransfer.effectAllowed = 'move'; } catch (err) {}
  });
  tree.addEventListener('dragover', function (e) {
    var r = target(e); if (!r) return;
    e.preventDefault();
    try { e.dataTransfer.dropEffect = 'move'; } catch (err) {}
    if (!r.classList.contains('ly-drop')) { clearDrop(); r.classList.add('ly-drop'); }
  });
  tree.addEventListener('dragleave', function (e) {
    var r = target(e); if (r && !r.contains(e.relatedTarget)) r.classList.remove('ly-drop');
  });
  tree.addEventListener('drop', function (e) {
    var r = target(e), id = dragId; clearDrop(); dragId = null;
    if (!r) return;
    e.preventDefault();
    var x = item(id); if (!x) return;
    if (r.dataset.kind === 'folder') { if (x.folder !== r.dataset.ly) send({type: 'add', id: r.dataset.ly, ids: [id]}); }
    else if (x.folder) send({type: 'take', ids: [id]});
  });
  tree.addEventListener('dragend', function () { clearDrop(); dragId = null; });

  bar.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act]'); if (!b) return;
    var ids = ctx.picked(), a = b.dataset.act;
    if (a === 'layout') { ctx.addLayout(); return; }
    if (!ids.length) return;
    if (a === 'folder') {
      if (!FD) return;
      q.value = ''; only = null;   // 새 폴더가 거르기에 가리지 않게
      send({type: 'create', ids: ids});
      var f = fstate().folders[0];
      if (f) rename(f.id);
    }
    else if (a === 'hide') ctx.hide(ids, true);
    else if (a === 'lock') { var st = ctx.state().locked || {}; ctx.lock(ids, !ids.every(function (id) { return st[id]; })); }
    else if (a === 'del') ctx.del(ids);
  });
  render();
  return {render: function () { if (renaming) return; render(); }, only: setOnly};
}

// 폴더 모양 — 회색만(H13). 4단계에서 셸 CSS 에 붙인다.
var CSS =
  '.ly-r.folder,.ly-r.row{font-weight:700;color:#444}\n' +
  '.ly-r.folder .ly-name,.ly-r.row .ly-name{cursor:pointer}\n' +
  '.ly-ficon{display:grid;place-items:center;width:18px;height:18px;color:#777;flex:none}\n' +
  '.ly-ficon svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linejoin:round}\n' +
  '.ly-count{font-size:11px;font-weight:400;color:#777;min-width:18px;text-align:right;padding-right:4px;flex:none}\n' +
  '.ly-r .ly-hov{opacity:0}.ly-r:hover .ly-hov,.ly-r .ly-hov:focus-visible{opacity:1}\n' +
  '.ly-r.screen[draggable="true"]{cursor:grab}\n' +
  '.ly-r.ly-drop{background:#E4E4E0;box-shadow:inset 0 0 0 1px #9a9a95}\n' +
  '.ly-rename{flex:1;min-width:0;height:22px;border:1px solid #9a9a95;border-radius:4px;padding:0 4px;font:inherit;font-weight:400}\n' +
  '#lyBar button:disabled{opacity:.35;cursor:default}\n';

HD.viewLayers = {mount: mount, CSS: CSS};
})();
