/* View — 화면 파일 보기: "AI 수정 중" 덮개 그리기(Q2b, D14 · #254)와 도우미가 알린 바뀐 화면 카드만 다시 싣기. 규칙은 modules/busy.js(Model).
   덮개 = 카드 .phone 안 <div class="busy" data-via="paseo|queue|cli" role="status">: Paseo → 도는 표시 + "AI 수정 중",
   대기열 → "대기열에 있음" + [걷기] · cli(hd claim) → 도는 표시 + 누가·무엇(HD.busy.label) + [걷기]. 화면 파일이 바뀌면 걷고 그 카드만 다시 부른다.
   덮개가 하나라도 있는 동안만 ctx.watch 를 2000ms 마다 부른다. 상태는 ctx.key 로 저장해 새로 고쳐도 남는다.
   adopt() = 상태 파일에서 busy 가 바뀜(hd claim·release, view-state-sync onExternal) → 다시 읽어 그리기(새로고침 없음).
   ctx.files 가 있으면 1000ms 마다(보일 때만) 도우미의 바뀐 화면 목록을 받아 HD.busy.refresh 로 고른 카드만 ctx.reload,
   크게 보기가 그 화면이면 ctx.reloadModal. wrote(ids) = 판이 방금 스스로 쓴·다시 실은 화면(5초 동안 다시 싣지 않음).
   HD.viewBusy.mount(ctx) → {mark(screens:[{id, file}], via), render(), lift(id), adopt(), wrote(ids)}
   ctx = {cardEl(id) → .card|null, watch(files) → Promise<{mtimes}>, reload(ids), getItem(k), setItem(k, v), key, toast(msg), warn(msg)?,
          files(since)? → Promise<{seq, changed:[id]}>, known()? → [id], modalScreen()? → id|null, reloadModal()?} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var EVERY = 2000, FILES_EVERY = 1000, SKIP_MS = 5000;

function mount(ctx) {
  var B = HD.busy, warn = ctx.warn || function (m) { console.warn(m); };
  var st = B.load(ctx.getItem, ctx.key, warn), els = {}, timer = 0, skip = {};

  function dispatch(a) {
    var n = B.reduce(st, a);
    if (n !== st) { st = n; B.save(st, ctx.setItem, ctx.key); }
    return st;
  }
  function ids() { return Object.keys(st.items); }

  function draw(id, it) {                             // 카드 하나에 덮개(이미 맞게 있으면 그대로)
    var card = ctx.cardEl(id), host = card && (card.querySelector('.phone') || card), el = els[id], text = B.label(it);
    if (!host) { if (el) { el.remove(); delete els[id]; } return; }
    if (el && el.parentNode === host && el.getAttribute('data-via') === it.via && el.getAttribute('data-label') === text) return;
    if (el) el.remove();
    el = document.createElement('div');
    el.className = 'busy'; el.setAttribute('data-via', it.via); el.setAttribute('data-id', id); el.setAttribute('data-label', text); el.setAttribute('role', 'status');
    if (it.via !== 'queue') {
      var sp = document.createElement('span'); sp.className = 'busy-spin'; sp.setAttribute('aria-hidden', 'true'); el.appendChild(sp);
    }
    var tx = document.createElement('span'); tx.className = 'busy-txt';
    tx.textContent = text;
    el.appendChild(tx);
    if (it.via !== 'paseo') {
      var b = document.createElement('button'); b.type = 'button'; b.setAttribute('data-act', 'lift'); b.textContent = '걷기';
      b.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
      b.addEventListener('click', function (e) { e.stopPropagation(); e.preventDefault(); lift(id); });
      el.appendChild(b);
    }
    host.appendChild(el); els[id] = el;
  }
  function render() {                                 // 지금 상태대로 덮개 그리기·지우기(여러 번 불러도 같음)
    var k;
    for (k in els) if (!Object.prototype.hasOwnProperty.call(st.items, k)) { els[k].remove(); delete els[k]; }
    for (k in st.items) draw(k, st.items[k]);
  }
  function wrote(list) { var until = Date.now() + SKIP_MS; (list || []).forEach(function (id) { skip[id] = until; }); }

  function poll() {
    clearTimeout(timer); timer = 0;
    if (!ids().length) return;
    var before = ids();
    Promise.resolve().then(function () { return ctx.watch(B.files(st)); }).then(function (r) {
      var m = (r && r.mtimes) || {};
      dispatch({type: 'baseline', mtimes: m});        // 기준을 못 잡았던 것은 여기서 잡는다
      dispatch({type: 'seen', mtimes: m});
      var gone = before.filter(function (id) { return !Object.prototype.hasOwnProperty.call(st.items, id); });
      if (gone.length) { render(); wrote(gone); ctx.reload(gone); }
    }, function () { /* 도우미가 잠깐 안 되면 다음 차례에 다시 */ }).then(schedule, schedule);
  }
  function schedule() { if (!timer && ids().length) timer = setTimeout(poll, EVERY); }

  function mark(screens, via) {
    var list = (screens || []).filter(function (s) { return s && s.id && s.file; });
    if (!list.length) return;
    dispatch({type: 'mark', screens: list, via: via, now: Date.now()});
    render();
    var fs = list.map(function (s) { return s.file; });
    Promise.resolve().then(function () { return ctx.watch(fs); }).then(function (r) {
      dispatch({type: 'baseline', mtimes: (r && r.mtimes) || {}});
    }, function () { /* 기준은 다음 차례 poll 에서 */ }).then(schedule, schedule);
  }
  function lift(id) {
    dispatch({type: 'lift', id: id});
    render();
  }
  function adopt() {                                  // 상태 파일 쪽이 바뀜 — 저장하지 않고 읽기만(쓴 곳이 이미 파일에 있다)
    st = B.load(ctx.getItem, ctx.key, warn);
    render();
    if (ids().some(function (id) { return st.items[id].mtime == null; })) poll(); else schedule();
  }

  // 도우미가 지켜본 화면 파일(GET /api/files) — 바뀐 카드만 다시
  var since = null, ftimer = 0, fwarned = false;
  function fpoll() {
    ftimer = 0;
    if (typeof document !== 'undefined' && document.hidden) { fnext(); return; }
    Promise.resolve().then(function () { return ctx.files(since == null ? -1 : since); }).then(function (r) {
      fwarned = false;
      if (!r || typeof r.seq !== 'number') { warn('[hd] /api/files 답이 깨졌어요'); return; }
      var first = since == null || r.seq < since;     // 처음 · 도우미가 다시 떴음 = 기준만 잡기
      since = r.seq;
      if (first || !Array.isArray(r.changed) || !r.changed.length) return;
      var now = Date.now(), t = B.refresh(r.changed, {known: ctx.known ? ctx.known() : [], busy: st, skip: skip, now: now,
                                                     modal: ctx.modalScreen ? ctx.modalScreen() : null});
      if (t.cards.length) { wrote(t.cards); ctx.reload(t.cards); }
      if (t.modal && ctx.reloadModal) ctx.reloadModal();
      if (r.changed.some(function (id) { return Object.prototype.hasOwnProperty.call(st.items, id); })) poll();   // 덮개 카드 = 걷는 길을 바로
    }, function (e) {
      if (!fwarned) { fwarned = true; warn('[hd] 바뀐 화면 파일을 받지 못했어요(다시 시도): ' + (e && e.message || e)); }
    }).then(fnext, fnext);
  }
  function fnext() { clearTimeout(ftimer); ftimer = setTimeout(fpoll, FILES_EVERY); }

  render(); schedule();
  if (ctx.files) fpoll();
  return {mark: mark, render: render, lift: lift, adopt: adopt, wrote: wrote};
}

HD.viewBusy = {mount: mount};
})();
