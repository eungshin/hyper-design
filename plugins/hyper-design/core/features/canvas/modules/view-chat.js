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
   판 노트(R25 · R27 F19): 고르기만으로는 싣지 않는다 — 판 메모 막대 'AI에게'(view-board-notes)의 의도 'hd-note-ai' {id} 를 받아 그 id 를 칩 목록(저장 안 함)에 넣고,
     셸 ctx.boardNotes() → 판 메모 모두 [{id, text, x, y, w, h}](판 좌표 — 주인은 view-board-notes, 읽기만) 중 넣은 것마다 [노트 "글" ×] 칩(HD.chat.chips notes, 밝은 칩 — 요소 칩과 같은 무리).
     지운 메모는 칩에서 빠지고, × 나 보내기 뒤에는 목록에서 뺀다(두 번 가지 않게).
     가까운 화면 = HD.chat.nearest(메모 상자, 카드 상자 — 둘 다 판 좌표, 메모 자리·크기가 바뀔 때만 다시 잼). 보내면 요청 글 끝 '노트:' 줄(HD.chat.build) — 글이 비어도 노트가 있으면 보낸다.
     ctx.boardNotes 가 없으면(옛 셸) [hd] 경고 한 번 + 노트 칩 없이.
   '/' 명령(R29): 빈 입력칸에 '/' 를 치면 명령 목록(HD.chatCmd.match — 지금 /memo 하나, 새 명령 = 표 한 줄 + 아래 RUN 한 함수). 위·아래·Enter·Tab·누르기 = 고르기,
     Esc = 닫기(그 글은 그대로, '/' 로 다시 시작할 때까지 안 열림), 빈칸 등 맞지 않는 글 = 닫히고 보통 글. 고르면 친 '/…' 글은 지운다.
     /memo = 칩 [메모 N건 ×](보내기 전 메모 모두 — HD.chatCmd.drafts/memoChip, 올리거나 포커스면 툴팁 .ch-tip 에 화면 이름 + 첫 글). 0건 = 토스트 '보낼 메모가 없어요', 칩 없음.
     보내면 대화 글로 만든 메모 + 그때의 보내기 전 메모를 ctx.sendNotes 한 번에(위쪽 [보내기]와 같은 요청문·같은 상태 바뀜) — 칩은 보낸 뒤 빠진다. 보낸·완료 메모는 넣지 않는다.
   받는 터미널 정보(R28): 도구 줄 알약 뒤 칸 [data-hd-agent-info] 만 둔다 — 모델·생각 깊이·컨텍스트 고리는 등록부 기능 agentInfo(view-agent-info)가 채운다.
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
  /* R27 F13 (bars): 요소 칩은 밝게(#ecece8 · 12px · 보통 굵기) + 작은 종류 아이콘 — 사용자가 쓰는 글보다 튀지 않게 */
  '#hdchat .ch-chip.el{background:#ecece8;color:#3a3a37;font-weight:500;padding-left:6px}' +
  '#hdchat .ch-chip.el .ch-ic{flex:none;width:12px;height:12px;margin-right:3px;fill:none;stroke:#6b6b66;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}' +
  /* /R27 F13 */
  /* R27 F19 + R29 (chatmemo): 노트 칩·메모 N건 칩도 요소 칩과 같은 밝은 칩 — 노랑을 쓰지 않는다(색은 판의 메모 자체에) */
  '#hdchat .ch-chip.note,#hdchat .ch-chip.memos{background:#ecece8;color:#3a3a37;font-weight:500;padding-left:6px}' +
  '#hdchat .ch-chip.note .ch-ic,#hdchat .ch-chip.memos .ch-ic{flex:none;width:12px;height:12px;margin-right:3px;fill:none;stroke:#6b6b66;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}' +
  '#hdchat .ch-tip{position:absolute;z-index:3;box-sizing:border-box;max-width:min(320px,calc(100% - 8px));padding:6px 8px;border-radius:8px;background:#2b2b29;color:#f4f4f1;font:12px/18px system-ui,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.18);pointer-events:none;white-space:nowrap}' +
  '#hdchat .ch-tip[hidden]{display:none}#hdchat .ch-tip div{overflow:hidden;text-overflow:ellipsis}' +
  '#hdchat .ch-cmds{position:absolute;left:8px;bottom:calc(100% + 6px);z-index:3;min-width:260px;padding:4px;margin:0;list-style:none;background:var(--ui-surface,#fff);border-radius:10px;box-shadow:0 0 0 1px rgba(0,0,0,.08),0 6px 20px rgba(0,0,0,.12)}' +
  '#hdchat .ch-cmds[hidden]{display:none}' +
  '#hdchat .ch-cmds li{display:flex;align-items:baseline;gap:10px;height:30px;line-height:30px;padding:0 8px;border-radius:6px;cursor:pointer;white-space:nowrap}' +
  '#hdchat .ch-cmds li[aria-selected="true"]{background:#F2F2EF}' +
  '#hdchat .ch-cmds b{font:600 13px system-ui,sans-serif;color:var(--ui-primary,#2b2b29)}#hdchat .ch-cmds span{font-size:12px;color:var(--ui-muted,#8a8a85)}' +
  /* /R27 F19 + R29 */
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
    '<ul class="ch-cmds" id="hdcmds" role="listbox" aria-label="명령" hidden></ul><div class="ch-tip" id="hdtip" role="tooltip" hidden></div>' +
    '<textarea rows="1" aria-label="요청 글"></textarea>' +
    '<div class="ch-tools"><button type="button" class="ch-agent" hidden aria-haspopup="menu" aria-expanded="false" aria-controls="amenu"><i></i><span></span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>' +
    '<span class="ch-meta" data-hd-agent-info hidden></span>' +
    '<button type="button" class="ch-clip" data-hd-attach-pick aria-label="이미지 첨부" title="이미지 첨부 — 붙여넣기(Ctrl+V)·끌어 놓기도 돼요"><svg viewBox="0 0 24 24"><path d="M21 11.5l-8.6 8.6a5 5 0 0 1-7.1-7.1l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9"/></svg></button>' +
    '<button type="button" class="ch-send" disabled aria-label="보내기" title="보내기 (Enter)"><svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6"/></svg></button></div></div>';
  document.body.appendChild(root); document.body.classList.add('has-chat');
  var ta = root.querySelector('textarea'), btn = root.querySelector('.ch-send'), chipsEl = root.querySelector('.ch-chips'), lineEl = root.querySelector('.ch-line');
  var boxEl = root.querySelector('.ch-box'), attN = 0, noteN = 0, memoN = 0;
  var CC = HD.chatCmd, cmdEl = root.querySelector('.ch-cmds'), tipEl = root.querySelector('.ch-tip');
  var memoOn = false, noteIds = [], cmd = {list: [], i: -1}, cmdOff = false;   // /memo 칩 켜짐 · 'AI에게'로 넣은 판 메모 id · 명령 목록(모두 저장 안 함)
  ta.setAttribute('aria-controls', 'hdcmds'); ta.setAttribute('aria-autocomplete', 'list');
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
    if (!noteIds.length) return [];
    var all = ctx.boardNotes() || [], byId = {};
    all.forEach(function (n) { byId[n.id] = n; });
    noteIds = noteIds.filter(function (id) { return byId[id]; });   // 지운 판 메모는 칩에서 빠진다
    return noteIds.map(function (id) { return byId[id]; }).map(function (n) {
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
  function memoDrafts() { return CC.drafts(ctx.notes.list()); }
  function chipsNow() {
    var raw = rawChips(); dismissed = C.prune(dismissed, raw);
    var list = C.visible(raw, dismissed), mc = memoOn ? CC.memoChip(memoDrafts(), ctx.title) : null;
    if (memoOn && !mc) memoOn = false;                     // 그 사이 다른 길로 다 보냈으면 칩도 빠진다
    return mc ? list.concat([mc]) : list;
  }

  var ICON = {                                           // 요소 칩 종류 아이콘(R27 F13) — 12px 선 그림
    text: '<path d="M4 6V4h16v2M12 4v16M9 20h6"/>', button: '<rect x="3" y="7" width="18" height="10" rx="5"/>',
    link: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
    field: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 10v4"/>', image: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 16l5-5 4 4 3-3 6 6"/>',
    box: '<rect x="4" y="4" width="16" height="16" rx="2" stroke-dasharray="3 2"/>',
    note: '<path d="M5 4h14v10l-6 6H5z"/><path d="M13 20v-6h6"/>', memos: '<path d="M4 6h12M4 11h12M4 16h8"/><path d="M19 14v6M16 17h6"/>'};
  function icon(t) { return '<svg class="ch-ic" viewBox="0 0 24 24" aria-hidden="true">' + (ICON[t] || ICON.box) + '</svg>'; }
  function renderChips() {                               // 칩 줄(S1c): 고른 것이 있을 때만 · 3개를 넘으면 앞 2개 + '외 N개'(누르면 펼침) · 범위는 입력 안내 글로
    var list = chipsNow();
    if (list.length <= 3) open = false;                    // 접을 것이 없어지면 다음 고르기는 다시 접힌 채로
    memoN = list.some(function (c) { return c.kind === 'memos'; }) ? 1 : 0;
    var f = C.fold(list, open), sig = JSON.stringify([f.more, f.shown.map(function (c) { return [c.key, c.label, c.tip || null]; })]);
    if (sig === chipSig) return;
    chipSig = sig;
    chipsEl.innerHTML = f.shown.map(function (c) {
      var memos = c.kind === 'memos';
      return '<span class="ch-chip' + (c.kind === 'el' || c.kind === 'note' || memos ? ' ' + c.kind : '') + '" data-key="' + ctx.esc(c.key) + '"' + (c.kind === 'el' ? ' data-type="' + ctx.esc(c.type || 'box') + '"' : '') +
        (memos ? ' tabindex="0" aria-describedby="hdtip"' : ' title="' + ctx.esc(c.label) + '"') + '>' + (c.kind === 'el' ? icon(c.type) : c.kind === 'note' || memos ? icon(c.kind) : '') + '<span>' + ctx.esc(c.label) +
        '</span><button type="button" aria-label="' + ctx.esc(c.label) + ' 빼기">×</button></span>';
    }).join('') + (f.more ? '<button type="button" class="ch-chip ch-more" aria-expanded="false" title="고른 것 모두 보기">외 ' + f.more + '개</button>' : '');
    chipsEl.hidden = !list.length;
    noteN = list.filter(function (c) { return c.kind === 'note'; }).length;   // 노트만 있어도 보내기를 켠다
    btn.disabled = !ta.value.trim() && !attN && !noteN && !memoN;
    if (!memoN) tipEl.hidden = true; else if (!tipEl.hidden) showTip();
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
    btn.disabled = !ta.value.trim() && !attN && !noteN && !memoN; place();
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
  function render() { renderChips(); renderLine(); place(); clearEdit(document.activeElement); }   // 칩 줄이 생겨 이 창이 커져도 고치는 글 상자를 가리지 않게(R25)
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
    var withMemos = chipList.some(function (c) { return c.kind === 'memos'; }), drafts = withMemos ? memoDrafts() : [];   // /memo(R29) — 보낼 때의 보내기 전 메모
    var r = C.build(chipList, full, {first: firstScreen(), titleOf: ctx.title}, mkId);
    if (!r.memos.length && !drafts.length) { ctx.toast(r.why); return false; }
    if (items.length) r.memos.forEach(function (m) { m.attach = items.slice(); });   // 메모가 첨부 목록을 지닌다
    var all = r.memos.concat(drafts), ok;                  // 한 요청 — 위쪽 [보내기]와 같은 요청문, 보낸 뒤 그 메모들도 '보냄'
    try { ok = ctx.sendNotes(all); }
    catch (e) { console.error('[hd] 대화창 보내기: ' + (e && e.message || e)); ctx.toast('보내지 못했어요 — ' + (e && e.message || e)); return false; }
    if (ok === false) { ctx.toast('보내는 중이에요 — 잠시 뒤 다시 보내 주세요'); return false; }
    if (items.length) att('hd-attach-set', []);
    memoOn = false; noteIds = []; hideCmds();              // 함께 보낸 메모·노트는 칩에서 뺀다(두 번 가지 않게)
    var said = text.trim() ? text : items.length ? '이미지 ' + items.length + '장' : notesN ? '노트 ' + notesN + '개' : '메모 ' + drafts.length + '건';
    last = C.record(said, all, Date.now());   // 상태 줄은 쓴 글(경로 줄·노트 줄 없이)
    prog = {screens: all.some(function (m) { return m.scope === 'all'; }) ? [] :   // 진행 줄(S2) — 이 요청 화면의 이벤트만(모든 화면 요청 = 아무 화면)
      all.map(function (m) { return m.screen; }).filter(function (s, i, a) { return s && a.indexOf(s) === i; }), p: null,
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
    var k = c.dataset.key;
    if (k === CC.KEY) memoOn = false;                      // 메모 N건 빼기(R29)
    else if (k.indexOf('note:') === 0) noteIds = noteIds.filter(function (id) { return 'note:' + id !== k; });   // 'AI에게'로 넣은 노트 빼기(F19)
    else dismissed[k] = 1;
    renderChips(); place(); ta.focus();
  });
  function showTip() {                                     // 메모 N건 툴팁(R29) — 칩 위, 화면 이름 + 첫 글
    var chip = chipsEl.querySelector('.ch-chip.memos'), mc = memoOn ? CC.memoChip(memoDrafts(), ctx.title) : null;
    if (!chip || !mc) { tipEl.hidden = true; return; }
    tipEl.innerHTML = mc.tip.map(function (t) { return '<div>' + ctx.esc(t) + '</div>'; }).join('');
    tipEl.hidden = false;
    var br = boxEl.getBoundingClientRect(), cr = chip.getBoundingClientRect();
    tipEl.style.left = Math.max(0, cr.left - br.left) + 'px';
    tipEl.style.bottom = (br.bottom - cr.top + 6) + 'px';
  }
  chipsEl.addEventListener('pointerover', function (e) { if (e.target.closest && e.target.closest('.ch-chip.memos')) showTip(); });
  chipsEl.addEventListener('pointerout', function (e) { var c = e.target.closest && e.target.closest('.ch-chip.memos'); if (c && !c.contains(e.relatedTarget)) tipEl.hidden = true; });
  chipsEl.addEventListener('focusin', function (e) { if (e.target.closest('.ch-chip.memos')) showTip(); });
  chipsEl.addEventListener('focusout', function () { tipEl.hidden = true; });

  // '/' 명령(R29) — 규칙은 HD.chatCmd, 여기는 목록 그리기와 실행만. 새 명령 = COMMANDS 한 줄 + RUN 한 함수
  var RUN = {
    memo: function () {
      if (!memoDrafts().length) { ctx.toast(CC.EMPTY); return; }
      memoOn = true; renderChips(); place();
    }
  };
  function hideCmds() { cmd = {list: [], i: -1}; cmdEl.hidden = true; cmdEl.innerHTML = ''; ta.removeAttribute('aria-activedescendant'); ta.setAttribute('aria-expanded', 'false'); }
  function drawCmds() {
    if (!cmd.list.length) { hideCmds(); return; }
    cmdEl.innerHTML = cmd.list.map(function (c, i) {
      return '<li role="option" id="hdcmd-' + ctx.esc(c.name) + '" data-cmd="' + ctx.esc(c.name) + '" aria-selected="' + (i === cmd.i) + '"><b>' + ctx.esc(c.label) + '</b><span>' + ctx.esc(c.hint) + '</span></li>';
    }).join('');
    cmdEl.hidden = false; ta.setAttribute('aria-expanded', 'true');
    ta.setAttribute('aria-activedescendant', 'hdcmd-' + cmd.list[cmd.i].name);
  }
  function syncCmds() {
    if (cmdOff && ta.value.charAt(0) !== '/') cmdOff = false;   // Esc 로 닫은 뒤 '/' 로 다시 시작하면 다시 연다
    var list = cmdOff ? [] : CC.match(ta.value), keep = cmd.list[cmd.i];
    var i = keep ? list.indexOf(keep) : -1;
    cmd = {list: list, i: list.length ? (i >= 0 ? i : 0) : -1};
    drawCmds();
  }
  function runCmd(c) {
    if (!c) return;
    var fn = RUN[c.name];
    ta.value = ''; hideCmds(); grow(); ta.focus();
    if (typeof fn !== 'function') { console.warn('[hd] 대화창: 실행할 수 없는 명령 /' + c.name); ctx.toast('그 명령은 아직 쓸 수 없어요'); return; }
    fn();
  }
  cmdEl.addEventListener('pointerdown', function (e) { e.preventDefault(); });   // 입력칸 포커스를 잃지 않게
  cmdEl.addEventListener('click', function (e) {
    var li = e.target.closest('li[data-cmd]'); if (!li) return;
    runCmd(cmd.list.filter(function (c) { return c.name === li.dataset.cmd; })[0]);
  });
  ta.addEventListener('blur', function () { setTimeout(function () { if (document.activeElement !== ta) hideCmds(); }, 0); });

  document.addEventListener('hd-note-ai', function (e) {   // 판 메모 'AI에게'(F19) — 고르기만으로는 싣지 않는다
    var d = e.detail || {}, id = d.id == null ? '' : String(d.id);
    d.done = true;
    if (!id) { console.warn('[hd] 대화창: 판 메모 id 가 없는 AI에게'); return; }
    if (noteIds.indexOf(id) < 0) noteIds.push(id);
    if (!docked && document.body.classList.contains('no-chat')) document.dispatchEvent(new CustomEvent('hd-chrome', {detail: {part: 'chat', on: true, done: false}}));   // 숨긴 대화창이면 다시 보인다
    renderChips(); place();
    if (!chipsEl.querySelector('.ch-chip[data-key="note:' + id.replace(/["\\]/g, '') + '"]')) {
      noteIds = noteIds.filter(function (x) { return x !== id; }); ctx.toast('빈 판 메모는 AI 에게 보낼 수 없어요'); return;
    }
    ta.focus();
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
  ta.addEventListener('input', function () { grow(); syncCmds(); });
  boxEl.addEventListener('hd-attach-changed', function (e) { attN = (e.detail && e.detail.count) || 0; grow(); });
  ta.addEventListener('keydown', function (e) {
    e.stopPropagation();                                   // 도구 키·Delete 가 판으로 가지 않게(입력 중)
    if (cmd.list.length && !e.isComposing && e.keyCode !== 229) {   // 명령 목록이 열려 있으면 화살표·Enter·Tab·Esc 는 목록 것
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); cmd.i = CC.move(cmd.i, cmd.list.length, e.key === 'ArrowDown' ? 1 : -1); drawCmds(); return; }
      if ((e.key === 'Enter' && !e.shiftKey) || e.key === 'Tab') { e.preventDefault(); runCmd(cmd.list[cmd.i]); return; }
      if (e.key === 'Escape') { e.preventDefault(); cmdOff = true; hideCmds(); return; }
    }
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
  function clearEdit(t) {                                 // 판 안 글 상자를 고치는 동안 떠 있는 이 창이 가리면 판을 그만큼 위로(R25 — HD.chat.clear)
    if (docked || !t || t.nodeType !== 1 || root.contains(t) || !root.getClientRects().length) return;
    if (!(t.isContentEditable || t.tagName === 'TEXTAREA' || t.tagName === 'INPUT')) return;
    var pane = ctx.$('#screens'); if (!pane || !pane.contains(t)) return;
    var box = (t.closest('.capbox, .bnote') || t).getBoundingClientRect();
    var dy = C.clear(box, root.getBoundingClientRect(), pane.getBoundingClientRect(), 16);
    if (!dy) return;
    if (!ctx.view || typeof ctx.view.set !== 'function') { warnOnce('view', 'ctx.view 가 없어 고치는 글 상자를 대화창 위로 올리지 못해요'); return; }
    var v = ctx.view.get(); ctx.view.set(v.z, v.tx, v.ty - dy);
  }
  document.addEventListener('focusin', function (e) { var t = e.target; setTimeout(function () { clearEdit(t); }, 0); });   // 그 기능이 배율·자리를 정한 뒤
  document.addEventListener('input', function (e) { clearEdit(e.target); });   // 쓰다가 상자가 길어지면
  setInterval(render, 1000);                              // 메모 상태·덮개는 다른 길(2초 읽기·답)로 바뀐다 — 47-4 SSE 가 오면 이벤트로
  renderAgent(); render(); grow(); booted = true;               // 처음 그린 줄(새로고침 뒤)은 맥박 없이
  return {render: render, send: send, last: function () { return last; }};
}

HD.feature('chat', {needs: ['$', 'toast', 'esc', 'notes', 'local', 'store', 'key', 'title', 'rowsEl'], mount: mount});
})();
