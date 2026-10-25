/* View — 메모 핀: 판 카드와 크게 보기 위, 메모가 달린 요소 자리에 번호(n.no) 핀. 자리는 화면에 다시 물어(hd-locate) 찾은 곳.
   상태(저장하지 않음) = 화면마다 다시 찾은 자리 located{화면 id: {키: {rect, how}}}(키 = 메모 id:대상 차례) · 크게 보기 것 따로 · 막 메모를 단 카드(focus) 하나.
   판: 보이는 메모(HD.annotation.visible — 아래 task 29)이고 다시 찾은 자리가 있는 대상만. 카드를 고르거나 올리거나, 판 배율로 화면이 실제의 60% 이상일 때(.pins-near), 막 메모를 단 카드에만 보인다(CSS).
     화면 전체(body)·빈 레이아웃·편집 메모는 핀 없음(배지·묶음만). 색: decide = --ui-accent 하나, 나머지 --ui-badge.
   크게 보기(셸 drawPins → paint): 그 화면 보이는 메모 전부, 다시 찾은 자리가 있으면 그것, 아직 답이 없으면 저장한 rect.
   보낸 메모 숨기기(task 29): 판·크게 보기 모두 HD.annotation.visible(n, 켜짐)인 메모만(켜짐 = ctx.showSent(), 주인 view-notes),
     숨김이 될 메모의 핀은 켜졌을 때 흐리게(.nhid). 켜짐이 바뀌면 셸이 render() 를 부른다 = 다시 그리고 자리를 다시 묻는다(#263).
   요소를 찾을 수 없음(#285): 답이 how 'none'(같은 요소가 여럿·없음)인 대상은 핀 없음 — lost(n)(HD.relocate.lost)로 메모 목록·묶음 줄이 알린다.
   핀 누르기 = ctx.openThread(화면 id, no, 핀) — 카드 고르기·끌기로 가지 않는다.
   HD.viewPins.mount(ctx) → {locate(id, frame), locateModal(), render(ids?), paint(), zoom(z), focus(id|null), highlight(id, no|null), lost(n)}
   ctx = {rowsEl, mpins, $, $$, esc, CARD, list() → 메모 전부, cardEl(id), modal() → {open, screen, scale, frame, draft}, openThread(id, no, el), showSent() → 켜짐, changed(id)?} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var A = HD.annotation, T = HD.notes.targets, L = HD.relocate, esc = ctx.esc;
  var located = {}, mloc = {screen: null, items: {}}, asked = [], focused = null;

  function key(n, i) { return L.key(n.id, i); }
  function shows(n) { return A.visible(n, ctx.showSent()); }   // 보일 메모(task 29) — 꺼짐이면 working·done 빠짐
  function dim(n) { return A.visible(n, false) ? '' : ' nhid'; }
  var css = document.createElement('style'); css.id = 'hd-pins-sent-css';
  css.textContent = '.npin.nhid,.pin.nhid{opacity:.55}.npbox.nhid,.pin-box.nhid{opacity:.4}';
  document.head.appendChild(css);
  var pinnable = L.pinnable;
  function boardMemos(id) {                          // 판 핀이 될 메모: 사람이 쓴 메모(편집 아님)
    return ctx.list().filter(function (n) { return n.screen === id && !n.edit; });
  }
  function items(list) {
    var out = [];
    list.forEach(function (n) { T(n).forEach(function (t, i) { if (pinnable(t)) out.push({key: key(n, i), path: t.path, quote: t.quote || {exact: String(t.text || ''), prefix: '', suffix: ''}}); }); });
    return out;
  }
  function ask(win, slot, id, list) {
    var its = items(list); if (!win) return;
    asked = asked.filter(function (a) { return a.win !== win; });
    asked.push({win: win, slot: slot, id: id});
    try { win.postMessage({type: 'hd-locate', items: its}, '*'); } catch (e) {}
  }
  function locate(id, frame) { if (frame && frame.contentWindow) ask(frame.contentWindow, 'card', id, boardMemos(id).filter(shows)); }
  function locateModal() {
    var m = ctx.modal(); if (!m.open || !m.screen || !m.frame || !m.frame.contentWindow) return;
    ask(m.frame.contentWindow, 'modal', m.screen, ctx.list().filter(function (n) { return n.screen === m.screen && shows(n); }));
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || d.type !== 'hd-located' || !Array.isArray(d.items)) return;
    var a = asked.filter(function (x) { return x.win === e.source; })[0]; if (!a) return;
    var map = {};
    d.items.forEach(function (it) { if (it && it.key) map[it.key] = {rect: it.rect || null, how: it.how || 'none'}; });
    if (a.slot === 'modal') { mloc = {screen: a.id, items: map}; paint(); }
    else { located[a.id] = map; draw(a.id); }
    if (ctx.changed) ctx.changed(a.id);
  });

  function phoneOf(id) { var c = ctx.cardEl(id); return c && !c.classList.contains('draft') ? ctx.$('.phone', c) : null; }
  function loaded(ph) { var f = ph && ctx.$('iframe', ph); return !!f && !f.hasAttribute('data-src') && !!f.getAttribute('src'); }
  function scaleOf(ph) { var c = ph.closest('.card'), w = c && ctx.sizeOf ? ctx.sizeOf(c.dataset.id).w : ctx.CARD.w; return ph.offsetWidth / w || 1; }   // 그 카드 폭 기준(task 46)
  function draw(id) {
    var ph = phoneOf(id); if (!ph) return;
    var box = ctx.$('.npins', ph);
    var map = located[id], h = '';
    if (map && loaded(ph)) {
      var s = scaleOf(ph);
      boardMemos(id).forEach(function (n) {
        if (!shows(n)) return;
        var st = A.status(n);
        T(n).forEach(function (t, i) {
          var at = map[key(n, i)]; if (!pinnable(t) || !at || !at.rect) return;
          var r = at.rect;
          h += '<div class="npbox' + dim(n) + '" data-no="' + n.no + '" style="left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px;width:' + (r.w * s) + 'px;height:' + (r.h * s) + 'px"></div>' +
               '<button type="button" class="npin' + dim(n) + '" data-id="' + esc(n.id) + '" data-no="' + n.no + '" data-st="' + st + '" title="메모 ' + n.no + ' — ' + A.LABEL[st] + '" style="left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px">' + n.no + '</button>';
        });
      });
    }
    if (!h) { if (box) box.remove(); return; }
    if (!box) { box = document.createElement('div'); box.className = 'npins'; ph.appendChild(box); }
    box.innerHTML = h;
  }
  function render(ids) {                             // 메모가 바뀐 화면(없으면 실린 카드 전부): 바로 그리고, 자리를 다시 묻는다(새 메모는 답이 오면 핀)
    var all = ids || Object.keys(located);
    all.forEach(function (id) {
      draw(id);
      var ph = phoneOf(id); if (ph && loaded(ph) && located[id]) locate(id, ctx.$('iframe', ph));
    });
    var m = ctx.modal(); if (m.open && (!ids || ids.indexOf(m.screen) >= 0)) locateModal();
    paint();
  }

  function paint() {                                 // 크게 보기 핀 + 판 위 지금 고른 요소 테두리(메모 창이 열린 동안)
    var m = ctx.modal(), h = '', s = m.scale;
    if (m.open && m.screen) {
      var mine = mloc.screen === m.screen ? mloc.items : {};
      ctx.list().forEach(function (n) {
        if (n.screen !== m.screen || !shows(n)) return;
        T(n).forEach(function (t, i) {
          var at = mine[key(n, i)], r = at ? at.rect : t.rect; if (!r) return;
          h += '<div class="pin-box' + dim(n) + '" data-no="' + n.no + '" style="left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px;width:' + (r.w * s) + 'px;height:' + (r.h * s) + 'px"></div>' +
            '<button type="button" class="pin' + dim(n) + '" data-id="' + esc(n.id) + '" data-n="' + n.no + '" data-no="' + n.no + '" data-st="' + A.status(n) + '" style="left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px">' + n.no + '</button>';
        });
      });
      if (m.draft) m.draft.targets.forEach(function (t, i) {   // 지금 고른 요소들: 테두리 + 고른 순서
        var r = t.rect; if (!r) return;
        h += '<div class="sel-box" style="left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px;width:' + (r.w * s) + 'px;height:' + (r.h * s) + 'px"><b>' + (i + 1) + '</b></div>';
      });
    }
    ctx.mpins.innerHTML = h;
    ctx.$$('.npsel', ctx.rowsEl).forEach(function (b) { b.remove(); });
    if (!m.open && m.draft) {                        // 판 위 카드에서 고른 요소(#11 B): 메모 창이 열린 동안 그 카드에 점선 테두리
      var ph = phoneOf(m.draft.screen);
      if (ph) m.draft.targets.forEach(function (t) {
        var r = t.rect; if (!r) return;
        var sc = scaleOf(ph), b = document.createElement('div');
        b.className = 'npsel'; b.style.cssText = 'left:' + (r.x * sc) + 'px;top:' + (r.y * sc) + 'px;width:' + (r.w * sc) + 'px;height:' + (r.h * sc) + 'px';
        ph.appendChild(b);
      });
    }
  }

  function zoom(z) {                                 // 카드 화면이 실제 크기의 60% 이상이면 핀을 늘 보인다
    var ph = ctx.$('.card:not(.draft) .phone', ctx.rowsEl), s = ph ? scaleOf(ph) : 1;
    ctx.rowsEl.classList.toggle('pins-near', z * s >= 0.6);
  }
  function focus(id) {                               // 막 메모를 단 카드: 다른 카드를 고르거나 올릴 때까지 핀을 보인다
    if (focused === id) return;
    ctx.$$('.card.pins-on', ctx.rowsEl).forEach(function (c) { c.classList.remove('pins-on'); });
    focused = id || null;
    var c = focused && ctx.cardEl(focused); if (c) c.classList.add('pins-on');
  }
  ctx.rowsEl.addEventListener('pointerover', function (e) {
    if (!focused) return;
    var c = e.target.closest ? e.target.closest('.card') : null;
    if (c && c.dataset.id !== focused) focus(null);
  });
  function highlight(id, no) {                       // 묶음 줄에 올리면 그 핀·요소 테두리(판·크게 보기)
    ctx.$$('.npins.show', ctx.rowsEl).forEach(function (b) { b.classList.remove('show'); });
    ctx.$$('.npin.hi, .npbox.hi, #mpins .hi', document).forEach(function (b) { b.classList.remove('hi'); });
    if (no == null) return;
    var ph = phoneOf(id), box = ph && ctx.$('.npins', ph);
    if (box) { box.classList.add('show'); ctx.$$('[data-no="' + no + '"]', box).forEach(function (b) { b.classList.add('hi'); }); }
    var m = ctx.modal();
    if (m.open && m.screen === id) ctx.$$('[data-no="' + no + '"]', ctx.mpins).forEach(function (b) { b.classList.add('hi'); });
  }
  function lost(n) {                                 // 다시 찾지 못한 대상이 있나(판 카드 답, 없으면 크게 보기 답)
    return L.lost(n.id, T(n), located[n.screen] || (mloc.screen === n.screen ? mloc.items : null));
  }

  function pinOf(e) { var p = e.target.closest ? e.target.closest('.npin, #mpins .pin') : null; return p; }
  document.addEventListener('click', function (e) {  // 판의 click(잡는 단계)보다 먼저 — 카드 고르기·도구 동작으로 가지 않게
    var p = pinOf(e); if (!p) return;
    e.preventDefault(); e.stopPropagation();
    var id = p.closest('.card') ? p.closest('.card').dataset.id : ctx.modal().screen;
    ctx.openThread(id, +p.dataset.no, p);
  }, true);
  ['pointerdown', 'dblclick'].forEach(function (n) {
    ctx.rowsEl.addEventListener(n, function (e) { if (pinOf(e)) e.stopPropagation(); });   // 판 끌기·카드 옮기기·크게 보기로 가지 않게
  });

  return {locate: locate, locateModal: locateModal, render: render, paint: paint, zoom: zoom, focus: focus, highlight: highlight, lost: lost};
}

HD.viewPins = {mount: mount};
})();
