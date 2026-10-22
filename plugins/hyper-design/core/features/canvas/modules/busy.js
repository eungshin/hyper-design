/* Model — "AI 수정 중" 덮개 상태(Q2b, D14). DOM·저장소를 쓰지 않는다(저장은 넘겨받은 getItem/setItem 으로).
   상태 = {v: 1, items: {<화면 id>: {via: 'paseo'|'queue', since: ms, file: out 기준 화면 파일, mtime: 기준 시각|null}}}
   끝 신호 = 화면 파일 mtime 이 덮개를 씌울 때 잡은 기준(mtime)보다 커짐. 기준이 null 이면 걷히지 않는다(손으로 걷기).
   reduce(state, a) → 새 상태(바뀐 게 없으면 같은 객체):
     mark{screens:[{id, file}], via, now}  덮개 더하기·덮어쓰기(mtime null = 기준 아직)
     baseline{mtimes:{file: number|null}}   null 기준 채우기
     seen{mtimes:{file: number|null}}       기준보다 새 mtime 인 것 걷기
     lift{id}                               하나 걷기
   load(getItem, key) → 상태(깨졌거나 판이 다르면 initial()) · save(state, setItem, key) 던지지 않음 · files(state) → 겹치지 않는 파일 목록
   HD.busy = {initial, reduce, load, save, files} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var VIA = ['paseo', 'queue'];

function initial() { return {v: 1, items: {}}; }
function num(x) { return typeof x === 'number' && isFinite(x); }
function copy(items) { var o = {}; for (var k in items) if (Object.prototype.hasOwnProperty.call(items, k)) o[k] = items[k]; return o; }

function reduce(s, a) {
  if (!a || !s || !s.items) return s;
  var items, changed = false, k, it, m;
  if (a.type === 'mark') {
    if (VIA.indexOf(a.via) < 0 || !Array.isArray(a.screens)) return s;
    items = copy(s.items);
    a.screens.forEach(function (sc) {
      if (!sc || typeof sc.id !== 'string' || !sc.id || typeof sc.file !== 'string' || !sc.file) return;
      items[sc.id] = {via: a.via, since: num(a.now) ? a.now : 0, file: sc.file, mtime: null};
      changed = true;
    });
    return changed ? {v: 1, items: items} : s;
  }
  if (a.type === 'baseline' || a.type === 'seen') {
    m = a.mtimes || {}; items = copy(s.items);
    for (k in items) {
      it = items[k];
      if (!Object.prototype.hasOwnProperty.call(m, it.file) || !num(m[it.file])) continue;
      if (a.type === 'baseline' && it.mtime == null) {
        items[k] = {via: it.via, since: it.since, file: it.file, mtime: m[it.file]}; changed = true;
      } else if (a.type === 'seen' && num(it.mtime) && m[it.file] > it.mtime) {
        delete items[k]; changed = true;
      }
    }
    return changed ? {v: 1, items: items} : s;
  }
  if (a.type === 'lift') {
    if (!Object.prototype.hasOwnProperty.call(s.items, a.id)) return s;
    items = copy(s.items); delete items[a.id];
    return {v: 1, items: items};
  }
  return s;
}

function load(getItem, key) {
  var raw, d, items = {}, k, it;
  try { raw = getItem(key); d = raw ? JSON.parse(raw) : null; } catch (e) { return initial(); }
  if (!d || typeof d !== 'object' || d.v !== 1 || !d.items || typeof d.items !== 'object' || Array.isArray(d.items)) return initial();
  for (k in d.items) {
    if (!Object.prototype.hasOwnProperty.call(d.items, k)) continue;
    it = d.items[k];
    if (!it || VIA.indexOf(it.via) < 0 || typeof it.file !== 'string' || !it.file) continue;
    items[k] = {via: it.via, since: num(it.since) ? it.since : 0, file: it.file, mtime: num(it.mtime) ? it.mtime : null};
  }
  return {v: 1, items: items};
}
function save(s, setItem, key) {
  try { setItem(key, JSON.stringify(s)); } catch (e) { /* 저장소가 막혀도 판은 그대로 */ }
}
function files(s) {
  var out = [], k;
  for (k in (s && s.items) || {}) if (out.indexOf(s.items[k].file) < 0) out.push(s.items[k].file);
  return out;
}

HD.busy = {initial: initial, reduce: reduce, load: load, save: save, files: files};
})();
