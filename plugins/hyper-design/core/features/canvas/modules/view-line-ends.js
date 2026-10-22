/* View — 선 고르기와 끝 손잡이(Q3). 기하·놓기 규칙은 modules/line-ends.js(Model), 여기는 누르기·손잡이 그리기·끌기.
   선(path.ln, 기획 갈래 빼고)을 누르면 그 쌍 강조(ctx.emphasise) + 도착 끝마다 둥근 손잡이(<circle class="ln-end">, 같은 svg).
   손잡이를 다른 카드로 끌어 놓으면 도착 바꾸기(ctx.retarget) — 끄는 동안 흐린 선(path.ln-ghost). 끄는 중 Esc = 취소.
   쉬는 중 Esc·빈 판 누르기·clear() = 손잡이 지우고 강조 풀기(ctx.unemphasise).
   HD.viewLineEnds.mount(ctx) → {select(from, to), clear(), selected() → {from, to}|null}
   ctx = {svg, rowsEl, toStage(clientX, clientY) → [x, y], cardBoxes() → [{id, x, y, w, h, hid, del}], emphasise(from, to), unemphasise(),
          retarget(from, oldTo, newTo, pending), toast(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NS = 'http://www.w3.org/2000/svg';

function mount(ctx) {
  var svg = ctx.svg, rowsEl = ctx.rowsEl, M = HD.lineEnds, sel = null, drag = null, down = null;

  function lineEl(from, to) {                        // 양방향 선은 a→b 하나로 그려진다 — 거꾸로 물어도 찾는다
    var ps = svg.querySelectorAll('path.ln:not(.plan)'), back = null;
    for (var i = 0; i < ps.length; i++) {
      var f = ps[i].getAttribute('data-from'), t = ps[i].getAttribute('data-to');
      if (f === from && t === to) return ps[i];
      if (f === to && t === from && ps[i].getAttribute('data-both') === '1') back = ps[i];
    }
    return back;
  }
  function wipe() {
    var hs = svg.querySelectorAll('circle.ln-end, path.ln-ghost');
    for (var i = 0; i < hs.length; i++) hs[i].remove();
  }
  function select(from, to) {
    if (drag) cancel();                               // 끄는 중 선을 새로 그리면(셸이 다시 고름) 끌기는 취소 — 떨어진 손잡이를 붙잡고 있지 않게
    var p = lineEl(from, to);
    if (!p) { clear(); return; }
    wipe();
    var f = p.getAttribute('data-from'), t = p.getAttribute('data-to');
    sel = {from: f, to: t};
    ctx.emphasise(f, t);
    M.handles({from: f, to: t, both: p.getAttribute('data-both') === '1', plan: p.classList.contains('plan'), d: p.getAttribute('d')}).forEach(function (h) {
      var c = document.createElementNS(NS, 'circle');
      c.setAttribute('class', 'ln-end');
      c.setAttribute('data-from', h.from); c.setAttribute('data-to', h.to);
      c.setAttribute('cx', h.at[0]); c.setAttribute('cy', h.at[1]); c.setAttribute('r', '7');
      c.setAttribute('fill', '#fff'); c.setAttribute('stroke', '#2b2b29'); c.setAttribute('stroke-width', '2');
      c.style.pointerEvents = 'auto'; c.style.cursor = 'grab';   // svg.ar 는 누르기를 통과시킨다 — 손잡이만 받는다
      c.addEventListener('pointerdown', function (e) { startDrag(c, p, h, e); });
      svg.appendChild(c);
    });
  }
  function clear() {
    if (drag) cancel();
    wipe();
    if (sel) { sel = null; ctx.unemphasise(); }
  }

  // 끌기: 고정 끝(반대쪽) → 포인터까지 흐린 선, 놓으면 Model 규칙대로 도착 바꾸기
  function startDrag(c, p, h, e) {
    if (e.button !== 0) return;
    e.preventDefault(); e.stopPropagation();          // 판이 끌려 움직이지 않게
    var en = M.ends(p.getAttribute('d')), fixed = h.from === p.getAttribute('data-from') ? en.start : en.end;
    var g = document.createElementNS(NS, 'path');
    g.setAttribute('class', 'ln-ghost'); g.setAttribute('fill', 'none'); g.setAttribute('stroke', '#6b6b66');
    g.setAttribute('stroke-width', '2'); g.setAttribute('stroke-dasharray', '6 4'); g.style.pointerEvents = 'none';
    svg.appendChild(g);
    drag = {c: c, h: h, g: g, fixed: fixed, pending: p.classList.contains('pd'), id: e.pointerId};
    c.setPointerCapture(e.pointerId); c.style.cursor = 'grabbing';
    move(e);
    c.addEventListener('pointermove', move);
    c.addEventListener('pointerup', up);
    c.addEventListener('pointercancel', cancel);
  }
  function move(e) {
    if (!drag) return;
    var q = ctx.toStage(e.clientX, e.clientY);
    drag.g.setAttribute('d', 'M' + drag.fixed[0] + ',' + drag.fixed[1] + ' L' + q[0] + ',' + q[1]);
    drag.c.setAttribute('cx', q[0]); drag.c.setAttribute('cy', q[1]);
  }
  function end() {                                    // 흐린 선 지우고 손잡이는 제자리로
    var d = drag; drag = null;
    d.c.removeEventListener('pointermove', move);
    d.c.removeEventListener('pointerup', up);
    d.c.removeEventListener('pointercancel', cancel);
    try { if (d.c.hasPointerCapture(d.id)) d.c.releasePointerCapture(d.id); } catch (x) { /* 이미 풀림 */ }
    d.g.remove();
    d.c.setAttribute('cx', d.h.at[0]); d.c.setAttribute('cy', d.h.at[1]); d.c.style.cursor = 'grab';
    return d;
  }
  function cancel() { if (drag) end(); }
  function up(e) {
    if (!drag) return;
    var d = end(), r = M.dropTarget(ctx.cardBoxes(), ctx.toStage(e.clientX, e.clientY), {from: d.h.from, to: d.h.to});
    if (!r) return;
    if (r.blocked === 'del') { ctx.toast('삭제 대기 화면에는 이을 수 없어요'); return; }   // E18
    clear();                                          // 고른 쌍은 곧 바뀐다
    ctx.retarget(d.h.from, d.h.to, r.id, d.pending);
  }

  // 선 누르기 = 고르기
  svg.addEventListener('click', function (e) {
    var p = e.target.closest ? e.target.closest('path.ln') : null;
    if (!p || p.classList.contains('plan')) return;
    e.stopPropagation();
    select(p.getAttribute('data-from'), p.getAttribute('data-to'));
  });
  // 빈 판 누르기(끌어 움직인 것 말고) = 풀기
  rowsEl.addEventListener('pointerdown', function (e) { down = [e.clientX, e.clientY]; });
  rowsEl.addEventListener('click', function (e) {
    if (!sel || drag) return;
    var moved = down && Math.abs(e.clientX - down[0]) + Math.abs(e.clientY - down[1]) > 4;
    if (moved) return;
    if (e.target.closest && e.target.closest('.card, .alabel, path.ln, circle.ln-end')) return;
    clear();
  });
  addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (drag) { e.preventDefault(); e.stopPropagation(); cancel(); return; }
    if (sel && !/^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '')) { e.preventDefault(); e.stopPropagation(); clear(); }   // 끌기 취소 > 선 고르기 풀기 > 셸의 Esc — 한 번에 하나
  }, true);

  return {select: select, clear: clear, selected: function () { return sel ? {from: sel.from, to: sel.to} : null; }};
}

HD.viewLineEnds = {mount: mount};
})();
