/* Model — 바뀐 곳 보기(48b): 옛 화면과 새 화면의 블록 차이 — 새 화면에서 잠깐 강조할 요소·떠오를 요소·빠진 요소를 고른다. DOM 을 모른다.
   나무 = {i: 번호, t: 태그, k: 짝 열쇠(태그 + #id·.첫 class·[data-region]), x: 제 글(자식 글 빼고, 공백 하나로), a: 속성 글(src·alt·value 등), c: [자식]} — View 가 DOM 에서 뽑는다.
   diff(옛 나무, 새 나무) → {changed: [새 i], added: [새 i], removed: [옛 i], many: bool}
     - 형제 줄은 통째로 같은 것(해시)끼리 먼저 잇고(LCS), 그 사이 틈은 같은 열쇠끼리 차례로 짝 지어 안쪽을 견준다 · 짝 없는 새 것 = added · 짝 없는 옛 것 = removed
     - 글(x)·속성(a)이 다르면 changed. 인라인(isInline: b·span 등)이면 그것을 담은 블록이 changed — 새로 생긴 인라인도 그 블록이 changed
     - 빠진 요소는 그 부모 블록이 changed · 뿌리(body)는 강조하지 않는다 · 강조한(changed·added) 요소의 안쪽은 빼고 바깥 것만
     - 남은 강조가 MAX 개를 넘으면 many = true 이고 changed·added 는 비운다(화면이 통째로 바뀜 — 강조가 잡음이 됨)
     깨진 나무(객체가 아님·c 가 배열이 아님) = 빈 결과(던지지 않음)
   HD.swapDiff = {MAX, diff, isInline} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MAX = 12, LCS_CAP = 40000;                         // 형제 줄 둘의 곱이 이보다 크면 LCS 없이 열쇠 차례 짝만(큰 표·긴 목록)
var INLINE = {};
'abbr b bdi bdo br cite code data dfn em font i kbd mark q s samp small span strong sub sup time u var wbr'.split(' ').forEach(function (t) { INLINE[t] = 1; });

function isInline(t) { return typeof t === 'string' && INLINE[t.toLowerCase()] === 1; }
function ok(n) { return !!n && typeof n === 'object' && typeof n.i === 'number'; }
function kids(n) { return Array.isArray(n.c) ? n.c.filter(ok) : []; }
function str(v) { return typeof v === 'string' ? v : ''; }

function diff(oldT, newT) {
  var res = {changed: [], added: [], removed: [], many: false};
  if (!ok(oldT) || !ok(newT)) return res;
  var memo = new Map(), parent = {}, marks = {}, root = newT.i;
  function hash(n) {                                   // 그 요소 + 안쪽 전부가 같은가
    if (memo.has(n)) return memo.get(n);
    var s = str(n.k) + '\u0001' + str(n.x) + '\u0001' + str(n.a) + '\u0002' + kids(n).map(hash).join('\u0003'), h = 5381;
    for (var j = 0; j < s.length; j++) h = ((h << 5) + h + s.charCodeAt(j)) | 0;
    memo.set(n, h + ':' + s.length);
    return memo.get(n);
  }
  (function up(n) { kids(n).forEach(function (k) { parent[k.i] = n.i; up(k); }); })(newT);
  function mark(n, kind) { if (n.i !== root && !marks[n.i]) marks[n.i] = kind; }
  function blockOf(n, blk) { return isInline(n.t) && blk ? blk : n; }
  function add(n, blk) { if (isInline(n.t)) mark(blk, 'changed'); else mark(n, 'added'); }
  function gone(o, blk) { res.removed.push(o.i); mark(blk, 'changed'); }

  function node(o, n, blk) {
    var b = blockOf(n, blk);
    if (str(o.x) !== str(n.x) || str(o.a) !== str(n.a)) mark(b, 'changed');
    line(kids(o), kids(n), b);
  }
  function gap(O, N, blk) {                            // 틈: 같은 열쇠끼리 차례로 짝
    var p = 0;
    N.forEach(function (n) {
      for (var q = p; q < O.length && str(O[q].k) !== str(n.k); q++);
      if (q >= O.length) { add(n, blk); return; }
      for (; p < q; p++) gone(O[p], blk);
      node(O[q], n, blk); p = q + 1;
    });
    for (; p < O.length; p++) gone(O[p], blk);
  }
  function line(O, N, blk) {
    if (!O.length && !N.length) return;
    var pairs = [];
    if (O.length * N.length <= LCS_CAP) {              // 통째로 같은 형제끼리 LCS
      var ho = O.map(hash), hn = N.map(hash), m = O.length, w = N.length, L = [], a, b;
      for (a = 0; a <= m; a++) { L.push(new Array(w + 1).fill(0)); }
      for (a = m - 1; a >= 0; a--) for (b = w - 1; b >= 0; b--) L[a][b] = ho[a] === hn[b] ? L[a + 1][b + 1] + 1 : Math.max(L[a + 1][b], L[a][b + 1]);
      for (a = 0, b = 0; a < m && b < w;) {
        if (ho[a] === hn[b]) { pairs.push([a, b]); a++; b++; } else if (L[a + 1][b] >= L[a][b + 1]) a++; else b++;
      }
    }
    var pa = 0, pb = 0;
    pairs.concat([[O.length, N.length]]).forEach(function (pr) {
      gap(O.slice(pa, pr[0]), N.slice(pb, pr[1]), blk);
      pa = pr[0] + 1; pb = pr[1] + 1;
    });
  }
  node(oldT, newT, null);

  var keep = Object.keys(marks).map(Number).filter(function (i) {   // 강조한 요소 안쪽은 빼기
    for (var p = parent[i]; p !== undefined; p = parent[p]) if (marks[p]) return false;
    return true;
  }).sort(function (x, y) { return x - y; });
  if (keep.length > MAX) { res.many = true; return res; }
  keep.forEach(function (i) { res[marks[i]].push(i); });
  return res;
}

HD.swapDiff = {MAX: MAX, diff: diff, isInline: isInline};
})();
