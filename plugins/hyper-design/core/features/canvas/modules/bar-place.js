/* Model — 요소 막대(#elbar) 자리 규칙(t51-7a, Figma 떠 있는 고르기 단추): 고른 요소·꼬리표 바깥 바로 위 → 아래 → 조금 더 위·아래(위·아래가 막히면 옆), 둘레 내용을 덮지 않는 첫 자리. DOM·저장소·메시지를 쓰지 않는다.
   HD.barPlace = {GAP, place(o) → {x, y, side: 'above'|'below'|'right'|'left'|'over', cover}}
   o = {anchor: 고른 요소 사각형, label?: 그 꼬리표 사각형|null, size: {w, h} 막대 크기, view: {x, y, w, h} 보이는 칸(창·판 칸),
        bars?: [떠 있는 다른 막대 사각형](#selbar·창 제목 막대·도구 막대 — 절대 덮지 않음), content?: [둘레 내용 사각형](형제 요소·글·그림 — 무르게)} — 모두 화면 좌표
   규칙: 고른 요소와 꼬리표(합친 상자)는 절대 덮지 않는다 · 보이는 칸 안 · 다른 막대를 덮지 않는다.
     차례 = 위(왼쪽 맞춤 → 오른쪽 맞춤 — 왼쪽 맞춤이 칸을 넘으면 오른쪽 맞춤 먼저, 간격 GAP → 좁게 TIGHT) → 아래(같은 차례) → 위로 비켜 올림 → 아래로 비켜 내림(둘 다 막대 높이 + 2·GAP 까지).
     내용을 덮지 않는 첫 자리 — 모두 덮으면 덮는 넓이가 가장 작은 자리(같으면 차례). 위·아래 어디에도 놓을 수 없을 때만(보이는 칸·다른 막대) 오른쪽 옆 → 왼쪽 옆
     (옆은 형제 밖 — 화면 글을 못 읽는 판에서는 보이지 않는 내용을 덮기 쉽다). 그것도 없으면 'over'(보이는 칸 맨 위, 요소를 덮을 수 있음).
     내용 중 고른 요소 안의 것과 고른 요소를 감싼 것(조상·배경)은 셈하지 않는다. 깨진 사각형은 건너뛴다. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var GAP = 6, TIGHT = 2, PAD = 3, M = 8;                // PAD = 내용과 막대 사이에 남길 틈(막대 그림자가 글에 닿지 않게)

function box(r) { return !!r && isFinite(r.x) && isFinite(r.y) && isFinite(r.w) && isFinite(r.h) && r.w > 0 && r.h > 0; }
function hits(a, b, pad) {
  var p = pad || 0;
  return a.x - p < b.x + b.w && a.x + a.w + p > b.x && a.y - p < b.y + b.h && a.y + a.h + p > b.y;
}
function area(a, b) {
  var w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}
function union(a, b) {
  if (!box(b)) return a;
  var x = Math.min(a.x, b.x), y = Math.min(a.y, b.y);
  return {x: x, y: y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.y + a.h, b.y + b.h) - y};
}
function within(o, k, e) { return o.x >= k.x - e && o.y >= k.y - e && o.x + o.w <= k.x + k.w + e && o.y + o.h <= k.y + k.h + e; }

function place(o) {
  o = o || {};
  var a = o.anchor, size = o.size || {w: 0, h: 0}, v = o.view || {x: 0, y: 0, w: 0, h: 0};
  var vx = v.x || 0, vy = v.y || 0, vr = vx + v.w, vb = vy + v.h, w = size.w, h = size.h;
  if (!box(a)) return {x: vx + M, y: vy + M, side: 'over', cover: 0};
  var keep = union(a, o.label);                       // 고른 요소 + 꼬리표 = 절대 덮지 않을 상자
  var bars = (Array.isArray(o.bars) ? o.bars : [o.bars]).filter(box);
  var content = (Array.isArray(o.content) ? o.content : []).filter(function (c) {
    return box(c) && !within(c, keep, 1) && !within(keep, c, 1);   // 안의 글 · 감싼 상자(조상·배경)는 셈하지 않음
  });
  var clampX = function (x) { return Math.max(vx + M, Math.min(vr - w - M, x)); };
  var rect = function (x, y) { return {x: x, y: y, w: w, h: h}; };
  var ok = function (x, y) {
    var r = rect(x, y);
    return x >= vx + M - 0.5 && x + w <= vr - M + 0.5 && y >= vy + M - 0.5 && y + h <= vb - M + 0.5 &&
      !hits(r, keep) && !bars.some(function (b) { return hits(r, b); });
  };
  var near = function (x, y) { var r = rect(x, y); return content.filter(function (c) { return hits(r, c, PAD); }); };
  var cover = function (x, y) { var r = rect(x, y); return content.reduce(function (s, c) { return s + area(r, c); }, 0); };
  var xl = clampX(keep.x), xr = clampX(keep.x + keep.w - w), xs = xl === xr ? [xl] : keep.x + w > vr - M ? [xr, xl] : [xl, xr];   // 왼쪽 맞춤이 칸을 넘으면 오른쪽 맞춤 먼저
  var top = keep.y - GAP - h, bot = keep.y + keep.h + GAP, reach = h + 2 * GAP;
  var cs = [];
  var add = function (x, y, side) {
    if (ok(x, y) && !cs.some(function (c) { return c.x === x && c.y === y; })) cs.push({x: x, y: y, side: side});
  };
  var slide = function (x, dir) {                      // 내용을 비켜 위(-1)·아래(+1)로 — reach 안에서만
    var y = dir < 0 ? top : bot;
    for (var i = 0; i < 6; i++) {
      var ns = near(x, y);
      if (!ns.length) return y;
      y = dir < 0 ? Math.min.apply(null, ns.map(function (c) { return c.y; })) - GAP - h
                  : Math.max.apply(null, ns.map(function (c) { return c.y + c.h; })) + GAP;
      if (Math.abs(y - (dir < 0 ? top : bot)) > reach || !ok(x, y)) return null;
    }
    return null;
  };
  xs.forEach(function (x) { add(x, top, 'above'); add(x, keep.y - TIGHT - h, 'above'); });
  xs.forEach(function (x) { add(x, bot, 'below'); add(x, keep.y + keep.h + TIGHT, 'below'); });
  xs.forEach(function (x) { var y = slide(x, -1); if (y !== null) add(x, y, 'above'); });
  xs.forEach(function (x) { var y = slide(x, 1); if (y !== null) add(x, y, 'below'); });
  if (!cs.length) {                                   // 위·아래 자리가 없음(보이는 칸·다른 막대) — 옆
    var sy = Math.max(vy + M, Math.min(vb - h - M, keep.y));
    add(keep.x + keep.w + GAP, sy, 'right');
    add(keep.x - w - GAP, sy, 'left');
  }
  for (var i = 0; i < cs.length; i++) if (!near(cs[i].x, cs[i].y).length) return {x: cs[i].x, y: cs[i].y, side: cs[i].side, cover: 0};
  var best = null, bs = Infinity;
  cs.forEach(function (c) { var s = cover(c.x, c.y); if (s < bs) { best = c; bs = s; } });
  if (best) return {x: best.x, y: best.y, side: best.side, cover: bs};
  return {x: xl, y: vy + M, side: 'over', cover: cover(xl, vy + M)};
}

HD.barPlace = {GAP: GAP, place: place};
})();
