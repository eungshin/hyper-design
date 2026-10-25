/* Model — 카드 바로 복제 계획(51-6, Figma F19): 고른 카드마다 새 id·제목·파일과 판에서 끼울 자리. DOM·저장소를 쓰지 않는다.
   서버 쪽 같은 규칙 = screen_copy.py(도우미 /api/apply 의 'clone' 편집 — 캔버스가 고른 id·제목을 보내고, 쓰였으면 서버가 거절).
   plan(cards [{id, title, file, app?}](판 차례), srcs [id]) → {items: [{src, id, title, file, after}], refused: [{id, why: 'app'|'missing'}]}
     id = '<원본>-copy'(쓰였으면 -copy-2 …, 판의 id·앞서 계획한 복사본 모두 피함) · title = 원본 제목 + SUFFIX · file = 원본과 같은 폴더의 '<id>.html'
     after = 판에서 바로 뒤에 끼울 카드 id — 원본 뒤에 이어진 그 원본의 상태 변형('<원본>--…')은 건너뜀(빌드가 변형을 원래 화면 바로 뒤에 그리므로 같은 자리)
   HD.cardCopy = {SUFFIX, plan, freshId} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var SUFFIX = ' 복사';                                 // 옛 복제 메모(빈 레이아웃 길)와 같은 꼬리

function dest(file, id) { var f = String(file || ''), i = f.lastIndexOf('/'); return (i >= 0 ? f.slice(0, i + 1) : '') + id + '.html'; }

function freshId(taken, src) {
  var base = src + '-copy', n = 1, id = base;
  while (taken[id]) { n++; id = base + '-' + n; }
  return id;
}

function plan(cards, srcs) {
  cards = Array.isArray(cards) ? cards : [];
  var taken = {}, by = {}, order = [], items = [], refused = [];
  cards.forEach(function (c) { if (c && c.id != null) { var id = String(c.id); taken[id] = 1; by[id] = c; order.push(id); } });
  (Array.isArray(srcs) ? srcs : []).forEach(function (s) {
    var src = String(s), c = by[src];
    if (!c) { refused.push({id: src, why: 'missing'}); return; }
    if (c.app) { refused.push({id: src, why: 'app'}); return; }
    var id = freshId(taken, src); taken[id] = 1;
    var at = order.indexOf(src), after = src;
    for (var i = at + 1; i < order.length && order[i].indexOf(src + '--') === 0; i++) after = order[i];
    items.push({src: src, id: id, title: (c.title || src) + SUFFIX, file: dest(c.file || 'screens/' + src + '.html', id), after: after});
  });
  return {items: items, refused: refused};
}

HD.cardCopy = {SUFFIX: SUFFIX, plan: plan, freshId: freshId};
})();
