/* View — 폴더(판의 화면 줄) 제목 끌기 = 폴더째 옮기기 + 제목이 그 폴더 카드를 따라가기(R31, Figma 섹션 이름 끌기).
   제목(.flow > .glabel)을 왼쪽 버튼으로 4px 넘게 끌면(Space·가운데·오른쪽 버튼은 예전대로 판) 그 폴더 카드 모두(숨김 포함, 지우기 대기 빼고)를 같은 거리만큼:
   끄는 중엔 cardPos.put·place(저장 없음), 놓으면 제자리로 돌린 뒤 cardPos.move 한 번 = 카드 옮긴 자리(card-pos) 저장 + 되돌리기 한 줄(카드 끌기와 같은 길).
   계획 = HD.rowOps.dragPlan(잠긴 화면이 끼면 옮기지 않고 토스트). 끈 뒤 따라오는 click 하나는 삼킨다(제목 누르기 = 폴더 고르기가 되지 않게). 움직이지 않으면 그대로 누르기·두 번 누르기.
   제목 자리: 그 폴더 카드 옮긴 거리의 가장 작은 값(HD.rowOps.titleShift)을 제목의 CSS translate 로 — 카드 style 이 바뀌거나 줄이 들고 날 때 한 프레임에 한 번.
   가진 상태 = 끄는 중 하나(저장 없음). HD.feature('rowDrag', {needs: ['rowsEl', 'cardPos', 'view', 'locked', 'toast', 'warn'], mount(ctx) → {paint()}})
   ctx.lines()(있으면) = 끄는 중 선 다시(한 프레임에 한 번) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var O = HD.rowOps, rowsEl = ctx.rowsEl, CP = ctx.cardPos, drag = null, raf = 0;
  function headOf(t) {
    var g = t && t.closest ? t.closest('.glabel') : null;
    return g && g.parentNode && g.parentNode.classList.contains('flow') && g.parentNode.parentNode === rowsEl ? g : null;
  }
  function cardsOf(f) { return Array.prototype.filter.call(f.querySelectorAll('.card'), function (c) { return !c.classList.contains('del'); }); }

  // 제목이 카드를 따라간다
  function paintFlow(f) {
    var g = f.querySelector(':scope > .glabel'); if (!g) return;
    var s = O.titleShift(cardsOf(f).map(function (c) { return CP.at(c.dataset.id) || {dx: 0, dy: 0}; }));
    var v = s.dx || s.dy ? s.dx + 'px ' + s.dy + 'px' : '';
    if (g.style.translate !== v) g.style.translate = v;
  }
  function paint() { Array.prototype.forEach.call(rowsEl.querySelectorAll(':scope > .flow'), paintFlow); }
  function later() { if (!raf) raf = requestAnimationFrame(function () { raf = 0; paint(); }); }
  new MutationObserver(function (ms) {
    for (var i = 0; i < ms.length; i++) {
      var m = ms[i];
      if (m.type === 'childList' || (m.target.classList && m.target.classList.contains('card'))) { later(); return; }
    }
  }).observe(rowsEl, {childList: true, subtree: true, attributes: true, attributeFilter: ['style']});

  // 제목 끌기 = 폴더째 옮기기
  function zoom() { var v = ctx.view && ctx.view.get ? ctx.view.get() : null; return v && v.z > 0 ? v.z : 1; }
  function swallow() {                               // 끈 뒤 오는 click 하나만(제목 누르기 = 고르기 막기) — 안 오면 곧 푼다
    var eat = function (e) { e.stopPropagation(); e.preventDefault(); };
    addEventListener('click', eat, true);
    setTimeout(function () { removeEventListener('click', eat, true); }, 0);
  }
  function put(d, to) {                              // to = {id: {dx, dy, g}|undefined} — 끄는 중·제자리(저장 없음)
    d.cards.forEach(function (c) { CP.put(c.dataset.id, to[c.dataset.id]); CP.place(c); });
    paintFlow(d.f);
    if (ctx.lines) ctx.lines();
  }
  rowsEl.addEventListener('pointerdown', function (e) {
    var g = headOf(e.target);
    if (!g || g.isContentEditable || e.button !== 0 || (e.target.closest && e.target.closest('.space'))) return;
    if (rowsEl.closest && rowsEl.closest('.space')) return;   // Space 를 누른 채 = 판 이동(셸)
    e.stopPropagation();                             // 셸의 판 끌기 대신 — 누르기·두 번 누르기(click·dblclick)는 그대로 온다
    var f = g.parentNode, cards = cardsOf(f), origin = {};
    cards.forEach(function (c) { var p = CP.at(c.dataset.id); origin[c.dataset.id] = p ? {dx: p.dx, dy: p.dy, g: p.g} : undefined; });
    drag = {id: e.pointerId, g: g, f: f, x: e.clientX, y: e.clientY, z: zoom(), cards: cards, origin: origin, moved: false, plan: null};
  });
  addEventListener('pointermove', function (e) {
    if (!drag || e.pointerId !== drag.id) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.moved) {
      if (Math.hypot(dx, dy) <= 4) return;
      var ids = drag.cards.map(function (c) { return c.dataset.id; }), locked = {};
      ids.forEach(function (id) { if (ctx.locked(id)) locked[id] = true; });
      var chk = O.dragPlan(ids, locked, 0, 0);
      if (chk.error) { ctx.toast(chk.error); drag = null; return; }
      drag.moved = true; drag.g.classList.add('hd-row-moving');
      try { drag.g.setPointerCapture(e.pointerId); } catch (err) {}
    }
    var to = {}, mx = dx / drag.z, my = dy / drag.z;
    drag.cards.forEach(function (c) {
      var o = drag.origin[c.dataset.id] || {dx: 0, dy: 0};
      to[c.dataset.id] = {dx: Math.round(o.dx + mx), dy: Math.round(o.dy + my), g: CP.group(c)};
    });
    drag.mx = mx; drag.my = my;
    put(drag, to);
  });
  function end(e) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    var d = drag; drag = null;
    if (!d.moved) return;
    d.g.classList.remove('hd-row-moving');
    swallow();
    put(d, d.origin);                                // 제자리로 돌린 뒤 한 번에 옮긴다(저장 + 되돌리기 한 줄)
    var p = O.dragPlan(d.cards.map(function (c) { return c.dataset.id; }), {}, d.mx, d.my);
    if (p.error) { ctx.toast(p.error); return; }
    if (Object.keys(p.moves).length && !CP.move(p.moves, '폴더 옮기기')) ctx.warn('[hd] 폴더 옮기기: 옮길 카드를 찾지 못했어요');
    paintFlow(d.f);
  }
  addEventListener('pointerup', end);
  addEventListener('pointercancel', end);
  paint();
  return {paint: paint};
}

HD.feature('rowDrag', {needs: ['rowsEl', 'cardPos', 'view', 'locked', 'toast', 'warn'], mount: mount});
})();
