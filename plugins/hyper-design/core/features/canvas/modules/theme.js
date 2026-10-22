/* Model — 테마(조각 5, H10·H12·H14). DOM·저장소를 쓰지 않는다.
   기본 테마 = 빌드가 준 팔레트(tokens-<slug>.css, 잠김). 내 테마 = 바탕 팔레트 + 색 네 칸 덮어쓰기(CSS 변수).
   상태 = {v:1, cur: 기본 slug | 내 테마 id, mine: [{id, name, base, c: {brand, text, bg, accent}}]}
   ROLES = 색 네 칸 → CSS 변수(화면 토큰 이름)
   reduce(state, a) → 새 상태: pick{id} · copy{from, c, name, id} · rename{id, name} · color{id, role, hex} · remove{id} · restore{item, at}
   contrast(a, b) → 대비 비(WCAG) · vars(theme) → {변수: 값} · hex(v) → '#RRGGBB' 또는 null
   키 hd-themes(모든 캔버스 공용, §8-1). HD.theme = {KEY, ROLES, LABEL, normalize, reduce, contrast, vars, hex, load, save} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEY = 'hd-themes', V = 1;
var ROLES = {brand: '--c-brand', text: '--c-text-1', bg: '--c-bg', accent: '--c-accent'};
var LABEL = {brand: '주 색', text: '글자', bg: '바탕', accent: '강조'};

function hex(v) {
  var m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(v || '').trim()); if (!m) return null;
  var h = m[1].length === 3 ? m[1].replace(/./g, function (c) { return c + c; }) : m[1];
  return '#' + h.toUpperCase();
}
function lum(h) {
  var n = parseInt(h.slice(1), 16), ch = [n >> 16 & 255, n >> 8 & 255, n & 255].map(function (x) {
    x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
}
function contrast(a, b) {
  a = hex(a); b = hex(b); if (!a || !b) return 0;
  var x = lum(a), y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
function colors(c) {
  var o = {}; Object.keys(ROLES).forEach(function (r) { o[r] = hex(c && c[r]) || '#000000'; }); return o;
}
function normalize(o) {
  var s = {v: V, cur: '', mine: []};
  if (!o || typeof o !== 'object') return s;
  s.cur = typeof o.cur === 'string' ? o.cur : '';
  var seen = {};
  (Array.isArray(o.mine) ? o.mine : []).forEach(function (t) {
    if (!t || typeof t.id !== 'string' || seen[t.id]) return; seen[t.id] = 1;
    s.mine.push({id: t.id, name: String(t.name || '내 테마'), base: String(t.base || ''), c: colors(t.c)});
  });
  return s;
}
function copy(s) { return normalize(s); }
function find(s, id) { for (var i = 0; i < s.mine.length; i++) if (s.mine[i].id === id) return i; return -1; }

function reduce(state, a) {
  var s = copy(state), i;
  if (!a) return state;
  switch (a.type) {
    case 'pick':
      s.cur = String(a.id || ''); return s;
    case 'copy':                                     // 새 테마 = 지금 색을 그대로 복제하고 고르기
      s.mine.push({id: a.id, name: String(a.name || '내 테마'), base: String(a.base || ''), c: colors(a.c)});
      s.cur = a.id; return s;
    case 'rename':
      i = find(s, a.id); if (i < 0 || !String(a.name || '').trim()) return state;
      s.mine[i].name = String(a.name).trim(); return s;
    case 'color':
      i = find(s, a.id); var h = hex(a.hex);
      if (i < 0 || !h || !ROLES[a.role]) return state;
      s.mine[i].c[a.role] = h; return s;
    case 'remove':
      i = find(s, a.id); if (i < 0) return state;
      s.mine.splice(i, 1); if (s.cur === a.id) s.cur = a.fallback || ''; return s;
    case 'restore':
      if (!a.item || find(s, a.item.id) >= 0) return state;
      s.mine.splice(Math.max(0, Math.min(s.mine.length, a.at == null ? s.mine.length : a.at)), 0, a.item); return normalize(s);
  }
  return state;
}
function vars(t) { var o = {}; if (t && t.c) Object.keys(ROLES).forEach(function (r) { o[ROLES[r]] = t.c[r]; }); return o; }

function load(getItem) {
  var o = null; try { o = JSON.parse(getItem(KEY) || 'null'); } catch (e) { o = null; }
  return normalize(o && o.v === V ? o : null);
}
function save(s, setItem) { try { setItem(KEY, JSON.stringify(normalize(s))); } catch (e) {} }

HD.theme = {KEY: KEY, ROLES: ROLES, LABEL: LABEL, normalize: normalize, reduce: reduce, contrast: contrast, vars: vars, hex: hex, load: load, save: save};
})();
