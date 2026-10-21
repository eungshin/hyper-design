/* View — 화면 안 연결: 고른 카드마다 그 화면의 링크(palette.js hd-links)를 받아 출발 버튼에 그 선과 같은 색 테두리 + 번호(hd-links-paint),
   소켓, 연결 패널 줄 목록(ctx.rows → 셸 → view-link-panel), 긴 화면 펼치기. 선·선 태그·강조는 view-lines 하나가 그린다(E20 A) — 색·번호는 ctx.mark(from, to).
   HD.viewLinks.mount(ctx) → {set(ids), paint(), refresh(), cardEl(id), item(from, i), linksOf(id, cb(items|null)), model(id), demoExpand(id)}
   소켓(.sock): 연결 출발 요소마다 출발 카드 위 점 — 보이기는 CSS(트리거 도구), 끌기는 캔버스가 받는다
   ctx = {rowsEl, CARD, $, $$, title(id), mark(from, to) → {n, color}|null, tagScale(), rows(rows, title),
          isHidden?(id) — 숨긴·삭제 대기 화면은 연결 대상에서 뺀다,
          pending?(from) → {byPath:{path:{op:'link'|'cut', to}}, adds:[{to,path,text,rect}], cutIn:{id:1}} — 아직 파일에 안 들어간 연결 편집을 바로 겹친다} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var GREY = '#8A8D86', WAIT = 1500;                 // 1.5초 안에 답이 없으면(palette.js 없음 등) 그 화면은 버튼 표시 없음

function mount(ctx) {
  var rowsEl = ctx.rowsEl, CARD = ctx.CARD, $ = ctx.$, $$ = ctx.$$, title = ctx.title;
  var ids = [], models = {}, lastD = {}, deadline = {}, waiters = {}, xpId = null;

  function cssMs(name, dflt) { return HD.camera.ms(getComputedStyle(document.documentElement).getPropertyValue(name), dflt); }
  function cardEl(id) { return $$('.card', rowsEl).filter(function (c) { return c.dataset.id === id; })[0] || null; }
  function frameOf(id) { var c = cardEl(id); return c ? $('.phone iframe', c) : null; }
  function postTo(id, msg) { var f = frameOf(id); try { if (f && f.contentWindow) f.contentWindow.postMessage(msg, '*'); } catch (e) {} }
  function wanted(id) { return ids.indexOf(id) >= 0 || !!waiters[id]; }
  function request(id) {
    var f = frameOf(id); if (!f) return false;
    deadline[id] = performance.now() + WAIT;
    if (f.hasAttribute('data-src')) { f.src = f.getAttribute('data-src'); f.removeAttribute('data-src'); }
    var ask = function () { if (wanted(id)) postTo(id, {type: 'hd-links', on: true}); };
    f.addEventListener('load', ask, {once: true});
    ask();
    return true;
  }
  // hd-links 답 + 아직 파일에 안 들어간 편집 → 그 화면의 링크 목록(끊은 것은 빼고, 도착 바꾼 것·새로 이은 것은 겹친다)
  function buildModel(id, d) {
    var live = {}, pd = ctx.pending ? ctx.pending(id) : null, seen = {};
    $$('.card', rowsEl).forEach(function (c) { if (!(ctx.isHidden && ctx.isHidden(c.dataset.id))) live[c.dataset.id] = 1; });
    var raw = (d.links || []).filter(function (l) { return l && l.rect; }).map(function (l) {
      return {to: String(l.to), path: String(l.path || ''), text: String(l.text || ''), rect: l.rect};
    });
    if (pd) {
      raw = raw.filter(function (l) {
        var o = pd.byPath[l.path]; seen[l.path] = 1;
        if ((o && o.op === 'cut') || pd.cutIn[l.to]) return false;
        if (o && o.op === 'link') l.to = String(o.to);
        return true;
      });
      pd.adds.forEach(function (a) { if (!seen[a.path] && a.rect) raw.push({to: String(a.to), path: String(a.path), text: String(a.text || ''), rect: a.rect}); });
    }
    return {from: id, docHeight: +d.docHeight || 0, items: raw.filter(function (l) { return live[l.to] && l.to !== id; })};
  }
  function clear(id) {
    postTo(id, {type: 'hd-links-paint', items: []});
    var c = cardEl(id); if (c) $$('.sock:not(.selsock)', c).forEach(function (n) { n.remove(); });   // 고른 요소의 소켓은 셸이 가진다
  }
  // 출발 버튼 테두리·번호 = 그 선의 색·번호(view-lines) · 소켓 = 출발 요소 오른쪽 가운데
  function paintOne(id) {
    var m = models[id], c = cardEl(id); if (!m || !c) return;
    clear(id);
    var ph = $('.phone', c), sc = ph.offsetWidth / CARD.w, ts = ctx.tagScale ? ctx.tagScale() : 1, sk = 16 * ts, items = [];
    m.items.forEach(function (it, i) {
      var mk = ctx.mark(id, it.to), color = mk ? mk.color : GREY, q = it.rect, b = document.createElement('span');
      items.push({path: it.path, color: color, n: mk ? mk.n : undefined});
      b.className = 'sock'; b.setAttribute('data-from', id); b.setAttribute('data-i', i); b.setAttribute('data-to', it.to);
      b.style.left = ((q.x + q.w) * sc) + 'px'; b.style.top = ((q.y + q.h / 2) * sc) + 'px'; b.style.background = color;
      b.style.width = b.style.height = sk + 'px'; b.style.margin = (-sk / 2) + 'px 0 0 ' + (-sk / 2) + 'px'; b.style.borderWidth = (2 * ts) + 'px';
      b.title = '끌어서 도착 바꾸기 (지금 → ' + title(it.to) + ')';
      ph.appendChild(b);
    });
    postTo(id, {type: 'hd-links-paint', items: items});
  }
  function paint() { ids.forEach(paintOne); renderLegend(); }
  // 연결 패널 줄: 고른 화면의 연결을 도착마다 하나(선과 같은 색·번호) → 셸이 패널(view-link-panel)에 넘긴다
  function renderLegend() {
    var rows = [];
    ids.forEach(function (id) {
      var m = models[id]; if (!m) return;
      var by = {}, order = [];
      m.items.forEach(function (it) { if (!by[it.to]) { by[it.to] = []; order.push(it.to); } if (by[it.to].indexOf(it.text) < 0) by[it.to].push(it.text || '(링크)'); });
      order.forEach(function (to) { rows.push({from: id, to: to, texts: by[to], mk: ctx.mark(id, to)}); });
    });
    ctx.rows(rows, (ids.length === 1 ? title(ids[0]) : '고른 화면 ' + ids.length + '개') + ' · 연결 ' + rows.length + '개');
  }
  // 펼치기(겹쳐서): 화면 전체 높이까지(카드 2.5배 한도), 다른 카드 자리는 그대로
  function expand(id, h, done) {
    var c = cardEl(id); if (!c) return;
    var ph = $('.phone', c), fr = $('iframe', ph);
    xpId = id;
    c.style.height = c.offsetHeight + 'px'; c.classList.add('xp');
    fr.style.height = h + 'px';
    void ph.offsetHeight;
    ph.style.height = h + 'px';
    var fin = false, end = function () { if (fin) return; fin = true; done(); };
    ph.addEventListener('transitionend', end, {once: true});
    setTimeout(end, cssMs('--resize-dur', 300) + 40);
  }
  function collapse(id) {
    var c = cardEl(id); if (xpId === id) xpId = null;
    if (!c) return;
    var ph = $('.phone', c), fr = $('iframe', ph);
    ph.style.height = '';
    setTimeout(function () { if (xpId === id) return; fr.style.height = ''; c.style.height = ''; c.classList.remove('xp'); }, cssMs('--resize-dur', 300) + 30);
  }

  // 고른 카드가 바뀜 → 빠진 화면은 표시를 지우고, 새 화면은 링크를 묻는다
  function set(next) {
    var prev = ids; ids = (next || []).slice();
    prev.forEach(function (id) {
      if (ids.indexOf(id) >= 0) return;
      if (!waiters[id]) postTo(id, {type: 'hd-links', on: false});
      clear(id); delete models[id];
    });
    if (xpId && (ids.length !== 1 || ids[0] !== xpId)) collapse(xpId);
    rowsEl.classList.toggle('lkwait', ids.some(function (id) { return !models[id]; }));
    ids.forEach(function (id) { if (!models[id]) request(id); });
    renderLegend();
  }
  addEventListener('message', function (e) {
    var d = e.data;
    if (!d || typeof d !== 'object' || d.type !== 'hd-links' || !Array.isArray(d.links)) return;
    var id = null;
    $$('.card', rowsEl).forEach(function (c) { var f = $('.phone iframe', c); if (f && f.contentWindow === e.source) id = c.dataset.id; });
    if (!id || !wanted(id) || performance.now() > (deadline[id] || 0)) return;
    lastD[id] = d;
    var m = buildModel(id, d);
    if (waiters[id]) { var ws = waiters[id]; delete waiters[id]; ws.forEach(function (fn) { fn(m.items); }); }
    if (ids.indexOf(id) < 0) { postTo(id, {type: 'hd-links', on: false}); return; }
    var want = Math.min(Math.round(m.docHeight), Math.round(CARD.h * 2.5));
    if (ids.length === 1 && m.items.length && xpId !== id && want > CARD.h + 4) {   // 긴 화면: 먼저 펼치고, 다 펼친 뒤 자리를 다시 받아 그린다
      expand(id, want, function () { if (ids.indexOf(id) >= 0) request(id); });
      return;
    }
    models[id] = m;
    if (!ids.some(function (x) { return !models[x]; })) rowsEl.classList.remove('lkwait');
    paintOne(id); renderLegend();
  });
  // 편집(자르기·도착 바꾸기)이 읽는 링크: 고른 화면이면 바로, 아니면 그 화면에 물어서(답이 없으면 null)
  function linksOf(id, cb) {
    if (models[id]) { cb(models[id].items.slice()); return; }
    (waiters[id] = waiters[id] || []).push(cb);
    if (!request(id)) { delete waiters[id]; cb(null); return; }
    setTimeout(function () { var ws = waiters[id]; if (!ws || ws.indexOf(cb) < 0) return; ws.splice(ws.indexOf(cb), 1); if (!ws.length) delete waiters[id]; cb(null); }, WAIT + 50);
  }
  function refresh() {                               // 편집이 바뀜 → 마지막 답에 다시 겹쳐 그린다
    ids.forEach(function (id) { if (lastD[id] && models[id]) models[id] = buildModel(id, lastD[id]); });
    paint();
  }
  function item(from, i) { var m = models[from], it = m && m.items[i]; return it ? {from: from, to: it.to, path: it.path, text: it.text, rect: it.rect} : null; }
  // 펼치기 보여 주기(전환 메뉴 ▶): 펼쳤다가 접기
  function demoExpand(id) {
    if (xpId) return;
    expand(id, Math.round(CARD.h * 1.4), function () { setTimeout(function () { if (xpId === id && ids.indexOf(id) < 0) collapse(id); }, 500); });
  }
  return {set: set, paint: paint, refresh: refresh, cardEl: cardEl, item: item, linksOf: linksOf, demoExpand: demoExpand,
          model: function (id) { return models[id] || null; }};
}

HD.viewLinks = {mount: mount};
})();
