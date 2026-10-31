/* Model — 캔버스 화면 ↔ 앱 화면 스냅숏 비교(V2 맞음 검증): 두 항목 목록 → 같음 수·빠짐·더함·스타일 다름·불확실. 순수(AI·DOM·시계 없음 — 같은 입력 = 같은 결과).
   항목 = palette.js hd-snapshot-r 의 items[i] = {role: button|heading|link|input|img|text, text, tag, style: {color, bg, fs, fw, radius}}.
   diff(a, b) → {match: 짝지어 모두 같은 수, missing: [{a, b:null, role, text}](캔버스에만), extra: [{a:null, b, role, text}](앱에만),
                 style: [{a, b, role, text, props: [{prop, a, b}]}], unsure: [{a, b, role, text, why, other}]} — a·b = 원래 목록의 차례 번호.
     1) 짝 = (역할, norm 글자) — 같은 열쇠가 여럿이면 차례로. 2) 남은 것끼리 글자는 같은데 역할만 다름 = unsure 'role'.
     3) 같은 자리(앞에 짝지은 수가 같음)에서 같은 역할인데 글자만 다름 = unsure 'text'(빠짐+더함 둘로 세지 않는다).
     4) 같은 열쇠가 이미 짝을 가졌는데 남음(같은 글자 수가 다름) = unsure 'dup'(어느 것이 빠졌는지 모름 — AI 에 묻지 않음). 5) 나머지 = missing·extra.
     스타일: color·bg = RGB 거리 COLOR_TOL 이하(둘 다 투명이면 같음, 못 읽는 색은 글자 그대로) · fs·radius = PX_TOL(1px) 이하 · fw = 같아야. 한쪽에 값이 없으면 견주지 않는다.
   count(d) → 다른 곳 수(missing + extra + style + unsure). norm(text) · color(css) → [r, g, b, a] | null.
   모양이 틀린 항목(role 없음)은 건너뛴다(차례 번호는 그대로). 목록이 아니면 [] 로 본다.
   HD.twinDiff = {COLOR_TOL, PX_TOL, PROPS, norm, color, diff, count} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var COLOR_TOL = 12, PX_TOL = 1, ALPHA_TOL = 0.05;
var PROPS = ['color', 'bg', 'fs', 'fw', 'radius'];

function norm(t) {
  var s = t == null ? '' : String(t);
  if (s.normalize) s = s.normalize('NFC');
  return s.replace(/[​-‍﻿]/g, '').replace(/[\s ]+/g, ' ').trim();
}

function color(v) {
  if (typeof v !== 'string') return null;
  var s = v.trim().toLowerCase(), m;
  if (s === 'transparent') return [0, 0, 0, 0];
  if ((m = /^#([0-9a-f]{6})$/.exec(s))) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16), 1];
  if ((m = /^#([0-9a-f]{3})$/.exec(s))) return [0, 1, 2].map(function (i) { return parseInt(m[1][i] + m[1][i], 16); }).concat([1]);
  if ((m = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/.exec(s))) {
    return [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]];
  }
  return null;
}

function sameColor(x, y) {
  var a = color(x), b = color(y);
  if (!a || !b) return String(x) === String(y);
  if (a[3] <= 0.01 && b[3] <= 0.01) return true;
  if (Math.abs(a[3] - b[3]) > ALPHA_TOL) return false;
  var d = Math.sqrt(Math.pow(a[0] - b[0], 2) + Math.pow(a[1] - b[1], 2) + Math.pow(a[2] - b[2], 2));
  return d <= COLOR_TOL;
}

function num(v) { return typeof v === 'number' && isFinite(v) ? v : null; }

function props(sa, sb) {
  var out = [];
  sa = sa && typeof sa === 'object' ? sa : {}; sb = sb && typeof sb === 'object' ? sb : {};
  PROPS.forEach(function (p) {
    var x = sa[p], y = sb[p], same;
    if (x == null || y == null) return;
    if (p === 'color' || p === 'bg') same = sameColor(x, y);
    else if (num(x) == null || num(y) == null) same = String(x) === String(y);
    else if (p === 'fw') same = x === y;
    else same = Math.abs(x - y) <= PX_TOL;
    if (!same) out.push({prop: p, a: x, b: y});
  });
  return out;
}

function clean(list) {
  var out = [];
  (Array.isArray(list) ? list : []).forEach(function (it, i) {
    if (!it || typeof it !== 'object' || typeof it.role !== 'string' || !it.role) return;
    out.push({i: i, role: it.role, text: norm(it.text), st: it['style']});
  });
  return out;
}

function keyOf(x) { return x.role + '\u0001' + x.text; }

function diff(a, b) {
  var A = clean(a), B = clean(b), res = {match: 0, missing: [], extra: [], style: [], unsure: []};
  var queue = {}, pairs = [], usedA = {}, usedB = {}, paired = {};
  B.forEach(function (y, j) { var k = keyOf(y); (queue[k] = queue[k] || []).push(j); });
  A.forEach(function (x, i) {                             // 1) 같은 열쇠 — 차례로
    var q = queue[keyOf(x)];
    if (q && q.length) { var j = q.shift(); pairs.push([i, j]); usedA[i] = 1; usedB[j] = 1; paired[keyOf(x)] = 1; }
  });
  pairs.forEach(function (p) {
    var x = A[p[0]], y = B[p[1]], ps = props(x.st, y.st);
    if (ps.length) res['style'].push({a: x.i, b: y.i, role: x.role, text: x.text, props: ps});
    else res.match++;
  });
  function gapA(i) { return pairs.filter(function (p) { return p[0] < i; }).length; }
  function gapB(j) { return pairs.filter(function (p) { return p[1] < j; }).length; }
  function unsure(x, y, why) {
    var base = x || y;
    res.unsure.push({a: x ? x.i : null, b: y ? y.i : null, role: base.role, text: base.text, why: why,
                     other: x && y ? {role: y.role, text: y.text} : null});
  }
  var la = A.map(function (x, i) { return i; }).filter(function (i) { return !usedA[i]; });
  var lb = B.map(function (y, j) { return j; }).filter(function (j) { return !usedB[j]; });
  function take(test, why) {                              // 남은 a 차례대로, 맞는 첫 b 와
    la = la.filter(function (i) {
      for (var n = 0; n < lb.length; n++) {
        if (test(A[i], B[lb[n]], i, lb[n])) { unsure(A[i], B[lb[n]], why); lb.splice(n, 1); return false; }
      }
      return true;
    });
  }
  take(function (x, y) { return x.text !== '' && x.text === y.text && x.role !== y.role; }, 'role');           // 2)
  take(function (x, y, i, j) { return x.role === y.role && gapA(i) === gapB(j); }, 'text');                       // 3)
  la = la.filter(function (i) { if (paired[keyOf(A[i])]) { unsure(A[i], null, 'dup'); return false; } return true; });   // 4)
  lb = lb.filter(function (j) { if (paired[keyOf(B[j])]) { unsure(null, B[j], 'dup'); return false; } return true; });
  la.forEach(function (i) { res.missing.push({a: A[i].i, b: null, role: A[i].role, text: A[i].text}); });       // 5)
  lb.forEach(function (j) { res.extra.push({a: null, b: B[j].i, role: B[j].role, text: B[j].text}); });
  return res;
}

function count(d) {
  if (!d || typeof d !== 'object') return 0;
  return ['missing', 'extra', 'style', 'unsure'].reduce(function (n, k) { return n + (Array.isArray(d[k]) ? d[k].length : 0); }, 0);
}

HD.twinDiff = {COLOR_TOL: COLOR_TOL, PX_TOL: PX_TOL, PROPS: PROPS, norm: norm, color: color, diff: diff, count: count};
})();
