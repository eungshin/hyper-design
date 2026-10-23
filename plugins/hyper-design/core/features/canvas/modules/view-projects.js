/* View — 위쪽 줄 '프로젝트 ▾' 메뉴(#246): 저장한 캔버스 목록을 도우미에서 받아 그리고, 줄을 누르면 그 캔버스를 새 탭에 연다.
   도우미가 없으면(ctx.api.on 거짓 — file:// 또는 도우미 꺼짐) 단추를 만들지 않고 아무것도 바꾸지 않는다.
   열 때마다 GET /api/projects → HD.projects.rows(줄 규칙) → 이름 · 상태(열림·꺼짐·없음) · 연 때, 지금 캔버스 표시, '없음' 줄은 못 누르고 까닭을 적는다.
   줄 누르기 → 빈 새 탭을 바로 열고(팝업 막힘 피하기) POST /api/open {name} → 받은 url 로 보낸다. 기다리는 동안 그 줄 aria-busy,
   실패하면 새 탭을 닫고 도우미의 한 줄({error})을 ctx.toast 로 — 조용히 삼키지 않는다.
   상태: 열린 메뉴·기다리는 줄 이름(이 모듈만). 지금 캔버스 = 도우미가 index.html 에 끼운 window.__hdOut.
   HD.feature('projects', {needs: ['api', '$', 'esc', 'toast']}) → {open(), close()} | {} (도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#pmenu{min-width:280px;max-width:420px;max-height:60vh;overflow:auto}' +
  '#pmenu .pj-row{min-height:40px;align-items:flex-start;flex-direction:column;justify-content:center;gap:1px;padding:4px 10px}' +
  '#pmenu .pj-top{display:flex;align-items:center;gap:8px;width:100%}' +
  '#pmenu .pj-name{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#pmenu .pj-cur{font-size:11px;color:var(--ui-on-badge-soft);background:var(--ui-badge-soft);border-radius:999px;padding:0 6px}' +
  '#pmenu .pj-st{margin-left:auto;font-size:12px;color:#6f6f6a}' +
  '#pmenu .pj-row[data-state="open"] .pj-st{color:var(--ui-ok)}' +
  '#pmenu .pj-when{font-size:11.5px;color:#8a8a85}' +
  '#pmenu .pj-why{font-size:11.5px;color:#8a8a85;white-space:normal}' +
  '#pmenu .pj-row:disabled{cursor:default;color:#9a9a95;background:none}' +
  '#pmenu .pj-row[aria-busy="true"]{cursor:progress;background:#F2F2EF}' +
  '#pmenu .pj-msg{padding:8px 10px;font-size:13px;color:#6f6f6a}';

function mount(ctx) {
  if (!ctx.api.on) return {};                       // file:// 또는 도우미 없음 — 단추도 메뉴도 없다
  var $ = ctx.$, esc = ctx.esc, P = HD.projects;
  var anchor = $('#wbtn'), bar = anchor ? anchor.parentNode : $('header .view');
  if (!bar) throw new Error('위쪽 줄(.view)이 없어요');

  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var btn = document.createElement('button');
  btn.type = 'button'; btn.className = 'vbtn wbtn'; btn.id = 'pbtn'; btn.textContent = '프로젝트 ▾';
  btn.title = '프로젝트 — 저장한 캔버스 열기';
  btn.setAttribute('aria-haspopup', 'menu'); btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'pmenu');
  bar.insertBefore(btn, anchor || null);
  var menu = document.createElement('div');
  menu.id = 'pmenu'; menu.className = 'wm'; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', '프로젝트'); menu.hidden = true;
  document.body.appendChild(menu);

  var busy = null, seq = 0;                          // busy = 여는 중인 프로젝트 이름 · seq = 늦게 온 목록 답 버리기

  function place() {
    var r = btn.getBoundingClientRect();
    menu.style.top = (r.bottom + 6) + 'px';
    menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, r.right - menu.offsetWidth)) + 'px';
  }
  function msg(t) { menu.innerHTML = '<div class="pj-msg">' + esc(t) + '</div>'; place(); }
  function draw(rows) {
    if (!rows.length) { msg('저장한 프로젝트가 없어요 — 터미널에서 hd save 로 넣어요'); return; }
    menu.innerHTML = rows.map(function (r) {
      return '<button type="button" class="wm-row pj-row" role="menuitem" data-name="' + esc(r.name) + '" data-state="' + r.state + '"' +
        (r.current ? ' aria-current="true"' : '') + (r.clickable ? '' : ' disabled aria-disabled="true"') +
        (busy === r.name ? ' aria-busy="true"' : '') + ' title="' + esc(r.why || r.out) + '">' +
        '<span class="pj-top"><span class="pj-name">' + esc(r.name) + '</span>' + (r.current ? '<span class="pj-cur">지금</span>' : '') +
        '<span class="pj-st">' + esc(busy === r.name ? '여는 중…' : r.word) + '</span></span>' +
        '<span class="pj-when">연 때 ' + esc(r.when) + '</span>' +
        (r.why ? '<span class="pj-why">' + esc(r.why) + '</span>' : '') + '</button>';
    }).join('');
    place();
  }
  function load() {
    var my = ++seq;
    msg('불러오는 중…');
    ctx.api.call('GET', '/api/projects').then(function (res) {
      if (my !== seq || menu.hidden) return;
      if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      var r = P.rows(res.body, window.__hdOut || null);
      if (r.bad) console.warn('[hd] 프로젝트 목록: ' + r.bad);
      draw(r.rows);
    }).catch(function (e) {
      if (my !== seq) return;
      var t = '프로젝트 목록을 불러오지 못했어요 — ' + (e && e.message || e);
      msg(t); ctx.toast(t);
    });
  }
  function open() { menu.hidden = false; btn.setAttribute('aria-expanded', 'true'); load(); }
  function close() { seq++; menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); }

  function go(row) {
    var name = row.dataset.name;
    if (busy) return;                                // 한 번에 하나만 연다
    busy = name; row.setAttribute('aria-busy', 'true');
    var stEl = row.querySelector('.pj-st'), was = stEl.textContent; stEl.textContent = '여는 중…';
    var tab = window.open('', '_blank');             // 누른 그 순간에 열어야 팝업 차단에 걸리지 않는다 — 주소는 답이 오면
    function done() { busy = null; row.removeAttribute('aria-busy'); stEl.textContent = was; }
    ctx.api.call('POST', '/api/open', {name: name}).then(function (res) {
      if (res.status !== 200 || !res.body || !res.body.url) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      done();
      var url = res.body.url;
      if (tab) { try { tab.opener = null; } catch (e) { /* 다른 출처면 못 바꿈 — 주소만 보낸다 */ } tab.location.href = url; }
      else if (!window.open(url, '_blank')) { ctx.toast('새 탭이 막혔어요 — 주소: ' + url, false, 8000); return; }
      close();
    }).catch(function (e) {
      done();
      if (tab) tab.close();
      ctx.toast('열지 못했어요 — ' + (e && e.message || e), false, 6000);
    });
  }

  btn.addEventListener('click', function () { if (menu.hidden) open(); else close(); });
  menu.addEventListener('click', function (e) {
    var b = e.target.closest('button.pj-row');
    if (b && !b.disabled) go(b);
  });
  document.addEventListener('pointerdown', function (e) {
    var t = e.target; if (menu.hidden || !t.closest || t.closest('#pmenu, #pbtn')) return;
    close();
  }, true);
  addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) close(); });
  return {open: open, close: close};
}

HD.viewProjects = {mount: mount};
HD.feature('projects', {needs: ['api', '$', 'esc', 'toast'], mount: mount});
})();
