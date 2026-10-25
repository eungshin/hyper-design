/* Model — 대화 패널(S3) 규칙: 서버 대화 기록(.hd-chat.jsonl 한 줄 = {seq, at, turn, kind, …}) → 턴 · 턴 상태 · 보일 줄 · 닿은 화면 · 되돌릴 stamp,
   그리고 받는 곳 터미널의 대화(S3b transcript {id, role, text, at})를 시간 차례로 섞기. DOM·저장소·메시지를 쓰지 않는다.
   기록 kind(서버 chat_log.py): ask(보낸 글·칩·화면·받는 곳 이름) · sent(to·via·요청문) · progress(에이전트가 알린 줄 = 터미널 출력) · reply(답 글·상태) ·
     write(AI 반영 줄 — stamp = 48c 되살리기) · built(빌드 완료) · failed(빌드 실패, 빨간 줄) · undone(턴 되돌림).
   parse(body) → {seq, records, reset} | null(깨진 답) · merge(have, incoming) → seq 차례, 겹친 seq 하나만.
   turns(records, now) → [{id, at, lastAt, ask:{text, chips, screens, agent, fromRequest}|null, lines:[{seq, kind, text, tone}], state, screens, stamps, undoable}]
     차례 = 처음 나온 차례(오래된 것 위). state(아래 차례로 처음 맞는 것): undone(되돌림) · failed(마지막 빌드 실패 뒤 쓰기·빌드·답이 없음) ·
     decide/done(답이 있음 — 마지막 답 상태 decide = decide) · done(마지막 턴이 아님 · IDLE_MS 동안 조용함) · queued(via queue 이고 진행·쓰기 없음) · running.
     built 줄은 그 턴에 AI 쓰기가 앞서 있을 때만(사람 편집의 빌드는 보이지 않음). ask 가 없으면 요청문 첫 줄로 말풍선(fromRequest).
     undoable = 되돌릴 stamp 가 있고 running·queued·undone 이 아님 · stamps = AI 쓰기 stamp(새것 먼저, 한 번씩).
   stick(top, height, client) → 맨 아래 근처(STICK px)인가 — 위로 올려 읽는 중이면 새 줄이 와도 자동 스크롤하지 않는다.
   터미널 대화(S3b 계약 — 공급자 모름, 모양만): parseTranscript(body) → {entries, cursor, source} | null · mergeEntries(have, new) → id 하나씩, at 차례 ·
     echo(entries, turns) → 캔버스 요청이 터미널에도 찍힌 user 줄 빼기(요청 글 또는 요청문 앞부분이 들어 있으면 같은 것) ·
     timeline(turns, entries) → [{type:'turn', turn} | {type:'term', entry}] 시간(at) 차례 · entryView(e) → {role, label, text, short}(tool = '도구 · <짧게>').
   HD.chatLog = {IDLE_MS, STICK, parse, merge, turns, state, stick, parseTranscript, mergeEntries, echo, timeline, entryView} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var IDLE_MS = 10 * 60 * 1000;                            // 마지막 턴이 이만큼 조용하면 끝난 것으로(답을 안 하는 에이전트)
var STICK = 24;
var ASK_CUT = 160, SHORT_CUT = 60, ECHO_MIN = 4, ECHO_HEAD = 80;
var VIA0 = {event: '실시간', paseo: 'Paseo', claude: 'Claude', queue: '대기열'};
var KINDS = ['ask', 'sent', 'progress', 'reply', 'write', 'built', 'failed', 'undone'];

function flat(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function cut(s, n) { s = flat(s); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
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
function firstLine(t) {
  var ls = String(t || '').split('\n').map(flat).filter(function (x) { return x && !/^[#>\-=*]+$/.test(x); });
  return ls.length ? cut(ls[0].replace(/^#+\s*/, ''), ASK_CUT) : '';
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

function lineOf(r, t, wrote) {
  switch (r.kind) {
    case 'sent': return {seq: r.seq, kind: 'sent', text: sentText(r, t.ask), tone: 'muted'};
    case 'progress': return {seq: r.seq, kind: 'progress', text: flat(r.text), tone: 'muted'};
    case 'reply': return {seq: r.seq, kind: 'reply', text: (r.status === 'decide' ? '결정 필요 · ' : '') + (flat(r.text) || flat(r.rkind) || '답했어요'), tone: r.status === 'decide' ? 'accent' : ''};
    case 'write': return {seq: r.seq, kind: 'write', text: flat(r.label) || 'AI 반영 · ' + (r.screen || ''), tone: 'ok'};
    case 'built': return wrote ? {seq: r.seq, kind: 'built', text: '빌드 완료', tone: 'muted'} : null;
    case 'failed': return {seq: r.seq, kind: 'failed', text: '빌드 실패' + (flat(r.reason) ? ' — ' + cut(r.reason, 160) : ''), tone: 'red'};
    case 'undone': return {seq: r.seq, kind: 'undone', text: '되돌렸어요', tone: 'muted'};
  }
  return null;
}

function turns(records, now) {
  var order = [], by = {};
  merge([], records).forEach(function (r) {
    var t = by[r.turn];
    if (!t) { t = by[r.turn] = {id: r.turn, at: r.at, lastAt: r.at, recs: []}; order.push(t); }
    t.recs.push(r);
    if (r.kind !== 'built' && r.kind !== 'undone') t.lastAt = Math.max(t.lastAt, r.at);
  });
  return order.map(function (t, i) {
    var ask = t.recs.filter(function (r) { return r.kind === 'ask'; })[0], sent = t.recs.filter(function (r) { return r.kind === 'sent'; })[0];
    t.ask = ask ? {text: flat(ask.text), chips: (ask.chips || []).slice(), screens: (ask.screens || []).slice(), agent: ask.agent || null, fromRequest: false}
      : sent && firstLine(sent.text) ? {text: firstLine(sent.text), chips: [], screens: [], agent: null, fromRequest: true} : null;
    var wrote = false;
    t.lines = [];
    t.recs.forEach(function (r) { if (r.kind === 'write') wrote = true; var l = lineOf(r, t, wrote); if (l && l.text) t.lines.push(l); });
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
  var text = String(e.text || '').trim(), short = cut(text.split('\n')[0], SHORT_CUT);
  if (e.role === 'tool') return {role: 'tool', label: '도구 · ' + (short || '…'), text: text, short: short};
  if (e.role === 'user') return {role: 'user', label: '터미널에서', text: text, short: short};
  return {role: 'assistant', label: '', text: text, short: short};
}

HD.chatLog = {IDLE_MS: IDLE_MS, STICK: STICK, parse: parse, merge: merge, turns: turns, state: state, stick: stick,
              parseTranscript: parseTranscript, mergeEntries: mergeEntries, echo: echo, timeline: timeline, entryView: entryView};
})();
