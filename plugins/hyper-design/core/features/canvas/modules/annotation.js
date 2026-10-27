/* Model — 메모 주석 규칙: 화면마다 바뀌지 않는 번호(n.no)·답(n.replies)에서 계산하는 상태·답 검사·답 글. DOM·저장소·메시지를 쓰지 않는다.
   번호: 메모를 만들 때 = 그 화면에서 지금까지 쓴 가장 큰 번호 + 1(지워도 다시 쓰지 않는다). '지금까지 쓴 가장 큰 번호'는 seq = {화면 id: 마지막 번호}(키 note-seq).
   답: n.replies = [{kind, by?, at?, …}] — AI 답(반영됨·일부·대체됨·답변·질문, `hd reply` #231 가 쓴다)과 사람 답(확인 = 완료(질문에 고른 답 answer 가 붙기도), 다시 = 다시 열기).
   상태는 저장하지 않고 늘 계산한다: 보내지 않음 → draft · 보냄 + 답 없음 → working · 마지막 답 질문 → decide · 일부 → partial ·
     반영됨/대체됨/답변/확인 → done · 다시 → (보내지 않았으면 draft, 다시 보냈으면) working.
   답 검사(validReply)는 hd_model.check_reply 와 같은 규칙 — 공유 fixture(core/features/hd/tests/fixtures/replies.json)가 둘을 묶는다.
   HD.annotation = {KINDS, USER, LABEL, status(n), isOpen(n), rework(n), nextNo(seq, screen), migrate(list, seq) → {seq, changed}, validReply(r, intent?, agent?) → {ok, why, errors},
     says(r), tip(r), question(n) → {question, choices}|null, answer(choice, at), followUp(question, choice), label(n, queued), decideCount(list), adopt(cur, next), reply(kind, at),
     SCOPES, scopeOf(n), scopeWord(n), visible(n, showSent), hiddenCount(list)}
   보낸 메모 숨기기(task 29): visible(n, showSent) — 보낸 뒤 AI 차례(working)·끝난 것(done)은 숨김(showSent 면 다 보임). draft·decide(AI 가 사람에게 물음)·partial(남긴 것)은 늘 보임.
     다시 → 다시 보냄 = working = 다시 숨김. hiddenCount = 숨김이 될 메모 수('보낸 메모 보기 (N)', 켜짐과 상관없이)
   범위(R7): n.scope = element|screen|all(없음·모르는 값 = element) — SCOPES = 메모 창 고르기 [값, 말] 차례, scopeWord = 묶음 줄에 보일 말(이 요소 = '')
   메모 만들기(셸 C7): make({id, screen, targets, note, intent, scope?}) → 새 메모 {id, screen, targets(사본), path·text·rect(첫 대상), note, intent, sent:false, scope?(element 가 아닐 때만)}
     · makeId(now, rnd) → 메모 id(now 36진 + rnd 36진 4자리 — 부르는 쪽이 Date.now()·Math.random() 을 넘긴다) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var KINDS = ['반영됨', '일부', '대체됨', '답변', '질문'];        // AI 답 — '보류'는 없다(미루려면 질문)
var USER = ['확인', '다시'];                                    // 사람 답 — 완료 · 다시 열기
var DONE = {'반영됨': 1, '대체됨': 1, '답변': 1, '확인': 1};
var LABEL = {draft: '보내기 전', working: 'AI 작업 중', decide: '결정 필요', partial: '일부 반영', done: '완료'};

function replies(n) { return n && Array.isArray(n.replies) ? n.replies : []; }
function last(n) { var r = replies(n); return r.length ? r[r.length - 1] : null; }

function status(n) {
  if (!n) return 'draft';
  var r = last(n), k = r && r.kind;
  if (k === '확인') return 'done';                               // 사람이 닫은 것은 보냈든 아니든 완료
  if (!n.sent) return 'draft';
  if (!r) return 'working';
  if (k === '질문') return 'decide';
  if (k === '일부') return 'partial';
  if (DONE[k]) return 'done';
  return 'working';                                              // 다시(다시 보낸 뒤) · 모르는 종류
}
function isOpen(n) { return status(n) !== 'done'; }
var HIDE = {working: 1, done: 1};                                // 보낸 메모 숨기기 — decide·partial 은 사람 차례라 숨기지 않는다
function visible(n, showSent) { return !!showSent || !HIDE[status(n)]; }
function hiddenCount(list) { return (list || []).filter(function (n) { return !visible(n, false); }).length; }
function rework(n) { return replies(n).filter(function (r) { return r && r.kind === '다시'; }).length; }

function nextNo(seq, screen) { var v = seq && +seq[screen]; return (v > 0 ? Math.floor(v) : 0) + 1; }

// 번호 없는 메모에 번호(그 화면에서 목록 차례대로), 답 칸이 없으면 [] — 메모 객체를 제자리에서 고친다(셸이 객체를 붙잡고 있다)
// seq 는 새 객체로 돌려준다: 목록에 있는 가장 큰 번호보다 작으면 올린다(키를 잃어도 번호가 겹치지 않게)
function migrate(list, seq) {
  var s = {}, changed = false, k;
  if (seq && typeof seq === 'object' && !Array.isArray(seq)) for (k in seq) if (Object.prototype.hasOwnProperty.call(seq, k) && +seq[k] > 0) s[k] = Math.floor(+seq[k]);
  (list || []).forEach(function (n) {
    if (!n || n.screen == null || !(n.no > 0)) return;
    var id = String(n.screen); if (!(s[id] >= n.no)) { s[id] = n.no; changed = true; }
  });
  (list || []).forEach(function (n) {
    if (!n || typeof n !== 'object') return;
    if (!Array.isArray(n.replies)) { n.replies = []; changed = true; }
    if (n.screen == null || n.no > 0) return;
    var id = String(n.screen); n.no = nextNo(s, id); s[id] = n.no; changed = true;
  });
  return {seq: s, changed: changed};
}

function str(v) { return typeof v === 'string' && v.trim() !== ''; }
var has = function (o, k) { return Object.prototype.hasOwnProperty.call(o, k); };
// 종류마다 칸: 이름 → [모양, 한도] — hd_model.FIELDS 와 같은 표
var FIELDS = {
  '반영됨': {what: ['str', 140], screens: ['screens'], captured: ['bool']},
  '일부': {done: ['str', 140], left: ['str', 140]},
  '대체됨': {where: ['str', 140]},
  '답변': {text: ['str', 280]},
  '질문': {question: ['str', 140], choices: ['choices', 40]},
  '확인': {},
  '다시': {}
};
var OPTIONAL = {'확인': {answer: ['str', 40]}};                  // 질문에 고른 답으로 닫을 때(사람 답) — hd_model.OPTIONAL
var COMMON = {kind: 1, by: 1, at: 1, detail: 1};
var DETAIL_MAX = 50000, TIP_CUT = 300;                       // detail = 긴 답 본문(hd_model.DETAIL_MAX, R26) · 툴팁엔 앞 TIP_CUT 자만(메모 묶음이 전체를 보인다)
function field(errs, name, v, spec) {
  var shape = spec[0], lim = spec[1];
  if (shape === 'str') { if (!str(v)) errs.push(name + ': 빈 글이 아니어야 해요'); else if (v.length > lim) errs.push(name + ': ' + lim + '자 넘음(' + v.length + '자)'); }
  else if (shape === 'bool') { if (typeof v !== 'boolean') errs.push(name + ': true/false 여야 해요'); }
  else if (shape === 'screens') { if (!Array.isArray(v) || !v.length || !v.every(str)) errs.push(name + ': 화면 id 1개 이상'); }
  else if (shape === 'choices') {
    if (!Array.isArray(v) || v.length < 2 || v.length > 4 || !v.every(str)) errs.push(name + ': 고를 것 2–4개(빈 글 아님)');
    else if (v.some(function (c) { return c.length > lim; })) errs.push(name + ': 하나마다 ' + lim + '자 넘음');
  }
}
// 답 하나 검사 → {ok, why(실패한 칸마다 한 줄을 '; ' 로 이음), errors}
// intent 를 주면 답변은 질문 메모에만 · agent=true 면 사람 답(확인·다시) 거절(캔버스에서 다는 답은 사람 것이라 보통 주지 않는다)
function validReply(r, intent, agent) {
  var errs = [];
  if (!r || typeof r !== 'object' || Array.isArray(r)) errs.push('reply: 객체가 아니에요');
  else if (!has(FIELDS, r.kind)) errs.push('kind: 모르는 종류 ' + r.kind);
  else if (agent && USER.indexOf(r.kind) >= 0) errs.push('kind: ' + r.kind + ' 은 사람만 캔버스에서 달아요');
  else {
    var spec = FIELDS[r.kind], opt = OPTIONAL[r.kind] || {};
    if (r.kind === '답변' && intent != null && intent !== 'question') errs.push('kind: 답변은 질문 메모에만');
    Object.keys(r).filter(function (k) { return !COMMON[k] && !has(spec, k) && !has(opt, k); }).sort()
      .forEach(function (k) { errs.push(k + ': ' + r.kind + ' 에 없는 칸'); });
    Object.keys(spec).forEach(function (k) { if (!has(r, k)) errs.push(k + ': 없어요'); else field(errs, k, r[k], spec[k]); });
    Object.keys(opt).forEach(function (k) { if (has(r, k)) field(errs, k, r[k], opt[k]); });
    if (has(r, 'detail') && !(typeof r.detail === 'string' && r.detail.length <= DETAIL_MAX)) errs.push('detail: ' + DETAIL_MAX + '자 이하 글');
    if (has(r, 'by') && !(str(r.by) && r.by.length <= 40)) errs.push('by: 1–40자 이름');
    if (has(r, 'at') && !str(r.at)) errs.push('at: ISO 시각 글');
  }
  return {ok: !errs.length, why: errs.join('; '), errors: errs};
}

// 답 한 줄 — 사람이 읽는 글(묶음의 회색 줄). 질문의 고를 것은 따로 단추(view-thread)
function says(r) {
  if (!r) return '';
  var list = function (a) { return Array.isArray(a) ? a.join(', ') : ''; };
  switch (r.kind) {
    case '반영됨': return '반영됨 — ' + (r.what || '') + (list(r.screens) ? ' · ' + list(r.screens) : '');
    case '일부': return '일부 — ' + (r.done || '') + ' · 남은 것 ' + (r.left || '');
    case '대체됨': return '대체됨 → ' + (r.where || '');
    case '답변': return '답변 — ' + (r.text || '');
    case '질문': return '질문 — ' + (r.question || '');
    case '확인': return '완료함' + (str(r.answer) ? ' — 고름: ' + r.answer : '');
    case '다시': return '다시 엶';
  }
  return String(r.kind || '');
}
// 답 줄에 올렸을 때 더 볼 것: 반영됨 = 화면·캡처 확인 여부(+ detail), 그 밖 = detail(없으면 '') — detail 은 앞 TIP_CUT 자(전체는 메모 묶음 본문, R26)
function tip(r) {
  if (!r) return '';
  var d = typeof r.detail === 'string' ? r.detail : '';
  if (d.length > TIP_CUT) d = d.slice(0, TIP_CUT - 1) + '…';
  if (r.kind === '반영됨') return '화면: ' + (Array.isArray(r.screens) ? r.screens.join(', ') : '') + ' · 캡처 ' + (r.captured ? '확인함' : '안 봄') + (d ? '\n' + d : '');
  return d;
}
// 지금 답을 기다리는 질문(마지막 답이 질문 = decide 일 때만) → {question, choices} | null
function question(n) {
  var r = last(n);
  return r && r.kind === '질문' && status(n) === 'decide' && Array.isArray(r.choices) ? {question: String(r.question || ''), choices: r.choices.slice()} : null;
}
function answer(choice, at) { return {by: 'user', kind: '확인', answer: String(choice), at: at}; }   // 고른 답으로 질문 메모 닫기
function followUp(q, choice) { return '질문 "' + q + '" → ' + choice; }                             // 고른 답을 AI 에 보낼 새 메모 글
// 상태 말: 보냈지만 받을 AI 가 없으면(대기열 파일에만, queued) working 대신 '대기열'
function label(n, queued) { var st = status(n); return st === 'working' && queued ? '대기열' : LABEL[st]; }
function decideCount(list) { return (list || []).filter(function (n) { return status(n) === 'decide'; }).length; }

// 파일에서 온 새 목록 → 같은 id 의 메모는 지금 객체를 그대로 두고 칸만 바꾼다(되돌리기 기록이 객체를 붙잡고 있다). 새 목록 차례, 없어진 것은 빠짐
function adopt(cur, next) {
  var byId = {};
  (cur || []).forEach(function (n) { if (n && n.id != null) byId[n.id] = n; });
  return (next || []).map(function (m) {
    var n = m && m.id != null && byId[m.id]; if (!n) return m;
    Object.keys(n).forEach(function (k) { if (!has(m, k)) delete n[k]; });
    Object.keys(m).forEach(function (k) { n[k] = m[k]; });
    return n;
  });
}

var SCOPES = [['element', '이 요소'], ['screen', '이 화면'], ['all', '모든 화면']];
var SCOPE_WORD = {screen: '이 화면', all: '모든 화면'};
function scopeOf(n) { return n && SCOPE_WORD[n.scope] ? n.scope : 'element'; }
function scopeWord(n) { return SCOPE_WORD[scopeOf(n)] || ''; }

function make(o) {
  var ts = (o.targets || []).slice(), t0 = ts[0] || {};
  var n = {id: o.id, screen: o.screen, targets: ts, path: t0.path, text: t0.text, rect: t0.rect, note: o.note, intent: o.intent, sent: false};
  if (o.scope && o.scope !== 'element') n.scope = o.scope;
  return n;
}
function makeId(now, rnd) { return now.toString(36) + rnd.toString(36).slice(2, 6); }

function reply(kind, at) { return {by: 'user', kind: kind, at: at}; }   // 사람 답(확인·다시) — at = ISO 시각(셸이 넣는다)

HD.annotation = {KINDS: KINDS, USER: USER, LABEL: LABEL, status: status, isOpen: isOpen, rework: rework, nextNo: nextNo, migrate: migrate, validReply: validReply,
                 says: says, tip: tip, question: question, answer: answer, followUp: followUp, label: label, decideCount: decideCount, adopt: adopt, reply: reply, make: make, makeId: makeId,
                 SCOPES: SCOPES, scopeOf: scopeOf, scopeWord: scopeWord, visible: visible, hiddenCount: hiddenCount};
})();
