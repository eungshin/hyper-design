/* View — 판 카드 iframe 싣기·내리기: 보이고 읽히는 크기인 카드만 싣고(이동·확대 뒤 100ms 묶어서 · 5초마다) 고르는 규칙(LOD·화면 밖 오래·상한)은 Model HD.liveCap.
   HD.viewLiveCap.mount(ctx) → {load(frame)(그 카드 iframe 을 지금 싣기 — 판 모드 주소), visible()(지금 한 번 고르기), schedule()(100ms 뒤 한 번)}
   ctx = {$, $$, pane, rowsEl, selected() → 고른 id(고르기가 붙기 전 = []), modalScreen() → 크게 보기 화면 id|null, loaded(id|null, frame)(카드 iframe 이 실림 — 테마·반영 대기·메모 자리)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, pane = ctx.pane, visT = 0, seenAt = {};

  function load(f) { var s = f.getAttribute('data-src'); f.dataset.live = s; f.removeAttribute('data-src'); f.src = HD.swap.boardUrl(s); }   // 판 위 카드 = 판 모드(palette.js 가 움직임을 멈춤) — 크게 보기(#mframe)는 붙이지 않는다
  function visible() {
    var pr = pane.getBoundingClientRect();
    if (!pr.width || pane.hidden) return;
    var now = Date.now(), loaded = [], vis = [], small = [], frames = {}, sel = ctx.selected(), mid = ctx.modalScreen();
    $$('.card', ctx.rowsEl).forEach(function (c) {
      var f = $('.phone iframe', c); if (!f) return;
      var id = c.dataset.id, r = f.parentNode.getBoundingClientRect();
      if (HD.liveCap.near(r, pr)) {                 // 판 칸 + 여유 80px 안
        vis.push(id); seenAt[id] = now;
        var tiny = !HD.liveCap.readable(r.width);     // LOD: 읽히지 않는 크기면 싣지 않는다(틀·제목·흰 바탕) — 고른·크게 보기 카드는 싣는다
        if (tiny) small.push(id);
        if (f.hasAttribute('data-src') && (!tiny || sel.indexOf(id) >= 0 || id === mid)) {
          if (!f.dataset.wired) {                   // 다시 실을 때(data-src 다시 붙임)마다 듣는 이를 더하지 않는다 — 실을 때마다 메시지 한 번
            f.dataset.wired = '1';
            f.addEventListener('load', function () { if (f.hasAttribute('data-src')) return;   // 내린 카드(about:blank)
              var c = f.closest('.card'); ctx.loaded(c ? c.dataset.id : null, f); });   // 메모 자리 다시 찾기(hd-locate)
          }
          load(f);
        }
      }
      if (!f.hasAttribute('data-src') && f.dataset.live) { loaded.push(id); frames[id] = f; }
    });
    HD.liveCap.unload({loaded: loaded, visible: vis, small: small, lastSeen: seenAt, selected: sel, modal: mid, now: now,
                       K: HD.liveCap.K, idle: HD.liveCap.IDLE})
      .forEach(function (id) { var f = frames[id]; f.setAttribute('data-src', f.dataset.live); f.src = 'about:blank'; });   // 내리기 = 틀·제목·핀은 그대로, 다시 보이면 위에서 다시 싣는다
  }
  function schedule() { clearTimeout(visT); visT = setTimeout(visible, 100); }

  addEventListener('resize', schedule);
  setInterval(visible, 5000);                         // 가만히 있어도 화면 밖 15초 지난 카드를 내린다

  return {load: load, visible: visible, schedule: schedule};
}

HD.viewLiveCap = {mount: mount};
})();
