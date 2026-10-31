/* Model — 부품 쓰는 화면 지도 읽기(R58): hd-data usage {key: [화면 id]} 검사 · 수 · 칩·막대 글 · 문서 탭 칩 메시지. 상태 없음, DOM 없음.
   read(raw, ids) → {map, bad, unknown} — raw 없음(앱 프로젝트·옛 데이터) = 빈 지도·경고 없음 · 모양이 깨짐(객체 아님·값이 글 목록 아님) = 빈 지도 + bad(까닭) ·
     판에 없는 id = 빼고 unknown 에(빈 key 는 빠짐). count(map, key) → 수 · label(n) → '쓰는 화면 N' · bar(title, n) → '버튼 · 쓰는 화면 N' ·
   showMsg(d) → {key, title} | null — components.html 칩이 보낸 hd-usage-show(key = 낱말 하나). 빌드 쪽 같은 규칙 = usage_map.py. 계약 contract/usage-map.md */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEY = /^[\w-]{1,64}$/;

function read(raw, ids) {
  var empty = function (why) { return {map: {}, bad: why || null, unknown: []}; };
  if (raw == null) return empty(null);
  if (typeof raw !== 'object' || Array.isArray(raw)) return empty('usage 가 객체가 아니에요');
  var have = {}, map = {}, unknown = [];
  (ids || []).forEach(function (id) { have[id] = true; });
  var keys = Object.keys(raw);
  for (var i = 0; i < keys.length; i++) {
    var v = raw[keys[i]];
    if (!Array.isArray(v) || v.some(function (x) { return typeof x !== 'string'; })) return empty('usage.' + keys[i] + ' 가 화면 id 목록이 아니에요');
    var ok = v.filter(function (id) { if (have[id]) return true; if (unknown.indexOf(id) < 0) unknown.push(id); return false; });
    if (ok.length) map[keys[i]] = ok;
  }
  return {map: map, bad: null, unknown: unknown};
}

function count(map, key) { return map && Array.isArray(map[key]) ? map[key].length : 0; }
function label(n) { return '쓰는 화면 ' + n; }
function bar(title, n) { return title + ' · ' + label(n); }

function showMsg(d) {
  if (!d || typeof d !== 'object' || d.type !== 'hd-usage-show' || typeof d.key !== 'string' || !KEY.test(d.key)) return null;
  return {key: d.key, title: typeof d.title === 'string' ? d.title.trim() : ''};
}

HD.usage = {read: read, count: count, label: label, bar: bar, showMsg: showMsg};
})();
