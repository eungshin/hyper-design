/* View — 생성 중 빈 틀(S5): 오는 중인 화면 자리에 무채색 반짝이는 틀('만드는 중…' + 받는 곳), 안 보이면 카메라가 살며시 데려가고, 화면이 오면 진짜 카드로 겹쳐 바꾼 뒤 토스트 [보기].
   규칙(언제 어떤 틀·단계·까닭·카메라 이동량)은 HD.placeholder(Model). 여기는 그리기·듣기만. 상태 = Model 상태 하나(저장 없음 — 새로고침 뒤에는 메모·덮개로 다시 맞춤).
   듣는 것: document 'hd-event'(view-live 의 서버 이벤트) · #rows 바뀜(MutationObserver — 카드가 생김·빈 레이아웃이 사라짐) · 1초마다 scan·tick(SSE 없는 판, 메모 sent·덮개).
   읽기만: ctx.notes.list()(빈 레이아웃 메모 edit=new-screen · 승격 moved.from) · 덮개 상태(ctx.store 의 hd-busy, HD.busy.load/look) · 판의 .card.
   그리기: 빈 레이아웃 = 그 카드 .phone 안 div.hd-gen(카드에 .hd-gen-on) · 판에 없는 화면 = #rows 안 div.hd-gen-slot[data-id](판 좌표, 카드 크기 ctx.CARD — 자리 = ctx.spot(id) 이 있으면 그것, 없으면 마지막 줄 오른쪽)
     div.hd-gen[data-state=pending|arriving|failed] > .hd-gen-sheen(쓸기 2.5s + 숨쉬기 2.5s, motion.css) + .hd-gen-msg(b 글 · span 받는 곳/까닭 · button.hd-gen-clear '지우기' — failed 만)
   카메라(선택 칸 ctx.view = {get() → {z, tx, ty}, set(z, tx, ty), pane?}): 새 틀이 판 창 밖이면 HD.placeholder.reveal 만큼 0.5초 ease-out 으로 — 사람이 누르고 있거나 1.5초 안에 판을 움직였으면 옮기지 않음, 움직이면 바로 멈춤.
     없으면 [hd] 경고 한 번 + 카메라·[보기] 없이. 선택 칸 ctx.refresh(ids) = 판 데이터 다시 받기(새 화면이 판에 실리게) — 없으면 [hd] 경고 한 번(새로고침하면 보임).
   도착: 틀 → 진짜 카드 겹쳐 바꾸기 CROSS_MS(틀 opacity 1→0 · 카드 0→1, WAAPI — 남는 style 없음) 뒤 토스트 '새 화면이 생겼어요' [보기](카드를 판 창 가운데로).
   움직임 줄이기(설정 motion:false · prefers-reduced-motion) = 반짝임 없음(motion.css) · 바로 바꿈 · 카메라는 끝 자리로 바로.
   HD.feature('placeholder', {needs: ['$', '$$', 'rowsEl', 'CARD', 'notes', 'store', 'key', 'toast', 'warn', 'prefs']}) → {state() → Model 상태, run(a)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var USER_MS = 1500, CAM_MS = 500, SCAN_MS = 100, GAP = 64;

function mount(ctx) {
  var P = HD.placeholder, s = P.initial(), rows = ctx.rowsEl, warned = {}, boxes = {}, slots = {};
  var pane = (ctx.view && ctx.view.pane) || ctx.$('#screens') || rows.parentNode;
  var lastUser = 0, down = false, cam = 0, scanT = 0;
  var ease = HD.camera ? HD.camera.bezier(0.22, 1, 0.36, 1) : function (p) { return p; };

  function warnOnce(k, m) { if (warned[k]) return; warned[k] = 1; ctx.warn('[hd] ' + m); }
  function reduced() {
    try { var p = ctx.prefs(); if (p && p.motion === false) return true; } catch (e) { warnOnce('prefs', '생성 중 틀: 설정을 읽지 못했어요 — ' + (e && e.message || e)); }
    try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; }   // matchMedia 없음 = 움직여도 됨
  }
  function find(sel, id) { var hit = null; ctx.$$(sel, rows).forEach(function (c) { if (c.dataset.id === id) hit = c; }); return hit; }
  function cardOf(id) { return find('.card:not(.draft)', id); }
  function draftOf(id) { return find('.card.draft', id); }

  function at() {
    var drafts = {}, promoted = {}, working = {}, real = {}, busy = null;
    ctx.$$('.card:not(.draft)', rows).forEach(function (c) { real[c.dataset.id] = 1; });
    if (HD.busy) busy = HD.busy.load(ctx.store.getItem, ctx.key('hd-busy'));
    (ctx.notes.list() || []).forEach(function (n) {
      if (!n || typeof n !== 'object') return;
      if (n.edit === 'new-screen' && n.screen != null) {
        var d = String(n.screen); drafts[n.id] = d;
        var b = busy && busy.items && busy.items[d];
        if (n.sent && !(n.replies || []).length && b && HD.busy.look(b).kind === 'working') working[d] = 1;
      }
      if (n.moved && typeof n.moved === 'object' && n.moved.from && n.screen != null) promoted[n.moved.from] = String(n.screen);
    });
    return {t: Date.now(), has: function (id) { return !!real[id]; }, drafts: drafts, promoted: promoted, working: working};
  }

  function boardBox(el) {                            // 판(#rows) 좌표 — 빈 카드·화면 카드를 같은 기준으로(view-promote 와 같은 계산)
    var rr = rows.getBoundingClientRect(), z = rows.offsetWidth ? rr.width / rows.offsetWidth : 1, r = el.getBoundingClientRect();
    z = z || 1;
    return {x: (r.left - rr.left) / z, y: (r.top - rr.top) / z, w: r.width / z, h: r.height / z};
  }
  function autoSpot() {                              // 마지막 줄 맨 오른쪽 카드 옆(먼저 놓인 틀이 있으면 그 옆)
    var bs = ctx.$$('.card:not(.draft):not(.hid)', rows).map(function (c) { return boardBox(c.querySelector('.phone') || c); });
    var n = Object.keys(slots).length, step = (ctx.CARD.w || 375) + GAP;
    if (!bs.length) return {x: n * step, y: 0};
    var top = Math.max.apply(null, bs.map(function (b) { return b.y; }));
    var row = bs.filter(function (b) { return b.y > top - 40; });
    return {x: Math.max.apply(null, row.map(function (b) { return b.x + b.w; })) + GAP + n * step, y: Math.min.apply(null, row.map(function (b) { return b.y; }))};
  }

  function frameIn(host, id) {
    var f = null;
    Array.prototype.forEach.call(host.children, function (c) { if (c.classList.contains('hd-gen')) f = c; });
    if (f) return f;
    f = document.createElement('div'); f.className = 'hd-gen'; f.setAttribute('role', 'status');
    f.innerHTML = '<div class="hd-gen-sheen" aria-hidden="true"></div><div class="hd-gen-msg"><b class="hd-gen-t"></b><span class="hd-gen-s"></span>' +
                  '<button type="button" class="hd-gen-clear">지우기</button></div>';
    var b = f.querySelector('.hd-gen-clear');
    ['pointerdown', 'mousedown', 'dblclick'].forEach(function (t) { b.addEventListener(t, function (e) { e.stopPropagation(); }); });   // 카드 끌기·고르기·메모 열기로 새지 않게
    b.addEventListener('click', function (e) { e.stopPropagation(); e.preventDefault(); run({type: 'clear', id: id}); });
    host.appendChild(f);
    return f;
  }
  function fill(f, lk) {
    f.dataset.state = lk.state;
    f.querySelector('.hd-gen-t').textContent = lk.title;
    var sub = f.querySelector('.hd-gen-s'); sub.textContent = lk.sub; sub.hidden = !lk.sub;
    f.title = lk.title + (lk.sub ? ' · ' + lk.sub : '');
  }
  function makeSlot(id, box) {
    var el = document.createElement('div'); el.className = 'hd-gen-slot'; el.dataset.id = id;
    el.style.left = box.x + 'px'; el.style.top = box.y + 'px'; el.style.width = box.w + 'px'; el.style.height = box.h + 'px';
    var ph = ctx.$('.card .phone', rows), rad = ph ? getComputedStyle(ph).borderRadius : '';
    if (rad) el.style.borderRadius = rad;
    rows.appendChild(el);
    return el;
  }
  function host(id) { var it = s.items[id]; if (!it) return null; if (it.kind === 'screen') return slots[id] || null; var c = draftOf(id); return c && (c.querySelector('.phone') || c); }

  function paint(id) {
    var it = s.items[id]; if (!it) return;
    var h;
    if (it.kind === 'draft') {
      var c = draftOf(id); if (!c) return;           // 빈 카드가 아직 안 그려짐 — 다음 scan 이 다시
      c.classList.add('hd-gen-on'); h = c.querySelector('.phone') || c;
      boxes[id] = boardBox(h);
    } else {
      if (!slots[id]) {
        var sp = null;
        try { sp = ctx.spot ? ctx.spot(id) : null; } catch (e) { warnOnce('spot', '생성 중 틀: 자리 계산 실패 — 마지막 줄 옆에 둬요 (' + (e && e.message || e) + ')'); }
        sp = sp || autoSpot();
        slots[id] = makeSlot(id, {x: sp.x, y: sp.y, w: ctx.CARD.w || 375, h: ctx.CARD.h || 812});
      }
      h = slots[id];
    }
    fill(frameIn(h, id), P.look(it));
  }
  function unframe(id) {
    var c = draftOf(id);
    if (c) { c.classList.remove('hd-gen-on'); ctx.$$('.hd-gen', c).forEach(function (f) { f.remove(); }); }
    if (slots[id]) { slots[id].remove(); delete slots[id]; }
    delete boxes[id];
  }
  function fadeOut(el) {
    if (!el.animate) { el.remove(); return; }
    var a = el.animate([{opacity: 1}, {opacity: 0}], {duration: P.CROSS_MS, easing: 'ease', fill: 'forwards'});
    a.onfinish = function () { el.remove(); };
  }
  function done(id, to) {
    var card = cardOf(to), calm = reduced(), ghost = slots[id] || null, box = boxes[id];
    delete slots[id]; delete boxes[id];
    if (!ghost && box && !calm) {                    // 빈 카드는 셸이 이미 지웠다 — 그 자리에 틀 그림자를 잠깐 두고 걷는다
      ghost = makeSlot(id, box); ghost.classList.add('hd-gen-ghost');
      fill(frameIn(ghost, id), {state: 'arriving', title: '화면을 싣는 중…', sub: '', shimmer: true, clear: false});
    }
    if (ghost) { if (calm) ghost.remove(); else fadeOut(ghost); }
    if (card && !calm && card.animate) card.animate([{opacity: 0}, {opacity: 1}], {duration: P.CROSS_MS, easing: 'ease'});
    say(to);
  }
  function say(to) {
    ctx.toast('새 화면이 생겼어요', false, 8000);
    var t = ctx.$('#toast'); if (!t || !ctx.view) return;
    var b = document.createElement('button'); b.type = 'button'; b.className = 'hd-gen-view'; b.textContent = '보기';
    b.addEventListener('click', function () {
      t.hidden = true;
      var c = cardOf(to);
      if (!c) { ctx.toast('그 화면이 판에 없어요'); return; }
      go([c.querySelector('.phone') || c], true);
    });
    t.appendChild(b);
  }
  function land(ids) {
    if (!ids || !ids.length) return;
    if (!ctx.refresh) { warnOnce('refresh', '생성 중 틀: 판 데이터를 다시 받는 칸(ctx.refresh)이 없어요 — 새 화면은 새로고침하면 보여요'); return; }
    try { ctx.refresh(ids); } catch (e) { ctx.warn('[hd] 생성 중 틀: 판 데이터를 다시 받지 못했어요 — ' + (e && e.message || e)); }
  }

  // 카메라 — 사람이 판을 만지는 동안은 옮기지 않는다
  function userBusy() { return down || Date.now() - lastUser < USER_MS || !!(ctx.view.moving && ctx.view.moving()); }
  function stopCam() { if (cam) { cancelAnimationFrame(cam); cam = 0; } }
  function touch() { lastUser = Date.now(); stopCam(); }
  if (pane) {
    pane.addEventListener('pointerdown', function () { down = true; touch(); }, true);
    pane.addEventListener('wheel', touch, {capture: true, passive: true});
  }
  addEventListener('pointerup', function () { if (down) { down = false; lastUser = Date.now(); } }, true);
  addEventListener('pointercancel', function () { down = false; }, true);

  function go(els, centre) {
    if (!ctx.view || !pane) return;
    var pr = pane.getBoundingClientRect(), x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    els.forEach(function (el) { var r = el.getBoundingClientRect(); x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
    if (!(x1 > x0)) return;
    var v = ctx.view.get(), view = {w: pane.clientWidth, h: pane.clientHeight, z: v.z, tx: v.tx, ty: v.ty};
    var to = P.reveal({x: x0 - pr.left, y: y0 - pr.top, w: x1 - x0, h: y1 - y0}, view, {margin: 48, centre: !!centre, zMin: 0.05});
    if (!to) return;
    stopCam();
    if (reduced() || !HD.camera) { ctx.view.set(to.z, to.tx, to.ty); return; }
    var keys = [{t: 0, z: v.z, tx: v.tx, ty: v.ty}, {t: CAM_MS, z: to.z, tx: to.tx, ty: to.ty}], t0 = performance.now();
    var tick = function (now) {
      var p = HD.camera.at(keys, now - t0, ease, view);
      ctx.view.set(p.z, p.tx, p.ty);
      cam = now - t0 < CAM_MS ? requestAnimationFrame(tick) : 0;
    };
    cam = requestAnimationFrame(tick);
  }
  function reveal(ids) {
    if (!ctx.view) { warnOnce('view', '생성 중 틀: 카메라 칸(ctx.view)이 없어 판을 옮기지 않아요'); return; }
    if (userBusy()) return;
    var els = ids.map(host).filter(Boolean);
    if (els.length) go(els, false);
  }

  function run(a) {
    var r;
    try { r = P.step(s, a, at()); } catch (e) { ctx.warn('[hd] 생성 중 틀: 처리 실패(' + (a && a.type) + ') — ' + (e && e.message || e)); return; }
    s = r.s;
    var shown = [];
    r.fx.forEach(function (f) {
      try {
        if (f.do === 'show') { paint(f.id); shown.push(f.id); }
        else if (f.do === 'paint') paint(f.id);
        else if (f.do === 'landing') land(f.ids);
        else if (f.do === 'done') done(f.id, f.to);
        else if (f.do === 'drop') unframe(f.id);
      } catch (e) { ctx.warn('[hd] 생성 중 틀: 그리기 실패(' + f.do + ') — ' + (e && e.message || e)); }
    });
    P.list(s).forEach(function (it) {               // 셸이 빈 카드를 다시 만들었으면 틀을 다시 씌운다
      var h = host(it.id); if (it.kind === 'draft' && h && !h.querySelector('.hd-gen')) paint(it.id);
    });
    if (shown.length) reveal(shown);
  }
  function scan() { scanT = 0; run({type: 'scan'}); }
  function later() { if (!scanT) scanT = setTimeout(scan, SCAN_MS); }

  document.addEventListener('hd-event', function (e) { if (e && e.detail) run(e.detail); });
  if (typeof MutationObserver === 'function') new MutationObserver(later).observe(rows, {childList: true, subtree: true});
  setInterval(function () { if (document.hidden) return; scan(); run({type: 'tick'}); }, 1000);
  if (ctx.api && ctx.api.on && ctx.api.call) {       // 받는 곳 이름(틀 글) — 접속한 에이전트 목록 한 번, 그 뒤는 agent.hello
    ctx.api.call('GET', '/api/presence').then(function (r) {
      var l = r && r.body && (Array.isArray(r.body.agents) ? r.body.agents : Array.isArray(r.body) ? r.body : null);
      if (l) run({type: 'agents', list: l});
    }, function (e) { warnOnce('presence', '생성 중 틀: 받는 곳 이름을 읽지 못했어요 — ' + (e && e.message || e)); });
  }
  later();
  return {state: function () { return s; }, run: run};
}

HD.feature('placeholder', {needs: ['$', '$$', 'rowsEl', 'CARD', 'notes', 'store', 'key', 'toast', 'warn', 'prefs'], mount: mount});
})();
