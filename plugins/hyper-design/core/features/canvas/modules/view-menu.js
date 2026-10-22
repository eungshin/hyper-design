/* View — 위쪽 줄 메뉴 둘(조각 3, H1·H2·H4·H11).
   보기 메뉴 = 화면 아이콘 단추(#vbtn) 또는 배율 칩 `72% ▾`(#zoom)을 누르면 아이콘 줄: 전체 보기(0) · 100%(1) · 확대(+) · 축소(-) · 고른 화면에 맞추기,
   그 아래 창 나누기 줄(하나 · 좌우 2분할, 조각 6) + 동시 스크롤(나눴을 때만). 나누기 상태의 주인은 modules/viewport.js.
   창 메뉴 = [창 ▾](#wbtn): 도구 막대 · 판 아래 안내 · 패널마다 켜짐 체크(아이콘 + 짧은 이름 — H8 의 예외), 작업 영역 되돌리기, 패널 모두 숨기기(Tab).
   창 상태의 주인은 modules/dock.js(도크와 같은 곳) — 여기는 의도만 보낸다(ctx.dock.dispatch).
   HD.viewMenu.mount(ctx) → {sync(dockState)}
   ctx = {$, esc, view: {fit, z100, zin, zout, pick, canPick()}, split: {state(), dispatch(a)}, dock: {state(), dispatch(a)}, icons: {패널: svg}, typing(e), modalOpen()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ZOOM = [
  {z: 'fit', key: '0', name: '전체 보기', svg: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'},
  {z: '100', key: '1', name: '100%', svg: '<text x="12" y="16" text-anchor="middle" font-size="10" font-weight="700" stroke="none" fill="currentColor">1:1</text>'},
  {z: 'in', key: '+', name: '확대', svg: '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5M8.5 11h5M11 8.5v5"/>'},
  {z: 'out', key: '-', name: '축소', svg: '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5M8.5 11h5"/>'},
  {z: 'pick', key: '', name: '고른 화면에 맞추기', svg: '<rect x="7" y="7" width="10" height="10" rx="1.5"/><path d="M3 7V3h4M21 7V3h-4M3 17v4h4M21 17v4h-4"/>'}
];
var SPLIT = [
  {mode: 'one', name: '나누지 않기', svg: '<rect x="3" y="5" width="18" height="14" rx="2"/>'},
  {mode: 'lr', name: '좌우로 나누기', svg: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M12 5v14"/>'}
];
var SYNC = '<path d="M7 4v16M17 4v16"/><path d="M4 8l3-3 3 3M14 16l3 3 3-3"/>';
var CHROME = [
  {w: 'tools', name: '도구 막대', svg: '<rect x="4" y="3" width="6" height="18" rx="2"/><path d="M7 7v.01M7 11v.01M7 15v.01"/>'},
  {w: 'hint', name: '판 아래 안내', svg: '<rect x="3" y="15" width="18" height="5" rx="2"/><path d="M6 17.5h8"/>'}
];

function mount(ctx) {
  var $ = ctx.$, esc = ctx.esc, zbtn = $('#zoom'), vbtn = $('#vbtn'), wbtn = $('#wbtn'), vmenu = $('#vmenu'), wmenu = $('#wmenu');

  function svg(d) { return '<svg viewBox="0 0 24 24">' + d + '</svg>'; }
  function renderView() {
    var sp = ctx.split.state();
    vmenu.innerHTML = ZOOM.map(function (x) {
      var off = x.z === 'pick' && !ctx.view.canPick();
      return '<button type="button" class="vm-ib"' + (x.z === 'fit' ? ' id="fit"' : '') + ' data-z="' + x.z + '" role="menuitem"' + (off ? ' disabled' : '') +
        ' title="' + esc(x.name + (x.key ? ' (' + x.key + ')' : '')) + '" aria-label="' + esc(x.name) + '">' + svg(x.svg) + '</button>';
    }).join('') + '<hr>' + SPLIT.map(function (x) {
      return '<button type="button" class="vm-ib" data-split="' + x.mode + '" role="menuitemradio" aria-checked="' + (sp.split === x.mode) + '"' +
        ' title="' + esc(x.name) + '" aria-label="' + esc(x.name) + '">' + svg(x.svg) + '</button>';
    }).join('') + '<button type="button" class="vm-ib" data-act="sync" role="menuitemcheckbox" aria-checked="' + sp.sync + '"' + (sp.split === 'one' ? ' disabled' : '') +
      ' title="동시 스크롤" aria-label="동시 스크롤">' + svg(SYNC) + '</button>';
  }
  function row(id, name, icon, on) {
    return '<button type="button" class="wm-row" role="menuitemcheckbox" data-w="' + id + '" aria-checked="' + on + '">' +
      '<span class="wm-ck">' + (on ? '✓' : '') + '</span>' + icon + '<span>' + esc(name) + '</span></button>';
  }
  function renderWin() {
    var st = ctx.dock.state();
    wmenu.innerHTML = CHROME.map(function (c) { return row(c.w, c.name, svg(c.svg), st[c.w] !== false); }).join('') +
      '<hr>' + HD.dock.PANELS.map(function (p) { return row(p, HD.dock.LABEL[p], ctx.icons[p] || '', st.closed.indexOf(p) < 0); }).join('') +
      '<hr><button type="button" class="wm-row" role="menuitem" data-act="bare"><span class="wm-ck"></span><span>패널 모두 숨기기</span><kbd>Tab</kbd></button>' +
      '<button type="button" class="wm-row" role="menuitem" data-act="reset"><span class="wm-ck"></span><span>작업 영역 되돌리기</span></button>';
  }
  function place(menu, btn) {
    var r = btn.getBoundingClientRect();
    menu.style.top = (r.bottom + 6) + 'px';
    menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, r.right - menu.offsetWidth)) + 'px';
  }
  function open(menu, btn) {
    close();
    if (menu === vmenu) renderView(); else renderWin();
    menu.hidden = false; place(menu, btn); btn.setAttribute('aria-expanded', 'true');
  }
  function close() {
    [[vmenu, zbtn], [vmenu, vbtn], [wmenu, wbtn]].forEach(function (m) { m[0].hidden = true; m[1].setAttribute('aria-expanded', 'false'); });
  }
  function toggle(menu, btn) { if (menu.hidden) open(menu, btn); else close(); }
  zbtn.addEventListener('click', function () { toggle(vmenu, zbtn); });
  vbtn.addEventListener('click', function () { toggle(vmenu, vbtn); });
  wbtn.addEventListener('click', function () { toggle(wmenu, wbtn); });

  function zoom(k) { var f = {fit: ctx.view.fit, '100': ctx.view.z100, 'in': ctx.view.zin, out: ctx.view.zout, pick: ctx.view.pick}[k]; if (f) f(); }
  vmenu.addEventListener('click', function (e) {
    var s = e.target.closest('button[data-split], button[data-act="sync"]');
    if (s && !s.disabled) {                          // 나누기·동시 스크롤은 메뉴를 열어 둔 채 다시 그린다(켜짐 표시)
      if (s.dataset.split) ctx.split.dispatch({type: 'split', mode: s.dataset.split}); else ctx.split.dispatch({type: 'sync', on: !ctx.split.state().sync});
      renderView(); return;
    }
    var b = e.target.closest('button[data-z]'); if (!b || b.disabled) return;
    zoom(b.dataset.z); if (b.dataset.z !== 'in' && b.dataset.z !== 'out') close();   // 확대·축소는 여러 번 누르게 열어 둔다
  });
  function bare(on) { ctx.dock.dispatch({type: 'bare', on: on}); }
  wmenu.addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    var st = ctx.dock.state(), w = b.dataset.w;
    if (b.dataset.act === 'reset') ctx.dock.dispatch({type: 'reset'});
    else if (b.dataset.act === 'bare') { close(); bare(!st.bare); return; }
    else if (w === 'tools' || w === 'hint') ctx.dock.dispatch({type: 'chrome', part: w, on: st[w] === false});
    else if (w) ctx.dock.dispatch({type: st.closed.indexOf(w) < 0 ? 'close' : 'activate', id: w});
    renderWin();
  });
  document.addEventListener('pointerdown', function (e) {
    var t = e.target; if (!t.closest || t.closest('#vmenu, #wmenu, #zoom, #vbtn, #wbtn')) return;
    close();
  }, true);

  addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { close(); return; }
    if (ctx.typing(e) || e.ctrlKey || e.metaKey || e.altKey || ctx.modalOpen() || document.body.dataset.tab !== 'screens') return;
    if (e.key === 'Tab') { e.preventDefault(); bare(!ctx.dock.state().bare); return; }   // 포토샵처럼 — 판 위에서 Tab 은 초점 이동 대신 패널 숨기기
    var k = e.key === '=' ? '+' : e.key, x = ZOOM.filter(function (z) { return z.key && z.key !== '0' && z.key === k; })[0];   // 0 은 셸(전체 보기)
    if (x) { e.preventDefault(); zoom(x.z); }
  });

  // 창 상태가 바뀌면(도크 끌기·닫기 포함) 몸에 표시 + 열린 창 메뉴 다시
  function sync(st) {
    var b = document.body.classList;
    b.toggle('bare', !!st.bare);
    b.toggle('no-tools', st.tools === false);
    b.toggle('no-hint', st.hint === false);
    if (!wmenu.hidden) renderWin();
  }
  sync(ctx.dock.state());
  return {sync: sync, close: close};
}

HD.viewMenu = {mount: mount, ZOOM: ZOOM};
})();
