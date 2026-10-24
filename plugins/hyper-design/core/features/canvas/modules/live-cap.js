/* Model — 판 위 라이브 카드 상한: 어떤 카드를 내릴지(화면 밖 오래·상한 넘음) 고른다. DOM·타이머를 쓰지 않는다.
   unload({loaded, visible, lastSeen, selected, modal, now, K, idle}) → 내릴 카드 id 목록(오래 안 본 것부터)
     loaded = 지금 실린 카드 id · visible = 지금 보이는 id · lastSeen = {id: 마지막으로 보인 ms} · selected = 고른 id · modal = 크게 보기 화면 id|null
     보이는·고른·크게 보기 카드는 내리지 않는다. 화면 밖이 idle ms 넘은 것만, 실린 수가 K 이하가 될 때까지만.
   HD.liveCap = {K, IDLE, unload}  (K·IDLE 은 셸이 부를 때마다 읽는다 — 테스트가 바꿀 수 있다) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function unload(o) {
  var loaded = o.loaded || [], K = o.K >= 0 ? o.K : HD.liveCap.K, idle = o.idle >= 0 ? o.idle : HD.liveCap.IDLE;
  var extra = loaded.length - K;
  if (extra <= 0) return [];
  var keep = {}, seen = o.lastSeen || {};
  (o.visible || []).concat(o.selected || []).forEach(function (id) { keep[id] = 1; });
  if (o.modal != null) keep[o.modal] = 1;
  var at = function (id) { return seen[id] || 0; };
  return loaded.filter(function (id) { return !keep[id] && o.now - at(id) >= idle; })
    .map(function (id, i) { return {id: id, i: i}; })
    .sort(function (a, b) { return at(a.id) - at(b.id) || a.i - b.i; })
    .slice(0, extra).map(function (x) { return x.id; });
}

HD.liveCap = {K: 10, IDLE: 15000, unload: unload};
})();
