/* View — 끄는 동안 판 가장자리에 대면 판을 그쪽으로 밀어 준다(트리거를 먼 줄의 카드까지 끌고 가게, E6).
   가장자리 안쪽 edge px 에 들어오면 깊이만큼 빨라지고(판 밖으로 나가도 최대 속도), 가운데로 돌아오면 멈춘다.
   HD.viewEdgePan.mount(ctx) → {track(x, y), stop()}
   ctx = {pane, pan(dx, dy, x, y) — 판을 dx·dy(px) 옮기고 끄는 선을 다시 그린다, edge? (기본 48), speed? (한 프레임 최대 px, 기본 18)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

// 한 축: 포인터 v 가 [lo, hi] 의 가장자리에 들어오면 판을 그 반대쪽으로 옮길 양(+ = 판을 오른쪽·아래로 → 왼쪽·위 내용이 보임)
function step(lo, hi, v, edge, speed) {
  if (v < lo + edge) return Math.round(speed * Math.min(1, (lo + edge - v) / edge));
  if (v > hi - edge) return -Math.round(speed * Math.min(1, (v - hi + edge) / edge));
  return 0;
}

function mount(ctx) {
  var edge = ctx.edge || 48, speed = ctx.speed || 18, at = null, raf = 0;
  function tick() {
    raf = 0; if (!at) return;
    var r = ctx.pane.getBoundingClientRect(), dx = step(r.left, r.right, at.x, edge, speed), dy = step(r.top, r.bottom, at.y, edge, speed);
    if (!dx && !dy) return;
    ctx.pan(dx, dy, at.x, at.y);
    raf = requestAnimationFrame(tick);
  }
  function track(x, y) { at = {x: x, y: y}; if (!raf) raf = requestAnimationFrame(tick); }
  function stop() { at = null; if (raf) cancelAnimationFrame(raf); raf = 0; }
  return {track: track, stop: stop};
}

HD.viewEdgePan = {mount: mount, step: step};
})();
