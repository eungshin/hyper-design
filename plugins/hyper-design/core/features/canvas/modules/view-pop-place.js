/* View — 메모 창(#pop)이 열린 동안의 틀(#223): 머리 줄 끌어 옮기기·오른쪽 아래 모서리 크기·저장한 자리, 대상 카드 표시.
   규칙(가장 작은 크기·창 안으로·저장 글)은 modules/pop-place.js(Model). 상태 = 저장한 자리 하나(키 ctx.key = 'hd-pop', 모든 캔버스 공용).
   한 번 옮기거나 크기를 바꾸면 다음부터 늘 그 자리(지금 창 안으로 맞춤), 머리 줄 두 번 누르기 = 저장 지우고 자동 자리로.
   HD.viewPopPlace.mount(ctx) → {open(auto, cardEl), close(), saved()}
     open: 저장한 자리가 있으면 그것, 없으면 auto() → {x, y}(셸이 계산한 자동 자리) · cardEl = 메모 대상 카드(테두리 표시, 없으면 null)
   ctx = {pop, head(끄는 머리 줄 Node), key, getItem(k), setItem(k, v), removeItem(k), warn(msg)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var P = HD.popPlace, pop = ctx.pop, auto = null, target = null, drag = null;
  var grip = document.createElement('div');
  grip.className = 'prs'; grip.setAttribute('aria-hidden', 'true'); grip.title = '끌어서 크기 바꾸기';
  pop.appendChild(grip);
  ctx.head.title = '끌어서 옮기기 · 두 번 누르면 자동 자리로';

  function read() {
    var raw = null;
    try { raw = ctx.getItem(ctx.key); } catch (e) {}   // 저장소를 못 읽으면(막힌 브라우저) 자동 자리
    var r = P.parse(raw);
    if (r.bad) { ctx.warn('[hd] 메모 창 자리 저장값이 깨져 자동 자리로 돌아가요: ' + String(raw).slice(0, 80)); forget(); }
    return r.place;
  }
  function save(p) { try { ctx.setItem(ctx.key, P.serialize(p)); } catch (e) {} }   // 저장 공간이 없으면 이번 창에서만 그 자리
  function forget() { try { ctx.removeItem(ctx.key); } catch (e) {} }   // 지우기 실패는 다음 읽기에서 다시 깨진 값으로 잡힌다
  function vp() { return {w: innerWidth, h: innerHeight}; }
  function put(p) {                                  // 크기까지 정한 자리(저장한 자리·끄는 중)
    pop.classList.add('sized');
    pop.style.left = p.x + 'px'; pop.style.top = p.y + 'px'; pop.style.width = p.w + 'px'; pop.style.height = p.h + 'px';
  }
  function putAuto() {                               // 자동 자리 = 셸이 정한 왼쪽 위, 크기는 기본(CSS)
    pop.classList.remove('sized'); pop.style.width = ''; pop.style.height = '';
    var a = auto ? auto() : {x: 24, y: 80};
    pop.style.left = a.x + 'px'; pop.style.top = a.y + 'px';
  }
  function place() {
    var s = read(), v = vp();
    if (s) put(P.clamp(s, v.w, v.h)); else putAuto();
  }
  function now() { return {x: pop.offsetLeft, y: pop.offsetTop, w: pop.offsetWidth, h: pop.offsetHeight}; }   // 여는 움직임(scale)과 무관한 배치 값

  function start(e, kind) {
    if (e.button !== 0) return;
    if (kind === 'move' && e.target.closest && e.target.closest('button, textarea, input')) return;
    e.preventDefault(); e.stopPropagation();
    drag = {kind: kind, id: e.pointerId, sx: e.clientX, sy: e.clientY, from: now(), moved: false};
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
  }
  function track(e) {
    if (!drag || e.pointerId !== drag.id) return;
    var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy, f = drag.from, v = vp();
    if (!drag.moved && Math.hypot(dx, dy) < 3) return;
    drag.moved = true;
    put(P.clamp(drag.kind === 'move' ? {x: f.x + dx, y: f.y + dy, w: f.w, h: f.h} : {x: f.x, y: f.y, w: f.w + dx, h: f.h + dy}, v.w, v.h));
  }
  function end(e) {
    if (!drag || e.pointerId !== drag.id) return;
    var d = drag; drag = null;
    if (d.moved) save(now());                        // 옮기거나 크기를 바꾼 것만 저장(그냥 누르기는 아님)
  }
  [[ctx.head, 'move'], [grip, 'size']].forEach(function (hk) {
    hk[0].addEventListener('pointerdown', function (e) { start(e, hk[1]); });
    hk[0].addEventListener('pointermove', track);
    hk[0].addEventListener('pointerup', end);
    hk[0].addEventListener('pointercancel', end);
  });
  ctx.head.addEventListener('dblclick', function (e) { e.preventDefault(); forget(); putAuto(); });

  function mark(c) {
    if (target === c) return;
    if (target) target.classList.remove('memo-target');
    target = c || null;
    if (target) target.classList.add('memo-target');
  }
  return {
    open: function (autoFn, cardEl) { auto = autoFn; place(); mark(cardEl); },
    close: function () { drag = null; mark(null); },
    saved: function () { return read(); }
  };
}

HD.viewPopPlace = {mount: mount};
})();
