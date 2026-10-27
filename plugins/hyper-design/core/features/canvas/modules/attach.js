/* Model — 첨부 이미지 규칙(R22): 붙일 수 있나(종류·크기) · 칩 목록 더하기·빼기·저장됨 · 요청 글의 '첨부 이미지: <절대 경로>' 줄 넣기·걷기. DOM·저장소·메시지를 쓰지 않는다.
   칩 = {id, name, type, size, url(미리보기), state:'up'|'ok', path?, rel?} — 목록은 늘 새 배열(받은 것을 바꾸지 않음).
   check({type, size}) → null | 이유(한국어 한 줄) · add(list, item) → {list, why} (COUNT 넘으면 why) · done(list, id, res{path, rel, type, size}) · remove(list, id)
   busy(list) → 올리는 중인 수 · saved(list) → [{path, rel, type, size, name}](메모에 남기는 모양) · fromSaved(items) → 칩(state ok, id = rel)
   lines(saved) → '첨부 이미지: <path>' 줄들 · strip(text) → 그 줄을 걷은 글 · withText(text, saved) → strip 뒤 줄 붙이기(고쳐 저장해도 한 번만)
   paths(text) → 요청문(들여 쓴 줄 포함)의 '첨부 이미지:' 경로들(같은 것 한 번, COUNT 장까지) — /api/forward 의 images(R28, 서버가 paseo send --image 로)
   서버 쪽 같은 말·한도는 attach_rules.py(LINE · MAX_BYTES) — 둘을 같이 고친다 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var LINE = '첨부 이미지: ';
var TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'];
var MAX = 10 * 1024 * 1024, COUNT = 6;

function check(f) {
  if (!f) return '붙일 파일이 없어요';
  if (TYPES.indexOf(String(f.type || '').toLowerCase()) < 0) return 'PNG·JPEG·WebP·GIF 이미지만 붙일 수 있어요' + (f.name ? ' (' + f.name + ')' : '');
  if (!(f.size > 0)) return '빈 이미지예요';
  if (f.size > MAX) return '이미지가 너무 커요(' + (f.size / 1024 / 1024).toFixed(1) + ' MB) — ' + MAX / 1024 / 1024 + ' MB 까지 붙일 수 있어요';
  return null;
}
function add(list, item) {
  list = (list || []).slice();
  if (list.length >= COUNT) return {list: list, why: '이미지는 한 번에 ' + COUNT + '장까지 붙일 수 있어요'};
  list.push({id: item.id, name: item.name || '', type: item.type || '', size: item.size || 0, url: item.url || '', state: 'up'});
  return {list: list, why: ''};
}
function done(list, id, res) {
  return (list || []).map(function (c) {
    if (c.id !== id || !res) return c;
    return {id: c.id, name: c.name, type: res.type || c.type, size: res.size || c.size, url: c.url, state: 'ok', path: String(res.path || ''), rel: String(res.rel || '')};
  });
}
function remove(list, id) { return (list || []).filter(function (c) { return c.id !== id; }); }
function busy(list) { return (list || []).filter(function (c) { return c.state === 'up'; }).length; }
function saved(list) {
  return (list || []).filter(function (c) { return c.state === 'ok' && c.path; })
    .map(function (c) { return {path: c.path, rel: c.rel || '', type: c.type || '', size: c.size || 0, name: c.name || ''}; });
}
function fromSaved(items) {
  return (Array.isArray(items) ? items : []).filter(function (x) { return x && typeof x.path === 'string' && x.path; })
    .map(function (x) { return {id: x.rel || x.path, name: x.name || '', type: x.type || '', size: x.size || 0, url: '', state: 'ok', path: x.path, rel: x.rel || ''}; });
}
function lines(items) { return (items || []).map(function (x) { return LINE + x.path; }).join('\n'); }
function strip(text) {
  return String(text == null ? '' : text).split('\n').filter(function (l) { return l.indexOf(LINE) !== 0; }).join('\n').replace(/\s+$/, '');
}
function paths(text) {
  var head = LINE.trim(), out = [];
  String(text == null ? '' : text).split('\n').forEach(function (l) {
    var s = l.trim();
    if (s.indexOf(head) !== 0) return;
    var p = s.slice(head.length).trim();
    if (p && out.indexOf(p) < 0 && out.length < COUNT) out.push(p);
  });
  return out;
}
function withText(text, items) {
  var t = strip(text), l = lines(items);
  return l ? (t ? t + '\n' + l : l) : t;
}

HD.attach = {LINE: LINE, TYPES: TYPES, MAX: MAX, COUNT: COUNT, check: check, add: add, done: done, remove: remove, busy: busy,
             saved: saved, fromSaved: fromSaved, lines: lines, strip: strip, withText: withText, paths: paths};
})();
