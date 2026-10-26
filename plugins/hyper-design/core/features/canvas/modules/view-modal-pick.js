/* View — 크게 보기 여러 요소 고르기(R19): 선택(V)으로 고른 요소 목록(규칙 HD.elPick — Shift = 더하기·빼기, 주인 = 마지막 것)과 고른 요소마다 테두리(#mbox 위 .msel-box).
   요소 막대는 주인만 — 셸이 pick 의 답으로 BK.show/hide 한다. 상태 = 고른 목록 [{screen, d(hd-sel 답)}](저장하지 않음, 크게 보기를 닫거나 도구·화면이 바뀌면 셸이 clear).
   HD.viewModalPick.mount(ctx) → {pick(screen, d, add) → 주인 d|null, clear(), all() → [{screen, d}], paint()}
   ctx = {box(#mbox), scale() → 크게 보기 배율}
   오류 탐지: path 없는 답은 목록을 바꾸지 않는다(셸이 토스트) · rect 가 없는 것은 테두리만 빼고 목록에는 둔다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var P = HD.elPick, sels = [], layer = document.createElement('div');
  layer.className = 'msel-layer'; layer.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none';
  ctx.box.appendChild(layer);
  function keyOf(s) { return s && s.d && s.d.path ? P.key(s.screen, s.d.path) : ''; }
  function paint() {
    var s = ctx.scale() || 1, pr = P.primary(sels);
    layer.innerHTML = '';
    sels.forEach(function (x) {
      var r = x.d.rect; if (!r) return;
      var b = document.createElement('div');
      b.className = 'msel-box' + (x === pr ? ' pri' : ''); b.dataset.key = keyOf(x);
      b.style.cssText = 'position:absolute;box-sizing:border-box;border:2px solid var(--ui-mark);border-radius:2px;left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px;width:' + (r.w * s) + 'px;height:' + (r.h * s) + 'px';
      layer.appendChild(b);
    });
  }
  function pick(screen, d, add) {
    if (!d || !d.path) return P.primary(sels) ? P.primary(sels).d : null;
    var it = {screen: String(screen), d: d};
    sels = add ? P.toggle(sels, it, keyOf) : P.only(it);
    paint();
    var pr = P.primary(sels); return pr ? pr.d : null;
  }
  function clear() { if (!sels.length) return; sels = []; paint(); }
  return {pick: pick, clear: clear, all: function () { return sels.slice(); }, paint: paint};
}

HD.viewModalPick = {mount: mount};
})();
