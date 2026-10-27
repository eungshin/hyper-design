/* View — 앱 부품 '낡음' 칩 그리기(R30): 열 때와 HD.parts.EVERY(60초)마다(보일 때만) GET /api/app-parts → 낡은 부품을 끌어 쓰는 카드에 칩. 규칙은 modules/parts.js(Model).
   칩 = 카드 .phone 왼쪽 위 <div class="pchip" role="status" title=전체 글>낡음</div> — busy 상태 칩(오른쪽 위)과 같은 모양, 화면을 가리지 않는다(자기 누르기만).
   카드가 다시 그려지면(교체 'hd-swap' done) 그 카드에 다시 붙인다. 도우미가 없으면(api.on 거짓) 아무것도 하지 않는다. 다시 빌드는 터미널(hd parts --rebuild)이 한다.
   HD.feature('parts', {needs: ['api', 'cardEl']}) → {refresh() → Promise, marks() → {화면 id: {text, title}}} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CSS = '.pchip{position:absolute;top:calc(8px * var(--ts,1));left:calc(8px * var(--ts,1));z-index:4;display:inline-flex;align-items:center;box-sizing:border-box;' +
  'height:calc(20px * var(--ts,1));max-width:calc(50% - 8px * var(--ts,1));padding:0 calc(8px * var(--ts,1));border:1px solid rgba(0,0,0,.12);border-radius:999px;' +
  'background:rgba(255,248,235,.96);color:#8a4b08;box-shadow:0 1px 4px rgba(0,0,0,.14);font:600 calc(11px * var(--ts,1))/1 system-ui,sans-serif;white-space:nowrap;' +
  'overflow:hidden;text-overflow:ellipsis;pointer-events:auto;cursor:default}';

function mount(ctx) {
  if (!ctx.api || !ctx.api.on) return {};
  var P = HD.parts, warn = ctx.warn || function (m) { console.warn(m); }, cur = {}, timer = 0, warned = false;
  if (!document.getElementById('hd-parts-css')) {
    var css = document.createElement('style'); css.id = 'hd-parts-css'; css.textContent = CSS; document.head.appendChild(css);
  }

  function put(id) {
    var card = ctx.cardEl(id), host = card && (card.querySelector('.phone') || card);
    if (!host) return;
    var el = host.querySelector(':scope > .pchip'), m = cur[id];
    if (!m) { if (el) el.remove(); return; }
    if (!el) { el = document.createElement('div'); el.className = 'pchip'; el.setAttribute('role', 'status'); host.appendChild(el); }
    el.textContent = m.text; el.title = m.title;
  }

  function render(prev) {
    Object.keys(prev || {}).forEach(function (id) { if (!cur[id]) put(id); });
    Object.keys(cur).forEach(put);
  }

  function refresh() {
    return ctx.api.call('GET', '/api/app-parts').then(function (res) {
      if (res.status !== 200) throw new Error('HTTP ' + res.status);
      var next = P.marks(res.body), prev = cur;
      warned = false;
      if (!P.same(prev, next)) { cur = next; render(prev); }
    }).catch(function (e) {
      if (!warned) { warn('[hd] 앱 부품 낡음을 읽지 못했어요(' + (e && e.message || e) + ')'); warned = true; }
    });
  }

  function loop() {
    clearTimeout(timer);
    timer = setTimeout(function () {
      (document.visibilityState === 'hidden' ? Promise.resolve() : refresh()).then(loop);
    }, P.EVERY);
  }

  document.addEventListener('hd-swap', function (e) {
    var d = e && e.detail;
    if (d && d.phase === 'done' && cur[d.id]) put(d.id);
  });
  refresh().then(loop);
  return {refresh: refresh, marks: function () { return cur; }};
}

HD.feature('parts', {needs: ['api', 'cardEl'], mount: mount});
})();
