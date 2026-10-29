/* View — 판에서 글자 고치기로 들어가기·옮기기(R52): 선택(V) 두 번 누르기 = 그 글자 고치기(글자가 아니면 크게 보기) · 고치는 중 선택(V)으로 다른 글자 누르기 = 그 글자로 전환.
   규칙은 HD.textEdit(Model). 판 카드 iframe 은 누르기를 받지 않아(pointer-events:none) 셸이 덮개(.cover) 누르기를 넘긴다 — 크게 보기는 palette.js 가 맡는다.
   고치는 중 판을 누르기 시작하면(pointerdown — 틀 밖 누르기의 blur 저장보다 먼저) 끝나는 고치기의 '그 요소 다시 고르기'를 뺀다(ctx.away — 누른 것이 골라진다).
   HD.viewTextEdit.mount(ctx) → {dbl(card, e) → bool(맡음), click(card, e)(셸이 하던 고르기를 부른 뒤 — 같은 틀에 묻는 차례가 그 뒤라 고치기가 고르기를 덮는다)}
   ctx = {pane, tool() → 지금 도구, typing() → 판에서 고치는 중인가, away() → 끝나는 고치기를 다시 고르지 않게, hit(card, x, y, quiet, cb, leaf)(view-frame-ask),
          edit(id, h)(셸 editScreenText), open(card)(크게 보기)}
   상태 = 이번 누르기를 고치는 중에 시작했나(pressed) 하나 — 저장 없음 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var T = HD.textEdit, pressed = false;
  ctx.pane.addEventListener('pointerdown', function (e) {
    pressed = e.button === 0 && !!ctx.typing();
    if (pressed) ctx.away();
  }, true);
  function isText(h) { return !!(h && !h.none && h.path); }
  function dbl(card, e) {
    if (!T.dbl(ctx.tool(), 'board') || card.classList.contains('draft')) return false;
    var id = card.dataset.id;
    ctx.hit(card, e.clientX, e.clientY, true, function (h) { if (isText(h)) ctx.edit(id, h); else ctx.open(card); }, true);   // 답 없음(palette.js 없음)·글자 아님 = 하던 대로 크게 보기
    return true;
  }
  function click(card, e) {
    var was = pressed, tool = ctx.tool(); pressed = false;
    if (!T.press({editing: was, text: true, tool: tool}) || card.classList.contains('draft')) return;
    var id = card.dataset.id;
    ctx.hit(card, e.clientX, e.clientY, true, function (h) { if (T.press({editing: true, text: isText(h), tool: tool}) === 'switch') ctx.edit(id, h); }, true);
  }
  return {dbl: dbl, click: click};
}

HD.viewTextEdit = {mount: mount};
})();
