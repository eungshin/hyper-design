/* Model — 판 위 라이브 카드 상한: 어떤 카드를 싣고 내릴지(읽히는 크기·화면 밖 오래·상한 넘음) 고른다. DOM·타이머를 쓰지 않는다.
   readable(w, minW) → 카드의 화면 위 너비 w(px)가 읽히는 크기(minW, 기본 MINW = 48 — 점처럼 작을 때만: 76px 에서 빈 흰 상자는 Figma·Stitch 의 축소 미리보기와 달라 윤곽을 잃는다, 미리보기 그림이 생기면 올린다)인가 — 아니면 iframe 을 싣지 않는다(LOD, Figma 처럼 틀·제목·흰 바탕만)
     배율이 아니라 화면 위 너비로 본다 — 크기를 바꾼 카드(task 46)도 같은 규칙. 숫자가 아니면 읽힌다로 본다(모르면 지금처럼 싣기)
   unload({loaded, visible, small, lastSeen, selected, modal, now, K, idle}) → 내릴 카드 id 목록(작은 것 먼저, 그다음 오래 안 본 것부터)
     loaded = 지금 실린 카드 id · visible = 지금 보이는 id · small = 보이지만 읽히지 않는 크기인 id · lastSeen = {id: 마지막으로 보인 ms} · selected = 고른 id · modal = 크게 보기 화면 id|null
     고른·크게 보기 카드는 내리지 않는다. small 은 바로 내린다(상한·idle 무관). 나머지는 보이는 것은 두고, 화면 밖이 idle ms 넘은 것만, 실린 수가 K 이하가 될 때까지만.
   HD.liveCap = {K, IDLE, MINW, readable, unload}  (K·IDLE·MINW 는 셸이 부를 때마다 읽는다 — 테스트가 바꿀 수 있다) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function readable(w, minW) {
  var m = minW >= 0 ? minW : HD.liveCap.MINW;
  return typeof w !== 'number' || isNaN(w) || w >= m;
}

function unload(o) {
  var loaded = o.loaded || [], K = o.K >= 0 ? o.K : HD.liveCap.K, idle = o.idle >= 0 ? o.idle : HD.liveCap.IDLE;
  var pin = {}, keep = {}, small = {}, seen = o.lastSeen || {};
  (o.selected || []).forEach(function (id) { pin[id] = 1; });
  if (o.modal != null) pin[o.modal] = 1;
  (o.small || []).forEach(function (id) { if (!pin[id]) small[id] = 1; });
  var tiny = loaded.filter(function (id) { return small[id]; });
  var rest = loaded.filter(function (id) { return !small[id]; });
  var extra = rest.length - K;
  if (extra <= 0) return tiny;
  (o.visible || []).forEach(function (id) { keep[id] = 1; });
  var at = function (id) { return seen[id] || 0; };
  return tiny.concat(rest.filter(function (id) { return !keep[id] && !pin[id] && o.now - at(id) >= idle; })
    .map(function (id, i) { return {id: id, i: i}; })
    .sort(function (a, b) { return at(a.id) - at(b.id) || a.i - b.i; })
    .slice(0, extra).map(function (x) { return x.id; }));
}

HD.liveCap = {K: 10, IDLE: 15000, MINW: 48, readable: readable, unload: unload};
})();
