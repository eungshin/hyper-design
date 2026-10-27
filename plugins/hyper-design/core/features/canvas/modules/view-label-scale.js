/* View — 판 위 이름표를 화면에서 같은 크기로(R27 F01): #stage 의 data-zoom 이 바뀌면 #rows 에 CSS 변수 --lz(= 1/z, 규칙 HD.labelScale)를 쓴다.
   배율이 HD.labelScale.FAR 보다 작으면 #rows[data-lz-far] — 펼친 카드 설명(.cbody)을 visibility 로 숨긴다(크기는 그대로라 줄 사이 계산은 배율과 상관없음).
   확대 중엔 한 프레임에 한 번 3% 넘게 바뀔 때만, 멈춘 뒤 150ms 에 정확한 값 — 그때 document 'hd-label-scale' {lz} 를 보낸다(선 태그 겹침 다시 재기 등).
   이름표 CSS 는 각 주인(shell.css 의 R27 F01 블록 · view-busy · view-rows)이 calc(… * var(--lz,1)) 또는 scale: var(--lz,1) 로 쓴다 — 여기는 값만.
   메모 배지(.nbadge)는 .phone 안에서 카드 제목 줄(카드 바로 아래 자식)로 옮긴다 — 자리 CSS 는 shell.css R27 F01 블록.
   가진 상태: 마지막으로 쓴 값(DOM 의 --lz) · 저장 없음. HD.feature('labelScale', {needs: ['rowsEl', 'warn'], mount(ctx) → {now() → 지금 --lz 수}}) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var L = HD.labelScale, rowsEl = ctx.rowsEl, stage = rowsEl.parentNode, raf = 0, timer = 0, warned = false;
  function zoom() {                                   // data-zoom(셸 apply) — 첫 apply 전이면 transform 의 scale(…) 을 읽는다
    if (!stage) return null;
    if (stage.dataset && stage.dataset.zoom) return stage.dataset.zoom;
    var m = /scale\(([-\d.e]+)\)/.exec(stage.style.transform || '');
    return m ? m[1] : '1';
  }
  function write(exact) {
    var v = L.inv(zoom());
    if (v == null) {
      if (!warned) { warned = true; ctx.warn('[hd] 판 배율(data-zoom)을 읽지 못해 이름표를 1배로 둬요: ' + zoom()); }
      v = 1;
    }
    var old = rowsEl.style.getPropertyValue('--lz');
    if (L.put(old, v, exact)) rowsEl.style.setProperty('--lz', L.fmt(v));
    var far = L.far(1 / v);
    if (far !== rowsEl.hasAttribute('data-lz-far')) rowsEl.toggleAttribute('data-lz-far', far);   // 작게 볼 때 펼친 설명 숨김(shell.css R27 F01)
    if (exact) document.dispatchEvent(new CustomEvent('hd-label-scale', {detail: {lz: v}}));
  }
  var last = zoom();
  function changed() {
    var z = zoom(); if (z === last) return;
    last = z;
    if (!raf) raf = requestAnimationFrame(function () { raf = 0; write(false); });
    clearTimeout(timer); timer = setTimeout(function () { write(true); }, 150);
  }
  // 메모 배지는 화면 밖 제목 줄로(R27, main 결정): view-notes 가 .phone 안에 만든 .nbadge 를 카드 바로 아래(화면 다음)로 옮긴다 — .phone 은 overflow:hidden 이라
  // 밖에 그릴 수 없다. view-notes 는 카드 안에서 .nbadge 를 찾아 고치고 지우므로(옮긴 뒤에도 같은 요소) 주인은 그대로 view-notes.
  function hoist(root) {
    Array.prototype.forEach.call((root || rowsEl).querySelectorAll('.card > .phone > .nbadge'), function (b) {
      var ph = b.parentNode, card = ph.parentNode; card.insertBefore(b, ph.nextSibling);
    });
  }
  hoist();
  new MutationObserver(function (ms) {
    for (var i = 0; i < ms.length; i++) for (var j = 0; j < ms[i].addedNodes.length; j++) {
      var n = ms[i].addedNodes[j];
      if (n.nodeType === 1 && (n.classList.contains('nbadge') || n.querySelector('.phone > .nbadge'))) { hoist(); return; }
    }
  }).observe(rowsEl, {childList: true, subtree: true});
  write(true);
  if (stage) new MutationObserver(changed).observe(stage, {attributes: true, attributeFilter: ['data-zoom']});
  return {now: function () { return parseFloat(rowsEl.style.getPropertyValue('--lz')) || 1; }};
}

HD.feature('labelScale', {needs: ['rowsEl', 'warn'], mount: mount});
})();
