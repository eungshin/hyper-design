/* View — 레이어 패널(조각 4, H6·H7 · 폴더 H17). 나무와 거르기는 modules/layers.js(Model), 폴더 규칙은 modules/folders.js(Model), 여기는 그리기와 누르기만.
   줄마다: 눈(숨김) · 이름(누르면 그 카드로 + 고르기, Shift/Ctrl = 고르기에 넣고 빼기) · 메모 수 · 잠금.
   폴더·줄(묶음) 줄: 접기 · 눈(그 아래 화면 모두) · 폴더 아이콘 · 이름(누르면 그 화면 모두 고르기) · 화면 수 ·
     올리면 [가로로 늘어놓기][세로로 늘어놓기], 사용자 폴더는 [폴더 풀기]도. 사용자 폴더 이름 두 번 누르기 = 이름 바꾸기.
   줄(묶음) = 판의 섹션(51-4): id = HD.layers.rowId(줄 이름)(셸 tree() 의 'g'+차례를 여기서 바꾼다), 이름 두 번 누르기 = 줄 이름 바꾸기,
     올리면 [줄만 걷기], 오른쪽 메뉴 = 이름 바꾸기 · 줄만 걷기 · 줄 화면 모두 삭제. 쓰기는 view-rows 'rowHeads' 가 맡는다 — 의도 'hd-row-rename' {from, to} ·
     'hd-row-dissolve' {name} 를 보내고, 'hd-row-pick' {ids}(→ ctx.pick) · 'hd-row-delete' {ids}(→ ctx.del) · 'hd-rows-changed'(→ 다시 그리기, 이름이 바뀐 줄의 접힘을 옮김)를 받는다.
   화면 줄을 끌어 사용자 폴더(머리 줄이든 그 안 화면 줄이든)에 놓으면 그 폴더로, 줄(묶음)에 놓으면 폴더에서 빼기 — 끈 줄이 고른 화면이면 고른 것 모두.
   끄는 중 나무 위·아래 끝에 가면 저절로 스크롤. 폴더는 패널에서만 묶는다(판 카드는 안 움직임).
   위: 이름 찾기 + 거르기 아이콘(숨긴 것만 · 잠긴 것만 · 메모 있는 것),
   아래 막대: 폴더로 묶기 · 폴더로 옮기기(메뉴: 폴더 목록 · 폴더에서 빼기) · 빈 레이아웃 · 숨기기 · 잠그기 · 삭제(고른 화면).
   숨김·잠금·고르기·폴더 상태의 주인은 셸 — 여기는 의도만 보낸다.
   HD.viewLayers.mount(ctx) → {render(), only(f)} · HD.viewLayers.CSS = 셸에 붙일 폴더 모양(문자열)
   ctx = {$, esc, root, tree() → {groups, texts}, state() → {hidden, locked, memo}, picked() → [id],
          hide(ids, on), lock(ids, on), reveal(id), addLayout(), del(ids),
          folders: {state(), dispatch(a)}, pick(ids, mode 'only'|'toggle'|'add'), arrange(ids, axis 'x'|'y'), hover(ids)} — 폴더 셋·hover 는 없으면 그 기능만 빠진다
   판 글 줄(kind text)을 누르면 의도 'hd-board-pick' {id}(판에서 그 글 고르기, t51-9).
   줄에 마우스를 올리면 ctx.hover(HD.layers.hoverIds(나무, 그 줄 id)) — 판이 그 카드·판 글을 강조(51-3, Figma F10), 나무 밖으로 나가면 hover([]) */
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
  fMove: '<path d="M3 6h7l2 2h9v11H3z"/><path d="M9 13.5h6M12.5 11l2.5 2.5-2.5 2.5"/>',
  rowX: '<rect x="2" y="8" width="5" height="8" rx="1"/><rect x="9.5" y="8" width="5" height="8" rx="1"/><rect x="17" y="8" width="5" height="8" rx="1"/>',
  ungroup: '<path d="M4 5h16M4 19h16"/><path d="M12 8v7M9 12l3 3 3-3"/>',
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
      (FD ? '<button type="button" data-act="folder" title="폴더로 묶기" aria-label="폴더로 묶기">' + svg(I.fNew) + '</button>' +
            '<button type="button" data-act="move" title="폴더로 옮기기" aria-label="폴더로 옮기기" aria-haspopup="menu">' + svg(I.fMove) + '</button>' : '') +
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
    if (section(x)) b += '<button type="button" class="ly-hov" data-act="ungroup" title="줄만 걷기 (Ctrl+Backspace) — 화면은 위 줄로" aria-label="줄만 걷기">' + svg(I.ungroup) + '</button>';
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
        '<span class="ly-name"' + (x.kind === 'folder' || section(x) ? ' title="두 번 눌러 이름 바꾸기"' : '') + '>' + esc(x.name) + '</span>' +
        hov(x) + '<span class="ly-count" title="화면 ' + (x.count || 0) + '개">' + (x.count || 0) + '</span></div>';
    }
    return '<div class="' + cls + '" data-ly="' + esc(x.id) + '" data-kind="' + x.kind + '" role="treeitem"' + (x.kind === 'screen' ? ' draggable="true"' : '') + '>' + eye +
      '<span class="ly-name">' + esc(x.name) + '</span>' + (x.memo ? '<span class="ly-cnt" title="메모 ' + x.memo + '건">' + x.memo + '</span>' : '') +
      (x.kind === 'screen' ? '<button type="button" class="ly-lock" aria-pressed="' + x.lock + '" aria-label="' + (x.lock ? '잠금 풀기' : '잠그기') + '">' + svg(x.lock ? I.lock : I.open) + '</button>' : '') +
      '</div>';
  }
  function section(x) { return x.kind === 'row' && String(x.id).indexOf('row:') === 0; }   // 판의 줄(빈 레이아웃 묶음 '@drafts' 는 아님)
  function rows(groups) {                            // 줄 id = 줄 이름(51-4) — 셸 tree() 는 차례('g'+i)를 준다
    return (groups || []).map(function (g) { return !g || String(g.id).charAt(0) === '@' ? g : {id: L.rowId(g.name), name: g.name, screens: g.screens}; });
  }
  var list = [], renaming = null;
  function render() {
    renaming = null;
    var t = ctx.tree(), picked = {}, ids = ctx.picked(), fs = fstate(), fold = {};
    ids.forEach(function (id) { picked[id] = 1; });
    list = L.build(rows(t.groups), t.texts, ctx.state(), fs);
    Object.keys(folded).forEach(function (k) { fold[k] = 1; });
    fs.folders.forEach(function (f) { if (f.open === false) fold[f.id] = 1; });
    var shown = L.filter(list, {q: q.value, only: only, folded: fold});
    tree.innerHTML = shown.length ? shown.map(function (x) { return rowHtml(x, picked); }).join('') : '<p class="dkp-empty">맞는 레이어가 없어요</p>';
    $$f().forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.f === only)); });
    var fb = bar.querySelector('[data-act="folder"]'); if (fb) fb.disabled = !ids.length;
    var mb = bar.querySelector('[data-act="move"]'); if (mb) mb.disabled = !ids.length;
  }
  function $$f() { return Array.prototype.slice.call(fbar.querySelectorAll('button[data-f]')); }
  function kids(headId) { return list.filter(function (x) { return x.kind === 'screen' && (x.folder || x.row) === headId; }).map(function (x) { return x.id; }); }
  function seen(headId) { return list.filter(function (x) { return x.kind === 'screen' && !x.hid && (x.folder || x.row) === headId; }).map(function (x) { return x.id; }); }
  function item(id) { return list.filter(function (x) { return x.id === id; })[0]; }
  function setOnly(f) { only = f || null; render(); }
  function send(a) { if (!FD) return; FD.dispatch(a); render(); }

  // 사용자 폴더·줄 이름 바꾸기 — Enter·밖 누르기 = 저장, Esc = 그대로. 줄은 의도만 보낸다(검사·쓰기는 view-rows)
  function rename(id) {
    var r = headEl(id), x = item(id), row = !!x && section(x);
    if (!r || !x || (!row && (x.kind !== 'folder' || !FD))) return;
    var span = r.querySelector('.ly-name'), inp = document.createElement('input'), done = false;
    inp.className = 'ly-rename'; inp.type = 'text'; inp.value = x.name; inp.setAttribute('aria-label', row ? '줄 이름' : '폴더 이름');
    span.replaceWith(inp); renaming = id; inp.focus(); inp.select();
    function end(save) {
      if (done) return; done = true; renaming = null;
      if (save && row) { if (inp.value.trim() !== x.name) emit('hd-row-rename', {from: x.name, to: inp.value}); }
      else if (save) FD.dispatch({type: 'rename', id: id, name: inp.value});
      render();
    }
    inp.addEventListener('keydown', function (e) {
      e.stopPropagation();
      if (e.key === 'Enter') { e.preventDefault(); end(true); } else if (e.key === 'Escape') { e.preventDefault(); end(false); }
    });
    inp.addEventListener('blur', function () { end(true); });
    ['pointerdown', 'click', 'dblclick', 'wheel'].forEach(function (ev) { inp.addEventListener(ev, function (e) { e.stopPropagation(); }); });
  }

  function emit(type, d) { document.dispatchEvent(new CustomEvent(type, {detail: d})); }
  document.addEventListener('hd-row-pick', function (e) { var d = e.detail || {}; if (ctx.pick && Array.isArray(d.ids)) ctx.pick(d.ids, 'only'); });
  document.addEventListener('hd-row-delete', function (e) { var d = e.detail || {}; if (Array.isArray(d.ids) && d.ids.length) ctx.del(d.ids); });
  document.addEventListener('hd-rows-changed', function (e) {
    var d = e.detail || {};
    if (d.renamed) folded = L.renameRow(folded, d.renamed.from, d.renamed.to);
    if (!renaming) render();
  });

  var hovId = null;                                  // 올린 줄(51-3) — 같은 줄 안 움직임은 한 번만 알린다
  function hoverTo(id) { if (id === hovId) return; hovId = id; if (ctx.hover) ctx.hover(id ? L.hoverIds(list, id) : []); }
  tree.addEventListener('mouseover', function (e) { var r = e.target.closest && e.target.closest('[data-ly]'); hoverTo(r && !dragId ? r.dataset.ly : null); });
  tree.addEventListener('mouseleave', function () { hoverTo(null); });

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
    if (e.target.closest('[data-act="ungroup"]')) { if (section(x)) emit('hd-row-dissolve', {name: x.name}); return; }
    if (head) { if (ctx.pick && e.target.closest('.ly-name')) ctx.pick(seen(id), 'only'); return; }
    if (x.kind === 'text') { if (!x.hid) emit('hd-board-pick', {id: id}); return; }   // 판 글 줄 = 판에서 그 글 고르기(t51-9, view-board-text)
    if (x.kind !== 'screen' || x.hid) return;
    if ((e.shiftKey || e.ctrlKey || e.metaKey) && ctx.pick) { ctx.pick([id], 'toggle'); return; }
    ctx.reveal(id);
  });
  tree.addEventListener('dblclick', function (e) {
    var n = e.target.closest('.ly-name'), r = n && n.closest('[data-kind="folder"],[data-kind="row"]');
    if (r) { e.preventDefault(); rename(r.dataset.ly); }
  });
  tree.addEventListener('contextmenu', function (e) {   // 줄 오른쪽 메뉴(51-4): 이름 바꾸기 · 줄만 걷기 · 줄 화면 모두 삭제
    var r = e.target.closest('[data-kind="row"]'), x = r && item(r.dataset.ly);
    if (!x || !section(x) || e.target.closest('.ly-rename')) return;
    e.preventDefault(); e.stopPropagation();
    openMenu(null, [{icon: I.layout, label: '이름 바꾸기', act: function () { rename(x.id); }},
                    {icon: I.ungroup, label: '줄만 걷기 — 화면은 위 줄로', act: function () { emit('hd-row-dissolve', {name: x.name}); }},
                    {icon: I.del, label: '줄 화면 모두 삭제', act: function () { var ids = kids(x.id); if (ids.length) ctx.del(ids); }}], e.clientX, e.clientY);
  });

  // 끌어 옮기기(HTML5) — 화면 줄 → 사용자 폴더(넣기) · 줄(묶음)(빼기). 놓는 곳은 머리 줄이든 그 안 화면 줄이든 같은 묶음
  var dragId = null, dragIds = null;
  function clearDrop() { Array.prototype.forEach.call(tree.querySelectorAll('.ly-drop'), function (n) { n.classList.remove('ly-drop'); }); }
  function headEl(id) {
    var heads = tree.querySelectorAll('[data-kind="folder"],[data-kind="row"]');
    for (var i = 0; i < heads.length; i++) if (heads[i].dataset.ly === id) return heads[i];
    return null;
  }
  function target(e) {                               // → 그 묶음의 머리 줄(폴더·줄)
    if (!FD || !dragId) return null;
    var r = e.target.closest && e.target.closest('[data-ly]'); if (!r) return null;
    if (r.dataset.kind === 'folder' || r.dataset.kind === 'row') return r;
    var x = item(r.dataset.ly); if (!x || x.kind !== 'screen') return null;
    var h = x.folder || x.row; return h ? headEl(h) : null;
  }
  function moveTo(head, ids) {                        // head = 폴더 id(넣기) · 줄 id 또는 ''(빼기)
    var f = fstate().folders.filter(function (g) { return g.id === head; })[0];
    if (f) { var add = ids.filter(function (id) { return f.ids.indexOf(id) < 0; }); if (add.length) send({type: 'add', id: head, ids: add}); }
    else { var out = ids.filter(function (id) { var x = item(id); return x && x.folder; }); if (out.length) send({type: 'take', ids: out}); }
  }
  function autoScroll(e) {                           // 끄는 중 나무 끝 가까이 = 그쪽으로 스크롤(긴 목록에서도 폴더에 닿게)
    var r = tree.getBoundingClientRect(), edge = 28;
    if (e.clientY < r.top + edge) tree.scrollTop -= 14; else if (e.clientY > r.bottom - edge) tree.scrollTop += 14;
  }
  tree.addEventListener('dragstart', function (e) {
    var r = e.target.closest && e.target.closest('[data-kind="screen"]');
    if (!r) return;
    if (!FD) { e.preventDefault(); return; }   // 폴더가 없으면 끌 곳도 없다
    dragId = r.dataset.ly;
    var pk = ctx.picked(); dragIds = pk.indexOf(dragId) >= 0 ? pk.slice() : [dragId];   // 고른 줄을 끌면 고른 것 모두
    try { e.dataTransfer.setData('text/plain', dragId); e.dataTransfer.effectAllowed = 'move'; } catch (err) {}
  });
  tree.addEventListener('dragover', function (e) {
    if (dragId) autoScroll(e);
    var r = target(e); if (!r) return;
    e.preventDefault();
    try { e.dataTransfer.dropEffect = 'move'; } catch (err) {}
    if (!r.classList.contains('ly-drop')) { clearDrop(); r.classList.add('ly-drop'); }
  });
  tree.addEventListener('dragleave', function (e) {
    var r = target(e); if (r && !r.contains(e.relatedTarget)) r.classList.remove('ly-drop');
  });
  tree.addEventListener('drop', function (e) {
    var r = target(e), ids = dragIds || []; clearDrop(); dragId = null; dragIds = null;
    if (!r) return;
    e.preventDefault();
    moveTo(r.dataset.kind === 'folder' ? r.dataset.ly : '', ids);
  });
  tree.addEventListener('dragend', function () { clearDrop(); dragId = null; dragIds = null; });

  // [폴더로 옮기기] 메뉴 — 끌지 않고 고른 화면을 폴더로(폴더 목록 · 폴더에서 빼기)
  var menu = null;
  function closeMenu() { if (menu) { menu.remove(); menu = null; document.removeEventListener('pointerdown', outside, true); } }
  function outside(e) { if (menu && !menu.contains(e.target) && !(e.target.closest && e.target.closest('#lyBar [data-act="move"]'))) closeMenu(); }
  function openMenu(btn, acts, x, y) {               // btn = [폴더로 옮기기] 메뉴 · acts = [{icon, label, act}] 를 (x, y) 에(줄 오른쪽 메뉴, 51-4)
    closeMenu();
    var fs = fstate().folders;
    menu = document.createElement('div'); menu.className = 'ly-menu'; menu.setAttribute('role', 'menu');
    menu.innerHTML = acts ? acts.map(function (a, i) { return '<button type="button" role="menuitem" data-a="' + i + '">' + svg(a.icon) + '<span>' + esc(a.label) + '</span></button>'; }).join('') :
      fs.map(function (f) { return '<button type="button" role="menuitem" data-to="' + esc(f.id) + '">' + svg(I.fShut) + '<span>' + esc(f.name) + '</span></button>'; }).join('') +
      (fs.length ? '<hr>' : '<p class="dkp-empty">폴더가 없어요 — 먼저 폴더로 묶기</p>') +
      '<button type="button" role="menuitem" data-to="">' + svg(I.fUn) + '<span>폴더에서 빼기</span></button>';
    document.body.appendChild(menu);
    if (btn) {
      var b = btn.getBoundingClientRect();
      menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, b.right - menu.offsetWidth)) + 'px';
      menu.style.top = Math.max(8, b.top - menu.offsetHeight - 4) + 'px';
    } else {
      menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, x)) + 'px';
      menu.style.top = Math.max(8, Math.min(innerHeight - menu.offsetHeight - 8, y)) + 'px';
    }
    menu.addEventListener('click', function (e) {
      var a = e.target.closest('[data-a]');
      if (a && acts) { var f = acts[+a.dataset.a]; closeMenu(); f.act(); return; }
      var it = e.target.closest('[data-to]'); if (!it) return;
      var ids = ctx.picked(); closeMenu(); moveTo(it.dataset.to, ids);
    });
    ['pointerdown', 'keydown', 'wheel'].forEach(function (ev) { menu.addEventListener(ev, function (e) { e.stopPropagation(); if (ev === 'keydown' && e.key === 'Escape') closeMenu(); }); });
    document.addEventListener('pointerdown', outside, true);
  }

  bar.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act]'); if (!b) return;
    var ids = ctx.picked(), a = b.dataset.act;
    if (a === 'layout') { ctx.addLayout(); return; }
    if (!ids.length) return;
    if (a === 'move') { if (menu) closeMenu(); else openMenu(b); return; }
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
  '#lyBar button:disabled{opacity:.35;cursor:default}\n' +
  '.ly-menu{position:fixed;z-index:60;min-width:160px;max-height:50vh;overflow:auto;background:#fff;border:1px solid #d6d6d1;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.14);padding:4px}\n' +
  '.ly-menu button{display:flex;align-items:center;gap:8px;width:100%;height:28px;padding:0 8px;border:0;border-radius:5px;background:none;font:13px system-ui,-apple-system,sans-serif;color:#2b2b29;cursor:pointer;text-align:left}\n' +
  '.ly-menu button:hover{background:#ecece8}.ly-menu svg{width:16px;height:16px;fill:none;stroke:#777;stroke-width:1.6;flex:none}\n' +
  '.ly-menu hr{border:0;border-top:1px solid #eee;margin:4px 0}.ly-menu .dkp-empty{margin:4px 8px;font-size:12px}\n';

HD.viewLayers = {mount: mount, CSS: CSS};
})();
