/* View — 위쪽 줄 메뉴 둘(조각 3, H1·H2·H4·H11).
   보기 메뉴 = 배율 칩 `72% ▾`(#zoom)을 누르면(같은 메뉴를 열던 화면 아이콘 단추는 뺐다 — U3 F11) 글자 줄(오른쪽 단축키, R27 F14): 전체 보기(0) · 100%(1) · 확대(+) · 축소(-) · 고른 화면에 맞추기,
   그 아래 창 나누기 줄(하나 · 좌우 2분할, 조각 6) + 동시 스크롤(나눴을 때만). 나누기 상태의 주인은 modules/viewport.js.
   창 메뉴 = [창 ▾](#wbtn): 도구 막대 · 대화창(R53 — 기록 + 입력창 창 하나 보이기) · 패널마다 켜짐 체크(대화는 패널 줄이 없다)(아이콘 + 짧은 이름 — H8 의 예외), 작업 영역 되돌리기, 패널 모두 숨기기(Tab).
   창 상태의 주인은 modules/dock.js(도크와 같은 곳) — 여기는 의도만 보낸다(ctx.dock.dispatch).
   대화창의 숨기기 단추는 document 에 의도 'hd-chrome' {part:'chat', on} 을 보내고 여기서 받는다(View 끼리 부르지 않음 — detail.done = true 로 받았음을 알린다).
   크게 보기가 열렸으면(R57) 배율 칩 메뉴 = 크게 보기 배율 줄만(MODAL_ZOOM: 폭 맞추기 Ctrl+0 · 100% · 확대 Ctrl+= · 축소 Ctrl+-) → ctx.modalView, 나누기 줄은 숨김.
   HD.viewMenu.mount(ctx) → {sync(dockState)}
   ctx = {$, esc, view: {fit, z100, zin, zout, pick, canPick()}, modalView?: {fit, z100, zin, zout}, split: {state(), dispatch(a)}, dock: {state(), dispatch(a), absent?() → 이 페이지에 없는 패널}, icons: {패널: svg}, typing(e), modalOpen()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ZOOM = [
  {z: 'fit', key: '0', name: '전체 보기'},
  {z: '100', key: '1', name: '100%'},
  {z: 'in', key: '+', name: '확대'},
  {z: 'out', key: '-', name: '축소'},
  {z: 'pick', key: '', name: '고른 화면에 맞추기'}
];
var MODAL_ZOOM = [                                   // 크게 보기(R57) — 키는 Ctrl/⌘ 와 함께(view-modal-zoom)
  {z: 'fit', key: 'Ctrl+0', name: '폭 맞추기'},
  {z: '100', key: '', name: '100%'},
  {z: 'in', key: 'Ctrl+=', name: '확대'},
  {z: 'out', key: 'Ctrl+-', name: '축소'}
];
var SPLIT = [
  {mode: 'one', name: '나누지 않기'},
  {mode: 'lr', name: '좌우로 나누기'}
];
var CHROME = [
  {w: 'tools', name: '도구 막대', svg: '<rect x="4" y="3" width="6" height="18" rx="2"/><path d="M7 7v.01M7 11v.01M7 15v.01"/>'},
  {w: 'chat', name: '대화창', svg: '<path d="M4 6a2 2 0 012-2h12a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 4v-4H6a2 2 0 01-2-2z"/>'}
];

function mount(ctx) {
  var $ = ctx.$, esc = ctx.esc, zbtn = $('#zoom'), wbtn = $('#wbtn'), vmenu = $('#vmenu'), wmenu = $('#wmenu');

  function svg(d) { return '<svg viewBox="0 0 24 24">' + d + '</svg>'; }
  function renderView() {                            // 글자 줄 + 오른쪽 단축키(R27 F14 — Figma 배율 메뉴처럼, 아이콘만인 줄 없음)
    var sp = ctx.split.state();
    var item = function (attrs, role, label, right, off, checked) {
      return '<button type="button" class="vm-row" ' + attrs + ' role="' + role + '"' + (checked == null ? '' : ' aria-checked="' + checked + '"') + (off ? ' disabled' : '') +
        '><span class="wm-ck">' + (checked ? '✓' : '') + '</span><span>' + esc(label) + '</span>' + (right ? '<kbd>' + esc(right) + '</kbd>' : '') + '</button>';
    };
    if (inModal()) {                                 // 크게 보기 배율(R57) — 판 메뉴의 나누기·고른 화면 줄은 판의 일
      vmenu.innerHTML = MODAL_ZOOM.map(function (x) { return item('data-z="' + x.z + '" data-modal="1"', 'menuitem', x.name, x.key); }).join('');
      return;
    }
    vmenu.innerHTML = ZOOM.map(function (x) {
      return item((x.z === 'fit' ? 'id="fit" ' : '') + 'data-z="' + x.z + '"', 'menuitem', x.name, x.key, x.z === 'pick' && !ctx.view.canPick());
    }).join('') + '<hr>' + SPLIT.map(function (x) {
      return item('data-split="' + x.mode + '"', 'menuitemradio', x.name, '', false, sp.split === x.mode);
    }).join('') + item('data-act="sync"', 'menuitemcheckbox', '동시 스크롤', '', sp.split === 'one', sp.sync);
  }
  function row(id, name, icon, on) {
    return '<button type="button" class="wm-row" role="menuitemcheckbox" data-w="' + id + '" aria-checked="' + on + '">' +
      '<span class="wm-ck">' + (on ? '✓' : '') + '</span>' + icon + '<span>' + esc(name) + '</span></button>';
  }
  function renderWin() {
    var st = ctx.dock.state();
    var gone = ctx.dock.absent ? ctx.dock.absent() : [];   // 이 페이지에 없는 패널(S3: 도우미 없이 연 캔버스의 대화)
    wmenu.innerHTML = CHROME.map(function (c) { return row(c.w, c.name, svg(c.svg), st[c.w] !== false); }).join('') +   // '대화창' = 대화 창 하나(R53 — 기록 + 입력창) 보이기
      '<hr>' + HD.dock.PANELS.filter(function (p) { return p !== 'talk'; }).map(function (p) {   // 대화는 패널 줄이 아니라 위 '대화창' 한 줄(R53)
        var r = row(p, HD.dock.LABEL[p], ctx.icons[p] || '', st.closed.indexOf(p) < 0 && gone.indexOf(p) < 0);
        return gone.indexOf(p) >= 0 ? r.replace('<button ', '<button disabled title="도우미로 열면 쓸 수 있어요" ') : r;
      }).join('') +
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
    [[vmenu, zbtn], [wmenu, wbtn]].forEach(function (m) { m[0].hidden = true; m[1].setAttribute('aria-expanded', 'false'); });
  }
  function toggle(menu, btn) { if (menu.hidden) open(menu, btn); else close(); }
  zbtn.addEventListener('click', function () { toggle(vmenu, zbtn); });
  wbtn.addEventListener('click', function () { toggle(wmenu, wbtn); });

  function inModal() { return !!(ctx.modalView && ctx.modalOpen && ctx.modalOpen()); }
  function zoom(k) {
    var v = inModal() ? ctx.modalView : ctx.view, f = {fit: v.fit, '100': v.z100, 'in': v.zin, out: v.zout, pick: v.pick}[k];
    if (f) f();
  }
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
    else if (w === 'tools' || w === 'chat') ctx.dock.dispatch({type: 'chrome', part: w, on: st[w] === false});
    else if (w) ctx.dock.dispatch({type: st.closed.indexOf(w) < 0 ? 'close' : 'activate', id: w});
    renderWin();
  });
  document.addEventListener('pointerdown', function (e) {
    var t = e.target; if (!t.closest || t.closest('#vmenu, #wmenu, #zoom, #wbtn')) return;
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
    b.toggle('no-chat', st.chat === false);
    if (!wmenu.hidden) renderWin();
  }
  document.addEventListener('hd-chrome', function (e) {   // 대화창 숨기기 단추 등 — 창 상태 의도
    var d = e.detail || {};
    if (d.part !== 'chat' && d.part !== 'tools') return;
    ctx.dock.dispatch({type: 'chrome', part: d.part, on: !!d.on}); d.done = true;
  });
  sync(ctx.dock.state());
  return {sync: sync, close: close};
}

HD.viewMenu = {mount: mount, ZOOM: ZOOM, MODAL_ZOOM: MODAL_ZOOM};
})();
