/* View — 우클릭 메뉴(#cmenu)와 그 옆 목록(#cmsub): 그리기·자리·키(↑↓ 돌기 · → 옆 목록 · ← / Esc 옆 목록 닫기)·밖 누르기·창 크기 바뀜에 닫기.
   항목을 고르는 일(무엇을 넣을지)은 셸, 이 모듈은 받은 항목을 보이고 누르면 act() 를 부른다. Esc 차례는 셸이 isOpen()/close() 로 정한다.
   items: [{label, key?, id?, act()} | {label, id?, sub(cb)}(옆 목록 — cb([{label, id?, title?, act}] | null = 찾는 중), 옆 목록 id 도 data-act)] · '-' = 구분선 · {head} = 소제목
   id = 항목의 뜻(data-act — 테스트·검사는 글이 아니라 이것으로 고른다, R17) · key = 실제로 듣는 단축키 힌트(오른쪽 맞춤 kbd)
   pin = {state() → {on, ok, why}, toggle()}(R50 막대에 고정 — 두 목록 모두): 줄 끝 핀 [data-pin=id](role=button · aria-pressed · Tab 으로 줄 → 핀).
     누르면 동작은 실행하지 않고 toggle(), 메뉴는 열린 채 두 목록의 핀을 state() 로 다시 칠한다(6개 한도로 다른 줄도 바뀜). 핀이 있는 줄만 .cmrow 로 감싼다(줄 단추 선택자 그대로)
   HD.viewCmenu.mount(ctx) → {open(x, y, head, items) → 토큰, isCurrent(토큰) → 그 열기가 아직 떠 있나, isOpen(), close()}
   ctx = {$, $$, esc, menu: #cmenu, sub: #cmsub} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CSS =                                            // R50 줄 끝 핀 — 고정 안 됨 = 올렸을 때만 옅게 · 고정됨 = 늘 채운 핀 · 꺼짐 = 흐리게
  '.cm .cmrow{position:relative}' +
  '.cm .cmrow>button{padding-right:32px}' +
  '.cm .cmpin{position:absolute;right:5px;top:50%;width:22px;height:22px;margin-top:-11px;display:grid;place-items:center;border-radius:6px;color:#8a8a85;opacity:0;cursor:pointer;outline:0}' +
  '.cm .cmrow:hover .cmpin,.cm .cmrow:focus-within .cmpin{opacity:.55}' +
  '.cm .cmpin:hover,.cm .cmpin:focus-visible{background:#E4E4DF;opacity:1}' +
  '.cm .cmpin[aria-pressed="true"]{opacity:1;color:var(--ui-primary,#2b2b29)}' +
  '.cm .cmpin[aria-pressed="true"] svg{fill:currentColor}' +
  '.cm .cmpin[aria-disabled="true"]{cursor:not-allowed}' +
  '.cm .cmrow:hover .cmpin[aria-disabled="true"],.cm .cmrow:focus-within .cmpin[aria-disabled="true"]{opacity:.25}' +
  '.cm .cmpin svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}';
var PIN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4h6l-1 6 3 3H7l3-3z"/><path d="M12 13v7"/></svg>';

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, cmenu = ctx.menu, cmsub = ctx.sub;
  var items = [], tok = null, subItems = [], subTok = null, subFrom = null;
  if (!document.getElementById('hd-cmpin-css')) { var st = document.createElement('style'); st.id = 'hd-cmpin-css'; st.textContent = CSS; document.head.appendChild(st); }

  function pinState(it) {                          // 항목의 핀 모양 — state() 가 던지면 꺼진 핀 + [hd] 경고(메뉴는 그대로)
    try { var s = it.pin.state(); return s && typeof s === 'object' ? s : {on: false, ok: false, why: ''}; }
    catch (e) { console.warn('[hd] 메뉴 핀 상태를 읽지 못했어요 — ' + (e && e.message || e)); return {on: false, ok: false, why: ''}; }
  }
  function pinLabel(s) { return s.on ? '막대에서 빼기' : '막대에 고정'; }
  function pinAttrs(it) {
    var s = pinState(it);
    return ' aria-pressed="' + (s.on ? 'true' : 'false') + '" aria-label="' + pinLabel(s) + '"' + (s.ok ? '' : ' aria-disabled="true"') + ' title="' + esc(s.why || pinLabel(s)) + '"';
  }
  function row(btn, it, attr) {                    // 핀이 있는 줄 = 줄 단추 + 그 옆 핀(줄 단추 안에 단추를 넣지 않는다)
    if (!it.pin || !it.id) return btn;
    return '<div class="cmrow">' + btn + '<span class="cmpin" role="button" tabindex="0" data-pin="' + esc(it.id) + '" ' + attr + pinAttrs(it) + '>' + PIN + '</span></div>';
  }
  function paintPins() {                           // 토글 뒤 두 목록의 핀을 다시 칠한다(6개 한도는 다른 줄도 바꾼다)
    [[cmenu, items, 'data-pi'], [cmsub, subItems, 'data-pj']].forEach(function (x) {
      $$('.cmpin', x[0]).forEach(function (p) {
        var it = x[1][+p.getAttribute(x[2])]; if (!it || !it.pin) return;
        var s = pinState(it);
        p.setAttribute('aria-pressed', s.on ? 'true' : 'false'); p.setAttribute('aria-label', pinLabel(s));
        if (s.ok) p.removeAttribute('aria-disabled'); else p.setAttribute('aria-disabled', 'true');
        p.title = s.why || pinLabel(s);
      });
    });
  }
  function pressPin(p, list, attr) {               // 핀 = 고정만 토글, 동작은 실행하지 않고 메뉴는 열린 채
    var it = list[+p.getAttribute(attr)];
    if (!it || !it.pin || p.getAttribute('aria-disabled') === 'true') return;
    try { it.pin.toggle(); } catch (e) { console.error('[hd] 메뉴 핀: ' + (e && e.message || e)); }
    paintPins();
  }

  function cycle(e, box) {                         // ↑↓ = 그 목록 안 단추 사이를 돈다(끝에서 처음으로)
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    var ae = document.activeElement, bs = $$('button', box), i = bs.indexOf(ae);
    if (i < 0 && ae && ae.classList && ae.classList.contains('cmpin')) i = bs.indexOf(ae.previousElementSibling);   // 핀에서 ↑↓ = 그 줄에서
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
        row('<button type="button" role="menuitem" data-i="' + i + '"' + (it.id ? ' data-act="' + esc(it.id) + '"' : '') + (it.sub ? ' aria-haspopup="menu" aria-expanded="false"' : '') + '>' + esc(it.label) +
        (it.key ? '<kbd>' + esc(it.key) + '</kbd>' : '') + (it.sub ? '<span class="sub" aria-hidden="true">▸</span>' : '') + '</button>', it, 'data-pi="' + i + '"');
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
        return row('<button type="button" role="menuitem" data-j="' + i + '"' + (x.id ? ' data-act="' + esc(x.id) + '"' : '') + (x.title ? ' title="' + esc(x.title) + '"' : '') + '>' + esc(x.label) + '</button>', x, 'data-pj="' + i + '"'); }).join('') : '<div class="cmh">고를 요소가 없어요</div>';
      cmsub.hidden = false;
      var r = b.getBoundingClientRect(), w = cmsub.offsetWidth, x = r.right + 2 + w > innerWidth - 8 ? r.left - w - 2 : r.right + 2;
      cmsub.style.left = Math.max(8, x) + 'px'; cmsub.style.top = Math.max(8, Math.min(innerHeight - cmsub.offsetHeight - 8, r.top - 5)) + 'px';
      if (focus && list && list.length) $('button', cmsub).focus({preventScroll: true});
    };
    put(null);
    it.sub(put);
  }

  cmenu.addEventListener('click', function (e) {
    var pn = e.target.closest('.cmpin'); if (pn) { e.stopPropagation(); pressPin(pn, items, 'data-pi'); return; }
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
    var pn = e.target.closest('.cmpin'); if (pn) { e.stopPropagation(); pressPin(pn, subItems, 'data-pj'); return; }
    var b = e.target.closest('button[data-j]'); if (!b) return;
    var x = subItems[+b.dataset.j]; close(); if (x) x.act();
  });
  function pinKey(e, list, attr) {                 // 핀(role=button)에서 Enter·Space = 누르기
    var pn = e.target && e.target.classList && e.target.classList.contains('cmpin') ? e.target : null;
    if (!pn || (e.key !== 'Enter' && e.key !== ' ')) return false;
    e.preventDefault(); e.stopPropagation(); pressPin(pn, list, attr); return true;
  }
  cmsub.addEventListener('keydown', function (e) {
    if (pinKey(e, subItems, 'data-pj')) return;
    if (e.key === 'ArrowLeft' || e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); var f = subFrom; closeSub(); if (f) f.focus(); return; }
    cycle(e, cmsub);
  });
  cmenu.addEventListener('keydown', function (e) {    // 위·아래 화살표로 항목 사이 이동 · → = 옆 목록
    if (pinKey(e, items, 'data-pi')) return;
    if (e.key === 'ArrowRight') { var sb = document.activeElement && document.activeElement.closest && document.activeElement.closest('button[data-i]'), si = sb && items[+sb.dataset.i];
      if (si && si.sub) { e.preventDefault(); openSub(sb, si, true); } return; }
    cycle(e, cmenu);
  });
  document.addEventListener('pointerdown', function (e) {   // 밖을 누르면 닫기
    var t = e.target, cl = function (q) { return t && t.closest ? t.closest(q) : null; };
    if (!cl('#cmenu') && !cl('#cmsub')) close();
  }, true);
  addEventListener('resize', function () { close(); });
  addEventListener('message', function (e) {         // 화면 틀(크게 보기) 안 왼쪽 누름 = 밖 누르기 — 틀 안 누름은 위 pointerdown 에 오지 않는다(palette.js hd-press)
    if (e.data && e.data.type === 'hd-press') close();
  });

  return {open: open, close: close,
          isOpen: function () { return !cmenu.hidden; },
          isCurrent: function (t) { return !!t && t === tok && !cmenu.hidden; }};
}

HD.viewCmenu = {mount: mount};
})();
