/* Model — 선 태그 규칙(R46): 선 하나(방향 하나)에 태그 하나 — 글(트리거 여럿이면 "첫 버튼 글 외 N")과 자리(그 선이 카드를 떠나는 점에서 시작해 제 선을 따라 비킴). DOM 을 쓰지 않는다.
   text(o) → {text, more, named}   o = {texts: 버튼 글(중복 없음, 처음 나온 차례), n: 트리거 수(같은 글 버튼도 하나씩), name: 붙인 이름, pend: 반영 대기로만 있는 선}
     이름이 있으면 이름 · 트리거 하나(또는 글만 하나·수 모름)면 그 글 · 둘 이상이면 "<첫 글> 외 <n-1>" · 글이 없으면 반영 대기 = '반영 대기', 아니면 ''.
     more = 태그에 다 못 보인 트리거 수(n-1, 0 이상) — 0 보다 크거나 이름이 있으면 View 가 올렸을 때 목록 창을 연다
   anchor(r, end) → [x, y] | null   길(HD.route 결과 {pts}) 의 그 태그 쪽 끝 점(end 0 = 첫 점 = 출발 카드, 1 = 끝 점 = 양방향의 다른 쪽 출발)
   from(r, end) → 점 목록(태그 쪽 끝에서 바깥으로) | null
   walk(pts, d) → {x, y, dir: 'h'|'v'}   꺾은선 위 d 만큼 간 점(0..길이로 자름)과 그 마디 방향
   seat(items, o) → [{x, y, d, free, side} | null]   보이는 태그 자리(화면 px, 태그 가운데) — items = [{pts(화면 px, 태그 쪽 끝에서 바깥으로), w, h}] 차례대로.
     태그는 제 선에 붙는다: 선 옆, 가장자리가 선에 닿게(가로 마디는 아래, 세로 마디는 오른쪽 — 선을 가리지 않음). 시작 = 카드 가장자리에서 태그 반 칸 + 2px(제 카드를 덮지 않게).
     앞서 놓인 태그와 겹치면(틈 gap) 제 선을 따라 step 씩 바깥으로 — 다른 선으로 건너가지도, 목록처럼 쌓이지도 않는다.
     그 쪽에 빈 자리가 없으면 같은 길이를 다시 반대 옆(side 1)으로, 그다음 선 위 가운데(side 2)로 — 짧은 양방향 선의 두 태그가 위·아래로 갈린다.
     한도 = min(o.max, 선 길이 × o.share)(짧은 선도 시작 자리 한 칸은): 그 안에 빈 자리가 없으면 시작 자리 그대로(겹침, free:false). 깨진 항목은 null(View 가 그 태그는 기본 자리)
     o.avoid = [{l, t, r, b}] 비킬 화면 px 상자(떠 있는 카드 막대 등 — 늘 피한다: 빈 자리가 없을 때도 막대만 피한 첫 자리, 깨진 상자는 건너뜀)
   HD.lineTags = {MORE, GAP, STEP, MAX, SHARE, text, anchor, from, walk, seat} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MORE = '외', GAP = 3, STEP = 4, MAX = 240, SHARE = 0.45;

function clean(t) { return String(t == null ? '' : t).replace(/\s+/g, ' ').trim(); }
function text(o) {
  o = o || {};
  var texts = (Array.isArray(o.texts) ? o.texts : []).map(clean).filter(Boolean), name = clean(o.name);
  var n = typeof o.n === 'number' && isFinite(o.n) ? Math.max(0, Math.floor(o.n)) : texts.length;
  n = Math.max(n, texts.length);
  var more = Math.max(0, n - 1);
  if (name) return {text: name, more: more, named: true};
  if (!texts.length) return {text: o.pend ? '반영 대기' : '', more: more, named: false};
  return {text: more ? texts[0] + ' ' + MORE + ' ' + more : texts[0], more: more, named: false};
}

function num(v) { return typeof v === 'number' && isFinite(v); }
function okPts(p) { return Array.isArray(p) && p.length >= 2 && p.every(function (q) { return Array.isArray(q) && num(q[0]) && num(q[1]); }); }
function from(r, end) {
  if (!r || !okPts(r.pts)) return null;
  var p = r.pts.map(function (q) { return [q[0], q[1]]; });
  return end ? p.reverse() : p;
}
function anchor(r, end) { var p = from(r, end); return p ? p[0] : null; }

function walk(pts, d) {
  var left = Math.max(0, d), last = null;
  for (var i = 1; i < pts.length; i++) {
    var a = pts[i - 1], b = pts[i], L = Math.abs(b[0] - a[0]) + Math.abs(b[1] - a[1]);
    if (L <= 0) continue;
    last = [a, b, L];
    if (left <= L) { var t = left / L; return {x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, dir: a[1] === b[1] ? 'h' : 'v'}; }
    left -= L;
  }
  if (!last) return {x: pts[0][0], y: pts[0][1], dir: 'h'};
  return {x: last[1][0], y: last[1][1], dir: last[0][1] === last[1][1] ? 'h' : 'v'};
}
function length(pts) {
  var L = 0;
  for (var i = 1; i < pts.length; i++) L += Math.abs(pts[i][0] - pts[i - 1][0]) + Math.abs(pts[i][1] - pts[i - 1][1]);
  return L;
}
function rectAt(p, w, h) { return {l: p.x - w / 2, t: p.y - h / 2, r: p.x + w / 2, b: p.y + h / 2}; }
function hit(a, b, g) { return a.l < b.r + g && a.r + g > b.l && a.t < b.b + g && a.b + g > b.t; }

function seat(items, o) {
  o = o || {};
  var g = num(o.gap) && o.gap >= 0 ? o.gap : GAP, step = num(o.step) && o.step > 0 ? o.step : STEP;
  var max = num(o.max) && o.max >= 0 ? o.max : MAX, share = num(o.share) && o.share > 0 ? o.share : SHARE;
  var bars = (Array.isArray(o.avoid) ? o.avoid : []).filter(function (q) { return q && num(q.l) && num(q.t) && num(q.r) && num(q.b) && q.r >= q.l && q.b >= q.t; });
  var placed = [];
  function clear(r, list) { return !list.some(function (q) { return hit(r, q, g); }); }
  return (Array.isArray(items) ? items : []).map(function (it) {
    if (!it || !okPts(it.pts) || !num(it.w) || !num(it.h) || it.w < 0 || it.h < 0) return null;
    var first = walk(it.pts, 0), d0 = (first.dir === 'v' ? it.h : it.w) / 2 + 2;
    var lim = Math.max(d0, Math.min(max, length(it.pts) * share)), pick = null, soft = null;
    function off(p, pass) {                           // 0 = 선 옆(가로 마디 아래 · 세로 마디 오른쪽) · 1 = 반대 옆 · 2 = 선 위 가운데 — 가장자리·가운데가 늘 선에 닿는다
      var s = pass === 2 ? 0 : pass === 1 ? -1 : 1;
      return p.dir === 'h' ? [0, s * (it.h / 2 + 2)] : [s * (it.w / 2 + 2), 0];   // 선에서 2px — 반대 옆 태그와 틈(gap 3)을 지킨다
    }
    for (var pass = 0; pass < 3 && !pick; pass++) {
      for (var d = d0; d <= lim + 1e-6 && !pick; d += step) {
        var p = walk(it.pts, d), o2 = off(p, pass), c = {x: p.x + o2[0], y: p.y + o2[1]}, r = rectAt(c, it.w, it.h);
        if (!clear(r, bars)) continue;                // 떠 있는 막대 밑은 늘 피한다
        if (!soft && !pass) soft = {x: c.x, y: c.y, d: d, free: false, r: r};
        if (clear(r, placed)) pick = {x: c.x, y: c.y, d: d, free: true, side: pass, r: r};
      }
    }
    // 한도 안에 빈 자리가 없으면: 막대만 피한 첫 자리(다른 태그와는 겹침) → 그것도 없으면 시작 자리
    if (!pick) pick = soft || (function () { var s = walk(it.pts, d0), o2 = off(s, 0), c = {x: s.x + o2[0], y: s.y + o2[1]}; return {x: c.x, y: c.y, d: d0, free: false, r: rectAt(c, it.w, it.h)}; })();
    placed.push(pick.r);
    return {x: pick.x, y: pick.y, d: pick.d, free: pick.free, side: pick.side || 0};
  });
}

HD.lineTags = {MORE: MORE, GAP: GAP, STEP: STEP, MAX: MAX, SHARE: SHARE, text: text, anchor: anchor, from: from, walk: walk, seat: seat};
})();
