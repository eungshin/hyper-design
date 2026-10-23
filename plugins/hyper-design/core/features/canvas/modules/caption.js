/* Model — 카드 아래 글(제목·설명·정책 줄) 한 상자 고치기의 비교 규칙(H16). DOM 을 쓰지 않는다.
   값 모양 = {title: 글, purpose: 글, policies: [글]}
   normalise(field, text) → 지금 고치기 칸과 같은 빈칸 정리
     title·policy = 모든 빈칸(줄바꿈 포함)을 한 칸으로 + 앞뒤 자르기
     purpose = 띄어쓰기·탭을 한 칸으로, 줄바꿈 앞뒤 띄어쓰기 지우기, 앞뒤 자르기(줄바꿈은 남긴다)
   diff(before, after, opts) → [{field: 'title'|'purpose'|'policy', index?: 번호, op?: 'delete', value: 새 글, old: 원래 글}]
     바뀌지 않은 칸은 빼고, 정책 줄은 번호끼리 비교. 비운 칸(#243): 제목 = 편집 아님(비울 수 없다) · 설명 = value '' 편집
     · 있던 정책 줄 = {op:'delete', value:''}(원래 번호 그대로 — 여러 줄이면 helper 가 큰 번호부터 지운다)
     before 보다 뒤 번호(새 줄)는 opts.allowAdd 일 때만 — 번호는 before 줄 수부터 빈 줄 없이 이어서, 빈 새 줄은 버린다
   HD.caption = {FIELDS, normalise, diff} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var FIELDS = ['title', 'purpose', 'policy'];

function normalise(field, text) {
  var s = text == null ? '' : String(text);
  if (field === 'purpose') return s.replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').trim();
  return s.replace(/\s+/g, ' ').trim();
}
function one(field, old, now, index, isNew) {      // 바뀐 칸이면 편집 한 줄, 아니면 null
  var v = normalise(field, now), o = old == null ? '' : String(old);
  if (v === normalise(field, o)) return null;
  if (!v && (field === 'title' || isNew)) return null;   // 제목은 비울 수 없고, 빈 새 줄은 버린다
  var e = {field: field, value: v, old: o};
  if (index != null) e.index = index;
  if (!v && field === 'policy') e = {field: field, index: index, op: 'delete', value: '', old: o};
  return e;
}
function diff(before, after, opts) {
  var b = before || {}, a = after || {}, out = [], allowAdd = !!(opts && opts.allowAdd);
  var e = one('title', b.title, a.title); if (e) out.push(e);
  e = one('purpose', b.purpose, a.purpose); if (e) out.push(e);
  var bp = b.policies || [], ap = a.policies || [], next = bp.length;
  for (var i = 0; i < ap.length; i++) {
    if (i < bp.length) { e = one('policy', bp[i], ap[i], i); if (e) out.push(e); continue; }
    if (!allowAdd) continue;
    e = one('policy', '', ap[i], next, true); if (e) { out.push(e); next++; }
  }
  return out;
}

HD.caption = {FIELDS: FIELDS, normalise: normalise, diff: diff};
})();
