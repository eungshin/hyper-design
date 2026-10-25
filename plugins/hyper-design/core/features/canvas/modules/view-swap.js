/* View — 스며드는 교체(48a): 화면 파일이 바뀐 카드의 새 버전을 숨긴 두 번째 iframe 에 미리 싣고, 다 그려지면 0.2초 겹쳐 바꾼다. 규칙은 modules/swap.js(Model).
   셸의 다시 싣기 자리 swapCard(id, frame, url) 가 FT.swap.swap 을 부른다(canvas_template.html 한 곳).
   - 안 실린 카드(data-src, 화면 밖) = 옛 길: data-src 만 바꾸고 보일 때 셸이 싣는다(미리 싣지 않음)
   - 실린 카드 = 같은 .phone 안 옛 iframe 바로 뒤에 <iframe class="hd-swap-next"> (absolute·opacity 0). load 뒤 옛 화면의 스크롤을 옮기고 결정:
       만지는 중(끌기 .card.moving · 메모 창 .memo-target · 글자 고치기 #tedit · 카드 글 .capopen · 크게 보기 그 화면) = 미룸: 알약 <button class="swap-pill">
         (누르면 바로 · 만지기가 끝나면 저절로) · 움직임 줄이기(설정 motion:false · prefers-reduced-motion) = 바로 · 아니면 새 것을 FADE_MS 동안 opacity 0→1(옛 것은 밑에 그대로 = 흰 깜빡임 없음)
     보이기 직전에 ctx.frameLoaded(id, 새 iframe)(셸: 테마·반영 대기·메모 자리 — 숨어 기다리는 동안 바뀐 메모까지, 없으면 [hd] 경고 한 번) → 두 프레임 뒤 보이기
     끝나면 옛 iframe 을 지우고 새 것이 그 자리(.phone 의 첫 iframe — 셸·다른 View 가 찾는 그 틀)가 된다
   - LOAD_MS 안에 안 실림 · HTTP 4xx/5xx = 새 것을 버리고 옛 화면 그대로 + [hd] 경고 + 'hd-swap' failed(카드 실패 줄은 view-busy 의 .cerr)
   의도: document 에 CustomEvent 'hd-swap' {id, phase: 'done'|'failed', why?} — view-busy 가 "방금 반영됨 ✓" 칩·실패 줄을 그린다(View 끼리 직접 부르지 않음)
   가진 상태: 교체 작업(HD.swap reduce) · 저장 없음. HD.feature('swap', {needs: ['warn'], mount(ctx) → {swap(id, frame, url), pending()}})
   ctx = warn · prefs()? · frameLoaded(id, frame)?(셸 — 없으면 교체는 하되 [hd] 경고 한 번) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CSS = '.phone iframe.hd-swap-next{position:absolute;left:0;top:0;opacity:0;pointer-events:none}' +
  '.phone iframe.hd-swap-next.hd-swap-in{opacity:1;transition:opacity var(--hd-swap-ms,200ms) ease-out}' +
  '.phone .swap-pill{position:absolute;left:50%;bottom:calc(14px * var(--ts,1));transform:translateX(-50%);z-index:5;display:inline-flex;align-items:center;gap:calc(6px * var(--ts,1));' +
  'height:calc(26px * var(--ts,1));padding:0 calc(12px * var(--ts,1));border:1px solid rgba(0,0,0,.14);border-radius:999px;background:rgba(255,255,255,.97);color:#2b2b29;' +
  'box-shadow:0 2px 10px rgba(0,0,0,.18);font:600 calc(12px * var(--ts,1))/1 system-ui,sans-serif;white-space:nowrap;cursor:pointer;pointer-events:auto}' +
  '.phone .swap-pill::before{content:"";width:calc(7px * var(--ts,1));height:calc(7px * var(--ts,1));border-radius:50%;background:var(--ui-accent,#c2590a)}' +
  '.phone .swap-pill:hover,.phone .swap-pill:focus-visible{background:#f1f1ee;outline:2px solid var(--ui-mark,#2b2b29);outline-offset:1px}';

function style() {
  if (document.getElementById('hd-swap-css')) return;
  var el = document.createElement('style'); el.id = 'hd-swap-css'; el.textContent = CSS;
  document.head.appendChild(el);
}

function mount(ctx) {
  var S = HD.swap, warn = ctx.warn || function (m) { console.warn(m); };
  var st = S.initial(), live = {}, warnedHook = false, modalHere = null, ob = null, obRaf = 0;

  function emit(id, phase, why) { document.dispatchEvent(new CustomEvent('hd-swap', {detail: {id: id, phase: phase, why: why || null}})); }
  function reduced() {
    var p = ctx.prefs ? ctx.prefs() : null;
    if (p && p.motion === false) return true;
    return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  function scrollOf(f) {                              // 같은 출처일 때만(앱 카드 등 다른 출처 = 옮기지 않음)
    try { var w = f.contentWindow; return w ? {x: w.scrollX, y: w.scrollY} : null; }
    catch (e) { return null; }                         // 다른 출처 — 읽을 수 없으면 스크롤은 그대로 둔다
  }
  function navStatus(f) {
    try { var n = f.contentWindow.performance.getEntriesByType('navigation')[0]; return n && typeof n.responseStatus === 'number' ? n.responseStatus : null; }
    catch (e) { return null; }                         // 다른 출처 — 상태를 모르면 실렸다고 본다
  }

  // 지금 만지는 카드 — 셸이 DOM 에 남기는 표시를 읽는다(상태 주인은 셸)
  function idOf(el) { var c = el && el.closest && el.closest('.card'); return c ? c.dataset.id : null; }
  function modalId() {
    var m = document.getElementById('modal'), mf = document.getElementById('mframe');
    if (!m || m.hidden) { modalHere = null; return null; }
    if (modalHere) return modalHere;
    var src = mf && (mf.getAttribute('src') || '').split(/[?#]/)[0], hit = null;
    if (src) Array.prototype.forEach.call(document.querySelectorAll('.card .cover[data-file]'), function (b) { if (b.dataset.file === src) hit = idOf(b); });
    return hit;
  }
  function editId() {
    var t = document.getElementById('tedit'), m = document.getElementById('modal');
    if (!t || t.hidden || (m && !m.hidden)) return null;
    var r = t.getBoundingClientRect(), x = r.left + 4, y = r.top + 4, hit = null;
    Array.prototype.forEach.call(document.querySelectorAll('.card .phone'), function (ph) {
      var q = ph.getBoundingClientRect();
      if (x >= q.left && x <= q.right && y >= q.top && y <= q.bottom) hit = idOf(ph);
    });
    return hit;
  }
  function signals() {
    var pop = document.getElementById('pop'), ids = function (sel) { return Array.prototype.map.call(document.querySelectorAll(sel), function (c) { return c.dataset.id; }); };
    var memo = pop && !pop.hidden ? ids('.card.memo-target')[0] || null : null;
    return {moving: ids('.card.moving'), caption: ids('.card.capopen'), memo: memo, edit: editId(), modal: modalId()};
  }

  function drop(id) {                                 // 그 카드의 교체 하나를 치운다(새 iframe·알약·타이머)
    var L = live[id]; if (!L) return;
    clearTimeout(L.timer); if (L.pill) L.pill.remove();
    if (L.next && L.next.parentNode && !L.done) L.next.remove();
    delete live[id];
    if (!Object.keys(live).length) watch(false);
  }
  function fail(id, seq, why) {
    if (!S.current(st, id, seq)) return;
    st = S.reduce(st, {type: 'end', id: id, seq: seq});
    drop(id);
    warn('[hd] 카드 ' + id + ' 새 버전: ' + why + ' — 옛 화면을 그대로 둬요');
    emit(id, 'failed', S.errorText(why));
  }
  function lazy(id, f, url) { f.removeAttribute('src'); f.setAttribute('data-src', url); emit(id, 'done'); }

  function commit(id) {
    var L = live[id], job = st.jobs[id];
    if (!L || !job || job.phase !== 'ready') return;
    var f = L.old, n = L.next;
    if (!f.isConnected || !n.isConnected || f.hasAttribute('data-src')) {   // 카드가 없어졌거나 그새 내려감(화면 밖) = 옛 길
      st = S.reduce(st, {type: 'end', id: id, seq: job.seq}); drop(id);
      if (f.isConnected) lazy(id, f, job.url);
      return;
    }
    st = S.reduce(st, {type: 'end', id: id, seq: job.seq});
    L.done = true; clearTimeout(L.timer); if (L.pill) { L.pill.remove(); L.pill = null; }
    var finished = false;
    function finish() {
      if (finished) return; finished = true;
      f.remove();
      n.classList.remove('hd-swap-next', 'hd-swap-in'); n.removeAttribute('aria-hidden');
      delete live[id]; if (!Object.keys(live).length) watch(false);
      emit(id, 'done');
    }
    // 보이기 직전에 셸의 load 뒤 일(테마·반영 대기·메모 자리) — 숨어 기다리는 동안 바뀐 메모도 새 화면에 실린다
    if (ctx.frameLoaded) ctx.frameLoaded(id, n);
    else if (!warnedHook) { warnedHook = true; warn('[hd] swap: 셸 ctx.frameLoaded 가 없어 새 화면에 테마·반영 대기·메모 자리를 보내지 못해요'); }
    requestAnimationFrame(function () { requestAnimationFrame(show); });   // 그 메시지가 한 번 그려진 뒤에 보인다
    function show() {
      if (reduced()) { finish(); return; }              // 움직임 줄이기 = 바로
      n.style.setProperty('--hd-swap-ms', S.FADE_MS + 'ms');
      n.classList.add('hd-swap-in');
      n.addEventListener('transitionend', finish, {once: true});
      var dur = parseFloat(getComputedStyle(n).transitionDuration) * 1000;   // CSS 가 정한 길이(s) — 없거나 깨지면 FADE_MS
      setTimeout(finish, (dur > 0 ? dur : S.FADE_MS) + 120);   // transitionend 이 안 와도(탭이 숨음 등)
    }
  }

  function pill(id) {
    var L = live[id]; if (!L || L.pill) return;
    var ph = L.old.parentNode, b = document.createElement('button');
    b.type = 'button'; b.className = 'swap-pill'; b.textContent = S.PILL; b.setAttribute('data-id', id);
    b.title = '이 카드를 쓰는 중이라 새 버전을 기다리게 했어요 — 누르면 지금 바꿔요';
    ph.appendChild(b); L.pill = b;
  }
  function decide(id) {
    var job = st.jobs[id], step = S.next(job, {touching: S.touching(id, signals()), reduced: reduced()});
    if (step === 'wait') return;
    if (step === 'defer') { pill(id); watch(true); return; }
    commit(id);
  }
  function recheck() {                                 // 만지기가 끝났나 — 미룬 카드만
    obRaf = 0;
    Object.keys(live).forEach(function (id) { if (live[id].pill) decide(id); });
  }
  function watch(on) {
    if (on && !ob && typeof MutationObserver !== 'undefined') {
      ob = new MutationObserver(function () { if (!obRaf) obRaf = requestAnimationFrame(recheck); });
      ob.observe(document.body, {subtree: true, attributes: true, attributeFilter: ['class', 'hidden']});
    } else if (!on && ob) { ob.disconnect(); ob = null; }
  }

  function swap(id, f, url) {
    if (!f || typeof url !== 'string' || !url) return;
    var isLive = !f.hasAttribute('data-src') && !!f.dataset.live && !!f.parentNode;
    if (live[id]) { var prev = st.jobs[id]; if (prev) st = S.reduce(st, {type: 'end', id: id, seq: prev.seq}); drop(id); }
    if (S.plan({live: isLive}) === 'lazy') { lazy(id, f, url); return; }
    st = S.reduce(st, {type: 'start', id: id, url: url});
    var seq = st.jobs[id].seq, n = document.createElement('iframe'), sc = scrollOf(f);
    n.className = 'hd-swap-next'; n.setAttribute('aria-hidden', 'true');
    ['scrolling', 'tabindex', 'title'].forEach(function (a) { if (f.hasAttribute(a)) n.setAttribute(a, f.getAttribute(a)); });
    n.dataset.live = url;
    live[id] = {old: f, next: n, pill: null, done: false, timer: setTimeout(function () { fail(id, seq, S.failed({timedOut: true})); }, S.LOAD_MS)};
    n.addEventListener('load', function () {
      if (!S.current(st, id, seq)) return;
      var why = S.failed({status: navStatus(n)});
      if (why) { fail(id, seq, why); return; }
      clearTimeout(live[id].timer);
      if (sc && (sc.x || sc.y)) { try { n.contentWindow.scrollTo(sc.x, sc.y); } catch (e) { warn('[hd] 카드 ' + id + ' 스크롤을 옮기지 못했어요'); } }
      st = S.reduce(st, {type: 'ready', id: id, seq: seq});
      decide(id);
    });
    n.src = S.boardUrl(url);                          // 붙이기 전에 — 붙인 뒤에 주면 빈 about:blank 의 load 가 먼저 와 빈 화면으로 바뀐다
    f.parentNode.insertBefore(n, f.nextSibling);
  }

  function onPill(e) {                               // 알약은 자기 누르기만 — 판의 capture 처리(메모·글자 도구, 카드 끌기)보다 먼저 받는다
    var b = e.target && e.target.closest ? e.target.closest('.swap-pill') : null;
    if (!b) return;
    e.stopPropagation(); e.preventDefault();
    if (e.type === 'click') commit(b.getAttribute('data-id'));
  }
  document.addEventListener('pointerdown', onPill, true);
  document.addEventListener('click', onPill, true);
  addEventListener('message', function (e) {         // 크게 보기 안에서 다른 화면으로 넘어가도 그 화면 id(palette.js hd-here)
    var d = e.data, mf = document.getElementById('mframe');
    if (d && d.type === 'hd-here' && typeof d.screen === 'string' && mf && e.source === mf.contentWindow) modalHere = d.screen;
  });
  style();
  return {swap: swap, pending: function () { return S.pending(st); }};
}

HD.feature('swap', {needs: ['warn'], mount: mount});
})();
