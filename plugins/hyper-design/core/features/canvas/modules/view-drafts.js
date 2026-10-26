/* View — 빈 레이아웃(N 도구 · 빈 곳에 놓기 · 여기에 레이아웃 · 레이어 [+]): 메모(edit 'new-screen') 하나 = 판 위 흰 카드, 이름·목적 고치기, 보내면 AI 가 채운다.
   메모 모양 = Model HD.edits.layout·layoutText·layoutOf·layoutId. 쌓기 = ctx.add(view-edit-path), 크기 대화상자·크기 = 등록부 기능 artboard(ctx.artboard()).
   HD.viewDrafts.mount(ctx) → {note(cx, cy) → 그 화면 자리의 빈 레이아웃 메모(쌓지 않음), add(cx, cy, size?, name?), at(cx, cy)(대화상자 뒤 놓기), render(ids?), of(id), edit(id, changes)}
   ctx = {$, $$, rowsEl, notes(NS), zoom() → z, save(), record(op), toast(msg), add(label, list, msg), artboard() → AB|null, place(card)(카드 옮긴 자리), cardEl(id), scr(id)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, NS = ctx.notes, E = HD.edits;

  function pt(cx, cy) { var r = ctx.rowsEl.getBoundingClientRect(), z = ctx.zoom(); return {x: Math.round((cx - r.left) / z), y: Math.round((cy - r.top) / z)}; }
  function note(cx, cy, name) { return E.layout(E.layoutId(Date.now(), Math.random()), pt(cx, cy), name); }
  function of(id) { return E.layoutOf(NS.list(), id); }
  function add(cx, cy, size, name) {                 // size·name = 새 화면 대화상자에서 고른 크기·이름(task 46) — 크기는 그 카드 크기로(되돌리기는 카드와 함께: 빈 카드가 사라지면 크기는 쓰이지 않음)
    var n = note(cx, cy, name), AB = ctx.artboard();
    ctx.add('빈 레이아웃', [n], '빈 레이아웃을 놓았어요 — 메모를 남기고 보내면 채워져요');
    if (size && AB) AB.seed(n.screen, size);
  }
  function at(cx, cy) {                              // N 도구·여기에 레이아웃·레이어 [+] = 새 화면 대화상자(크기·이름) 뒤 그 자리에 빈 카드 — 대화상자가 붙지 못했으면 기본 크기로 바로
    var AB = ctx.artboard();
    if (!AB) { add(cx, cy); return; }
    AB.openNew(function (size, name) { add(cx, cy, size, name); });
  }
  function render(ids) {                             // 메모의 빈 레이아웃 → 판 위 흰 카드(없어진 것은 지운다) · ids = 닿은 화면만 다시(없으면 전부)
    var want = {}, AB = ctx.artboard();
    NS.list().forEach(function (n) { if (n.edit === 'new-screen') want[n.screen] = n; });
    $$('.card.draft', ctx.rowsEl).forEach(function (c) { if (!want[c.dataset.id]) c.remove(); });
    Object.keys(want).forEach(function (id) {
      var n = want[id], c = ctx.cardEl(id);
      if (c && ids && ids.indexOf(id) < 0) return;
      if (!c) {
        c = document.createElement('div'); c.className = 'card draft'; c.dataset.id = id;
        c.innerHTML = '<div class="phone"><div class="blank">빈 레이아웃</div><button class="cover" data-file=""></button></div><div class="ftitle"></div><div class="fdesc"></div>';
        ctx.rowsEl.appendChild(c);
      }
      c.dataset.x = n.x; c.dataset.y = n.y;
      var cv = $('.cover', c); cv.dataset.title = n.value; cv.setAttribute('aria-label', n.value + ' — 빈 레이아웃(두 번 누르면 메모)');
      $('.ftitle', c).textContent = n.value; $('.fdesc', c).textContent = n.purpose || '';   // 이름 · 목적(여러 줄)
      if (AB) AB.paint([id]);                          // 그 빈 카드의 크기(다시 만든 카드에도)
      ctx.place(c);
    });
  }
  function edit(id, changes) {                       // 빈 레이아웃 카드 글(#225): 이름·목적은 그 메모 안(n.value·n.purpose) — 보내면 목적이 AI 의 첫째 브리프 · 되돌리기 한 단계
    var n0 = of(id); if (!n0) { ctx.toast('그 빈 레이아웃이 없어요 — 이미 지워졌어요'); return; }
    var before = {value: n0.value, purpose: n0.purpose || ''}, after = {value: before.value, purpose: before.purpose};
    changes.forEach(function (ch) { if (ch.field === 'title') after.value = ch.value; else if (ch.field === 'purpose') after.purpose = ch.value; });
    var set = function (v) {
      var n = of(id); if (!n) return;
      n.value = v.value; n.purpose = v.purpose; n.note = n.copyOf ? E.say.copy(v.value, n.screen, ctx.scr(n.copyOf)) : E.layoutText(n); n.sent = false; ctx.save();
    };
    set(after);
    ctx.record({label: '빈 레이아웃 글', undo: function () { set(before); }, redo: function () { set(after); }});
  }

  return {note: note, add: add, at: at, render: render, of: of, edit: edit};
}

HD.viewDrafts = {mount: mount};
})();
