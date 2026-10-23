/* Model — 메모 주석 규칙: 화면마다 바뀌지 않는 번호(n.no)·답(n.replies)에서 계산하는 상태·답 검사. DOM·저장소·메시지를 쓰지 않는다.
   번호: 메모를 만들 때 = 그 화면에서 지금까지 쓴 가장 큰 번호 + 1(지워도 다시 쓰지 않는다). '지금까지 쓴 가장 큰 번호'는 seq = {화면 id: 마지막 번호}(키 note-seq).
   답: n.replies = [{kind, by?, at?, …}] — AI 답(반영됨·일부·대체됨·답변·질문, `hd reply` #231 가 쓴다)과 사람 답(확인 = 완료, 다시 = 다시 열기).
   상태는 저장하지 않고 늘 계산한다: 보내지 않음 → draft · 보냄 + 답 없음 → working · 마지막 답 질문 → decide · 일부 → partial ·
     반영됨/대체됨/답변/확인 → done · 다시 → (보내지 않았으면 draft, 다시 보냈으면) working.
   HD.annotation = {KINDS, USER, LABEL, status(n), isOpen(n), rework(n), nextNo(seq, screen), migrate(list, seq) → {seq, changed}, validReply(r) → {ok, why}, says(r), reply(kind, at)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var KINDS = ['반영됨', '일부', '대체됨', '답변', '질문'];        // AI 답 — '보류'는 없다(미루려면 질문)
var USER = ['확인', '다시'];                                    // 사람 답 — 완료 · 다시 열기(덧붙는 칸 없음)
var DONE = {'반영됨': 1, '대체됨': 1, '답변': 1, '확인': 1};
var LABEL = {draft: '보내기 전', working: '작업 중', decide: '결정 필요', partial: '일부 반영', done: '완료'};

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
var NEED = {
  '반영됨': function (r) { return !str(r.what) ? 'what' : !Array.isArray(r.screens) ? 'screens' : typeof r.captured !== 'boolean' ? 'captured' : ''; },
  '일부': function (r) { return !str(r.done) ? 'done' : !str(r.left) ? 'left' : ''; },
  '대체됨': function (r) { return !str(r.where) ? 'where' : ''; },
  '답변': function (r) { return !str(r.text) ? 'text' : ''; },
  '질문': function (r) {
    if (!str(r.question)) return 'question';
    if (!Array.isArray(r.choices) || r.choices.length < 2 || r.choices.length > 4 || !r.choices.every(str)) return 'choices(2–4)';
    return '';
  },
  '확인': function () { return ''; },
  '다시': function () { return ''; }
};
function validReply(r) {
  if (!r || typeof r !== 'object' || Array.isArray(r)) return {ok: false, why: 'not an object'};
  if (!Object.prototype.hasOwnProperty.call(NEED, r.kind)) return {ok: false, why: 'unknown kind: ' + r.kind};
  var miss = NEED[r.kind](r);
  return miss ? {ok: false, why: r.kind + ': ' + miss} : {ok: true, why: ''};
}

// 답 한 줄 — 사람이 읽는 글
function says(r) {
  if (!r) return '';
  switch (r.kind) {
    case '반영됨': return '반영됨 — ' + (r.what || '');
    case '일부': return '일부 반영 — ' + (r.done || '') + ' · 남음: ' + (r.left || '');
    case '대체됨': return '다른 곳에서 반영 — ' + (r.where || '');
    case '답변': return '답변 — ' + (r.text || '');
    case '질문': return '질문 — ' + (r.question || '') + (Array.isArray(r.choices) && r.choices.length ? ' (' + r.choices.join(' / ') + ')' : '');
    case '확인': return '완료로 표시함';
    case '다시': return '다시 열었음';
  }
  return String(r.kind || '');
}

function reply(kind, at) { return {by: 'user', kind: kind, at: at}; }   // 사람 답(확인·다시) — at = ISO 시각(셸이 넣는다)

HD.annotation = {KINDS: KINDS, USER: USER, LABEL: LABEL, status: status, isOpen: isOpen, rework: rework, nextNo: nextNo, migrate: migrate, validReply: validReply, says: says, reply: reply};
})();
