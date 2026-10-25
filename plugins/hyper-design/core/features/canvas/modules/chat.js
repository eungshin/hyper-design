/* Model — 하단 대화창 규칙: 고른 것 → 칩, 칩 + 글 → 메모 초안·범위, 마지막 요청 → 상태 한 줄. DOM·저장소·메시지를 쓰지 않는다(S1).
   칩 = {key, kind:'screen'|'el', screen, label, h?, app?} — chips({ids, titleOf, el}) : 고른 카드마다 [화면 이름](겹침·빈 값 빼고 차례 그대로),
     고른 요소 el = {screen, h:hd-hit, app} 가 있으면 그 화면 칩(없으면 앞에 더함) + [TAG "글"] 칩. visible(chips, dismissed) = 지운 칩(×) 빼기,
     prune(dismissed, chips) = 지금 칩에 없는 지운 표시 버리기(다시 고르면 다시 보임).
   범위: scope(chips) = all(칩 없음) · screen · element(요소 칩 있음), scopeLabel = 칩 줄 앞 말.
   build(chips, text, {first, titleOf}, mkId) → {memos, why} — 메모 모양·요청문은 지금 메모와 같다(셸 commitPop · memo-batch.build 재사용):
     요소 칩마다 요소 메모(범위 칸 없음 = 이 요소, quote·src 그대로 — 앱 카드면 요청문 '소스:' 줄) → 요소 칩이 없는 화면 칩들은 memo-batch.build(scope screen),
     칩이 없으면 첫 화면에 scope all 메모 하나. 글이 비었거나 화면이 없으면 memos [] + why(한국어 한 줄).
   상태: stage(n, busyItem, inflight) — 메모 하나의 단계(sending·unsent·sent·queued·working·decide·partial·applied·answered, 메모가 없음 = 바로 반영돼 빠짐 = applied).
     line(last, find, busyOf, inflight, opt?{progress, titleOf}) → {stage, text, req}|null — 여러 메모면 가장 앞선 단계(STAGES 차례) + 끝난 수 (k/N).
     진행(S2, 47-4b): progress(p, ev, screens) → {step:'working'|'landed'|'done', screen} | p — 요청 화면(screens, 비면 아무 화면)의 claim · AI 쓰기(screen.written ai · ai.write) · release.
       opt.progress 가 있고 손이 필요한 단계(sending·unsent·decide)가 아니면 줄 = 'AI 작업 중 · <화면>' · '반영됨 · <화면>' · '끝'(+ ' · ' 짧은 답, stage working·applied·done).
     받는 곳(47-5b): progress(p, ev, screens, ids) — ids = 이 요청의 메모 id. request.sent(notes 가 ids 와 겹침) = {step:'sent', via, to}(처음·sent 일 때만 — 뒤로 가지 않음),
       agent.progress(받는 곳의 것 · 받는 곳을 모르면 아무 에이전트) = {step:'progress', text, screen, via, to}, agent.reply(note 가 ids 안) = {step:'replied', kind, status, to}.
       줄 = '보냄 · <이름> (실시간|Paseo|Claude)' · '보냄 · 대기열 — …'(via queue) · 'AI 작업 중 · <진행 글>' · '답 옴 · <짧은 답|종류>'. opt.agentName(id) → 이름(없으면 id).
   마지막 요청 record(text, memos, at) = {text, ids, at} · parseLast(raw) → {last, bad}(깨졌으면 bad — 셸 아닌 View 가 [hd] 경고)
   칩 줄 접기(S1c): fold(chips, open) → {shown, more} — 3개까지는 다, 넘으면 앞 2개(+ 고른 요소 칩은 늘) + '외 N개'(more), open = 펼침(다 보임).
   placeholder(chips) — 범위를 칩이 아니라 입력 안내 글로: 칩 없음 = '모든 화면에 대해 …', 있으면 '무엇을 바꿀까요?'.
   HD.chat = {VIA, PLACEHOLDER, ALL, STAGES, tagOf, elLabel, chips, visible, prune, scope, scopeLabel, fold, placeholder, build, stage, line, progress, record, parseLast} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var PLACEHOLDER = '모든 화면에 대해 무엇을 바꾸거나 만들까요?';   // 고른 것 없음 = 범위 모든 화면(S1c — 칩 대신)
var PLACEHOLDER_PICKED = '무엇을 바꿀까요?';
var FOLD_AT = 3, FOLD_KEEP = 2;                          // 칩이 3개를 넘으면 앞 2개 + 외 N개
var ALL = '모든 화면';
var CUT = 20;                                            // 요소 칩 글 최대 글자(넘으면 …)
var STAGES = ['sending', 'unsent', 'decide', 'working', 'queued', 'sent', 'partial', 'answered', 'applied'];   // 여럿이면 앞의 것이 줄을 맡는다
var SAY = {
  sending: '보내는 중…',
  unsent: '보내지 못했어요 — 위쪽 [보내기]로 다시 보내 주세요',
  decide: '결정 필요 — 메모에서 답을 골라 주세요',
  working: 'AI 작업 중…',
  queued: '보냄 · 대기열 — 터미널 에이전트가 아직 읽지 않았어요',
  sent: '보냄 — AI가 받기를 기다려요',
  partial: '일부 반영 — 남은 것은 메모에',
  applied: '반영됨 ✓'
};
var PSAY = {working: 'AI 작업 중 · ', landed: '반영됨 · ', done: '끝', progress: 'AI 작업 중 · ', replied: '답 옴 · '};    // 이벤트 진행 줄(S2 · 47-5b)
var PSTAGE = {working: 'working', landed: 'applied', done: 'done', sent: 'sent', progress: 'working', replied: 'answered'};
var VIA = {event: '실시간', paseo: 'Paseo', claude: 'Claude', queue: '대기열'};
var QUEUED = '보냄 · 대기열 — 읽는 에이전트를 기다려요';
var PROGRESS_CUT = 60;
var HANDS = ['sending', 'unsent', 'decide'];
var FINAL = ['applied', 'answered', 'partial'];          // 메모가 끝난 단계               // 손이 필요한 단계 = 이벤트보다 앞선다
var REPLY_CUT = 40;

function flat(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function tagOf(path) {
  if (!path) return '';
  var segs = String(path).split('>'), m = /^\s*([a-z][a-z0-9-]*)/i.exec(segs[segs.length - 1]);
  return m ? m[1].toUpperCase() : '';
}
function elLabel(h) {
  var tag = tagOf(h && h.path) || flat(h && h.kind).toUpperCase() || '요소';
  var t = flat(h && h.quote && h.quote.exact) || flat(h && h.text);
  if (!t) return tag;
  return tag + ' "' + (t.length > CUT ? t.slice(0, CUT) + '…' : t) + '"';
}

function chips(sel) {
  sel = sel || {};
  var titleOf = sel.titleOf || function (id) { return id; }, seen = {}, out = [];
  var screen = function (id) {
    id = String(id); if (seen[id]) return; seen[id] = 1;
    var t = titleOf(id); out.push({key: 'screen:' + id, kind: 'screen', screen: id, label: t == null || t === '' ? id : String(t)});
  };
  var el = sel.el && sel.el.h && sel.el.h.path && sel.el.screen != null ? sel.el : null;
  if (el && (sel.ids || []).map(String).indexOf(String(el.screen)) < 0) screen(el.screen);
  (sel.ids || []).forEach(function (id) { if (id != null && id !== '') screen(id); });
  if (el) out.push({key: 'el:' + el.screen + ':' + el.h.path, kind: 'el', screen: String(el.screen), label: elLabel(el.h), h: el.h, app: !!el.app});
  return out;
}
function visible(list, dismissed) { return (list || []).filter(function (c) { return !(dismissed && dismissed[c.key]); }); }
function prune(dismissed, list) {
  var o = {}; (list || []).forEach(function (c) { if (dismissed && dismissed[c.key]) o[c.key] = 1; }); return o;
}
function scope(list) {
  if (!list || !list.length) return 'all';
  return list.some(function (c) { return c.kind === 'el'; }) ? 'element' : 'screen';
}
function scopeLabel(list) {
  var s = scope(list);
  return s === 'all' ? ALL : s === 'element' ? '요소' : '화면 ' + list.length + '개';
}
function fold(list, open) {
  list = Array.isArray(list) ? list : [];
  if (open || list.length <= FOLD_AT) return {shown: list.slice(), more: 0};
  var shown = list.filter(function (c, i) { return i < FOLD_KEEP || c.kind === 'el'; });   // 고른 요소는 접지 않는다 — 보내면 그 요소가 범위다
  return {shown: shown, more: list.length - shown.length};
}
function placeholder(list) { return list && list.length ? PLACEHOLDER_PICKED : PLACEHOLDER; }

function elMemo(id, c, note) {
  var h = c.h, t = {path: h.path, text: String(h.text || '').slice(0, 60), rect: h.rect || null};
  if (h.quote) t.quote = h.quote;                        // 다시 찾을 글(task 11)
  if (h.src) t.src = h.src;                              // 앱 소스 위치 → 요청문 '소스:' 줄(task 27)
  return {id: id, screen: c.screen, targets: [t], path: t.path, text: t.text, rect: t.rect, note: note, intent: 'change', sent: false};
}
function build(list, text, opt, mkId) {
  var note = String(text == null ? '' : text).trim(), B = HD.memoBatch;
  opt = opt || {};
  if (!note) return {memos: [], why: '무엇을 바꿀지 적어 주세요'};
  list = list || [];
  if (!list.length) {
    if (opt.first == null || opt.first === '') return {memos: [], why: '보낼 화면이 없어요'};
    return {memos: B.build(B.draft([opt.first], opt.titleOf), {note: note, intent: 'change', scope: 'all'}, mkId), why: ''};
  }
  var els = list.filter(function (c) { return c.kind === 'el'; }), covered = {};
  var memos = els.map(function (c) { covered[c.screen] = 1; return elMemo(mkId(), c, note); });
  var rest = list.filter(function (c) { return c.kind === 'screen' && !covered[c.screen]; }).map(function (c) { return c.screen; });
  if (rest.length) memos = memos.concat(B.build(B.draft(rest, opt.titleOf), {note: note, intent: 'change', scope: 'screen'}, mkId));
  return {memos: memos, why: ''};
}

function lastReply(n) { var r = n && Array.isArray(n.replies) ? n.replies : []; return r.length ? r[r.length - 1] : null; }
function stage(n, busy, inflight) {
  if (!n) return 'applied';                              // 도우미가 바로 반영해 목록에서 빠진 메모
  var s = HD.annotation.status(n);
  if (s === 'draft') return inflight ? 'sending' : 'unsent';
  if (s === 'decide' || s === 'partial') return s;
  if (s === 'done') { var r = lastReply(n); return r && r.kind === '답변' ? 'answered' : 'applied'; }
  if (busy && busy.via === 'queue') return 'queued';
  if (busy && (busy.via === 'paseo' || busy.via === 'cli')) return 'working';
  return 'sent';
}
function line(last, find, busyOf, inflight, opt) {
  if (!last || !Array.isArray(last.ids) || !last.ids.length) return null;
  var ns = last.ids.map(function (id) { return find ? find(id) : null; });
  var st = ns.map(function (n) { return stage(n, n && busyOf ? busyOf(n.screen) : null, inflight); });
  var top = STAGES.filter(function (s) { return st.indexOf(s) >= 0; })[0] || 'sent';
  var pr = opt && opt.progress;
  if (pr && PSTAGE[pr.step] && HANDS.indexOf(top) < 0) {   // 이벤트 진행(S2) — 손이 필요한 단계가 아니면 마지막 이벤트가 줄을 맡는다
    var said = replyText(ns), step = pr.step;
    if (step === 'sent') return {stage: pr.via === 'queue' ? 'queued' : 'sent', text: sentText(pr, opt.agentName), req: last.text};
    if (step === 'progress') return {stage: 'working', text: PSAY.progress + cutText(pr.text, PROGRESS_CUT), req: last.text};
    if (step === 'replied') return {stage: replyStage(pr.status), text: PSAY.replied + (said || flat(pr.kind) || '답'), req: last.text};
    var t = opt.titleOf ? opt.titleOf(pr.screen) : pr.screen;
    if (step === 'landed' && st.every(function (x) { return FINAL.indexOf(x) >= 0; })) step = 'done';   // 쓰고 모든 메모에 답함 = 끝(덮개를 캔버스가 먼저 걷으면 release 가 오지 않는다)
    pr = {step: step, screen: pr.screen};
    var tx = pr.step === 'done' ? PSAY.done : PSAY[pr.step] + (t == null || t === '' ? pr.screen : t);
    if (said && pr.step !== 'working') tx += ' · ' + said;
    return {stage: PSTAGE[pr.step], text: tx, req: last.text};
  }
  var text = SAY[top];
  if (top === 'answered') {
    var a = ns.filter(function (n, i) { return st[i] === 'answered'; })[0], r = lastReply(a);
    text = '답: ' + flat(r && r.text);
  }
  if (st.length > 1) text += ' (' + st.filter(function (s) { return s === 'applied' || s === 'answered'; }).length + '/' + st.length + ')';
  return {stage: top, text: text, req: last.text};
}
function replyText(ns) {                                 // 요청 메모의 마지막 답을 짧게(답변 = '답: …', 반영됨 = 무엇, 일부 = 한 것)
  for (var i = 0; i < ns.length; i++) {
    var r = lastReply(ns[i]); if (!r) continue;
    var x = r.kind === '답변' ? '답: ' + flat(r.text) : r.kind === '반영됨' ? flat(r.what) : r.kind === '일부' ? flat(r.done) : '';
    if (x && x !== '답: ') return x.length > REPLY_CUT ? x.slice(0, REPLY_CUT) + '…' : x;
  }
  return '';
}
function cutText(t, n) { t = flat(t); return t.length > n ? t.slice(0, n - 1) + '…' : t; }
function sentText(pr, nameOf) {
  if (pr.via === 'queue' || !VIA[pr.via]) return QUEUED;
  var n = pr.to && nameOf ? nameOf(pr.to) : null;
  return '보냄 · ' + (n || pr.to || 'AI') + ' (' + VIA[pr.via] + ')';
}
function replyStage(status) { return status === 'partial' ? 'partial' : status === 'decide' ? 'decide' : status === 'done' ? 'applied' : 'answered'; }
function str(x) { return typeof x === 'string' && x ? x : null; }
function progress(p, ev, screens, ids) {
  if (!ev || typeof ev.type !== 'string') return p;
  var mine = function (id) { return typeof id === 'string' && !!id && (!screens || !screens.length || screens.indexOf(id) >= 0); };
  var t = ev.type, to = p && p.to || null;
  if (t === 'request.sent') {                            // 보낸 곳과 길(47-5b) — 이 요청의 메모 id 가 든 것만, 진행이 이미 앞섰으면 그대로
    var hit = Array.isArray(ids) && Array.isArray(ev.notes) && ev.notes.some(function (n) { return ids.indexOf(n) >= 0; });
    if (!hit || (p && p.step !== 'sent') || !str(ev.via)) return p;
    return {step: 'sent', via: ev.via, to: str(ev.to)};
  }
  if (t === 'agent.progress') {
    if (!str(ev.text) || !flat(ev.text) || (to && str(ev.agent) && ev.agent !== to)) return p;
    return {step: 'progress', text: flat(ev.text), screen: str(ev.screen), via: p && p.via || null, to: to || str(ev.agent)};
  }
  if (t === 'agent.reply') {
    if (!Array.isArray(ids) || ids.indexOf(ev.note) < 0) return p;
    return {step: 'replied', kind: str(ev.kind) || '', status: str(ev.status) || '', to: to || str(ev.agent)};
  }
  if (t === 'claim' && mine(ev.screen)) return {step: 'working', screen: ev.screen};
  if (t === 'release' && mine(ev.screen)) return {step: 'done', screen: ev.screen};
  if (t === 'ai.write' && mine(ev.screen)) return {step: 'landed', screen: ev.screen};
  if (t === 'screen.written' && ev.by === 'ai' && Array.isArray(ev.screens)) {
    var hit = ev.screens.filter(mine)[0];
    if (hit) return {step: 'landed', screen: hit};
  }
  return p;
}

function record(text, memos, at) {
  return {text: flat(text).slice(0, 200), ids: (memos || []).map(function (m) { return m.id; }), at: at};
}
function parseLast(raw) {
  if (raw == null || raw === '') return {last: null, bad: false};
  var v; try { v = JSON.parse(raw); } catch (e) { return {last: null, bad: true}; }
  if (!v || typeof v !== 'object' || Array.isArray(v) || typeof v.text !== 'string' || !Array.isArray(v.ids) ||
      !v.ids.every(function (x) { return typeof x === 'string'; })) return {last: null, bad: true};
  return {last: {text: v.text, ids: v.ids.slice(), at: +v.at || 0}, bad: false};
}

HD.chat = {VIA: VIA, PLACEHOLDER: PLACEHOLDER, ALL: ALL, STAGES: STAGES, tagOf: tagOf, elLabel: elLabel, chips: chips, visible: visible, prune: prune,
           scope: scope, scopeLabel: scopeLabel, fold: fold, placeholder: placeholder, build: build, stage: stage, line: line, progress: progress, record: record, parseLast: parseLast};
})();
