/* Model — 눈앞 내용 제자리: 내용 높이가 바뀌면 카메라를 다시 맞추지 않고 보이던 맨 위 덩어리의 화면 위치를 지키는 세로 이동(순수, U2 F1a).
   덩어리 = [{id, y, h}] 판 좌표(소개 글·DS 카드·줄 …, 차례 = 위에서 아래). view = {h, z, ty}(판 칸 높이 px · 배율 · 세로 이동).
   pick(items, view) → id | null   판 칸에 가장 많이 보이는 덩어리(눈앞 내용) — 1px 안으로 같으면 위의 것. 판 가장자리에 조금 걸친 것(DS 카드 끝 20px 등)은
                                   기준이 되지 않는다(그것이 줄면 눈앞 줄이 밀렸다). 숫자가 아닌 칸은 건너뜀
   keep(prev, next, view) → ty     바뀌기 전 배치(prev)에서 고른 기준이 next 에서 dy 만큼 움직였으면 ty - dy·z(화면 위치 그대로).
                                   기준이 next 에 없으면 prev 에서 그다음으로 많이 보이던 것. 보이는 게 없거나 움직임이 0.01px 아래면 ty 그대로(같은 값)
   브라우저 스크롤 고정(overflow-anchor)과 같은 뜻(기준 고르기만 '가장 많이 보이는 것') — 기준 아래쪽 변화는 카메라를 움직이지 않는다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function num(v) { return typeof v === 'number' && isFinite(v); }
function ok(it) { return !!it && it.id != null && num(it.y) && num(it.h); }
function shown(it, v) { var top = it.y * v.z + v.ty; return Math.min(v.h, top + it.h * v.z) - Math.max(0, top); }   // 판 칸 안에 보이는 높이(px)
function visible(items, v) {                       // 보이는 것, 많이 보이는 차례(1px 안 = 위의 것 먼저)
  return (items || []).filter(ok).map(function (it) { return {it: it, s: shown(it, v)}; })
    .filter(function (e) { return e.s > 0; })
    .sort(function (a, b) { return Math.abs(a.s - b.s) > 1 ? b.s - a.s : a.it.y - b.it.y; })
    .map(function (e) { return e.it; });
}

function pick(items, view) {
  var vis = visible(items, view);
  return vis.length ? vis[0].id : null;
}

function keep(prev, next, view) {
  var ty = view.ty, at = {};
  (next || []).forEach(function (it) { if (ok(it) && !(it.id in at)) at[it.id] = it; });
  var vis = visible(prev, view);
  for (var i = 0; i < vis.length; i++) {
    var n = at[vis[i].id]; if (!n) continue;
    var d = (n.y - vis[i].y) * view.z;
    return Math.abs(d) < 0.01 ? ty : ty - d;
  }
  return ty;
}

HD.cameraAnchor = {pick: pick, keep: keep};
})();
