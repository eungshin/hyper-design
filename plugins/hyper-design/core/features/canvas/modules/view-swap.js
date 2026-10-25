/* View — 스며드는 교체(48a)·바뀐 곳 보기(48b): 화면 파일이 바뀐 카드의 새 버전을 숨긴 두 번째 iframe 에 미리 싣고, 다 그려지면 0.2초 겹쳐 바꾼 뒤 바뀐 곳을 잠깐 강조한다. 규칙은 modules/swap.js·swap-diff.js(Model).
   셸의 다시 싣기 자리 swapCard(id, frame, url) 가 FT.swap.swap 을 부른다(canvas_template.html 한 곳).
   - 안 실린 카드(data-src, 화면 밖) = 옛 길: data-src 만 바꾸고 보일 때 셸이 싣는다(미리 싣지 않음)
   - 실린 카드 = 같은 .phone 안 옛 iframe 바로 뒤에 <iframe class="hd-swap-next"> (absolute·opacity 0). load 뒤 옛 화면의 스크롤을 옮기고 결정:
       만지는 중(끌기 .card.moving · 메모 창 .memo-target · 글자 고치기 #tedit · 카드 글 .capopen · 크게 보기 그 화면) = 미룸: 알약 <button class="swap-pill">
         (누르면 바로 · 만지기가 끝나면 저절로 — 화면을 가리지 않게 카드 화면 밑 가장자리 바로 아래 오른쪽) · 움직임 줄이기(설정 motion:false · prefers-reduced-motion) = 바로 ·
         아니면 새 것을 FADE_MS 동안 opacity 0→1(옛 것은 밑에 그대로 = 흰 깜빡임 없음)
     보이기 직전에 ctx.frameLoaded(id, 새 iframe)(셸: 테마·반영 대기·메모 자리 — 숨어 기다리는 동안 바뀐 메모까지, 없으면 [hd] 경고 한 번) → 두 프레임 뒤 보이기
     끝나면 옛 iframe 을 지우고 새 것이 그 자리(.phone 의 첫 iframe — 셸·다른 View 가 찾는 그 틀)가 된다
   - LOAD_MS 안에 안 실림 · HTTP 4xx/5xx = 새 것을 버리고 옛 화면 그대로 + [hd] 경고 + 'hd-swap' failed(카드 실패 줄은 view-busy 의 .cerr)
   - 바뀐 곳 보기(48b): 바꾸기 직전 옛 틀·새 틀의 DOM(같은 출처만)을 나무로 뽑아 HD.swapDiff.diff → HD.swap.flash 계획 →
       새로 생긴 블록은 보이기 전에 숨겨 두고, 새 틀 load 뒤 FLASH.AFTER_LOAD 가 지나면(판 모드 palette.js 가 움직임을 끝내는 때 뒤) Element.animate 로
       바뀐 블록 외곽선(OUTLINE_HOLD 뒤 OUTLINE_MS 사라짐) · 새 블록 RISE_MS ease 로 RISE_PX 아래에서 떠오름. 움직임 줄이기 = 숨기기·강조 모두 없음.
       WAAPI 라 판 모드 CSS(transition·animation 0초)에 막히지 않고, 화면 문서에 남는 것(class·style)이 없다. 다른 출처(앱 카드) = 강조 없음
     · 옛 화면 HTML 스냅숏(카드마다 마지막 교체 하나, 메모리만) — 'hd-swap-compare' {id, on} 을 받으면 새 틀 위에 iframe.hd-swap-before(srcdoc, 스크립트 없음)를 겹친다
   - 같은 내용(49c): 옛 틀이 낙관 반영으로 먼저 바뀐 틀(iframe[data-hd-opt])이고 새 틀이 다 실렸을 때 나무가 같으면(HD.swap.same) 'silent' — 만지는 중이어도 알약·겹치기·강조 없이 바로 바꾼다
       (그 카드에서 글자를 고치는 중 .card.hd-typing 이면 아님). done 의도에 silent:true · before:false(전/후 볼 것이 없다)
   - same(frame, url) → Promise<bool> — 크게 보기 틀처럼 교체 길 밖의 틀: url 을 화면 밖 숨은 iframe 에 실어 지금 틀과 나무가 같은지(다른 출처·시간 초과 = false)
   의도: document 에 CustomEvent 'hd-swap' {id, phase: 'start'|'done'|'failed', why?, before?, silent?} — view-busy 가 "방금 반영됨 ✓" 칩(before = 전/후 보기 있음)·실패 줄을 그린다
     (View 끼리 직접 부르지 않음) · 'start' = 실린 카드의 새 교체가 시작됨 · 'done' 뒤 view-links 가 그 카드 링크 표시를 다시 묻는다.
     받는 의도: 'hd-swap-compare' {id, on}(view-busy 의 [전/후])
   가진 상태: 교체 작업(HD.swap reduce) · 카드마다 마지막 옛 화면 스냅숏 · 저장 없음. HD.feature('swap', {needs: ['warn'], mount(ctx) → {swap(id, frame, url), pending(), same(frame, url)}})
   ctx = warn · prefs()? · frameLoaded(id, frame)?(셸 — 없으면 교체는 하되 [hd] 경고 한 번) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CSS = '.phone iframe.hd-swap-next{position:absolute;left:0;top:0;opacity:0;pointer-events:none}' +
  '.phone iframe.hd-swap-next.hd-swap-in{opacity:1;transition:opacity var(--hd-swap-ms,200ms) ease-out}' +
  '.phone iframe.hd-swap-before{position:absolute;left:0;top:0}' +
  '.card .swap-pill{position:absolute;right:0;margin-top:calc(8px * var(--ts,1));z-index:5;display:inline-flex;align-items:center;gap:calc(6px * var(--ts,1));' +
  'height:calc(26px * var(--ts,1));padding:0 calc(12px * var(--ts,1));border:1px solid rgba(0,0,0,.14);border-radius:999px;background:rgba(255,255,255,.97);color:#2b2b29;' +
  'box-shadow:0 2px 10px rgba(0,0,0,.18);font:600 calc(12px * var(--ts,1))/1 system-ui,sans-serif;white-space:nowrap;cursor:pointer;pointer-events:auto}' +
  '.card .swap-pill::before{content:"";width:calc(7px * var(--ts,1));height:calc(7px * var(--ts,1));border-radius:50%;background:var(--ui-accent,#c2590a)}' +
  '.card .swap-pill:hover,.card .swap-pill:focus-visible{background:#f1f1ee;outline:2px solid var(--ui-mark,#2b2b29);outline-offset:1px}';

function style() {
  if (document.getElementById('hd-swap-css')) return;
  var el = document.createElement('style'); el.id = 'hd-swap-css'; el.textContent = CSS;
  document.head.appendChild(el);
}

var SKIP = {SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEMPLATE: 1, LINK: 1, META: 1};
function hdOwn(el) { for (var j = 0; j < el.attributes.length; j++) if (el.attributes[j].name.indexOf('data-hd-') === 0) return true; return false; }

function mount(ctx) {
  var S = HD.swap, warn = ctx.warn || function (m) { console.warn(m); };
  var st = S.initial(), live = {}, warnedHook = false, modalHere = null, ob = null, obRaf = 0, snaps = {}, before = {};

  function emit(id, phase, why, extra) {
    var d = {id: id, phase: phase, why: why || null}, k;
    for (k in extra || {}) d[k] = extra[k];
    document.dispatchEvent(new CustomEvent('hd-swap', {detail: d}));
  }
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
    var typing = ids('.card.hd-typing');              // 화면 안 글자를 그 자리에서 고치는 중(49c, view-optimistic 이 표시)
    return {moving: ids('.card.moving'), caption: ids('.card.capopen'), memo: memo, edit: editId() || typing[0] || null, modal: modalId(), typing: typing};
  }

  // 바뀐 곳 보기(48b) — 화면 DOM → 나무(HD.swapDiff 가 읽는 꼴). 다른 출처면 null
  function treeOf(f) {
    var doc;
    try { doc = f.contentDocument; } catch (e) { return null; }   // 다른 출처(앱 카드) — 견줄 수 없으면 강조 없음
    if (!doc || !doc.body) return null;
    var els = [];
    function walk(el) {
      var tag = el.tagName.toLowerCase(), i = els.length, x = '', a = '', key = tag, c = [], k;
      var reg = el.getAttribute('data-region'), cls = (el.getAttribute('class') || '').trim().split(/\s+/)[0];
      els.push(el);
      if (el.id) key += '#' + el.id; else if (reg != null) key += '[' + reg + ']'; else if (cls) key += '.' + cls;
      ['src', 'alt', 'placeholder'].forEach(function (n) { if (el.hasAttribute(n)) a += n + '=' + el.getAttribute(n) + ';'; });
      if (/^(input|textarea|select)$/.test(tag)) a += 'value=' + el.value + ';';
      if (tag === 'svg') return {i: i, t: tag, k: key, x: '', a: a + el.innerHTML, c: []};   // 그림은 통째로 한 덩이
      for (k = el.firstChild; k; k = k.nextSibling) {
        if (k.nodeType === 3) x += k.nodeValue;
        else if (k.nodeType === 1 && !SKIP[k.tagName] && !hdOwn(k)) c.push(walk(k));
      }
      return {i: i, t: tag, k: key, x: x.replace(/\s+/g, ' ').trim(), a: a, c: c};
    }
    return {root: walk(doc.body), els: els};
  }
  function planFlash(f, n) {                         // 옛 틀·새 틀 → {plan, els} | null
    if (!HD.swapDiff) return null;
    var A = treeOf(f), B = A && treeOf(n);
    if (!A || !B) return null;
    var plan = S.flash(HD.swapDiff.diff(A.root, B.root), reduced());
    return plan ? {plan: plan, els: B.els} : null;
  }
  function hideRise(fl) {                            // 새 블록은 떠오르기 전까지 숨겨 둔다(보이고 나서 사라지는 깜빡임 없게)
    fl.prev = fl.plan.rise.map(function (i) { var el = fl.els[i], p = el.getAttribute('style'); el.style.opacity = '0'; return p; });
  }
  function unhide(el, p) { if (p === null) el.removeAttribute('style'); else el.setAttribute('style', p); }   // 원래 style 그대로(없었으면 없게)
  function runFlash(id, n, fl, loadedAt) {
    var F = S.FLASH, wait = Math.max(0, loadedAt + F.AFTER_LOAD - performance.now());
    setTimeout(function () {
      if (!n.isConnected) return;
      try {
        var tot = F.OUTLINE_HOLD + F.OUTLINE_MS, at = F.OUTLINE_HOLD / tot;
        fl.plan.outline.forEach(function (i) {
          fl.els[i].animate([{outline: F.OUTLINE, outlineOffset: '2px', offset: 0}, {outline: F.OUTLINE, outlineOffset: '2px', offset: at},
                             {outline: F.OUTLINE_END, outlineOffset: '2px', offset: 1}], {duration: tot, easing: 'ease-out'});
        });
        fl.plan.rise.forEach(function (i, j) {
          var el = fl.els[i];
          el.animate([{opacity: 0, transform: 'translateY(' + F.RISE_PX + 'px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: F.RISE_MS, easing: 'ease'});
          unhide(el, fl.prev[j]);
        });
      } catch (e) {                                   // 강조는 덤 — 실패해도 새 화면은 그대로(숨긴 새 블록은 되돌림)
        fl.plan.rise.forEach(function (i, j) { unhide(fl.els[i], fl.prev[j]); });
        warn('[hd] 카드 ' + id + ' 바뀐 곳 강조를 못 했어요 — ' + e);
      }
    }, wait);
  }
  function snapOf(f) {                               // 옛 화면 HTML(스크립트·캔버스 표시 빼고, 상대 주소는 <base>) — 다른 출처면 null
    try {
      var d = f.contentDocument, c = d.documentElement.cloneNode(true), head = c.querySelector('head'), b = d.createElement('base');
      Array.prototype.forEach.call(c.querySelectorAll('script,[data-hd-links],[data-hd-pick]'), function (x) { x.remove(); });
      b.setAttribute('href', f.contentWindow.location.href);
      if (head) head.insertBefore(b, head.firstChild);
      return '<!doctype html>' + c.outerHTML;
    } catch (e) { return null; }                       // 다른 출처 — 전/후 보기 없음(칩에 버튼이 안 생긴다)
  }
  function phoneOf(id) {
    var hit = null;
    Array.prototype.forEach.call(document.querySelectorAll('.card'), function (c) { if (!hit && c.dataset.id === id) hit = c.querySelector('.phone'); });
    return hit;
  }
  function compare(id, on) {                         // 전/후 보기: 옛 화면을 새 화면 위에(다시 누르면 걷음)
    if (before[id]) { before[id].remove(); delete before[id]; }
    if (!on) return;
    var ph = phoneOf(id), cur = ph && ph.querySelector('iframe'), s = snaps[id];
    if (!cur || !s) { warn('[hd] 카드 ' + id + ' 전/후 보기: 옛 화면이 없어요'); return; }
    var o = document.createElement('iframe');
    o.className = 'hd-swap-before'; o.setAttribute('sandbox', 'allow-same-origin'); o.setAttribute('aria-hidden', 'true'); o.setAttribute('tabindex', '-1');
    o.setAttribute('scrolling', 'no');
    o.addEventListener('load', function () {
      var sc = scrollOf(cur);
      if (sc && (sc.x || sc.y)) { try { o.contentWindow.scrollTo(sc.x, sc.y); } catch (e) { warn('[hd] 카드 ' + id + ' 전/후 보기 스크롤을 맞추지 못했어요'); } }
    });
    o.srcdoc = s;
    cur.parentNode.insertBefore(o, cur.nextSibling); before[id] = o;
  }
  document.addEventListener('hd-swap-compare', function (e) { var d = e.detail || {}; if (typeof d.id === 'string' && d.id) compare(d.id, !!d.on); });

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

  function sameOf(a, b) {                            // 두 틀의 화면 나무가 같은가(49c) — 다른 출처·깨진 문서 = false
    if (!HD.swapDiff) return false;
    var A = treeOf(a), B = A && treeOf(b);
    return !!(A && B) && S.same(HD.swapDiff.diff(A.root, B.root));
  }
  function commit(id, silent) {
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
    var fl = silent ? null : planFlash(f, n), snap = silent ? null : snapOf(f);   // 바뀐 곳(48b) — 옛 틀이 아직 있을 때 · 같은 내용이면 강조·전/후 없음
    if (snap) snaps[id] = snap; else delete snaps[id];
    if (fl) hideRise(fl);
    // 크기는 옛 틀 그대로 — 셸·다른 View 가 옛 틀에 둔 인라인 style(긴 화면 펼치기 height 등)을 새 틀이 이어받는다(48b 탐침: 펼친 카드에서 새 틀만 680px)
    var os = f.getAttribute('style');
    if (os === null) n.removeAttribute('style'); else n.setAttribute('style', os);
    var finished = false;
    function finish() {
      if (finished) return; finished = true;
      f.remove();
      n.classList.remove('hd-swap-next', 'hd-swap-in'); n.removeAttribute('aria-hidden');
      n.style.removeProperty('--hd-swap-ms'); if (!n.getAttribute('style')) n.removeAttribute('style');   // 겹치기용 값은 남기지 않는다
      if (!n.getAttribute('class')) n.removeAttribute('class');
      delete live[id]; if (!Object.keys(live).length) watch(false);
      if (fl) runFlash(id, n, fl, L.loadedAt);
      emit(id, 'done', null, silent ? {before: false, silent: true} : {before: !!snap});
    }
    // 보이기 직전에 셸의 load 뒤 일(테마·반영 대기·메모 자리) — 숨어 기다리는 동안 바뀐 메모도 새 화면에 실린다
    if (ctx.frameLoaded) ctx.frameLoaded(id, n);
    else if (!warnedHook) { warnedHook = true; warn('[hd] swap: 셸 ctx.frameLoaded 가 없어 새 화면에 테마·반영 대기·메모 자리를 보내지 못해요'); }
    requestAnimationFrame(function () { requestAnimationFrame(show); });   // 그 메시지가 한 번 그려진 뒤에 보인다
    function show() {
      if (silent || reduced()) { finish(); return; }    // 같은 내용(49c)·움직임 줄이기 = 바로
      n.style.setProperty('--hd-swap-ms', S.FADE_MS + 'ms');
      n.classList.add('hd-swap-in');
      n.addEventListener('transitionend', finish, {once: true});
      var dur = parseFloat(getComputedStyle(n).transitionDuration) * 1000;   // CSS 가 정한 길이(s) — 없거나 깨지면 FADE_MS
      setTimeout(finish, (dur > 0 ? dur : S.FADE_MS) + 120);   // transitionend 이 안 와도(탭이 숨음 등)
    }
  }

  function pill(id) {
    var L = live[id]; if (!L || L.pill) return;
    var ph = L.old.parentNode, card = ph.closest('.card') || ph, b = document.createElement('button');
    b.type = 'button'; b.className = 'swap-pill'; b.textContent = S.PILL; b.setAttribute('data-id', id);
    b.title = '이 카드를 쓰는 중이라 새 버전을 기다리게 했어요 — 누르면 지금 바꿔요';
    b.style.top = (ph.offsetTop + ph.offsetHeight) + 'px';   // 화면 밑 가장자리 바로 아래 — 화면 안 버튼·탭 막대를 가리지 않는다
    card.appendChild(b); L.pill = b;
  }
  function decide(id) {
    var job = st.jobs[id], sig = signals(), L = live[id];
    var same = !!(job && job.phase === 'ready' && L && L.old.hasAttribute('data-hd-opt')) && sameOf(L.old, L.next);   // 먼저 바뀐 틀(낙관 반영, view-optimistic 표시)만 — AI 쓰기는 예전처럼 겹치기·알약
    var step = S.next(job, {touching: S.touching(id, sig), reduced: reduced(), same: same, typing: sig.typing.indexOf(id) >= 0});
    if (step === 'wait') return;
    if (step === 'defer') { pill(id); watch(true); return; }
    commit(id, step === 'silent');
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
    if (before[id]) compare(id, false);
    if (S.plan({live: isLive}) === 'lazy') { lazy(id, f, url); return; }
    emit(id, 'start');
    st = S.reduce(st, {type: 'start', id: id, url: url});
    var seq = st.jobs[id].seq, n = document.createElement('iframe'), sc = scrollOf(f);
    n.className = 'hd-swap-next'; n.setAttribute('aria-hidden', 'true');
    ['scrolling', 'tabindex', 'title'].forEach(function (a) { if (f.hasAttribute(a)) n.setAttribute(a, f.getAttribute(a)); });
    n.dataset.live = url;
    live[id] = {old: f, next: n, pill: null, done: false, loadedAt: 0, timer: setTimeout(function () { fail(id, seq, S.failed({timedOut: true})); }, S.LOAD_MS)};
    n.addEventListener('load', function () {
      if (!S.current(st, id, seq)) return;
      var why = S.failed({status: navStatus(n)});
      if (why) { fail(id, seq, why); return; }
      clearTimeout(live[id].timer); live[id].loadedAt = performance.now();
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
  function same(f, url) {                            // 교체 길 밖의 틀(크게 보기)이 url 과 같은 내용인가 — 화면 밖 숨은 틀에 실어 견준다(49c)
    return new Promise(function (done) {
      if (!f || typeof url !== 'string' || !url || !f.isConnected) { done(false); return; }
      var n = document.createElement('iframe'), t = 0, end = function (v) { clearTimeout(t); if (n.parentNode) n.remove(); done(v); };
      n.className = 'hd-swap-probe'; n.setAttribute('aria-hidden', 'true'); n.setAttribute('tabindex', '-1');
      n.style.cssText = 'position:fixed;left:-20000px;top:0;visibility:hidden;pointer-events:none;width:' + (f.offsetWidth || 375) + 'px;height:' + (f.offsetHeight || 700) + 'px';
      t = setTimeout(function () { warn('[hd] 같은 내용인지 견주지 못했어요(시간 초과) — 다시 싣는다'); end(false); }, S.LOAD_MS);
      n.addEventListener('load', function () {
        if (S.failed({status: navStatus(n)})) { end(false); return; }
        requestAnimationFrame(function () { var v = false; try { v = sameOf(f, n); } catch (e) { warn('[hd] 같은 내용 견주기 실패 — ' + e); } end(v); });
      });
      n.src = url;
      document.body.appendChild(n);
    });
  }
  style();
  return {swap: swap, pending: function () { return S.pending(st); }, same: same};
}

HD.feature('swap', {needs: ['warn'], mount: mount});
})();
