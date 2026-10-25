/* View — 대화 패널(S3, 도크 패널 '대화' #pTalk): 요청 하나 = 턴 하나(오래된 것 위) — 내 요청 말풍선(글 + 칩) · 보냄 · 진행 줄(에이전트가 알린 터미널 출력) · 답 ·
   AI 반영 · 빌드 완료/실패(빨간 줄) · 끝 ✓ / 작업 중 회전. 규칙(턴·상태·줄·되돌릴 stamp·자동 스크롤·터미널 섞기)은 HD.chatLog(Model).
   상태(주인 이 파일, 저장 안 함 — 진실은 서버 .hd-chat.jsonl): 받은 기록 records + 마지막 seq · 터미널 줄 entries + cursor + 받는 곳 · 펼친 도구 줄 · 이미 본 seq(맥박).
   읽기: GET /api/chat?since= — 처음 · 서버 이벤트(view-live 의 document 'hd-event': request.sent · agent.* · ai.write · build.* · notes.changed) 뒤 ·
     실시간이 없을 때를 위해 패널이 보이는 동안 4초마다. 남기기: 대화창 의도 'hd-chat-sent' {text, chips, screens, notes, agent} → POST /api/chat ask ·
     턴 되돌리기 성공 → POST /api/chat undone.
   턴 누르기 = 닿은 카드 잠깐 강조(.card.tk-hl) + ctx.focus(ids)(셸: 그 카드들로 판 옮기기, 지금보다 크게는 안 함).
   [되돌리기](끝난 턴, AI 쓰기가 있을 때) = 48c 되살리기(POST /api/restore, HD.aiUndo.body/outcome) 를 stamp 마다 새것부터 — 거절되면 이유 토스트, 되살린 카드는 ctx.reload.
   입력창 자리(S3): 패널이 보이면(도크·떠 있는 창 어디든) 의도 'hd-composer' {host: 패널 아래 칸} → view-chat 이 같은 #hdchat 을 그리로 옮긴다, 안 보이면 {host:null} = 판 아래로.
   터미널 대화(S3b 계약): 받는 곳(window.__hdAgent)이 있으면 GET /api/agents/transcript?agent=&since=<cursor> + 이벤트 agent.transcript — 턴과 시간 차례로 섞는다.
     user = '터미널에서' 오른쪽 말풍선 · assistant = 에이전트 답 · tool = 회색 한 줄 '도구 · …'(누르면 펼침). 같은 요청은 한 번(HD.chatLog.echo). 없음·못 읽음 = 조용한 한 줄.
   움직임(FINDINGS §8): 새 줄 맥박 600ms · 패널 나타남 spring-fade 400ms · 진행 회전 1s — 움직임 줄이기면 모두 끔.
   HD.feature('chatLog', {needs: ['$', 'toast', 'esc', 'api', 'reload', 'cardEl']}) → {refresh(), records(), shown()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var EVERY = 4000;
var REFRESH = ['request.sent', 'agent.progress', 'agent.reply', 'ai.write', 'build.done', 'build.failed', 'notes.changed'];
var STATE_SAY = {running: '작업 중…', queued: '대기 중 — 읽는 에이전트를 기다려요', done: '끝', failed: '실패', decide: '결정 필요 — 메모에서 골라 주세요', undone: '되돌림'};
var NO_TERM = '이 터미널의 대화는 가져올 수 없어요';

var CSS =
  '#pTalk{padding:0;height:100%;min-height:0;display:flex;flex-direction:column;box-sizing:border-box}' +
  '#pTalk .tk-list{flex:1 1 auto;min-height:0;overflow-y:auto;margin:0;padding:10px 12px 4px;list-style:none;display:flex;flex-direction:column;gap:14px;scrollbar-width:thin}' +
  '#pTalk .tk-empty{margin:auto 0;padding:24px 8px;color:var(--ui-muted,#8a8a85);font-size:12.5px;text-align:center;line-height:1.5}' +
  '#pTalk .tk-foot{flex:none;padding:0 8px 8px}' +
  '#pTalk .tk-foot:empty{display:none}' +
  '#pTalk.tk-in{animation:tkIn .4s cubic-bezier(0.34,0.88,0.34,1)}' +
  '@keyframes tkIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}' +
  '#pTalk .tk-turn{display:flex;flex-direction:column;gap:6px;border-radius:10px;padding:2px;cursor:pointer;outline:none}' +
  '#pTalk .tk-turn:hover .tk-lines,#pTalk .tk-turn:focus-visible .tk-lines{background:#F6F6F3}' +
  '#pTalk .tk-ask{align-self:flex-end;max-width:88%;background:var(--ui-badge-soft,#E4E4DF);color:var(--ui-primary,#2b2b29);border-radius:14px 14px 4px 14px;padding:7px 11px;font-size:13px;line-height:18px;white-space:pre-wrap;word-break:break-word}' +
  '#pTalk .tk-ask.req{background:#F2F2EF;color:#6b6b66}' +
  '#pTalk .tk-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}' +
  '#pTalk .tk-chip{font-size:11px;font-weight:600;line-height:18px;padding:0 7px;border-radius:999px;background:#fff;color:#3a3a37;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#pTalk .tk-lines{list-style:none;margin:0;padding:4px 6px;border-radius:8px;display:flex;flex-direction:column;gap:3px}' +
  '#pTalk .tk-l{position:relative;padding-left:14px;font-size:12px;line-height:17px;color:#5f5f5a;word-break:break-word}' +
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
  '#pTalk .tk-term{display:flex;flex-direction:column;gap:3px}' +
  '#pTalk .tk-term[data-role="user"]{align-self:flex-end;max-width:88%;align-items:flex-end}' +
  '#pTalk .tk-term .tk-who{font-size:10.5px;color:var(--ui-muted,#8a8a85)}' +
  '#pTalk .tk-term[data-role="user"] .tk-tx{background:#F2F2EF;border-radius:14px 14px 4px 14px;padding:6px 10px}' +
  '#pTalk .tk-tx{font-size:13px;line-height:19px;white-space:pre-wrap;word-break:break-word;color:var(--ui-primary,#2b2b29)}' +
  '#pTalk details.tk-tool{font-size:11.5px;color:#7a7a75}#pTalk details.tk-tool summary{cursor:pointer;list-style:none;padding-left:14px;position:relative;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#pTalk details.tk-tool summary::before{content:"\\203A";position:absolute;left:3px}#pTalk details.tk-tool[open] summary::before{content:"\\2304"}' +
  '#pTalk details.tk-tool pre{margin:4px 0 0 14px;padding:6px 8px;background:#F6F6F3;border-radius:6px;font:11px/15px ui-monospace,Menlo,monospace;white-space:pre-wrap;max-height:160px;overflow:auto}' +
  '#pTalk .tk-quiet{font-size:11.5px;color:var(--ui-muted,#8a8a85);text-align:center}' +
  '#pTalk .tk-new{animation:tkPulse .6s ease-out;transform-origin:left center}' +
  '@keyframes tkPulse{0%{transform:scale(1)}50%{transform:scale(1.02)}100%{transform:scale(1)}}' +
  '.card.tk-hl .phone{box-shadow:0 0 0 3px var(--ui-primary,#2b2b29),0 8px 24px rgba(0,0,0,.18)!important;transition:box-shadow .3s}' +
  '@media (prefers-reduced-motion: reduce){#pTalk.tk-in,#pTalk .tk-new,#pTalk .tk-turn[data-state="running"] .tk-ic{animation:none}.card.tk-hl .phone{transition:none}}';

function mount(ctx) {
  var L = HD.chatLog, A = HD.aiUndo, host = ctx.$('#pTalk');
  if (!host) { console.warn('[hd] 대화 패널: 자리(#pTalk)가 없어요 — 대화 패널 없이'); return {}; }
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  host.innerHTML = '<ol class="tk-list" aria-label="대화"></ol><div class="tk-foot"></div>';
  var list = host.querySelector('.tk-list'), foot = host.querySelector('.tk-foot');
  var on = !!(ctx.api && ctx.api.on), records = [], seq = null, seen = null, sig = null, warned = {};
  var term = {agent: null, entries: [], cursor: null, source: null, failed: false}, openTools = {}, undoing = {};
  var fetching = false, again = false, tick = 0, shownNow = false;

  function warnOnce(k, m) { if (warned[k]) return; warned[k] = 1; console.warn('[hd] 대화 패널: ' + m); }
  function shown() { return host.getClientRects().length > 0; }

  /* ---------- 그리기 ---------- */
  function chipHtml(c) { return '<span class="tk-chip" title="' + ctx.esc(c) + '">' + ctx.esc(c) + '</span>'; }
  function turnHtml(t, fresh) {
    var a = t.ask, say = STATE_SAY[t.state] || '';
    var ask = a ? '<div class="tk-ask' + (a.fromRequest ? ' req' : '') + (fresh(t.recs[0].seq) ? ' tk-new' : '') + '">' + ctx.esc(a.text) +
      (a.chips.length ? '<div class="tk-chips">' + a.chips.map(chipHtml).join('') + '</div>' : '') + '</div>' : '';
    var lines = t.lines.length ? '<ol class="tk-lines">' + t.lines.map(function (l) {
      return '<li class="tk-l' + (fresh(l.seq) ? ' tk-new' : '') + '" data-kind="' + l.kind + '" data-tone="' + (l.tone || '') + '">' + ctx.esc(l.text) + '</li>';
    }).join('') + '</ol>' : '';
    var ic = t.state === 'done' ? '✓' : t.state === 'failed' ? '!' : '';
    var undo = t.undoable && on ? '<button type="button" class="tk-undo"' + (undoing[t.id] ? ' disabled' : '') + ' title="이 요청으로 AI 가 바꾼 화면을 되돌려요">' +
      (undoing[t.id] ? '되돌리는 중…' : '되돌리기') + '</button>' : '';
    return '<li class="tk-turn" data-turn="' + t.id + '" data-state="' + t.state + '" tabindex="0" title="누르면 이 요청이 닿은 화면으로">' + ask + lines +
      '<div class="tk-st"><span class="tk-ic" aria-hidden="true">' + ic + '</span><span class="tk-say">' + ctx.esc(say) + '</span>' + undo + '</div></li>';
  }
  function termHtml(e, fresh) {
    var v = L.entryView(e), nw = fresh ? ' tk-new' : '';
    if (v.role === 'tool') return '<li class="tk-term' + nw + '" data-role="tool" data-id="' + ctx.esc(e.id) + '"><details class="tk-tool"' + (openTools[e.id] ? ' open' : '') +
      '><summary>' + ctx.esc(v.label) + '</summary><pre>' + ctx.esc(v.text) + '</pre></details></li>';
    return '<li class="tk-term' + nw + '" data-role="' + v.role + '" data-id="' + ctx.esc(e.id) + '">' + (v.label ? '<span class="tk-who">' + ctx.esc(v.label) + '</span>' : '') +
      '<div class="tk-tx">' + ctx.esc(v.text) + '</div></li>';
  }
  function render(force) {
    var ts = L.turns(records, Date.now()), ents = L.echo(term.entries, ts);
    var s = JSON.stringify([records.length && records[records.length - 1].seq, ts.map(function (t) { return t.state + (undoing[t.id] ? 'u' : ''); }), ents.map(function (e) { return e.id; }), term.failed, term.source, on]);
    if (s === sig && !force) return;
    sig = s;
    var bottom = L.stick(list.scrollTop, list.scrollHeight, list.clientHeight);
    var first = seen == null, seenIds = render.ids || {};
    var fresh = function (q) { return !first && q > seen; };
    var items = L.timeline(ts, ents), ids = {};
    var html = items.map(function (x) {
      if (x.type === 'turn') return turnHtml(x.turn, fresh);
      ids[x.entry.id] = 1;
      return termHtml(x.entry, !first && !seenIds[x.entry.id]);
    }).join('');
    if (term.agent && (term.failed || term.source === 'none')) html += '<li class="tk-quiet">' + NO_TERM + '</li>';
    if (!html) html = '<li class="tk-empty">' + (on ? '아래 입력창으로 보낸 요청과 AI 의 진행·답이 여기에 쌓여요' :
      '도우미로 열면 보낸 요청과 AI 의 진행·답이 여기에 남아요') + '</li>';
    list.innerHTML = html;
    render.ids = ids;
    seen = records.length ? records[records.length - 1].seq : 0;
    if (bottom || first) list.scrollTop = list.scrollHeight;   // 맨 아래를 보고 있었으면 따라간다 — 위로 올려 읽는 중이면 그대로
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
    var d = e.target.closest('details.tk-tool');
    if (d) { var li = d.closest('.tk-term'); setTimeout(function () { if (li) openTools[li.dataset.id] = d.open; }, 0); return; }
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
  if (window.ResizeObserver) new ResizeObserver(function () { if (shown() !== shownNow) placeComposer(); }).observe(host);
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

HD.feature('chatLog', {needs: ['$', 'toast', 'esc', 'api', 'reload', 'cardEl'], mount: mount});
})();
