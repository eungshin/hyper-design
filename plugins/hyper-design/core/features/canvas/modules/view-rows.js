/* View — 판의 화면 줄(섹션): 그리기·새 데이터에 맞추기(51-1)와 줄 제목으로 고르기·이름 바꾸기·지우기·줄만 걷기(51-4).
   HD.viewRows.mount(ctx) → {html(rows) → 줄 전체 HTML(카드 아래 본문 = HD.caption.body — 설명 + 옛 정책 줄 '- ', R21),
                             sync(rows, has(id)) → {removed: [이름], added: [새로 만든 카드 요소]}, space()}
   space(): 줄 사이 띄우기(t51-8) — 카드 아래 설명(.cbody)은 고를 때만 펼쳐져 판 배치를 밀지 않으므로(task 31), 줄마다 펼친 설명이 들어갈 자리를 늘 비워 둔다
     (고르기로 아래 줄이 움직이지 않게). 접힌 카드도 잠깐 펼쳐 재고(그리기 전 같은 틱에서 되돌림) 계획은 HD.rows.space(Model), 그 값을 .flow 아래 여백으로.
     옮긴 카드(card-pos)는 제 자리(slot) 기준. 셸이 카드 글이 바뀐 뒤·줄 높이가 바뀐 뒤 부른다
   ctx = {rowsEl, $, $$, esc, warn(msg)}
   sync: 계획은 HD.rows.plan(Model). 걷은 줄은 이름별로 떼어 두었다가 같은 이름이 돌아오면(되살리기) 그 요소를 다시 끼운다 — 셸이 떼어 둔 카드(gone)가 제 상자로
   돌아가게. 처음 보는 줄은 rows 의 화면 중 has(id) 가 아닌 것(판에도·떼어 둔 곳에도 없음)으로 카드를 만든다. 붙이기(iframe 싣기·자리·크기)는 셸.
   줄 = 섹션(51-4, Figma F16·F17) — 등록부 기능 'rowHeads'(needs rowsEl·$·$$·api·record·toast·selected·warn). 상태 = 고른 줄 이름 하나(저장 안 함).
     제목 누르기 = 그 줄 카드 모두 고르기 · 두 번 = 그 자리 이름 바꾸기(Enter 저장 · Esc 취소 · 밖 누르기 저장) · Del/Backspace = 그 줄 화면 모두 지우기(기존 지우기 길)
     · Ctrl+Backspace(·제목 오른쪽 메뉴·레이어 줄 메뉴) = 줄만 걷기: 그 줄 화면은 위 줄로, 첫 줄이면 아래 줄로(HD.rows.target). 쓰기 = 도우미
     /api/group-rename · /api/group-dissolve 한 번 → 되돌리기 한 번(/api/restore). 판은 먼저 바꾸고(이름·카드 옮기기) 실패하면 되돌리고 알린다.
     의도(document CustomEvent) — 보냄: 'hd-row-pick' {ids}(고르기 = 레이어 패널의 ctx.pick) · 'hd-row-delete' {ids}(지우기 = ctx.del) ·
       'hd-rows-changed' {renamed?: {from, to}}(레이어 다시 그리기) / 받음: 'hd-row-rename' {from, to} · 'hd-row-dissolve' {name}(레이어 줄 메뉴) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var esc = ctx.esc, $ = ctx.$, $$ = ctx.$$, parked = {};
  function cardHtml(s) {
    var body = HD.caption.body(s.purpose, s.policies);
    return '<div class="card" data-id="' + esc(s.id) + '"><div class="phone"><iframe scrolling="no" tabindex="-1" title="' + esc(s.title) +
      '" data-src="' + esc(s.file) + '"></iframe><button class="cover" data-file="' + esc(s.file) + '" data-title="' + esc(s.title) +
      '" aria-label="' + esc(s.title) + ' 크게 보기"></button></div><button class="pres" data-file="' + esc(s.file) + '" data-title="' + esc(s.title) +
      '" title="실제로 눌러 보기(두 번 눌러도 같아요)" aria-label="' + esc(s.title) + ' 크게 보기">보기</button>' +
      '<div class="ftitle">' + (s.state ? '<span class="state">상태</span>' : '') + esc(s.title) + '</div>' +
      '<div class="cbody">' + (body ? '<div class="fdesc">' + esc(body) + '</div>' : '') + '</div></div>';
  }
  function rowHtml(row, screens) {
    return '<div class="flow"><div class="glabel">' + esc(row.group) + '</div><div class="cards">' + screens.map(cardHtml).join('') + '</div></div>';
  }
  function html(rows) { return (rows || []).map(function (r) { return rowHtml(r, r.screens || []); }).join(''); }
  function flows() { return $$('.flow', ctx.rowsEl); }
  function nameOf(f) { var g = $('.glabel', f); return g ? g.textContent : ''; }
  function sync(rows, has) {
    rows = Array.isArray(rows) ? rows : [];
    var byName = {}, now = {}, added = [];
    rows.forEach(function (r) { if (r && typeof r.group === 'string') byName[r.group] = r; });
    flows().forEach(function (f) { now[nameOf(f)] = f; });
    var p = HD.rows.plan(flows().map(function (f) { return {group: nameOf(f), n: $$('.card', f).length}; }), Object.keys(byName));
    p.remove.forEach(function (g) { var f = now[g]; if (!f) return; parked[g] = f; f.remove(); delete now[g]; });
    p.insert.forEach(function (it) {
      var f = parked[it.group];
      if (f) delete parked[it.group];
      else {
        var tmp = document.createElement('div');
        tmp.innerHTML = rowHtml(byName[it.group], (byName[it.group].screens || []).filter(function (s) { return !has(s.id); }));
        f = tmp.firstChild;
        $$('.card', f).forEach(function (c) { added.push(c); });
      }
      var at = it.before && now[it.before];
      if (it.before && !at) ctx.warn('[hd] 줄 맞추기: 기준 줄이 없어 끝에 붙여요 — ' + it.before);
      if (at) ctx.rowsEl.insertBefore(f, at);
      else { var last = flows().pop(); ctx.rowsEl.insertBefore(f, last ? last.nextSibling : null); }   // 끝 = 마지막 줄 뒤(빈 레이아웃 카드는 rowsEl 끝에 따로 붙는다)
      now[it.group] = f;
    });
    return {removed: p.remove, added: added};
  }
  var FOLD = ['capfold-d'];
  function space() {
    var fs = flows().filter(function (f) { return f.parentNode === ctx.rowsEl; });
    if (!fs.length) return;
    var k = ctx.rowsEl.offsetHeight ? ctx.rowsEl.getBoundingClientRect().height / ctx.rowsEl.offsetHeight : 1;   // 화면 px → 판 px(배율)
    if (!(k > 0)) k = 1;
    var top = ctx.rowsEl.getBoundingClientRect().top, y = function (r) { return (r - top) / k; }, folded = [];
    fs.forEach(function (f) { $$('.card', f).forEach(function (c) {
      var had = FOLD.filter(function (n) { return c.classList.contains(n); });
      if (had.length) { folded.push([c, had]); had.forEach(function (n) { c.classList.remove(n); }); }
    }); });
    var rows = fs.map(function (f) {
      var cs = $('.cards', f); if (!cs) return null;
      var bottom = y(cs.getBoundingClientRect().bottom), over = bottom;
      $$('.card', f).forEach(function (c) {
        var b = $(':scope > .cbody', c); if (!b || !b.offsetHeight) return;
        over = Math.max(over, y(b.getBoundingClientRect().bottom) - (parseFloat(c.style.top) || 0));   // 옮긴 카드 = 제 자리 기준
      });
      return {bottom: bottom, over: over};
    });
    folded.forEach(function (x) { x[1].forEach(function (n) { x[0].classList.add(n); }); });
    var base = parseFloat(getComputedStyle(fs[0]).paddingTop) || 0;
    HD.rows.space(rows, {base: base, clear: HD.rows.CLEAR}).forEach(function (px, i) {
      var v = px ? px + 'px' : '';
      if (fs[i].style.paddingBottom !== v) fs[i].style.paddingBottom = v;
    });
  }
  return {html: html, sync: sync, space: space};
}

HD.viewRows = {mount: mount};

// ---------------------------------------------------------------- 줄 = 섹션(51-4)
var CSS =
  '#rows .flow>.glabel{width:max-content;cursor:pointer;border-radius:calc(6px * var(--ts,1))}\n' +
  '#rows .flow>.glabel:hover{background:var(--ui-badge-soft);box-shadow:0 0 0 calc(8px * var(--ts,1)) var(--ui-badge-soft)}\n' +
  '#rows .flow>.glabel.hd-row-on{outline:calc(3px * var(--ts,1)) solid var(--ui-mark);outline-offset:calc(8px * var(--ts,1))}\n' +
  '#rows .flow>.glabel[contenteditable]{cursor:text;background:none;box-shadow:none;outline:calc(3px * var(--ts,1)) solid var(--ui-mark);outline-offset:calc(8px * var(--ts,1))}\n' +
  '.hd-rmenu{position:fixed;z-index:60;min-width:190px;background:#fff;border:1px solid var(--ui-badge-soft);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.14);padding:4px}\n' +
  '.hd-rmenu .cmh{padding:4px 8px;font:700 12px system-ui,sans-serif;color:var(--ui-badge);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:260px}\n' +
  '.hd-rmenu button{display:flex;align-items:center;gap:12px;width:100%;height:28px;padding:0 8px;border:0;border-radius:5px;background:none;font:13px system-ui,sans-serif;color:var(--ui-primary);cursor:pointer;text-align:left}\n' +
  '.hd-rmenu button:hover,.hd-rmenu button:focus-visible{background:var(--ui-badge-soft);outline:0}\n' +
  '.hd-rmenu kbd{margin-left:auto;font:11px ui-monospace,Menlo,monospace;color:var(--ui-badge)}\n' +
  '.hd-rmenu hr{border:0;border-top:1px solid var(--ui-badge-soft);margin:4px 0}\n';

function heads(ctx) {
  var R = HD.rows, rowsEl = ctx.rowsEl, $ = ctx.$, $$ = ctx.$$, cur = null, editing = null, menu = null;
  if (!document.getElementById('hd-rows-css')) {
    var st = document.createElement('style'); st.id = 'hd-rows-css'; st.textContent = CSS; document.head.appendChild(st);
  }
  function flows() { return $$('.flow', rowsEl).filter(function (f) { return f.parentNode === rowsEl; }); }
  function label(f) { return $('.glabel', f); }
  function nameOf(f) { var g = label(f); return g ? g.textContent : ''; }
  function names() { return flows().map(nameOf); }
  function flowOf(name) { return flows().filter(function (f) { return nameOf(f) === name; })[0] || null; }
  function idsOf(name, all) {
    var f = flowOf(name);
    return f ? $$('.card', f).filter(function (c) { return all || !c.classList.contains('hid'); }).map(function (c) { return c.dataset.id; }) : [];
  }
  function emit(type, detail) { document.dispatchEvent(new CustomEvent(type, {detail: detail || {}})); }
  function paint() { flows().forEach(function (f) { var g = label(f); if (g) g.classList.toggle('hd-row-on', !!cur && nameOf(f) === cur); }); }
  function select(name) { cur = name; paint(); emit('hd-row-pick', {ids: idsOf(name)}); }
  function drop() { if (cur) { cur = null; paint(); } }
  function same(a, b) { return a.length === b.length && a.slice().sort().join('\n') === b.slice().sort().join('\n'); }
  function stillOn() {                               // 고른 줄 = 그 줄 카드만 골라져 있을 때 — 다른 것을 고르면 풀린다
    if (cur && (!flowOf(cur) || !same(ctx.selected(), idsOf(cur)))) drop();
    return !!cur;
  }
  function changed(d) { emit('hd-rows-changed', d); }
  function off() { if (ctx.api.on) return false; ctx.toast('도우미로 열었을 때만 줄을 바꿀 수 있어요(파일에 바로 쓰기)'); return true; }
  function call(path, body) {                        // → 답 몸통(성공) | null(이유는 알렸다)
    return ctx.api.call('POST', path, body).then(function (r) {
      if (r.status === 200 && r.body && !r.body.error) return r.body;
      ctx.toast('줄을 바꾸지 못했어요: ' + ((r.body && r.body.error) || r.status)); return null;
    }, function (e) { ctx.toast('줄을 바꾸지 못했어요 — 도우미에 닿지 않아요'); ctx.warn('[hd] 줄 쓰기 실패: ' + (e && e.message || e)); return null; });
  }
  function restore(stamp, what, after) {
    return ctx.api.call('POST', '/api/restore', {stamp: stamp}).then(function (r) {
      if (r.body && r.body.error) { ctx.toast(r.body.reason === 'changed-since' ? '그 뒤에 파일이 바뀌어 되돌릴 수 없어요' : '되돌리지 못했어요: ' + r.body.error); return; }
      after();
    }, function () { ctx.toast('되돌리지 못했어요 — 도우미에 닿지 않아요: ' + what); });
  }
  function logged(what, stamp, undo, again) {        // 쓰기 한 번 = 기록 한 줄(되돌리기 = 되살리기, 다시 하기 = 같은 쓰기를 새로)
    var at = stamp;
    ctx.record({label: what, status: 'file',
      undo: function () { restore(at, what, undo); },
      redo: function () { again().then(function (r) { if (r && r.stamp) at = r.stamp; }); }});
  }

  // 이름 바꾸기
  function setName(from, to) {
    var f = flowOf(from); if (!f) return;
    label(f).textContent = to;
    if (cur === from) cur = to;
    changed({renamed: {from: from, to: to}});
  }
  function write(from, to) {                         // 판 이름 먼저 → 도우미 쓰기, 실패면 판 이름 되돌림
    setName(from, to);
    return call('/api/group-rename', {from: from, to: to}).then(function (r) {
      if (!r || !r.stamp) { if (flowOf(to)) setName(to, from); return null; }
      return r;
    });
  }
  function rename(from, to) {
    var c = R.checkName(names(), from, to);
    if (c.error) { ctx.toast(c.error); return; }
    if (c.same || off()) return;
    write(from, c.name).then(function (r) {
      if (!r) return;
      logged('줄 이름 바꾸기', r.stamp, function () { setName(c.name, from); }, function () { return write(from, c.name); });
      ctx.toast('줄 이름을 바꿨어요 — 파일에 썼어요', true);
    });
  }
  function edit(g) {                                 // 그 자리 고치기 — Enter 저장 · Esc 취소 · 밖 누르기 저장
    if (editing) return;
    var old = g.textContent, done = false;
    editing = g;
    try { g.contentEditable = 'plaintext-only'; } catch (e) { g.contentEditable = 'true'; }   // plaintext-only 를 모르는 브라우저
    g.setAttribute('role', 'textbox'); g.setAttribute('aria-label', '줄 이름');
    g.focus();
    var rg = document.createRange(); rg.selectNodeContents(g); var sel = getSelection(); sel.removeAllRanges(); sel.addRange(rg);
    function end(save) {
      if (done) return; done = true; editing = null;
      var v = g.textContent.replace(/\s+/g, ' ');
      g.removeAttribute('contenteditable'); g.removeAttribute('role'); g.removeAttribute('aria-label');
      g.removeEventListener('keydown', key); g.removeEventListener('blur', blur);
      g.textContent = old;
      if (save) rename(old, v);
    }
    function key(e) {
      e.stopPropagation();
      if (e.key === 'Enter') { e.preventDefault(); end(true); }
      else if (e.key === 'Escape') { e.preventDefault(); end(false); }
    }
    function blur() { end(true); }
    g.addEventListener('keydown', key);
    g.addEventListener('blur', blur);
  }

  // 줄만 걷기 — 판 먼저(카드를 그 줄로 옮기고 줄을 뗌) → 도우미 쓰기, 실패면 판 되돌림
  function move(name, t) {
    var f = flowOf(name), into = flowOf(t.into); if (!f || !into) return null;
    var box = $('.cards', into), cards = $$('.card', f), at = f.nextSibling, head = box.firstChild;
    cards.forEach(function (c) { if (t.where === 'above') box.appendChild(c); else box.insertBefore(c, head); });
    f.remove();
    if (cur === name) cur = null;
    paint(); changed();
    return {f: f, at: at, cards: cards};
  }
  function unmove(m) {
    var box = $('.cards', m.f);
    m.cards.forEach(function (c) { box.appendChild(c); });
    rowsEl.insertBefore(m.f, m.at && m.at.parentNode === rowsEl ? m.at : null);
    paint(); changed();
  }
  function dissolveOnce(name) {
    var t = R.target(names(), name);
    if (t.error) { ctx.toast(t.error); return Promise.resolve(null); }
    var m = move(name, t);
    if (!m) { ctx.warn('[hd] 줄만 걷기: 줄을 판에서 찾지 못했어요 — ' + name); return Promise.resolve(null); }
    return call('/api/group-dissolve', {name: name}).then(function (r) {
      if (!r || !r.stamp) { unmove(m); return null; }
      r.move = m; return r;
    });
  }
  function dissolve(name) {
    if (off()) return;
    dissolveOnce(name).then(function (r) {
      if (!r) return;
      var m = r.move;
      emit('hd-row-pick', {ids: m.cards.filter(function (c) { return !c.classList.contains('hid'); }).map(function (c) { return c.dataset.id; })});   // 걷은 뒤 그 화면들이 골라진 채(Figma Ungroup)
      logged('줄만 걷기', r.stamp, function () { unmove(m); }, function () { return dissolveOnce(name).then(function (x) { if (x) m = x.move; return x; }); });
      ctx.toast('줄만 걷었어요 — 화면 ' + m.cards.length + '개는 ' + (r.where === 'above' ? '위' : '아래') + ' 줄 「' + r.into + '」로', true);
    });
  }
  function remove(name) {                            // 그 줄 화면 모두 지우기 = 기존 지우기 길(레이어 패널 ctx.del → 셸 deleteCards, 되돌리기 한 번)
    var ids = idsOf(name, true); drop();
    if (ids.length) emit('hd-row-delete', {ids: ids});
  }

  // 오른쪽 메뉴
  function closeMenu() { if (menu) { menu.remove(); menu = null; document.removeEventListener('pointerdown', outside, true); } }
  function outside(e) { if (menu && !menu.contains(e.target)) closeMenu(); }
  function openMenu(x, y, name) {
    closeMenu();
    var items = [{l: '줄 고르기', k: '누르기', a: function () { select(name); }},
                 {l: '이름 바꾸기', k: '두 번', a: function () { var f = flowOf(name); if (f) edit(label(f)); }}, '-',
                 {l: '줄만 걷기', k: 'Ctrl+⌫', a: function () { dissolve(name); }},
                 {l: '줄 화면 모두 삭제', k: 'Del', a: function () { remove(name); }}];
    menu = document.createElement('div'); menu.className = 'hd-rmenu'; menu.setAttribute('role', 'menu');
    menu.innerHTML = '<div class="cmh"></div>' + items.map(function (it, i) {
      return it === '-' ? '<hr>' : '<button type="button" role="menuitem" data-i="' + i + '"><span></span><kbd></kbd></button>';
    }).join('');
    $('.cmh', menu).textContent = name;
    items.forEach(function (it, i) { if (it === '-') return; var b = $('[data-i="' + i + '"]', menu); $('span', b).textContent = it.l; $('kbd', b).textContent = it.k; });
    document.body.appendChild(menu);
    menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, x)) + 'px';
    menu.style.top = Math.max(8, Math.min(innerHeight - menu.offsetHeight - 8, y)) + 'px';
    menu.addEventListener('click', function (e) { var b = e.target.closest('[data-i]'); if (!b) return; var it = items[+b.dataset.i]; closeMenu(); it.a(); });
    menu.addEventListener('keydown', function (e) { e.stopPropagation(); if (e.key === 'Escape') closeMenu(); });
    document.addEventListener('pointerdown', outside, true);
    var first = $('button', menu); if (first) first.focus({preventScroll: true});
  }

  function headOf(e) { var g = e.target && e.target.closest ? e.target.closest('.glabel') : null; return g && g.parentNode && g.parentNode.parentNode === rowsEl ? g : null; }
  rowsEl.addEventListener('click', function (e) {    // 셸의 판 누르기(capture)가 고르기를 푼 뒤 — 그 줄 카드 모두 고르기
    var g = headOf(e); if (!g || editing === g || e.ctrlKey || e.metaKey) return;
    select(g.textContent);
  });
  rowsEl.addEventListener('dblclick', function (e) { var g = headOf(e); if (!g) return; e.preventDefault(); edit(g); });
  rowsEl.addEventListener('pointerdown', function (e) { if (editing && headOf(e) === editing) e.stopPropagation(); });   // 고치는 중에는 판을 끌지 않는다
  rowsEl.addEventListener('contextmenu', function (e) {
    var g = headOf(e); if (!g || editing === g) return;
    e.preventDefault(); e.stopPropagation();
    select(g.textContent); openMenu(e.clientX, e.clientY, g.textContent);
  });
  document.addEventListener('click', function (e) { if (!headOf(e)) stillOn(); });
  addEventListener('keydown', function (e) {        // 고른 줄 + Del/Backspace = 화면 모두 지우기 · Ctrl+Backspace = 줄만 걷기(셸의 카드 지우기보다 먼저)
    if (e.key !== 'Delete' && e.key !== 'Backspace') return;
    var t = e.target, modal = document.getElementById('modal');
    if (editing || (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable))) return;
    if ((modal && !modal.hidden) || document.body.dataset.tab !== 'screens' || !stillOn()) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if ((e.ctrlKey || e.metaKey) && e.key === 'Backspace') dissolve(cur);
    else if (!e.ctrlKey && !e.metaKey && !e.altKey) remove(cur);
  }, true);
  document.addEventListener('hd-row-rename', function (e) { var d = e.detail || {}; if (typeof d.from === 'string') rename(d.from, d.to); });
  document.addEventListener('hd-row-dissolve', function (e) { var d = e.detail || {}; if (typeof d.name === 'string') dissolve(d.name); });
  return {selected: function () { return stillOn() ? cur : null; }, select: select, rename: rename, dissolve: dissolve};
}

HD.feature('rowHeads', {needs: ['rowsEl', '$', '$$', 'api', 'record', 'toast', 'selected', 'warn'], mount: heads});
})();
