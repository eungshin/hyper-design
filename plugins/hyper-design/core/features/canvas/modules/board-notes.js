/* Model — 판 메모(R23): 빈 판에 사람이 둔 글 상자의 모양·만들기·고치기·빈 메모 버리기·충돌 합치기·빈 자리 규칙. DOM·저장소를 쓰지 않는다.
   상태 파일 이름 'board-notes' = {<id>: {x, y, w, h?, text, color?, hidden?, locked?, at}} — 판(#stage) 좌표 정수 px, h 없음 = 글 높이대로, at = 마지막으로 바꾼 시각(ms).
     모르는 칸은 그대로 둔다(다른 도구가 더한 칸을 지우지 않게). 글 = 평문, \r\n → \n, 끝 빈칸 뺌, MAX 자까지.
   parse(text) → {map, bad} — 깨진 JSON·객체 아님 = 빈 판(bad:'broken') · 모양이 틀린 메모만 뺌(bad:'dropped') · 없음 = 빈 판(bad:null)
   newId(now, rnd) → 'n' + 시각 36진 + 4자(rnd = 0..1 수 함수)
   create(map, id, {x, y, w?}, now) → 새 map(글 빈 메모 — 셸은 쓰기 전까지 저장하지 않는다)
   finish(map, id, text, now) → {map, kind}: 'drop'(빈 글 = 메모를 뺌) | 'keep'(글이 바뀜) | 'same'(그대로 — 저장·기록 없음)
   move(map, id, x, y, now) · remove(map, id) → 새 map(없는 id = 같은 map)
   resize(map, id, w, h, now) → 새 map(R25): 폭 MIN_W..MAX_W · h = undefined 그대로 | null 글 높이대로(h 뺌) | 수 MIN_H..MAX_H(최소 높이 — 글이 길면 더 커진다). 그대로·없는 id = 같은 map
   flag(map, ids, key, on, now) → 새 map(R26): key 'hidden'|'locked' — 켜기 = 칸 true · 끄기 = 칸을 뺌(옛 메모와 같은 모양). 바뀐 것 없음·없는 id·모르는 key = 같은 map
   isHidden(n) · isLocked(n) → 칸이 true 인가(숨김 = 판에 그리지 않고 전체 보기에서 뺌 · 잠금 = 판에서 옮기기·크기·고치기·지우기 안 됨, 고르기는 됨)
   extent(ext, boxes) → ext {x0, y0, x1, y1}(없으면 null)를 메모 상자 [{x, y, w, h}] 까지 넓힌 판 범위(전체 보기, R25) · 숫자가 아닌 상자는 건너뜀
   layers(map) → [{id: 'note:<id>', name, hid, lock}] 레이어 패널 줄(R25) — 위→아래·왼→오른 차례, 이름 = 첫 글 줄 40자 · hid·lock = 숨김·잠금(R26)
   merge(base, local, server) → {ok, map} — 409 합치기: id 마다 한쪽만 바꿈 = 그쪽 · 둘이 같음 = 그대로 · 둘 다 다르게 바꿈 = 실패(ok:false)
   room(pt, boxes) → {free, x, y, w} — 새 메모 자리(판 좌표): 누른 점이 카드 상자(boxes [{x0, y0, x1, y1}]) 안이면 free:false.
     메모 왼쪽 위 = 누른 점 − (PAD_X, PAD_Y)(첫 줄 글자 자리, 바로 위 카드에 걸치면 그 아래로), 폭 = 오른쪽 가까운 카드 앞 GAP 까지(MIN_W..W) — 카드를 덮지 않게
   spot(chain) → 'note' | 'empty' | 'busy' — 누른 자리(맨 안쪽부터 바깥으로 요소 표시 목록, 각 '#id' · '.class' · 'tag' 글들)가 메모인가, 빈 판인가, 그 밖(카드·판 글·선·UI)인가
   HD.boardNotes = {NAME, W, MIN_W, MAX_W, MIN_H, MAX, LAYER, FLAGS, parse, newId, create, finish, move, resize, flag, isHidden, isLocked, remove, merge, room, spot, extent, layers, text, EMPTY, BUSY} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NAME = 'board-notes', W = 280, MIN_W = 120, MAX_W = 1600, MIN_H = 52, MAX_H = 4000, LAYER = 'note:', MAX = 2000, PAD_X = 14, PAD_Y = 26, GAP = 12, BAND = 80;
var EMPTY = ['#screens', '#stage', '#intro', '#rows', '#foot', '.flow', '.cards'];   // 이 요소 자체를 누름 = 빈 판(줄 사이·줄 안 카드 사이 빈칸)
var BUSY = ['.card', '.bt', '#dscard', '.glabel', 'svg', '#tools', 'button', 'input', 'textarea'];   // 조상에 이것이 있으면 빈 판이 아님
var FLAGS = ['hidden', 'locked'];                    // 메모의 켜고 끄는 칸(R26) — true 만 켜짐, 다른 값은 parse 가 뺀다
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };
function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
function same(a, b) { return JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b); }
function copy(o) { var r = {}; for (var k in o) if (has(o, k)) r[k] = o[k]; return r; }
function num(v) { return typeof v === 'number' && isFinite(v); }

function text(t) {
  var s = String(t == null ? '' : t).replace(/\r\n?/g, '\n').replace(/\s+$/, '');
  return s.length > MAX ? s.slice(0, MAX) : s;
}
function clean(n) {                                    // 메모 하나 → 고친 메모 | null(모양이 틀림)
  if (!isObj(n) || !num(n.x) || !num(n.y) || typeof n.text !== 'string') return null;
  var o = copy(n);
  o.x = Math.round(n.x); o.y = Math.round(n.y);
  o.w = num(n.w) && n.w >= 40 ? Math.round(n.w) : W;
  if (has(n, 'h')) { if (num(n.h) && n.h > 0) o.h = Math.round(n.h); else delete o.h; }
  o.text = text(n.text);
  FLAGS.forEach(function (k) { if (has(o, k) && o[k] !== true) delete o[k]; });
  if (!num(n.at)) o.at = 0;
  return o;
}
function parse(t) {
  if (t == null) return {map: {}, bad: null};
  var v; try { v = JSON.parse(t); } catch (e) { return {map: {}, bad: 'broken'}; }
  if (!isObj(v)) return {map: {}, bad: 'broken'};
  var map = {}, dropped = false;
  Object.keys(v).forEach(function (id) { var n = clean(v[id]); if (n && n.text) map[id] = n; else dropped = true; });
  return {map: map, bad: dropped ? 'dropped' : null};
}
function newId(now, rnd) {
  var r = '';
  for (var i = 0; i < 4; i++) r += Math.floor((rnd ? rnd() : Math.random()) * 36).toString(36);
  return 'n' + Math.floor(now).toString(36) + r;
}
function create(map, id, at, now) {
  var m = copy(map || {});
  m[id] = {x: Math.round(at.x), y: Math.round(at.y), w: num(at.w) && at.w >= 40 ? Math.round(at.w) : W, text: '', at: now};
  return m;
}
function finish(map, id, t, now) {
  if (!has(map, id)) return {map: map, kind: 'same'};
  var v = text(t), m = copy(map);
  if (!v.trim()) { delete m[id]; return {map: m, kind: 'drop'}; }
  if (v === map[id].text) return {map: map, kind: 'same'};
  m[id] = copy(map[id]); m[id].text = v; m[id].at = now;
  return {map: m, kind: 'keep'};
}
function move(map, id, x, y, now) {
  if (!has(map, id)) return map;
  var m = copy(map); m[id] = copy(map[id]); m[id].x = Math.round(x); m[id].y = Math.round(y); m[id].at = now;
  return m;
}
function clamp(v, a, b) { return Math.max(a, Math.min(b, Math.round(v))); }
function resize(map, id, w, h, now) {
  if (!has(map, id)) return map;
  var n = map[id], nw = num(w) ? clamp(w, MIN_W, MAX_W) : n.w, nh = h === null ? undefined : num(h) ? clamp(h, MIN_H, MAX_H) : n.h;
  if (nw === n.w && nh === n.h) return map;
  var m = copy(map); m[id] = copy(n); m[id].w = nw; m[id].at = now;
  if (nh === undefined) delete m[id].h; else m[id].h = nh;
  return m;
}
function isHidden(n) { return !!n && n.hidden === true; }
function isLocked(n) { return !!n && n.locked === true; }
function flag(map, ids, key, on, now) {
  if (FLAGS.indexOf(key) < 0 || !isObj(map)) return map;
  var m = null;
  (ids || []).forEach(function (id) {
    if (!has(map, id) || (map[id][key] === true) === !!on) return;
    m = m || copy(map); m[id] = copy(map[id]); m[id].at = now;
    if (on) m[id][key] = true; else delete m[id][key];
  });
  return m || map;
}
function extent(ext, boxes) {
  var e = ext ? {x0: ext.x0, y0: ext.y0, x1: ext.x1, y1: ext.y1} : null;
  (boxes || []).forEach(function (b) {
    if (!b || !num(b.x) || !num(b.y) || !num(b.w) || !num(b.h)) return;
    if (!e) { e = {x0: b.x, y0: b.y, x1: b.x + b.w, y1: b.y + b.h}; return; }
    e.x0 = Math.min(e.x0, b.x); e.y0 = Math.min(e.y0, b.y); e.x1 = Math.max(e.x1, b.x + b.w); e.y1 = Math.max(e.y1, b.y + b.h);
  });
  return e;
}
function layers(map) {
  var m = isObj(map) ? map : {};
  return Object.keys(m).sort(function (a, b) { return (m[a].y - m[b].y) || (m[a].x - m[b].x) || (a < b ? -1 : a > b ? 1 : 0); }).map(function (id) {
    var line = String(m[id].text || '').split('\n').map(function (s) { return s.trim(); }).filter(Boolean)[0] || '(빈 메모)';
    return {id: LAYER + id, name: line.length > 40 ? line.slice(0, 40) + '…' : line, hid: isHidden(m[id]), lock: isLocked(m[id])};
  });
}
function remove(map, id) {
  if (!has(map, id)) return map;
  var m = copy(map); delete m[id]; return m;
}
function merge(base, local, server) {
  var B = isObj(base) ? base : {}, L = isObj(local) ? local : {}, S = isObj(server) ? server : {}, ids = {}, out = {}, ok = true;
  [L, S, B].forEach(function (o) { Object.keys(o).forEach(function (k) { ids[k] = 1; }); });
  Object.keys(ids).forEach(function (id) {
    var b = B[id], l = L[id], s = S[id], v;
    if (same(b, s)) v = l;
    else if (same(b, l) || same(l, s)) v = s;
    else { ok = false; return; }
    if (v != null) out[id] = v;
  });
  return ok ? {ok: true, map: out} : {ok: false, map: null};
}
function room(pt, boxes) {
  var x = Math.round(pt.x - PAD_X), y = Math.round(pt.y - PAD_Y), w = W;
  for (var i = 0; i < (boxes || []).length; i++) {
    var b = boxes[i];
    if (pt.x >= b.x0 && pt.x <= b.x1 && pt.y >= b.y0 && pt.y <= b.y1) return {free: false, x: x, y: y, w: 0};
    if (b.x0 >= pt.x && b.y0 < y + BAND && b.y1 > y) w = Math.min(w, Math.floor(b.x0 - GAP - x));   // 같은 높이 띠에서 오른쪽에 있는 카드 앞까지
    else if (b.x0 < pt.x && b.x1 > x && b.y1 <= pt.y && b.y1 > y) y = Math.ceil(b.y1 + 4);           // 바로 위 카드(이름 줄)에 걸치면 그 아래로
  }
  return {free: true, x: x, y: y, w: Math.max(MIN_W, w)};
}
function matches(tags, list) { return (tags || []).some(function (t) { return list.indexOf(t) >= 0; }); }
function spot(chain) {
  chain = Array.isArray(chain) ? chain : [];
  for (var i = 0; i < chain.length; i++) {
    if (matches(chain[i], ['.bnote'])) return 'note';
    if (matches(chain[i], BUSY)) return 'busy';
  }
  return chain.length && matches(chain[0], EMPTY) ? 'empty' : 'busy';
}

HD.boardNotes = {NAME: NAME, FLAGS: FLAGS, flag: flag, isHidden: isHidden, isLocked: isLocked, W: W, MIN_W: MIN_W, MAX_W: MAX_W, MIN_H: MIN_H, MAX: MAX, LAYER: LAYER, resize: resize, extent: extent, layers: layers, room: room, EMPTY: EMPTY, BUSY: BUSY, parse: parse, newId: newId, create: create, finish: finish, move: move, remove: remove, merge: merge, spot: spot, text: text};
})();
