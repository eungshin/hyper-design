/* Model — 대화 패널(S3) 규칙: 서버 대화 기록(.hd-chat.jsonl 한 줄 = {seq, at, turn, kind, …}) → 턴 · 턴 상태 · 보일 줄 · 닿은 화면 · 되돌릴 stamp,
   그리고 받는 곳 터미널의 대화(S3b transcript {id, role, text, at})를 시간 차례로 섞기. DOM·저장소·메시지를 쓰지 않는다.
   기록 kind(서버 chat_log.py): ask(보낸 글·칩·화면·받는 곳 이름) · sent(to·via·요청문) · progress(에이전트가 알린 줄 = 터미널 출력) · reply(답 글·상태) ·
     write(AI 반영 줄 — stamp = 48c 되살리기) · built(빌드 완료) · failed(빌드 실패, 빨간 줄) · undone(턴 되돌림).
   parse(body) → {seq, records, reset} | null(깨진 답) · merge(have, incoming) → seq 차례, 겹친 seq 하나만.
   turns(records, now) → [{id, at, lastAt, ask:{text, chips, screens, agent, fromRequest}|null, lines:[{seq, kind, text, tone}], state, screens, stamps, undoable}]
     차례 = 처음 나온 차례(오래된 것 위). state(아래 차례로 처음 맞는 것): undone(되돌림) · failed(마지막 빌드 실패 뒤 쓰기·빌드·답이 없음) ·
     decide/done(답이 있음 — 마지막 답 상태 decide = decide) · done(마지막 턴이 아님 · IDLE_MS 동안 조용함) · queued(via queue 이고 진행·쓰기 없음) · running.
     built 줄은 그 턴에 AI 쓰기가 앞서 있을 때만(사람 편집의 빌드는 보이지 않음). ask 가 없으면 요청문 전체로 말풍선(fromRequest).
     undoable = 되돌릴 stamp 가 있고 running·queued·undone 이 아님 · stamps = AI 쓰기 stamp(새것 먼저, 한 번씩).
   stick(top, height, client) → 맨 아래 근처(STICK px)인가 — 위로 올려 읽는 중이면 새 줄이 와도 자동 스크롤하지 않는다.
   jump(prev, {top, height, client, grew}) → {show, unseen} — '맨 아래로' 단추(R50, Slack·ChatGPT·Claude.ai 의 scroll-to-bottom):
     맨 아래(stick)가 아니면 보임 · 올려 읽는 중에 새 줄이 오면(grew) unseen(점) — 맨 아래로 오면 둘 다 꺼짐. 숫자가 아닌 값 = 숨김(맨 아래로 침).
     보이는 문턱 = 따라가기 문턱(STICK) 하나 — 자동으로 따라가지 않는 동안은 늘 단추가 있다(사이 틈에서 새 줄을 놓치지 않게).
   터미널 대화(S3b 계약 — 공급자 모름, 모양만): parseTranscript(body) → {entries, cursor, source} | null · mergeEntries(have, new) → id 하나씩, at 차례 ·
     echo(entries, turns) → 캔버스 요청이 터미널에도 찍힌 user 줄 빼기(요청 글 또는 요청문 앞부분이 들어 있으면 같은 것) ·
     timeline(turns, entries) → [{type:'turn', turn} | {type:'term', entry}] 시간(at) 차례 · entryView(e) → {role, label, text, short}(short = 첫 줄 · tool label = '도구 · <첫 줄>').
   늘 전문(R24 · login#7): 보낸 글 · 요청문 말풍선 · 진행 · 답 · 빌드 실패 이유 · 터미널 줄(도구 = 첫 줄 요약 + 부른 입력 전체)을 자르거나 접지 않고
     줄바꿈 그대로(앞뒤 공백만 걷음). 그리기 나누기 —
     blocks(text) → [{type:'text', text} | {type:'code', lang, text}] (``` 울타리 코드 덩이, 닫히지 않으면 끝까지 코드) · spans(text) → [{code, text}] (`인라인 코드`, 짝 없는 ` 는 글).
   메모의 답 설명(옛 기록 보충): 옛 reply 기록(42f8c85 전 · 옛 도우미)은 요약 칸만 있다 — memoDetail(rec, note) → 그 메모(.replies)에서 같은 답
     (종류 rkind + 요약 칸 글 — 답변 text · 반영됨 what · 일부 done · 질문 question, 안 맞으면 마지막 AI 답)의 detail | ''(없음 · 기록이 이미 detail 을 담음).
     turns(records, now, {note: id → 메모|null}) 이면 답 줄에 detail 칸(전체 — 접지 않음).
   HD.chatLog = {IDLE_MS, STICK, parse, merge, turns, state, stick, jump, parseTranscript, mergeEntries, echo, timeline, entryView, blocks, spans, memoDetail} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var IDLE_MS = 10 * 60 * 1000;                            // 마지막 턴이 이만큼 조용하면 끝난 것으로(답을 안 하는 에이전트)
var STICK = 24;
var ECHO_MIN = 4, ECHO_HEAD = 80;
var VIA0 = {event: '실시간', paseo: 'Paseo', claude: 'Claude', queue: '대기열'};
var HEADS = {'답변': 'text', '반영됨': 'what', '일부': 'done', '질문': 'question'};   // 답 종류 → 요약 칸(annotation.js FIELDS · chat_log.reply_text)
var KINDS = ['ask', 'sent', 'progress', 'reply', 'write', 'built', 'failed', 'undone'];

function flat(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function whole(s) { return String(s == null ? '' : s).replace(/\r\n?/g, '\n').replace(/^\s*\n/, '').replace(/\s+$/, '').replace(/^[ \t]+/, ''); }   // 답 글 = 앞뒤만 걷기(줄바꿈·들여쓰기 그대로, R24)
function int(v) { return typeof v === 'number' && isFinite(v) && Math.floor(v) === v; }
function okRec(r) { return !!r && typeof r === 'object' && int(r.seq) && int(r.at) && int(r.turn) && KINDS.indexOf(r.kind) >= 0; }

function parse(body) {
  if (!body || typeof body !== 'object' || !int(body.seq) || !Array.isArray(body.records)) return null;
  return {seq: body.seq, records: body.records.filter(okRec), reset: body.reset === true};
}
function merge(have, incoming) {
  var by = {};
  (have || []).concat(incoming || []).forEach(function (r) { if (okRec(r)) by[r.seq] = r; });
  return Object.keys(by).map(function (k) { return by[k]; }).sort(function (a, b) { return a.seq - b.seq; });
}

function via(v) { var V = HD.chat && HD.chat.VIA || VIA0; return V[v] || null; }
function sentText(r, ask) {
  if (r.via === 'queue' || !via(r.via)) return '보냄 · 대기열 — 읽는 에이전트를 기다려요';
  return '보냄 · ' + (ask && ask.agent || r.to || 'AI') + ' (' + via(r.via) + ')';
}

function state(t, isLast, now) {
  var rs = t.recs, has = function (k) { return rs.some(function (r) { return r.kind === k; }); };
  if (has('undone')) return 'undone';
  var lf = -1; rs.forEach(function (r, i) { if (r.kind === 'failed') lf = i; });
  if (lf >= 0 && !rs.slice(lf + 1).some(function (r) { return r.kind === 'write' || r.kind === 'built' || r.kind === 'reply'; })) return 'failed';
  var reps = rs.filter(function (r) { return r.kind === 'reply'; });
  if (reps.length) return reps[reps.length - 1].status === 'decide' ? 'decide' : 'done';
  if (!isLast) return 'done';
  if (typeof now === 'number' && now - t.lastAt > IDLE_MS) return 'done';
  var sent = rs.filter(function (r) { return r.kind === 'sent'; })[0];
  if (sent && sent.via === 'queue' && !has('progress') && !has('write')) return 'queued';
  return 'running';
}

/* ---------- 메모의 답 설명(옛 기록 보충) ---------- */
function headOf(r) { var k = HEADS[r && r.kind]; return k && typeof r[k] === 'string' ? whole(r[k]) : ''; }
function memoDetail(rec, note) {
  if (!rec || rec.kind !== 'reply' || typeof rec.note !== 'string' || !rec.note) return '';
  if (!note || typeof note !== 'object' || !Array.isArray(note.replies)) return '';
  var ai = note.replies.filter(function (r) { return r && typeof r === 'object' && HEADS[r.kind]; });
  if (!ai.length) return '';
  var text = whole(rec.text), kind = typeof rec.rkind === 'string' ? rec.rkind : '';
  var same = ai.filter(function (r) { return headOf(r) && headOf(r) === text && (!kind || r.kind === kind); });
  var r = same.length ? same[same.length - 1] : ai[ai.length - 1];
  var d = typeof r.detail === 'string' ? whole(r.detail) : '';
  if (!d || d === text || text.indexOf(d) >= 0) return '';   // 기록이 이미 detail 을 담음(42f8c85 뒤 기록) = 두 번 보이지 않게
  return d;
}

function lineOf(r, t, wrote, opts) {
  switch (r.kind) {
    case 'sent': return {seq: r.seq, kind: 'sent', text: sentText(r, t.ask), tone: 'muted'};
    case 'progress': return {seq: r.seq, kind: 'progress', text: whole(r.text), tone: 'muted'};
    case 'reply':
      var l = {seq: r.seq, kind: 'reply', text: (r.status === 'decide' ? '결정 필요 · ' : '') + (whole(r.text) || flat(r.rkind) || '답했어요'), tone: r.status === 'decide' ? 'accent' : ''};
      var d = opts && typeof opts.note === 'function' && r.note ? memoDetail(r, opts.note(r.note)) : '';
      if (d) l.detail = d;
      return l;
    case 'write': return {seq: r.seq, kind: 'write', text: flat(r.label) || 'AI 반영 · ' + (r.screen || ''), tone: 'ok'};
    case 'built': return wrote ? {seq: r.seq, kind: 'built', text: '빌드 완료', tone: 'muted'} : null;
    case 'failed': return {seq: r.seq, kind: 'failed', text: '빌드 실패' + (whole(r.reason) ? ' — ' + whole(r.reason) : ''), tone: 'red'};
    case 'undone': return {seq: r.seq, kind: 'undone', text: '되돌렸어요', tone: 'muted'};
  }
  return null;
}

function turns(records, now, opts) {
  var order = [], by = {};
  merge([], records).forEach(function (r) {
    var t = by[r.turn];
    if (!t) { t = by[r.turn] = {id: r.turn, at: r.at, lastAt: r.at, recs: []}; order.push(t); }
    t.recs.push(r);
    if (r.kind !== 'built' && r.kind !== 'undone') t.lastAt = Math.max(t.lastAt, r.at);
  });
  return order.map(function (t, i) {
    var ask = t.recs.filter(function (r) { return r.kind === 'ask'; })[0], sent = t.recs.filter(function (r) { return r.kind === 'sent'; })[0];
    t.ask = ask ? {text: whole(ask.text), chips: (ask.chips || []).slice(), screens: (ask.screens || []).slice(), agent: ask.agent || null, fromRequest: false}
      : sent && whole(sent.text) ? {text: whole(sent.text), chips: [], screens: [], agent: null, fromRequest: true} : null;   // ask 가 없으면 요청문 전체(login#7)
    var wrote = false;
    t.lines = [];
    t.recs.forEach(function (r) { if (r.kind === 'write') wrote = true; var l = lineOf(r, t, wrote, opts); if (l && l.text) t.lines.push(l); });
    t.state = state(t, i === order.length - 1, now);
    var sc = [], add = function (s) { if (typeof s === 'string' && s && sc.indexOf(s) < 0) sc.push(s); };
    if (t.ask) t.ask.screens.forEach(add);
    t.recs.forEach(function (r) { add(r.screen); (r.kind === 'failed' || r.kind === 'built' ? [] : r.screens || []).forEach(add); });
    t.screens = sc;
    t.stamps = t.recs.filter(function (r) { return r.kind === 'write' && typeof r.stamp === 'string' && r.stamp; }).map(function (r) { return r.stamp; })
      .reverse().filter(function (s, k, a) { return a.indexOf(s) === k; });
    t.undoable = t.stamps.length > 0 && ['running', 'queued', 'undone'].indexOf(t.state) < 0;
    return t;
  });
}

function stick(top, height, client) { return height - top - client <= STICK; }
function jump(prev, m) {
  m = m || {};
  if (![m.top, m.height, m.client].every(function (v) { return typeof v === 'number' && isFinite(v); })) return {show: false, unseen: false};
  var at = stick(m.top, m.height, m.client);
  return {show: !at, unseen: !at && (!!(prev && prev.unseen) || !!m.grew)};
}

/* ---------- 터미널 대화(S3b 계약) ---------- */
var ROLES = ['user', 'assistant', 'tool'];
function okEntry(e) { return !!e && typeof e === 'object' && typeof e.id === 'string' && !!e.id && ROLES.indexOf(e.role) >= 0 && typeof e.text === 'string' && int(e.at); }
function parseTranscript(body) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.entries)) return null;
  return {entries: body.entries.filter(okEntry), cursor: body.cursor == null ? null : body.cursor, source: typeof body.source === 'string' ? body.source : 'none'};
}
function mergeEntries(have, incoming) {
  var by = {}, out = [];
  (have || []).concat(incoming || []).forEach(function (e) { if (okEntry(e)) { if (!by[e.id]) out.push(e); by[e.id] = e; } });
  return out.map(function (e) { return by[e.id]; }).sort(function (a, b) { return a.at - b.at; });
}
function norm(s) { return flat(s).toLowerCase(); }
function echo(entries, ts) {
  var asks = [], heads = [];
  (ts || []).forEach(function (t) {
    if (t.ask && !t.ask.fromRequest && norm(t.ask.text).length >= ECHO_MIN) asks.push(norm(t.ask.text));
    t.recs.forEach(function (r) { if (r.kind === 'sent' && r.text) { var h = norm(r.text).slice(0, ECHO_HEAD); if (h.length >= ECHO_MIN) heads.push(h); } });
  });
  return (entries || []).filter(function (e) {
    if (e.role !== 'user') return true;
    var x = norm(e.text);
    return !asks.some(function (a) { return x.indexOf(a) >= 0; }) && !heads.some(function (h) { return x.indexOf(h) >= 0; });
  });
}
function timeline(ts, entries) {
  var items = (ts || []).map(function (t, i) { return {type: 'turn', at: t.at, k: i, turn: t}; })
    .concat((entries || []).map(function (e, i) { return {type: 'term', at: e.at, k: i, entry: e}; }));
  items.sort(function (a, b) { return a.at - b.at || (a.type === b.type ? a.k - b.k : a.type === 'turn' ? -1 : 1); });
  return items.map(function (x) { return x.type === 'turn' ? {type: 'turn', turn: x.turn} : {type: 'term', entry: x.entry}; });
}
function entryView(e) {
  var text = whole(e.text), short = flat(text.split('\n')[0]);
  if (e.role === 'tool') return {role: 'tool', label: '도구 · ' + (short || '…'), text: text, short: short};
  if (e.role === 'user') return {role: 'user', label: '터미널에서', text: text, short: short};
  return {role: 'assistant', label: '', text: text, short: short};
}

/* ---------- 답 글 나누기(R24 — View 가 코드 덩이를 pre 로) ---------- */
var FENCE = /^ {0,3}(`{3,}|~{3,})\s*([\w+#.-]*)\s*$/;
function blocks(text) {
  var out = [], buf = [], code = null;
  var push = function () { var t = buf.join('\n').replace(/^\n+|\n+$/g, ''); if (t) out.push({type: 'text', text: t}); buf = []; };
  String(text == null ? '' : text).replace(/\r\n?/g, '\n').split('\n').forEach(function (ln) {
    var m = FENCE.exec(ln);
    if (code) {
      if (m && !m[2] && m[1].charAt(0) === code.mark.charAt(0) && m[1].length >= code.mark.length) { out.push({type: 'code', lang: code.lang, text: code.lines.join('\n')}); code = null; }
      else code.lines.push(ln);
      return;
    }
    if (m) { push(); code = {mark: m[1], lang: m[2] || '', lines: []}; return; }
    buf.push(ln);
  });
  if (code) { push(); out.push({type: 'code', lang: code.lang, text: code.lines.join('\n')}); }   // 닫히지 않은 울타리 = 끝까지 코드(쓰는 중인 답)
  else push();
  return out;
}
function spans(text) {
  var s = String(text == null ? '' : text), out = [], re = /`([^`\n]+)`/g, at = 0, m;
  while ((m = re.exec(s))) {
    if (m.index > at) out.push({code: false, text: s.slice(at, m.index)});
    out.push({code: true, text: m[1]}); at = re.lastIndex;
  }
  if (at < s.length) out.push({code: false, text: s.slice(at)});
  return out;
}

HD.chatLog = {IDLE_MS: IDLE_MS, STICK: STICK, parse: parse, merge: merge, turns: turns, state: state, stick: stick, jump: jump,
              parseTranscript: parseTranscript, mergeEntries: mergeEntries, echo: echo, timeline: timeline, entryView: entryView, blocks: blocks, spans: spans, memoDetail: memoDetail};
})();
