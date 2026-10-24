/* Model — 완료 메모 보관 고르기(#273): 상태 파일이 2 MB 를 넘지 않게 오래된·넘친 완료 메모를 고르고, 보관한 뒤 목록에서 뺄 것을 정한다. DOM·저장소·메시지를 쓰지 않는다.
   완료(done) = HD.annotation.status. 끝난 시각 = 마지막 답의 at(ISO). 보내기 전·AI 작업 중·결정 필요·일부 반영은 절대 고르지 않는다. id 없는 메모도(뺄 수 없다).
   pickArchive(notes, now, status?) → [메모](목록 차례) — 끝난 지 KEEP_DAYS 일 넘은 완료 + 완료가 KEEP_DONE 개를 넘으면 가장 오래 전에 끝난 것부터(시각 모름 = 가장 오래됨) 넘친 것
   without(notes, archived) → 새 목록 — 보관한 것과 id·내용이 그대로 같은 메모만 뺀다(그 사이 다시 연 메모는 남긴다)
   HD.archive = {KEEP_DAYS, KEEP_DONE, pickArchive, without} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var KEEP_DAYS = 30, KEEP_DONE = 200, DAY = 86400000;

function doneAt(n) {
  var r = Array.isArray(n.replies) && n.replies.length ? n.replies[n.replies.length - 1] : null;
  var t = r && typeof r.at === 'string' ? Date.parse(r.at) : NaN;
  return isFinite(t) ? t : NaN;
}
function hasId(n) { return typeof n.id === 'string' || typeof n.id === 'number'; }

function pickArchive(notes, now, status) {
  if (!Array.isArray(notes)) return [];
  status = status || (HD.annotation && HD.annotation.status);
  if (typeof status !== 'function') return [];
  var done = [];
  notes.forEach(function (n, i) {
    if (n && typeof n === 'object' && hasId(n) && status(n) === 'done') done.push({n: n, i: i, at: doneAt(n)});
  });
  var pick = {};
  done.forEach(function (d) { if (isFinite(d.at) && now - d.at > KEEP_DAYS * DAY) pick[d.i] = 1; });
  if (done.length > KEEP_DONE) {
    var order = done.slice().sort(function (a, b) {          // 새것 먼저 — 시각 모름은 맨 뒤(가장 오래됨), 같으면 목록 뒤쪽이 새것
      var x = isFinite(a.at) ? a.at : -Infinity, y = isFinite(b.at) ? b.at : -Infinity;
      return y - x || b.i - a.i;
    });
    order.slice(KEEP_DONE).forEach(function (d) { pick[d.i] = 1; });
  }
  return done.filter(function (d) { return pick[d.i]; }).map(function (d) { return d.n; });
}

function without(notes, archived) {
  var gone = {};
  (archived || []).forEach(function (n) { if (n && hasId(n)) gone[typeof n.id + ':' + n.id] = JSON.stringify(n); });
  return (Array.isArray(notes) ? notes : []).filter(function (n) {
    return !(n && hasId(n) && gone[typeof n.id + ':' + n.id] === JSON.stringify(n));
  });
}

HD.archive = {KEEP_DAYS: KEEP_DAYS, KEEP_DONE: KEEP_DONE, pickArchive: pickArchive, without: without};
})();
