/* Model — 카드 아래 글(제목·설명·정책) 한 상자 고치기의 비교 규칙과 판에 보일 칸(H16 · task 31). DOM 을 쓰지 않는다.
   값 모양 = {title: 글, purpose: 글, policies: [글]}
   normalise(field, text) → 지금 고치기 칸과 같은 빈칸 정리
     title·policy = 모든 빈칸(줄바꿈 포함)을 한 칸으로 + 앞뒤 자르기
     purpose = 띄어쓰기·탭을 한 칸으로, 줄바꿈 앞뒤 띄어쓰기 지우기, 앞뒤 자르기(줄바꿈은 남긴다)
   lines(text) → 정책 메모 글 한 덩어리를 줄 목록으로(줄마다 normalise('policy'), 빈 줄 버림)
   diff(before, after) → [{field: 'title'|'purpose', value, old} | {field: 'policies', value: [줄], old: [원래 줄]}]
     바뀌지 않은 칸은 빼고, 정책은 목록 하나로 비교(빈 줄 버림 — 가운데 넣기·지우기·순서 바꾸기 모두 목록 하나). 비운 칸(#243): 제목 = 편집 아님 · 설명 = value ''
   pending(notes, id, orig) → 그 화면의 반영 대기 정책 목록(없으면 null) — 메모 차례대로: 옛 줄 편집(policy[i], 원래 번호)을 원래 목록에 얹고,
     목록 편집(policies)이 나오면 그것이 통째로 이긴다(그 뒤 옛 줄 편집은 번호가 맞지 않아 무시)
   shown({selected, blank, pending:{purpose, policies}}) → {purpose, policies, mark} 판의 카드 아래 글에 보일 칸
     고른 카드·빈 레이아웃 = 다 보임 · 아니면 제목만, 설명·정책에 반영 대기가 있으면 mark(작은 표시)
   HD.caption = {FIELDS, normalise, lines, diff, pending, shown} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var FIELDS = ['title', 'purpose', 'policies'];

function normalise(field, text) {
  var s = text == null ? '' : String(text);
  if (field === 'purpose') return s.replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').trim();
  return s.replace(/\s+/g, ' ').trim();
}
function lines(text) {
  return String(text == null ? '' : text).split(/\r?\n|\r/).map(function (l) { return normalise('policy', l); }).filter(Boolean);
}
function clean(list) { return (list || []).map(function (l) { return normalise('policy', l); }).filter(Boolean); }
function one(field, old, now) {                     // 바뀐 칸이면 편집 한 줄, 아니면 null
  var v = normalise(field, now), o = old == null ? '' : String(old);
  if (v === normalise(field, o)) return null;
  if (!v && field === 'title') return null;         // 제목은 비울 수 없다
  return {field: field, value: v, old: o};
}
function diff(before, after) {
  var b = before || {}, a = after || {}, out = [];
  var e = one('title', b.title, a.title); if (e) out.push(e);
  e = one('purpose', b.purpose, a.purpose); if (e) out.push(e);
  var bp = clean(b.policies), ap = clean(a.policies);
  if (JSON.stringify(bp) !== JSON.stringify(ap)) out.push({field: 'policies', value: ap, old: (b.policies || []).slice()});
  return out;
}
function pending(notes, id, orig) {
  var cur = null, base = (orig || []).slice(), gone = {}, whole = false;
  (notes || []).forEach(function (n) {
    if (n.screen !== id) return;
    if (n.edit === 'policies' && Array.isArray(n.value)) { cur = n.value.slice(); whole = true; return; }
    if (n.edit !== 'policy' || whole || !(n.index >= 0 && n.index < base.length)) return;
    if (n.op === 'delete' || !String(n.value == null ? '' : n.value).trim()) gone[n.index] = 1; else { base[n.index] = String(n.value); delete gone[n.index]; }
    cur = base.filter(function (x, i) { return !gone[i]; });
  });
  return cur;
}
function shown(s) {
  s = s || {};
  if (s.selected || s.blank) return {purpose: true, policies: true, mark: false};
  var p = s.pending || {};
  return {purpose: false, policies: false, mark: !!(p.purpose || p.policies)};
}

HD.caption = {FIELDS: FIELDS, normalise: normalise, lines: lines, diff: diff, pending: pending, shown: shown};
})();
