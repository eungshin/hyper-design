/* Model — 편집 메모(화면 파일을 바꾸는 편집). DOM·저장소·메시지를 쓰지 않는다.
   단일 진실 원천: 편집은 모두 메모 목록 하나에 쌓이고, 판 위 표시(반영 대기 선·빈 레이아웃·글자 미리보기)는 여기서 계산한다.
   메모 = {id, screen, targets:[{path,text,rect}], path, text, rect, note, intent:'change', sent, edit, op?, to?, value?, index?, x?, y?}
     edit: link(op: link·cut·untrigger·trigger·new) · text · title · purpose · policy(index) · new-screen · cut-in · delete · copy
   HD.edits = {note, pendingFor, directOf, tally, say} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function newId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

// 메모 하나 — h = 대상 요소 {path, text, rect}
function note(screen, h, text, op, to) {
  return {id: newId(), screen: screen, targets: [{path: h.path, text: h.text, rect: h.rect}],
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

// 도우미(helper.py)가 화면 파일에 바로 쓸 수 있는 편집
function directOf(n) {
  return n.edit === 'text' || n.edit === 'title' || n.edit === 'purpose' || n.edit === 'policy' ||
         (n.edit === 'link' && ((n.op === 'link' && !!n.to) || n.op === 'cut' || n.op === 'untrigger'));
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
  layout: function (value, id) { return '새 화면 "' + value + '"(' + id + ')을 빈 레이아웃으로 만들기 — 내용은 이 화면에 남긴 메모를 따라 채우기'; },
  linkNew: function (value, id) { return '이 요소를 누르면 새 화면 "' + value + '"(' + id + ')으로 가게 연결'; }
};

HD.edits = {note: note, newId: newId, pendingFor: pendingFor, directOf: directOf, tally: tally, say: say, FIELD: FIELD};
})();
