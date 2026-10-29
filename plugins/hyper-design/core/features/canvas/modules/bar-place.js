/* Model — 요소 막대(#elbar) 자리 규칙(t51-7a, Figma 떠 있는 고르기 단추): 고른 요소·꼬리표 바깥 바로 위 → 아래 → 조금 더 위·아래(위·아래가 막히면 옆), 둘레 내용을 덮지 않는 첫 자리. DOM·저장소·메시지를 쓰지 않는다.
   HD.barPlace = {GAP, FAR, place(o) → {x, y, side: 'above'|'below'|'right'|'left'|'over', cover, near?}}
   o = {anchor: 고른 요소 사각형, label?: 그 꼬리표 사각형|null, size: {w, h} 막대 크기, view: {x, y, w, h} 보이는 칸(창·판 칸),
        bars?: [떠 있는 다른 막대 사각형](#selbar·창 제목 막대·도구 막대 — 절대 덮지 않음), content?: [둘레 내용 사각형](형제 요소·글·그림 — 무르게)} — 모두 화면 좌표
   규칙: 고른 요소와 꼬리표(합친 상자)는 절대 덮지 않는다 · 보이는 칸 안 · 다른 막대를 덮지 않는다.
     차례 = 위(왼쪽 맞춤 → 오른쪽 맞춤 — 왼쪽 맞춤이 칸을 넘으면 오른쪽 맞춤 먼저, 간격 GAP → 좁게 TIGHT) → 아래(같은 차례) → 위로 비켜 올림 → 아래로 비켜 내림(둘 다 막대 높이 + 2·GAP 까지).
     내용을 덮지 않는 첫 자리 — 모두 덮으면 덮는 넓이가 가장 작은 자리(같으면 차례). 위·아래 어디에도 놓을 수 없을 때만(보이는 칸·다른 막대) 오른쪽 옆 → 왼쪽 옆
     (옆은 형제 밖 — 화면 글을 못 읽는 판에서는 보이지 않는 내용을 덮기 쉽다). 그것도 없으면 'over'(보이는 칸 맨 위, 요소를 덮을 수 있음).
     내용 중 고른 요소 안의 것과 고른 요소를 감싼 것(조상·배경)은 셈하지 않는다. 깨진 사각형은 건너뛴다.
   누른 자리 가까이(R51): o.pointer = {x, y} 요소를 누른 자리(화면 좌표, 클릭으로 고를 때만 — 키보드 고르기·상위는 없음).
     큰 요소(높이 > min(FAR, BIG·보이는 칸 높이))이고 위 규칙의 자리가 누른 자리에서 FAR 보다 멀면 → 누른 자리 바로 위(UP) → 바로 아래(DOWN, 커서 몸통을 비킴),
     가운데 = 누른 x(보이는 칸 안으로 당김). 이때만 고른 요소 몸은 덮을 수 있다(큰 요소 밖은 멀다) — 꼬리표·다른 막대·보이는 칸은 그대로 지킨다.
     둘 다 안 되거나 누른 자리가 보이는 칸 밖이면 위 규칙 그대로. 결과에 near: true. 작은 요소·pointer 없음 = 위 규칙 그대로(바뀌지 않음).
   HD.barPlace.card(o) → {hidden, cx, y} — 카드 선택 막대(#selbar, R27 F07): 판 칸(#screens) 밖으로 나가 옆 패널(대화 도크)을 덮지 않는다.
     o = {cards: 고른 카드들을 합친 사각형, size: {w, h} 막대, view: 판 칸 사각형, lift: 카드 위 띄움} — 화면 좌표.
     카드가 판 칸에 하나도 안 보이면 숨김. 가운데 = 카드의 보이는 부분 가운데, 막대가 판 칸 안(여백 M)에 들도록 당긴다.
     위 = 카드 위 lift 만큼, 판 칸 위를 넘으면 판 칸 맨 위. o.bars(판 위 떠 있는 도구 막대 등)와 겹치면 그 오른쪽 → 왼쪽으로 비킨다(판 칸 안일 때만). 깨진 사각형 → 숨김. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var GAP = 6, TIGHT = 2, PAD = 3, M = 8;                // PAD = 내용과 막대 사이에 남길 틈(막대 그림자가 글에 닿지 않게)
// 누른 자리 가까이(R51) — FAR 160px ≈ 막대(26px) 여섯 개 높이: 누른 자리를 보는 눈이 막대를 한눈에 찾는 거리(이보다 멀면 '막대가 어디 갔지').
//   요소가 FAR 보다 낮으면 누른 자리에서 요소 위 끝까지가 FAR 안 — 위 규칙이 이미 가깝다. 짧은 보이는 칸(크게 보기 창 400px 등)에서는 FAR 가 칸의 대부분이라 BIG(40%)로 줄인다.
//   UP 12px = 막대 아래 끝과 커서 끝 사이 틈 · DOWN 24px = 화살표 커서 몸통(약 20px)이 막대를 가리지 않게.
var FAR = 160, BIG = 0.4, UP = 12, DOWN = 24;

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
  var r = edge(o), pt = o.pointer, a = o.anchor, size = o.size || {w: 0, h: 0}, v = o.view || {x: 0, y: 0, w: 0, h: 0};
  if (!pt || !isFinite(pt.x) || !isFinite(pt.y) || !box(a) || !box(v)) return r;
  if (a.h <= Math.min(FAR, BIG * v.h)) return r;                          // 작은 요소 = 위 규칙 그대로
  if (pt.x < v.x || pt.x > v.x + v.w || pt.y < v.y || pt.y > v.y + v.h) return r;   // 누른 자리가 보이는 칸 밖(판을 옮김)
  var w = size.w, h = size.h;
  var dx = Math.max(r.x - pt.x, 0, pt.x - (r.x + w)), dy = Math.max(r.y - pt.y, 0, pt.y - (r.y + h));
  if (Math.sqrt(dx * dx + dy * dy) <= FAR) return r;                     // 위 규칙의 자리가 이미 가깝다(요소 위 끝 가까이 누름)
  var bars = (Array.isArray(o.bars) ? o.bars : [o.bars]).filter(box), label = box(o.label) ? o.label : null;
  var x = Math.max(v.x + M, Math.min(v.x + v.w - w - M, pt.x - w / 2));
  var fits = function (y) {
    var q = {x: x, y: y, w: w, h: h};
    return y >= v.y + M - 0.5 && y + h <= v.y + v.h - M + 0.5 && !(label && hits(q, label)) && !bars.some(function (b) { return hits(q, b); });
  };
  var ys = [[pt.y - UP - h, 'above'], [pt.y + DOWN, 'below']];
  for (var i = 0; i < ys.length; i++) if (fits(ys[i][0])) return {x: x, y: ys[i][0], side: ys[i][1], cover: 0, near: true};
  return r;
}

function edge(o) {
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

function card(o) {
  o = o || {};
  var c = o.cards, v = o.view, size = o.size || {w: 0, h: 0}, w = size.w || 0, h = size.h || 0, lift = o.lift || 0;
  if (!box(c) || !box(v)) return {hidden: true, cx: 0, y: 0};
  var l = Math.max(c.x, v.x), r = Math.min(c.x + c.w, v.x + v.w), t = Math.max(c.y, v.y), b = Math.min(c.y + c.h, v.y + v.h);
  if (r <= l || b <= t) return {hidden: true, cx: 0, y: 0};          // 카드가 판 칸 밖 — 막대도 숨김
  var lo = v.x + M + w / 2, hi = v.x + v.w - M - w / 2, cx = (l + r) / 2;
  cx = lo > hi ? v.x + v.w / 2 : Math.max(lo, Math.min(hi, cx));
  var y = Math.max(v.y + M, c.y - h - lift);
  (Array.isArray(o.bars) ? o.bars : []).filter(box).forEach(function (b) {
    if (!hits({x: cx - w / 2, y: y, w: w, h: h}, b)) return;
    var right = b.x + b.w + GAP + w / 2, left = b.x - GAP - w / 2;
    if (right <= hi) cx = right; else if (left >= lo) cx = left;
  });
  return {hidden: false, cx: cx, y: y};
}

HD.barPlace = {GAP: GAP, FAR: FAR, place: place, card: card};
})();
