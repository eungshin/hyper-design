/* Model — 숨긴·잠근 화면 표시 정리(polish-1): 저장된 id 목록을 지금 있는 화면 + 판 글 레이어에 맞춰 거르고 다시 쓸지 알린다. DOM·저장소·메시지를 쓰지 않는다.
   저장 키·형식은 셸 그대로(`hd-hidden:<hash>` · `hd-locked:<hash>` = id 의 JSON 배열) — 읽기·쓰기는 셸이, 거르기 규칙만 여기.
   HD.layerFlags = {BOARD, live(rows, notes) → 지금 있는 id 목록(화면 · 메모의 빈 레이아웃 · 판 글),
                    clean(text, live) → {ids, set, dropped, changed, bad}(changed = 셸이 ids 를 다시 써야 함 · bad = 깨진 저장값)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var BOARD = ['@intro', '@foot', '@dscard'];          // 판 글도 레이어(H7) — 화면 목록에 없어도 늘 있음

function live(rows, notes) {
  var ids = [];
  (Array.isArray(rows) ? rows : []).forEach(function (r) {
    (r && Array.isArray(r.screens) ? r.screens : []).forEach(function (s) { if (s && typeof s.id === 'string') ids.push(s.id); });
  });
  (Array.isArray(notes) ? notes : []).forEach(function (n) { if (n && n.edit === 'new-screen' && typeof n.screen === 'string') ids.push(n.screen); });
  return ids.concat(BOARD);
}

function clean(text, liveIds) {
  if (text == null) return {ids: [], set: {}, dropped: [], changed: false, bad: false};
  var raw;
  try { raw = JSON.parse(text); } catch (e) { raw = undefined; }
  if (!Array.isArray(raw)) return {ids: [], set: {}, dropped: [], changed: true, bad: true};
  var ok = {}, set = {}, ids = [], dropped = [], changed = false;
  (Array.isArray(liveIds) ? liveIds : []).concat(BOARD).forEach(function (id) { ok[id] = 1; });
  raw.forEach(function (id) {
    if (typeof id !== 'string' || !id || set[id]) { changed = true; return; }
    if (!ok[id]) { dropped.push(id); changed = true; return; }
    set[id] = 1; ids.push(id);
  });
  return {ids: ids, set: set, dropped: dropped, changed: changed, bad: false};
}

HD.layerFlags = {BOARD: BOARD, live: live, clean: clean};
})();
