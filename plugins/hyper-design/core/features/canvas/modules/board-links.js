/* Model — 판 메모 선(R47): 판 메모에서 메모·화면·폴더로 잇는 선의 모양·잇기·끊기·이름·없어진 메모 거두기·이름 바뀐 끝 따라가기·충돌 합치기·선 경로. DOM·저장소를 쓰지 않는다.
   상태 파일 이름 'board-links' = {<id>: {from: 'note:<메모 id>', to: 'note:<id>'|'screen:<화면 id>'|'folder:<줄 이름>', fromSide?, toSide?, label?, at}}
     side = 'top'|'right'|'bottom'|'left' · label = 평문 한 줄 LABEL_MAX(40)자 · at = ISO 시각 글. 모르는 칸은 그대로 둔다.
     folder:<줄 이름> = screens.json screens[].group(판에 보이는 줄 제목) — 레이어 패널 사용자 폴더(f<n>)는 판에 없어 아직 아님(나중에 따로 앞붙이 — 예 'ufolder:').
     메모 id 는 글자로만 안다(board-notes 를 부르지 않는다). 없는 끝을 가리키는 선은 저장에 남기고 그리지·풀지 않는다(live) — 던지지 않는다.
   parse(text) → {map, bad} — 깨진 JSON·객체 아님 = 빈 map(bad:'broken') · 모양이 틀린 선만 뺌(bad:'dropped') · 없음 = 빈 map(bad:null)
   end(s) → {kind: 'note'|'screen'|'folder', id} | null · newId(now, rnd) → 'l' + 시각 36진 + 4자
   add(map, id, {from, to, fromSide?, toSide?}, at) → {map, ok, why}: why 'bad'(모양·from 이 메모 아님) | 'self'(자기 자신) | 'dup'(같은 방향 같은 쌍) | 'taken'(id 겹침)
   remove(map, id) · rename(map, id, label, at) → 새 map(그대로·없는 id = 같은 map, 빈 이름 = 칸을 뺌)
   touching(map, noteIds) → 그 메모에 닿은 선 {id: 선} · prune(map, noteIds) → 그 선을 뺀 새 map(없으면 같은 map)
   retarget(map, old, now, at) → 끝 old('folder:<옛 이름>' 등)를 now 로 바꾼 새 map — 바꾸면 자기 자신이거나 같은 쌍이 되는 선은 뺀다(없으면 같은 map)
   live(map, has) → 그릴 선 [{id, from, to, …}] — has(end 글) 가 참인 끝만, 같은 방향 같은 쌍은 하나만(id 차례 첫 것)
   merge(base, local, server) → {ok, map} — 409 합치기: id 마다 한쪽만 바꿈 = 그쪽 · 둘이 같음 = 그대로 · 둘 다 다르게 바꿈 = 실패(ok:false)
   anchor(box, side) → 변 가운데 점 · nearSide(box, pt) → pt 에 가장 가까운 변 · path(a, aSide, b, bSide) → 굽은 선 SVG d · mid(같은 인자) → 선 가운데 점(이름 자리)
   HD.boardLinks = {NAME, LABEL_MAX, SIDES, KINDS, parse, end, newId, add, remove, rename, touching, prune, retarget, live, merge, anchor, nearSide, path, mid} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NAME = 'board-links', LABEL_MAX = 40, BEND = 80;
var SIDES = ['top', 'right', 'bottom', 'left'], KINDS = ['note', 'screen', 'folder'];
var has = function (o, k) { return !!o && Object.prototype.hasOwnProperty.call(o, k); };
function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
function same(a, b) { return JSON.stringify(a === undefined ? null : a) === JSON.stringify(b === undefined ? null : b); }
function copy(o) { var r = {}; for (var k in o) if (has(o, k)) r[k] = o[k]; return r; }

function end(s) {
  if (typeof s !== 'string') return null;
  var i = s.indexOf(':'); if (i <= 0 || i === s.length - 1) return null;
  var kind = s.slice(0, i);
  return KINDS.indexOf(kind) >= 0 ? {kind: kind, id: s.slice(i + 1)} : null;
}
function isNote(s) { var e = end(s); return !!e && e.kind === 'note'; }
function label(t) { return String(t == null ? '' : t).replace(/\s+/g, ' ').trim().slice(0, LABEL_MAX); }
function clean(l) {                                    // 선 하나 → 고친 선 | null(모양이 틀림)
  if (!isObj(l) || !isNote(l.from) || !end(l.to) || l.from === l.to) return null;
  var o = copy(l);
  ['fromSide', 'toSide'].forEach(function (k) { if (has(o, k) && SIDES.indexOf(o[k]) < 0) delete o[k]; });
  if (has(o, 'label')) { var v = typeof o.label === 'string' ? label(o.label) : ''; if (v) o.label = v; else delete o.label; }
  if (typeof o.at !== 'string') o.at = '';
  return o;
}
function parse(t) {
  if (t == null) return {map: {}, bad: null};
  var v; try { v = JSON.parse(t); } catch (e) { return {map: {}, bad: 'broken'}; }
  if (!isObj(v)) return {map: {}, bad: 'broken'};
  var map = {}, dropped = false;
  Object.keys(v).forEach(function (id) { var l = clean(v[id]); if (l) map[id] = l; else dropped = true; });
  return {map: map, bad: dropped ? 'dropped' : null};
}
function newId(now, rnd) {
  var r = '';
  for (var i = 0; i < 4; i++) r += Math.floor((rnd ? rnd() : Math.random()) * 36).toString(36);
  return 'l' + Math.floor(now).toString(36) + r;
}
function dupOf(map, from, to, skip) {
  return Object.keys(map || {}).some(function (k) { return k !== skip && map[k].from === from && map[k].to === to; });
}
function add(map, id, l, at) {
  var m = isObj(map) ? map : {};
  if (typeof id !== 'string' || !id || !isObj(l) || !isNote(l.from) || !end(l.to)) return {map: map, ok: false, why: 'bad'};
  if (l.from === l.to) return {map: map, ok: false, why: 'self'};
  if (has(m, id)) return {map: map, ok: false, why: 'taken'};
  if (dupOf(m, l.from, l.to)) return {map: map, ok: false, why: 'dup'};
  var o = {from: l.from, to: l.to};
  if (SIDES.indexOf(l.fromSide) >= 0) o.fromSide = l.fromSide;
  if (SIDES.indexOf(l.toSide) >= 0) o.toSide = l.toSide;
  o.at = String(at || '');
  var r = copy(m); r[id] = o;
  return {map: r, ok: true, why: null};
}
function remove(map, id) {
  if (!has(map, id)) return map;
  var m = copy(map); delete m[id]; return m;
}
function rename(map, id, t, at) {
  if (!has(map, id)) return map;
  var v = label(t), l = map[id];
  if ((l.label || '') === v) return map;
  var m = copy(map); m[id] = copy(l); m[id].at = String(at || '');
  if (v) m[id].label = v; else delete m[id].label;
  return m;
}
function keys(noteIds) { var k = {}; (noteIds || []).forEach(function (n) { k['note:' + n] = 1; }); return k; }
function touching(map, noteIds) {
  var k = keys(noteIds), out = {};
  Object.keys(isObj(map) ? map : {}).forEach(function (id) { if (k[map[id].from] || k[map[id].to]) out[id] = map[id]; });
  return out;
}
function prune(map, noteIds) {
  var t = touching(map, noteIds), ids = Object.keys(t);
  if (!ids.length) return map;
  var m = copy(map); ids.forEach(function (id) { delete m[id]; }); return m;
}
function retarget(map, old, now, at) {
  if (!isObj(map) || !end(old) || !end(now) || old === now) return map;
  if (isNote(old) !== isNote(now)) return map;          // 메모 끝(from)은 메모로만
  var m = null;
  Object.keys(map).sort().forEach(function (id) {
    var l = map[id]; if (l.from !== old && l.to !== old) return;
    m = m || copy(map);
    var n = copy(l); n.from = l.from === old ? now : l.from; n.to = l.to === old ? now : l.to; n.at = String(at || '');
    if (n.from === n.to || dupOf(m, n.from, n.to, id)) delete m[id]; else m[id] = n;
  });
  return m || map;
}
function live(map, ok) {
  var m = isObj(map) ? map : {}, seen = {}, out = [];
  Object.keys(m).sort().forEach(function (id) {
    var l = m[id]; if (!isObj(l) || !isNote(l.from) || !end(l.to) || l.from === l.to) return;
    var pair = l.from + '\n' + l.to;
    if (seen[pair] || !ok(l.from) || !ok(l.to)) return;
    seen[pair] = 1;
    var e = copy(l); e.id = id; out.push(e);
  });
  return out;
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

/* ---- 선 경로(판 좌표) ---- */
function anchor(box, side) {
  var cx = box.x + box.w / 2, cy = box.y + box.h / 2;
  return side === 'top' ? {x: cx, y: box.y} : side === 'bottom' ? {x: cx, y: box.y + box.h} :
         side === 'left' ? {x: box.x, y: cy} : {x: box.x + box.w, y: cy};
}
function nearSide(box, pt) {
  var best = 'right', bd = Infinity;
  SIDES.forEach(function (s) { var a = anchor(box, s), d = Math.hypot(a.x - pt.x, a.y - pt.y); if (d < bd) { bd = d; best = s; } });
  return best;
}
var NORMAL = {top: [0, -1], right: [1, 0], bottom: [0, 1], left: [-1, 0]};
function ctrl(a, aSide, b, bSide) {
  var k = Math.min(BEND, Math.max(24, Math.hypot(b.x - a.x, b.y - a.y) / 2));   // 짧은 선은 덜 휘게
  var na = NORMAL[aSide] || [1, 0], nb = NORMAL[bSide] || [-1, 0];
  return [a, {x: a.x + na[0] * k, y: a.y + na[1] * k}, {x: b.x + nb[0] * k, y: b.y + nb[1] * k}, b];
}
function r1(v) { return Math.round(v * 10) / 10; }
function path(a, aSide, b, bSide) {
  var p = ctrl(a, aSide, b, bSide);
  return 'M' + r1(p[0].x) + ',' + r1(p[0].y) + ' C' + r1(p[1].x) + ',' + r1(p[1].y) + ' ' + r1(p[2].x) + ',' + r1(p[2].y) + ' ' + r1(p[3].x) + ',' + r1(p[3].y);
}
function mid(a, aSide, b, bSide) {                    // 3차 베지어 t=0.5
  var p = ctrl(a, aSide, b, bSide);
  return {x: r1((p[0].x + 3 * p[1].x + 3 * p[2].x + p[3].x) / 8), y: r1((p[0].y + 3 * p[1].y + 3 * p[2].y + p[3].y) / 8)};
}

HD.boardLinks = {NAME: NAME, LABEL_MAX: LABEL_MAX, SIDES: SIDES, KINDS: KINDS, parse: parse, end: end, newId: newId, add: add, remove: remove, rename: rename,
                 touching: touching, prune: prune, retarget: retarget, live: live, merge: merge, anchor: anchor, nearSide: nearSide, path: path, mid: mid};
})();
