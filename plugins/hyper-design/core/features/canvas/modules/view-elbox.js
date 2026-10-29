/* View — 판 위 요소 테두리: 마우스를 올린 카드 안 요소(도구마다 tools.hoverOf)를 화면에 물어 종류별 테두리, 고른 요소(테두리 고정 + 소켓 + 부모 점선 + 요소 막대).
   묻기 = ctx.ask·chain(view-frame-ask), 부모 고르기 = HD.blocks.parentPick, 색·꼬리표 = HD.blocks.tone · HD.tools.LABEL.
   여러 요소(R19): 고른 요소는 목록(규칙 HD.elPick) — 모두 테두리 고정, 소켓·부모 점선·요소 막대는 주인(마지막 것)만. Shift+누르기 = 더하기·빼기(셸이 add 로 부른다).
   HD.viewElbox.mount(ctx) → {clear()(미리 그린 테두리 걷기), selected() → 주인 {card, h}|null, all() → 고른 요소 모두 [{card, h}](고른 차례),
     select(card, h, pt?)(그 하나만), toggle(card, h, pt?)(더하기·빼기), unselect()(모두), keep(ok(cardId))(ok 인 카드의 것만 남김), pickAt(card, x, y, deep?, add?)}
   누른 자리(R51): pickAt(클릭)으로 고르면 그 자리를 카드 화면(.phone) 안 비율 pt {fx, fy} 로 고른 항목에 두고, 요소 막대에 pointer() → 지금 화면 좌표로 건넨다
     (판을 옮기거나 확대해도 따라감 — 막대 자리 규칙 HD.barPlace 가 큰 요소면 누른 자리 가까이). 메뉴·키보드·쓴 뒤 다시 고르기(select 에 pt 없음) = pointer 없음.
   ctx = {$, $$, rowsEl, pane, wOf(card), tagScale(), zoom(), app(id) → 앱 카드인가, title(id), toast(msg), ask(card, x, y, quiet, cb, leaf, deep), chain(frame, h, cb),
          lastFrame(card), blocks() → 요소 막대(BK)|null, tool() → 지금 도구, only(id) → 그 카드만 골랐나, busy() → 끄는 중·도착 고르는 중} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, rowsEl = ctx.rowsEl, pane = ctx.pane, hov = {busy: false, next: null, card: null}, sels = [], P = HD.elPick;

  function rectOf(el) { var r = el.getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; }
  function clear() { $$('.elbox:not(.sel):not(.par)', rowsEl).forEach(function (b) { b.remove(); }); hov.card = null; }
  function keyOf(s) { return s && s.card && s.h && s.h.path ? P.key(s.card.dataset.id, s.h.path) : ''; }
  function primary() { return P.primary(sels); }
  function wipe() { $$('.elbox.sel, .elbox.par, .sock.selsock', rowsEl).forEach(function (n) { n.remove(); }); }
  function unselect() { wipe(); sels = []; var BK = ctx.blocks(); if (BK) BK.hide('board'); }
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
      var pr = primary(); if (!pr || pr.card !== card || pr.h !== h || !chain) return;   // 그 사이 다른 요소를 골랐다
      var p = HD.blocks.parentPick(h, chain); if (p) draw(card, p, 'par');
    });
  }
  function outline(card, h, pri) {                   // 고른 테두리 하나(주인 = .pri + 소켓)
    draw(card, h);
    var b = $('.elbox:not(.sel):not(.par)', card); if (!b) return false;
    b.classList.add('sel'); if (pri) b.classList.add('pri'); b.dataset.key = P.key(card.dataset.id, h.path); hov.card = null;
    if (!pri) return true;
    var ph = $('.phone', card), sc = ph.offsetWidth / ctx.wOf(card), ts = ctx.tagScale(), q = h.rect, sk = document.createElement('span'), d = 16 * ts;
    sk.className = 'sock selsock'; sk.title = '끌어서 다른 화면에 놓으면 연결';
    sk.style.left = ((q.x + q.w) * sc) + 'px'; sk.style.top = ((q.y + q.h / 2) * sc) + 'px';
    sk.style.width = sk.style.height = d + 'px'; sk.style.margin = (-d / 2) + 'px 0 0 ' + (-d / 2) + 'px'; sk.style.borderWidth = (2 * ts) + 'px';
    ph.appendChild(sk);
    return true;
  }
  function paint() {                                 // 고른 목록 그대로 다시 그리기 — 모두 테두리, 주인만 소켓·부모 점선·요소 막대
    wipe(); clear();
    var BK = ctx.blocks(), pr = primary();
    sels = sels.filter(function (s) { return s.card.isConnected; });
    sels.forEach(function (s) { if (s !== pr) outline(s.card, s.h, false); });
    pr = primary();
    if (!pr) { if (BK) BK.hide('board'); return; }
    if (!outline(pr.card, pr.h, true)) { if (BK) BK.hide('board'); return; }
    var card = pr.card, h = pr.h;
    drawParent(card, h);
    var pt = pr.pt;
    if (BK) BK.show({screen: card.dataset.id, h: h, app: ctx.app(card.dataset.id), where: 'board',   // 요소 막대(task 49a) — 고른 테두리 옆, 판이 움직이면 placeSelbar 가 다시 놓는다
                     pointer: pt ? function () { var ph = card.isConnected && $('.phone', card); if (!ph) return null; var r = ph.getBoundingClientRect(); return {x: r.left + pt.fx * r.width, y: r.top + pt.fy * r.height}; } : null,   // 누른 자리(R51)
                     frame: function () { var fs = $$('.phone iframe', card); return fs[fs.length - 1] || null; }, view: function () { return rectOf(pane); },   // 상위 묻기 · 판 칸 안에(task 49b)
                     anchor: function () { var bx = $('.elbox.sel.pri', card); if (!bx || !card.isConnected) return null; var r = bx.getBoundingClientRect(), lb = bx.classList.contains('in') ? 0 : 17 * ctx.tagScale() * ctx.zoom(); return {x: r.left, y: r.top - lb, w: r.width, h: r.height + lb}; },   // lb = 테두리 위 종류 꼬리표를 덮지 않게
                     label: function () { var bx = $('.elbox.sel.pri', card); if (!bx || !card.isConnected || bx.classList.contains('in')) return null; var r = bx.getBoundingClientRect(), lb = 17 * ctx.tagScale() * ctx.zoom(); return {x: r.left, y: r.top - lb, w: r.width, h: lb}; }});   // 꼬리표 띠(anchor 안 — 작은 요소 자리는 그대로, 누른 자리 가까이 둘 때 덮지 않게)
  }
  function select(card, h, pt) { sels = P.only({card: card, h: h, pt: pt || null}); paint(); }
  function toggle(card, h, pt) { sels = P.toggle(sels, {card: card, h: h, pt: pt || null}, keyOf); paint(); }
  function ptOf(card, x, y) {                        // 누른 자리 → 카드 화면 안 비율(판이 움직여도 따라가게) · 화면이 없거나 크기 0 = null
    var ph = $('.phone', card), r = ph && ph.getBoundingClientRect();
    return r && r.width > 0 && r.height > 0 && isFinite(x) && isFinite(y) ? {fx: (x - r.left) / r.width, fy: (y - r.top) / r.height} : null;
  }
  function keep(ok) {
    var n = P.keep(sels, function (s) { return ok(s.card.dataset.id); });
    if (n.length === sels.length) return;
    sels = n; paint();
  }
  function pickAt(card, x, y, deep, add) {           // 선택(V)으로 고른 카드를 한 번 더 = 그 자리 요소 고르기(누를 수 있는 요소 → 그 요소, 트리거 도구와 같은 규칙) · deep = 가장 안쪽 요소(Alt+클릭, 51-2) · add = Shift(더하기·빼기, R19)
    var pt = ptOf(card, x, y);
    ctx.ask(card, x, y, false, function (h) {
      if (!h) return;
      if (h.none) { ctx.toast('여기에는 고를 요소가 없어요'); return; }
      if (add) toggle(card, h, pt); else select(card, h, pt);
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
        if (mv && h && h.path && P.has(sels, {card: card, h: h}, keyOf)) clear();   // 고른 요소 위 = 이미 고른 상자
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

  return {clear: clear, selected: primary, all: function () { return sels.slice(); }, select: select, toggle: toggle, unselect: unselect, keep: keep, pickAt: pickAt};
}

HD.viewElbox = {mount: mount};
})();
