/* View — 연결 보기의 DOM/SVG: 색 링크 선·칩·테두리 고리·범례·펼치기/접기·마우스 강조.
   상태는 HD.focus 리듀서 하나. 이벤트는 의도를 만들어 dispatch(intent) 만 부른다 → reduce → 그리기.
   HD.viewLinks.mount(ctx) → {dispatch, render, focusId, state}
   ctx = {graph, rowsEl, pane, CARD, $, $$, esc, circled, isDragging(), prefs, savePrefs()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var F = HD.focus, G = HD.graph;
  var rowsEl = ctx.rowsEl, pane = ctx.pane, CARD = ctx.CARD, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, circled = ctx.circled;
  var graph = ctx.graph, state = F.initial(ctx.prefs && ctx.prefs.sat);
  var lkDeadline = 0, lkWaitT = 0, curView = null, xpId = null, satRaf = 0;
  var TITLES = {};
  (graph.screens || []).forEach(function (s) { TITLES[s.id] = s.title; });

  function cardEl(id) { return $$('.card', rowsEl).filter(function (c) { return c.dataset.id === id; })[0] || null; }
  function frameOf(id) { var c = cardEl(id); return c ? $('.phone iframe', c) : null; }
  function postTo(id, msg) { var f = frameOf(id); try { if (f && f.contentWindow) f.contentWindow.postMessage(msg, '*'); } catch (e) {} }
  function requestLinks(id) {
    var f = frameOf(id); if (!f) return;
    lkDeadline = performance.now() + 1500;            // 1.5초 안에 답이 없으면(palette.js 없음 등) 갈래 이름표로
    if (f.hasAttribute('data-src')) { f.src = f.getAttribute('data-src'); f.removeAttribute('data-src'); }
    var ask = function () { if (state.focusId === id) postTo(id, {type: 'hd-links', on: true}); };
    f.addEventListener('load', ask, {once: true});
    ask();
  }
  // hd-links 답 → 그래프의 link 간선 → 색 모델
  function buildModel(d) {
    var focusId = state.focusId, ids = {};
    $$('.card', rowsEl).forEach(function (c) { ids[c.dataset.id] = 1; });
    var items = (d.links || []).filter(function (l) { return l && ids[l.to] && l.to !== focusId && l.rect; });
    if (!items.length) return null;
    graph = G.addLinks(graph, focusId, items.map(function (l) { return {to: String(l.to), path: String(l.path || ''), text: String(l.text || ''), rect: l.rect}; }));
    var m = F.assignColors(G.edgesFrom(graph, focusId, 'link').map(function (e) { return {to: e.to, path: e.via.path, text: e.via.text, rect: e.via.rect}; }), d.accent, F.LINK_COLORS);
    m.from = focusId; m.accent = d.accent || ''; m.titles = TITLES; m.docHeight = +d.docHeight || 0;
    return m;
  }
  function applyFocus() {
    var v = curView, focusId = state.focusId, lk = state.links;
    rowsEl.classList.toggle('focusing', !!focusId);
    rowsEl.classList.toggle('haslk', !!(focusId && lk));
    var linked = {};
    if (focusId) linked[focusId] = 1;
    $$('path.ln, .alabel', rowsEl).forEach(function (n) {
      var on = !!focusId && (n.getAttribute('data-from') === focusId || n.getAttribute('data-to') === focusId);
      n.classList.toggle('on', on);
      var rp = on && !!lk && n.getAttribute('data-from') === focusId && !!lk.targets[n.getAttribute('data-to')];   // 색 링크가 대신 그린다
      n.classList.toggle('rep', rp);
      if (rp) n.classList.remove('on');
      if (on) { linked[n.getAttribute('data-from')] = 1; linked[n.getAttribute('data-to')] = 1; }
    });
    var rings = v ? v.rings : {};
    $$('.card', rowsEl).forEach(function (c) {
      var t = rings[c.dataset.id];
      c.classList.toggle('hl', !!focusId && (!!linked[c.dataset.id] || !!t));
      c.classList.toggle('focus', c.dataset.id === focusId);
      c.classList.toggle('lt', !!t);
      if (t) c.style.setProperty('--ring', t.color); else { c.style.removeProperty('--ring'); c.classList.remove('em', 'dim'); }
    });
  }
  function clearLinkLayer() {
    var svg = $('#lks');
    $$('path.lk, marker.lkm', svg).forEach(function (n) { n.remove(); });
    $('#lkl').innerHTML = '';
    $$('.lnum', rowsEl).forEach(function (n) { n.remove(); });
  }
  function renderLegend(v) {
    var lg = $('#legend');
    if (!v || !v.legend || !state.focusId) { lg.hidden = true; return; }
    $('#lgTitle').textContent = v.legend.title;
    $('#lgRows').innerHTML = v.legend.rows.map(function (r) {
      return '<label class="lgrow" data-k="' + r.k + '"><span class="lgdot" style="background:' + r.color + '"></span><span class="lgtx">' + esc(r.from) +
        ' › <b>[' + esc(r.text) + ']</b><br><i>→ ' + esc(r.to) + '</i></span><input type="checkbox"' + (r.checked ? ' checked' : '') + '></label>';
    }).join('');
    $('#lgSat').value = String(state.sat);
    lg.hidden = false;
  }
  function renderLinks() {
    clearLinkLayer();
    var lk = state.links;
    var src = lk && lk.from === state.focusId ? cardEl(lk.from) : null;
    if (!src) { curView = null; applyFocus(); renderLegend(null); return; }
    var layer = $('#lkl'), svg = $('#lks');
    layer.innerHTML = lk.items.map(function (it, k) { return '<div class="lchip" data-k="' + k + '">' + esc(it.text || '(링크)') + ' →</div>'; }).join('');
    var chips = $$('.lchip', layer), ph = $('.phone', src), targets = {}, nb = src.nextElementSibling;
    lk.order.forEach(function (t) {
      var c = cardEl(t); if (!c) return;
      var p = $('.phone', c); targets[t] = {x: c.offsetLeft, y: c.offsetTop, w: p.offsetWidth, h: p.offsetHeight};
    });
    lk.geom = {src: {x: src.offsetLeft, y: src.offsetTop, w: ph.offsetWidth, h: ph.offsetHeight, sc: ph.offsetWidth / CARD.w, limit: nb ? nb.offsetLeft : null},
               targets: targets, chips: chips.map(function (n) { return {w: n.offsetWidth, h: n.offsetHeight}; })};
    var v = curView = F.deriveView(lk, state), defs = '', paths = '', cols = [];
    v.pairs.forEach(function (p) {
      var n = chips[p.k];
      n.style.left = p.chip.x + 'px'; n.style.top = p.chip.y + 'px'; n.style.color = p.color;
      n.setAttribute('data-to', p.to); n.title = '→ ' + (TITLES[p.to] || p.to);
      n.classList.add('on');
      if (!p.path) return;
      var ci = cols.indexOf(p.color); if (ci < 0) { ci = cols.length; cols.push(p.color); }
      paths += '<path class="lk" data-k="' + p.k + '" data-from="' + esc(p.from) + '" data-to="' + esc(p.to) + '" stroke="' + p.color + '" marker-end="url(#hd-lk-' + ci + ')" d="' + p.path + '"><title>' +
        esc(p.text) + ' → ' + esc(TITLES[p.to] || p.to) + '</title></path>';
    });
    cols.forEach(function (c, i) {                    // 화살촉 색 = 선 색(색마다 marker 하나)
      defs += '<marker class="lkm" id="hd-lk-' + i + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="' + c + '"/></marker>';
    });
    $('defs', svg).insertAdjacentHTML('beforeend', defs);
    svg.insertAdjacentHTML('beforeend', paths);
    Object.keys(v.rings).forEach(function (t) {
      var g = v.rings[t], c = cardEl(t); if (!g.n || !c) return;
      var b = document.createElement('span'); b.className = 'lnum'; b.textContent = circled(g.n); $('.phone', c).appendChild(b);
    });
    applyFocus(); renderLegend(v); markHover();
    postTo(lk.from, {type: 'hd-links-paint', items: v.pairs.map(function (p) { return {path: lk.items[p.k].path, color: p.color, n: p.n || undefined}; })});
  }
  function markHover() {                              // 마우스: 그 한 쌍만 진하게, 나머지 쌍·대상 테두리는 흐리게
    var lk = state.links;
    if (!lk) return;
    var v = F.deriveView({from: lk.from, order: lk.order, items: lk.items, titles: lk.titles}, state), by = {};
    v.pairs.forEach(function (p) { by[p.k] = p; });
    $$('#lks path.lk, #lkl .lchip').forEach(function (n) {
      var p = by[n.getAttribute('data-k')];
      n.classList.toggle('em', !!p && p.emph); n.classList.toggle('dim', !!p && p.dim);
    });
    $$('#lgRows .lgrow').forEach(function (n) { n.classList.toggle('em', state.hover === +n.dataset.k); });
    $$('.card.lt', rowsEl).forEach(function (c) {
      var g = v.rings[c.dataset.id];
      c.classList.toggle('em', !!g && g.emph); c.classList.toggle('dim', !!g && g.dim);
    });
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
    setTimeout(end, 300);
  }
  function collapse(id) {
    var c = cardEl(id); if (xpId === id) xpId = null;
    if (!c) return;
    var ph = $('.phone', c), fr = $('iframe', ph);
    ph.style.height = '';
    setTimeout(function () { if (xpId === id) return; fr.style.height = ''; c.style.height = ''; c.classList.remove('xp'); }, 230);
  }

  // 의도 하나 → 리듀서 → 그리기(바뀐 게 없으면 아무것도 안 함)
  function dispatch(intent) {
    var prev = state;
    state = F.reduce(state, intent);
    if (state === prev) return;
    var t = intent.type;
    if (t === 'focus' || t === 'exitFocus') {
      var p = prev.focusId, focusId = state.focusId;
      if (p && p !== focusId) { postTo(p, {type: 'hd-links', on: false}); postTo(p, {type: 'hd-links-paint', items: []}); }
      if (xpId && xpId !== focusId) collapse(xpId);
      curView = null;
      clearTimeout(lkWaitT);
      rowsEl.classList.toggle('lkwait', !!focusId);
      if (focusId) { lkWaitT = setTimeout(function () { rowsEl.classList.remove('lkwait'); }, 1500); requestLinks(focusId); }
      renderLinks();
    } else if (t === 'links') {
      clearTimeout(lkWaitT); rowsEl.classList.remove('lkwait');
      renderLinks();
    } else if (t === 'hover') {
      markHover();
    } else if (t === 'setSat') {
      if (ctx.prefs) { ctx.prefs.sat = state.sat; if (ctx.savePrefs) ctx.savePrefs(); }
      cancelAnimationFrame(satRaf); satRaf = requestAnimationFrame(renderLinks);
    } else {
      renderLinks();
    }
  }

  addEventListener('message', function (e) {
    var d = e.data, focusId = state.focusId;
    if (!d || typeof d !== 'object' || d.type !== 'hd-links' || !focusId || !Array.isArray(d.links)) return;
    var f = frameOf(focusId); if (!f || e.source !== f.contentWindow || performance.now() > lkDeadline) return;
    var id = focusId, m = buildModel(d), want = Math.min(Math.round(+d.docHeight || 0), Math.round(CARD.h * 2.5));
    if (m && xpId !== id && want > CARD.h + 4) {      // 긴 화면: 먼저 펼치고, 다 펼친 뒤 자리를 다시 받아 그린다
      expand(id, want, function () { if (state.focusId === id) requestLinks(id); });
      return;
    }
    dispatch({type: 'links', links: m});
  });
  pane.addEventListener('mousemove', function (e) {
    var lk = state.links;
    if (!lk || !curView || ctx.isDragging()) return;
    var el = e.target, k = null, vis = curView.visible, cl = function (s) { return el && el.closest ? el.closest(s) : null; };
    var row = cl('.lgrow'), chip = cl('.lchip');
    if (row) k = +row.dataset.k;
    else if (chip) k = +chip.dataset.k;
    else if (el && el.classList && el.classList.contains('lk')) k = +el.getAttribute('data-k');
    else if (!cl('#legend')) {
      var c = cl('.card');
      if (c && c.dataset.id === lk.from) {
        var r = $('.phone', c).getBoundingClientRect(), s = r.width / CARD.w, x = (e.clientX - r.left) / s, y = (e.clientY - r.top) / s;
        lk.items.forEach(function (it, i) { var q = it.rect; if (vis[i] && x >= q.x && x <= q.x + q.w && y >= q.y && y <= q.y + q.h) k = i; });
      } else if (c && curView.rings[c.dataset.id]) {
        lk.items.forEach(function (it, i) { if (k == null && vis[i] && it.to === c.dataset.id) k = i; });
      }
    }
    if (k != null && !vis[k]) k = null;
    dispatch({type: 'hover', k: k});
  });
  var lg = $('#legend');
  ['pointerdown', 'wheel', 'dblclick'].forEach(function (ev) { lg.addEventListener(ev, function (e) { e.stopPropagation(); }); });
  $('#lgRows').addEventListener('change', function (e) { var r = e.target.closest('.lgrow'); if (r) dispatch({type: 'toggle', k: +r.dataset.k}); });
  $('#lgSat').addEventListener('input', function (e) { dispatch({type: 'setSat', v: e.target.value}); });

  return {dispatch: dispatch, render: renderLinks, focusId: function () { return state.focusId; }, state: function () { return state; }};
}

HD.viewLinks = {mount: mount};
})();
