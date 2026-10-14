/* Model — 색 링크 칩 자리(순수 기하). TODO(phase 1): 선 위 태그·옆면 출발 자리도 여기로. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

// 칩 하나의 자리: 카드 오른쪽 테두리에 걸쳐(반은 밖, 반은 안) 요소 높이에. 이미 놓인 칩(placed)과 안 겹치게 4px 띄워 쌓는다.
// S = 출발 카드 {x,y,w,h,sc}, r = 요소 rect(화면 좌표), sz = 칩 크기 {w,h}. placed 는 읽기만 한다.
function placeChip(S, r, sz, placed) {
  var sc = S.sc || 1;
  var ey = S.y + r.y * sc, eh = r.h * sc, bot = S.y + S.h;
  var cy = Math.max(S.y + 4 + sz.h / 2, Math.min(bot - 4 - sz.h / 2, ey + eh / 2));
  var c = {x: S.x + S.w - sz.w / 2, y: cy - sz.h / 2, w: sz.w, h: sz.h};
  for (var guard = 0; guard < 60; guard++) {
    var hit = (placed || []).filter(function (q) { return c.x < q.x + q.w && q.x < c.x + c.w && c.y < q.y + q.h + 4 && q.y < c.y + c.h + 4; })[0];
    if (!hit) break;
    c.y = hit.y + hit.h + 4;
  }
  return c;
}

HD.labels = {placeChip: placeChip};
})();
