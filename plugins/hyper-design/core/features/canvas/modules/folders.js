/* Model — 레이어 패널의 사용자 폴더 상태(패널에서만 묶음, 판 카드는 옮기지 않음). DOM·저장소를 쓰지 않는다(저장은 넘겨받은 getItem/setItem 으로).
   상태 = {v: 1, folders: [{id: 'f<n>', name, ids: [화면 id], open: bool}]} — 한 화면은 많아야 한 폴더, 순서 = 배열 순(새 폴더가 맨 앞)
   reduce(state, a) → 새 상태(바뀐 게 없으면 같은 객체):
     create{ids, name?}  새 폴더(id = 'f' + (가장 큰 번호 + 1), 이름 기본 '새 폴더 ' + 그 번호) · ids 는 다른 폴더에서 빼 옴 · 빈 ids 도 됨
     rename{id, name}    앞뒤 빈칸 정리, 비면 그대로
     remove{id}          폴더 지우기(화면은 데이터 줄로 돌아감)
     add{id, ids}        폴더로 옮기기(다른 폴더에서 빼 옴)
     take{ids}           어느 폴더에서든 빼기
     fold{id, open}      접기·펴기
     prune{live}         없는 화면 id 지우기(빈 폴더는 남김)
   load(getItem, key) → 상태(깨졌으면 initial()) · save(state, setItem, key) 던지지 않음 · of(state, 화면 id) → 폴더 id | null
   HD.folders = {initial, reduce, load, save, of} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function initial() { return {v: 1, folders: []}; }
function str(x) { return typeof x === 'string' && x.length > 0; }
// 겹치지 않는 문자열 id 목록
function uniq(ids) {
  var out = [];
  (Array.isArray(ids) ? ids : []).forEach(function (id) { if (str(id) && out.indexOf(id) < 0) out.push(id); });
  return out;
}
function num(id) { var m = /^f(\d+)$/.exec(id); return m ? parseInt(m[1], 10) : 0; }
function find(s, id) { for (var i = 0; i < s.folders.length; i++) if (s.folders[i].id === id) return i; return -1; }
function folder(f, o) { return {id: f.id, name: o.name != null ? o.name : f.name, ids: o.ids || f.ids, open: o.open != null ? o.open : f.open}; }
// 모든 폴더에서 ids 빼기(skip 폴더는 건드리지 않음) → [새 폴더 배열, 바뀜?]
function without(folders, ids, skip) {
  var changed = false;
  var out = folders.map(function (f) {
    if (f.id === skip) return f;
    var rest = f.ids.filter(function (x) { return ids.indexOf(x) < 0; });
    if (rest.length === f.ids.length) return f;
    changed = true;
    return folder(f, {ids: rest});
  });
  return [out, changed];
}

function reduce(s, a) {
  if (!a || !s || !Array.isArray(s.folders)) return s;
  var ids, i, f, r, name, n;
  if (a.type === 'create') {
    ids = uniq(a.ids);
    n = 1; s.folders.forEach(function (x) { n = Math.max(n, num(x.id) + 1); });
    name = typeof a.name === 'string' ? a.name.trim() : '';
    r = without(s.folders, ids, null);
    return {v: 1, folders: [{id: 'f' + n, name: name || '새 폴더 ' + n, ids: ids, open: true}].concat(r[0])};
  }
  if (a.type === 'rename') {
    i = find(s, a.id); name = typeof a.name === 'string' ? a.name.trim() : '';
    if (i < 0 || !name || name === s.folders[i].name) return s;
    r = s.folders.slice(); r[i] = folder(r[i], {name: name});
    return {v: 1, folders: r};
  }
  if (a.type === 'remove') {
    i = find(s, a.id);
    if (i < 0) return s;
    r = s.folders.slice(); r.splice(i, 1);
    return {v: 1, folders: r};
  }
  if (a.type === 'add') {
    i = find(s, a.id);
    if (i < 0) return s;
    f = s.folders[i];
    ids = uniq(a.ids).filter(function (x) { return f.ids.indexOf(x) < 0; });
    if (!ids.length) return s;
    r = without(s.folders, ids, f.id)[0];
    r[i] = folder(f, {ids: f.ids.concat(ids)});
    return {v: 1, folders: r};
  }
  if (a.type === 'take') {
    r = without(s.folders, uniq(a.ids), null);
    return r[1] ? {v: 1, folders: r[0]} : s;
  }
  if (a.type === 'fold') {
    i = find(s, a.id);
    if (i < 0 || !!a.open === s.folders[i].open) return s;
    r = s.folders.slice(); r[i] = folder(r[i], {open: !!a.open});
    return {v: 1, folders: r};
  }
  if (a.type === 'prune') {
    var live = uniq(a.live), changed = false;
    r = s.folders.map(function (x) {
      var keep = x.ids.filter(function (id) { return live.indexOf(id) >= 0; });
      if (keep.length === x.ids.length) return x;
      changed = true;
      return folder(x, {ids: keep});
    });
    return changed ? {v: 1, folders: r} : s;
  }
  return s;
}

function load(getItem, key) {
  var raw, d, out = [], seenF = [], seenS = [];
  try { raw = getItem(key); d = raw ? JSON.parse(raw) : null; } catch (e) { return initial(); }
  if (!d || typeof d !== 'object' || d.v !== 1 || !Array.isArray(d.folders)) return initial();
  d.folders.forEach(function (f) {
    if (!f || typeof f !== 'object' || !/^f\d+$/.test(f.id) || seenF.indexOf(f.id) >= 0) return;
    seenF.push(f.id);
    var ids = uniq(f.ids).filter(function (x) { return seenS.indexOf(x) < 0; });
    seenS = seenS.concat(ids);
    var name = typeof f.name === 'string' ? f.name.trim() : '';
    out.push({id: f.id, name: name || '새 폴더 ' + num(f.id), ids: ids, open: f.open !== false});
  });
  return {v: 1, folders: out};
}
function save(s, setItem, key) {
  try { setItem(key, JSON.stringify(s)); } catch (e) { /* 저장소가 막혀도 패널은 그대로 */ }
}
function of(s, id) {
  var fs = (s && s.folders) || [];
  for (var i = 0; i < fs.length; i++) if (fs[i].ids.indexOf(id) >= 0) return fs[i].id;
  return null;
}

HD.folders = {initial: initial, reduce: reduce, load: load, save: save, of: of};
})();
