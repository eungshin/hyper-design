/* View — 대화 패널(S3, 도크 패널 '대화' #pTalk): 요청 하나 = 턴 하나(오래된 것 위) — 내 요청 말풍선(글 + 칩) · 보냄 · 진행 줄(에이전트가 알린 터미널 출력) · 답 ·
   AI 반영 · 빌드 완료/실패(빨간 줄) · 끝 ✓ / 작업 중 회전. 규칙(턴·상태·줄·되돌릴 stamp·자동 스크롤·터미널 섞기)은 HD.chatLog(Model).
   상태(주인 이 파일, 저장 안 함 — 진실은 서버 .hd-chat.jsonl): 받은 기록 records + 마지막 seq · 터미널 줄 entries + cursor + 받는 곳 · 이미 본 seq(맥박).
   읽기: GET /api/chat?since= — 처음 · 서버 이벤트(view-live 의 document 'hd-event': request.sent · agent.* · ai.write · build.* · notes.changed) 뒤 ·
     실시간이 없을 때를 위해 패널이 보이는 동안 4초마다. 남기기: 대화창 의도 'hd-chat-sent' {text, chips, screens, notes, agent} → POST /api/chat ask ·
     턴 되돌리기 성공 → POST /api/chat undone.
   턴 누르기 = 닿은 카드 잠깐 강조(.card.tk-hl) + ctx.focus(ids)(셸: 그 카드들로 판 옮기기, 지금보다 크게는 안 함).
   [되돌리기](끝난 턴, AI 쓰기가 있을 때) = 48c 되살리기(POST /api/restore, HD.aiUndo.body/outcome) 를 stamp 마다 새것부터 — 거절되면 이유 토스트, 되살린 카드는 ctx.reload.
   입력창 자리(S3): 패널이 보이면(도크·떠 있는 창 어디든) 의도 'hd-composer' {host: 패널 아래 칸} → view-chat 이 같은 #hdchat 을 그리로 옮긴다, 안 보이면 {host:null} = 판 아래로.
   터미널 대화(S3b 계약): 받는 곳(window.__hdAgent)이 있으면 GET /api/agents/transcript?agent=&since=<cursor> + 이벤트 agent.transcript — 턴과 시간 차례로 섞는다.
     user = '터미널에서' 오른쪽 말풍선 · assistant = 에이전트 답 · tool = 회색 머리 줄 '도구 · <첫 줄>' + 아래 부른 입력 전체(늘 펼침). 같은 요청은 한 번(HD.chatLog.echo). 없음·못 읽음 = 조용한 한 줄.
   늘 전문(R24 · login#7): 말풍선·진행·답·실패 이유·터미널 줄을 다 그린다 — 접기·펼치기 단추 없음, 줄바꿈 그대로, 긴 낱말·경로는 줄 안에서 꺾고
     ``` 덩이 = 고정폭 <pre>(가로 스크롤), `인라인` = <code>(나누기는 HD.chatLog.blocks/spans).
     글은 골라 복사할 수 있고(도크의 user-select:none 을 목록만 풀어 줌 · 글을 고르는 중이면 턴 누르기를 하지 않음), 답마다 [복사](올리면 보임).
     다시 그리기는 줄마다(턴·터미널 줄 key) 바뀐 것만 새로 만들고 나머지 요소는 그대로 둔다 — 긴 기록에서도 이벤트마다 목록 전체를 다시 만들지 않는다.
   메모의 답 설명: 답 기록에 detail 이 없고 메모(note)를 이름 대면 그 메모의 같은 답 detail 을 답 줄 아래에 전체를 그린다(ctx.notes.find — 읽기만, 고르는 규칙 HD.chatLog.memoDetail).
   맨 아래로 단추(R50, Slack·ChatGPT·Claude.ai 의 scroll-to-bottom): 목록을 위로 올려 읽는 중이면 목록 오른쪽 아래(입력창 위 — 입력창은 덮지 않음)에
     둥근 반투명 ↓ 단추 .tk-jump · 누르면 맨 아래로(부드럽게, 움직임 줄이기면 바로) · 맨 아래면 숨김. 올려 읽는 중에 새 줄이 오면 당기지 않고 단추에 점(.tk-dot).
     보일지·점은 HD.chatLog.jump(Model), 상태(보임·점)는 이 파일.
   움직임(FINDINGS §8): 새 줄 맥박 600ms · 패널 나타남 spring-fade 400ms · 진행 회전 1s — 움직임 줄이기면 모두 끔.
   HD.feature('chatLog', {needs: ['$', 'toast', 'esc', 'api', 'reload', 'cardEl', 'notes']}) → {refresh(), records(), shown()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var EVERY = 4000;
var REFRESH = ['request.sent', 'agent.progress', 'agent.reply', 'ai.write', 'build.done', 'build.failed', 'notes.changed'];
var STATE_SAY = {running: '작업 중…', queued: '대기 중 — 읽는 에이전트를 기다려요', done: '끝', failed: '', decide: '결정 필요 — 메모에서 골라 주세요', undone: '되돌림'};   // 실패 = 빨간 빌드 실패 줄 하나로 말한다(꼬리 '! 실패' 없음, R27 F04)
var NO_TERM = '이 터미널의 대화는 가져올 수 없어요';

var CSS =
  '#pTalk{padding:0;height:100%;min-height:0;display:flex;flex-direction:column;box-sizing:border-box}' +
  '#pTalk .tk-wrap{position:relative;flex:1 1 auto;min-height:0;display:flex;flex-direction:column}' +
  '#pTalk .tk-list{flex:1 1 auto;min-height:0;overflow-y:auto;margin:0;padding:10px 12px 4px;list-style:none;display:flex;flex-direction:column;gap:14px;scrollbar-width:thin;-webkit-user-select:text;user-select:text;cursor:auto}' +
  '#pTalk .tk-empty{margin:auto 0;padding:24px 8px;color:var(--ui-muted,#8a8a85);font-size:12.5px;text-align:center;line-height:1.5}' +
  '#pTalk .tk-foot{flex:none;padding:0 8px 8px}' +
  '#pTalk .tk-foot:empty{display:none}' +
  '#pTalk.tk-in{animation:tkIn .4s cubic-bezier(0.34,0.88,0.34,1)}' +
  '@keyframes tkIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}' +
  '#pTalk .tk-turn{display:flex;flex-direction:column;gap:6px;min-width:0;border-radius:10px;padding:2px;cursor:pointer;outline:none}' +
  '#pTalk .tk-turn:hover .tk-lines,#pTalk .tk-turn:focus-visible .tk-lines{background:#F6F6F3}' +
  '#pTalk .tk-ask{align-self:flex-end;max-width:88%;background:var(--ui-badge-soft,#E4E4DF);color:var(--ui-primary,#2b2b29);border-radius:14px 14px 4px 14px;padding:7px 11px;font-size:13px;line-height:18px;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;min-width:0}' +
  '#pTalk .tk-ask.req{background:#F2F2EF;color:#6b6b66}' +
  '#pTalk .tk-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}' +
  '#pTalk .tk-chip{font-size:11px;font-weight:600;line-height:18px;padding:0 7px;border-radius:999px;background:#fff;color:#3a3a37;max-width:100%;overflow-wrap:anywhere;white-space:normal}' +
  '#pTalk .tk-lines{list-style:none;margin:0;padding:4px 6px;border-radius:8px;display:flex;flex-direction:column;gap:3px}' +
  '#pTalk .tk-l{position:relative;padding-left:14px;font-size:12px;line-height:17px;color:#5f5f5a;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;min-width:0}' +
  '#pTalk .tk-l::before{content:"";position:absolute;left:3px;top:6px;width:5px;height:5px;border-radius:50%;background:#c4c4bf}' +
  '#pTalk .tk-l[data-kind="reply"]{padding-left:0;font-size:13px;line-height:19px;color:var(--ui-primary,#2b2b29);white-space:pre-wrap}' +
  '#pTalk .tk-l[data-kind="reply"]::before{display:none}' +
  '#pTalk .tk-l[data-tone="ok"]::before{background:var(--ui-ok,#4f7d5f)}' +
  '#pTalk .tk-l[data-tone="accent"]{color:var(--ui-accent,#c2590a)}' +
  '#pTalk .tk-l[data-tone="red"]{color:var(--ui-danger,#B42318);font-weight:600}#pTalk .tk-l[data-tone="red"]::before{background:var(--ui-danger,#B42318)}' +
  '#pTalk .tk-st{display:flex;align-items:center;gap:6px;min-height:22px;padding:0 6px;font-size:11.5px;color:var(--ui-muted,#8a8a85)}' +
  '#pTalk .tk-ic{flex:none;width:12px;height:12px;display:grid;place-items:center;font-size:11px;line-height:1}' +
  '#pTalk .tk-turn[data-state="running"] .tk-ic{box-sizing:border-box;border:1.6px solid #c4c4bf;border-top-color:var(--ui-primary,#2b2b29);border-radius:50%;animation:tkSpin 1s linear infinite}' +
  '#pTalk .tk-turn[data-state="done"] .tk-ic{color:var(--ui-ok,#4f7d5f)}' +
  '#pTalk .tk-turn[data-state="failed"] .tk-st{color:var(--ui-danger,#B42318)}' +
  '#pTalk .tk-turn[data-state="decide"] .tk-st{color:var(--ui-accent,#c2590a)}' +
  '@keyframes tkSpin{to{transform:rotate(360deg)}}' +
  '#pTalk .tk-undo{margin-left:auto;border:1px solid var(--ui-line,#ddd);background:#fff;border-radius:6px;padding:1px 8px;font:500 11.5px system-ui,sans-serif;color:#3a3a37;cursor:pointer}' +
  '#pTalk .tk-undo:hover{background:#F2F2EF}#pTalk .tk-undo:disabled{opacity:.5;cursor:default}' +
  '#pTalk .tk-term{display:flex;flex-direction:column;gap:3px;min-width:0}' +
  '#pTalk .tk-term[data-role="user"]{align-self:flex-end;max-width:88%;align-items:flex-end}' +
  '#pTalk .tk-term .tk-who{font-size:10.5px;color:var(--ui-muted,#8a8a85)}' +
  '#pTalk .tk-term[data-role="user"] .tk-tx{background:#F2F2EF;border-radius:14px 14px 4px 14px;padding:6px 10px}' +
  '#pTalk .tk-tx{font-size:13px;line-height:19px;white-space:pre-wrap;word-break:break-word;overflow-wrap:anywhere;min-width:0;color:var(--ui-primary,#2b2b29)}' +
  '#pTalk .tk-tool{font-size:11.5px;color:#7a7a75;min-width:0}#pTalk .tk-tool-h{display:block;padding-left:14px;position:relative;white-space:pre-wrap;overflow-wrap:anywhere}' +
  '#pTalk .tk-tool-h::before{content:"\\203A";position:absolute;left:3px}' +
  '#pTalk .tk-tool pre{margin:4px 0 0 14px;padding:6px 8px;background:#F6F6F3;border-radius:6px;font:11px/15px ui-monospace,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere}' +
  '#pTalk .tk-md{position:relative;white-space:normal}#pTalk .tk-md .tk-p{white-space:pre-wrap;word-break:keep-all;overflow-wrap:anywhere}#pTalk .tk-md .tk-p+.tk-p,#pTalk .tk-md .tk-p+pre,#pTalk .tk-md pre+.tk-p{margin-top:6px}' +
  '#pTalk .tk-md code{font:12px/17px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:#EFEFEB;border-radius:4px;padding:0 3px}' +
  '#pTalk .tk-md pre.tk-code{margin:6px 0 0;padding:8px 10px;background:#F4F4F0;border:1px solid #E6E6E1;border-radius:8px;font:12px/17px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre;overflow-x:auto;scrollbar-width:thin;color:#2b2b29;tab-size:2}' +
  '#pTalk .tk-md pre.tk-code code{background:none;padding:0;font:inherit}' +
  '#pTalk .tk-copy{display:block;margin:4px 0 0 auto;padding:1px 7px;border:1px solid var(--ui-line,#ddd);border-radius:6px;background:#fff;color:#6b6b66;font:500 11px system-ui,sans-serif;cursor:pointer;opacity:0;transition:opacity .12s;-webkit-user-select:none;user-select:none}' +
  '#pTalk .tk-copy:focus-visible,#pTalk .tk-term:hover .tk-copy,#pTalk .tk-l:hover .tk-copy{opacity:1}#pTalk .tk-copy:hover{background:#F2F2EF;color:#2b2b29}' +
  '#pTalk .tk-detail{margin-top:6px}' +
  /* R50 맨 아래로 단추 — 목록 칸(.tk-wrap) 오른쪽 아래, 입력창(.tk-foot) 위 */
  '#pTalk .tk-jump{position:absolute;right:12px;bottom:10px;z-index:2;width:32px;height:32px;padding:0;border-radius:50%;border:1px solid rgba(0,0,0,.08);' +
    'background:rgba(255,255,255,.82);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);box-shadow:0 2px 8px rgba(0,0,0,.14);color:#3a3a37;' +
    'display:grid;place-items:center;cursor:pointer;animation:tkJump .16s ease-out;-webkit-user-select:none;user-select:none}' +
  '#pTalk .tk-jump[hidden]{display:none}' +
  '#pTalk .tk-jump:hover{background:rgba(255,255,255,.96);color:var(--ui-primary,#2b2b29)}' +
  '#pTalk .tk-jump:focus-visible{outline:2px solid var(--ui-primary,#2b2b29);outline-offset:2px}' +
  '#pTalk .tk-jump svg{width:16px;height:16px;display:block}' +
  '#pTalk .tk-dot{position:absolute;top:1px;right:1px;width:8px;height:8px;border-radius:50%;background:var(--ui-accent,#c2590a);box-shadow:0 0 0 2px #fff}' +
  '#pTalk .tk-dot[hidden]{display:none}' +
  '@keyframes tkJump{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}' +
  '#pTalk .tk-quiet{font-size:11.5px;color:var(--ui-muted,#8a8a85);text-align:center}' +
  '#pTalk .tk-new{animation:tkPulse .6s ease-out;transform-origin:left center}' +
  '@keyframes tkPulse{0%{transform:scale(1)}50%{transform:scale(1.02)}100%{transform:scale(1)}}' +
  '.card.tk-hl .phone{box-shadow:0 0 0 3px var(--ui-primary,#2b2b29),0 8px 24px rgba(0,0,0,.18)!important;transition:box-shadow .3s}' +
  '@media (prefers-reduced-motion: reduce){#pTalk.tk-in,#pTalk .tk-new,#pTalk .tk-turn[data-state="running"] .tk-ic,#pTalk .tk-jump{animation:none}.card.tk-hl .phone{transition:none}}';

function mount(ctx) {
  var L = HD.chatLog, A = HD.aiUndo, host = ctx.$('#pTalk');
  if (!host) { console.warn('[hd] 대화 패널: 자리(#pTalk)가 없어요 — 대화 패널 없이'); return {}; }
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  host.innerHTML = '<div class="tk-wrap"><ol class="tk-list" aria-label="대화"></ol>' +
    '<button type="button" class="tk-jump" hidden aria-label="최신 메시지로" title="최신 메시지로">' +
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3v10M3.5 8.5 8 13l4.5-4.5"/></svg>' +
    '<span class="tk-dot" hidden></span></button></div><div class="tk-foot"></div>';
  var list = host.querySelector('.tk-list'), foot = host.querySelector('.tk-foot'), jumpBtn = host.querySelector('.tk-jump'), jumpDot = host.querySelector('.tk-dot');
  var jumpSt = {show: false, unseen: false};
  var on = !!(ctx.api && ctx.api.on), records = [], seq = null, seen = null, sig = null, warned = {};
  var term = {agent: null, entries: [], cursor: null, source: null, failed: false}, undoing = {};
  var fetching = false, again = false, tick = 0, shownNow = false, nodes = {}, copies = {};
  function noteOf(id) { var n = ctx.notes.find(id); return n || null; }

  function warnOnce(k, m) { if (warned[k]) return; warned[k] = 1; console.warn('[hd] 대화 패널: ' + m); }
  function shown() { return host.getClientRects().length > 0; }

  /* ---------- 그리기 ---------- */
  function chipHtml(c) { return '<span class="tk-chip" title="' + ctx.esc(c) + '">' + ctx.esc(c) + '</span>'; }
  function turnHtml(t, fresh) {
    var a = t.ask, say = STATE_SAY[t.state] || '';
    var ask = a ? '<div class="tk-ask' + (a.fromRequest ? ' req' : '') + (fresh(t.recs[0].seq) ? ' tk-new' : '') + '">' + ctx.esc(a.text) +
      (a.chips.length ? '<div class="tk-chips">' + a.chips.map(chipHtml).join('') + '</div>' : '') + '</div>' : '';
    var lines = t.lines.length ? '<ol class="tk-lines">' + t.lines.map(function (l) {
      var body = l.kind === 'reply' ? (l.detail ? withDetail(l) : rich(l.text, 'r' + l.seq)) : ctx.esc(l.text);   // 답 = 전체(R24) · 메모 설명 붙임
      return '<li class="tk-l' + (l.kind === 'reply' ? ' tk-md' : '') + (fresh(l.seq) ? ' tk-new' : '') + '" data-kind="' + l.kind + '" data-tone="' + (l.tone || '') + '">' + body + '</li>';
    }).join('') + '</ol>' : '';
    var ic = t.state === 'done' ? '✓' : '';
    var undo = t.undoable && on ? '<button type="button" class="tk-undo"' + (undoing[t.id] ? ' disabled' : '') + ' title="이 요청으로 AI 가 바꾼 화면을 되돌려요">' +
      (undoing[t.id] ? '되돌리는 중…' : '되돌리기') + '</button>' : '';
    return '<li class="tk-turn" data-turn="' + t.id + '" data-state="' + t.state + '" tabindex="0" title="누르면 이 요청이 닿은 화면으로">' + ask + lines +
      '<div class="tk-st"><span class="tk-ic" aria-hidden="true">' + ic + '</span><span class="tk-say">' + ctx.esc(say) + '</span>' + undo + '</div></li>';
  }
  function withDetail(l) {                               // 답 줄 + 메모의 설명(detail) 전체 — 접지 않는다(login#7)
    var key = 'r' + l.seq;
    copies[key] = l.text + '\n\n' + l.detail;
    return md(l.text) + '<div class="tk-detail" data-detail="' + l.seq + '">' + md(l.detail) +
      '</div><button type="button" class="tk-copy" data-copy="' + key + '" title="이 답을 복사">복사</button>';
  }
  function rich(text, key) {                             // 답 글 → html(R24): 글 덩이 = 줄바꿈 그대로 · ``` = <pre> · `인라인` = <code> · [복사]
    copies[key] = text;
    return md(text) + '<button type="button" class="tk-copy" data-copy="' + ctx.esc(key) + '" title="이 답을 복사">복사</button>';
  }
  function md(text) {
    return L.blocks(text).map(function (b) {
      if (b.type === 'code') return '<pre class="tk-code"' + (b.lang ? ' data-lang="' + ctx.esc(b.lang) + '"' : '') + '><code>' + ctx.esc(b.text) + '</code></pre>';
      return '<div class="tk-p">' + L.spans(b.text).map(function (x) { return x.code ? '<code>' + ctx.esc(x.text) + '</code>' : ctx.esc(x.text); }).join('') + '</div>';
    }).join('');
  }
  function termHtml(e, fresh) {
    var v = L.entryView(e), nw = fresh ? ' tk-new' : '';
    if (v.role === 'tool') {                              // 도구 줄 = 머리 줄 + 부른 입력 전체(늘 펼침, login#7)
      var rest = v.text.split('\n').slice(1).join('\n');
      return '<li class="tk-term' + nw + '" data-role="tool" data-id="' + ctx.esc(e.id) + '"><div class="tk-tool"><span class="tk-tool-h">' + ctx.esc(v.label) + '</span>' +
        (rest.trim() ? '<pre>' + ctx.esc(rest) + '</pre>' : '') + '</div></li>';
    }
    return '<li class="tk-term' + nw + '" data-role="' + v.role + '" data-id="' + ctx.esc(e.id) + '">' + (v.label ? '<span class="tk-who">' + ctx.esc(v.label) + '</span>' : '') +
      (v.role === 'assistant' ? '<div class="tk-tx tk-md">' + rich(v.text, 'e' + e.id) + '</div></li>' : '<div class="tk-tx">' + ctx.esc(v.text) + '</div></li>');
  }
  function render(force) {
    var ts = L.turns(records, Date.now(), {note: noteOf}), ents = L.echo(term.entries, ts);
    var s = JSON.stringify([records.length && records[records.length - 1].seq, ts.map(function (t) { return t.state + (undoing[t.id] ? 'u' : '') +
      t.lines.map(function (l) { return l.detail ? '|' + l.seq + ':' + l.detail.length : ''; }).join(''); }), ents.map(function (e) { return e.id; }), term.failed, term.source, on]);
    if (s === sig && !force) return;
    sig = s;
    var bottom = L.stick(list.scrollTop, list.scrollHeight, list.clientHeight);
    var first = seen == null, seenIds = render.ids || {}, lastSeq = records.length ? records[records.length - 1].seq : 0;
    var grew = !first && !force && (lastSeq > seen || term.entries.some(function (e) { return !seenIds[e.id]; }));   // 새 기록·새 터미널 줄(점 — 내가 누른 것은 아님)
    var fresh = function (q) { return !first && q > seen; }, never = function () { return false; };
    var items = L.timeline(ts, ents), ids = {}, rows = [];
    copies = {};
    items.forEach(function (x) {                          // 줄마다 key + 맥박 없는 html — 같으면 있던 요소 그대로(patch)
      if (x.type === 'turn') { rows.push({key: 't' + x.turn.id, html: turnHtml(x.turn, never), make: function () { return turnHtml(x.turn, fresh); }}); return; }
      var e = x.entry; ids[e.id] = 1;
      rows.push({key: 'e' + e.id, html: termHtml(e, false), make: function () { return termHtml(e, !first && !seenIds[e.id]); }});
    });
    if (term.agent && (term.failed || term.source === 'none')) rows.push({key: 'quiet', html: '<li class="tk-quiet">' + NO_TERM + '</li>'});
    if (!rows.length) rows.push({key: 'empty', html: '<li class="tk-empty">' + (on ? '아래 입력창으로 보낸 요청과 AI 의 진행·답이 여기에 쌓여요' :
      '도우미로 열면 보낸 요청과 AI 의 진행·답이 여기에 남아요') + '</li>'});
    patch(rows);
    render.ids = ids;
    seen = records.length ? records[records.length - 1].seq : 0;
    if (bottom || first) list.scrollTop = list.scrollHeight;   // 맨 아래를 보고 있었으면 따라간다 — 위로 올려 읽는 중이면 그대로
    syncJump(grew);
  }

  /* ---------- 맨 아래로 단추(R50) ---------- */
  function syncJump(grew) {
    jumpSt = L.jump(jumpSt, {top: list.scrollTop, height: list.scrollHeight, client: list.clientHeight, grew: !!grew});
    if (jumpBtn.hidden === jumpSt.show) jumpBtn.hidden = !jumpSt.show;
    jumpDot.hidden = !jumpSt.unseen;
    var t = jumpSt.unseen ? '최신 메시지로 — 새 메시지가 있어요' : '최신 메시지로';
    if (jumpBtn.title !== t) { jumpBtn.title = t; jumpBtn.setAttribute('aria-label', t); }
  }
  list.addEventListener('scroll', function () { syncJump(false); }, {passive: true});
  jumpBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (list.scrollTo) list.scrollTo({top: list.scrollHeight, behavior: calm ? 'auto' : 'smooth'}); else list.scrollTop = list.scrollHeight;
  });

  function patch(rows) {                                 // 바뀐 줄만 새 요소로, 차례는 맞춘다(긴 기록에서 이벤트마다 전체를 다시 만들지 않게)
    var next = {}, tpl = document.createElement('template');
    rows.forEach(function (r, i) {
      var have = nodes[r.key], el;
      if (have && have.html === r.html) el = have.el;
      else { tpl.innerHTML = r.make ? r.make() : r.html; el = tpl.content.firstElementChild; }
      next[r.key] = {html: r.html, el: el};
      var at = list.children[i];
      if (at !== el) list.insertBefore(el, at || null);
    });
    while (list.children.length > rows.length) list.removeChild(list.lastElementChild);
    nodes = next;
  }
  function copy(text) {
    var ok = function () { ctx.toast('복사했어요'); };
    var old = function () {                               // 클립보드 API 가 없거나 막힘(권한) = 옛 길
      var ta = document.createElement('textarea'); ta.value = text; ta.style.cssText = 'position:fixed;left:-9999px;top:0';
      document.body.appendChild(ta); ta.select();
      var done = false; try { done = document.execCommand('copy'); } catch (e) { done = false; }
      ta.remove();
      if (done) ok(); else { ctx.toast('복사하지 못했어요 — 글을 골라 Ctrl+C 로 복사해 주세요'); console.warn('[hd] 대화 패널: 복사 실패'); }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(ok, old); else old();
  }

  /* ---------- 서버 ---------- */
  function fetchLog() {
    if (!on) return Promise.resolve();
    if (fetching) { again = true; return Promise.resolve(); }
    fetching = true;
    return ctx.api.call('GET', '/api/chat' + (seq == null ? '' : '?since=' + seq)).then(function (res) {
      var p = res && res.status === 200 ? L.parse(res.body) : null;
      if (!p) { if (res && res.status === 404) warnOnce('old', '도우미에 /api/chat 이 없어요(옛 도우미) — 기록 없이'); else warnOnce('bad', '/api/chat 답이 깨졌어요'); return; }
      records = p.reset ? p.records : L.merge(records, p.records);
      seq = p.seq; render();
    }, function (e) { warnOnce('net', '기록을 받지 못했어요(다시 시도): ' + (e && e.message || e)); })
      .then(function () { fetching = false; if (again) { again = false; fetchLog(); } });
  }
  function receiver() { return typeof window.__hdAgent === 'string' && window.__hdAgent ? window.__hdAgent : null; }
  function fetchTerm() {
    var ag = receiver();
    if (ag !== term.agent) { term = {agent: ag, entries: [], cursor: null, source: null, failed: false}; render(); }
    if (!on || !ag) return Promise.resolve();
    var q = '/api/agents/transcript?agent=' + encodeURIComponent(ag) + (term.cursor == null ? '' : '&since=' + encodeURIComponent(term.cursor));
    return ctx.api.call('GET', q).then(function (res) {
      if (ag !== term.agent) return;
      var p = res && res.status === 200 ? L.parseTranscript(res.body) : null;
      if (!p) { term.failed = true; warnOnce('term', '터미널 대화를 받지 못했어요(' + (res && res.status) + ')'); render(); return; }
      term.failed = false; term.source = p.source; term.cursor = p.cursor;
      term.entries = L.mergeEntries(term.entries, p.entries); render();
    }, function (e) { term.failed = true; warnOnce('term', '터미널 대화에 닿지 않아요: ' + (e && e.message || e)); render(); });
  }
  function soon() { clearTimeout(tick); tick = setTimeout(fetchLog, 80); }

  /* ---------- 턴: 누르기 · 되돌리기 ---------- */
  function turnOf(id) { return L.turns(records, Date.now()).filter(function (t) { return t.id === id; })[0] || null; }
  function focusTurn(t) {
    var ids = t.screens.filter(function (s) { return ctx.cardEl && ctx.cardEl(s); });
    if (!ids.length) { ctx.toast('이 요청이 닿은 화면이 판에 없어요'); return; }
    ids.forEach(function (s) { var c = ctx.cardEl(s); c.classList.remove('tk-hl'); void c.offsetWidth; c.classList.add('tk-hl'); setTimeout(function () { c.classList.remove('tk-hl'); }, 1800); });
    if (typeof ctx.focus === 'function') ctx.focus(ids); else warnOnce('focus', 'ctx.focus 가 없어요 — 강조만 해요');
  }
  function undo(t) {
    if (undoing[t.id]) return;
    undoing[t.id] = 1; render(true);
    var stamps = t.stamps.slice(), done = 0;
    var step = function () {
      if (!stamps.length) {
        return ctx.api.call('POST', '/api/chat', {kind: 'undone', turn: t.id}).then(function (res) {
          if (!res || res.status !== 200) warnOnce('undone', '되돌림 표시를 남기지 못했어요(' + (res && res.status) + ')');
        }).then(function () { ctx.toast('되돌렸어요 — 화면 ' + done + '개'); });
      }
      var stamp = stamps.shift();
      return ctx.api.call('POST', '/api/restore', A.body(stamp)).then(function (res) {
        var o = A.outcome(res);
        if (!o.ok) { ctx.toast('되돌리지 못했어요 — ' + o.msg); return; }
        done++;
        if (res.body && Array.isArray(res.body.changed) && res.body.changed.length) ctx.reload(res.body.changed, {stamp: o.next, echo: true});
        return step();
      });
    };
    step().catch(function (e) { ctx.toast('되돌리지 못했어요 — 도우미에 닿지 않아요'); console.warn('[hd] 대화 턴 되돌리기: ' + (e && e.message || e)); })
      .then(function () { delete undoing[t.id]; return fetchLog(); }).then(function () { render(true); });
  }
  list.addEventListener('click', function (e) {
    var cp = e.target.closest('.tk-copy');
    if (cp) { e.stopPropagation(); var tx = copies[cp.dataset.copy]; if (typeof tx === 'string') copy(tx); return; }
    var sl = window.getSelection && window.getSelection();
    if (sl && !sl.isCollapsed && String(sl).trim() && list.contains(sl.anchorNode)) return;   // 글을 골라 복사하는 중 = 턴 누르기 아님
    var li2 = e.target.closest('.tk-turn'); if (!li2) return;
    var t = turnOf(+li2.dataset.turn); if (!t) return;
    if (e.target.closest('.tk-undo')) { e.stopPropagation(); undo(t); return; }
    focusTurn(t);
  });
  list.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var li = e.target.closest && e.target.closest('.tk-turn'); if (!li || e.target !== li) return;
    e.preventDefault(); var t = turnOf(+li.dataset.turn); if (t) focusTurn(t);
  });
  host.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 판 고르기 풀기·끌기로 새지 않게(떠 있는 창일 때)

  /* ---------- 대화창이 보낸 요청 → ask 기록 ---------- */
  document.addEventListener('hd-chat-sent', function (e) {
    var d = e.detail || {};
    if (!on || typeof d.text !== 'string' || !d.text.trim()) return;
    ctx.api.call('POST', '/api/chat', {kind: 'ask', text: d.text, notes: d.notes || [], chips: d.chips || [], screens: d.screens || [], agent: d.agent || null})
      .then(function (res) { if (!res || res.status !== 200) warnOnce('ask', '보낸 글을 기록하지 못했어요(' + (res && res.status) + ')'); else soon(); },
            function (e2) { warnOnce('ask', '보낸 글을 기록하지 못했어요: ' + (e2 && e2.message || e2)); });
  });

  /* ---------- 서버 이벤트 ---------- */
  document.addEventListener('hd-event', function (e) {
    var ev = e.detail || {};
    if (REFRESH.indexOf(ev.type) >= 0) soon();
    if (ev.type === 'agent.transcript' && ev.agent && ev.agent === term.agent) {
      var p = L.parseTranscript(ev);
      if (p) { term.entries = L.mergeEntries(term.entries, p.entries); term.failed = false; if (!term.source) term.source = 'event'; render(); }
    }
  });

  /* ---------- 입력창 자리: 패널이 보이면 패널 아래로(S3) ---------- */
  function placeComposer() {
    var vis = shown();
    if (vis && !shownNow) { host.classList.remove('tk-in'); void host.offsetWidth; host.classList.add('tk-in'); list.scrollTop = list.scrollHeight; }
    shownNow = vis;
    var d = {host: vis ? foot : null, done: false};
    document.dispatchEvent(new CustomEvent('hd-composer', {detail: d}));
    if (!d.done) warnOnce('composer', '대화창(view-chat)이 붙지 않아 입력창을 패널로 옮기지 못했어요');
  }
  if (window.ResizeObserver) new ResizeObserver(function () { if (shown() !== shownNow) placeComposer(); syncJump(false); }).observe(host);   // 칸 높이가 바뀌면 맨 아래인지 다시
  else warnOnce('ro', 'ResizeObserver 가 없어 입력창 자리를 1초마다 봐요');
  setTimeout(placeComposer, 0);                              // view-chat 이 붙은 뒤(등록 차례가 이 파일 다음)

  setInterval(function () {
    if (!window.ResizeObserver && shown() !== shownNow) placeComposer();
    if (document.hidden || !shown()) return;
    fetchLog(); fetchTerm(); render();                      // 상태(10분 조용함)는 시간으로도 바뀐다
  }, EVERY);
  render(); fetchLog(); fetchTerm();
  return {refresh: function () { return fetchLog(); }, records: function () { return records.slice(); }, shown: shown};
}

HD.feature('chatLog', {needs: ['$', 'toast', 'esc', 'api', 'reload', 'cardEl', 'notes'], mount: mount});
})();
