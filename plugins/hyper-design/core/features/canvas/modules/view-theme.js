/* View — 테마 패널(조각 5, H10·H12·H14). 상태 규칙은 modules/theme.js(Model), 여기는 그리기·누르기와 저장.
   목록: 색 점 + 이름, 기본 테마는 자물쇠(복제만), 내 테마는 마우스를 올리면 이름 바꾸기·복제·삭제(되돌리기 됨).
   '+ 새 테마' = 지금 테마 복제. 내 테마를 고르면 색 네 칸(주 색·글자·바탕·강조): 색 고르기 + HEX, 판의 화면에 바로, 글자 대비 4.5:1 미만 경고.
   HD.viewTheme.mount(ctx) → {render()}
   ctx = {$, esc, root, bases: [{slug, name, brand}], apply(slug, vars), readColors() → {brand, text, bg, accent}(지금 판 색),
          record({label, undo, redo}), getItem, setItem} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var I = {
  lock: '<svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/></svg>',
  ren: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/></svg>',
  dup: '<svg viewBox="0 0 24 24"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 00-1-1H5a1 1 0 00-1 1v10a1 1 0 001 1h3"/></svg>',
  del: '<svg viewBox="0 0 24 24"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>'
};

function mount(ctx) {
  var T = HD.theme, $ = ctx.$, esc = ctx.esc, root = ctx.root, bases = ctx.bases || [];
  var st = T.load(ctx.getItem);
  root.innerHTML = '<div id="thList" role="listbox" aria-label="테마"></div>' +
    '<button type="button" id="thNew" class="th-new">+ 새 테마</button>' +
    '<div id="thEdit" hidden>' + Object.keys(T.ROLES).map(function (r) {
      return '<label class="th-c" data-role="' + r + '"><span>' + T.LABEL[r] + '</span><input type="color" class="th-col" aria-label="' + T.LABEL[r] + ' 색 고르기">' +
        '<input class="th-hex" maxlength="7" spellcheck="false" aria-label="' + T.LABEL[r] + ' HEX"></label>';
    }).join('') + '<p id="thWarn" role="status"></p></div>' +
    '<p id="thNote" class="dkp-empty" hidden>기본 테마는 잠겨 있어요 — 복제해서 고쳐요</p>';
  var list = $('#thList'), edit = $('#thEdit'), warn = $('#thWarn');

  function base(slug) { return bases.filter(function (b) { return b.slug === slug; })[0] || bases[0] || {slug: ''}; }
  function mineOf(id) { return st.mine.filter(function (t) { return t.id === id; })[0] || null; }
  function curId() { return mineOf(st.cur) || bases.some(function (b) { return b.slug === st.cur; }) ? st.cur : (bases[0] || {}).slug; }
  function applyCur() {
    var t = mineOf(curId());
    if (t) ctx.apply(base(t.base).slug, T.vars(t)); else ctx.apply(curId(), {});
  }
  function commit(s, quiet) { st = s; T.save(st, ctx.setItem); render(); if (!quiet) applyCur(); }
  function dispatch(a, quiet) { var n = T.reduce(st, a); if (n !== st) commit(n, quiet); return n; }

  function row(id, name, dot, mine, on) {
    return '<div class="th-r' + (on ? ' on' : '') + '" data-th="' + esc(id) + '" role="option" aria-selected="' + on + '">' +
      '<i class="th-dot" style="--d:' + esc(dot) + '"></i><span class="th-name">' + esc(name) + '</span>' +
      (mine ? '' : '<span class="th-lock" title="기본 테마 — 복제해서 고쳐요">' + I.lock + '</span>') +
      '<span class="th-acts">' + (mine ? '<button type="button" data-act="ren" title="이름 바꾸기">' + I.ren + '</button>' : '') +
      '<button type="button" data-act="dup" title="복제">' + I.dup + '</button>' +
      (mine ? '<button type="button" data-act="del" title="삭제">' + I.del + '</button>' : '') + '</span></div>';
  }
  function render() {
    var cur = curId();
    list.innerHTML = bases.map(function (b) { return row(b.slug, b.name, b.brand, false, b.slug === cur); }).join('') +
      st.mine.map(function (t) { return row(t.id, t.name, t.c.brand, true, t.id === cur); }).join('');
    var t = mineOf(cur);
    edit.hidden = !t; $('#thNote').hidden = !!t;
    if (!t) return;
    Object.keys(T.ROLES).forEach(function (r) {
      var lab = edit.querySelector('[data-role="' + r + '"]');
      lab.querySelector('.th-col').value = t.c[r].toLowerCase();
      if (document.activeElement !== lab.querySelector('.th-hex')) lab.querySelector('.th-hex').value = t.c[r];
    });
    var k = T.contrast(t.c.text, t.c.bg);
    warn.textContent = k < 4.5 ? '글자 대비 ' + k.toFixed(1) + ':1 — 4.5:1 미만이라 읽기 어려워요' : '';
  }

  function copyOf(id) {
    var t = mineOf(id), b = t ? null : base(id);
    var nid = 'my-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
    dispatch({type: 'copy', id: nid, name: (t ? t.name : b.name) + ' 복사', base: t ? t.base : b.slug, c: t ? t.c : ctx.readColors()});
  }
  function remove(id) {
    var at = -1; st.mine.forEach(function (t, i) { if (t.id === id) at = i; });
    var item = mineOf(id), wasCur = st.cur === id; if (!item) return;
    var gone = function () { dispatch({type: 'remove', id: id, fallback: item.base}); };
    gone();
    ctx.record({label: '테마 삭제', undo: function () { dispatch({type: 'restore', item: item, at: at}); if (wasCur) dispatch({type: 'pick', id: id}); }, redo: gone});
  }
  function rename(r) {
    var id = r.dataset.th, t = mineOf(id), nm = r.querySelector('.th-name'); if (!t || r.querySelector('.th-in')) return;
    var inp = document.createElement('input'); inp.className = 'th-in'; inp.value = t.name; nm.replaceWith(inp); inp.focus(); inp.select();
    var done = false, fin = function (ok) { if (done) return; done = true; if (ok) dispatch({type: 'rename', id: id, name: inp.value}, true); render(); };
    inp.addEventListener('keydown', function (e) { e.stopPropagation(); if (e.key === 'Enter') fin(true); else if (e.key === 'Escape') fin(false); });
    inp.addEventListener('blur', function () { fin(true); });
  }
  function setColor(role, h) {
    var t = mineOf(curId()), v = T.hex(h); if (!t || (v && t.c[role] === v)) return;   // 같은 값이면 다시 그리지 않는다(초점이 빠질 때의 change 가 누르던 버튼을 바꿔 치우지 않게)
    if (!v) { render(); return; }                       // 잘못된 HEX = 칸을 원래 값으로
    var id = t.id, old = t.c[role];
    dispatch({type: 'color', id: id, role: role, hex: v});
    ctx.record({label: '테마 색', undo: function () { dispatch({type: 'color', id: id, role: role, hex: old}); },
                redo: function () { dispatch({type: 'color', id: id, role: role, hex: v}); }});
  }

  list.addEventListener('click', function (e) {
    var r = e.target.closest('[data-th]'); if (!r || e.target.closest('.th-in')) return;
    var b = e.target.closest('button[data-act]'), id = r.dataset.th;
    if (!b) { dispatch({type: 'pick', id: id}); return; }
    if (b.dataset.act === 'dup') copyOf(id);
    else if (b.dataset.act === 'del') remove(id);
    else if (b.dataset.act === 'ren') rename(r);
  });
  $('#thNew').addEventListener('click', function () { copyOf(curId()); });
  edit.addEventListener('input', function (e) {           // 색 고르기 판: 끄는 동안 판에 바로(저장·되돌리기는 change 에서)
    if (!e.target.classList.contains('th-col')) return;
    var t = mineOf(curId()), role = e.target.closest('[data-role]').dataset.role; if (!t) return;
    var v = {}; v[T.ROLES[role]] = T.hex(e.target.value); ctx.apply(base(t.base).slug, Object.assign(T.vars(t), v));
  });
  edit.addEventListener('change', function (e) {
    var lab = e.target.closest('[data-role]'); if (lab) setColor(lab.dataset.role, e.target.value);
  });
  edit.addEventListener('keydown', function (e) {
    e.stopPropagation();                                  // 판 단축키와 겹치지 않게
    if (e.key === 'Enter' && e.target.classList.contains('th-hex')) { e.preventDefault(); setColor(e.target.closest('[data-role]').dataset.role, e.target.value); }
  });

  render(); applyCur();
  return {render: render};
}

HD.viewTheme = {mount: mount};
})();
