/* Model — 대화창 '/' 명령(R29): 명령 표 · 입력 글에 맞는 명령 · /memo 가 함께 보낼 메모(보내기 전) · 그 칩 이름과 툴팁 줄. DOM·저장소·메시지를 쓰지 않는다.
   COMMANDS = [{name, label, hint}] — 새 명령 = 이 표 한 줄 + View(view-chat) 의 같은 이름 실행 함수 하나.
   token(text, caret) → {start, end, q} | null — 커서(없으면 글 끝) 앞 낱말이 글·줄 첫머리 또는 빈칸 바로 뒤의 '/' + 빈칸 없는 글자일 때(글 도중에도 — GPT·Slack 관례).
     end = 커서 뒤로 이어진 빈칸 없는 글자까지(바꿀 자리), q = '/' 뒤~커서. 'a/b'·주소 안의 '/' 는 아님.
   match(text, caret) → 맞는 명령들 — token 의 q 가 이름 앞부분인 것(대소문자 무시), token 이 없으면 [](빈칸을 치면 보통 글).
   move(i, n, d) → 위·아래 화살표로 옮긴 자리(끝에서 돌아감, n = 0 이면 -1).
   drafts(list) → 함께 보낼 메모 = 보내기 전(annotation.status 'draft') 메모만, 목록 차례 그대로 — 보낸 것(AI 작업 중)·완료·결정 필요·일부 반영·반영 대기 편집(n.edit)은 빠진다.
   memoChip(drafts, titleOf) → {key:'memos', kind:'memos', n, label:'메모 N건', tip:[줄…]} | null(0건) — tip 줄 = tipLine, TIP_MAX 넘으면 마지막 줄 '외 N건'.
   tipLine(n, titleOf) → '<화면 이름> — <메모 글 앞 CUT 자>…'(화면 이름이 없으면 id, 글이 없으면 '(글 없음)').
   EMPTY = 0건일 때 토스트 말.
   HD.chatCmd = {COMMANDS, EMPTY, KEY, token, match, move, drafts, memoChip, tipLine} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var COMMANDS = [
  {name: 'memo', label: '/memo', hint: '보내기 전 메모를 이 요청에 함께 싣기'}
];
var EMPTY = '보낼 메모가 없어요';
var KEY = 'memos';
var CUT = 24, TIP_MAX = 8;

function flat(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); }
function token(text, caret) {
  text = String(text == null ? '' : text);
  var c = typeof caret === 'number' && caret >= 0 && caret <= text.length ? caret : text.length;
  var m = /(^|\s)\/(\S*)$/.exec(text.slice(0, c));
  if (!m) return null;
  return {start: c - m[2].length - 1, end: c + /^\S*/.exec(text.slice(c))[0].length, q: m[2]};
}
function match(text, caret) {
  var t = token(text, caret);
  if (!t) return [];
  var q = t.q.toLowerCase();
  return COMMANDS.filter(function (c) { return c.name.indexOf(q) === 0; });
}
function move(i, n, d) {
  if (!n) return -1;
  var j = (typeof i === 'number' && i >= 0 ? i : (d > 0 ? -1 : 0)) + (d > 0 ? 1 : -1);
  return ((j % n) + n) % n;
}
function drafts(list) {
  var A = HD.annotation;
  return (Array.isArray(list) ? list : []).filter(function (n) {
    return n && typeof n === 'object' && n.id != null && !n.edit && A.status(n) === 'draft';
  });
}
function tipLine(n, titleOf) {
  var t = titleOf ? titleOf(n.screen) : null, name = t == null || t === '' ? String(n.screen == null ? '' : n.screen) : String(t);
  var x = flat(n.note);
  x = x ? (x.length > CUT ? x.slice(0, CUT) + '…' : x) : '(글 없음)';
  return (name ? name + ' — ' : '') + x;
}
function memoChip(list, titleOf) {
  list = Array.isArray(list) ? list : [];
  if (!list.length) return null;
  var tip = list.slice(0, list.length > TIP_MAX ? TIP_MAX - 1 : TIP_MAX).map(function (n) { return tipLine(n, titleOf); });
  if (list.length > TIP_MAX) tip.push('외 ' + (list.length - TIP_MAX + 1) + '건');
  return {key: KEY, kind: 'memos', n: list.length, label: '메모 ' + list.length + '건', tip: tip};
}

HD.chatCmd = {COMMANDS: COMMANDS, EMPTY: EMPTY, KEY: KEY, token: token, match: match, move: move, drafts: drafts, memoChip: memoChip, tipLine: tipLine};
})();
