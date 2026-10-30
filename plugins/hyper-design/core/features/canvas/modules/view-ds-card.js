/* View — 판 위 디자인 시스템 카드(S6): 판 글 아래·화면 줄 위 자기 줄에 카드 하나, 화면과 같은 tokens.css 로 그린다. 칸 규칙은 modules/ds-card.js(Model).
   카드 = iframe(srcdoc) 하나 — <link id="tokens" href="tokens.css"> 를 화면과 똑같이 읽고, 셸이 모든 iframe 에 보내는 hd-palette·hd-theme-vars 를
   그대로 받는다(화면의 palette.js 와 같은 것만 — 토큰 저장 뒤 hd-tokens-reload 도, R55). 그래서 테마 패널에서 고르거나 색을 고치면 카드와 모든 화면이 한 번에 바뀐다.
   누르기(끌지 않고)·Enter = Foundation 탭(이동 도구 V 에서는 누르기 = 판 글 고르기, t51-9). 숨기기 = 판 글 레이어 '@dscard'(주인은 셸 hidden — 레이어 패널 눈·숨긴 것 목록). 시작 때 숨김은
   view-layer-flags 의 loadHidden(셸이 붙일 때) 이 이 카드보다 먼저 돌아서 저장 키 hd-hidden 을 읽기만 한다. 요청문·메모 핀·연결·교체 대상이 아니다(.card 가 아님).
   토큰이 없으면(hd-data tokens 없음·색 토큰 0) 카드 없음, 오류 없음. 데이터가 깨졌으면 [hd] 경고 한 줄.
   HD.feature('dsCard', {needs: [rowsEl, frameLoaded, store, key, warn]}) → {el | null} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var ID = 'dscard', LAYER = '@dscard';

var CSS = '#dscard{margin:72px 0 0;width:960px;cursor:pointer;outline:none}' +
  '#dscard[hidden]{display:none}' +
  '#dscard .dsh{display:flex;align-items:baseline;gap:12px;margin:0 0 14px}' +
  '#dscard .dsh b{font-size:31px;font-weight:700;color:#1c1c1c}' +
  '#dscard .dsh span{font-size:18px;color:#6b6b66}' +
  '#dscard .dsf{display:block;width:960px;height:540px;border:0;border-radius:18px;background:#fff;box-shadow:0 3px 14px rgba(0,0,0,.10);pointer-events:none}' +
  '#dscard:hover .dsf,#dscard:focus-visible .dsf{box-shadow:0 0 0 3px rgba(0,0,0,.18),0 3px 14px rgba(0,0,0,.10)}';

// 카드 문서 안 — 값은 모두 var(--…)(Model), 모양 수치만 여기
var DOC_CSS = '*{box-sizing:border-box}html,body{margin:0;height:100%;overflow:hidden}' +
  'body{background:var(--c-surface,#fff);color:var(--c-text-1,#1b1b1b);font-family:var(--font,-apple-system,sans-serif);letter-spacing:var(--tracking,0);' +
  'display:grid;grid-template-columns:1.15fr 1fr;gap:40px;padding:34px 38px}' +
  'h3{margin:0 0 14px;font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--c-text-3,#777)}' +
  '.row{margin:0 0 20px}.rl{display:flex;justify-content:space-between;font-size:15px;margin:0 0 8px}.rl b{font-weight:600}.rl code{font:12px ui-monospace,Menlo,monospace;color:var(--c-text-3,#777)}' +
  '.strip{display:flex;height:62px;border-radius:12px;overflow:hidden;border:1px solid var(--c-line,#e5e5e5)}.strip i{flex:1}' +
  '.ty{display:flex;align-items:baseline;gap:14px;margin:0 0 12px;white-space:nowrap;overflow:hidden}.ty small{flex:none;width:76px;font-size:12px;color:var(--c-text-3,#777)}' +
  '.btns{display:flex;gap:12px;margin:0 0 18px}.btns button{height:48px;padding:0 20px;font:inherit;font-size:15px;font-weight:600}' +
  '.in{display:flex;gap:10px;align-items:center}.in label{flex:1;display:flex;align-items:center;gap:10px;height:50px;padding:0 14px;font-size:15px}' +
  '.in label svg,.ib svg{width:18px;height:18px;flex:none;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}' +
  '.ib{width:50px;height:50px;display:grid;place-items:center;border:0}' +
  '.shape{display:flex;gap:14px;margin:22px 0 0;align-items:flex-end}.shape div{display:flex;flex-direction:column;align-items:center;gap:6px;font:11px ui-monospace,Menlo,monospace;color:var(--c-text-3,#777)}' +
  '.shape i{display:block;width:52px;height:40px;background:var(--c-brand-tint,#eee);border:2px solid var(--c-brand,#333)}' +
  '.shape i.sh{background:var(--c-surface,#fff);border:0;border-radius:8px}';

// 화면의 palette.js 와 같은 세 가지(바탕 토큰 파일 바꾸기 — '@project' = tokens.css 그대로 · 내 테마 색 덮어쓰기 · hd-tokens-reload 토큰 다시 읽기, R55)만 — 나머지 메시지는 모른다
var DOC_JS = '(function(){var KEY="hd-palette",set=[],cur="",ver="";' +
  'function href(b){b=String(b).split("?")[0];var h=cur&&cur!=="@project"?b.replace(/tokens(-[^/]*)?\\.css$/,"tokens-"+cur+".css"):b;return ver?h+"?v="+ver:h;}' +
  'function put(){var l=document.getElementById("tokens");if(!l)return;var b=l.getAttribute("data-base")||l.getAttribute("href");l.setAttribute("data-base",b);l.setAttribute("href",href(b));}' +
  'function pal(s){if(!s)return;cur=String(s);put();}' +
  'function reload(v){ver=String(v||Date.now()).replace(/[^\\w-]/g,"");put();}' +
  'function vars(v){var st=document.documentElement.style;set.forEach(function(k){st.removeProperty(k);});set=[];' +
  'Object.keys(v||{}).forEach(function(k){if(/^--c-[a-z0-9-]+$/.test(k)&&/^#[0-9a-f]{6}$/i.test(v[k])){st.setProperty(k,v[k]);set.push(k);}});}' +
  'try{pal(localStorage.getItem(KEY));}catch(e){}' +
  'addEventListener("message",function(e){var d=e.data;if(!d||e.source!==parent)return;if(d.type==="hd-palette")pal(d.slug);else if(d.type==="hd-theme-vars")vars(d.vars);else if(d.type==="hd-tokens-reload")reload(d.v);});})();';

var ICON_SEARCH = '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>';
var ICON_PLUS = '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>';

function doc(s, esc) {
  var colors = s.colors.map(function (c) {
    return '<div class="row" data-row="' + c.key + '"><div class="rl"><b>' + c.label + '</b><code>' + esc(c.token || '기본 회색') + '</code></div>' +
      '<div class="strip">' + c.steps.map(function (t, i) { return '<i data-i="' + i + '" title="' + esc(t.label) + '" style="background:' + esc(t.css) + '"></i>'; }).join('') + '</div></div>';
  }).join('');
  var type = s.type.map(function (t) {
    return '<div class="ty" data-type="' + t.key + '"><small>' + t.label + '</small><span style="font-size:' + esc(t.size) + ';font-weight:' + esc(t.weight) +
      ';line-height:' + esc(t.lh) + '">' + esc(t.sample) + '</span></div>';
  }).join('');
  var btns = s.buttons.map(function (b) {
    return '<button type="button" data-btn="' + b.key + '" style="background:' + esc(b.bg) + ';color:' + esc(b.fg) + ';border:' + esc(b.border) +
      ';border-radius:' + esc(b.radius) + '">' + b.label + '</button>';
  }).join('');
  var p = s.buttons[0], inp = s.input;
  var shape = s.radius.map(function (n) { return '<div><i style="border-radius:var(' + esc(n) + ')"></i>' + esc(n.slice(2)) + '</div>'; }).join('') +
    s.shadow.map(function (n) { return '<div><i class="sh" style="box-shadow:var(' + esc(n) + ')"></i>' + esc(n.slice(2)) + '</div>'; }).join('');
  return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><link id="tokens" rel="stylesheet" href="tokens.css"><style>' + DOC_CSS + '</style>' +
    '<script>' + DOC_JS + '<\/script></head><body><section><h3>Colors</h3>' + colors + '</section>' +
    '<section><h3>Type</h3>' + type + '<h3 style="margin-top:22px">Components</h3><div class="btns">' + btns + '</div>' +
    '<div class="in"><label data-input style="background:' + esc(inp.bg) + ';color:' + esc(inp.placeholder) + ';border:' + esc(inp.border) + ';border-radius:' + esc(inp.radius) + '">' +
    ICON_SEARCH + '검색</label><button type="button" class="ib" data-iconbtn aria-label="더하기" style="background:' + esc(p.bg) + ';color:' + esc(p.fg) + ';border-radius:' + esc(inp.radius) + '">' + ICON_PLUS + '</button></div>' +
    (shape ? '<div class="shape">' + shape + '</div>' : '') + '</section></body></html>';
}

function mount(ctx) {
  var data = null;
  try { data = JSON.parse((document.getElementById('hd-data') || {}).textContent || '{}'); } catch (e) { data = {}; }
  var names = data.tokens;
  if (names != null && !Array.isArray(names)) ctx.warn('[hd] 디자인 시스템 카드: hd-data tokens 가 목록이 아니에요 — 카드 없이');
  var spec = HD.dsCard.sections(names);
  if (!spec) return {el: null};
  if (spec.bad) ctx.warn('[hd] 디자인 시스템 카드: 토큰 이름이 아닌 값 ' + spec.bad + '개를 버렸어요');

  if (!document.getElementById('hd-dscard-css')) {
    var st = document.createElement('style'); st.id = 'hd-dscard-css'; st.textContent = CSS; document.head.appendChild(st);
  }
  var esc = ctx.esc || function (x) { return String(x).replace(/[&<>"']/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; }); };
  var el = document.createElement('section');
  el.id = ID; el.tabIndex = 0; el.setAttribute('role', 'button');
  el.setAttribute('aria-label', '디자인 시스템 — 누르면 Foundation 탭');
  el.title = '디자인 시스템 — 누르면 Foundation 탭';
  el.style.marginLeft = ctx.rowsEl.style.paddingLeft || '0px';
  el.innerHTML = '<div class="dsh"><b>디자인 시스템</b><span>화면과 같은 tokens.css · 테마를 바꾸면 이 카드와 모든 화면이 함께 바뀌어요</span></div>';
  var f = document.createElement('iframe');
  f.className = 'dsf'; f.title = '디자인 시스템 카드'; f.tabIndex = -1; f.setAttribute('scrolling', 'no');
  f.addEventListener('load', function () { ctx.frameLoaded(LAYER, f); });   // 지금 테마(바탕 파일 + 내 테마 색)를 화면 카드와 같은 길로
  f.srcdoc = doc(spec, esc);
  el.appendChild(f);
  try {                                                // 시작 숨김 — 주인은 view-layer-flags(hd-hidden), 그 loadHidden 이 이 카드보다 먼저 돈다
    var hid = JSON.parse(ctx.store.getItem(ctx.key('hd-hidden')) || '[]');
    el.hidden = Array.isArray(hid) && hid.indexOf(LAYER) >= 0;
  } catch (e) { ctx.warn('[hd] 디자인 시스템 카드: 숨김 목록을 읽지 못했어요 — 보이게 둬요'); }
  ctx.rowsEl.parentNode.insertBefore(el, ctx.rowsEl);

  function open() {
    var tab = document.querySelector('.tab[data-tab="foundation"]');
    if (tab) tab.click(); else if (ctx.toast) ctx.toast('Foundation 탭이 없어요');
  }
  var down = null;
  el.addEventListener('pointerdown', function (e) { down = {x: e.clientX, y: e.clientY}; });
  el.addEventListener('click', function (e) {
    if (el.closest('.t-move')) { down = null; return; }   // 이동 도구(V) = 판 글 고르기(t51-9, view-board-text) — Enter 가 Foundation 탭
    e.stopPropagation();                               // 판의 빈 곳 누르기(고르기 풀기·레이아웃 놓기)로 가지 않게
    var moved = !down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 4; down = null;
    if (!moved && !e.shiftKey && !e.ctrlKey && !e.metaKey && e.button === 0) open();   // 끌어 판을 옮긴 뒤의 click 은 열지 않는다
  });
  el.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); open(); } });
  return {el: el};
}

HD.feature('dsCard', {needs: ['rowsEl', 'frameLoaded', 'store', 'key', 'warn'], mount: mount});
})();
