/* Model — 카드 아래 글(제목 + 본문 한 칸) 고치기의 비교 규칙과 판에 보일 칸(H16 · task 31 · R21). DOM 을 쓰지 않는다.
   본문 = screens.json 의 purpose 하나(여러 줄 자유 글, 비워도 됨). 옛 데이터의 policies 줄은 본문 끝에 '- ' 줄로 합쳐 보이고(body),
   본문을 고쳐 저장하면 purpose 로 접혀 들어가고 policies 는 빈 목록이 된다(diff — 쓴 글은 사라지지 않는다).
   normalise(field, text) → 빈칸 정리
     title·policy = 모든 빈칸(줄바꿈 포함)을 한 칸으로 + 앞뒤 자르기
     purpose = 띄어쓰기·탭을 한 칸으로, 줄바꿈 앞뒤 띄어쓰기 지우기, 앞뒤 자르기(줄바꿈·빈 줄은 남긴다)
   body(purpose, policies) → 보일 본문 = purpose + 정책 줄마다 '- 줄'(빈 줄 버림)
   diff(before{title, purpose, policies}, after{title, body}) → [{field: 'title'|'purpose'|'policies', value, old}]
     제목: 바뀌면 편집 · 비운 제목 = 편집 아님(#243). 본문: body(before) 와 같으면 아무것도 안 함(옛 데이터 그대로) ·
     다르면 purpose = 새 본문(원래 purpose 와 같으면 빼고) + 원래 정책이 있으면 {field:'policies', value: []}(접기)
   pending(notes, id, orig) → 그 화면의 반영 대기 정책 목록(없으면 null) — 옛 메모(policy[i]·policies)를 차례대로 얹는다(목록 편집이 통째로 이김)
   shown({selected, blank, pending:{purpose, policies}}) → {purpose, policies, mark} 판의 카드 아래 글에 보일 칸
     고른 카드·빈 레이아웃 = 다 보임 · 아니면 제목만, 본문에 반영 대기가 있으면 mark(작은 표시)
   origOf(rows) → {화면 id: {title, purpose, policies(사본)}} — 데이터 줄(D.rows·새 데이터 nd.rows)의 원래 글(셸 C8 — 처음·쓴 뒤 데이터가 같은 길)
   HD.caption = {FIELDS, normalise, body, diff, pending, shown, origOf} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var FIELDS = ['title', 'purpose'];

function normalise(field, text) {
  var s = text == null ? '' : String(text);
  if (field === 'purpose') return s.replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').trim();
  return s.replace(/\s+/g, ' ').trim();
}
function clean(list) { return (Array.isArray(list) ? list : []).map(function (l) { return normalise('policy', l); }).filter(Boolean); }
function body(purpose, policies) {
  var p = purpose == null ? '' : String(purpose), pol = clean(policies).map(function (l) { return '- ' + l; });
  return (p ? [p] : []).concat(pol).join('\n');
}
function diff(before, after) {
  var b = before || {}, a = after || {}, out = [];
  var t = normalise('title', a.title), ot = b.title == null ? '' : String(b.title);
  if (t && t !== normalise('title', ot)) out.push({field: 'title', value: t, old: ot});   // 제목은 비울 수 없다
  var now = normalise('purpose', a.body), op = b.purpose == null ? '' : String(b.purpose);
  if (now === normalise('purpose', body(op, b.policies))) return out;   // 본문 그대로 = 옛 데이터도 그대로
  if (now !== normalise('purpose', op)) out.push({field: 'purpose', value: now, old: op});
  if (clean(b.policies).length) out.push({field: 'policies', value: [], old: b.policies.slice()});   // 정책 줄은 본문에 접혀 들어갔다
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

function origOf(rows) {
  var o = {};
  (Array.isArray(rows) ? rows : []).forEach(function (row) {
    ((row && row.screens) || []).forEach(function (sc) { o[sc.id] = {title: sc.title || '', purpose: sc.purpose || '', policies: (sc.policies || []).slice()}; });
  });
  return o;
}

HD.caption = {FIELDS: FIELDS, normalise: normalise, body: body, diff: diff, pending: pending, shown: shown, origOf: origOf};
})();
