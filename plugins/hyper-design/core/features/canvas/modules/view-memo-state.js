/* View — 움직이는 화면의 메모 칩 줄(memo-state): 지금 단계가 메모를 단 단계와 달라 점선·핀을 그리지 않는 메모의 번호 칩을 화면 내용 밖에 — 판 카드 위쪽 빈 줄(막히면 아래), 크게 보기 머리 줄.
   칩 = 메모 번호(n.no, 판 핀과 같은 색·숫자 — decide 는 강조색). 올리기·포커스 = 메모 글 미리보기(#mschtip, 자리는 공용 HD.popSide.beside). 누르기 = 그 단계로 가기:
     HD.memoState.plan 차례대로 'hd'(hd-goto → 화면 window.hdGoto) · 'replay'(카드·크게 보기 iframe 을 다시 읽고 hd-replay = 클릭 기록 다시 하기) — 한 가지가 끝나면
     그 메모 핀이 그려질 때까지(ARRIVE) 기다려 ctx.select(그 메모를 고른 상태 = 메모 묶음이 그 메모로) · 다 실패하면 토스트 HD.memoState.FAIL, 칩은 그대로.
   상태(저장하지 않음) = 가는 중인 메모 id 하나(busy) · 답 기다리는 tag 표(waits). 칩 줄 배치 규칙(위·아래, 한 줄 칩 수)은 Model HD.memoState.side·row.
   HD.viewMemoState.mount(ctx) → {render(id?), layer}   id = 칩을 다시 그릴 화면(없으면 판 카드 전부 + 크게 보기) — 셸이 핀 답(PN changed)·크게 보기 다시 그리기 때 부른다
   layer = 떠 있는 층 'chiptip'(view-float-stack, U1): 미리보기(꼬리말)는 Esc 로 닫힌다(꼬리말 관례 — 누르기는 아래 층 몫, 칩에서 벗어나면 스스로 숨는다). 칩 줄은 늘 있는 상태 표시라 닫지 않는다
   ctx = {rowsEl, mbar(크게 보기 머리 줄), esc, away(id, modal) → [메모], cardEl(id), modal() → {open, screen, frame}, frameOf(id) → 카드 iframe|null,
          select(id, no, modal, pin), toast(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var ARRIVE = 3000, GONE = 1500, REPLAY = 15000, CHIP = 20, GAP = 4, RESERVE = 70;   // RESERVE = 카드 오른쪽 위 '크게 보기'(.pres) 자리

function mount(ctx) {
  var M = HD.memoState, A = HD.annotation, esc = ctx.esc, rowsEl = ctx.rowsEl, busy = null, seq = 0, waits = {};
  var css = document.createElement('style'); css.id = 'hd-memo-state-css';
  css.textContent =
    '.mschips{display:flex;align-items:center;gap:' + GAP + 'px;pointer-events:auto}' +
    '#rows .card>.mschips{position:absolute;left:0;bottom:calc(100% + 8px);z-index:5;transform-origin:0 100%;transform:scale(var(--lz,1))}' +
    '#rows .card>.mschips.bot{bottom:auto;top:calc(100% + 4px);transform-origin:0 0}' +
    '.mschip{min-width:' + CHIP + 'px;height:' + CHIP + 'px;padding:0 5px;box-sizing:border-box;border:0;border-radius:999px;background:var(--ui-badge);color:#fff;' +
      'font:600 12px/1 system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.25)}' +
    '.mschip[data-st="decide"]{background:var(--ui-accent)}' +
    '.mschip:hover,.mschip:focus-visible{outline:2px solid var(--ui-mark);outline-offset:1px}' +
    '.mschip.more{background:transparent;color:#6b6b66;box-shadow:none;cursor:default}' +
    '.mschip[aria-busy="true"]{opacity:.55;cursor:progress}' +
    '#modal .mbar .mschips{flex:none;margin-right:auto}#modal .mbar:has(.mschips) #mtitle{flex:0 1 auto}' +   // 크게 보기: 제목 바로 뒤(닫기 단추와 떨어지게)
    '#mschtip{position:fixed;z-index:60;max-width:260px;padding:6px 9px;border-radius:6px;background:#2b2b29;color:#fff;font:400 12px/17px system-ui,-apple-system,sans-serif;pointer-events:none;white-space:normal}';
  document.head.appendChild(css);
  var tip = document.createElement('div'); tip.id = 'mschtip'; tip.hidden = true; tip.setAttribute('role', 'tooltip');
  document.body.appendChild(tip);

  function byNo(a, b) { return (a.no || 0) - (b.no || 0); }
  function chipHtml(n) {
    return '<button type="button" class="mschip" data-id="' + esc(n.id) + '" data-no="' + esc(n.no) + '" data-st="' + A.status(n) + '"' +
      (busy === n.id ? ' aria-busy="true"' : '') + ' aria-label="' + esc(M.preview(n)) + ' — 그 단계로 가기">' + esc(n.no) + '</button>';
  }
  function strip(list, show) {
    var more = list.slice(show);
    return list.slice(0, show).map(chipHtml).join('') +
      (more.length ? '<span class="mschip more" title="' + esc(more.map(M.preview).join('\n')) + '">+' + more.length + '</span>' : '');
  }
  function boxOf(el) { var r = el.getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; }
  function obstacles(card) {                         // 칩 줄이 덮으면 안 되는 판 위 것들 — 다른 카드 화면·제목, 묶음 이름, 선 태그
    return Array.prototype.filter.call(rowsEl.querySelectorAll('.card .phone, .card>.ftitle, .card>.nbadge, .glabel, .alabel'), function (e) {
      return !card.contains(e);
    }).map(boxOf);
  }
  function drawCard(id) {
    var card = ctx.cardEl(id); if (!card) return;
    var old = card.querySelector(':scope>.mschips'), list = ctx.away(id, false).sort(byNo);
    if (!list.length) { if (old) old.remove(); return; }
    var ph = card.querySelector('.phone'), lz = parseFloat(getComputedStyle(rowsEl).getPropertyValue('--lz')) || 1;
    var avail = ph ? ph.offsetWidth / lz - RESERVE : 200, fit = M.row(list.length, avail, CHIP, GAP);
    var el = old || document.createElement('div');
    el.className = 'mschips'; el.setAttribute('role', 'group'); el.setAttribute('aria-label', '다른 단계에 단 메모');
    el.innerHTML = strip(list, fit.show);
    if (!old) card.appendChild(el);
    var top = boxOf(el), c = boxOf(card), bottom = {x: top.x, y: c.y + c.h + 4, w: top.w, h: top.h};
    if (el.classList.contains('bot')) top = {x: top.x, y: c.y - 8 - top.h, w: top.w, h: top.h};
    el.classList.toggle('bot', M.side(top, bottom, obstacles(card)) === 'bottom');
  }
  function drawModal() {
    var m = ctx.modal(), old = ctx.mbar.querySelector('.mschips');
    var list = m.open && m.screen ? ctx.away(m.screen, true).sort(byNo) : [];
    if (!list.length) { if (old) old.remove(); return; }
    var el = old || document.createElement('div');
    el.className = 'mschips'; el.setAttribute('role', 'group'); el.setAttribute('aria-label', '다른 단계에 단 메모');
    el.innerHTML = strip(list, M.row(list.length, 360, CHIP, GAP).show);
    if (!old) { var t = ctx.mbar.querySelector('#mtitle'); ctx.mbar.insertBefore(el, t ? t.nextSibling : null); }
  }
  function render(id) {
    if (id != null) drawCard(id);
    else Array.prototype.forEach.call(rowsEl.querySelectorAll('.card[data-id]'), function (c) { drawCard(c.dataset.id); });
    drawModal();
  }

  function showTip(b) {
    var n = memoOf(b); if (!n) { hideTip(); return; }
    tip.textContent = M.preview(n); tip.hidden = false;
    var r = boxOf(b), y0 = r.y + r.h + 2, all = {x: 4, y: 4, w: innerWidth - 8, h: innerHeight - 8};
    var p = HD.popSide.beside(r, {w: tip.offsetWidth, h: tip.offsetHeight}, [{x: 4, y: y0, w: innerWidth - 8, h: innerHeight - y0 - 4}, all], 6);   // 칩 줄 아래 자리 먼저 — 크게 보기 닫기 단추·제목을 가리지 않게
    tip.style.left = p.x + 'px'; tip.style.top = p.y + 'px';
  }
  function hideTip() { tip.hidden = true; }
  function chipOf(e) { return e.target && e.target.closest ? e.target.closest('.mschip:not(.more)') : null; }
  function memoOf(b) {
    var inModal = !!b.closest('#modal'), id = inModal ? ctx.modal().screen : (b.closest('.card') || {dataset: {}}).dataset.id;
    return ctx.away(id, inModal).filter(function (n) { return String(n.id) === b.dataset.id; })[0] || null;
  }

  addEventListener('message', function (e) {         // hd-gone · hd-replayed — 보낸 tag 하나에 한 번
    var d = e.data; if (!d || typeof d !== 'object' || (d.type !== 'hd-gone' && d.type !== 'hd-replayed')) return;
    var w = waits[d.tag]; if (!w || w.type !== d.type) return;
    delete waits[d.tag]; clearTimeout(w.timer); w.done(d);
  });
  function expect(tag, type, ms, done) {
    waits[tag] = {type: type, done: done, timer: setTimeout(function () { delete waits[tag]; done(null); }, ms)};
  }
  function pinOf(id, no, modal) {
    if (modal) return document.querySelector('#mpins .pin[data-no="' + no + '"]');
    var c = ctx.cardEl(id); return c ? c.querySelector('.npin[data-no="' + no + '"]') : null;
  }
  function go(id, n, modal) {
    if (busy) return;
    var frameOf = function () { return modal ? ctx.modal().frame : ctx.frameOf(id); };
    var tries = M.plan(n.view);
    busy = n.id; render(modal ? null : id);
    function finish(ok, pin) {
      busy = null; render(modal ? null : id);
      if (ok) ctx.select(id, n.no, modal, pin);
      else ctx.toast(M.FAIL);
    }
    function arrive(orElse) {                        // 그 메모 핀이 그려질 때까지 — 화면이 바뀌면 palette 가 자리를 다시 답한다
      var t0 = Date.now();
      (function poll() {
        var p = pinOf(id, n.no, modal);
        if (p) { finish(true, p); return; }
        if (Date.now() - t0 > ARRIVE) { orElse(); return; }
        setTimeout(poll, 100);
      })();
    }
    function next() {
      var how = tries.shift(), f = frameOf();
      if (!how || !f || !f.contentWindow) { finish(false); return; }
      var tag = 'ms' + (++seq);
      if (how === 'hd') {
        expect(tag, 'hd-gone', GONE, function (d) { if (d && d.ok) arrive(next); else next(); });
        try { f.contentWindow.postMessage({type: 'hd-goto', tag: tag, state: n.view.hd}, '*'); } catch (err) { next(); }
        return;
      }
      expect(tag, 'hd-replayed', REPLAY, function (d) { if (d && d.ok) arrive(next); else next(); });
      f.addEventListener('load', function () {       // 화면을 처음부터 다시 읽은 뒤 클릭 기록을 차례로
        try { f.contentWindow.postMessage({type: 'hd-replay', tag: tag, trail: n.view.trail}, '*'); } catch (err) { console.warn('[hd] 다시 하기를 보내지 못했어요'); }
      }, {once: true});
      f.src = f.src;
    }
    next();
  }

  document.addEventListener('click', function (e) {  // 판의 click(잡는 단계)보다 먼저 — 카드 고르기·도구 동작으로 가지 않게
    var b = chipOf(e); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    var n = memoOf(b); if (!n) return;
    var inModal = !!b.closest('#modal');
    hideTip();
    go(inModal ? ctx.modal().screen : b.closest('.card').dataset.id, n, inModal);
  }, true);
  ['pointerdown', 'dblclick'].forEach(function (t) {
    document.addEventListener(t, function (e) { if (e.target && e.target.closest && e.target.closest('.mschips')) e.stopPropagation(); }, true);   // 판 끌기·카드 옮기기·크게 보기로 가지 않게
  });
  document.addEventListener('pointerover', function (e) { var b = chipOf(e); if (b) showTip(b); else if (!tip.hidden) hideTip(); });
  document.addEventListener('focusin', function (e) { var b = chipOf(e); if (b) showTip(b); else if (!tip.hidden) hideTip(); });

  var layer = {id: 'chiptip', escOnly: true, isOpen: function () { return !tip.hidden; }, close: hideTip, hit: function () { return 'ignore'; }};
  return {render: render, layer: layer};
}

HD.viewMemoState = {mount: mount};
})();
