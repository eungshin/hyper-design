/* View — 판 위 요소 테두리: 마우스를 올린 카드 안 요소(도구마다 tools.hoverOf)를 화면에 물어 종류별 테두리, 고른 요소(테두리 고정 + 소켓 + 부모 점선 + 요소 막대).
   묻기 = ctx.ask·chain(view-frame-ask), 부모 고르기 = HD.blocks.parentPick, 색·꼬리표 = HD.blocks.tone · HD.tools.LABEL.
   HD.viewElbox.mount(ctx) → {clear()(미리 그린 테두리 걷기), selected() → 고른 요소 {card, h}|null, select(card, h), unselect(), pickAt(card, x, y, deep?)}
   ctx = {$, $$, rowsEl, pane, wOf(card), tagScale(), zoom(), app(id) → 앱 카드인가, title(id), toast(msg), ask(card, x, y, quiet, cb, leaf, deep), chain(frame, h, cb),
          lastFrame(card), blocks() → 요소 막대(BK)|null, tool() → 지금 도구, only(id) → 그 카드만 골랐나, busy() → 끄는 중·도착 고르는 중} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, rowsEl = ctx.rowsEl, pane = ctx.pane, hov = {busy: false, next: null, card: null}, selEl = null;

  function rectOf(el) { var r = el.getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; }
  function clear() { $$('.elbox:not(.sel):not(.par)', rowsEl).forEach(function (b) { b.remove(); }); hov.card = null; }
  function unselect() { $$('.elbox.sel, .elbox.par, .sock.selsock', rowsEl).forEach(function (n) { n.remove(); }); selEl = null; var BK = ctx.blocks(); if (BK) BK.hide('board'); }
  function draw(card, h, how) {                      // how: 'hov' = 다음 클릭이 고를 요소(얇은 실선, 51-3) · 'par' = 고른 요소의 부모(점선) · 없음 = 요소 도구 테두리
    if (how !== 'par') clear();
    if (!h || h.none || !h.rect) return;
    var ph = $('.phone', card), sc = ph.offsetWidth / ctx.wOf(card), ts = ctx.tagScale(), q = h.rect, b = document.createElement('div');
    b.className = 'elbox' + (q.y * sc < 18 * ts ? ' in' : '') + (how ? ' ' + how : '');
    b.dataset.kind = h.kind || 'box';
    var tn = HD.blocks.tone(h, {app: ctx.app(card.dataset.id)}); if (tn) b.dataset.tone = tn;   // 앱 카드 = 요청으로만 색·꼬리표(51-3)
    b.dataset.label = (HD.tools.LABEL[h.kind] || '영역') + (h.kind === 'link' && h.to ? ' → ' + ctx.title(h.to) : '');
    b.style.left = q.x * sc + 'px'; b.style.top = q.y * sc + 'px'; b.style.width = q.w * sc + 'px'; b.style.height = q.h * sc + 'px';
    b.style.borderWidth = ((how ? 1 : 2) * ts) + 'px'; b.style.setProperty('--ts', ts);
    ph.appendChild(b); if (how !== 'par') hov.card = card;
  }
  // 고른 요소의 부모 점선(51-3, Figma F11): 화면에 조상을 묻고(hd-up) 상자가 다른 첫 조상(blocks.parentPick — [상위] 와 같은 판정)
  function drawParent(card, h) {
    ctx.chain(ctx.lastFrame(card), h, function (chain) {
      if (!selEl || selEl.card !== card || selEl.h !== h || !chain) return;   // 그 사이 다른 요소를 골랐다
      var p = HD.blocks.parentPick(h, chain); if (p) draw(card, p, 'par');
    });
  }
  function select(card, h) {
    unselect(); clear(); draw(card, h);
    var b = $('.elbox:not(.sel):not(.par)', card); if (!b) return;
    b.classList.add('sel'); hov.card = null;
    var ph = $('.phone', card), sc = ph.offsetWidth / ctx.wOf(card), ts = ctx.tagScale(), q = h.rect, sk = document.createElement('span'), d = 16 * ts;
    sk.className = 'sock selsock'; sk.title = '끌어서 다른 화면에 놓으면 연결';
    sk.style.left = ((q.x + q.w) * sc) + 'px'; sk.style.top = ((q.y + q.h / 2) * sc) + 'px';
    sk.style.width = sk.style.height = d + 'px'; sk.style.margin = (-d / 2) + 'px 0 0 ' + (-d / 2) + 'px'; sk.style.borderWidth = (2 * ts) + 'px';
    ph.appendChild(sk); selEl = {card: card, h: h}; drawParent(card, h);
    var BK = ctx.blocks();
    if (BK) BK.show({screen: card.dataset.id, h: h, app: ctx.app(card.dataset.id), where: 'board',   // 요소 막대(task 49a) — 고른 테두리 옆, 판이 움직이면 placeSelbar 가 다시 놓는다
                     frame: function () { var fs = $$('.phone iframe', card); return fs[fs.length - 1] || null; }, view: function () { return rectOf(pane); },   // 상위 묻기 · 판 칸 안에(task 49b)
                     anchor: function () { var bx = $('.elbox.sel', card); if (!bx || !card.isConnected) return null; var r = bx.getBoundingClientRect(), lb = bx.classList.contains('in') ? 0 : 17 * ctx.tagScale() * ctx.zoom(); return {x: r.left, y: r.top - lb, w: r.width, h: r.height + lb}; }});   // lb = 테두리 위 종류 꼬리표를 덮지 않게
  }
  function pickAt(card, x, y, deep) {                // 선택(V)으로 고른 카드를 한 번 더 = 그 자리 요소 고르기(누를 수 있는 요소 → 그 요소, 트리거 도구와 같은 규칙) · deep = 가장 안쪽 요소(Alt+클릭, 51-2)
    ctx.ask(card, x, y, false, function (h) {
      if (!h) return;
      if (h.none) { ctx.toast('여기에는 고를 요소가 없어요'); return; }
      select(card, h);
    }, false, deep);
  }
  function hoverMode(card) {                          // 그 카드 위에서 미리 그릴 방식(tools.hoverOf) — 선택(V)은 그 카드만 골랐을 때(다음 클릭 = 요소 고르기, 51-3)
    return HD.tools.hoverOf(ctx.tool(), {only: ctx.only(card.dataset.id), typing: card.classList.contains('hd-typing')});
  }
  function hoverAsk(card, x, y, deep) {              // 한 번에 하나만 묻고, 그 사이 움직임은 마지막 자리만 기억 · deep = Alt(가장 안쪽 — 이동 도구의 Alt+클릭과 같게)
    var mode = hoverMode(card); if (!mode) return;
    if (hov.busy) { hov.next = [card, x, y, deep]; return; }
    hov.busy = true;
    ctx.ask(card, x, y, true, function (h) {
      hov.busy = false;
      var mv = ctx.tool() === 'move';
      if (hov.live === card && hoverMode(card) && !ctx.busy()) {
        if (mv && h && selEl && selEl.card === card && h.path === selEl.h.path) clear();   // 고른 요소 위 = 이미 고른 상자
        else draw(card, h, mv ? 'hov' : undefined);
      }
      var n = hov.next; hov.next = null; if (n) hoverAsk(n[0], n[1], n[2], n[3]);
    }, mode === 'leaf', ctx.tool() === 'move' && !!deep);
  }
  function hoverOff() { hov.live = null; hov.next = null; if (hov.card) clear(); }

  pane.addEventListener('mousemove', function (e) {
    if (ctx.busy()) { hoverOff(); return; }
    var c = e.target.closest ? e.target.closest('.card:not(.draft)') : null, ph = c ? $('.phone', c) : null;
    if (!ph || !ph.contains(e.target) || e.target.closest('.sock') || !hoverMode(c)) { hoverOff(); return; }
    if (hov.card && hov.card !== c) clear();
    hov.live = c; hoverAsk(c, e.clientX, e.clientY, e.altKey);
  });
  pane.addEventListener('mouseleave', hoverOff);     // 판 밖으로 = 미리 표시 걷기(늦게 온 답도 그리지 않게 hov.live)

  return {clear: clear, selected: function () { return selEl; }, select: select, unselect: unselect, pickAt: pickAt};
}

HD.viewElbox = {mount: mount};
})();
