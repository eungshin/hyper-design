/* Model — 카드(아트보드) 크기 규칙(task 46): 프리셋 묶음·검사·카드마다 크기(없으면 프로젝트 기본)·방향·최근 6개·내 프리셋. DOM·저장소를 쓰지 않는다.
   크기 = {w, h, preset?} (CSS px 정수 MIN~MAX = 16~60000, preset = 고른 프리셋 이름 — 요청문·단추에 보임). 카드 크기 맵 sizes = {카드 id: 크기}(상태 이름 card-size).
   CATS = [{id, name}] (recent 최근 · mobile 모바일 · tablet 태블릿 · desktop 웹/데스크톱 · saved 사용자 정의) · PRESETS = [{cat, name, w, h}]
   check(w, h) → {ok:true, w, h} | {ok:false, error}   글자 숫자도 받는다, 정수 MIN~MAX 만
   of(sizes, id, def) → {w, h, preset?, custom}   custom = 이 카드에 저장된 크기(아니면 def = 프로젝트 카드 크기)
   set(sizes, ids, size | null, def) → 새 sizes   null 또는 기본과 같은 크기(프리셋 이름 없음) = 그 카드 항목을 지움(기본 크기로)
   common(sizes, ids, def) → 모두 같은 크기면 그 of(…), 다르면 null
   swap(size) → 가로·세로 바꾼 크기(프리셋 이름은 presetOf 로 다시) · orient(size) → 'portrait'(w ≤ h) | 'landscape'
   presetOf(w, h, saved?) → 맞는 프리셋 이름 | 가로로 맞으면 '이름 가로' | ''   (내 프리셋 먼저)
   label(size) → 'W×H' · full(size) → 'W×H(프리셋)' | 'W×H' — 요청문 '화면 크기:' 줄
   pushRecent(list, size) → 새 목록(맨 앞, 같은 크기 빼고, 많아야 RECENT) · savePreset(saved, name, w, h) → {ok, saved} | {ok:false, error}(같은 이름 = 덮어쓰기)
   list(cat, prefs) → 그 탭의 카드 [{name, w, h, saved?}] · prefs(raw) → {recent, saved}(전역 설정 키 hd-artboard, 깨진 항목은 뺌)
   norm(raw) → {sizes, bad:[id]}   저장값 읽기 — 깨진 항목은 빼고 bad 로(View 가 [hd] 경고), 객체가 아니면 bad ['*']
   carry(sizes, from, to) → 새 sizes   빈 레이아웃(from) 크기를 승격된 화면(to)으로 · nudge(v, key, shift) → 새 값 | null(화살표 ±1, Shift ±10, 범위 안)
   HD.artboard = {CATS, PRESETS, MIN, MAX, RECENT, check, of, set, common, swap, orient, presetOf, label, full, pushRecent, savePreset, list, prefs, norm, carry, nudge} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var MIN = 16, MAX = 60000, RECENT = 6;            // R57: 웹·광고(320×50)·상세페이지(860×40000)·AI 이미지 어떤 모양이든 — 정말 예외만 거절(hd_place.py SIZE_MIN·SIZE_MAX 와 같게, test_canvas_unit_size_range.py)
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };
var CATS = [{id: 'recent', name: '최근'}, {id: 'mobile', name: '모바일'}, {id: 'tablet', name: '태블릿'}, {id: 'desktop', name: '웹/데스크톱'}, {id: 'saved', name: '사용자 정의'}];
// 크기 = CSS px(기기 논리 해상도) — Figma 프레임 프리셋·Apple/Google 기기 표(RESEARCH.md)
var PRESETS = [
  ['mobile', 'iPhone 16', 393, 852], ['mobile', 'iPhone 16 Pro', 402, 874], ['mobile', 'iPhone 16 Plus', 430, 932], ['mobile', 'iPhone 16 Pro Max', 440, 956],
  ['mobile', 'iPhone 13 mini', 375, 812], ['mobile', 'iPhone SE', 375, 667], ['mobile', 'Android Compact', 412, 917], ['mobile', 'Android Small', 360, 640],
  ['mobile', 'Android Medium', 700, 840],
  ['tablet', 'iPad mini', 744, 1133], ['tablet', 'iPad Air 11', 820, 1180], ['tablet', 'iPad Pro 11', 834, 1194], ['tablet', 'iPad Pro 12.9', 1024, 1366],
  ['tablet', 'Surface Pro 8', 1440, 960], ['tablet', 'Android Expanded', 1280, 800],
  ['desktop', 'MacBook Air', 1280, 832], ['desktop', 'MacBook Pro 14', 1512, 982], ['desktop', 'MacBook Pro 16', 1728, 1117], ['desktop', 'Desktop', 1440, 1024],
  ['desktop', 'Web 1366', 1366, 768], ['desktop', 'Web 1920', 1920, 1080], ['desktop', 'iMac', 1280, 720]
].map(function (p) { return {cat: p[0], name: p[1], w: p[2], h: p[3]}; });

function int(v) {
  if (typeof v === 'string') { v = v.trim(); if (!/^\d+$/.test(v)) return null; v = +v; }
  return typeof v === 'number' && isFinite(v) && Math.floor(v) === v ? v : null;
}
function inRange(n) { return n != null && n >= MIN && n <= MAX; }
function check(w, h) {
  var W = int(w), H = int(h), why = function (f) { return f + '는 ' + MIN + '~' + MAX + ' 사이 정수(px)로 적어 주세요'; };
  if (!inRange(W)) return {ok: false, error: why('너비')};
  if (!inRange(H)) return {ok: false, error: why('높이')};
  return {ok: true, w: W, h: H};
}
function clean(v) {                                // 저장값 하나 → 크기 | null
  if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
  var c = check(v.w, v.h); if (!c.ok) return null;
  var o = {w: c.w, h: c.h}; if (typeof v.preset === 'string' && v.preset) o.preset = v.preset;
  return o;
}
function of(sizes, id, def) {
  var s = has(sizes, id) ? clean(sizes[id]) : null;
  if (!s) return {w: def.w, h: def.h, custom: false};
  var o = {w: s.w, h: s.h}; if (s.preset) o.preset = s.preset; o.custom = true;
  return o;
}
function set(sizes, ids, size, def) {
  var n = {}; Object.keys(sizes || {}).forEach(function (k) { n[k] = sizes[k]; });
  var s = size ? clean(size) : null, plain = s && !s.preset && s.w === def.w && s.h === def.h;
  (ids || []).forEach(function (id) { if (!s || plain) delete n[id]; else n[id] = JSON.parse(JSON.stringify(s)); });
  return n;
}
function common(sizes, ids, def) {
  var first = null, same = true;
  (ids || []).forEach(function (id) { var s = of(sizes, id, def); if (!first) first = s; else if (s.w !== first.w || s.h !== first.h) same = false; });
  return same ? first : null;
}
function orient(s) { return s.w <= s.h ? 'portrait' : 'landscape'; }
function presetOf(w, h, saved) {
  var all = (saved || []).concat(PRESETS), i;
  for (i = 0; i < all.length; i++) if (all[i].w === w && all[i].h === h) return all[i].name;
  for (i = 0; i < all.length; i++) if (all[i].w === h && all[i].h === w) return all[i].name + ' 가로';
  return '';
}
function swap(s, saved) { var o = {w: s.h, h: s.w}, p = presetOf(o.w, o.h, saved); if (p) o.preset = p; return o; }
function label(s) { return s.w + '×' + s.h; }
function full(s) { return label(s) + (s.preset ? '(' + s.preset + ')' : ''); }
function pushRecent(list, size) {
  var s = clean(size); if (!s) return (list || []).slice();
  var out = [{w: s.w, h: s.h}];
  (list || []).forEach(function (r) { if (out.length < RECENT && (r.w !== s.w || r.h !== s.h)) out.push({w: r.w, h: r.h}); });
  return out;
}
function savePreset(saved, name, w, h) {
  var nm = typeof name === 'string' ? name.trim() : '';
  if (!nm) return {ok: false, error: '프리셋 이름을 적어 주세요'};
  var c = check(w, h); if (!c.ok) return c;
  var out = (saved || []).filter(function (p) { return p.name !== nm; });
  var at = (saved || []).map(function (p) { return p.name; }).indexOf(nm);
  out.splice(at < 0 ? out.length : at, 0, {name: nm, w: c.w, h: c.h});
  return {ok: true, saved: out};
}
function prefs(raw) {
  var o = {recent: [], saved: []}; if (!raw || typeof raw !== 'object') return o;
  (Array.isArray(raw.recent) ? raw.recent : []).forEach(function (r) { var s = clean(r); if (s && o.recent.length < RECENT) o.recent.push({w: s.w, h: s.h}); });
  (Array.isArray(raw.saved) ? raw.saved : []).forEach(function (p) { var s = clean(p); if (s && p && typeof p.name === 'string' && p.name.trim()) o.saved.push({name: p.name.trim(), w: s.w, h: s.h}); });
  return o;
}
function list(cat, pf) {
  pf = pf || {recent: [], saved: []};
  if (cat === 'recent') return (pf.recent || []).map(function (r) { return {name: presetOf(r.w, r.h, pf.saved) || label(r), w: r.w, h: r.h}; });
  if (cat === 'saved') return (pf.saved || []).map(function (p) { return {name: p.name, w: p.w, h: p.h, saved: true}; });
  return PRESETS.filter(function (p) { return p.cat === cat; }).map(function (p) { return {name: p.name, w: p.w, h: p.h}; });
}
function norm(raw) {
  if (raw == null) return {sizes: {}, bad: []};
  if (typeof raw !== 'object' || Array.isArray(raw)) return {sizes: {}, bad: ['*']};
  var sizes = {}, bad = [];
  Object.keys(raw).forEach(function (id) { var s = clean(raw[id]); if (s) sizes[id] = s; else bad.push(id); });
  return {sizes: sizes, bad: bad};
}
function carry(sizes, from, to) {
  var n = {}; Object.keys(sizes || {}).forEach(function (k) { if (k !== from) n[k] = sizes[k]; });
  if (has(sizes, from)) n[to] = sizes[from];
  return n;
}
function nudge(v, key, shift) {
  var n = int(v); if (n == null) return null;
  var d = key === 'ArrowUp' ? 1 : key === 'ArrowDown' ? -1 : 0; if (!d) return null;
  return Math.min(MAX, Math.max(MIN, n + d * (shift ? 10 : 1)));
}

HD.artboard = {CATS: CATS, PRESETS: PRESETS, MIN: MIN, MAX: MAX, RECENT: RECENT, check: check, of: of, set: set, common: common, swap: swap, orient: orient,
               presetOf: presetOf, label: label, full: full, pushRecent: pushRecent, savePreset: savePreset, list: list, prefs: prefs, norm: norm, carry: carry, nudge: nudge};
})();
