/* View — 하단 대화창(S1): 판 아래 가운데 입력창 · 고른 카드·요소 칩(×) · 마지막 요청 상태 한 줄. 규칙(칩·범위·메모 초안·상태 말)은 HD.chat(Model).
   상태 = 지운 칩 표시(저장하지 않음) · 마지막 요청 {text, ids, at}(ctx.local 키 hd-chat-last:<해시>, 주인 이 파일). 메모·보내기는 셸 것 — ctx.sendNotes(list) 하나로만 나간다
   (위쪽 [보내기]와 같은 길: 도우미가 있으면 /api/forward, 없으면 복사). 고른 것은 ctx.selected()·ctx.picked() 로 읽기만, 덮개 상태(hd-busy)도 읽기만.
   Enter = 보내기 · Shift+Enter = 줄바꿈(한글 조합 중 Enter 는 무시) · Esc = 입력창에서 나가기. 크게 보기·다른 탭·읽기만 탭에서는 숨긴다.
   HD.feature('chat', {needs: ['$', 'toast', 'esc', 'notes', 'local', 'store', 'key', 'title', 'rowsEl']}) → {render(), send(text), last()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '#hdchat{position:fixed;bottom:10px;left:50%;z-index:24;width:560px;max-width:calc(100vw - 32px);transform:translateX(-50%);font:13px system-ui,sans-serif;color:var(--ui-primary,#2b2b29)}' +
  'body.has-ptabs #hdchat{bottom:56px}' +
  '#hdchat[hidden],body.modal-open #hdchat,body.bare #hdchat,body:not([data-tab="screens"]) #hdchat,html[data-hd-tab="reader"] #hdchat{display:none}' +
  '#hdchat .ch-line{display:flex;align-items:center;gap:6px;margin:0 6px 4px;padding:3px 10px;border-radius:8px;background:rgba(255,255,255,.92);box-shadow:0 1px 6px rgba(0,0,0,.10);font-size:12px;color:#5f5f5a;max-width:100%;width:max-content;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transform-origin:left center}' +
  '#hdchat .ch-line[hidden]{display:none}' +
  '#hdchat .ch-line b{font-weight:600;color:var(--ui-primary,#2b2b29);overflow:hidden;text-overflow:ellipsis}' +
  '#hdchat .ch-line[data-stage="applied"] .ch-st,#hdchat .ch-line[data-stage="answered"] .ch-st{color:var(--ui-ok,#4f7d5f)}' +
  '#hdchat .ch-line[data-stage="decide"] .ch-st,#hdchat .ch-line[data-stage="unsent"] .ch-st{color:var(--ui-accent,#c2590a)}' +
  '#hdchat .ch-line.pulse{animation:hdChatPulse .6s ease-out}' +
  '@keyframes hdChatPulse{0%{transform:scale(1)}50%{transform:scale(1.02)}100%{transform:scale(1)}}' +
  '@media (prefers-reduced-motion: reduce){#hdchat .ch-line.pulse{animation:none}}' +
  '#hdchat .ch-box{background:#fff;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.16);padding:8px 8px 8px 10px}' +
  '#hdchat .ch-chips{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px}' +
  '#hdchat .ch-chip{display:inline-flex;align-items:center;gap:2px;max-width:240px;height:22px;padding:0 4px 0 8px;border-radius:999px;background:var(--ui-badge-soft,#E4E4DF);color:var(--ui-on-badge-soft,#3a3a37);font-size:12px;font-weight:600}' +
  '#hdchat .ch-chip.all{padding-right:8px;background:#F2F2EF;color:#6b6b66;font-weight:500}' +
  '#hdchat .ch-chip.el{background:#2b2b29;color:#fff}' +
  '#hdchat .ch-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#hdchat .ch-chip button{border:0;background:none;color:inherit;font:inherit;width:18px;height:18px;border-radius:999px;cursor:pointer;opacity:.7;line-height:1}' +
  '#hdchat .ch-chip button:hover{opacity:1;background:rgba(0,0,0,.12)}' +
  '#hdchat .ch-row{display:flex;align-items:flex-end;gap:6px}' +
  '#hdchat textarea{flex:1;min-width:0;border:0;outline:none;resize:none;font:inherit;font-size:14px;line-height:20px;height:20px;max-height:100px;padding:4px 0;background:none;color:inherit}' +
  '#hdchat .ch-send{flex:none;height:30px;padding:0 12px;border:0;border-radius:9px;background:var(--ui-primary,#2b2b29);color:#fff;font:600 13px system-ui,sans-serif;cursor:pointer}' +
  '#hdchat .ch-send:disabled{opacity:.35;cursor:default}' +
  'html body.has-chat #toast{bottom:var(--hd-chat-top,120px)}';

function mount(ctx) {
  var C = HD.chat, dismissed = {}, last = null, shownLine = null, chipSig = null, warned = {}, booted = false;
  var LKEY = ctx.key('hd-chat-last');
  var root = document.createElement('div');
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  root.id = 'hdchat'; root.setAttribute('role', 'form'); root.setAttribute('aria-label', 'AI 에게 요청');
  root.innerHTML = '<div class="ch-line" hidden aria-live="polite"><b class="ch-req"></b><span class="ch-st"></span></div>' +
    '<div class="ch-box"><div class="ch-chips" aria-label="요청 범위"></div><div class="ch-row">' +
    '<textarea rows="1" aria-label="요청 글"></textarea><button type="button" class="ch-send" disabled>보내기</button></div></div>';
  document.body.appendChild(root); document.body.classList.add('has-chat');
  var ta = root.querySelector('textarea'), btn = root.querySelector('.ch-send'), chipsEl = root.querySelector('.ch-chips'), lineEl = root.querySelector('.ch-line');
  ta.placeholder = C.PLACEHOLDER;

  function warnOnce(k, msg) { if (warned[k]) return; warned[k] = 1; console.warn('[hd] 대화창: ' + msg); }
  function selected() {
    if (typeof ctx.selected === 'function') return ctx.selected() || [];
    warnOnce('selected', 'ctx.selected 가 없어요 — 고른 카드는 .card.picked 로 읽어요');
    return Array.prototype.map.call(ctx.rowsEl.querySelectorAll('.card.picked'), function (c) { return c.dataset.id; });
  }
  function picked() {
    if (typeof ctx.picked === 'function') return ctx.picked();
    warnOnce('picked', 'ctx.picked 가 없어요 — 요소 칩 없이');
    return null;
  }
  function rawChips() { return C.chips({ids: selected(), titleOf: ctx.title, el: picked()}); }
  function chipsNow() { var raw = rawChips(); dismissed = C.prune(dismissed, raw); return C.visible(raw, dismissed); }

  function renderChips() {
    var list = chipsNow(), sig = JSON.stringify(list.map(function (c) { return [c.key, c.label]; }));
    if (sig === chipSig) return;
    chipSig = sig;
    chipsEl.innerHTML = list.length ? list.map(function (c) {
      return '<span class="ch-chip' + (c.kind === 'el' ? ' el' : '') + '" data-key="' + ctx.esc(c.key) + '" title="' + ctx.esc(c.label) + '"><span>' + ctx.esc(c.label) +
        '</span><button type="button" aria-label="' + ctx.esc(c.label) + ' 빼기">×</button></span>';
    }).join('') : '<span class="ch-chip all" title="고른 것이 없으면 모든 화면에 요청해요"><span>' + ctx.esc(C.ALL) + '</span></span>';
    chipsEl.dataset.scope = C.scope(list);
  }
  function busyOf() {
    var s = null;
    try { s = HD.busy ? HD.busy.load(ctx.store.getItem, ctx.key('hd-busy')) : null; } catch (e) { s = null; }   // 덮개 상태는 읽기만 — 못 읽으면 덮개 없이 말한다
    return function (screen) { return s && s.items ? s.items[screen] || null : null; };
  }
  function renderLine() {
    var inflight = !!(last && Date.now() - last.at < 20000);
    var l = C.line(last, function (id) { return ctx.notes.find(id) || null; }, busyOf(), inflight);
    if (!l) { lineEl.hidden = true; shownLine = null; return; }
    var key = l.req + '\n' + l.text;
    if (key === shownLine) return;
    shownLine = key;
    lineEl.hidden = false; lineEl.dataset.stage = l.stage;
    lineEl.querySelector('.ch-req').textContent = l.req;
    lineEl.querySelector('.ch-st').textContent = '· ' + l.text;
    lineEl.title = l.req + ' — ' + l.text;
    if (booted) { lineEl.classList.remove('pulse'); void lineEl.offsetWidth; lineEl.classList.add('pulse'); }   // 새 줄마다 한 번(움직임 줄이기면 CSS 가 끈다)
  }
  function place() {
    var dk = ctx.$('#dock'), right = innerWidth;
    if (dk && dk.offsetParent !== null) { var r = dk.getBoundingClientRect(); if (r.width && r.left > innerWidth / 2) right = r.left; }   // 도크를 가리지 않게 그 왼쪽 가운데
    var w = Math.min(560, right - 32);
    root.style.width = Math.max(240, w) + 'px';
    root.style.left = (right / 2) + 'px';
    var top = root.hidden || !root.offsetHeight ? 0 : innerHeight - root.getBoundingClientRect().top + 8;
    document.body.style.setProperty('--hd-chat-top', (top || 120) + 'px');   // 토스트는 대화창 위에
  }
  function grow() { ta.style.height = '20px'; ta.style.height = Math.min(100, ta.scrollHeight - 8 > 20 ? ta.scrollHeight - 8 : 20) + 'px'; btn.disabled = !ta.value.trim(); place(); }
  function render() { renderChips(); renderLine(); place(); }
  var tick = 0;
  function soon() { clearTimeout(tick); tick = setTimeout(render, 60); }

  function mkId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function firstScreen() { var c = ctx.rowsEl.querySelector('.card:not(.draft):not(.hid)'); return c ? c.dataset.id : null; }
  function send(text) {
    if (typeof ctx.sendNotes !== 'function') { warnOnce('send', 'ctx.sendNotes 가 없어요 — 보낼 수 없어요'); ctx.toast('대화창 보내기가 아직 연결되지 않았어요 — 메모 도구와 위쪽 [보내기]를 써 주세요'); return false; }
    var r = C.build(chipsNow(), text, {first: firstScreen(), titleOf: ctx.title}, mkId);
    if (!r.memos.length) { ctx.toast(r.why); return false; }
    var ok;
    try { ok = ctx.sendNotes(r.memos); }
    catch (e) { console.error('[hd] 대화창 보내기: ' + (e && e.message || e)); ctx.toast('보내지 못했어요 — ' + (e && e.message || e)); return false; }
    if (ok === false) { ctx.toast('보내는 중이에요 — 잠시 뒤 다시 보내 주세요'); return false; }
    last = C.record(text, r.memos, Date.now());
    try { ctx.local.setItem(LKEY, JSON.stringify(last)); } catch (e) {}   // 저장 공간이 꽉 차도 이 창의 상태 줄은 그대로 보인다
    render();
    return true;
  }

  (function load() {
    var p = C.parseLast(ctx.local.getItem(LKEY));
    if (p.bad) console.warn('[hd] 대화창: 마지막 요청 기록이 깨져 버렸어요');
    last = p.last;
  })();

  root.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 판 고르기 풀기·끌기로 새지 않게
  root.addEventListener('click', function (e) { e.stopPropagation(); });
  chipsEl.addEventListener('click', function (e) {
    var b = e.target.closest('button'), c = b && b.closest('.ch-chip[data-key]'); if (!c) return;
    dismissed[c.dataset.key] = 1; renderChips(); place(); ta.focus();
  });
  ta.addEventListener('input', grow);
  ta.addEventListener('keydown', function (e) {
    e.stopPropagation();                                   // 도구 키·Delete 가 판으로 가지 않게(입력 중)
    if (e.key === 'Escape') { ta.blur(); return; }
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing || e.keyCode === 229) return;
    e.preventDefault();
    if (send(ta.value)) { ta.value = ''; grow(); }
  });
  btn.addEventListener('click', function () { if (send(ta.value)) { ta.value = ''; grow(); } ta.focus(); });
  ['pointerup', 'keyup'].forEach(function (t) { addEventListener(t, soon, true); });
  addEventListener('message', soon);                       // 요소 고르기는 화면의 답(hd-hit) 뒤에 정해진다
  addEventListener('resize', place);
  setInterval(render, 1000);                               // 메모 상태·덮개는 다른 길(2초 읽기·답)로 바뀐다 — 47-4 SSE 가 오면 이벤트로
  render(); grow(); booted = true;               // 처음 그린 줄(새로고침 뒤)은 맥박 없이
  return {render: render, send: send, last: function () { return last; }};
}

HD.feature('chat', {needs: ['$', 'toast', 'esc', 'notes', 'local', 'store', 'key', 'title', 'rowsEl'], mount: mount});
})();
