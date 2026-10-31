/* View — 부품 쓰는 화면 보이기(R58): Components 칩·속성 창 '쓰는 화면 N' 누르기 → Screens 탭, 그 카드만 또렷·나머지 흐리게 + 카메라 맞춤 + 막대 '버튼 · 쓰는 화면 5 · ✕'.
   데이터 = hd-data usage(빌드 board_data.usage) → HD.usage.read(Model) 로 검사. 상태(이 View 만): 지도 · 꺼짐(깨진 데이터) · 지금 보이는 부품.
   받는 것: components.html 칩의 hd-usage-show {key, title}(그 iframe 에서만) · 의도 'hd-usage-show' {key, title}(속성 창) · 'hd-usage-count' {key} → detail.n 을 채움(동기).
   걷기 = ✕ · Esc · 다른 탭으로. 카메라는 셸 ctx.focus(ids, 1)(fitCards 와 같은 계산, 100% 까지), 탭 바꾸기는 Screens 탭 단추 누르기(셸 showTab 그대로).
   오류 탐지: 데이터가 깨짐 = [hd] 경고 한 번 + 칩 숨김(문서 탭에 hd-usage-off) · 판에 없는 화면 id = 빼고 [hd] 한 줄 · 지도에 없는 부품을 누름 = 토스트.
   HD.feature('usage', {needs: ['$', '$$', 'toast', 'warn', 'rowsEl', 'cardEl', 'focus']}) → {show(key, title), clear(), current() → key|null}. 계약 contract/usage-map.md */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#rows.use-on .card:not(.use-hit){opacity:.22}' +
  '#rows.use-on .card.use-hit{opacity:1}' +
  '#rows.use-on .card.use-hit .phone{outline:calc(3px * var(--ts,1)) solid var(--ui-mark,#2b2b29);outline-offset:calc(5px * var(--ts,1))}' +
  '#rows.use-on path.ln,#rows.use-on .alabel{opacity:.15}' +
  '#useBar{position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:30;display:flex;align-items:center;gap:6px;height:32px;padding:0 4px 0 12px;box-sizing:border-box;' +
    'background:var(--ui-surface,#fff);border-radius:8px;box-shadow:0 0 0 1px var(--ui-line,#e3e3df),0 4px 14px rgba(0,0,0,.12);' +
    'font:12.5px/1 system-ui,-apple-system,"Pretendard",sans-serif;color:#1c1c1c;cursor:default;white-space:nowrap}' +
  '#useBar[hidden]{display:none}#useBar .ub-t b{font-weight:600}#useBar .ub-t span{color:#6b6b66}' +
  '#useBar .ub-x{width:24px;height:24px;border:0;border-radius:6px;background:none;color:#6b6b66;font-size:14px;line-height:1;cursor:pointer;padding:0}' +
  '#useBar .ub-x:hover{background:#F1F1EE;color:#1c1c1c}';

function mount(ctx) {
  var U = HD.usage, $ = ctx.$, rowsEl = ctx.rowsEl, data;
  try { data = JSON.parse((document.getElementById('hd-data') || {}).textContent || '{}'); } catch (e) { data = {}; }
  var ids = [];
  (Array.isArray(data.rows) ? data.rows : []).forEach(function (r) { (r && Array.isArray(r.screens) ? r.screens : []).forEach(function (c) { if (c && c.id) ids.push(c.id); }); });
  var got = U.read(data.usage, ids), map = got.map, off = !!got.bad, cur = null;
  if (got.bad) ctx.warn('[hd] 부품 쓰는 화면: ' + got.bad + ' — 칩 없이');
  if (got.unknown.length) ctx.warn('[hd] 부품 쓰는 화면: 판에 없는 화면 id 를 뺐어요 — ' + got.unknown.join(', '));

  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var pane = $('#screens') || document.body;
  var bar = document.createElement('div');
  bar.id = 'useBar'; bar.setAttribute('role', 'status'); bar.hidden = true;
  bar.innerHTML = '<span class="ub-t"></span><button type="button" class="ub-x" aria-label="강조 걷기" title="걷기 (Esc)">✕</button>';
  pane.appendChild(bar);
  ['pointerdown', 'mousedown', 'wheel', 'dblclick', 'contextmenu'].forEach(function (t) { bar.addEventListener(t, function (e) { e.stopPropagation(); }); });   // 판 끌기·확대가 받지 않게
  bar.querySelector('.ub-x').addEventListener('click', function () { clear(); });

  var doc = $('#components iframe.doc');
  function quiet() { if (off && doc && doc.contentWindow) { try { doc.contentWindow.postMessage({type: 'hd-usage-off'}, '*'); } catch (e) { ctx.warn('[hd] 문서 탭에 보내지 못함 — ' + (e && e.message || e)); } } }
  if (doc) doc.addEventListener('load', quiet);

  function clear() {
    if (!cur) return;
    cur = null; bar.hidden = true;
    rowsEl.classList.remove('use-on');
    ctx.$$('.card.use-hit', rowsEl).forEach(function (c) { c.classList.remove('use-hit'); });
  }
  function show(key, title) {
    var list = off ? null : map[key];
    if (!list || !list.length) { ctx.toast('이 부품을 쓰는 화면을 찾지 못했어요'); return; }
    if (document.body.dataset.tab !== 'screens') { var tb = $('.tab[data-tab="screens"]'); if (tb) tb.click(); }
    var a = document.activeElement; if (a && a.tagName === 'IFRAME') a.blur();   // Esc 가 판으로 오게(문서 탭 틀에 초점이 남지 않게)
    clear();
    cur = key;
    list.forEach(function (id) { var c = ctx.cardEl(id); if (c) c.classList.add('use-hit'); });
    rowsEl.classList.add('use-on');
    var t = U.bar(title || key, list.length), i = t.indexOf(' · ');
    bar.querySelector('.ub-t').innerHTML = '<b></b><span></span>';
    bar.querySelector('.ub-t b').textContent = t.slice(0, i); bar.querySelector('.ub-t span').textContent = t.slice(i);
    bar.hidden = false;
    requestAnimationFrame(function () { if (cur === key) ctx.focus(list, 1); });   // 100% 까지 다가가 담는다(Figma 고른 것에 맞추기)
  }

  addEventListener('message', function (e) {
    if (!doc || e.source !== doc.contentWindow) return;
    var m = U.showMsg(e.data); if (m) show(m.key, m.title);
  });
  document.addEventListener('hd-usage-count', function (e) { if (e.detail) e.detail.n = off ? 0 : U.count(map, e.detail.key); });
  document.addEventListener('hd-usage-show', function (e) { var d = e.detail || {}; if (typeof d.key === 'string') show(d.key, d.title || ''); });
  document.addEventListener('keydown', function (e) {
    if (!cur || e.key !== 'Escape' || document.body.dataset.tab !== 'screens') return;
    var t = e.target; if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
    clear();
  });
  ctx.$$('.tab').forEach(function (b) { b.addEventListener('click', function () { if (b.dataset.tab !== 'screens') clear(); }); });

  return {show: show, clear: clear, current: function () { return cur; }};
}

HD.feature('usage', {needs: ['$', '$$', 'toast', 'warn', 'rowsEl', 'cardEl', 'focus'], mount: mount});
})();
