/* View — 눈앞 내용 제자리: 판 위 덩어리(소개 글·DS 카드·줄·꼬리말)의 판 좌표를 재 두었다가 높이가 바뀌면 세로 이동만 보정(규칙 HD.cameraAnchor, U2 F1a).
   HD.viewCameraAnchor.mount(ctx) → {keep()}
   ctx = {stage, rowsEl, pane, getView() → {z, tx, ty}, setView(z, tx, ty), busy() → 끄는 중이면 true}
   상태 = 지난 배치 하나(prev). #stage 크기가 바뀌면(ResizeObserver) 스스로 keep — 셸은 같은 프레임에 배치를 또 바꾼 뒤(줄 사이 다시 재기 등) keep() 을 부른다.
   첫 카메라(셸 home)는 한 번만 — 그 뒤로 사용자가 판을 안 움직였어도 내용 높이 변화로 카메라를 다시 맞추지 않는다. 끄는 중에는 보정하지 않고 배치만 새로 잰다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var A = HD.cameraAnchor, stage = ctx.stage, rowsEl = ctx.rowsEl, ids = new WeakMap(), seq = 0, prev = null;
  function id(el) { if (!ids.has(el)) ids.set(el, ++seq); return ids.get(el); }
  function inFlow(el) { return el.offsetParent !== null && getComputedStyle(el).position !== 'absolute'; }
  function items() {                                 // 판 좌표 [{id, y, h}] — 줄 묶음(#rows) 대신 그 안의 줄들
    var sr = stage.getBoundingClientRect(), k = stage.offsetHeight ? sr.height / stage.offsetHeight : 1, els = [];
    if (!(k > 0)) k = 1;
    Array.prototype.forEach.call(stage.children, function (el) {
      if (el === rowsEl) Array.prototype.forEach.call(rowsEl.children, function (r) { els.push(r); });
      else els.push(el);
    });
    return els.filter(inFlow).map(function (el) {
      var r = el.getBoundingClientRect();
      return {id: id(el), y: (r.top - sr.top) / k, h: r.height / k};
    });
  }
  function keep() {
    var next = items();
    if (prev && !ctx.busy()) {
      var v = ctx.getView(), ty = A.keep(prev, next, {h: ctx.pane.clientHeight, z: v.z, ty: v.ty});
      if (ty !== v.ty) ctx.setView(v.z, v.tx, ty);
    }
    prev = next;
  }
  prev = items();
  if (window.ResizeObserver) new ResizeObserver(function () { keep(); }).observe(stage);
  return {keep: keep};
}

HD.viewCameraAnchor = {mount: mount};
})();
