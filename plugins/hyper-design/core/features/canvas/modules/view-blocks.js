/* View — 요소 막대(블록 편집, task 49a): 고른 요소 옆 [글자][지우기][복제][↑][↓][메모] · Alt+↑↓·Ctrl+D 단축키. 규칙(켜짐·앱 = AI 요청·자리)은 HD.blocks(Model).
   상태 = 지금 고른 요소 하나 {screen, h, app, where:'board'|'modal', anchor() → 화면 좌표 사각형|null} (막대가 그 주인, 저장하지 않음).
   편집 자체는 셸이 한다 — 단추는 onAct(fn) 로 받은 fn(act, sel) 하나로만 나간다(View 끼리 부르지 않음). 읽기만인 탭(<html data-hd-tab="reader">)은 누르면 알리기만.
   HD.feature('blocks', {needs: ['$', 'toast']}) → {show(sel), hide(where?), place(), sel(), onAct(fn)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '#elbar{position:fixed;z-index:35;display:flex;gap:2px;padding:3px;background:#1c1c1c;border-radius:9px;box-shadow:0 4px 14px rgba(0,0,0,.25);font:600 12.5px system-ui,sans-serif}' +
  '#elbar[hidden]{display:none}' +
  '#elbar button{border:0;background:none;color:#fff;font:inherit;padding:5px 9px;border-radius:6px;cursor:pointer;white-space:nowrap}' +
  '#elbar button:hover{background:#3a3a3a}' +
  '#elbar button[aria-disabled="true"]{opacity:.35;cursor:not-allowed}' +
  '#elbar button.ask{color:#f5c26b}' +
  '#elbar .eb-sep{width:1px;margin:4px 3px;background:#444}' +
  'html[data-hd-tab="reader"] #elbar button{opacity:.35;cursor:not-allowed}';
var RO = '이 탭은 읽기만 해요 — 위쪽 "여기서 편집하기"를 누르면 여기서 편집할 수 있어요';

function mount(ctx) {
  var B = HD.blocks, cur = null, act = null, bar = document.createElement('div');
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  bar.id = 'elbar'; bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', '고른 요소'); bar.hidden = true;
  document.body.appendChild(bar);

  function reader() { return document.documentElement.dataset.hdTab === 'reader'; }
  function paint() {
    var items = B.bar(cur.h, {app: cur.app});
    bar.innerHTML = items.map(function (it) {
      return (it.act === 'memo' ? '<span class="eb-sep"></span>' : '') +
        '<button type="button" data-act="' + it.act + '"' + (it.on ? '' : ' aria-disabled="true"') + (it.ask ? ' class="ask" data-ask="1"' : '') +
        ' title="' + ctx.esc(it.title) + '" aria-label="' + ctx.esc(it.title) + '">' + ctx.esc(it.label) + '</button>';
    }).join('');
    bar.dataset.screen = cur.screen; bar.dataset.where = cur.where; bar.dataset.app = cur.app ? '1' : '';
  }
  function place() {
    if (!cur) return;
    var a = cur.anchor && cur.anchor();
    if (!a || !a.w && !a.h) { bar.hidden = true; return; }
    bar.hidden = false;
    var sb = ctx.$('#selbar'), avoid = sb && !sb.hidden ? sb.getBoundingClientRect() : null;
    var p = B.place(a, {w: bar.offsetWidth, h: bar.offsetHeight}, {w: innerWidth, h: innerHeight},
                    avoid ? {x: avoid.left, y: avoid.top, w: avoid.width, h: avoid.height} : null);
    bar.style.left = p.x + 'px'; bar.style.top = p.y + 'px';
  }
  function show(sel) {
    if (!sel || !sel.h || !sel.h.path) { hide(); return; }
    cur = sel; paint(); bar.hidden = false; place();
  }
  function hide(where) {
    if (where && cur && cur.where !== where) return;
    cur = null; bar.hidden = true;
  }
  function fire(a) {
    if (!cur || !act) return;
    var it = B.bar(cur.h, {app: cur.app}).filter(function (x) { return x.act === a; })[0];
    if (!it) return;
    if (reader()) { ctx.toast(RO); return; }
    if (!it.on) { ctx.toast(it.title); return; }   // 꺼진 단추 = 까닭을 알린다
    var s = cur; s.ask = it.ask;
    try { act(a, s); } catch (e) { console.error('[hd] 요소 막대 ' + a + ': ' + (e && e.message || e)); ctx.toast('요소 편집을 하지 못했어요 — ' + (e && e.message || e)); }
  }
  bar.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 판 끌기·고르기 풀기로 새지 않게
  bar.addEventListener('click', function (e) {
    e.stopPropagation();
    var b = e.target.closest('button[data-act]'); if (b) fire(b.dataset.act);
  });
  addEventListener('keydown', function (e) {        // 고른 요소가 있을 때만: Alt+↑↓ 옮기기 · Ctrl+D 복제
    if (!cur || bar.hidden) return;
    var t = e.target; if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
    var a = B.keyAct({key: e.key, alt: e.altKey, ctrl: e.ctrlKey, meta: e.metaKey, shift: e.shiftKey});
    if (!a) return;
    e.preventDefault(); e.stopPropagation(); fire(a);
  }, true);
  addEventListener('resize', place);
  return {show: show, hide: hide, place: place, sel: function () { return cur; }, onAct: function (fn) { act = typeof fn === 'function' ? fn : null; }};
}

HD.feature('blocks', {needs: ['$', 'toast', 'esc'], mount: mount});
})();
