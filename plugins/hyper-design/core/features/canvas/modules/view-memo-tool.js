/* View — 말풍선 메모 도구 한 칸(data-tool="memo")의 모드(요소 P · 화면 M): 칸 귀퉁이 글·꼬리말·키·aria-label, 판 커서 표시 t-annotate(요소)·t-memo(화면).
   규칙(키 → 모드 · 이름표 · 꼬리말 글) = ViewModel HD.tools(modeOfKey·memoMode·memoTip). 모드는 저장하지 않는다(새로 열면 요소) — 같은 칸 단추 = 마지막 모드.
   키: P·M 을 window capture 에서 먼저 읽어 모드만 바꾼다(도구 켜기는 셸 keydown 이 tools.byKey 로 — 두 키 모두 'memo'). 글 칸에 쓰는 중·Ctrl/Alt/Meta 면 건드리지 않는다.
   HD.viewMemoTool.mount(ctx) → {mode() → 'el'|'screen', set(mode)(칸·판 커서 다시), paint()(지금 도구에 맞게 판 커서)}
   ctx = {$, pane, tool() → 지금 판 도구, typing(e) → 글 칸에 쓰는 중인가} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#tools .tb .tmode{position:absolute;right:2px;bottom:2px;font:700 7.5px/1 system-ui,sans-serif;letter-spacing:-.3px;color:#8a8a86;pointer-events:none}' +
  '#tools .tb[aria-pressed="true"] .tmode{color:#d8d8d4}' +
  '.elbox.scr{--kc:var(--ui-primary,#1c1c1c);border-style:solid;border-radius:calc(var(--card-r,28px) + 6px);z-index:6}';

function mount(ctx) {
  var T = HD.tools, $ = ctx.$, btn = $('#tools [data-tool="memo"]'), mode = 'el', tag = null;
  if (typeof document.createElement === 'function' && document.head) {
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  }
  if (btn) { tag = document.createElement('span'); tag.className = 'tmode'; tag.setAttribute('aria-hidden', 'true'); btn.appendChild(tag); }
  function paint() {
    var on = ctx.tool() === 'memo';
    ctx.pane.classList.toggle('t-annotate', on && mode === 'el');   // 커서(shell.css): 요소 = cell · 화면 = text
    ctx.pane.classList.toggle('t-memo', on && mode === 'screen');
  }
  function set(m) {
    var n = T.memoMode(m);
    if (m != null && n !== m) console.warn('[hd] 모르는 메모 모드 "' + m + '" — 요소로');
    mode = n;
    var t = T.memoTip(mode);
    if (btn) { btn.dataset.tip = t.tip; btn.dataset.key = t.key; btn.dataset.mode = mode; btn.setAttribute('aria-label', t.aria); }
    if (tag) tag.textContent = t.corner;
    paint();
  }
  addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey || ctx.typing(e)) return;
    var m = T.modeOfKey((e.key || '').toLowerCase()); if (m) set(m);
  }, true);
  set(mode);
  return {mode: function () { return mode; }, set: set, paint: paint};
}

HD.viewMemoTool = {mount: mount};
})();
