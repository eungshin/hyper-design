/* View — 읽기만인 탭(#274)의 편집 막기: 편집 조작부를 흐리게 + aria-disabled, 편집 시도는 막고 '여기서 편집하기' 줄을 가리킨다. 규칙은 HD.readOnly(ViewModel).
   역할은 view-state-sync 가 알린다(document 'hd-tab-role' {role} + <html data-hd-tab>). reader 가 되면 편집 도구를 쓰고 있었으면 손으로 돌리고,
   창 capture 단계에서 막는다: CONTROLS 누르기 · 판 오른쪽 끌기(자르기)·우클릭 메뉴 · 판·레이어 두 번 누르기(이름·설명 고치기) · 레이어 끌기 · HD.readOnly.key 가 막는 키.
   글 쓰기는 막지 않는다 — 열린 메모 칸의 글은 그대로 남고, 여기서 편집하기를 누르면 그대로 추가할 수 있다(버린 쓰기가 없으니 다시 불러오지 않음).
   흐린 조작부도 눌리게 둔다(pointer-events:auto — 템플릿의 aria-disabled 도구 규칙은 눌림을 판으로 흘려 줄을 가리킬 수 없다).
   상태 = 지금 역할 · 붙인 aria-disabled(data-hd-ro 로 표시해 writer 가 되면 그것만 걷음) · 알림 시각(3초에 한 번).
   HD.feature('readOnly', {needs: ['$', '$$', 'toast']}) → {role()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NUDGE = '이 탭은 읽기만 해요 — 위쪽 "여기서 편집하기"를 누르면 여기서 편집할 수 있어요';

function mount(ctx) {
  var R = HD.readOnly, root = document.documentElement, SEL = R.CONTROLS.join(','), role = root.dataset.hdTab || 'writer', mo = null, raf = 0, lastNudge = 0;
  var css = document.createElement('style');
  css.textContent = R.CONTROLS.map(function (s) { return 'html.hd-ro ' + s; }).join(',') + '{opacity:.35!important;cursor:not-allowed!important;pointer-events:auto!important}\n' +
    ['foundation', 'components'].map(function (t) { return 'html.hd-ro body[data-tab="' + t + '"] ' + R.PICK; }).join(',') + '{opacity:1!important;cursor:pointer!important}\n' +   // 문서 탭 V = 고르기(R55)
    '#hd-tab-lock.hd-nudge{animation:hdRoNudge .5s ease 2}@keyframes hdRoNudge{50%{transform:translateX(-50%) scale(1.08)}}';
  document.head.appendChild(css);

  function reader() { return role === 'reader'; }
  function mark() {
    raf = 0;
    if (!reader()) return;
    ctx.$$(SEL).forEach(function (el) {
      if (el.getAttribute('aria-disabled') === 'true') return;
      el.setAttribute('aria-disabled', 'true'); el.setAttribute('data-hd-ro', '');
    });
  }
  function unmark() { ctx.$$('[data-hd-ro]').forEach(function (el) { el.removeAttribute('aria-disabled'); el.removeAttribute('data-hd-ro'); }); }
  function apply(r) {
    role = r;
    root.classList.toggle('hd-ro', reader());
    if (reader()) {
      var on = ctx.$('#tools [data-tool][aria-pressed="true"]'), hand = ctx.$('#tools [data-tool="hand"]');
      if (on && R.editTool(on.dataset.tool) && hand) hand.click();   // 편집 도구 → 손(셸의 도구 바꾸기 길 그대로)
      mark();
      if (!mo && typeof MutationObserver === 'function') {           // 목록·메모 묶음은 다시 그려진다 — 새 조작부도 표시
        mo = new MutationObserver(function () { if (!raf) raf = requestAnimationFrame(mark); });
        mo.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['aria-disabled']});   // 크게 보기 도구 표시(modalTools)가 걷어도 다시
      }
    } else {
      if (mo) { mo.disconnect(); mo = null; }
      unmark();
    }
  }
  function nudge() {
    var bar = document.getElementById('hd-tab-lock'), now = Date.now();
    if (bar) {
      bar.classList.remove('hd-nudge'); void bar.offsetWidth; bar.classList.add('hd-nudge');
      var b = bar.querySelector('button');            // 누르기의 기본 초점 이동이 끝난 뒤에 줄 단추로
      if (b) setTimeout(function () { b.focus({preventScroll: true}); }, 0);
    }
    if (now - lastNudge > 3000) { lastNudge = now; ctx.toast(NUDGE); }
  }
  function block(e) { e.preventDefault(); e.stopImmediatePropagation(); nudge(); }
  function inside(e, q) { var t = e.target; return !!(t && t.closest && t.closest(q)); }
  function docTab() { var t = document.body.dataset.tab; return t === 'foundation' || t === 'components'; }   // 고르기만 하는 탭(R55)
  function pointer(e) {
    if (!reader()) return;
    if (inside(e, '#hd-tab-lock')) return;
    if (inside(e, SEL) && !(docTab() && inside(e, R.PICK))) return block(e);
    var right = e.button === 2 && (e.type === 'pointerdown' || e.type === 'mousedown');
    if (right && inside(e, '#screens') && !inside(e, '#tools')) return block(e);   // 오른쪽 끌기 = 선 자르기
  }
  ['pointerdown', 'mousedown', 'click'].forEach(function (n) { addEventListener(n, pointer, true); });
  addEventListener('contextmenu', function (e) { if (reader() && inside(e, '#screens') && !inside(e, 'input,textarea,[contenteditable]')) block(e); }, true);
  addEventListener('dblclick', function (e) { if (reader() && inside(e, '#screens,#lyTree')) block(e); }, true);
  addEventListener('dragstart', function (e) { if (reader() && inside(e, '#lyTree')) block(e); }, true);
  addEventListener('keydown', function (e) {
    if (!reader()) return;
    var t = e.target, typing = !!(t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || '')));
    var field = typing ? (t.id || (t.closest && t.closest('#tedit') ? 'tedit' : '')) : null;
    if (R.key({key: e.key, ctrl: e.ctrlKey, meta: e.metaKey, shift: e.shiftKey, alt: e.altKey, typing: typing, field: field, doc: docTab()})) block(e);
  }, true);
  document.addEventListener('hd-tab-role', function (e) { apply(e.detail && e.detail.role || 'writer'); });
  if (reader()) apply(role);
  return {role: function () { return role; }};
}

HD.feature('readOnly', {needs: ['$', '$$', 'toast'], mount: mount});
})();
