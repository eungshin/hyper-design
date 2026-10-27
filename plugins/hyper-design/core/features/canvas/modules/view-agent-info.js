/* View — 대화창 아래 줄의 받는 터미널 정보(R28, 시안 A): 모델 이름(보기만, 툴팁 '모델은 Paseo에서 바꿔요') · 생각 깊이 알약 ⌄ + 메뉴 · 컨텍스트 고리 + %(툴팁 '컨텍스트 340k / 1M 토큰 · 34% 사용').
   자리 = 대화창(view-chat)이 도구 줄에 둔 [data-hd-agent-info] 칸 — 이 기능이 채운다(대화창은 칸만, 서로 부르지 않음). 받는 곳이 Paseo 에이전트가 아니면 칸째 숨김.
   읽기: GET /api/agents/info(열 때 · 받는 곳이 바뀔 때 'hd-agent'(잡는 단계) · 15초마다, 창이 숨었으면 건너뜀). 규칙(답 읽기·줄임 글·고리·메뉴)은 HD.agentInfo(Model).
   바꾸기: 메뉴에서 고르면 POST /api/agents/effort {effort}(서버가 paseo agent update --thinking) → 답으로 다시 그림. 실패 = 서버 까닭 토스트, 알약 그대로.
   상태 = 마지막 정보 · 열린 메뉴 · 바꾸는 중(모두 저장 안 함). 오류 탐지: 칸이 없음·옛 도우미(404)·못 닿음 = [hd] 경고 한 번 + 숨김(고리는 모르면 숨김 — 0% 가 아니다).
   HD.feature('agentInfo', {needs: ['api', 'toast', 'esc']}) → {refresh() → Promise, info()} | {}(도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '.hd-ainfo{position:relative;flex:0 4 auto;min-width:0;display:inline-flex;align-items:center;gap:2px;font:500 12px system-ui,sans-serif;color:#6b6b66}' +
  '.hd-ainfo[hidden]{display:none}' +
  '.hd-ainfo .ai-model{flex:0 1 auto;min-width:0;display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 6px;border-radius:8px;white-space:nowrap;cursor:default}' +
  '.hd-ainfo .ai-model span{overflow:hidden;text-overflow:ellipsis}' +
  '.hd-ainfo .ai-effort,.hd-ainfo .ai-ring{flex:none}' +
  '.hd-ainfo svg.ai-ic{flex:none;width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;opacity:.8}' +
  '.hd-ainfo .ai-effort{display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 6px 0 7px;border:1px solid rgba(0,0,0,.12);border-radius:8px;background:none;color:#4a4a46;font:500 12px system-ui,sans-serif;cursor:pointer;white-space:nowrap}' +
  '.hd-ainfo .ai-effort:hover,.hd-ainfo .ai-effort[aria-expanded="true"]{background:#F2F2EF;color:#2b2b29}' +
  '.hd-ainfo .ai-effort:disabled{opacity:.55;cursor:default}' +
  '.hd-ainfo .ai-effort svg.ai-dn{width:10px;height:10px;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;opacity:.7}' +
  '.hd-ainfo .ai-ring{display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 6px;border-radius:8px;font-size:11px;color:#8a8a85;cursor:default}' +
  '.hd-ainfo .ai-ring[hidden]{display:none}' +
  '.hd-ainfo .ai-ring svg{width:16px;height:16px;transform:rotate(-90deg)}' +
  '.hd-ainfo .ai-ring circle{fill:none;stroke-width:3}' +
  '.hd-ainfo .ai-ring .bg{stroke:#e4e4df}.hd-ainfo .ai-ring .fg{stroke:#4a4a46;stroke-linecap:round}' +
  '.hd-ainfo .ai-ring[data-level="high"] .fg{stroke:var(--ui-accent,#c2590a)}' +
  '.hd-ainfo .ai-menu{position:absolute;left:0;bottom:calc(100% + 8px);z-index:4;min-width:168px;margin:0;padding:4px;list-style:none;background:var(--ui-surface,#fff);border-radius:10px;box-shadow:0 0 0 1px rgba(0,0,0,.08),0 6px 20px rgba(0,0,0,.12)}' +
  '.hd-ainfo .ai-menu[hidden]{display:none}' +
  '.hd-ainfo .ai-menu .ai-mh{padding:4px 8px 2px;font-size:11px;color:#8a8a85}' +
  '.hd-ainfo .ai-menu button{display:flex;align-items:center;justify-content:space-between;gap:12px;width:100%;height:28px;padding:0 8px;border:0;border-radius:6px;background:none;color:#2b2b29;font:13px system-ui,sans-serif;text-align:left;cursor:pointer}' +
  '.hd-ainfo .ai-menu button:hover,.hd-ainfo .ai-menu button:focus-visible{background:#F2F2EF;outline:none}' +
  '.hd-ainfo .ai-menu button[aria-checked="true"]{background:#EEF0F6}' +
  '.hd-ainfo .ai-menu button i{font-style:normal;font-size:11px;color:#8a8a85}' +
  '.hd-ainfo .ai-tip{position:absolute;bottom:calc(100% + 8px);z-index:4;padding:5px 8px;border-radius:7px;background:#2b2b29;color:#f4f4f1;font:12px/16px system-ui,sans-serif;white-space:nowrap;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.18)}' +
  '.hd-ainfo .ai-tip[hidden]{display:none}' +
  // 좁은 대화창(탭 바에 자리를 준 360px · 대화 패널 안)에서는 모델 이름 글을 감추고 아이콘만(툴팁에 이름) — 받는 곳 알약·생각 깊이·고리가 먼저
  '#hdchat .ch-tools{container-type:inline-size}' +
  '@container (max-width: 440px){.hd-ainfo .ai-model span{display:none}.hd-ainfo .ai-model{padding:0 4px}}';

var POLL = 15000;
var IC_CHIP = '<svg class="ai-ic" viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/></svg>';
var IC_BRAIN = '<svg class="ai-ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a2 2 0 0 0-3-1zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/></svg>';
var IC_DN = '<svg class="ai-dn" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
var R = 6;

function mount(ctx) {
  if (!ctx.api || !ctx.api.on) return {};
  var A = HD.agentInfo, info = null, busy = false, warned = {}, el = null, loading = null, again = false;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);

  function warnOnce(k, msg) { if (warned[k]) return; warned[k] = 1; console.warn('[hd] 터미널 정보: ' + msg); }
  function slot() {
    var s = document.querySelector('[data-hd-agent-info]');
    if (!s) { warnOnce('slot', '대화창에 칸([data-hd-agent-info])이 없어요 — 모델·생각 깊이 줄 없이'); return null; }
    if (s !== el) { el = s; build(s); }
    return s;
  }
  function build(s) {
    s.classList.add('hd-ainfo');
    s.innerHTML = '<span class="ai-model" tabindex="0" aria-describedby="hdai-tip">' + IC_CHIP + '<span></span></span>' +
      '<button type="button" class="ai-effort" aria-haspopup="menu" aria-expanded="false" aria-controls="hdai-menu">' + IC_BRAIN + '<span></span>' + IC_DN + '</button>' +
      '<span class="ai-ring" tabindex="0" role="img" hidden><svg viewBox="0 0 16 16" aria-hidden="true"><circle class="bg" cx="8" cy="8" r="' + R + '"/><circle class="fg" cx="8" cy="8" r="' + R + '"/></svg><span></span></span>' +
      '<div class="ai-menu" id="hdai-menu" role="menu" aria-label="생각 깊이" hidden></div><div class="ai-tip" id="hdai-tip" role="tooltip" hidden></div>';
    var eff = s.querySelector('.ai-effort'), menuEl = s.querySelector('.ai-menu'), tipEl = s.querySelector('.ai-tip');
    eff.addEventListener('click', function () { if (menuEl.hidden) openMenu(); else closeMenu(); });
    menuEl.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-opt]'); if (!b) return;
      choose(b.dataset.opt);
    });
    menuEl.addEventListener('keydown', function (e) {
      var items = Array.prototype.slice.call(menuEl.querySelectorAll('button')), i = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); var n = items.length; items[((i < 0 ? 0 : i) + (e.key === 'ArrowDown' ? 1 : -1) + n) % n].focus(); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(); eff.focus(); }
    });
    function showTip(target, text) {
      if (!text) { tipEl.hidden = true; return; }
      tipEl.textContent = text; tipEl.hidden = false;
      var sr = s.getBoundingClientRect(), tr = target.getBoundingClientRect();
      tipEl.style.left = Math.max(0, tr.left - sr.left + tr.width / 2 - tipEl.offsetWidth / 2) + 'px';
    }
    [['.ai-model', function () { var t = s.querySelector('.ai-model span'); return t && !t.offsetWidth && info ? info.modelLabel + ' · ' + A.MODEL_TIP : A.MODEL_TIP; }], ['.ai-ring', function () { return info && info.ctx ? A.tip(info.ctx) : ''; }]].forEach(function (p) {
      var t = s.querySelector(p[0]);
      t.addEventListener('pointerenter', function () { showTip(t, p[1]()); });
      t.addEventListener('focus', function () { showTip(t, p[1]()); });
      t.addEventListener('pointerleave', function () { tipEl.hidden = true; });
      t.addEventListener('blur', function () { tipEl.hidden = true; });
    });
  }
  function draw() {
    var s = slot(); if (!s) return;
    if (!info || !info.show) { s.hidden = true; closeMenu(); return; }
    s.hidden = false;
    var m = s.querySelector('.ai-model');
    m.querySelector('span').textContent = info.modelLabel;
    m.setAttribute('aria-label', '모델 ' + info.modelLabel + ' — ' + A.MODEL_TIP);
    var eff = s.querySelector('.ai-effort');
    eff.querySelector('span').textContent = A.effortLabel(info.effort);
    eff.setAttribute('aria-label', '생각 깊이 ' + A.effortLabel(info.effort) + ' — 바꾸기');
    eff.title = '생각 깊이(effort)';
    eff.disabled = busy || !info.options.length;
    var ring = s.querySelector('.ai-ring');
    ring.hidden = !info.ctx;
    if (info.ctx) {
      var g = A.ring(info.ctx.pct, R), fg = ring.querySelector('.fg');
      fg.setAttribute('stroke-dasharray', g.dash + ' ' + g.len);
      fg.style.display = g.dash > 0 ? '' : 'none';
      ring.dataset.level = info.ctx.pct >= 80 ? 'high' : 'ok';
      ring.querySelector('span').textContent = info.ctx.pct + '%';
      ring.setAttribute('aria-label', A.tip(info.ctx));
    }
    if (!s.querySelector('.ai-menu').hidden) drawMenu();
  }
  function drawMenu() {
    var menuEl = el.querySelector('.ai-menu');
    menuEl.innerHTML = '<div class="ai-mh">생각 깊이 (effort)</div>' + A.menu(info.options, info.effort).map(function (o) {
      return '<button type="button" role="menuitemradio" data-opt="' + ctx.esc(o.id) + '" aria-checked="' + o.on + '"><span>' + ctx.esc(o.label) + '</span>' + (o.on ? '<i>지금</i>' : '') + '</button>';
    }).join('');
  }
  function openMenu() {
    if (!el || !info || !info.show || busy) return;
    drawMenu();
    var menuEl = el.querySelector('.ai-menu');
    menuEl.hidden = false; el.querySelector('.ai-effort').setAttribute('aria-expanded', 'true');
    var on = menuEl.querySelector('button[aria-checked="true"]') || menuEl.querySelector('button');
    if (on) on.focus();
  }
  function closeMenu() {
    if (!el) return;
    el.querySelector('.ai-menu').hidden = true; el.querySelector('.ai-effort').setAttribute('aria-expanded', 'false');
  }
  function set(next) {
    if (A.same(next, info)) return;
    info = next; draw();
  }
  function refresh() {
    if (loading) { again = true; return loading; }
    loading = ctx.api.call('GET', '/api/agents/info').then(function (r) {
      if (r.status !== 200) { warnOnce('http' + r.status, '도우미가 정보를 주지 않았어요(' + r.status + (r.body && r.body.error ? ' ' + r.body.error : '') + ') — 줄 없이'); set(null); return; }
      var p = A.parse(r.body);
      if (p.why === 'bad') warnOnce('bad', '정보 모양이 틀렸어요 — 줄 없이');
      set(p);
    }).catch(function (e) { warnOnce('net', '도우미에 닿지 못했어요(' + (e && e.message || e) + ')'); set(null); })
      .then(function () { loading = null; if (again) { again = false; return refresh(); } });
    return loading;
  }
  function choose(opt) {
    closeMenu();
    if (!info || busy || opt === info.effort) return;
    busy = true; draw();
    ctx.api.call('POST', '/api/agents/effort', {effort: opt}).then(function (r) {
      busy = false;
      if (r.status !== 200) {                              // 서버 까닭(502 는 이미 '생각 깊이를 바꾸지 못했어요 — …')
        var why = r.body && r.body.error || ('도우미 답 ' + r.status);
        ctx.toast(why.indexOf('생각 깊이') === 0 ? why : '생각 깊이를 바꾸지 못했어요 — ' + why); draw(); return;
      }
      var p = A.parse(r.body); info = p; draw();
      ctx.toast('생각 깊이 → ' + A.effortLabel(p.effort));
    }).catch(function (e) {
      busy = false; draw();
      ctx.toast('생각 깊이를 바꾸지 못했어요 — ' + (e && e.message || '도우미에 닿지 못했어요'));
    });
  }

  document.addEventListener('pointerdown', function (e) { if (el && !el.querySelector('.ai-menu').hidden && !el.contains(e.target)) closeMenu(); }, true);
  document.addEventListener('hd-agent', function () { setTimeout(refresh, 0); }, true);   // 받는 곳이 바뀜(칩 위에서 나고 올라오지 않아 잡는 단계)
  setInterval(function () { if (!document.hidden) refresh(); }, POLL);
  setTimeout(function () { draw(); refresh(); }, 0);   // 대화창(view-chat)이 칸을 만든 뒤 — 등록부는 이름 차례로 붙인다
  return {refresh: refresh, info: function () { return info; }};
}

HD.feature('agentInfo', {needs: ['api', 'toast', 'esc'], mount: mount});
})();
