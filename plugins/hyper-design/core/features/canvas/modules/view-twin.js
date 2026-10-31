/* View — 캔버스 화면 ↔ 앱 카드 맞음 검증(V2): 두 카드 iframe 에 hd-snapshot 을 묻고 HD.twinDiff 로 견줘 카드에 표 '앱과 일치'·'다름 N', 누르면 목록 창, hd verify 요청에 답.
   짝·결과·글은 modules/twin.js(Model), 비교는 twin-diff.js(Model) — AI·토큰 없음. 짝 정보 = GET /api/app-parts 의 links(HD.chatBoth.links — V1 과 같은 읽기).
   표 = 카드 .phone 왼쪽 아래 <button class="tchip" data-tone=ok|diff|none> (짝 있는 캔버스 화면만). 다시 재기 = 카드 iframe load · hd-here(실림 · 앱 HMR) · 'hd-swap' done 뒤
     0.4초 묶어서, 기억 열쇠(HD.twin.key: 화면 카드 주소 ?v= · 앱 부품 도장 + 앱 카드 주소 + HMR 수)가 같으면 다시 재지 않는다. 표는 실린 카드끼리만 잰다(안 실린 카드를 싣지 않음).
   목록 창 #twinwin(role=dialog) — 여닫기 진입점은 open(id, anchor) · close() 둘뿐. 떠 있는 층 layer('twin') 을 셸이 view-float-stack 에 더한다(Esc·바깥 누르기는 거기서,
     표 = 여는 것 'opener' — 같은 표 다시 누르기 = 닫기는 표 click 이 정한다). 자리 = HD.popSide.under(표 아래, 도구 막대 피하기 — 메모 묶음 창과 같은 규칙).
     줄 누르기 = 두 카드에서 그 항목에 주황 테두리(hd-snapshot-mark, 캔버스 쪽 a · 앱 쪽 b), 닫으면 지움. [이 다른 곳 고쳐 달라고 보내기] = HD.twin.request 글 하나로
     화면 메모(intent change) 하나를 만들어 ctx.sendNotes 로 보낸다(위쪽 [보내기]·대화창과 같은 길 — 부르기만).
   hd verify: document 'hd-event' {type:'verify.ask', req, screen} → 링크를 새로 읽고, 두 카드를 (안 실렸으면 실어서) 기억 없이 재고 POST /api/verify-result {req, result}.
   오류 탐지: 화면이 SNAP_MS 안에 답하지 않으면(palette.js 없음) 결과 status error(표 '검증 못 함') + [hd] 경고 한 줄, 보내기 실패는 토스트.
   가진 상태: 링크 · 부품 도장 · 결과·기억(화면 id → {key, res}) · HMR 수 · 열린 창 id. 저장 없음.
   HD.feature('twin', {needs: ['api', 'cardEl', 'rowsEl', 'toast', 'title', 'sendNotes']}) → {refresh() → Promise, measure(id, opt) → Promise(결과), result(id), open(id, anchor), close(), isOpen(), layer} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var SNAP_MS = 4000, DEBOUNCE = 400, LINKS_MS = 3000;
var CSS = '.tchip{position:absolute;left:calc(8px * var(--ts,1));bottom:calc(8px * var(--ts,1));z-index:4;display:inline-flex;align-items:center;box-sizing:border-box;' +
  'height:calc(20px * var(--ts,1));padding:0 calc(8px * var(--ts,1));border:1px solid var(--ui-line,rgba(0,0,0,.14));border-radius:999px;background:var(--ui-panel,#fff);' +
  'color:var(--ui-text,#222);box-shadow:0 1px 4px rgba(0,0,0,.14);font:600 calc(11px * var(--ts,1))/1 system-ui,sans-serif;white-space:nowrap;cursor:pointer;pointer-events:auto}' +
  '.tchip::before{content:"";width:6px;height:6px;border-radius:50%;margin-right:5px;background:currentColor;opacity:.55}' +
  '.tchip[data-tone=ok]::before{background:#16a34a;opacity:1}.tchip[data-tone=diff]::before{background:#ea580c;opacity:1}' +
  '#twinwin{position:fixed;z-index:60;width:340px;max-height:60vh;display:flex;flex-direction:column;box-sizing:border-box;background:var(--ui-panel,#fff);color:var(--ui-text,#222);' +
  'border:1px solid var(--ui-line,rgba(0,0,0,.14));border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.18);font:13px/1.4 system-ui,sans-serif}' +
  '#twinwin[hidden]{display:none}#twinwin .tw-h{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--ui-line,rgba(0,0,0,.1));font-weight:600}' +
  '#twinwin .tw-h span{flex:1}#twinwin .tw-x{border:0;background:none;font-size:16px;cursor:pointer;color:inherit}' +
  '#twinwin ul{list-style:none;margin:0;padding:4px 0;overflow:auto}#twinwin li{padding:6px 12px;cursor:pointer}#twinwin li:hover,#twinwin li[aria-selected=true]{background:var(--ui-hover,rgba(0,0,0,.05))}' +
  '#twinwin .tw-f{padding:10px 12px;border-top:1px solid var(--ui-line,rgba(0,0,0,.1))}#twinwin .tw-send{width:100%;padding:7px 10px;border-radius:8px;border:1px solid var(--ui-line,rgba(0,0,0,.2));background:var(--ui-panel,#fff);color:inherit;cursor:pointer;font:inherit}';

function mount(ctx) {
  var T = HD.twin, D = HD.twinDiff, warn = ctx.warn || function (m) { console.warn(m); };
  var links = {}, stamps = {}, linksAt = 0, memo = {}, hmr = {}, timers = {}, warned = {}, waits = [], seq = 0, openId = null, win = null;
  if (!ctx.api || !ctx.api.on) return {refresh: function () { return Promise.resolve(); }, measure: function (id) { return Promise.resolve(T.failed(id, null, '도우미로 연 캔버스에서만 잴 수 있어요')); },
                                       result: function () { return null; }, open: function () {}, close: function () {}, isOpen: function () { return false; }};
  if (!document.getElementById('hd-twin-css')) {
    var css = document.createElement('style'); css.id = 'hd-twin-css'; css.textContent = CSS; document.head.appendChild(css);
  }

  function cards() {
    return Array.prototype.map.call(ctx.rowsEl.querySelectorAll('.card[data-id]'), function (c) {
      var cv = c.querySelector('.cover'); return {id: c.dataset.id, file: cv ? cv.dataset.file || '' : ''};
    });
  }
  function frameOf(id) {
    var c = ctx.cardEl(id), fs = c ? c.querySelectorAll('.phone iframe') : [];
    for (var i = fs.length - 1; i >= 0; i--) if (!fs[i].classList.contains('hd-swap-before')) return fs[i];
    return null;
  }
  function loaded(f) { return !!f && !f.hasAttribute('data-src') && !!f.getAttribute('src') && f.getAttribute('src') !== 'about:blank'; }
  function idOfFrame(src) {
    var fs = ctx.rowsEl.querySelectorAll('.card[data-id] .phone iframe');
    for (var i = 0; i < fs.length; i++) if (fs[i].contentWindow === src) { var c = fs[i].closest('.card[data-id]'); return c ? c.dataset.id : null; }
    return null;
  }
  function load(f) {                                   // 안 실린 카드를 지금 싣기(hd verify 만) — 판 위 카드 규칙 그대로(HD.swap.boardUrl, view-live-cap 이 내릴 수 있게 dataset.live)
    return new Promise(function (ok) {
      if (loaded(f)) { ok(); return; }
      var s = f.getAttribute('data-src') || (f.dataset && f.dataset.live);
      if (!s) { ok(); return; }
      f.addEventListener('load', function () { ok(); }, {once: true});
      f.dataset.live = s; f.removeAttribute('data-src'); f.src = HD.swap.boardUrl(s);
    });
  }

  function snap(f) {
    return new Promise(function (ok, no) {
      var w = {win: f.contentWindow, tag: 'tw' + (++seq), ok: ok};
      w.t = setTimeout(function () { var i = waits.indexOf(w); if (i >= 0) waits.splice(i, 1); no(new Error('화면이 답하지 않아요(palette.js 없음 · ' + SNAP_MS / 1000 + '초)')); }, SNAP_MS);
      waits.push(w);
      try { f.contentWindow.postMessage({type: 'hd-snapshot', tag: w.tag}, '*'); }
      catch (e) { clearTimeout(w.t); waits.splice(waits.indexOf(w), 1); no(e); }
    });
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object') return;
    if (d.type === 'hd-snapshot-r') {
      for (var i = 0; i < waits.length; i++) {
        var w = waits[i]; if (w.win !== e.source || w.tag !== d.tag) continue;
        waits.splice(i, 1); clearTimeout(w.t); w.ok(d); return;
      }
    } else if (d.type === 'hd-here') {
      var id = idOfFrame(e.source); if (!id) return;
      if (d.hmr) hmr[id] = (hmr[id] || 0) + 1;
      touched(id);
    }
  });

  function readLinks(force) {
    if (!force && Date.now() - linksAt < LINKS_MS) return Promise.resolve();
    return ctx.api.call('GET', '/api/app-parts').then(function (res) {
      if (res.status !== 200) throw new Error('HTTP ' + res.status);
      links = HD.chatBoth.links(res.body); linksAt = Date.now(); stamps = {};
      (res.body && Array.isArray(res.body.parts) ? res.body.parts : []).forEach(function (p) { if (p && p.file) stamps[p.file] = p.current || p.stamp || ''; });
    }).catch(function (e) { once('links', '[hd] 맞음 검증: 앱 부품 연결을 읽지 못했어요(' + (e && e.message || e) + ')'); });
  }
  function once(k, m) { if (!warned[k]) { warned[k] = 1; warn(m); } }

  function keyOf(p, fa, fb) {
    return T.key(fa.getAttribute('src'), (stamps[p.part] || '') + '|' + (fb.getAttribute('src') || '') + '|' + (hmr[p.app] || 0));
  }
  function measure(id, opt) {
    opt = opt || {};
    var p = T.pair(id, links, cards());
    if (!p) { delete memo[id]; paint(id); return Promise.resolve(T.noPair(id)); }
    var fa = frameOf(id), fb = frameOf(p.app);
    if (!fa || !fb) return Promise.resolve(T.failed(id, p.app, '카드가 판에 없어요'));
    if (!opt.load && !(loaded(fa) && loaded(fb))) return Promise.resolve(memo[id] ? memo[id].res : null);
    return Promise.all([load(fa), load(fb)]).then(function () {
      var k = keyOf(p, fa, fb);
      if (!opt.force && k && memo[id] && memo[id].key === k) return memo[id].res;
      var t0 = Date.now();
      return Promise.all([snap(fa), snap(fb)]).then(function (s) {
        var a = s[0].items || [], b = s[1].items || [];
        var res = T.result(id, p.app, D.diff(a, b), {size: [s[0].size, s[1].size], capped: s[0].size > a.length || s[1].size > b.length, ms: Date.now() - t0});
        memo[id] = {key: keyOf(p, fa, fb), res: res}; delete warned['snap:' + id];
        return res;
      }, function (e) {
        once('snap:' + id, '[hd] 맞음 검증: ' + id + ' ↔ ' + p.app + ' 을 재지 못했어요 — ' + (e && e.message || e));
        var res = T.failed(id, p.app, e && e.message || String(e)); memo[id] = {key: null, res: res}; return res;
      });
    }).then(function (res) { paint(id); if (openId === id) render(); return res; });
  }

  function paint(id) {
    var card = ctx.cardEl(id), host = card && (card.querySelector('.phone') || card);
    if (!host) return;
    var el = host.querySelector(':scope > .tchip'), b = T.badge(memo[id] && memo[id].res);
    if (!b) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('button'); el.type = 'button'; el.className = 'tchip';
      el.addEventListener('click', function (e) { e.stopPropagation(); if (openId === id) close(); else open(id, el); });
      el.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 카드 끌기·고르기로 가지 않게
      host.appendChild(el);
    }
    el.textContent = b.text; el.title = b.title; el.dataset.tone = b.tone;
  }

  function pairsTouching(id) {
    var cs = cards(), out = [];
    cs.forEach(function (c) { var p = T.pair(c.id, links, cs); if (p && (c.id === id || p.app === id)) out.push(c.id); });
    return out;
  }
  function touched(id) {
    readLinks(false).then(function () {
      pairsTouching(id).forEach(function (sid) {
        clearTimeout(timers[sid]);
        timers[sid] = setTimeout(function () { delete timers[sid]; measure(sid); }, DEBOUNCE);
      });
    });
  }
  function refresh() {
    return readLinks(true).then(function () {
      var cs = cards();
      return Promise.all(cs.filter(function (c) { return T.pair(c.id, links, cs); }).map(function (c) { return measure(c.id); }));
    });
  }

  /* ---- 목록 창: 여닫기 진입점 open · close ---- */
  function frameWin(id) { var f = id && frameOf(id); return f && loaded(f) ? f.contentWindow : null; }
  function markBoth(a, b) {
    var r = memo[openId] && memo[openId].res, wa = frameWin(openId), wb = frameWin(r && r.app);
    try { if (wa) wa.postMessage({type: 'hd-snapshot-mark', i: a}, '*'); if (wb) wb.postMessage({type: 'hd-snapshot-mark', i: b}, '*'); }
    catch (e) { warn('[hd] 맞음 검증: 강조를 보내지 못했어요 — ' + (e && e.message || e)); }
  }
  function render() {
    if (!win || openId == null) return;
    var res = memo[openId] && memo[openId].res, ls = T.lines(res), b = T.badge(res);
    win.querySelector('.tw-h span').textContent = (b ? b.text : '맞음 검증') + ' · ' + (ctx.title(openId) || openId) + ' ↔ ' + (res && res.app ? ctx.title(res.app) || res.app : '');
    var ul = win.querySelector('ul'); ul.textContent = '';
    if (res && res.status === 'error') { var li0 = document.createElement('li'); li0.textContent = res.why; ul.appendChild(li0); }
    ls.forEach(function (l) {
      var li = document.createElement('li'); li.textContent = l.label; li.dataset.kind = l.kind; li.setAttribute('role', 'option');
      li.addEventListener('click', function () {
        Array.prototype.forEach.call(ul.children, function (x) { x.removeAttribute('aria-selected'); });
        li.setAttribute('aria-selected', 'true'); markBoth(l.a, l.b);
      });
      ul.appendChild(li);
    });
    win.querySelector('.tw-send').disabled = !ls.length;
  }
  function open(id, anchor) {
    if (!win) {
      win = document.createElement('div'); win.id = 'twinwin'; win.setAttribute('role', 'dialog'); win.setAttribute('aria-label', '앱과 다른 곳'); win.hidden = true;
      win.innerHTML = '<div class="tw-h"><span></span><button type="button" class="tw-x" aria-label="닫기">×</button></div><ul role="listbox"></ul>' +
        '<div class="tw-f"><button type="button" class="tw-send">이 다른 곳 고쳐 달라고 보내기</button></div>';
      win.querySelector('.tw-x').addEventListener('click', close);
      win.querySelector('.tw-send').addEventListener('click', sendFix);
      document.body.appendChild(win);
    }
    if (openId != null && openId !== id) markBoth(null, null);
    openId = id; win.hidden = false; render();
    var r = anchor && anchor.getBoundingClientRect ? anchor.getBoundingClientRect() : null, t = document.getElementById('tools');
    var edge = function (b) { return {left: b.left, right: b.right, top: b.top, bottom: b.bottom}; };
    var p = HD.popSide.under(r && edge(r), {w: win.offsetWidth, h: win.offsetHeight}, {x: 8, y: 8, w: innerWidth - 16, h: innerHeight - 16},
                             t && t.offsetParent !== null ? [edge(t.getBoundingClientRect())] : []);   // 공용 자리 규칙 — 왼쪽 도구 막대는 피한다
    win.style.left = p.x + 'px'; win.style.top = p.y + 'px';
  }
  function close() {
    if (!win || win.hidden) { openId = null; return; }
    markBoth(null, null); win.hidden = true; openId = null;
  }
  function sendFix() {
    var res = memo[openId] && memo[openId].res, text = T.request(res, ctx.title);
    if (!text) { ctx.toast('보낼 다른 곳이 없어요'); return; }
    var mk = function () { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); };
    var memos = HD.memoBatch.build(HD.memoBatch.draft([openId], ctx.title), {note: text, intent: 'change', scope: 'screen'}, mk), ok;
    try { ok = ctx.sendNotes(memos); }
    catch (e) { console.error('[hd] 맞음 검증 보내기: ' + (e && e.message || e)); ctx.toast('보내지 못했어요 — ' + (e && e.message || e)); return; }
    if (ok === false) { ctx.toast('보내는 중이에요 — 잠시 뒤 다시 보내 주세요'); return; }
    ctx.toast('다른 곳 ' + T.lines(res).length + '개를 고쳐 달라고 보냈어요');
    close();
  }

  /* ---- hd verify ---- */
  document.addEventListener('hd-event', function (e) {
    var ev = e && e.detail;
    if (!ev || ev.type !== 'verify.ask' || typeof ev.req !== 'string') return;
    var sid = String(ev.screen || '');
    readLinks(true).then(function () {
      return ctx.cardEl(sid) ? measure(sid, {force: true, load: true}) : T.failed(sid, null, '캔버스에 없는 화면이에요: ' + sid);
    }).catch(function (x) { return T.failed(sid, null, x && x.message || String(x)); }).then(function (res) {
      return ctx.api.call('POST', '/api/verify-result', {req: ev.req, result: res});
    }).catch(function (x) { warn('[hd] 맞음 검증 결과를 돌려주지 못했어요 — ' + (x && x.message || x)); });
  });
  ctx.rowsEl.addEventListener('load', function (e) {   // 카드 iframe 이 실림(이 기능이 붙기 전 hd-here 를 놓쳐도) — load 는 거품이 없어 잡는 단계에서
    var f = e.target, c = f && f.tagName === 'IFRAME' && f.closest ? f.closest('.card[data-id]') : null;
    if (c && loaded(f)) touched(c.dataset.id);
  }, true);
  document.addEventListener('hd-swap', function (e) { var d = e && e.detail; if (d && d.phase === 'done' && d.id) touched(d.id); });

  var layer = {id: 'twin', isOpen: function () { return !!win && !win.hidden; }, close: close,   // 떠 있는 층(view-float-stack): Esc·바깥 누르기는 거기서
    hit: function (t) {
      if (!t || !t.closest) return 'outside';
      if (win && win.contains(t)) return 'inside';
      return t.closest('.tchip') ? 'opener' : 'outside';
    }};
  refresh();
  return {refresh: refresh, measure: measure, result: function (id) { return memo[id] ? memo[id].res : null; }, open: open, close: close,
          isOpen: layer.isOpen, layer: layer};
}

HD.feature('twin', {needs: ['api', 'cardEl', 'rowsEl', 'toast', 'title', 'sendNotes'], mount: mount});
})();
