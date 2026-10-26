/* View — 하단 대화창(S1): 판 아래 가운데 입력창 · 고른 카드·요소 칩(×) · 마지막 요청 상태 한 줄. 규칙(칩·범위·메모 초안·상태 말)은 HD.chat(Model).
   모양(S1c, tasks/52-composer '정한 모양'): 카드 한 장 = 칩 줄(고른 것이 있을 때만, 3개 넘으면 앞 2개 + 외 N개 — HD.chat.fold) · 입력칸(카드 폭 전체, 32→200px 뒤 얇은 스크롤)
     · 도구 줄 28px(받는 곳 알약 왼쪽 · 둥근 보내기 오른쪽). 범위는 칩이 아니라 입력 안내 글(HD.chat.placeholder). 숨김 ⌄ = 카드 오른쪽 위, 올리거나 포커스일 때만. 상태 = 펼침 여부(저장 안 함).
   상태 = 지운 칩 표시(저장하지 않음) · 마지막 요청 {text, ids, at}(ctx.local 키 hd-chat-last:<해시>, 주인 이 파일). 메모·보내기는 셸 것 — ctx.sendNotes(list) 하나로만 나간다
   (위쪽 [보내기]와 같은 길: 도우미가 있으면 /api/forward, 없으면 복사). 고른 것은 ctx.selected()·ctx.pickedAll()(판에서 고른 요소 모두, R19 — 비면 ctx.picked() 하나) 로 읽기만, 덮개 상태(hd-busy)도 읽기만.
   Enter = 보내기 · Shift+Enter = 줄바꿈(한글 조합 중 Enter 는 무시) · Esc = 입력창에서 나가기. 크게 보기·다른 탭·읽기만 탭·Tab(bare)에서는 숨긴다.
   보이기 설정(S1b)의 주인은 dock.js(창 메뉴 '대화창', 키 hd-dock) — 숨기기 단추는 document 에 의도 'hd-chrome' {part:'chat', on:false} 만 보내고, 몸의 no-chat 표시로 숨는다.
   받는 곳 알약(S1b): 위쪽 #aichip 의 글을 그대로 비춰 보이고(읽기만 — 주인은 view-sync), 누르면 의도 'hd-agent-pick' {anchor} → view-agents 가 같은 메뉴를 연다.
   대화 패널 안(S3): 의도 'hd-composer' {host}(view-chat-log — 대화 패널이 보이면 그 아래 칸, 아니면 null)를 받아 같은 #hdchat 을 그리로 옮긴다(.docked —
     상태 줄·숨김 ⌄ 은 감춤, 진행은 패널이 보인다, '대화창' 숨김 설정은 떠 있는 창에만). 보낸 뒤 의도 'hd-chat-sent' {text, chips, screens, notes, agent} → 대화 패널이 기록.
   자리: 판(#screens — 두 도크 사이) 아래 가운데. 프로젝트 탭 바(아래 왼쪽, view-tabs 가 이 창 앞에서 멈춤)가 좁은 창에서 최소 폭이라 겹칠 때만 그 위로 올린다.
   진행 줄(S2, 47-4b): document 'hd-event'(view-live)를 HD.chat.progress 로 — 보낸 요청 화면의 claim·AI 쓰기·release 를 줄 하나(마지막 상태)로. 저장하지 않음(새로고침 = 메모 상태 줄).
   받는 곳(47-5b): 알약 점은 #aichip[data-state](view-presence — 접속 중 초록 · 자리 비움 회색)를 따른다. 진행 줄은 이 요청의 메모 id 로 request.sent(via) →
     agent.progress(진행 글) → agent.reply 를 따라가고, 받는 곳 이름은 보낼 때의 알약 글(HD.chat.line opt.agentName).
   첨부 이미지(R22): 카드 .ch-box 가 [data-hd-attach] 상자(칩 자리 = 카드 맨 위 · 📎 = 보내기 앞) — 붙이기·저장·썸네일은 등록부 기능 attach(view-attach), 여기서는 의도만:
     보낼 때 'hd-attach-get' → 글 끝에 '첨부 이미지: <절대 경로>' 줄(HD.attach.withText) + 메모마다 attach 칸 · 올리는 중이면 토스트하고 보내지 않음 · 보낸 뒤 'hd-attach-set' [] ·
     'hd-attach-changed' 를 들어 글 없이 이미지만 있어도 보내기를 켠다. 대화 패널 안(docked)도 같은 요소라 같다.
   판 노트(R25): 셸 ctx.boardNotes() → 고른 판 메모 [{id, text, x, y, w, h}](판 좌표 — 주인은 view-board-notes, 읽기만)마다 [노트 "글" ×] 칩(HD.chat.chips notes).
     가까운 화면 = HD.chat.nearest(메모 상자, 카드 상자 — 둘 다 판 좌표, 메모 자리·크기가 바뀔 때만 다시 잼). 보내면 요청 글 끝 '노트:' 줄(HD.chat.build) — 글이 비어도 노트가 있으면 보낸다.
     ctx.boardNotes 가 없으면(옛 셸) [hd] 경고 한 번 + 노트 칩 없이.
   HD.feature('chat', {needs: ['$', 'toast', 'esc', 'notes', 'local', 'store', 'key', 'title', 'rowsEl']}) → {render(), send(text), last()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '#hdchat{position:fixed;bottom:12px;left:50%;z-index:24;width:640px;max-width:calc(100vw - 32px);transform:translateX(-50%);font:13px system-ui,sans-serif;color:var(--ui-primary,#2b2b29)}' +
  '#hdchat[hidden],body.no-chat #hdchat:not(.docked),body.modal-open #hdchat,body.bare #hdchat,body:not([data-tab="screens"]) #hdchat,html[data-hd-tab="reader"] #hdchat{display:none}' +
  // 상태 줄(진행 줄 S2) — 카드 위 20px 한 줄, 말이 없으면 숨김(S1c)
  '#hdchat .ch-line{display:flex;align-items:center;gap:6px;box-sizing:border-box;height:20px;margin:0 8px 4px;padding:2px 8px;border-radius:6px;background:rgba(255,255,255,.94);box-shadow:0 1px 4px rgba(0,0,0,.08);font-size:12px;line-height:16px;color:var(--ui-badge,#5f5f5a);max-width:calc(100% - 16px);width:max-content;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transform-origin:left center}' +
  '#hdchat .ch-line[hidden]{display:none}' +
  '#hdchat .ch-line b{font-weight:600;color:var(--ui-primary,#2b2b29);overflow:hidden;text-overflow:ellipsis}' +
  '#hdchat .ch-line[data-stage="applied"] .ch-st,#hdchat .ch-line[data-stage="answered"] .ch-st{color:var(--ui-ok,#4f7d5f)}' +
  '#hdchat .ch-line[data-stage="decide"] .ch-st,#hdchat .ch-line[data-stage="unsent"] .ch-st{color:var(--ui-accent,#c2590a)}' +
  '#hdchat .ch-line.pulse{animation:hdChatPulse .6s ease-out}' +
  '@keyframes hdChatPulse{0%{transform:scale(1)}50%{transform:scale(1.02)}100%{transform:scale(1)}}' +
  '@media (prefers-reduced-motion: reduce){#hdchat .ch-line.pulse{animation:none}#hdchat .ch-box,#hdchat .ch-hide{transition:none}}' +
  // 카드 한 장(S1c): 칩 줄(고른 것이 있을 때만) · 입력칸(카드 폭 전체) · 도구 줄 28px(받는 곳 알약 왼쪽 · 둥근 보내기 오른쪽). 빈 높이 8+32+6+28+8 = 82
  '#hdchat .ch-box{position:relative;display:flex;flex-direction:column;gap:6px;padding:8px;background:var(--ui-surface,#fff);border-radius:16px;box-shadow:0 0 0 1px rgba(0,0,0,.08),0 4px 20px rgba(0,0,0,.08);transition:box-shadow .15s}' +
  '#hdchat .ch-box:focus-within{box-shadow:0 0 0 1px rgba(0,0,0,.16),0 4px 20px rgba(0,0,0,.08)}' +
  '#hdchat .ch-hide{position:absolute;top:6px;right:6px;z-index:1;width:20px;height:20px;padding:0;border:0;border-radius:6px;background:none;color:var(--ui-muted,#8a8a85);cursor:pointer;display:grid;place-items:center;opacity:0;transition:opacity .12s}' +
  '#hdchat .ch-box:hover .ch-hide,#hdchat .ch-box:focus-within .ch-hide{opacity:1}' +
  '#hdchat .ch-hide:hover{background:#F2F2EF;color:var(--ui-primary,#2b2b29)}' +
  '#hdchat .ch-hide svg{width:12px;height:12px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}' +
  '#hdchat .ch-chips{display:flex;flex-wrap:wrap;align-content:flex-start;gap:4px;max-height:48px;overflow-y:auto;scrollbar-width:thin;padding-right:24px}' +
  '#hdchat .ch-chips[hidden]{display:none}' +
  '#hdchat .ch-chip{display:inline-flex;align-items:center;gap:2px;max-width:240px;height:22px;box-sizing:border-box;padding:0 4px 0 8px;border-radius:999px;background:var(--ui-badge-soft,#E4E4DF);color:var(--ui-on-badge-soft,#3a3a37);font-size:12px;font-weight:600}' +
  '#hdchat .ch-chip.el{background:#2b2b29;color:#fff}' +
  '#hdchat .ch-chip.note{background:#fff7c2;color:#5a4b00;box-shadow:inset 0 0 0 1px #eadb85}' +
  '#hdchat .ch-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#hdchat .ch-chip button{border:0;background:none;color:inherit;font:inherit;width:18px;height:18px;border-radius:999px;cursor:pointer;opacity:.7;line-height:1}' +
  '#hdchat .ch-chip button:hover{opacity:1;background:rgba(0,0,0,.12)}' +
  '#hdchat .ch-chip.ch-more{padding:0 8px;border:0;background:#F2F2EF;color:#6b6b66;font:500 12px system-ui,sans-serif;cursor:pointer}' +
  '#hdchat .ch-chip.ch-more:hover{background:var(--ui-badge-soft,#E4E4DF);color:var(--ui-primary,#2b2b29)}' +
  '#hdchat textarea{display:block;width:100%;box-sizing:border-box;height:32px;min-height:32px;max-height:200px;margin:0;padding:6px;border:0;outline:none;resize:none;font:inherit;font-size:14px;line-height:20px;background:none;color:inherit;overflow-y:hidden;scrollbar-width:thin;scrollbar-color:#cfcfca transparent}' +
  '#hdchat .ch-chips[hidden]+textarea{padding-right:26px}' +             // 칩 줄이 없으면 첫 줄 = 입력칸 — 숨김 ⌄ 자리를 비운다
  '#hdchat textarea::placeholder{color:var(--ui-muted,#8a8a85)}' +
  '#hdchat .ch-tools{display:flex;align-items:center;gap:6px;height:28px}' +
  '#hdchat .ch-agent{flex:0 1 auto;min-width:0;display:inline-flex;align-items:center;gap:6px;max-width:180px;height:26px;padding:0 8px;border:0;border-radius:8px;background:none;color:#6b6b66;font:500 12px system-ui,sans-serif;cursor:pointer}' +
  '#hdchat .ch-agent[hidden]{display:none}' +
  '#hdchat .ch-agent:hover,#hdchat .ch-agent[aria-expanded="true"]{background:#F2F2EF;color:#2b2b29}' +
  '#hdchat .ch-agent i{flex:none;width:7px;height:7px;border-radius:50%;background:#b5b5b0}' +
  '#hdchat .ch-agent.on{color:var(--ui-primary,#2b2b29)}#hdchat .ch-agent.on i{background:var(--ui-ok,#4f7d5f)}' +
  '#hdchat .ch-agent.on[data-state="away"] i{background:#b5b5b0}' +
  '#hdchat .ch-agent svg{flex:none;width:12px;height:12px;margin-left:-2px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;opacity:.7}' +
  '#hdchat .ch-agent span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#hdchat .ch-send{flex:none;margin-left:auto;width:28px;height:28px;padding:0;border:0;border-radius:50%;background:var(--ui-primary,#2b2b29);color:#fff;display:grid;place-items:center;cursor:pointer}' +
  '#hdchat .ch-send:disabled{background:#E4E4DF;color:var(--ui-muted,#8a8a85);cursor:default}' +
  '#hdchat .ch-att{padding-right:24px}' +
  '#hdchat.docked .ch-att{padding-right:0}' +
  '#hdchat .ch-clip{flex:none;margin-left:auto;width:28px;height:28px;padding:0;border:0;border-radius:8px;background:none;color:#6b6b66;display:grid;place-items:center;cursor:pointer}' +
  '#hdchat .ch-clip:hover{background:#F2F2EF;color:var(--ui-primary,#2b2b29)}' +
  '#hdchat .ch-clip svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}' +
  '#hdchat .ch-clip+.ch-send{margin-left:0}' +
  '#hdchat .ch-send svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}' +
  'html body.has-chat:not(.no-chat):not(.bare):not(.modal-open):not(.chat-docked) #toast{bottom:var(--hd-chat-top,120px)}' +
  // 대화 패널 안(S3): 같은 카드, 패널 폭 · 패널 아래 — 상태 줄(패널이 진행을 보인다)·숨김 ⌄(패널을 닫으면 된다)은 감춘다
  '#hdchat.docked{position:static;transform:none;width:auto!important;max-width:none;z-index:auto}' +
  '#hdchat.docked .ch-line,#hdchat.docked .ch-hide{display:none}' +
  '#hdchat.docked .ch-chips[hidden]+textarea{padding-right:6px}' +
  '#hdchat.docked textarea::placeholder{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}';   // 좁은 패널에서 안내 글이 두 줄로 잘리지 않게

function mount(ctx) {
  var C = HD.chat, prog = null, dismissed = {}, open = false, last = null, shownLine = null, chipSig = null, warned = {}, booted = false, tbSeen = false;
  var LKEY = ctx.key('hd-chat-last');
  var root = document.createElement('div');
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  root.id = 'hdchat'; root.setAttribute('role', 'form'); root.setAttribute('aria-label', 'AI 에게 요청');
  root.innerHTML = '<div class="ch-line" hidden aria-live="polite"><b class="ch-req"></b><span class="ch-st"></span></div>' +
    '<div class="ch-box" data-hd-attach="chat"><button type="button" class="ch-hide" title="대화창 숨기기 — 창 메뉴에서 다시 보여요" aria-label="대화창 숨기기"><svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></button>' +
    '<div class="ch-att hd-att" data-hd-attach-slot hidden aria-label="첨부 이미지"></div>' +
    '<div class="ch-chips" aria-label="요청 범위" hidden></div>' +
    '<textarea rows="1" aria-label="요청 글"></textarea>' +
    '<div class="ch-tools"><button type="button" class="ch-agent" hidden aria-haspopup="menu" aria-expanded="false" aria-controls="amenu"><i></i><span></span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>' +
    '<button type="button" class="ch-clip" data-hd-attach-pick aria-label="이미지 첨부" title="이미지 첨부 — 붙여넣기(Ctrl+V)·끌어 놓기도 돼요"><svg viewBox="0 0 24 24"><path d="M21 11.5l-8.6 8.6a5 5 0 0 1-7.1-7.1l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9"/></svg></button>' +
    '<button type="button" class="ch-send" disabled aria-label="보내기" title="보내기 (Enter)"><svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></svg></button></div></div>';
  document.body.appendChild(root); document.body.classList.add('has-chat');
  var ta = root.querySelector('textarea'), btn = root.querySelector('.ch-send'), chipsEl = root.querySelector('.ch-chips'), lineEl = root.querySelector('.ch-line');
  var boxEl = root.querySelector('.ch-box'), attN = 0, noteN = 0;
  var hideB = root.querySelector('.ch-hide'), agentB = root.querySelector('.ch-agent'), ai = ctx.$('#aichip');
  ta.placeholder = C.placeholder([]);

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
  function pickedEls() {                                 // 고른 요소 모두(R19 — 판 Shift+누르기) · 칸이 없으면 요소 막대의 하나
    if (typeof ctx.pickedAll === 'function') { var a = ctx.pickedAll() || []; if (a.length) return a; }
    var p = picked(); return p ? [p] : [];
  }
  var nearBy = {};                                       // 판 노트 id → {k: 자리 열쇠, id: 가까운 카드}(메모 자리·크기가 바뀔 때만 다시 잼)
  function boardNotes() {                                // 고른 판 메모(R25) — 주인은 view-board-notes, 셸이 ctx.boardNotes 로 건넨다(읽기만)
    if (typeof ctx.boardNotes !== 'function') { warnOnce('bnotes', 'ctx.boardNotes 가 없어요 — 노트 칩 없이'); return []; }
    var list = ctx.boardNotes() || [];
    return list.map(function (n) {
      var k = [n.x, n.y, n.w, n.h].join(':'), c = nearBy[n.id];
      if (!c || c.k !== k) nearBy[n.id] = c = {k: k, id: nearCard(n)};
      return {id: n.id, text: n.text, near: c.id};
    });
  }
  function nearCard(n) {                                 // 메모 상자와 가장 가까운 카드(판 좌표 — 확대·이동과 무관)
    var stage = ctx.$('#stage'), v = ctx.view && ctx.view.get ? ctx.view.get() : null;
    if (!stage || !v || !v.z) return null;
    var r = stage.getBoundingClientRect(), z = v.z;
    var cards = Array.prototype.map.call(ctx.rowsEl.querySelectorAll('.card:not(.hid):not(.draft)'), function (c) {
      var b = (c.querySelector('.phone') || c).getBoundingClientRect();
      return {id: c.dataset.id, x: (b.left - r.left) / z, y: (b.top - r.top) / z, w: b.width / z, h: b.height / z};
    }).filter(function (c) { return c.w > 0; });
    return C.nearest({x: +n.x || 0, y: +n.y || 0, w: +n.w || 0, h: +n.h || 60}, cards);
  }
  function rawChips() { return C.chips({ids: selected(), titleOf: ctx.title, els: pickedEls(), notes: boardNotes()}); }
  function chipsNow() { var raw = rawChips(); dismissed = C.prune(dismissed, raw); return C.visible(raw, dismissed); }

  function renderChips() {                               // 칩 줄(S1c): 고른 것이 있을 때만 · 3개를 넘으면 앞 2개 + '외 N개'(누르면 펼침) · 범위는 입력 안내 글로
    var list = chipsNow();
    if (list.length <= 3) open = false;                    // 접을 것이 없어지면 다음 고르기는 다시 접힌 채로
    var f = C.fold(list, open), sig = JSON.stringify([f.more, f.shown.map(function (c) { return [c.key, c.label]; })]);
    if (sig === chipSig) return;
    chipSig = sig;
    chipsEl.innerHTML = f.shown.map(function (c) {
      return '<span class="ch-chip' + (c.kind === 'el' ? ' el' : c.kind === 'note' ? ' note' : '') + '" data-key="' + ctx.esc(c.key) + '" title="' + ctx.esc(c.label) + '"><span>' + ctx.esc(c.label) +
        '</span><button type="button" aria-label="' + ctx.esc(c.label) + ' 빼기">×</button></span>';
    }).join('') + (f.more ? '<button type="button" class="ch-chip ch-more" aria-expanded="false" title="고른 것 모두 보기">외 ' + f.more + '개</button>' : '');
    chipsEl.hidden = !list.length;
    noteN = list.filter(function (c) { return c.kind === 'note'; }).length;   // 노트만 있어도 보내기를 켠다
    btn.disabled = !ta.value.trim() && !attN && !noteN;
    chipsEl.dataset.scope = C.scope(list);
    ta.placeholder = C.placeholder(list);
  }
  function busyOf() {
    var s = null;
    try { s = HD.busy ? HD.busy.load(ctx.store.getItem, ctx.key('hd-busy')) : null; } catch (e) { s = null; }   // 덮개 상태는 읽기만 — 못 읽으면 덮개 없이 말한다
    return function (screen) { return s && s.items ? s.items[screen] || null : null; };
  }
  function renderLine() {
    var inflight = !!(last && Date.now() - last.at < 20000);
    var l = C.line(last, function (id) { return ctx.notes.find(id) || null; }, busyOf(), inflight, {progress: prog && prog.p, titleOf: ctx.title,
      agentName: function (id) { return prog && prog.name && (!prog.agent || prog.agent === id) ? prog.name : null; }});
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
  var docked = false;
  function place() {
    if (docked) { root.style.width = root.style.left = root.style.bottom = ''; document.body.style.removeProperty('--hd-chat-top'); return; }   // 패널 안 = 패널이 자리를 정한다
    var pane = ctx.$('#screens'), pr = pane && pane.getClientRects().length ? pane.getBoundingClientRect() : null;
    var L = pr ? pr.left : 0, right = pr ? pr.right : innerWidth;   // 판(두 도크 사이)의 가운데 — 왼쪽 도크(S3)가 있어도
    // 탭 바(아래 왼쪽, data-need = 다 보이는 데 드는 폭 — view-tabs)는 이 창 앞에서 멈춘다 → 가운데는 그대로, 폭만 줄여(최소 360) 탭 자리를 준다.
    // 그래도 겹치면(아주 좁은 창) 그때만 탭 위로 비킨다
    var tb = ctx.$('#ptabs'), b = tb && tb.getClientRects().length ? tb.getBoundingClientRect() : null;
    if (tb && window.ResizeObserver && !tbSeen) { tbSeen = true; new ResizeObserver(function () { place(); }).observe(tb); }   // 탭은 늦게 실린다
    var need = b && b.width ? (+tb.dataset.need || 0) : 0;
    var W = right - L, mid = L + W / 2;
    var w = Math.min(640, W - 32);
    if (need) w = Math.min(w, Math.max(360, W - 2 * (b.left - L + need + 12)));
    root.style.width = Math.max(240, w) + 'px';
    root.style.left = mid + 'px';
    root.style.bottom = (b && b.width && b.right > mid - root.getBoundingClientRect().width / 2 ? innerHeight - b.top + 8 : 12) + 'px';
    var top = root.hidden || !root.offsetHeight ? 0 : innerHeight - root.getBoundingClientRect().top + 8;
    document.body.style.setProperty('--hd-chat-top', (top || 120) + 'px');   // 토스트는 대화창 위에
  }
  function grow() {                                       // 32px(한 줄) → 줄마다 +20 → 200px 뒤 스크롤(얇은 막대, S1c)
    ta.style.height = '32px';
    var h = ta.scrollHeight;
    ta.style.height = Math.min(200, Math.max(32, h)) + 'px';
    ta.style.overflowY = h > 200 ? 'auto' : 'hidden';
    btn.disabled = !ta.value.trim() && !attN && !noteN; place();
  }
  function renderAgent() {                                // 위쪽 받는 곳 칩(#aichip)을 그대로 비춘다 — 진실은 view-sync(도우미 attach) 하나
    if (!ai) { agentB.hidden = true; return; }
    var on = ai.classList.contains('on'), t = ai.textContent || '', i = t.indexOf(' · '), label = on ? (i >= 0 ? t.slice(i + 3) : t) : (t || '받는 곳 없음');
    agentB.hidden = ai.hidden;
    agentB.classList.toggle('on', on);
    if (on && ai.dataset.state) agentB.dataset.state = ai.dataset.state; else delete agentB.dataset.state;   // 접속 상태(view-presence)
    agentB.querySelector('span').textContent = label;
    agentB.title = ai.title || '';
    agentB.setAttribute('aria-label', '받는 곳: ' + label + ' — 바꾸기');
  }
  function render() { renderChips(); renderLine(); place(); }
  var tick = 0;
  function soon() { clearTimeout(tick); tick = setTimeout(render, 60); }

  function mkId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function firstScreen() { var c = ctx.rowsEl.querySelector('.card:not(.draft):not(.hid)'); return c ? c.dataset.id : null; }
  function att(type, items) {                             // 첨부 상자 의도(view-attach) — 그 기능이 없으면 done=false, 첨부 없음
    var d = {items: items || [], busy: 0, done: false};
    boxEl.dispatchEvent(new CustomEvent(type, {bubbles: true, detail: d}));
    return d;
  }
  function send(text) {
    if (typeof ctx.sendNotes !== 'function') { warnOnce('send', 'ctx.sendNotes 가 없어요 — 보낼 수 없어요'); ctx.toast('대화창 보내기가 아직 연결되지 않았어요 — 메모 도구와 위쪽 [보내기]를 써 주세요'); return false; }
    var a = att('hd-attach-get');
    if (a.busy) { ctx.toast('이미지를 올리는 중이에요 — 끝나면 보내 주세요'); return false; }
    var items = a.items || [], full = HD.attach.withText(text, items);
    var chipList = chipsNow(), notesN = chipList.filter(function (c) { return c.kind === 'note'; }).length;
    var r = C.build(chipList, full, {first: firstScreen(), titleOf: ctx.title}, mkId);
    if (!r.memos.length) { ctx.toast(r.why); return false; }
    if (items.length) r.memos.forEach(function (m) { m.attach = items.slice(); });   // 메모가 첨부 목록을 지닌다
    var ok;
    try { ok = ctx.sendNotes(r.memos); }
    catch (e) { console.error('[hd] 대화창 보내기: ' + (e && e.message || e)); ctx.toast('보내지 못했어요 — ' + (e && e.message || e)); return false; }
    if (ok === false) { ctx.toast('보내는 중이에요 — 잠시 뒤 다시 보내 주세요'); return false; }
    if (items.length) att('hd-attach-set', []);
    var said = text.trim() ? text : items.length ? '이미지 ' + items.length + '장' : '노트 ' + notesN + '개';
    last = C.record(said, r.memos, Date.now());   // 상태 줄은 쓴 글(경로 줄·노트 줄 없이)
    prog = {screens: r.memos.some(function (m) { return m.scope === 'all'; }) ? [] :   // 진행 줄(S2) — 이 요청 화면의 이벤트만(모든 화면 요청 = 아무 화면)
      r.memos.map(function (m) { return m.screen; }).filter(function (s, i, a) { return s && a.indexOf(s) === i; }), p: null,
      ids: last.ids.slice(), agent: window.__hdAgent || null, name: ai && ai.classList.contains('on') ? agentB.querySelector('span').textContent : null};   // 받는 곳(47-5b) = 보낼 때의 알약
    try { ctx.local.setItem(LKEY, JSON.stringify(last)); } catch (e) {}   // 저장 공간이 꽉 차도 이 창의 상태 줄은 그대로 보인다
    document.dispatchEvent(new CustomEvent('hd-chat-sent', {detail: {text: full.trim() ? full : said, notes: last.ids.slice(), agent: prog.name,   // 대화 패널(S3)이 기록한다
      chips: chipList.map(function (c) { return c.label; }), screens: prog.screens.length ? prog.screens.slice() : []}}));
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
    var b = e.target.closest('button');
    if (b && b.classList.contains('ch-more')) { open = true; renderChips(); place(); ta.focus(); return; }   // 외 N개 = 펼침
    var c = b && b.closest('.ch-chip[data-key]'); if (!c) return;
    dismissed[c.dataset.key] = 1; renderChips(); place(); ta.focus();
  });
  hideB.addEventListener('click', function () {
    var d = {part: 'chat', on: false, done: false};
    document.dispatchEvent(new CustomEvent('hd-chrome', {detail: d}));
    if (!d.done) { warnOnce('chrome', '창 메뉴가 붙지 않아 숨기기를 받을 곳이 없어요'); ctx.toast('대화창을 숨기지 못했어요 — 창 메뉴가 붙지 않았어요'); return; }
    ctx.toast('대화창을 숨겼어요 — 창 ▾ 메뉴에서 다시 보여요');
  });
  agentB.addEventListener('click', function () {
    var d = {anchor: agentB, done: false};
    document.dispatchEvent(new CustomEvent('hd-agent-pick', {detail: d}));
    if (!d.done) { warnOnce('agents', '받는 곳 고르기(view-agents)가 붙지 않았어요'); ctx.toast('받는 곳 고르기가 붙지 않았어요 — 위쪽 받는 곳 칩을 써 주세요'); }
  });
  if (ai && window.MutationObserver) new MutationObserver(renderAgent).observe(ai, {childList: true, characterData: true, subtree: true, attributes: true});
  else if (!ai) warnOnce('aichip', '위쪽 받는 곳 칩(#aichip)이 없어요 — 대화창 받는 곳 칩 없이');
  ta.addEventListener('input', grow);
  boxEl.addEventListener('hd-attach-changed', function (e) { attN = (e.detail && e.detail.count) || 0; grow(); });
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
  document.addEventListener('hd-composer', function (e) {   // 대화 패널(S3)이 보이면 그 아래 칸으로, 아니면 판 아래로 — 같은 요소를 옮긴다
    var d = e.detail || {}, h = d.host && d.host.nodeType === 1 ? d.host : null;
    d.done = true;
    if (h ? root.parentNode === h : (!docked && root.parentNode === document.body)) return;
    var focus = document.activeElement === ta;
    (h || document.body).appendChild(root);
    docked = !!h; root.classList.toggle('docked', docked); document.body.classList.toggle('chat-docked', docked);
    if (focus) ta.focus();
    grow(); place();
  });
  document.addEventListener('hd-event', function (e) {   // 서버 이벤트(view-live 의도, 47-4b) → 진행 줄: AI 작업 중 · 반영됨 · 끝 — 메모 답은 상태를 다시 읽은 뒤 1초 그리기가 붙인다
    if (!prog) return;
    var np = C.progress(prog.p, e.detail, prog.screens, prog.ids);
    if (np !== prog.p) { prog.p = np; renderLine(); }
  });
  setInterval(render, 1000);                              // 메모 상태·덮개는 다른 길(2초 읽기·답)로 바뀐다 — 47-4 SSE 가 오면 이벤트로
  renderAgent(); render(); grow(); booted = true;               // 처음 그린 줄(새로고침 뒤)은 맥박 없이
  return {render: render, send: send, last: function () { return last; }};
}

HD.feature('chat', {needs: ['$', 'toast', 'esc', 'notes', 'local', 'store', 'key', 'title', 'rowsEl'], mount: mount});
})();
