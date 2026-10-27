/* View — 표시 팝오버(R27 F02): 선 색·굵기·투명도·움직임 줄이기(#pShow)를 늘 열린 도크 패널 대신 위쪽 줄 단추 하나(#showbtn) 아래 팝오버로.
   패널 안 동작(선 색 고르기·슬라이더·체크)은 그 요소의 주인(셸 · view-line-ends · line-tone · view-motion)이 그대로 갖는다 — 여기는 #pShow 를 옮겨 붙이고 열고 닫기만.
   열기 = 단추 누르기 · 닫기 = 다시 누르기 · Esc · 팝오버 밖 누르기. 상태: 열림 하나(저장 안 함).
   #pShow 나 위쪽 줄 자리(#vbtn)가 없으면 붙지 않고 [hd] 경고(표시 없이).
   HD.feature('showPop', {needs: ['$']}) → {open(), close(), isOpen()} | {} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ICON = '<svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" stroke-width="1.2"/><path d="M4 7h7" stroke-width="3"/><path d="M4 12h11" stroke-width="2.2"/><path d="M4 17h5" stroke-width="3.6"/></svg>';
var CSS = '#showpop{position:fixed;z-index:26;width:300px;background:#fff;border:1px solid var(--ui-line,#e3e3df);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.14);overflow:visible}' +
  '#showpop[hidden]{display:none}' +
  '#showpop .sp-h{padding:10px 12px 0;font-size:12px;font-weight:600;color:#6b6b66}' +
  '#showpop #pShow{min-height:0;padding:8px 12px 10px}';

function mount(ctx) {
  var $ = ctx.$, panel = $('#pShow'), anchor = $('#vbtn');
  if (!panel || !anchor) { console.warn('[hd] 표시 팝오버: ' + (panel ? '위쪽 줄 자리(#vbtn)' : '표시 패널(#pShow)') + '가 없어요 — 표시 없이'); return {}; }
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'vbtn ib'; btn.id = 'showbtn'; btn.innerHTML = ICON;
  btn.title = '표시 — 선 색·굵기·투명도·움직임'; btn.setAttribute('aria-label', '표시');
  btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'showpop');
  anchor.parentNode.insertBefore(btn, anchor);
  var pop = document.createElement('div');
  pop.id = 'showpop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '표시'); pop.hidden = true;
  pop.innerHTML = '<div class="sp-h">표시</div>';
  pop.appendChild(panel);
  document.body.appendChild(pop);

  function place() {
    var r = btn.getBoundingClientRect();
    pop.style.top = (r.bottom + 6) + 'px';
    pop.style.left = Math.max(8, Math.min(innerWidth - pop.offsetWidth - 8, r.right - pop.offsetWidth)) + 'px';
  }
  function open() { pop.hidden = false; place(); btn.setAttribute('aria-expanded', 'true'); }
  function close() { if (pop.hidden) return; pop.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
  btn.addEventListener('click', function () { if (pop.hidden) open(); else close(); });
  document.addEventListener('pointerdown', function (e) {
    var t = e.target; if (pop.hidden || !t.closest || t.closest('#showpop, #showbtn')) return;
    close();
  }, true);
  addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  addEventListener('resize', function () { if (!pop.hidden) place(); });
  return {open: open, close: close, isOpen: function () { return !pop.hidden; }};
}

HD.feature('showPop', {needs: ['$'], mount: mount});
})();
