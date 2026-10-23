/* Model — 편집 메모(화면 파일을 바꾸는 편집). DOM·저장소·메시지를 쓰지 않는다.
   단일 진실 원천: 편집은 모두 메모 목록 하나에 쌓이고, 판 위 표시(반영 대기 선·빈 레이아웃·글자 미리보기)는 여기서 계산한다.
   메모 = {id, no, screen, targets:[{path,text,rect,quote?}], replies:[], path, text, rect, note, intent:'change', sent, edit, op?, to?, value?, index?, x?, y?}
     edit: link(op: link·cut·untrigger·trigger·new) · text · title · purpose · policy(index) · new-screen · cut-in · delete · copy
   HD.edits = {note, pendingFor, overviewPending, pendingLink, directOf, instantOf, split, tally, request, say} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function newId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

// 메모 하나 — h = 대상 요소 {path, text, rect}
function note(screen, h, text, op, to) {
  var t = {path: h.path, text: h.text, rect: h.rect}; if (h.quote) t.quote = h.quote;   // quote = 다시 찾을 글(palette.js, task 11)
  return {id: newId(), screen: screen, targets: [t],
          path: h.path, text: h.text, rect: h.rect, note: text, intent: 'change', sent: false, edit: 'link', op: op || '', to: to || ''};
}

// 아직 파일에 안 들어간 연결 편집 → 연결 보기가 겹쳐 그릴 것(출발 화면 from 기준)
function pendingFor(notes, from) {
  var pd = {byPath: {}, adds: [], cutIn: {}};
  (notes || []).forEach(function (n) {
    if (n.edit === 'cut-in' || n.edit === 'delete') pd.cutIn[n.screen] = 1;
    if (n.edit !== 'link' || n.screen !== from) return;
    if (n.op === 'link' && n.to) { pd.byPath[n.path] = {op: 'link', to: n.to}; pd.adds.push({to: n.to, path: n.path, text: n.text, rect: n.rect}); }
    else if (n.op === 'cut' || n.op === 'untrigger') pd.byPath[n.path] = {op: 'cut'};
  });
  return pd;
}

// 판에 늘 그리는 선에 겹칠 편집(graph.overview 의 pend) — 잇기 = 더함, 끊기·트리거 해제·도착 바꾸기 전 도착(was) = 뺌, 삭제·들어오는 연결 끊기 = 그 화면으로 오는 선 모두 뺌
function overviewPending(notes) {
  var pd = {add: [], drop: {}, cutIn: {}}, dec = function (k) { pd.drop[k] = (pd.drop[k] || 0) + 1; };
  (notes || []).forEach(function (n) {
    if (n.edit === 'cut-in' || n.edit === 'delete') pd.cutIn[n.screen] = 1;
    if (n.edit !== 'link' || !n.to) return;
    if (n.op === 'link') { pd.add.push({from: n.screen, to: String(n.to)}); if (n.was) dec(n.screen + '>' + n.was); }
    else if (n.op === 'cut' || n.op === 'untrigger') dec(n.screen + '>' + n.to);
  });
  return pd;
}

// 그 요소(from·path)를 to 로 잇는, 아직 보내지 않은 연결 편집 — 이 선을 자르면 끊기 메모 대신 이 편집을 취소한다(E4)
function pendingLink(notes, from, path, to) {
  return (notes || []).filter(function (n) {
    return !n.sent && n.edit === 'link' && n.op === 'link' && n.screen === from && n.path === path && String(n.to) === String(to);
  }).pop() || null;
}

// 도우미(helper.py)가 화면 파일에 바로 쓸 수 있는 편집
function directOf(n) {
  return n.edit === 'text' || n.edit === 'title' || n.edit === 'purpose' || n.edit === 'policy' ||
         (n.edit === 'link' && ((n.op === 'link' && !!n.to) || n.op === 'cut' || n.op === 'untrigger'));
}

// 누르는 즉시 파일에 쓰는 편집(조각 2.2 D1): 잇기·끊기·트리거 해제 — 도착이 빈 레이아웃(new-…)이면 아직 파일이 없어 반영 대기로
function instantOf(n) {
  return n.edit === 'link' && (n.op === 'cut' || n.op === 'untrigger' || (n.op === 'link' && !!n.to && !/^new-/.test(n.to)));
}

// 메모 패널 둘로(E5): pending = 기계적 편집(파일에 바로 쓸 수 있는 것) · memos = 나머지(AI 에 보내는 요청)
function split(notes) {
  var out = {memos: [], pending: []};
  (notes || []).forEach(function (n) { (directOf(n) ? out.pending : out.memos).push(n); });
  return out;
}

// 보내기 요청문(/hyper-design:fix 가 읽는 형식 — 바꾸지 않는다). 여러 요소 메모는 요소마다 한 항목으로 펼친다
// 요청 글이 여러 줄이면 둘째 줄부터 '요청: ' 뒤 글자 자리에 맞춰 들여 쓴다(항목은 늘 '번호. screen=' 줄로 시작)
var CONT = '       ';
function targetsOf(n) { return n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text, rect: n.rect}]; }
function request(notes, out) {
  var list = [];
  (notes || []).forEach(function (n) { targetsOf(n).forEach(function (t) { list.push({screen: n.screen, path: t.path, text: t.text, intent: n.intent, note: n.note}); }); });
  return '[hyper-design 수정 요청] out=' + out + ' · ' + list.length + '건\n' + list.map(function (n, i) {
    return (i + 1) + '. screen=' + n.screen + ' · path=' + n.path + '\n   text="' + String(n.text).replace(/\s+/g, ' ') + '" · intent=' + n.intent +
      '\n   요청: ' + String(n.note).replace(/[ \t]*\r?\n\s*/g, '\n' + CONT);   // 줄바꿈은 들여 쓴 다음 줄로 이어 남긴다(#225)
  }).join('\n');
}

// 화면마다 반영 대기 편집 수
function tally(notes) {
  var c = {}; (notes || []).forEach(function (n) { if (n.edit) c[n.screen] = (c[n.screen] || 0) + 1; }); return c;
}

// 요청문 글귀 — label = '"제목"(id)' 처럼 사람이 읽는 화면 이름(View 가 만들어 넘긴다)
var FIELD = {title: '화면 이름', purpose: '화면 설명', policy: '정책 줄'};
var say = {
  link: function (to) { return '이 요소를 누르면 ' + to + ' 화면으로 가게 연결'; },
  retarget: function (from, to) { return '도착 바꾸기: 지금 ' + from + ' → ' + to + ' 화면으로 가게'; },
  cut: function (to) { return '연결 끊기: 이 요소를 눌러도 ' + to + ' 화면으로 가지 않게'; },
  untrigger: function (to) { return '트리거 해제: 이 요소를 눌러도 화면이 바뀌지 않게(지금 ' + to + '로 가는 연결 없애기)'; },
  trigger: function () { return '트리거 지정: 이 요소를 다른 화면으로 가는 버튼으로(도착은 아직 정하지 않음)'; },
  text: function (v) { return '글자를 "' + v + '"(으)로 바꾸기'; },
  field: function (field, v, index) {
    return (field === 'policy' ? '정책 ' + (index + 1) + '번째 줄' : FIELD[field]) + '을 "' + v + '"(으)로 바꾸기 (screens.json의 ' +
           (field === 'policy' ? 'policies[' + index + ']' : field) + ')';
  },
  layout: function (value, id, purpose) {           // purpose = 이 화면의 목적(여러 줄 그대로) — 있으면 첫째 브리프(#225)
    var p = purpose == null ? '' : String(purpose).trim();
    return '새 화면 "' + value + '"(' + id + ')을 빈 레이아웃으로 만들기 — ' +
           (p ? '목적: ' + p + ' · 내용은 이 목적과 이 화면에 남긴 메모를 따라 채우기' : '내용은 이 화면에 남긴 메모를 따라 채우기');
  },
  linkNew: function (value, id) { return '이 요소를 누르면 새 화면 "' + value + '"(' + id + ')으로 가게 연결'; },
  copy: function (value, id, src) { return '새 화면 "' + value + '"(' + id + ')을 ' + src + ' 화면을 복제해 만들기'; },
  remove: function (label) { return '이 화면 ' + label + '을 지우기 — 화면 파일과 screens.json 항목, 이 화면으로 오는 연결도 정리'; },
  cutIn: function (label) { return '이 화면 ' + label + '으로 오는 연결을 모두 끊기(다른 화면의 버튼·링크에서)'; }
};

HD.edits = {note: note, newId: newId, pendingFor: pendingFor, overviewPending: overviewPending, pendingLink: pendingLink, directOf: directOf, instantOf: instantOf, split: split, tally: tally, request: request, say: say, FIELD: FIELD};
})();
