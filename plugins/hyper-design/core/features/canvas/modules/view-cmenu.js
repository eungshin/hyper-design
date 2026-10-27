/* View — 우클릭 메뉴(#cmenu)와 그 옆 목록(#cmsub): 그리기·자리·키(↑↓ 돌기 · → 옆 목록 · ← / Esc 옆 목록 닫기)·밖 누르기·창 크기 바뀜에 닫기.
   항목을 고르는 일(무엇을 넣을지)은 셸, 이 모듈은 받은 항목을 보이고 누르면 act() 를 부른다. Esc 차례는 셸이 isOpen()/close() 로 정한다.
   items: [{label, key?, id?, act()} | {label, id?, sub(cb)}(옆 목록 — cb([{label, id?, title?, act}] | null = 찾는 중), 옆 목록 id 도 data-act)] · '-' = 구분선 · {head} = 소제목
   id = 항목의 뜻(data-act — 테스트·검사는 글이 아니라 이것으로 고른다, R17) · key = 실제로 듣는 단축키 힌트(오른쪽 맞춤 kbd)
   HD.viewCmenu.mount(ctx) → {open(x, y, head, items) → 토큰, isCurrent(토큰) → 그 열기가 아직 떠 있나, isOpen(), close()}
   ctx = {$, $$, esc, menu: #cmenu, sub: #cmsub} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, cmenu = ctx.menu, cmsub = ctx.sub;
  var items = [], tok = null, subItems = [], subTok = null, subFrom = null;

  function cycle(e, box) {                         // ↑↓ = 그 목록 안 단추 사이를 돈다(끝에서 처음으로)
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    var bs = $$('button', box), i = bs.indexOf(document.activeElement);
    bs[(i + (e.key === 'ArrowDown' ? 1 : bs.length - 1)) % bs.length].focus();
  }
  function closeSub() {
    if (cmsub.hidden) return;
    cmsub.hidden = true; subTok = null;
    $$('button[aria-expanded="true"]', cmenu).forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
  }
  function close() { closeSub(); if (cmenu.hidden) return; cmenu.hidden = true; cmenu.classList.remove('is-open'); }
  function open(x, y, head, list) {
    closeSub();
    cmenu.innerHTML = (head ? '<div class="cmh">' + esc(head) + '</div>' : '') + list.map(function (it, i) {
      return it === '-' ? '<hr>' : it.head ? '<div class="cmh sub">' + esc(it.head) + '</div>' :
        '<button type="button" role="menuitem" data-i="' + i + '"' + (it.id ? ' data-act="' + esc(it.id) + '"' : '') + (it.sub ? ' aria-haspopup="menu" aria-expanded="false"' : '') + '>' + esc(it.label) +
        (it.key ? '<kbd>' + esc(it.key) + '</kbd>' : '') + (it.sub ? '<span class="sub" aria-hidden="true">▸</span>' : '') + '</button>';
    }).join('');
    items = list;
    cmenu.hidden = false; cmenu.classList.add('is-open');
    cmenu.style.left = Math.max(8, Math.min(innerWidth - cmenu.offsetWidth - 8, x)) + 'px';
    cmenu.style.top = Math.max(8, Math.min(innerHeight - cmenu.offsetHeight - 8, y)) + 'px';
    var first = $('button', cmenu); if (first) first.focus({preventScroll: true});
    return (tok = {});
  }
  // 옆 목록(51-3 '고르기 ▸', Figma F6 Select layer) — 올리거나 누르거나 → 키로 연다. 목록은 it.sub(cb) 가 늦게 줄 수 있다(화면에 조상 묻기)
  function openSub(b, it, focus) {
    if (!cmsub.hidden && subFrom === b) { if (focus) { var f0 = $('button', cmsub); if (f0) f0.focus(); } return; }
    var t = subTok = {}; subFrom = b; b.setAttribute('aria-expanded', 'true');
    var put = function (list) {
      if (subTok !== t || cmenu.hidden) return;
      subItems = list || [];
      cmsub.innerHTML = list == null ? '<div class="cmh">찾는 중…</div>' : list.length ? list.map(function (x, i) {
        return '<button type="button" role="menuitem" data-j="' + i + '"' + (x.id ? ' data-act="' + esc(x.id) + '"' : '') + (x.title ? ' title="' + esc(x.title) + '"' : '') + '>' + esc(x.label) + '</button>'; }).join('') : '<div class="cmh">고를 요소가 없어요</div>';
      cmsub.hidden = false;
      var r = b.getBoundingClientRect(), w = cmsub.offsetWidth, x = r.right + 2 + w > innerWidth - 8 ? r.left - w - 2 : r.right + 2;
      cmsub.style.left = Math.max(8, x) + 'px'; cmsub.style.top = Math.max(8, Math.min(innerHeight - cmsub.offsetHeight - 8, r.top - 5)) + 'px';
      if (focus && list && list.length) $('button', cmsub).focus({preventScroll: true});
    };
    put(null);
    it.sub(put);
  }

  cmenu.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-i]'); if (!b) return;
    var it = items[+b.dataset.i];
    if (it.sub) { openSub(b, it, true); return; }
    close(); it.act();
  });
  cmenu.addEventListener('mouseover', function (e) {
    var b = e.target.closest('button[data-i]'); if (!b) return;
    var it = items[+b.dataset.i];
    if (it.sub) openSub(b, it, false); else closeSub();
  });
  cmsub.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-j]'); if (!b) return;
    var x = subItems[+b.dataset.j]; close(); if (x) x.act();
  });
  cmsub.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft' || e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); var f = subFrom; closeSub(); if (f) f.focus(); return; }
    cycle(e, cmsub);
  });
  cmenu.addEventListener('keydown', function (e) {    // 위·아래 화살표로 항목 사이 이동 · → = 옆 목록
    if (e.key === 'ArrowRight') { var sb = document.activeElement && document.activeElement.closest && document.activeElement.closest('button[data-i]'), si = sb && items[+sb.dataset.i];
      if (si && si.sub) { e.preventDefault(); openSub(sb, si, true); } return; }
    cycle(e, cmenu);
  });
  document.addEventListener('pointerdown', function (e) {   // 밖을 누르면 닫기
    var t = e.target, cl = function (q) { return t && t.closest ? t.closest(q) : null; };
    if (!cl('#cmenu') && !cl('#cmsub')) close();
  }, true);
  addEventListener('resize', function () { close(); });

  return {open: open, close: close,
          isOpen: function () { return !cmenu.hidden; },
          isCurrent: function (t) { return !!t && t === tok && !cmenu.hidden; }};
}

HD.viewCmenu = {mount: mount};
})();
