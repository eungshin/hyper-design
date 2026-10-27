/* Model — 앱 부품 '낡음' 표시 규칙(R30): 도우미 GET /api/app-parts 답 → 카드마다 칩 모양. DOM·저장소·메시지를 쓰지 않는다.
   답 = {parts: [{file, state, stale, dirty, label, …}], stale: [화면 id]} — 낡음 판단은 도우미(part_stamp.py)가 하고 여기서는 보이는 글만 정한다.
   HD.parts = {EVERY: 60000(ms — 다시 묻는 간격, 도우미도 60초 캐시), TEXT: '낡음', marks(body) → {화면 id: {text, title}}, same(a, b) → bool}
   모양이 틀린 답(도우미가 옛것 · 오류)은 {} — 표시 없음(부르는 쪽이 [hd] 경고). */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var EVERY = 60000, TEXT = '낡음', MAX_FILES = 3;

function staleFiles(parts) {
  return (Array.isArray(parts) ? parts : []).filter(function (p) { return p && p.stale === true && typeof p.file === 'string'; })
    .map(function (p) { return p.file + (p.dirty ? ' (미커밋 변경 포함)' : ''); });
}

function marks(body) {
  if (!body || typeof body !== 'object' || !Array.isArray(body.stale)) return {};
  var files = staleFiles(body.parts), out = {};
  var list = files.slice(0, MAX_FILES).join(', ') + (files.length > MAX_FILES ? ' 외 ' + (files.length - MAX_FILES) + '개' : '');
  var title = '이 화면이 끌어 쓰는 앱 부품이 앱 소스보다 옛것이에요' + (list ? ': ' + list : '') + ' — 터미널에서 hd parts --rebuild';
  body.stale.forEach(function (id) {
    if (typeof id === 'string' && id) out[id] = {text: TEXT, title: title};
  });
  return out;
}

function same(a, b) {
  var ka = Object.keys(a || {}).sort(), kb = Object.keys(b || {}).sort();
  if (ka.join('\n') !== kb.join('\n')) return false;
  return ka.every(function (k) { return a[k].text === b[k].text && a[k].title === b[k].title; });
}

HD.parts = {EVERY: EVERY, TEXT: TEXT, marks: marks, same: same};
})();
