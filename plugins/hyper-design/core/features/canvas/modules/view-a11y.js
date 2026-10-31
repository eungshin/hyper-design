/* View — 접근성 검사(R59): 크게 보기 머리 줄 '접근성' 단추 → 연 화면 안에서 axe-core 검사 → 결과 창(요약·줄마다 문제·요소·AI로 고치기)·번호 핀. 규칙(규칙 표·차례·글·자리)은 HD.a11y(Model).
   길: 화면 틀에 palette.js 메시지 {type:'hd-a11y', tag, src, rules} — 틀이 axe.min.js(out/axe.min.js, 이 페이지 기준 주소)를 제 문서에 한 번 끼워 axe.run 하고 hd-a11y-r 로 답한다.
     직접 부르지 않는 까닭: file:// 로 연 판에서 크게 보기 iframe 문서는 읽을 수 없다(Chromium — contentDocument = null). 메시지는 file:// · 도우미 http 둘 다 같다.
     axe 는 검사할 때만 읽힌다(판을 여는 데는 0). 다른 출처 화면(앱 카드 개발 서버 주소)은 단추를 끄고(aria-disabled) 까닭을 툴팁·토스트로.
   결과 창 #a11yPanel: 크게 보기 창 옆(HD.a11y.place → HD.popPlace.clamp) · 머리 '문제 N · 대비 n …' · 줄 = 번호(핀과 같은 색) · 문제 글 · 요소 이름 · [AI로 고치기].
     줄에 올리기·누르기 = 그 요소 테두리 + 크게 보기 굴림 칸에서 보이게 굴림(R57 #mbox 좌표 = 화면 CSS px × 배율 — 메모 핀·고른 요소 테두리와 같은 자리 맞춤).
   핀: #mbox 안 층 .a11y-layer — 문제 요소마다 번호 핀 + 테두리(색 = HD.a11y.tone, 있는 --ui-* 토큰). 배율이 바뀌면 셸 drawPins() → paint().
   AI로 고치기: 셸 pick(screen, hit)(크게 보기 선택 도구로 그 요소를 고름 = 대화창 요소 칩 — 기존 길) + 의도 'hd-chat-prefill' {text}(대화창 입력칸에 글만, 보내지 않음).
     읽기만 탭은 HD.readOnly.CONTROLS 의 '.a11y-fix' 로 막힌다(보내기 규칙 그대로) — 검사 자체는 쓰지 않으니 된다.
   걷기: Esc(떠 있는 층 'a11y', escOnly — 누르기로는 닫히지 않음) · 크게 보기 닫기 · 틀이 다시 실림(다른 화면). 다시 검사하면 바꿔 그린다.
   상태(저장하지 않음) = 지금 결과(화면·문제 목록·평평한 노드) · 검사 중 tag · 강조한 줄 · 실릴 때 검사할 표시.
   오류 탐지: axe.min.js 없음·못 읽음 = [hd] 경고 한 번 + 토스트 HD.a11y.MISSING · axe.run 실패 = 토스트(까닭) · 2초 안에 받았음 답 없음 = 토스트 NO_PALETTE ·
     30초 안에 끝나지 않음 = 토스트 · 결과 모양이 깨짐 = [hd] 경고 + 토스트 · 셸이 attach 하지 않음 = [hd] 경고 한 번(단추 눌러도 아무것도 안 함) · 대화창이 prefill 을 받지 않음 = [hd] 경고 + 토스트.
   HD.feature('a11y', {needs: ['$', 'esc', 'toast', 'warn']}) → {attach(shell), run(), runOnLoad(), clear(), paint(), layer, result()}
     shell = {modal() → {open, screen, scale, frame, box(#mbox), view(#mview), win(#mwin), bar(.mbar)}, pick(screen, hit) → 골랐나} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '#ma11y{flex:none;height:24px;display:flex;align-items:center;gap:4px;padding:0 8px;border:0;border-radius:6px;background:none;color:#8a8a85;font-size:12px;font-weight:500;font-family:inherit;cursor:pointer}' +
  '#ma11y:hover,#ma11y:focus-visible{background:#F2F2EF;color:#2b2b29;outline:0}' +
  '#ma11y svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}' +
  '#ma11y[aria-disabled="true"]{opacity:.4;cursor:not-allowed}#ma11y[aria-busy="true"]{color:#2b2b29;cursor:progress}' +
  '#a11yPanel{position:fixed;z-index:26;display:flex;flex-direction:column;background:var(--ui-surface,#fff);border:1px solid rgba(0,0,0,.08);border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.18);' +
    'font:13px/1.4 system-ui,sans-serif;color:var(--ui-primary,#2b2b29);overflow:hidden}#a11yPanel[hidden]{display:none}' +
  '#a11yPanel .a11y-head{flex:none;display:flex;align-items:center;gap:8px;padding:10px 8px 8px 14px;border-bottom:1px solid var(--ui-line,#e3e3df)}' +
  '#a11yPanel .a11y-head b{font-size:13px}#a11yPanel .a11y-sum{flex:1;min-width:0;color:var(--ui-muted,#8a8a85);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#a11yPanel .a11y-x{flex:none;width:24px;height:24px;border:0;border-radius:6px;background:none;color:#8a8a85;cursor:pointer;display:grid;place-items:center;padding:0}' +
  '#a11yPanel .a11y-x:hover{background:#F2F2EF;color:#2b2b29}#a11yPanel .a11y-x svg{width:12px;height:12px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}' +
  '#a11yPanel ol{flex:1;min-height:0;overflow:auto;margin:0;padding:4px 0;list-style:none;scrollbar-width:thin}' +
  '#a11yPanel li{display:flex;align-items:flex-start;gap:8px;padding:7px 10px 7px 12px;cursor:pointer}#a11yPanel li:hover,#a11yPanel li.hi{background:#F5F5F2}' +
  '#a11yPanel .a11y-no{flex:none;min-width:20px;height:20px;margin-top:1px;padding:0 4px;border-radius:999px;background:var(--a11y-tone);color:#fff;font-size:11px;font-weight:700;display:grid;place-items:center}' +
  '#a11yPanel .a11y-t{flex:1;min-width:0}#a11yPanel .a11y-t small{display:block;margin-top:2px;color:var(--ui-muted,#8a8a85);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#a11yPanel .a11y-fix{flex:none;height:24px;padding:0 8px;border:1px solid var(--ui-line,#e3e3df);border-radius:6px;background:#fff;color:#2b2b29;font-size:12px;font-family:inherit;cursor:pointer;white-space:nowrap}' +
  '#a11yPanel .a11y-fix:hover{background:#F2F2EF}' +
  '#a11yPanel .a11y-foot{flex:none;margin:0;padding:6px 14px 8px;border-top:1px solid var(--ui-line,#e3e3df);color:var(--ui-muted,#8a8a85);font-size:11px}' +
  '.a11y-layer{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none}' +
  '.a11y-box{position:absolute;box-sizing:border-box;border:2px solid var(--a11y-tone);border-radius:3px;opacity:.55}.a11y-box.hi{opacity:1;box-shadow:0 0 0 3px rgba(255,255,255,.8)}' +
  '.a11y-pin{position:absolute;pointer-events:auto;cursor:pointer;border:0;font-family:inherit;transform:translate(-40%,-40%);min-width:22px;height:22px;padding:0 4px;border-radius:999px;' +
    'background:var(--a11y-tone);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,.3)}' +
  '.a11y-pin.hi{box-shadow:0 0 0 3px #fff,0 0 0 5px var(--ui-mark,#2b2b29)}';
var ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="4.5" r="1.6"/><path d="M5 8.5l7 1.5 7-1.5M12 10v5M12 15l-3.5 6M12 15l3.5 6"/></svg>';
var X = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
var ACK_MS = 2000, RUN_MS = 30000, W = 320;

function mount(ctx) {
  var A = HD.a11y, esc = ctx.esc, sh = null, warned = {}, seq = 0;
  var res = null, flat = [], busy = null, onLoad = false, hiK = -1;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  function warnOnce(k, m) { if (warned[k]) return; warned[k] = true; ctx.warn('[hd] ' + m); }

  var btn = document.createElement('button');
  btn.type = 'button'; btn.id = 'ma11y'; btn.setAttribute('aria-label', '접근성 검사');
  btn.innerHTML = ICON + '<span>접근성</span>';
  var bar = ctx.$('#modal .mbar'), mclose = ctx.$('#mclose');
  if (bar) bar.insertBefore(btn, mclose && mclose.parentNode === bar ? mclose : null);
  else warnOnce('bar', '크게 보기 머리 줄(.mbar)이 없어요 — 접근성 단추 없이');

  var panel = document.createElement('div');
  panel.id = 'a11yPanel'; panel.hidden = true; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', '접근성 검사 결과');
  document.body.appendChild(panel);
  var layer = document.createElement('div'); layer.className = 'a11y-layer';

  function modal() { return sh ? sh.modal() : {open: false}; }
  function cross(f) {                                    // 다른 출처 화면(앱 카드 개발 서버) — 틀 문서에 메시지는 가도 검사를 약속하지 않는다(v1)
    var src = f && f.getAttribute('src'); if (!src) return false;
    try { var u = new URL(src, location.href); return /^https?:$/.test(u.protocol) && u.origin !== location.origin; } catch (e) { return false; }
  }
  function sync() {                                      // 단추 상태 = 지금 크게 보기 화면
    var m = modal(), x = m.open && cross(m.frame);
    if (x) { btn.setAttribute('aria-disabled', 'true'); btn.title = A.CROSS; }
    else { btn.removeAttribute('aria-disabled'); btn.title = '접근성 검사 — 글자 대비·이름 없는 단추·그림 설명·누르는 크기 (v1 규칙 ' + A.RULES.length + '개)'; }
    if (busy) btn.setAttribute('aria-busy', 'true'); else btn.removeAttribute('aria-busy');
  }

  function stop() { if (busy) { clearTimeout(busy.ackT); clearTimeout(busy.runT); } busy = null; sync(); }
  function clear() {                                     // 결과·핀·창 걷기(검사 중이면 그것도 버림)
    stop(); res = null; flat = []; hiK = -1;
    panel.hidden = true; panel.innerHTML = ''; layer.innerHTML = '';
    if (layer.parentNode) layer.parentNode.removeChild(layer);
  }
  function fail(msg) { stop(); ctx.toast(msg); }

  function run() {
    if (!sh) { warnOnce('attach', '접근성 검사: 셸이 attach 하지 않았어요 — 검사 없이'); return; }
    var m = modal(); if (!m.open || !m.frame) return;
    if (cross(m.frame)) { ctx.toast(A.CROSS); return; }
    if (busy) return;                                    // 검사 중 — 두 번 누르기는 하나로
    clear();
    var win = m.frame.contentWindow; if (!win) { ctx.toast(A.NO_PALETTE); return; }
    var tag = 'a11y-' + (++seq) + '-' + Date.now();
    busy = {tag: tag, win: win, screen: m.screen, acked: false, src: new URL('axe.min.js', location.href).href};
    busy.ackT = setTimeout(function () { if (busy && busy.tag === tag && !busy.acked) fail(A.NO_PALETTE); }, ACK_MS);
    busy.runT = setTimeout(function () { if (busy && busy.tag === tag) fail('접근성 검사가 ' + (RUN_MS / 1000) + '초 안에 끝나지 않았어요'); }, RUN_MS);
    sync();
    try { win.postMessage({type: 'hd-a11y', tag: tag, src: busy.src, rules: A.RULES.slice()}, '*'); }
    catch (e) { fail('접근성 검사를 시작하지 못했어요 — ' + (e && e.message || e)); }
  }

  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || d.type !== 'hd-a11y-r' || !busy || d.tag !== busy.tag || e.source !== busy.win) return;
    if (d.state === 'run') { busy.acked = true; return; }
    var b = busy; stop();
    if (d.state === 'error') {
      if (d.why === 'load') { warnOnce('axe', '접근성 검사 파일(axe.min.js)을 읽지 못했어요: ' + b.src + ' — ' + (d.message || '')); ctx.toast(A.MISSING); }
      else ctx.toast('접근성 검사가 실패했어요 — ' + (d.message || '까닭 모름'));
      return;
    }
    var bad = A.check(d.result);
    if (bad) { ctx.warn('[hd] 접근성 검사: ' + bad); ctx.toast('접근성 검사 결과를 읽지 못했어요 — ' + bad); return; }
    show(String(d.screen || b.screen || ''), A.items(d.result));
  });

  function show(screen, list) {
    if (!list.length) { clear(); ctx.toast(A.EMPTY); return; }
    res = {screen: screen, items: list}; flat = [];
    list.forEach(function (it) { it.nodes.forEach(function (n) { flat.push({it: it, n: n}); }); });
    var rows = flat.map(function (x, k) {
      return '<li data-k="' + k + '" data-rule="' + esc(x.it.rule) + '" data-impact="' + esc(x.n.impact) + '" style="--a11y-tone:' + A.tone(x.n.impact) + '" title="' + esc(x.it.hint) + '">' +
        '<span class="a11y-no">' + (k + 1) + '</span><span class="a11y-t">' + esc(x.n.text) + '<small>' + esc(x.n.label + (x.n.detail ? ' · ' + x.n.detail : '')) + '</small></span>' +
        '<button type="button" class="a11y-fix" data-k="' + k + '">AI로 고치기</button></li>';
    }).join('');
    panel.innerHTML = '<div class="a11y-head"><b>접근성</b><span class="a11y-sum">' + esc(A.summary(list)) + '</span>' +
      '<button type="button" class="a11y-x" aria-label="접근성 결과 닫기" title="닫기 (Esc)">' + X + '</button></div>' +
      '<ol aria-label="접근성 문제">' + rows + '</ol><p class="a11y-foot">v1 규칙 ' + A.RULES.length + '개 · axe-core</p>';
    panel.hidden = false;
    paint();
  }

  function rectOf(n) { var r = n && n.hit && n.hit.rect; return r && isFinite(r.x) && isFinite(r.y) && r.w >= 0 && r.h >= 0 ? r : null; }
  function placePanel() {
    var m = modal(); if (panel.hidden || !m.open || !m.win) return;
    panel.style.height = ''; panel.style.width = W + 'px';
    var wr = m.win.getBoundingClientRect(), h = panel.scrollHeight + 2;
    var p = A.place({left: wr.left, top: wr.top, right: wr.right, bottom: wr.bottom}, {w: W, h: h}, innerWidth, innerHeight);
    panel.style.left = p.x + 'px'; panel.style.top = p.y + 'px'; panel.style.width = p.w + 'px'; panel.style.height = p.h + 'px';
  }
  function paint() {                                     // 핀·테두리(#mbox 좌표 = 화면 px × 배율) + 창 자리 — 배율·창 크기가 바뀔 때마다
    var m = modal();
    if (!res || !m.open || m.screen !== res.screen || !m.box) { layer.innerHTML = ''; return; }
    if (layer.parentNode !== m.box) m.box.appendChild(layer);
    var s = m.scale || 1, h = '';
    flat.forEach(function (x, k) {
      var r = rectOf(x.n); if (!r) return;
      var tone = A.tone(x.n.impact), hi = k === hiK ? ' hi' : '';
      h += '<div class="a11y-box' + hi + '" data-k="' + k + '" style="--a11y-tone:' + tone + ';left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px;width:' + (r.w * s) + 'px;height:' + (r.h * s) + 'px"></div>' +
           '<button type="button" class="a11y-pin' + hi + '" data-k="' + k + '" data-impact="' + esc(x.n.impact) + '" aria-label="접근성 문제 ' + (k + 1) + ' — ' + esc(x.n.text) + '" style="--a11y-tone:' + tone + ';left:' + (r.x * s) + 'px;top:' + (r.y * s) + 'px">' + (k + 1) + '</button>';
    });
    layer.innerHTML = h;
    placePanel();
  }

  function mark(k) {
    hiK = k;
    Array.prototype.forEach.call(panel.querySelectorAll('li'), function (li) { li.classList.toggle('hi', +li.dataset.k === k); });
    Array.prototype.forEach.call(layer.querySelectorAll('[data-k]'), function (el) { el.classList.toggle('hi', +el.dataset.k === k); });
  }
  function reveal(k) {                                   // 그 요소가 크게 보기 굴림 칸에 보이게(R57 — #mview 굴림, 배율 곱한 자리)
    var m = modal(), x = flat[k], r = x && rectOf(x.n), v = m.view; if (!r || !v) return;
    var s = m.scale || 1, top = r.y * s, bot = (r.y + r.h) * s, left = r.x * s, right = (r.x + r.w) * s, pad = 40;
    if (top < v.scrollTop || bot > v.scrollTop + v.clientHeight) v.scrollTop = Math.max(0, top - pad);
    if (left < v.scrollLeft || right > v.scrollLeft + v.clientWidth) v.scrollLeft = Math.max(0, left - pad);
  }
  function fix(k) {
    var x = flat[k]; if (!x || !res) return;
    if (!sh || !x.n.hit || !x.n.path || !sh.pick(res.screen, x.n.hit)) ctx.toast('이 요소는 고를 수 없어요 — 화면에서 직접 골라 주세요');
    var d = {text: x.n.ask, done: false};
    document.dispatchEvent(new CustomEvent('hd-chat-prefill', {detail: d}));
    if (!d.done) { warnOnce('chat', '대화창이 접근성 요청 글을 받지 않았어요(hd-chat-prefill)'); ctx.toast('대화창이 붙지 않았어요 — 요청 글: ' + x.n.ask); }
  }

  panel.addEventListener('click', function (e) {
    var t = e.target;
    if (t.closest('.a11y-x')) { clear(); return; }
    var f = t.closest('.a11y-fix'); if (f) { fix(+f.dataset.k); return; }
    var li = t.closest('li[data-k]'); if (li) { mark(+li.dataset.k); reveal(+li.dataset.k); }
  });
  panel.addEventListener('mouseover', function (e) {
    var li = e.target.closest && e.target.closest('li[data-k]'); if (!li || +li.dataset.k === hiK) return;
    mark(+li.dataset.k); reveal(+li.dataset.k);
  });
  panel.addEventListener('mouseleave', function () { mark(-1); });
  layer.addEventListener('click', function (e) {
    var p = e.target.closest && e.target.closest('.a11y-pin'); if (!p) return;
    e.stopPropagation();
    var k = +p.dataset.k; mark(k);
    var li = panel.querySelector('li[data-k="' + k + '"]'); if (li && li.scrollIntoView) li.scrollIntoView({block: 'nearest'});
  });
  btn.addEventListener('click', function () { if (btn.getAttribute('aria-disabled') === 'true') { ctx.toast(A.CROSS); return; } run(); });
  addEventListener('resize', function () { placePanel(); });

  function attach(shell) {
    if (!shell || typeof shell.modal !== 'function' || typeof shell.pick !== 'function') { warnOnce('attach', '접근성 검사: 셸 칸(modal·pick)이 모자라요 — 검사 없이'); return api; }
    sh = shell;
    var m = sh.modal();
    if (m.frame) m.frame.addEventListener('load', function () {   // 틀이 다시 실림(다른 화면·새로고침) — 지난 결과는 걷고, 카드 메뉴에서 왔으면 이제 검사
      var go = onLoad || !!busy; onLoad = false; clear(); sync();   // 실리기 전에 누른 검사(옛 문서로 갔음)도 다시
      if (go) run();
    });
    var mo = ctx.$('#modal');
    if (mo && window.MutationObserver) new MutationObserver(function () { if (mo.hidden) { onLoad = false; clear(); } sync(); }).observe(mo, {attributes: true, attributeFilter: ['hidden']});
    sync();
    return api;
  }
  var api = {attach: attach, run: run, clear: clear, paint: paint,
             runOnLoad: function () { onLoad = true; },   // 카드 메뉴 '접근성 검사' — 크게 보기를 연 다음 틀이 실리면 검사
             result: function () { return res ? {screen: res.screen, items: res.items.slice()} : null; },
             layer: {id: 'a11y', escOnly: true, isOpen: function () { return !panel.hidden || !!layer.childNodes.length; }, close: clear,
                     hit: function (t) { return t && t.closest && (panel.contains(t) || layer.contains(t)) ? 'inside' : t === btn || (t && t.closest && t.closest('#ma11y')) ? 'opener' : 'outside'; }}};
  return api;
}

HD.feature('a11y', {needs: ['$', 'esc', 'toast', 'warn'], mount: mount});
})();
