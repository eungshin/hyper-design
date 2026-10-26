/* View — 카드 동작: 삭제(진짜 화면 = 삭제 요청·도우미면 파일에서 바로 · 빈 레이아웃 = 그 메모째) · 삭제 대기 표시 · 복제(Ctrl+D) · 들어오는 연결 끊기 · Del/Backspace.
   편집 모양 = HD.edits(say), 쌓기 = ctx.add(view-edit-path), 바로 복제 = 등록부 기능 cardCopy(ctx.copy()), 빈 복제 카드 = view-drafts(ctx.layoutNote).
   HD.viewCardActions.mount(ctx) → {paint(ids?)(삭제 대기 표시), isDeleted(id), del(ids), dup(ids), cutIn(ids)}
   ctx = {$, notes(NS), save(), record(op), toast(msg, undo?), add(label, list, msg?), note(id, h, text), scr(id), title(id), cardEl(id), cardsOf(ids?), guard(ids), locked(id),
          selected() → 고른 id, clear()(고르기 풀기), sync() → VS, copy() → cardCopy|null, app(id) → 앱 카드인가, layoutNote(cx, cy), sizeOf(id), artboard() → AB|null,
          tagScale(), modalOpen(), tab() → 지금 탭, typing(e), element() → 고른 요소 {card, h}|null, unselect(), removeElement(id, h), changed()(선·보이는 카드)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, NS = ctx.notes, deleted = {};

  function paint(ids) {                              // 삭제 대기(메모 edit=delete) → 판에서 빼고, 그 화면으로 오는 선도 겹쳐 그리기에서 뺀다 · ids = 닿은 화면만
    deleted = {}; NS.list().forEach(function (n) { if (n.edit === 'delete') deleted[n.screen] = 1; });
    var changed = false;
    ctx.cardsOf(ids).forEach(function (c) {          // 사라지지 않고 흐리게 + '삭제 대기' — 보내고 반영되기 전까지 무엇이 지워질지 판에서 보인다
      var d = !!deleted[c.dataset.id], chip = $('.delchip', c);
      if (d && !chip) { chip = document.createElement('span'); chip.className = 'delchip'; chip.textContent = '× 삭제 대기'; $('.phone', c).appendChild(chip); }
      if (!d && chip) chip.remove();
      if (c.classList.contains('del') !== d) { c.classList.toggle('del', d); changed = true; }
    });
    if (changed) ctx.changed();
  }
  function del(ids) {                                // 진짜 화면 = 삭제 요청 메모 · 빈 레이아웃 = 그 메모(와 그리로 가는 잇기)를 지움 — 되돌리기 됨
    if (ctx.guard(ids)) { ids = ids.filter(function (id) { return !ctx.locked(id); }); if (!ids.length) return; }
    var drafts = ids.filter(function (id) { var c = ctx.cardEl(id); return c && c.classList.contains('draft'); });
    var real = ids.filter(function (id) { return drafts.indexOf(id) < 0; });
    ctx.clear();
    var pend = function () { if (real.length) ctx.add('화면 삭제', real.map(function (id) {
      var n = ctx.note(id, {path: '(화면 전체)', text: ctx.title(id), rect: null}, HD.edits.say.removeScreen(ctx.scr(id))); n.edit = 'delete'; return n;
    }), real.length + '개 화면을 지웠어요 — 반영 대기'); };
    var VS = ctx.sync();
    if (real.length && VS && VS.on) VS.del(real).catch(pend); else pend();   // 파일에 바로 지우고 오는 연결도 끊음(E1·E10)
    if (drafts.length) {
      var gone = NS.list().filter(function (n) { return drafts.indexOf(n.screen) >= 0 || (n.op === 'link' && drafts.indexOf(n.to) >= 0); });
      var drop = function () { NS.remove(function (n) { return gone.indexOf(n) >= 0; }); ctx.save(); };
      drop();
      ctx.record({label: '빈 레이아웃 지우기', undo: function () { gone.forEach(function (n) { NS.add(n); }); ctx.save(); }, redo: drop});
      ctx.toast('빈 레이아웃을 지웠어요', true);
    }
  }
  function dupOne(id) {                              // 도우미 없음·빈 레이아웃: 오른쪽 옆에 흰 복제 카드(빈 레이아웃과 같은 메모, 보내면 AI 가 복제)
    var c = ctx.cardEl(id); if (!c) return;
    var r = $('.phone', c).getBoundingClientRect(), n = ctx.layoutNote(r.right + 40 * ctx.tagScale(), r.top), AB = ctx.artboard();
    n.value = ctx.title(id) + ' 복사'; n.copyOf = id; n.note = HD.edits.say.copy(n.value, n.screen, ctx.scr(id));
    ctx.add('복제', [n], '복제했어요 — 반영 대기');
    if (AB && ctx.sizeOf(id).custom) AB.seed(n.screen, ctx.sizeOf(id));   // 복제 카드는 원본 크기 그대로
  }
  function dup(ids) {                                // Ctrl+D·메뉴 [복제](51-6, Figma F19): 도우미 = 파일째 바로 복제(cardCopy — 오른쪽 옆, 복사본이 골라짐) · 없으면 예전 흰 복제 카드 · 앱 카드 = 거절
    var app = ids.filter(ctx.app), rest = ids.filter(function (id) { return !ctx.app(id); }), CC = ctx.copy();
    if (app.length) ctx.toast('앱 카드는 복제할 수 없어요 — 요청(메모)으로만 바꿀 수 있어요');
    var real = rest.filter(function (id) { var c = ctx.cardEl(id); return c && !c.classList.contains('draft'); });
    if (real.length && CC && CC.copy(real)) rest = rest.filter(function (id) { return real.indexOf(id) < 0; });
    rest.forEach(dupOne);
  }
  function cutIn(ids) {
    ctx.add('들어오는 연결 끊기', ids.map(function (id) {
      var n = ctx.note(id, {path: '(이 화면으로 오는 연결)', text: ctx.title(id), rect: null}, HD.edits.say.cutIn(ctx.scr(id))); n.edit = 'cut-in'; return n;
    }), '이 화면으로 오는 연결을 끊었어요');
  }

  addEventListener('keydown', function (e) {         // Ctrl/Cmd+D = 고른 카드 복제(51-6) — 고른 요소가 있으면 요소 복제(view-blocks 가 먼저 받는다)
    if (!(e.ctrlKey || e.metaKey) || e.altKey || e.shiftKey || (e.key || '').toLowerCase() !== 'd' || e.defaultPrevented || ctx.typing(e) || ctx.modalOpen() || ctx.tab() !== 'screens' || ctx.element()) return;
    var ids = ctx.selected(); if (!ids.length) return;
    e.preventDefault(); dup(ids);
  });
  addEventListener('keydown', function (e) {         // Del · Backspace = 고른 카드 삭제(입력 중·크게 보기 아닐 때)
    if ((e.key !== 'Delete' && e.key !== 'Backspace') || ctx.typing(e) || ctx.modalOpen() || ctx.tab() !== 'screens') return;
    var se = ctx.element();
    if (se) { e.preventDefault(); ctx.unselect(); ctx.removeElement(se.card.dataset.id, se.h); return; }   // 고른 요소 = 요소 지우기(task 30) — Backspace 도(Figma · 카드 전체로 떨어지지 않게)
    var ids = ctx.selected(); if (!ids.length) return;
    e.preventDefault(); del(ids);
  });

  return {paint: paint, isDeleted: function (id) { return !!deleted[id]; }, del: del, dup: dup, cutIn: cutIn};
}

HD.viewCardActions = {mount: mount};
})();
