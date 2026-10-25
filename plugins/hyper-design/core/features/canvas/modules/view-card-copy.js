/* View — 카드 바로 복제(51-6, Figma F19: Ctrl+D = 프레임 복제 → 바로 오른쪽에, 복사본이 골라짐): 판에 복사본 카드를 먼저 끼우고 도우미 쓰기 한 번.
   계획(새 id·제목·파일·끼울 자리) = HD.cardCopy(Model). 상태 = 쓰기를 기다리거나 빌드 확인 전인 복사본(편집 id → {id, el}, 저장 안 함).
   등록부 기능 'cardCopy'(needs $ · $$ · toast · warn · cardEl · rowsEl) → {attach(A), copy(ids) → bool(맡음 — false = 도우미 없음, 셸의 예전 길), reverted(ids, why) → [편집 id]}
   A(셸이 attach 로 한 번) = {on() → 도우미로 열림, write(label, list) → Promise(view-sync write — 기록 한 줄·되돌리기 = 되살리기), app(id) → 앱 카드인가,
        card(item) → 새 카드 요소(줄 HTML 과 같은 모양 · 틀은 원본 파일을 먼저 싣는다), placed(ids) — 끼운 뒤 자리·크기·선·레이어 다시,
        removed(ids) — 거둔 뒤 다시, select(ids)}
   쓰기 = /api/apply 'clone' 편집(카드마다 하나, 한 번에 = 되돌리기 한 줄). 거절 = 그 복사본을 거두고 토스트 "화면 복제 — 파일에 쓰지 못해 되돌렸어요: <까닭>",
   도우미에 닿지 않음 = 모두 거둠 + 토스트, 뒤 빌드 실패(build.failed) = 셸이 reverted 로 알림 → 거둠 + 토스트. 앱 카드 = 거절 토스트(요청으로만). */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var LABEL = '화면 복제';

function mount(ctx) {
  var A = null, mine = {};
  function cards() {
    return ctx.$$('.card:not(.draft)', ctx.rowsEl).map(function (c) {
      var id = c.dataset.id, cv = ctx.$('.cover', c);
      return {id: id, title: cv ? cv.dataset.title : id, file: cv ? cv.dataset.file : '', app: !!(A && A.app(id))};
    });
  }
  function takeBack(made, why) {
    var ids = made.map(function (m) { if (m.el.parentNode) m.el.remove(); return m.it.id; });
    if (!ids.length) return;
    A.removed(ids);
    A.select(made.map(function (m) { return m.it.src; }).filter(function (id) { return !!ctx.cardEl(id); }));
    ctx.toast(LABEL + ' — ' + why);
  }
  function copy(ids) {
    if (!A || !A.on()) return false;
    var p = HD.cardCopy.plan(cards(), ids || []);
    if (p.refused.some(function (r) { return r.why === 'app'; })) ctx.toast('앱 카드는 복제할 수 없어요 — 요청(메모)으로만 바꿀 수 있어요');
    p.refused.forEach(function (r) { if (r.why === 'missing') ctx.warn('[hd] 복제: 판에 없는 카드 ' + r.id); });
    if (!p.items.length) return true;
    var made = [];
    p.items.forEach(function (it) {
      var at = ctx.cardEl(it.after), el = at && A.card(it);
      if (!el) { ctx.warn('[hd] 복제: 끼울 자리가 없어요 ' + it.after); return; }
      at.parentNode.insertBefore(el, at.nextSibling);
      made.push({it: it, el: el, note: {id: HD.edits.newId(), screen: it.src, edit: 'clone', to: it.id, value: it.title, opt: true}});
    });
    if (!made.length) return true;
    A.placed(made.map(function (m) { return m.it.id; }));
    A.select(made.map(function (m) { return m.it.id; }));
    A.write(LABEL, made.map(function (m) { return m.note; })).then(function (res) {
      var ok = {}, why = {};
      ((res && res.applied) || []).forEach(function (id) { ok[id] = 1; });
      ((res && res.failed) || []).forEach(function (f) { if (f && f.id != null) why[f.id] = f.reason; });
      var bad = made.filter(function (m) { return !ok[m.note.id]; });
      made.forEach(function (m) { if (ok[m.note.id]) mine[m.note.id] = m; });
      if (bad.length) takeBack(bad, '파일에 쓰지 못해 되돌렸어요: ' + (why[bad[0].note.id] || (res && res.error) || '도우미가 받지 않았어요'));
    }, function (e) {
      ctx.warn('[hd] 복제 쓰기 실패: ' + (e && e.message || e));
      takeBack(made, '도우미에 닿지 않아 되돌렸어요');
    });
    return true;
  }
  function reverted(ids, why) {                       // 뒤 빌드가 깨져 도우미가 되돌린 쓰기 중 내 것 — 판에서 거두고 한 번 알림(셸이 판을 파일대로 다시 불러온다)
    var got = (ids || []).filter(function (id) { return mine[id]; });
    if (!got.length) return [];
    var made = got.map(function (id) { var m = mine[id]; delete mine[id]; return m; });
    takeBack(made, '빌드가 깨져 되돌렸어요: ' + (why || ''));
    return got;
  }
  return {attach: function (a) { A = a; return this; }, copy: copy, reverted: reverted};
}

HD.feature('cardCopy', {needs: ['$', '$$', 'toast', 'warn', 'cardEl', 'rowsEl'], mount: mount});
})();
