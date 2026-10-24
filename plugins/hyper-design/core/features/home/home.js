/* View — 홈 화면: 사이드바 구역 · 찾기 · 카드 격자(누르기 = 고르기, 두 번/Enter = 열기) · 우클릭 메뉴 · 대화상자 · 토스트. 규칙은 HDHomeModel, 상태는 이 파일의 S 하나 */
(function () {
  'use strict';
  var M = window.HDHomeModel;
  var $ = function (s) { return document.querySelector(s); };
  var SEC_KEY = 'hd-home-section';
  var TOKEN = new URLSearchParams(location.search).get('hd') || window.__hdToken || '';
  // S: rows = 받은 줄 · sec = 구역 · q = 찾기 · sel = 고른 칸 열쇠('new' | 이름) · loading · renaming = 이름 바꾸는 줄 이름
  var S = {rows: [], sec: 'recent', q: '', sel: null, loading: true, renaming: null, failed: false};

  try { S.sec = M.validSection(localStorage.getItem(SEC_KEY)); } catch (e) { /* 저장소를 못 읽으면 기본 구역 */ }

  var ICON = {
    star: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 2.8l2.2 4.6 5 .6-3.7 3.4 1 5-4.5-2.5-4.5 2.5 1-5L2.8 8l5-.6z"/></svg>',
    plus: '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v12M4 10h12"/></svg>',
    canvas: '<svg viewBox="0 0 40 26" aria-hidden="true"><rect x="2" y="3" width="10" height="20" rx="2"/><rect x="15" y="3" width="10" height="20" rx="2"/><rect x="28" y="3" width="10" height="20" rx="2"/><path d="M12 13h3M25 13h3"/></svg>'
  };

  // ---- API ----
  function api(method, path, body) {
    var opt = {method: method, headers: {'X-HD-Token': TOKEN}};
    if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    return fetch(path, opt).then(function (res) {
      return res.text().then(function (txt) {
        var data = null;
        try { data = txt ? JSON.parse(txt) : null; } catch (e) { data = null; console.warn('[hd] home: JSON 이 아닌 답', path, res.status); }
        if (!res.ok || (data && data.error)) {
          var msg = (data && data.error) || (res.status === 403 ? '토큰이 맞지 않아요 — hd home 으로 다시 여세요' : '요청이 실패했어요 (' + res.status + ')');
          var err = new Error(msg); err.status = res.status; throw err;
        }
        return data;
      });
    }, function () { throw new Error('홈 서버에 닿지 않아요 — hd home 으로 다시 여세요'); });
  }

  // ---- 토스트 ----
  function toast(text, opts) {
    opts = opts || {};
    var el = document.createElement('div');
    el.className = 'toast' + (opts.error ? ' err' : '');
    el.setAttribute('role', opts.error ? 'alert' : 'status');
    var sp = document.createElement('span'); sp.textContent = text; el.appendChild(sp);
    if (opts.action) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = opts.action.label;
      b.addEventListener('click', function () { el.remove(); opts.action.run(); });
      el.appendChild(b);
    }
    $('#toasts').appendChild(el);
    setTimeout(function () { el.remove(); }, opts.action ? 8000 : 4000);
    return el;
  }
  function fail(what) { return function (e) { console.error('[hd] home:', what, e); toast(e.message || String(e), {error: true}); }; }

  // ---- 대화상자 (이름 묻기 · 확인) ----
  function dialog(o) {
    return new Promise(function (resolve) {
      var box = $('#dlg'), inp = $('#dlgIn'), yes = $('#dlgYes');
      $('#dlgTitle').textContent = o.title; $('#dlgText').textContent = o.text || '';
      inp.hidden = o.value === undefined; inp.value = o.value || '';
      yes.textContent = o.ok || '확인'; yes.classList.toggle('danger', !!o.danger);
      box.hidden = false;
      var prev = document.activeElement;
      (inp.hidden ? yes : inp).focus(); if (!inp.hidden) inp.select();
      function done(v) {
        box.hidden = true; $('#dlgBox').onsubmit = null; $('#dlgNo').onclick = null; box.onkeydown = null; box.onmousedown = null;
        if (prev && prev.focus) prev.focus();
        resolve(v);
      }
      $('#dlgBox').onsubmit = function (e) { e.preventDefault(); done(inp.hidden ? true : inp.value); };
      $('#dlgNo').onclick = function () { done(null); };
      box.onkeydown = function (e) { if (e.key === 'Escape') { e.stopPropagation(); done(null); } };
      box.onmousedown = function (e) { if (e.target === box) done(null); };
    });
  }

  // ---- 그리기 ----
  function visible() { return M.view(S.rows, S.sec, S.q); }
  function keys() { var v = visible().map(function (r) { return r.name; }); return S.sec === 'trash' ? v : ['new'].concat(v); }
  function byName(n) { for (var i = 0; i < S.rows.length; i++) if (S.rows[i].name === n) return S.rows[i]; return null; }

  function renderNav() {
    document.querySelectorAll('.nv[data-sec]').forEach(function (b) { b.setAttribute('aria-selected', String(b.dataset.sec === S.sec)); });
    $('#secTitle').textContent = M.LABEL[S.sec];
    document.title = M.LABEL[S.sec] + ' — Hyper Design';
  }

  function skeleton() {
    var g = $('#grid'); g.innerHTML = ''; g.setAttribute('aria-busy', 'true');
    for (var i = 0; i < 8; i++) {
      var c = document.createElement('div'); c.className = 'card sk';
      c.innerHTML = '<div class="th"></div><div class="nm"></div><div class="mt"></div>';
      g.appendChild(c);
    }
    $('#empty').hidden = true;
  }

  function newCard() {
    var c = document.createElement('div');
    c.className = 'card new'; c.dataset.key = 'new'; c.setAttribute('role', 'option'); c.tabIndex = -1;
    c.innerHTML = '<div class="th"><span class="plus">' + ICON.plus + '새 프로젝트</span></div><div class="nm">새 프로젝트</div><div class="mt">빈 캔버스로 시작</div>';
    return c;
  }

  function card(r, now) {
    var c = document.createElement('div');
    c.className = 'card' + (r.state === 'missing' ? ' missing' : '');
    c.dataset.key = r.name; c.dataset.state = r.state; c.setAttribute('role', 'option'); c.tabIndex = -1;
    var th = document.createElement('div'); th.className = 'th';
    if (r.state === 'missing') th.innerHTML = '<span class="gone">폴더 없음</span>';
    else if (r.thumb) {
      var img = document.createElement('img'); img.alt = ''; img.loading = 'lazy'; img.draggable = false; img.src = r.thumb;
      img.addEventListener('error', function () { img.replaceWith(placeholder()); });   // 썸네일이 아직 없거나 깨짐 → 기본 그림(오류 아님)
      th.appendChild(img);
    } else th.appendChild(placeholder());
    c.appendChild(th);
    if (S.renaming === r.name) {
      var inp = document.createElement('input'); inp.className = 'ren'; inp.value = r.title; inp.setAttribute('aria-label', '새 이름');
      c.appendChild(inp);
    } else {
      var nm = document.createElement('div'); nm.className = 'nm'; nm.textContent = r.title; nm.title = r.title; c.appendChild(nm);
    }
    var mt = document.createElement('div'); mt.className = 'mt';
    if (r.state === 'running') { var d = document.createElement('span'); d.className = 'dot'; d.title = '열려 있음'; mt.appendChild(d); }
    var when = S.sec === 'trash' ? M.relTime(r.trashed, now) : M.relTime(r.last_opened || r.created, now);
    mt.appendChild(document.createTextNode(r.state === 'missing' ? '폴더 없음' : (S.sec === 'trash' ? (when ? when + ' 휴지통으로' : '휴지통') : (when || '열지 않음'))));
    mt.title = r.out;
    c.appendChild(mt);
    if (S.sec !== 'trash') {
      var st = document.createElement('button'); st.type = 'button'; st.className = 'star'; st.tabIndex = -1;
      st.setAttribute('aria-pressed', String(r.starred)); st.title = r.starred ? '별표 빼기' : '별표';
      st.setAttribute('aria-label', st.title); st.innerHTML = ICON.star;
      c.appendChild(st);
    }
    return c;
  }
  function placeholder() { var p = document.createElement('div'); p.className = 'ph'; p.innerHTML = ICON.canvas; return p; }

  function render() {
    renderNav();
    if (S.loading) { skeleton(); return; }
    var g = $('#grid'), now = Date.now(), list = visible();
    g.removeAttribute('aria-busy'); g.innerHTML = '';
    if (S.failed) { $('#empty').hidden = true; return; }
    if (S.sec !== 'trash') g.appendChild(newCard());
    list.forEach(function (r) { g.appendChild(card(r, now)); });
    if (S.sel && keys().indexOf(S.sel) < 0) S.sel = null;
    markSel(false);
    var em = $('#empty');
    em.hidden = list.length > 0; em.textContent = list.length ? '' : M.empty(S.sec, S.q);
    if (S.renaming) {
      var inp = g.querySelector('.ren');
      if (inp) { inp.focus(); inp.select(); wireRename(inp, S.renaming); }
    }
  }

  function cell(key) { return key ? document.querySelector('#grid .card[data-key="' + CSS.escape(key) + '"]') : null; }
  function markSel(focus) {
    document.querySelectorAll('#grid .card[data-key]').forEach(function (c) { c.setAttribute('aria-selected', String(c.dataset.key === S.sel)); });
    var c = cell(S.sel);
    if (c && focus) { c.focus({preventScroll: true}); c.scrollIntoView({block: 'nearest'}); }
  }
  function select(key, focus) { S.sel = key; markSel(focus !== false); }

  function cols() {
    var t = getComputedStyle($('#grid')).gridTemplateColumns;
    return t && t !== 'none' ? t.split(' ').filter(Boolean).length : 1;
  }

  // ---- 동작 ----
  function load(keepSel) {
    S.loading = true; render();
    return api('GET', '/api/projects').then(function (body) {
      var n = M.normalize(body);
      if (n.bad) console.warn('[hd] home: 모양이 틀린 프로젝트 줄 ' + n.bad + '개를 뺐어요');
      S.rows = n.rows; S.loading = false; S.failed = false; $('#banner').hidden = true;
      if (!keepSel) S.sel = null;
      render();
    }, function (e) {
      console.error('[hd] home: 목록을 못 읽음', e);
      S.loading = false; S.failed = true; render();
      var b = $('#banner'); b.hidden = false; b.innerHTML = '';
      var sp = document.createElement('span'); sp.textContent = '프로젝트 목록을 못 읽었어요 — ' + e.message; b.appendChild(sp);
      var rb = document.createElement('button'); rb.type = 'button'; rb.textContent = '다시 시도'; rb.onclick = function () { load(); }; b.appendChild(rb);
    });
  }

  function setSection(sec) {
    S.sec = M.validSection(sec); S.sel = null; S.renaming = null;
    try { localStorage.setItem(SEC_KEY, S.sec); } catch (e) { /* 저장소에 못 쓰면 이번 창에서만 기억 */ }
    render();
  }

  function replaceRow(row) {
    if (!row || typeof row !== 'object' || !row.name) { console.warn('[hd] home: 답에 row 가 없어 목록을 다시 읽어요'); return load(true); }
    var r = M.row(row);
    S.rows = S.rows.map(function (x) { return x.name === r.name ? r : x; });
    render();
  }
  function patch(name, fields, okText, undo) {
    return api('POST', '/api/project', Object.assign({name: name}, fields)).then(function (d) {
      replaceRow(d && d.row);
      if (okText) toast(okText, undo ? {action: {label: '되돌리기', run: function () { patch(name, undo); }}} : {});
    }, fail('프로젝트 바꾸기'));
  }

  function navigate(url) { window.location.assign(url); }

  function open(name) {
    var r = byName(name);
    if (!r) return;
    if (r.state === 'missing') {
      toast('‘' + r.title + '’ 폴더가 없어요 — 옮겼거나 지웠어요', {error: true, action: {label: '목록에서 빼기', run: function () { removeMissing(r); }}});
      return;
    }
    var c = cell(name); if (c) c.classList.add('busy');
    api('POST', '/api/open', {name: name}).then(function (d) {
      if (!d || !d.url) throw new Error('열 주소를 받지 못했어요');
      navigate(d.url);
    }).catch(function (e) { if (c) c.classList.remove('busy'); fail('열기')(e); });
  }

  function removeMissing(r) {   // 없는 폴더 = 휴지통으로 넣고 바로 목록에서 뺀다(파일은 원래 없음)
    api('POST', '/api/project', {name: r.name, trashed: true})
      .then(function () { return api('POST', '/api/forget', {name: r.name}); })
      .then(function () { S.rows = S.rows.filter(function (x) { return x.name !== r.name; }); render(); toast('목록에서 뺐어요'); }, fail('목록에서 빼기'));
  }

  function createNew() {
    dialog({title: '새 프로젝트', text: '빈 캔버스를 만들어 열어요.', value: M.newTitle(S.rows), ok: '만들기'}).then(function (v) {
      if (v === null) return;
      var title = String(v).trim();
      api('POST', '/api/new', title ? {title: title} : {}).then(function (d) {
        if (!d || !d.url) throw new Error('새 프로젝트 주소를 받지 못했어요');
        navigate(d.url);
      }).catch(fail('새 프로젝트'));
    });
  }

  function startRename(name) {
    var r = byName(name);
    if (!r || S.sec === 'trash') return;
    S.sel = name; S.renaming = name; render();
  }
  function wireRename(inp, name) {
    var done = false;
    function finish(commit) {
      if (done) return; done = true;
      var r = byName(name), v = commit && r ? M.renameValue(inp.value, r.title) : null;
      S.renaming = null; render(); select(name);
      if (v) patch(name, {title: v});
    }
    inp.addEventListener('keydown', function (e) {
      e.stopPropagation();
      if (e.key === 'Enter') { e.preventDefault(); finish(true); } else if (e.key === 'Escape') { e.preventDefault(); finish(false); }
    });
    inp.addEventListener('blur', function () { finish(true); });
    inp.addEventListener('dblclick', function (e) { e.stopPropagation(); });
  }

  function trash(name) {
    var r = byName(name); if (!r || r.trashed) return;
    var ks = keys(), i = ks.indexOf(name);
    patch(name, {trashed: true}, '‘' + r.title + '’을(를) 휴지통으로 옮겼어요', {trashed: false}).then(function () {
      var nk = keys(); S.sel = nk.length ? nk[Math.min(i, nk.length - 1)] : null; markSel(true);
    });
  }
  function forget(name) {
    var r = byName(name); if (!r) return;
    dialog({title: '목록에서 완전히 빼기', text: '‘' + r.title + '’을(를) 홈 목록에서 뺍니다. 폴더의 파일은 지우지 않아요.', ok: '빼기', danger: true}).then(function (ok) {
      if (!ok) return;
      api('POST', '/api/forget', {name: name}).then(function () {
        S.rows = S.rows.filter(function (x) { return x.name !== name; }); render(); toast('목록에서 뺐어요');
      }, fail('목록에서 빼기'));
    });
  }
  function reveal(name) { api('POST', '/api/reveal', {name: name}).catch(fail('폴더 열기')); }
  function star(name) { var r = byName(name); if (r) patch(name, {starred: !r.starred}); }

  function pickFolder() {
    api('POST', '/api/pick-folder', {}).then(function (d) {
      if (!d || d.cancel) return;
      if (!d.name) throw new Error('추가한 프로젝트 이름을 받지 못했어요');
      return load(true).then(function () { S.sec === 'trash' && setSection('all'); select(d.name); toast('프로젝트를 추가했어요'); });
    }).catch(fail('폴더 열기'));
  }

  var ACT = {open: open, rename: startRename, star: star, reveal: reveal, trash: trash, restore: function (n) {
    var r = byName(n); patch(n, {trashed: false}, r ? '‘' + r.title + '’을(를) 되돌렸어요' : null);
  }, forget: forget};

  // ---- 우클릭 메뉴 ----
  function showMenu(name, x, y) {
    var items = M.menu(byName(name), S.sec), m = $('#menu');
    m.innerHTML = '';
    items.forEach(function (it) {
      if (it === '-') { m.appendChild(document.createElement('hr')); return; }
      var b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'menuitem');
      b.dataset.id = it.id; b.textContent = it.label; b.disabled = !!it.disabled;
      b.addEventListener('click', function () { hideMenu(); ACT[it.id](name); });
      m.appendChild(b);
    });
    m.hidden = false;
    var w = m.offsetWidth, h = m.offsetHeight;
    m.style.left = Math.min(x, innerWidth - w - 8) + 'px'; m.style.top = Math.min(y, innerHeight - h - 8) + 'px';
    var first = m.querySelector('button:not(:disabled)'); if (first) first.focus();
  }
  function hideMenu() { $('#menu').hidden = true; }

  // ---- 입력 ----
  document.querySelectorAll('.nv[data-sec]').forEach(function (b) { b.addEventListener('click', function () { setSection(b.dataset.sec); }); });
  $('#pickFolder').addEventListener('click', pickFolder);
  $('#q').addEventListener('input', function (e) { S.q = e.target.value; render(); });
  $('#q').addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && S.q) { e.preventDefault(); e.target.value = ''; S.q = ''; render(); }
    else if (e.key === 'ArrowDown' || e.key === 'Enter') { e.preventDefault(); var k = keys(); if (k.length) select(S.sel || k[Math.min(1, k.length - 1)]); }
  });

  var grid = $('#grid');
  grid.addEventListener('click', function (e) {
    var c = e.target.closest('.card[data-key]'); hideMenu();
    if (!c) { if (e.target === grid) { S.sel = null; markSel(false); } return; }
    if (e.target.closest('.star')) { e.stopPropagation(); star(c.dataset.key); return; }
    if (c.dataset.key === 'new') { select('new'); createNew(); return; }
    select(c.dataset.key);
  });
  grid.addEventListener('dblclick', function (e) {
    var c = e.target.closest('.card[data-key]');
    if (!c || c.dataset.key === 'new' || e.target.closest('.star') || S.sec === 'trash') return;
    open(c.dataset.key);
  });
  grid.addEventListener('contextmenu', function (e) {
    var c = e.target.closest('.card[data-key]');
    if (!c || c.dataset.key === 'new') return;
    e.preventDefault(); select(c.dataset.key, false); showMenu(c.dataset.key, e.clientX, e.clientY);
  });
  document.addEventListener('mousedown', function (e) { if (!$('#menu').hidden && !e.target.closest('#menu')) hideMenu(); });

  $('#menu').addEventListener('keydown', function (e) {
    var bs = [].slice.call($('#menu').querySelectorAll('button:not(:disabled)')), i = bs.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault(); hideMenu(); markSel(true); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); bs[(i + 1) % bs.length].focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); bs[(i - 1 + bs.length) % bs.length].focus(); }
    e.stopPropagation();
  });

  document.addEventListener('keydown', function (e) {
    if (!$('#dlg').hidden || S.renaming) return;
    if ((e.ctrlKey || e.metaKey) && (e.key === 'f' || e.key === 'F')) { e.preventDefault(); $('#q').focus(); $('#q').select(); return; }
    if (e.target.closest && e.target.closest('input,textarea,#menu')) return;
    if (S.loading) return;
    var ks = keys(), i = ks.indexOf(S.sel);
    if (['ArrowRight', 'ArrowLeft', 'ArrowUp', 'ArrowDown', 'Home', 'End'].indexOf(e.key) >= 0) {
      e.preventDefault(); var j = M.move(i, e.key, ks.length, cols()); if (j >= 0) select(ks[j]); return;
    }
    if (!S.sel) return;
    if (e.key === 'Enter') { e.preventDefault(); if (S.sel === 'new') createNew(); else if (S.sec !== 'trash') open(S.sel); }
    else if (e.key === 'Delete' && S.sel !== 'new') { e.preventDefault(); if (S.sec === 'trash') forget(S.sel); else trash(S.sel); }
    else if (e.key === 'F2' && S.sel !== 'new') { e.preventDefault(); startRename(S.sel); }
    else if (e.key === 'ContextMenu' || (e.shiftKey && e.key === 'F10')) {
      if (S.sel === 'new') return;
      e.preventDefault(); var r = cell(S.sel).getBoundingClientRect(); showMenu(S.sel, r.left + 20, r.top + 20);
    }
  });

  if (!TOKEN) {
    var b = $('#banner'); b.hidden = false; b.textContent = '주소에 토큰이 없어요 — 터미널에서 hd home 으로 다시 여세요';
    console.error('[hd] home: ?hd= 토큰 없음');
  }
  window.HDHome = {state: S, reload: load};
  load();
})();
