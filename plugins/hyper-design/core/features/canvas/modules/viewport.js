/* Model — 판 카메라 계산과 창 나누기 상태(조각 6, H2·H3). DOM 을 쓰지 않는다.
   카메라 cam = {z, tx, ty}(판 좌표 → 화면: x*z + tx).
   zoomAt(cam, px, py, nz) → 새 cam: 화면 점 (px, py) 아래의 판 점은 그대로
   fit(ext, w, h, pad, clamp?) → 새 cam: 판 상자 ext = {x0, y0, x1, y1} 가 w×h 칸에 꽉 차게(가운데, 여백 pad · 배율은 clamp 를 거침)
   창 나누기 상태 = {split: 'one' | 'lr', sync: 동시 스크롤} — 저장하지 않는다(열 때마다 하나)
   reduce(state, a) → 새 상태: split{mode} · sync{on}
   HD.viewport = {SPLITS, zoomAt, fit, initial, reduce} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var SPLITS = ['one', 'lr'];

function zoomAt(cam, px, py, nz) {
  var bx = (px - cam.tx) / cam.z, by = (py - cam.ty) / cam.z;
  return {z: nz, tx: px - bx * nz, ty: py - by * nz};
}
function fit(ext, w, h, pad, clamp) {
  var p = pad == null ? 32 : pad, bw = ext.x1 - ext.x0, bh = ext.y1 - ext.y0;
  var z = Math.min((w - p) / bw, (h - p) / bh);
  if (clamp) z = clamp(z);
  return {z: z, tx: (w - bw * z) / 2 - ext.x0 * z, ty: (h - bh * z) / 2 - ext.y0 * z};
}
function initial() { return {split: 'one', sync: false}; }
function reduce(s, a) {
  if (!a) return s;
  if (a.type === 'split' && SPLITS.indexOf(a.mode) >= 0 && a.mode !== s.split) return {split: a.mode, sync: a.mode === 'one' ? false : s.sync};
  if (a.type === 'sync' && s.split !== 'one' && !!a.on !== s.sync) return {split: s.split, sync: !!a.on};
  return s;
}

HD.viewport = {SPLITS: SPLITS, zoomAt: zoomAt, fit: fit, initial: initial, reduce: reduce};
})();
