/* View — 판 위 이름표를 화면에서 같은 크기로(R27 F01): #stage 의 data-zoom 이 바뀌면 #rows 에 CSS 변수 --lz(= 1/z, 규칙 HD.labelScale)를 쓴다.
   확대 중엔 한 프레임에 한 번 3% 넘게 바뀔 때만, 멈춘 뒤 150ms 에 정확한 값 — 그때 document 'hd-label-scale' {lz} 를 보낸다(선 태그 겹침 다시 재기 등).
   이름표 CSS 는 각 주인(shell.css 의 R27 F01 블록 · view-busy · view-rows)이 calc(… * var(--lz,1)) 또는 scale: var(--lz,1) 로 쓴다 — 여기는 값만.
   가진 상태: 마지막으로 쓴 값(DOM 의 --lz) · 저장 없음. HD.feature('labelScale', {needs: ['rowsEl', 'warn'], mount(ctx) → {now() → 지금 --lz 수}}) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var L = HD.labelScale, rowsEl = ctx.rowsEl, stage = rowsEl.parentNode, raf = 0, timer = 0, warned = false;
  function zoom() { return stage && stage.dataset ? stage.dataset.zoom : null; }
  function write(exact) {
    var v = L.inv(zoom());
    if (v == null) {
      if (!warned) { warned = true; ctx.warn('[hd] 판 배율(data-zoom)을 읽지 못해 이름표를 1배로 둬요: ' + zoom()); }
      v = 1;
    }
    var old = rowsEl.style.getPropertyValue('--lz');
    if (L.put(old, v, exact)) rowsEl.style.setProperty('--lz', L.fmt(v));
    if (exact) document.dispatchEvent(new CustomEvent('hd-label-scale', {detail: {lz: v}}));
  }
  var last = zoom();
  function changed() {
    var z = zoom(); if (z === last) return;
    last = z;
    if (!raf) raf = requestAnimationFrame(function () { raf = 0; write(false); });
    clearTimeout(timer); timer = setTimeout(function () { write(true); }, 150);
  }
  write(true);
  if (stage) new MutationObserver(changed).observe(stage, {attributes: true, attributeFilter: ['data-zoom']});
  return {now: function () { return parseFloat(rowsEl.style.getPropertyValue('--lz')) || 1; }};
}

HD.feature('labelScale', {needs: ['rowsEl', 'warn'], mount: mount});
})();
