/* View — 대화 창 틀(R53): 기록(#pTalk, view-chat-log)과 입력창(#hdchat, view-chat)을 창 하나(#hdtalk)에 담고 접힘·펼침·끌기·크기·붙이기/떼기만 한다.
   규칙(접힘↔펼침 · 판 끝 40px 붙기 판정 · 붙은 폭 · 붙기/떼기 의도)은 HD.talkWindow(Model), 떠 있는 창 자리 맞추기는 HD.popPlace.clamp(R58 — 함수 하나),
   자리의 진실은 도크 배치(dock.js, 키 hd-dock — ctx.dock.dispatch 로 의도만). 붙으면 #hdtalk 이 도크 패널 'talk' 로 도크 묶음 안에 들어가고(view-dock 이 옮김,
   혼자 있는 묶음이면 탭 줄 대신 이 머리 줄), 떠 있으면 이 파일이 몸(body)에 둔다.
   모양: 접힘 = 입력창만, 판 아래 가운데(예전 대화창 자리 규칙 — 탭 바 자리) + 위 끝 손잡이 알약 + 오른쪽 위 펼치기(작업 중인 턴이 있으면 점) ·
     펼침 = 머리 줄 36px(손잡이 · 대화 · 받는 곳 이름 흐리게 · 붙이기/떼기 · 접기 — 닫기 없음, 숨기기는 창 메뉴 '대화창') + 기록 + 입력창, 끌어 옮기기·크기 ·
     붙음 = 도크 높이 전체, 늘 펼침 — 크게 보기·Foundation·Components 탭에서도 그대로. 떠 있는 창은 크게 보기가 열리면 그동안 접힌 창으로 덮개 위에 뜬다(크게 보기 칩·sizeModal 은 view-chat·셸 그대로).
   끌기: 머리 줄(접힘이면 알약)을 끌면 따라오고, 판 왼쪽·오른쪽 끝 40px 안이면 그 쪽 도크 자리를 미리 보이고(#ldock.empty·#dock + '놓으면 왼쪽에 붙어요'),
     놓으면 붙는다. 붙은 창의 머리 줄을 끌면 떨어져 펼친 창으로 따라온다. 접힌 창은 끝이 아닌 곳에 놓으면 제자리(판 아래 가운데)로. 알약 누르기 = 펼치기.
   상태(주인 이 파일, 저장 안 함): 끄는 중인 것. 저장되는 배치는 모두 도크 상태(접힘/펼침·떠 있는 자리·크기·붙은 쪽·폭).
   오류 탐지: #hdtalk 이 없으면 [hd] 경고 + 기능 빠짐(입력창은 예전처럼 판 아래 혼자) · #pTalk 이 없으면 [hd] 경고 + 펼치기 없이 입력창만 ·
     #hdchat 이 없거나 입력창이 'hd-composer' 를 받지 않으면 [hd] 경고 · ctx.dock 이 없으면 [hd] 경고 + 접힌 창만(붙이기·펼치기 없음).
   HD.feature('talkWindow', {needs: ['$', 'warn']}) → {layout(), place()} — 셸은 도크 배치가 바뀔 때(onLayout) layout() 을 부른다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var IC = {
  grip: '<svg viewBox="0 0 12 16" aria-hidden="true"><g fill="currentColor"><circle cx="3" cy="3" r="1.3"/><circle cx="9" cy="3" r="1.3"/><circle cx="3" cy="8" r="1.3"/><circle cx="9" cy="8" r="1.3"/><circle cx="3" cy="13" r="1.3"/><circle cx="9" cy="13" r="1.3"/></g></svg>',
  dock: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="14" rx="2"/><path d="M10 5v14"/></svg>',
  pop: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-8 8"/><path d="M18 14v4a2 2 0 01-2 2H6a2 2 0 01-2-2V8a2 2 0 012-2h4"/></svg>',
  fold: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4l-6 6M14 5v5h5M4 20l6-6M10 19v-5H5"/></svg>',
  expand: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-6 6M10 20H4v-6M4 20l6-6"/></svg>'
};

var CSS =
  '#hdtalk{box-sizing:border-box;display:flex;flex-direction:column;min-height:0;font:13px system-ui,sans-serif;color:var(--ui-primary,#2b2b29)}' +
  '#hdtalk[hidden],body.no-chat #hdtalk,body.bare #hdtalk,html[data-hd-tab="reader"] #hdtalk{display:none}' +
  '#hdtalk .tw-head{flex:none;display:flex;align-items:center;gap:6px;box-sizing:border-box;height:36px;padding:0 6px 0 8px;border-bottom:1px solid #ECECE8;cursor:move;-webkit-user-select:none;user-select:none;touch-action:none}' +
  '#hdtalk .tw-grip{flex:none;width:10px;height:14px;color:#b5b5b0;display:grid;place-items:center}#hdtalk .tw-grip svg{width:8px;height:12px}' +
  '#hdtalk .tw-head b{flex:none;font-weight:600;font-size:13px}' +
  '#hdtalk .tw-agent{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--ui-muted,#8a8a85);font-size:12.5px}' +
  '#hdtalk .tw-sp{flex:1 1 auto}' +
  '#hdtalk .tw-ib{flex:none;width:26px;height:26px;padding:0;border:0;border-radius:6px;background:none;color:#6b6b66;display:grid;place-items:center;cursor:pointer}' +
  '#hdtalk .tw-ib:hover,#hdtalk .tw-ib:focus-visible{background:#F2F2EF;color:var(--ui-primary,#2b2b29)}' +
  '#hdtalk .tw-ib svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}' +
  '#hdtalk .tw-body{flex:1 1 auto;min-height:0;display:flex;flex-direction:column}' +
  '#hdtalk .tw-body>#pTalk{flex:1 1 auto;min-height:0;height:auto}' +
  '#hdtalk .tw-foot{flex:none;padding:0 8px 8px}' +
  '#hdtalk .tw-pill,#hdtalk .tw-expand,#hdtalk .tw-rs,#hdtalk .tw-rn{display:none}' +
  // 접힘 = 입력창만(판 아래 가운데) + 알약 + 펼치기
  '#hdtalk.tw-compact{position:fixed;z-index:24;transform:translateX(-50%)}' +
  '#hdtalk.tw-compact .tw-head,#hdtalk.tw-compact .tw-body{display:none}' +
  '#hdtalk.tw-compact .tw-foot{padding:0}' +
  '#hdtalk.tw-compact .tw-pill{display:block;position:absolute;top:0;left:50%;z-index:2;width:48px;height:12px;margin-left:-24px;padding:0;border:0;background:none;cursor:grab;touch-action:none}' +
  '#hdtalk.tw-compact .tw-pill::before{content:"";display:block;width:32px;height:4px;margin:3px auto 0;border-radius:2px;background:#d6d6d1}' +
  '#hdtalk.tw-compact .tw-pill:hover::before,#hdtalk.tw-compact .tw-pill:focus-visible::before{background:#a8a8a3}' +
  '#hdtalk.tw-compact .tw-expand{display:grid;position:absolute;top:6px;right:6px;z-index:2;width:22px;height:22px}' +
  '#hdtalk.tw-compact .tw-expand svg{width:13px;height:13px}' +
  '#hdtalk .tw-dot{position:absolute;top:1px;right:1px;width:7px;height:7px;border-radius:50%;background:var(--ui-primary,#2b2b29);box-shadow:0 0 0 2px #fff}' +
  '#hdtalk .tw-dot[hidden]{display:none}' +
  '#hdtalk:not(.tw-compact) #hdchat .ch-chips{padding-right:0}' +
  '#hdtalk.tw-compact #hdchat .ch-chips[hidden]+textarea{padding-right:28px}#hdtalk.tw-compact #hdchat .ch-att{padding-right:24px}' +
  '#hdtalk.tw-nolog .tw-expand,#hdtalk.tw-nolog .tw-pill{display:none!important}' +
  // 펼침(떠 있음) = 둥근 창 · 머리 줄 · 기록 · 입력창 · 크기 손잡이(오른쪽 아래·위 끝)
  '#hdtalk.tw-expanded{position:fixed;z-index:24;background:var(--ui-surface,#fff);border-radius:14px;box-shadow:0 0 0 1px rgba(0,0,0,.08),0 12px 40px rgba(0,0,0,.16);overflow:hidden}' +
  '#hdtalk.tw-expanded .tw-rs{display:block;position:absolute;right:0;bottom:0;z-index:3;width:16px;height:16px;cursor:nwse-resize}' +
  '#hdtalk.tw-expanded .tw-rn{display:block;position:absolute;left:16px;right:16px;top:0;z-index:3;height:5px;cursor:ns-resize}' +
  // 붙음 = 도크 칸 높이 전체
  '#hdtalk.tw-docked{position:relative;height:100%;background:var(--ui-surface,#fff)}' +
  '.dk-g:has(>.dk-body>#hdtalk)>.dk-body{overflow:hidden}' +
  '.dk-g>.dk-tabs:has(>.dk-tab[data-p="talk"]):not(:has(.dk-tab+.dk-tab)){display:none}' +   // 혼자 있는 묶음 = 탭 줄 대신 창 머리 줄(크게 보기로 창이 잠깐 떠도)
  '#hdtalk.tw-drag{transition:none;opacity:.97;z-index:30}#hdtalk.tw-drag .tw-head{cursor:grabbing}' +
  // 붙기 미리보기(판 끝 40px 안)
  'body.tw-snap-left #ldock.empty{display:flex;width:var(--tw-dw,360px);background:rgba(43,43,41,.06);border-right:2px solid #8a8a85}' +
  'body.tw-snap-left #ldock:not(.empty),body.tw-snap-right #dock{box-shadow:inset 0 0 0 2px #8a8a85}' +
  '.tw-hint{position:fixed;z-index:40;padding:6px 10px;border-radius:8px;background:#2b2b29;color:#fff;font:600 12px/16px system-ui,sans-serif;pointer-events:none;white-space:nowrap;box-shadow:0 4px 14px rgba(0,0,0,.18)}' +
  '.tw-hint[hidden]{display:none}' +
  'html body.tw-compact-on:not(.no-chat):not(.bare):not(.modal-open) #toast{bottom:var(--hd-chat-top,120px)}';

function mount(ctx) {
  var T = HD.talkWindow, P = HD.popPlace, $ = ctx.$, warned = {};
  function warnOnce(k, m) { if (warned[k]) return; warned[k] = 1; console.warn('[hd] 대화 창: ' + m); }
  var frame = $('#hdtalk');
  if (!frame) { warnOnce('frame', '창 자리(#hdtalk)가 없어요 — 입력창만 판 아래에'); return {}; }
  var log = $('#pTalk'), chat = $('#hdchat'), dock = ctx.dock || null;
  if (!log) warnOnce('log', '기록(#pTalk)이 없어요 — 펼치기 없이 입력창만');
  if (!dock || typeof dock.state !== 'function' || typeof dock.dispatch !== 'function') { warnOnce('dock', 'ctx.dock 이 없어요 — 붙이기·펼치기 없이 접힌 창만'); dock = null; }
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  frame.innerHTML = '<button type="button" class="tw-pill" title="끌어서 옮기기·붙이기 — 누르면 펼쳐요" aria-label="대화 창 펼치기"></button>' +
    '<button type="button" class="tw-ib tw-expand" title="펼치기 — 대화 기록과 함께" aria-label="대화 창 펼치기">' + IC.expand + '<span class="tw-dot" hidden></span></button>' +
    '<header class="tw-head"><span class="tw-grip">' + IC.grip + '</span><b>대화</b><span class="tw-agent"></span><span class="tw-sp"></span>' +
    '<button type="button" class="tw-ib tw-dock"></button><button type="button" class="tw-ib tw-fold" title="접기 — 입력창만" aria-label="대화 창 접기">' + IC.fold + '</button></header>' +
    '<div class="tw-body"></div><div class="tw-foot"></div><span class="tw-rn" title="끌어서 높이 조절"></span><span class="tw-rs" title="끌어서 크기 조절"></span>';
  frame.setAttribute('role', 'region'); frame.setAttribute('aria-label', '대화');
  var head = frame.querySelector('.tw-head'), body = frame.querySelector('.tw-body'), foot = frame.querySelector('.tw-foot');
  var dockB = frame.querySelector('.tw-dock'), foldB = frame.querySelector('.tw-fold'), expB = frame.querySelector('.tw-expand'), dot = frame.querySelector('.tw-dot');
  var agentEl = frame.querySelector('.tw-agent'), ai = $('#aichip');
  var hint = document.createElement('div'); hint.className = 'tw-hint'; hint.hidden = true; document.body.appendChild(hint);
  if (log) body.appendChild(log);
  if (!chat) warnOnce('chat', '입력창(#hdchat)이 없어요');
  else {
    var d = {host: foot, done: false};
    document.dispatchEvent(new CustomEvent('hd-composer', {detail: d}));
    if (!d.done) warnOnce('composer', '입력창(view-chat)이 hd-composer 를 받지 않아 창에 넣지 못했어요');
  }

  function state() { return dock ? dock.state() : null; }
  function absent() { return !dock || !log || (dock.absent ? dock.absent() : []).indexOf('talk') >= 0; }
  function modal() { return document.body.classList.contains('modal-open'); }
  function look() {                                  // 지금 그릴 모양: 'docked'|'expanded'|'compact' + 떠 있나
    var s = state();
    if (!s || absent()) return {m: 'compact', float: true};
    var m = T.mode(s);
    if (modal() && m !== 'docked') return {m: 'compact', float: true};   // 붙은 창은 크게 보기 옆에 그대로(10-30)
    return {m: m, float: m !== 'docked'};
  }
  function act(list, quiet) { if (dock) list.forEach(function (a) { dock.dispatch(a, quiet); }); }
  function rect(el) { return el && el.getClientRects().length ? el.getBoundingClientRect() : null; }
  function area() {                                  // 떠 있는 펼친 창의 판 칸(#dklayer — 도크 떠 있는 창과 같은 기준)
    var r = rect($('#dklayer')) || rect($('#screens'));
    return r || {left: 0, top: 0, width: innerWidth, height: innerHeight};
  }

  var cur = null, fixing = false;
  function layout() {
    var L = look();
    if (L.float && frame.parentNode !== document.body) document.body.appendChild(frame);
    if (!L.float && !frame.closest('.dk-body') && !fixing && dock && dock.render) { fixing = true; try { dock.render(); } finally { fixing = false; } return; }   // 크게 보기를 닫은 뒤 — 도크가 다시 넣게
    var cls = 'tw tw-' + L.m + (absent() ? ' tw-nolog' : '') + (drag ? ' tw-drag' : '');
    if (frame.className !== cls) frame.className = cls;
    document.body.classList.toggle('tw-compact-on', L.m === 'compact');
    var s = state();
    if (s) document.body.style.setProperty('--tw-dw', T.width(s.lw) + 'px');
    var docked = L.m === 'docked';
    dockB.innerHTML = docked ? IC.pop : IC.dock;
    dockB.title = docked ? '떼어 띄우기' : '왼쪽에 붙이기';
    dockB.setAttribute('aria-label', docked ? '대화 창 떼어 띄우기' : '대화 창 왼쪽에 붙이기');
    cur = L; place();
  }
  function place() {
    if (!cur || drag) return;
    if (cur.m === 'docked') { frame.style.cssText = ''; document.body.style.removeProperty('--hd-chat-top'); return; }
    if (cur.m === 'expanded') {
      var A = area(), b = P.clamp(T.box(state(), {w: A.width, h: A.height}), A.width, A.height, T.MIN);
      frame.style.cssText = 'left:' + (A.left + b.x) + 'px;top:' + (A.top + b.y) + 'px;width:' + b.w + 'px;height:' + b.h + 'px';
      document.body.style.removeProperty('--hd-chat-top');
      return;
    }
    // 접힘 = 판(#screens — 두 도크 사이) 아래 가운데. 탭 바(아래 왼쪽, data-need = 다 보이는 데 드는 폭 — view-tabs)는 이 창 앞에서 멈춘다 →
    // 가운데는 그대로, 폭만 줄여(최소 360) 자리를 준다. 그래도 겹치면(아주 좁은 창) 그때만 탭 위로 비킨다
    var pr = rect($('#screens')), L0 = pr ? pr.left : 0, right = pr ? pr.right : innerWidth;
    var tb = $('#ptabs'), tr = rect(tb);
    var need = tr && tr.width ? (+tb.dataset.need || 0) : 0;
    var W = right - L0, mid = L0 + W / 2, w = Math.min(640, W - 32);
    if (need) w = Math.min(w, Math.max(360, W - 2 * (tr.left - L0 + need + 12)));
    w = Math.max(240, w);
    var up = tr && tr.width && tr.right > mid - w / 2 ? innerHeight - tr.top + 8 : 12;
    frame.style.cssText = 'left:' + mid + 'px;bottom:' + up + 'px;width:' + w + 'px';
    var top = frame.offsetHeight ? innerHeight - frame.getBoundingClientRect().top + 8 : 0;
    document.body.style.setProperty('--hd-chat-top', (top || 120) + 'px');   // 토스트는 접힌 창 위에
  }

  /* ---------- 단추 ---------- */
  function expand() { var s = state(); if (s) act(T.toggle(s)); }
  expB.addEventListener('click', function (e) { e.stopPropagation(); if (absent()) return; if (T.mode(state()) === 'compact') expand(); });
  foldB.addEventListener('click', function (e) {
    e.stopPropagation(); var s = state(); if (!s) return;
    if (T.mode(s) === 'docked') act(T.undock(s, null, 'compact')); else act(T.toggle(s));
  });
  dockB.addEventListener('click', function (e) {
    e.stopPropagation(); var s = state(); if (!s) return;
    if (T.mode(s) === 'docked') act(T.undock(s, null, 'expanded')); else act(T.dock(s, 'left'));
  });
  frame.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 판 고르기 풀기·끌기로 새지 않게
  frame.addEventListener('click', function (e) { e.stopPropagation(); });

  /* ---------- 끌기: 머리 줄·알약(옮기기 · 붙이기 · 떼기) · 크기 ---------- */
  var drag = null;
  function board() { var r = rect($('#screens')); return r ? {left: r.left, right: r.right} : {left: 0, right: innerWidth}; }
  function preview(side, e) {
    var b = document.body.classList;
    b.toggle('tw-snap-left', side === 'left'); b.toggle('tw-snap-right', side === 'right');
    if (!side) { hint.hidden = true; return; }
    hint.textContent = side === 'left' ? '놓으면 왼쪽에 붙어요' : '놓으면 오른쪽에 붙어요';
    hint.hidden = false;
    var zone = side === 'left' ? rect($('#ldock')) : rect($('#dock')), fr = frame.getBoundingClientRect();
    var top = Math.max(zone ? zone.top + 12 : 60, fr.top - 44);
    hint.style.top = top + 'px';
    hint.style.left = side === 'left' ? ((zone ? zone.left : 0) + 12) + 'px' : Math.max(8, (zone ? zone.right : innerWidth) - hint.offsetWidth - 12) + 'px';
  }
  function startDrag(e, kind) {
    if (e.button !== 0 || !dock || absent()) return;
    e.preventDefault();
    var r = frame.getBoundingClientRect();
    drag = {kind: kind, x0: e.clientX, y0: e.clientY, r: r, m: cur ? cur.m : 'compact', moved: false, gx: e.clientX - r.left, gy: e.clientY - r.top};
  }
  head.addEventListener('pointerdown', function (e) { if (e.target.closest('button')) return; startDrag(e, 'move'); });
  frame.querySelector('.tw-pill').addEventListener('pointerdown', function (e) { startDrag(e, 'move'); });
  frame.querySelector('.tw-rs').addEventListener('pointerdown', function (e) { startDrag(e, 'se'); });
  frame.querySelector('.tw-rn').addEventListener('pointerdown', function (e) { startDrag(e, 'n'); });
  addEventListener('pointermove', function (e) {
    var z = drag; if (!z) return;
    var dx = e.clientX - z.x0, dy = e.clientY - z.y0;
    if (!z.moved && Math.abs(dx) + Math.abs(dy) < 5) return;
    if (!z.moved) {
      z.moved = true; frame.classList.add('tw-drag');
      if (z.kind === 'move' && z.m === 'docked') {   // 붙은 창 머리 줄을 끌면 떨어져 펼친 창으로 따라온다
        var s = state(), w = T.BOX.w, h = Math.min(T.BOX.h, Math.round(z.r.height));
        z.gx = Math.min(z.gx, w - 60);
        drag = null; act(T.undock(s, {x: 0, y: 0, w: w, h: h}, 'expanded'), true); drag = z;
        z.m = 'expanded'; z.r = {left: e.clientX - z.gx, top: e.clientY - z.gy, width: w, height: h};
        z.x0 = e.clientX; z.y0 = e.clientY; dx = dy = 0;
        frame.classList.add('tw-drag');
      }
    }
    if (z.kind === 'move') {
      if (z.m === 'compact') frame.style.transform = 'translate(calc(-50% + ' + dx + 'px),' + dy + 'px)';
      else {                                         // 끄는 동안도 창 안으로(떠 있는 창 자리 함수 하나 — R58)
        var c = P.clamp({x: z.r.left + dx, y: z.r.top + dy, w: z.r.width, h: z.r.height}, innerWidth, innerHeight, T.MIN);
        frame.style.cssText = 'left:' + c.x + 'px;top:' + c.y + 'px;width:' + c.w + 'px;height:' + c.h + 'px';
      }
      z.side = T.snap(e.clientX, board());
      preview(z.side, e);
    } else if (z.kind === 'se') {
      frame.style.width = Math.max(T.MIN.w, z.r.width + dx) + 'px'; frame.style.height = Math.max(T.MIN.h, z.r.height + dy) + 'px';
    } else if (z.kind === 'n') {
      var nh = Math.max(T.MIN.h, z.r.height - dy);
      frame.style.top = (z.r.top + z.r.height - nh) + 'px'; frame.style.height = nh + 'px';
    }
  });
  addEventListener('pointerup', function () {
    var z = drag; if (!z) return; drag = null;
    frame.classList.remove('tw-drag'); preview(null);
    if (!z.moved) { if (z.kind === 'move' && z.m === 'compact') expand(); return; }   // 알약 누르기 = 펼치기
    var s = state();
    frame.style.transform = '';
    if (z.kind === 'move' && z.side) { act(T.dock(s, z.side)); layout(); return; }
    if (z.m === 'compact') { layout(); return; }     // 접힌 창은 끝이 아니면 제자리(판 아래 가운데)
    var A = area(), fr = frame.getBoundingClientRect();
    var b = P.clamp({x: fr.left - A.left, y: fr.top - A.top, w: fr.width, h: fr.height}, A.width, A.height, T.MIN);
    var i = T.fi(s);
    if (i >= 0) act([{type: 'float', fi: i, x: b.x, y: b.y, w: b.w, h: b.h}, {type: 'talk', auto: false}]);
    layout();
  });

  /* ---------- 받는 곳 이름 · 작업 중 점 ---------- */
  function renderAgent() {
    if (!ai) { agentEl.textContent = ''; return; }
    var on = ai.classList.contains('on') && !ai.hidden, t = ai.textContent || '', i = t.indexOf(' · ');
    agentEl.textContent = on ? (i >= 0 ? t.slice(i + 3) : t) : '';
  }
  function renderDot() {
    var run = !!(log && log.querySelector('.tk-turn[data-state="running"]'));
    if (dot.hidden === run) dot.hidden = !run;
    var t = run ? '펼치기 — AI 가 작업 중이에요' : '펼치기 — 대화 기록과 함께';
    if (expB.title !== t) expB.title = t;
  }
  if (ai && window.MutationObserver) new MutationObserver(renderAgent).observe(ai, {childList: true, characterData: true, subtree: true, attributes: true});
  if (log && window.MutationObserver) new MutationObserver(renderDot).observe(log, {childList: true, subtree: true, attributes: true, attributeFilter: ['data-state']});
  if (window.MutationObserver) new MutationObserver(function () { if (!drag && (!cur || cur.m !== look().m)) layout(); })
    .observe(document.body, {attributes: true, attributeFilter: ['class']});   // 크게 보기 열고 닫기
  addEventListener('resize', place);
  var tb = $('#ptabs');
  if (tb && window.ResizeObserver) new ResizeObserver(place).observe(tb);
  if (chat && window.ResizeObserver) new ResizeObserver(function () { if (cur && cur.m === 'compact') place(); }).observe(chat);   // 입력창이 자라면 토스트 자리도
  setTimeout(function () { var t2 = $('#ptabs'); if (t2 && t2 !== tb && window.ResizeObserver) new ResizeObserver(place).observe(t2); place(); }, 0);   // 탭은 늦게 실린다
  renderAgent(); renderDot(); layout();
  return {layout: layout, place: place};
}

HD.feature('talkWindow', {needs: ['$', 'warn'], mount: mount});
})();
