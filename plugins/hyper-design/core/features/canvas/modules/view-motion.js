/* View — 움직임: Ctrl/Cmd+클릭 "어디로 가나" 카메라 · 전환 메뉴(T) · 애니메이션 끄기.
   계획은 HD.camera.plan(순수, 숫자만). 시간·곡선은 여기서 CSS 변수(modules/motion.css)를 읽어 넘긴다.
   HD.viewMotion.mount(ctx) → {ctrlClick(e), stop(), go(from, toId), goLink(from, to), replay(id), toggleMenu()}
   ctx = {VL, LN, select(id|null), pane, rowsEl, CARD, $, $$, esc, prefs, savePrefs(), typing(e), getView(), setView(z,tx,ty), openModal(file,title), closeModal(), modalOpen(), mframe}
   Ctrl+클릭 대상: 카드 안 링크 요소(카드 iframe 에 hd-link-at 으로 물어 hd-link-go 답) · 선 태그 · 연결 패널 줄.
   고른 카드가 없을 때 링크를 Ctrl+클릭하면 그 쌍의 선 하나만 강조(LN.pair) — 다음 고르기·풀기로 해제. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var TRANSITIONS = [
  {id: 'focus', name: '포커스 진입 / 해제', where: '카드 누르기', dur: '--focus-dur', ease: '--focus-ease', basis: 'tokens'},
  {id: 'expand', name: '카드 펼치기 / 접기', where: '긴 화면 고르기', dur: '--resize-dur', ease: '--resize-ease', basis: '01-card-resize'},
  {id: 'camera', name: '카메라 이동', where: 'Ctrl+클릭', dur: '--camera-glide-dur', ease: '--camera-ease', basis: '08-page-side-by-side'},
  {id: 'modal', name: '크게 보기 모달 열기/닫기', where: '화면 클릭', dur: '--modal-open-dur', ease: '--modal-ease', basis: '06-modal'},
  {id: 'legend', name: '연결 패널 표시', where: '고른 화면의 연결', dur: '--panel-open-dur', ease: '--panel-ease', basis: '07-panel-reveal'},
  {id: 'dropdown', name: '드롭다운 / 팝오버', where: '색 드롭다운 · 메모 · 이 메뉴', dur: '--dropdown-open-dur', ease: '--dropdown-ease', basis: '05-menu-dropdown'},
  {id: 'tooltip', name: '태그·툴팁 등장', where: '선 태그 · 단축키 안내', dur: '--tt-in-dur', ease: '--tt-in-ease', basis: '17-tooltip'}
];

function mount(ctx) {
  var C = HD.camera, VL = ctx.VL, pane = ctx.pane, CARD = ctx.CARD, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, root = document.documentElement;
  var raf = 0, anim = null, pulseT = 0;
  var menu = $('#tmenu'), btn = $('#tbtn');

  function css(name) { return getComputedStyle(root).getPropertyValue(name).trim(); }
  function msOf(name, d) { return C.ms(css(name), d); }
  function reduced() {
    if (ctx.prefs.motion === false) return true;
    try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; }
  }
  function setMotion(on) {
    ctx.prefs.motion = !!on; ctx.savePrefs();
    document.body.classList.toggle('nomotion', !on);
    var cb = $('#tmOff'); if (cb) cb.checked = !on;
  }

  /* ---------- 좌표: 화면(client) → 판(stage) ---------- */
  function toStage(cx, cy) { var r = pane.getBoundingClientRect(), v = ctx.getView(); return {x: (cx - r.left - v.tx) / v.z, y: (cy - r.top - v.ty) / v.z}; }
  function phoneBox(id) {
    var c = VL.cardEl(id); if (!c) return null;
    var r = $('.phone', c).getBoundingClientRect(), a = toStage(r.left, r.top), b = toStage(r.right, r.bottom);
    return {x: a.x, y: a.y, w: b.x - a.x, h: b.y - a.y};
  }
  function elemPoint(id, rect) {                      // 카드 안 요소(카드 iframe 좌표 rect)의 가운데 → 판 좌표
    var p = phoneBox(id); if (!p) return null;
    if (!rect) return {x: p.x + p.w / 2, y: p.y + Math.min(p.h, CARD.h) / 2};
    var s = p.w / CARD.w;
    return {x: p.x + (rect.x + rect.w / 2) * s, y: p.y + (rect.y + rect.h / 2) * s};
  }

  /* ---------- 카메라 ---------- */
  function stop() {
    if (!anim) return;
    cancelAnimationFrame(raf); anim = null;
    if (window.__hdCam) window.__hdCam.running = false;
  }
  function pulse(id) {
    var c = VL.cardEl(id); if (!c) return;
    clearTimeout(pulseT);
    $$('.card.pulse', ctx.rowsEl).forEach(function (n) { n.classList.remove('pulse'); });
    c.style.setProperty('--ph', $('.phone', c).offsetHeight + 'px');
    void c.offsetWidth;
    c.classList.add('pulse');
    pulseT = setTimeout(function () { c.classList.remove('pulse'); }, msOf('--camera-pulse-dur', 500) + 60);
  }
  function go(from, toId) {
    var to = phoneBox(toId); if (!from || !to) return false;
    stop();
    var v = ctx.getView(), view = {w: pane.clientWidth, h: pane.clientHeight, z: v.z, tx: v.tx, ty: v.ty};
    var keys = C.plan(from, to, view, {centre: msOf('--camera-centre-dur', 250), glide: msOf('--camera-glide-dur', 600), margin: 24, reduced: reduced()});
    var ease = C.parseEase(css('--camera-ease')), end = keys[keys.length - 1];
    window.__hdCam = {to: toId, keys: keys, running: keys.length > 1, started: performance.now()};
    if (keys.length === 1) { ctx.setView(end.z, end.tx, end.ty); pulse(toId); return true; }   // 움직임 줄이기 · 애니메이션 끄기: 바로 끝 상태
    var t0 = performance.now();
    anim = {to: toId};
    var step = function (now) {
      if (!anim) return;
      var t = Math.max(0, now - t0), s = C.at(keys, t, ease, view);
      ctx.setView(s.z, s.tx, s.ty);
      if (t >= end.t) { anim = null; window.__hdCam.running = false; pulse(toId); return; }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return true;
  }
  function goLink(from, to) {                         // 연결 하나: 출발 요소(고른 화면이면 그 버튼, 아니면 카드 가운데) → 도착 카드
    var m = VL.model(from), it = null;
    if (m) m.items.forEach(function (x) { if (!it && x.to === to) it = x; });
    return go(elemPoint(from, it && it.rect), to);
  }
  function frameCard(win) {
    var hit = null;
    $$('.card', ctx.rowsEl).forEach(function (c) { var f = $('.phone iframe', c); if (f && f.contentWindow === win) hit = c.dataset.id; });
    return hit;
  }
  function askAt(card, cx, cy) {                       // 카드 iframe 에 "이 자리의 링크는?" (그냥 클릭은 덮개가 받으므로 화면은 이동하지 않는다)
    var f = $('.phone iframe', card); if (!f || !f.contentWindow || f.hasAttribute('data-src')) return;
    var r = $('.phone', card).getBoundingClientRect(), s = r.width / CARD.w;
    try { f.contentWindow.postMessage({type: 'hd-link-at', x: (cx - r.left) / s, y: (cy - r.top) / s}, '*'); } catch (e) {}
  }
  function ctrlClick(e) {
    var t = e.target, cl = function (q) { return t && t.closest ? t.closest(q) : null; };
    var row = cl('#legend .lgrow[data-to]') || cl('.alabel'), cover = cl('.cover');
    if (row) { goLink(row.getAttribute('data-from'), row.getAttribute('data-to')); return true; }
    if (cover) { askAt(cover.closest('.card'), e.clientX, e.clientY); return true; }
    return false;
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || d.type !== 'hd-link-go' || !d.to) return;
    var id = frameCard(e.source), inModal = !id && ctx.mframe && e.source === ctx.mframe.contentWindow;
    if (inModal) { id = String(d.screen || ''); ctx.closeModal(); }
    if (!id || !VL.cardEl(id) || !VL.cardEl(String(d.to))) return;
    if (!ctx.rowsEl.querySelector('.card.picked')) ctx.LN.pair(id, String(d.to));   // 고른 카드가 없으면: 그 쌍의 선 하나만 강조
    go(elemPoint(id, inModal ? null : d.rect), String(d.to));
  });

  /* ---------- 전환 메뉴 ---------- */
  function renderMenu() {
    menu.innerHTML = '<h2>전환</h2>' + TRANSITIONS.map(function (x) {
      return '<div class="trow" data-t="' + x.id + '" title="' + esc(x.basis) + '"><span class="tn">' + esc(x.name) + '</span><span class="tw">' + esc(x.where) + '</span>' +
        '<span class="tv" title="' + esc(x.dur + ' · ' + x.ease) + '">' + esc(css(x.dur) + ' · ' + css(x.ease)) + '</span>' +
        '<button type="button" class="tplay" data-play="' + x.id + '">▶ 보기</button></div>';
    }).join('') + '<label class="toff"><input type="checkbox" id="tmOff"' + (ctx.prefs.motion === false ? ' checked' : '') + '> 애니메이션 끄기</label>';
  }
  function openMenu() {
    renderMenu();
    var hd = document.querySelector('.hd'); menu.style.top = ((hd ? hd.getBoundingClientRect().bottom : 56) + 8) + 'px';
    menu.hidden = false; menu.classList.remove('is-closing'); menu.classList.add('is-open');
    btn.setAttribute('aria-expanded', 'true');
  }
  function closeMenu(after) {
    if (menu.hidden) { if (after) after(); return; }
    menu.classList.remove('is-open'); menu.classList.add('is-closing'); btn.setAttribute('aria-expanded', 'false');
    setTimeout(function () { if (menu.classList.contains('is-closing')) { menu.classList.remove('is-closing'); menu.hidden = true; } if (after) after(); }, msOf('--dropdown-close-dur', 150));
  }
  function menuOpen() { return !menu.hidden && !menu.classList.contains('is-closing'); }
  function toggleMenu() { if (menuOpen()) closeMenu(); else openMenu(); }
  btn.addEventListener('click', toggleMenu);
  menu.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-play]'); if (b) { e.preventDefault(); replay(b.dataset.play); }
  });
  menu.addEventListener('change', function (e) { if (e.target.id === 'tmOff') setMotion(!e.target.checked); });
  document.addEventListener('click', function (e) {
    var t = e.target; if (!menuOpen() || !t.closest || t.closest('#tmenu') || t.closest('#tbtn') || t.closest('#modal')) return;
    closeMenu();
  }, true);
  addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && menuOpen()) { closeMenu(); return; }
    if (ctx.typing(e) || e.ctrlKey || e.metaKey || e.altKey) return;
    if ((e.key || '').toLowerCase() === 't' && !ctx.modalOpen() && document.body.dataset.tab === 'screens') { e.preventDefault(); toggleMenu(); }
  });

  // ▶ 보기: 진짜 요소에서 그 전환을 다시 한다
  function firstCards() { return $$('.card', ctx.rowsEl).map(function (c) { return c.dataset.id; }); }
  function replay(id) {
    var ids = firstCards(), pk = ctx.rowsEl.querySelector('.card.picked'), fid = pk ? pk.dataset.id : null, lg = $('#legend');
    if (id === 'focus') {
      var f = fid || ids[0];
      if (fid) { ctx.select(null); setTimeout(function () { ctx.select(f); }, msOf('--focus-dur', 250)); }
      else ctx.select(f);
    } else if (id === 'expand') {
      VL.demoExpand(ids.filter(function (x) { return x !== fid; })[0]);
    } else if (id === 'camera') {
      var m = fid && VL.model(fid);
      if (!(m && m.items.length && goLink(fid, m.items[0].to))) go(elemPoint(ids[0], null), ids[1] || ids[0]);
    } else if (id === 'modal') {
      var cv = $('.card[data-id] .cover', ctx.rowsEl);
      if (cv) { ctx.openModal(cv.dataset.file, cv.dataset.title); setTimeout(function () { ctx.closeModal(); }, 900); }
    } else if (id === 'legend') {
      if (!lg.hidden) { lg.hidden = true; void lg.offsetWidth; lg.hidden = false; }
      else ctx.select(ids[0]);
    } else if (id === 'dropdown') {
      if (!lg.hidden) { ctx.LN.openDropdown(); setTimeout(ctx.LN.closeDropdown, 900); }
      else closeMenu(function () { setTimeout(openMenu, 60); });
    } else if (id === 'tooltip') {
      var tags = $$('.alabel.on', ctx.rowsEl), kh = $('#khint');
      tags.forEach(function (n) { n.style.animation = ''; n.classList.remove('on'); });
      if (kh) { kh.style.animation = 'none'; void kh.offsetWidth; kh.style.animation = ''; }
      void root.offsetWidth;
      tags.forEach(function (n) { n.classList.add('on'); });
      if (!tags.length && !fid) ctx.select(ids[0]);
    }
  }

  setMotion(ctx.prefs.motion !== false);
  return {ctrlClick: ctrlClick, stop: stop, go: go, goLink: goLink, replay: replay, toggleMenu: toggleMenu, TRANSITIONS: TRANSITIONS};
}

HD.viewMotion = {mount: mount, TRANSITIONS: TRANSITIONS};
})();
