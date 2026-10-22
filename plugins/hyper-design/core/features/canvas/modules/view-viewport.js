/* View — 창 나누기(조각 6, H2·H3). 상태 규칙은 modules/viewport.js(Model), 여기는 둘째 칸 그리기·끌기·동시 스크롤.
   좌우 2분할: 오른쪽 칸(#vp2) = 판의 복사본(보기 전용 — 고치기는 왼쪽 판에서), 칸마다 따로 이동·배율, 왼쪽 아래 작은 배율 칩.
   복사본은 나눌 때와 refresh()(판이 바뀐 뒤) 다시 뜬다. 화면은 보이는 것만 불러온다.
   동시 스크롤 = 한 칸을 움직이면 다른 칸도 같은 만큼(배율은 따로).
   HD.viewViewport.mount(ctx) → {state(), dispatch(a), refresh(), follow(dx, dy)}
   ctx = {stage, host(칸을 넣을 곳), cam() → 왼쪽 판 {z, tx, ty}, panMain(dx, dy), clampZ(z), onFrame(iframe), onChange(state)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var V = HD.viewport, st = V.initial(), el = null, inner = null, chip = null, cam = null, driving = false, refT = 0, visT = 0;

  function apply() {
    if (!el) return;
    inner.style.transform = 'translate(' + cam.tx.toFixed(1) + 'px,' + cam.ty.toFixed(1) + 'px) scale(' + cam.z.toFixed(4) + ')';
    inner.dataset.zoom = cam.z.toFixed(4);
    chip.textContent = Math.round(cam.z * 100) + '%';
    clearTimeout(visT); visT = setTimeout(loadVisible, 100);
  }
  function loadVisible() {
    if (!el) return;
    var pr = el.getBoundingClientRect();
    inner.querySelectorAll('iframe[data-src]').forEach(function (f) {
      var r = f.parentNode.getBoundingClientRect();
      if (r.right > pr.left - 80 && r.left < pr.right + 80 && r.bottom > pr.top - 80 && r.top < pr.bottom + 80) {
        f.addEventListener('load', function () { ctx.onFrame(f); });
        f.src = f.getAttribute('data-src'); f.removeAttribute('data-src');
      }
    });
  }
  function copy() {                                   // 판 복사본: id 는 지우고(겹치지 않게), 화면은 보일 때 불러오게, 누르기는 막는다
    var c = ctx.stage.cloneNode(true);
    c.removeAttribute('id'); c.className = 'vp2-stage';
    c.querySelectorAll('[id]').forEach(function (n) { n.removeAttribute('id'); });
    c.querySelectorAll('iframe').forEach(function (f) {
      var s = f.getAttribute('src') || f.getAttribute('data-src');
      f.removeAttribute('src'); if (s) f.setAttribute('data-src', s);
    });
    c.inert = true;
    return c;
  }
  function open() {
    el = document.createElement('section');
    el.id = 'vp2'; el.className = 'vp2'; el.setAttribute('aria-label', '나눈 칸(보기 전용)');
    inner = copy(); chip = document.createElement('span'); chip.className = 'pz';
    el.appendChild(inner); el.appendChild(chip); ctx.host.appendChild(el);
    var c = ctx.cam(); cam = {z: c.z, tx: c.tx, ty: c.ty};
    wire(); apply();
  }
  function close() { if (el) el.remove(); el = inner = chip = cam = null; }

  function pan(dx, dy) {
    cam.tx += dx; cam.ty += dy; apply();
    if (st.sync) { driving = true; ctx.panMain(dx, dy); driving = false; }
  }
  function wire() {
    el.addEventListener('wheel', function (e) {
      e.preventDefault();
      var r = el.getBoundingClientRect(), k = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? el.clientHeight : 1, dx = e.deltaX * k, dy = e.deltaY * k;
      if (e.ctrlKey || e.metaKey) { cam = V.zoomAt(cam, e.clientX - r.left, e.clientY - r.top, ctx.clampZ(cam.z * Math.exp(-dy * 0.0022))); apply(); return; }
      if (e.shiftKey && !dx) { dx = dy; dy = 0; }
      pan(-dx, -dy);
    }, {passive: false});
    el.addEventListener('pointerdown', function (e) {
      if (e.button !== 0 && e.button !== 1) return;
      e.preventDefault();
      var x = e.clientX, y = e.clientY;
      el.setPointerCapture(e.pointerId); el.classList.add('drag');
      function mv(m) { pan(m.clientX - x, m.clientY - y); x = m.clientX; y = m.clientY; }
      function up() { el.classList.remove('drag'); el.removeEventListener('pointermove', mv); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); }
      el.addEventListener('pointermove', mv); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
    });
  }

  function dispatch(a) {
    var n = V.reduce(st, a); if (n === st) return st;
    var was = st.split; st = n;
    if (was === 'one' && st.split !== 'one') open(); else if (st.split === 'one') close();
    document.body.classList.toggle('split-lr', st.split === 'lr');
    ctx.onChange(st);
    return st;
  }
  function refresh() {                                // 판이 바뀐 뒤 복사본 다시(묶어서)
    if (!el) return;
    clearTimeout(refT);
    refT = setTimeout(function () { if (!el) return; var n = copy(); el.replaceChild(n, inner); inner = n; apply(); }, 400);
  }
  function follow(dx, dy) { if (el && st.sync && !driving && (dx || dy)) { cam.tx += dx; cam.ty += dy; apply(); } }

  return {state: function () { return st; }, dispatch: dispatch, refresh: refresh, follow: follow};
}

HD.viewViewport = {mount: mount};
})();
