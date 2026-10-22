/* View — "AI 수정 중" 덮개(Q2b, D14). 상태 규칙은 modules/busy.js(Model), 여기는 카드 위 덮개 그리기·2초마다 파일 보기.
   덮개 = 카드 .phone 안 <div class="busy" data-via="paseo|queue" role="status">: Paseo → 도는 표시 + "AI 수정 중",
   대기열 → "대기열에 있음" + [걷기](손으로 걷기, 다시 부르지 않음). 화면 파일이 바뀌면 걷고 그 카드만 다시 부른다.
   덮개가 하나라도 있는 동안만 ctx.watch 를 2000ms 마다 부른다. 상태는 ctx.key 로 저장해 새로 고쳐도 남는다.
   HD.viewBusy.mount(ctx) → {mark(screens:[{id, file}], via), render(), lift(id)}
   ctx = {cardEl(id) → .card|null, watch(files) → Promise<{mtimes}>, reload(ids), getItem(k), setItem(k, v), key, toast(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var EVERY = 2000;

function mount(ctx) {
  var B = HD.busy, st = B.load(ctx.getItem, ctx.key), els = {}, timer = 0;

  function dispatch(a) {
    var n = B.reduce(st, a);
    if (n !== st) { st = n; B.save(st, ctx.setItem, ctx.key); }
    return st;
  }
  function ids() { return Object.keys(st.items); }

  function draw(id, it) {                             // 카드 하나에 덮개(이미 맞게 있으면 그대로)
    var card = ctx.cardEl(id), host = card && (card.querySelector('.phone') || card), el = els[id];
    if (!host) { if (el) { el.remove(); delete els[id]; } return; }
    if (el && el.parentNode === host && el.getAttribute('data-via') === it.via) return;
    if (el) el.remove();
    el = document.createElement('div');
    el.className = 'busy'; el.setAttribute('data-via', it.via); el.setAttribute('data-id', id); el.setAttribute('role', 'status');
    if (it.via === 'paseo') {
      var sp = document.createElement('span'); sp.className = 'busy-spin'; sp.setAttribute('aria-hidden', 'true'); el.appendChild(sp);
    }
    var tx = document.createElement('span'); tx.className = 'busy-txt';
    tx.textContent = it.via === 'paseo' ? 'AI 수정 중' : '대기열에 있음';
    el.appendChild(tx);
    if (it.via === 'queue') {
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

  function poll() {
    timer = 0;
    if (!ids().length) return;
    var before = ids();
    Promise.resolve().then(function () { return ctx.watch(B.files(st)); }).then(function (r) {
      var m = (r && r.mtimes) || {};
      dispatch({type: 'baseline', mtimes: m});        // 기준을 못 잡았던 것은 여기서 잡는다
      dispatch({type: 'seen', mtimes: m});
      var gone = before.filter(function (id) { return !Object.prototype.hasOwnProperty.call(st.items, id); });
      if (gone.length) { render(); ctx.reload(gone); }
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

  render(); schedule();
  return {mark: mark, render: render, lift: lift};
}

HD.viewBusy = {mount: mount};
})();
