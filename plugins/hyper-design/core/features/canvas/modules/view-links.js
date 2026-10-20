/* View — 연결 보기의 DOM/SVG: 색 링크 선·선 위 태그·테두리 고리·범례(색 드롭다운·쌍 색·굵기)·펼치기/접기·마우스 강조.
   경로·태그 자리는 HD.route.plan / HD.labels.placeTags(focus.deriveView 안)가 정한다. 여기서는 DOM 을 재고 그리기만.
   상태는 HD.focus 리듀서 하나. 이벤트는 의도를 만들어 dispatch(intent) 만 부른다 → reduce → 그리기.
   HD.viewLinks.mount(ctx) → {dispatch, render, focusId, state, cardEl, demoExpand, openDropdown, closeDropdown, renameTag(k), group(k), item(i)}
   소켓(.sock): 연결 출발 요소마다 출발 카드 위 점 — 보이기는 CSS(트리거 도구 · 그 연결 강조 .lit), 끌기는 캔버스가 받는다
   ctx = {graph, rowsEl, pane, CARD, LEFT, $, $$, esc, circled, isDragging(), prefs, savePrefs(), tagScale(), names:{get(from,to), set(from,to,text)},
          record?({label, undo(), redo()}) — 선 색·굵기 바꿈을 되돌리기에, isHidden?(id) — 숨긴 화면은 연결 대상·장애물에서 뺀다,
          pending?(from) → {byPath:{path:{op:'link'|'cut', to}}, adds:[{to,path,text,rect}], cutIn:{id:1}} — 아직 파일에 안 들어간 연결 편집을 바로 겹쳐 그린다}
   refresh() — 편집이 바뀌면 마지막 hd-links 답에 편집을 다시 겹쳐 그린다(새 선·바뀐 도착 = 점선 .pd, 끊은 선 = 안 그림)
   names: 태그 이름(이 이동이 무슨 맥락인지) — 버튼 글과 따로. 없으면 태그는 버튼 글. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var F = HD.focus, G = HD.graph;
  var rowsEl = ctx.rowsEl, pane = ctx.pane, CARD = ctx.CARD, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, circled = ctx.circled;
  var S = HD.lineStyle, prefs = ctx.prefs || HD.prefs.defaults();
  var styleOf = function () { return {preset: prefs.preset, rand: prefs.rand, custom: prefs.custom}; };
  var graph = ctx.graph, state = F.initial(styleOf());
  var lkDeadline = 0, lkWaitT = 0, curView = null, xpId = null, styleRaf = 0, lastD = null;
  var TITLES = {};
  (graph.screens || []).forEach(function (s) { TITLES[s.id] = s.title; });

  function cssMs(name, dflt) { return HD.camera.ms(getComputedStyle(document.documentElement).getPropertyValue(name), dflt); }
  function shown(c) { return !(ctx.isHidden && ctx.isHidden(c.dataset.id)); }
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
    var focusId = state.focusId, ids = {}, pd = ctx.pending ? ctx.pending(focusId) : null, seen = {}, pend = {};
    lastD = d;
    $$('.card', rowsEl).filter(shown).forEach(function (c) { ids[c.dataset.id] = 1; });
    var raw = (d.links || []).filter(function (l) { return l && l.rect; }).map(function (l) {
      return {to: String(l.to), path: String(l.path || ''), text: String(l.text || ''), rect: l.rect};
    });
    if (pd) {                                         // 아직 파일에 안 들어간 편집: 끊은 것은 빼고, 도착 바꾼 것·새로 이은 것은 점선으로
      raw = raw.filter(function (l) {
        var o = pd.byPath[l.path]; seen[l.path] = 1;
        if ((o && o.op === 'cut') || pd.cutIn[l.to]) return false;
        if (o && o.op === 'link') { l.to = String(o.to); pend[l.path + '>' + l.to] = 1; }
        return true;
      });
      pd.adds.forEach(function (a) { if (!seen[a.path] && a.rect) { raw.push({to: String(a.to), path: String(a.path), text: String(a.text || ''), rect: a.rect}); pend[a.path + '>' + a.to] = 1; } });
    }
    var items = raw.filter(function (l) { return ids[l.to] && l.to !== focusId; });
    if (!items.length) return null;
    graph = G.addLinks(graph, focusId, items);
    var m = F.assignColors(G.edgesFrom(graph, focusId, 'link').map(function (e) { return {to: e.to, path: e.via.path, text: e.via.text, rect: e.via.rect}; }), d.accent, F.LINK_COLORS);
    m.from = focusId; m.accent = d.accent || ''; m.titles = TITLES; m.docHeight = +d.docHeight || 0;
    m.seq = (graph.screens || []).map(function (s) { return s.id; });   // 흐름 순서 — 앞 화면으로 가는 연결은 가늘고 흐리게
    m.pend = {}; m.part = {};                         // pend = 그 도착 그룹이 모두 반영 대기(점선) · part = 기존 연결과 섞임(선은 실선, 태그에 '반영 대기 n')
    var pc = {}, tc = {};
    m.items.forEach(function (it) { tc[it.ci] = (tc[it.ci] || 0) + 1; if (pend[it.path + '>' + it.to]) pc[it.ci] = (pc[it.ci] || 0) + 1; });
    Object.keys(pc).forEach(function (k) { if (pc[k] === tc[k]) m.pend[k] = 1; else m.part[k] = pc[k]; });
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
    $$('.lnum, .sock:not(.selsock)', rowsEl).forEach(function (n) { n.remove(); });   // 고른 요소의 소켓은 셸이 가진다
  }
  function renderLegend(v) {
    var lg = $('#legend');
    if (!v || !v.legend || !state.focusId) { lg.hidden = true; return; }
    $('#lgTitle').textContent = v.legend.title;
    $('#lgRows').innerHTML = '<label class="lgrow lgall"><span class="lgtx">모두 표시</span><input type="checkbox" id="lgAll"></label>' +
      v.legend.rows.map(function (r) {
        return '<label class="lgrow" data-k="' + r.k + '"><button type="button" class="lgdot" title="이 연결의 색 바꾸기" aria-label="이 연결의 색 바꾸기" style="background:' + r.color + '"></button><span class="lgtx">' + esc(r.from) +
          ' › <b>[' + esc(r.text) + ']</b><br><i>→ ' + esc(r.to) + '</i></span><input type="checkbox"' + (r.checked ? ' checked' : '') + '></label>';
      }).join('');
    var all = $('#lgAll');
    all.checked = v.legend.all === 'on'; all.indeterminate = v.legend.all === 'mixed';
    renderStyle();
    lg.hidden = false;
  }
  function geomOf(card) {                             // 카드 · 그 줄의 위쪽(카드 윗변) · 줄 제목 상자(판 좌표)
    var fl = card.closest('.flow'), cap = fl ? $('.glabel', fl) : null;
    return {x: card.offsetLeft, y: card.offsetTop, rowTop: card.offsetTop, row: fl ? $$('.flow', rowsEl).indexOf(fl) : -1,
            cap: cap ? {top: cap.offsetTop, bottom: cap.offsetTop + cap.offsetHeight} : null};
  }
  function renderLinks(quiet) {                   // quiet: 확대·색 바꿈으로 다시 그릴 때는 그려지는 움직임 없이
    quiet = quiet === true; var still = quiet ? ' style="animation:none"' : '';
    clearLinkLayer();
    var lk = state.links;
    var src = lk && lk.from === state.focusId ? cardEl(lk.from) : null;
    if (!src) { curView = null; applyFocus(); renderLegend(null); return; }
    var layer = $('#lkl'), svg = $('#lks'), gs = F.groupsOf(lk);
    layer.innerHTML = gs.map(function (g) {
      var nm = ctx.names ? ctx.names.get(lk.from, g.to) : '';
      var part = lk.part && lk.part[g.k];
      return '<div class="ltag' + (nm ? ' named' : '') + (lk.pend && lk.pend[g.k] || part ? ' pd' : '') + '"' + still + ' data-k="' + g.k + '" data-to="' + esc(g.to) + '">' +
        esc(nm || g.tag) + (part ? ' · 반영 대기 ' + part : '') + '</div>'; }).join('');
    var tagEls = $$('.ltag', layer), ph = $('.phone', src), sg = geomOf(src), targets = {}, sizes = {};
    lk.order.forEach(function (t) {
      var c = cardEl(t); if (!c) return;
      var p = $('.phone', c), tg = geomOf(c);
      targets[t] = {x: tg.x, y: tg.y, w: p.offsetWidth, h: p.offsetHeight, rowTop: tg.rowTop, cap: tg.cap, row: tg.row};
    });
    var ts = ctx.tagScale ? ctx.tagScale() : 1;        // 작게 볼 때 태그는 화면에서 읽히는 크기로 키운다 → 겹침 상자도 그 크기로
    tagEls.forEach(function (n) { sizes[n.dataset.k] = {w: n.offsetWidth * ts, h: n.offsetHeight * ts}; });
    lk.geom = {src: {x: sg.x, y: sg.y, w: ph.offsetWidth, h: ph.offsetHeight, sc: ph.offsetWidth / CARD.w},
               rowTop: sg.rowTop, cap: sg.cap, srcRow: sg.row, left: ctx.LEFT || 0, targets: targets, tags: sizes,
               cards: $$('.card', rowsEl).filter(shown).map(function (c) { var p = $('.phone', c); return {x: c.offsetLeft, y: c.offsetTop, w: p.offsetWidth, h: p.offsetHeight}; })};
    var v = curView = F.deriveView(lk, state), defs = '', paths = '', cols = [];
    v.groups.forEach(function (g) {
      var n = tagEls[g.k];
      n.style.color = g.color; n.title = g.text + ' → ' + (TITLES[g.to] || g.to) + ' · 두 번 눌러 이름 바꾸기';
      if (g.tag) {                                  // gap: 곧은 선 — 틈 칸 폭에 맞게(말줄임, 마우스 올리면 전체) · float: 틈 칸도 없음 → 마우스 올릴 때만
        n.style.left = g.tag.x + 'px'; n.style.top = g.tag.y + 'px'; n.classList.add(g.tag.float ? 'float' : 'on');
        if (g.tag.gap) { n.classList.add('gap'); n.style.maxWidth = (g.tag.maxW / ts) + 'px'; }
      }
      var ci = cols.indexOf(g.color); if (ci < 0) { ci = cols.length; cols.push(g.color); }
      g.paths.forEach(function (d, i) {
        var pd = !!(lk.pend && lk.pend[g.k]);           // 반영 대기 선: 점선은 화면 px(길이 비율 pathLength 를 쓰면 짧은 선에서 실선처럼 보인다)
        paths += '<path class="lk' + (g.back ? ' bk' : '') + (pd ? ' pd' : '') + '"' + (pd ? '' : ' pathLength="1"') + still + ' data-k="' + g.k + '" data-from="' + esc(g.from) + '" data-to="' + esc(g.to) + '" data-pts="' + esc(JSON.stringify(g.pts[i])) +
          '" stroke="' + g.color + '" marker-end="url(#hd-lk-' + ci + ')" d="' + d + '"><title>' + esc(g.text) + ' → ' + esc(TITLES[g.to] || g.to) + '</title></path>';
      });
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
    var sc = ph.offsetWidth / CARD.w, sk = 16 * ts;   // 소켓 지름: 화면에서 12px 안팎(태그와 같은 배율 보정)
    v.groups.forEach(function (g) {                 // 소켓: 출발 요소 오른쪽 가운데
      g.items.forEach(function (i) {
        var q = lk.items[i].rect, b = document.createElement('span');
        b.className = 'sock'; b.setAttribute('data-k', g.k); b.setAttribute('data-i', i); b.setAttribute('data-to', g.to);
        b.style.left = ((q.x + q.w) * sc) + 'px'; b.style.top = ((q.y + q.h / 2) * sc) + 'px'; b.style.background = g.color;
        b.style.width = b.style.height = sk + 'px'; b.style.margin = (-sk / 2) + 'px 0 0 ' + (-sk / 2) + 'px'; b.style.borderWidth = (2 * ts) + 'px';
        b.title = '끌어서 도착 바꾸기 (지금 → ' + (TITLES[g.to] || g.to) + ')';
        ph.appendChild(b);
      });
    });
    applyFocus(); renderLegend(v); markHover();
    var paint = [];
    v.groups.forEach(function (g) { g.items.forEach(function (i) { paint.push({path: lk.items[i].path, color: g.color, n: g.n || undefined}); }); });
    postTo(lk.from, {type: 'hd-links-paint', items: paint});
  }
  function markHover() {                              // 마우스: 그 그룹만 진하게, 나머지 그룹(선·태그·범례 줄)·대상 테두리는 흐리게
    var lk = state.links;
    if (!lk) return;
    var v = F.deriveView({from: lk.from, order: lk.order, targets: lk.targets, items: lk.items, titles: lk.titles}, state), by = {};
    v.groups.forEach(function (g) { by[g.k] = g; });
    $$('#lks path.lk, #lkl .ltag').forEach(function (n) {
      var g = by[n.getAttribute('data-k')];
      n.classList.toggle('em', !!g && g.emph); n.classList.toggle('dim', !!g && g.dim);
    });
    $$('#lgRows .lgrow[data-k]').forEach(function (n) {
      var r = v.legend.rows[+n.dataset.k];
      n.classList.toggle('em', !!r && r.emph); n.classList.toggle('dim', !!r && r.dim);
    });
    $$('.card.lt', rowsEl).forEach(function (c) {
      var g = v.rings[c.dataset.id];
      c.classList.toggle('em', !!g && g.emph); c.classList.toggle('dim', !!g && g.dim);
    });
    $$('.sock', rowsEl).forEach(function (n) { var g = by[n.getAttribute('data-k')]; n.classList.toggle('lit', !!g && g.emph); });
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

  // 의도 하나 → 리듀서 → 그리기(바뀐 게 없으면 아무것도 안 함)
  function dispatch(intent) {
    var prev = state;
    state = F.reduce(state, intent);
    if (state === prev) return;
    var t = intent.type;
    if (t === 'focus' || t === 'exitFocus' || t === 'pair') {
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
    } else if (t === 'style') {
      cancelAnimationFrame(styleRaf); styleRaf = requestAnimationFrame(function () { renderLinks(true); });
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
  function onHover(e) {
    var lk = state.links;
    if (!lk || !curView || ctx.isDragging()) return;
    var el = e.target, k = null, vis = curView.visible, cl = function (s) { return el && el.closest ? el.closest(s) : null; };
    var row = cl('.lgrow'), tag = cl('.ltag');
    if (row) k = row.dataset.k == null ? null : +row.dataset.k;
    else if (tag) k = +tag.dataset.k;
    else if (el && el.classList && el.classList.contains('lk')) k = +el.getAttribute('data-k');
    else if (!cl('#legend')) {
      var c = cl('.card');
      if (c && c.dataset.id === lk.from) {
        var r = $('.phone', c).getBoundingClientRect(), s = r.width / CARD.w, x = (e.clientX - r.left) / s, y = (e.clientY - r.top) / s;
        lk.items.forEach(function (it, i) { var q = it.rect; if (vis[it.ci] && x >= q.x && x <= q.x + q.w && y >= q.y && y <= q.y + q.h) k = it.ci; });
      } else if (c && curView.rings[c.dataset.id]) {
        k = lk.order.indexOf(c.dataset.id);
      }
    }
    if (k != null && !vis[k]) k = null;
    dispatch({type: 'hover', k: k});
  }
  pane.addEventListener('mousemove', onHover);
  $('#legend').addEventListener('mousemove', onHover);          // 범례는 판 밖(오른쪽 도크)이라 따로
  $('#legend').addEventListener('mouseleave', function () { if (state.links) dispatch({type: 'hover', k: null}); });
  /* 태그 이름 바꾸기(두 번 누르기): 이 이동이 무슨 맥락인지 — 버튼 글은 그대로. 비우면 버튼 글로 돌아간다 */
  $('#lkl').addEventListener('dblclick', function (e) {
    var n = e.target.closest && e.target.closest('.ltag');
    if (!n || !state.links || $('input', n)) return;
    e.preventDefault(); e.stopPropagation();
    startRename(n);
  });
  function renameTag(k) { var n = $('#lkl .ltag[data-k="' + k + '"]'); if (n && state.links && !$('input', n)) startRename(n); }
  function startRename(n) {
    var lk = state.links, to = n.dataset.to, old = ctx.names ? ctx.names.get(lk.from, to) : '', inp = document.createElement('input');
    var base = old ? '' : n.textContent;               // 이름이 없을 때 보이던 버튼 글 — 그대로 두면 이름을 만들지 않는다
    inp.className = 'ltag-in'; inp.value = old || n.textContent; inp.setAttribute('aria-label', '연결 이름');
    inp.style.width = Math.max(6, inp.value.length + 2) + 'em';
    n.textContent = ''; n.appendChild(inp); n.classList.add('editing'); inp.focus(); inp.select();
    var done = false, finish = function (save) {
      if (done) return; done = true;
      var v = inp.value.replace(/\s+/g, ' ').trim();
      if (save && ctx.names) ctx.names.set(lk.from, to, v === base ? '' : v);
      renderLinks(true);
    };
    inp.addEventListener('keydown', function (ev) {
      ev.stopPropagation();                             // Esc 가 연결 보기를 끄지 않게 · 캔버스 단축키도 막는다
      if (ev.key === 'Enter') { ev.preventDefault(); finish(true); } else if (ev.key === 'Escape') { ev.preventDefault(); finish(false); }
    });
    inp.addEventListener('input', function () { inp.style.width = Math.max(6, inp.value.length + 2) + 'em'; });
    inp.addEventListener('blur', function () { finish(true); });
    ['pointerdown', 'click', 'dblclick', 'contextmenu'].forEach(function (ev) { inp.addEventListener(ev, function (x) { x.stopPropagation(); }); });
  }
  var lg = $('#legend');
  ['pointerdown', 'wheel', 'dblclick'].forEach(function (ev) { lg.addEventListener(ev, function (e) { e.stopPropagation(); }); });
  $('#lgRows').addEventListener('change', function (e) {
    if (e.target.id === 'lgAll') { dispatch({type: 'all', on: e.target.checked}); return; }
    var r = e.target.closest('.lgrow[data-k]'); if (r) dispatch({type: 'toggle', k: +r.dataset.k});
  });
  /* ---------- 선 스타일: 색 드롭다운(위로) · 쌍마다 색(● → 색판) · 굵기 — 설명 글 없이 ---------- */
  var dd = $('#lgDd'), ddb = $('#lgDdb'), sw = $('#lgSw'), popKey = null;
  function swatchHtml(cs) { return '<span class="sw">' + cs.map(function (c) { return '<i style="background:' + c + '"></i>'; }).join('') + '</span>'; }
  function presetName() { return prefs.preset === 'random' ? '🎲 랜덤' : (S.PRESETS[prefs.preset] || S.PRESETS.calm).name; }
  function renderStyle() {
    ddb.innerHTML = swatchHtml(S.paletteOf(prefs).slice(0, 6)) + '<b>' + esc(presetName()) + '</b> ▾';
    dd.innerHTML = S.ORDER.map(function (k) {
      return '<button type="button" data-preset="' + k + '"' + (prefs.preset === k ? ' class="on"' : '') + '>' + esc(S.PRESETS[k].name) + swatchHtml(S.PRESETS[k].c.slice(0, 6)) + '</button>';
    }).join('') + '<button type="button" data-preset="random"' + (prefs.preset === 'random' ? ' class="on"' : '') + '>🎲 랜덤 섞기' + (prefs.rand ? swatchHtml(prefs.rand.slice(0, 6)) : '') + '</button>' +
      '<hr><button type="button" class="mut" data-act="reset">● 점으로 바꾼 색 초기화</button>';
    $('#lgW').value = String(prefs.width); $('#lgWv').textContent = prefs.width + 'px';
  }
  function applyWidth() { rowsEl.style.setProperty('--lkw', prefs.width + 'px'); rowsEl.style.setProperty('--lnk', (prefs.width / 2.5).toFixed(2)); }   // 늘 그리는 선도 같은 굵기 설정
  function setStyle(patch, quiet) {                 // quiet: 되돌리기·다시 하기에서 부를 때(기록하지 않음)
    var old = {};
    for (var k in patch) { old[k] = prefs[k]; prefs[k] = patch[k]; }
    if (ctx.savePrefs) ctx.savePrefs();
    renderStyle();
    dispatch({type: 'style', colors: styleOf()});
    if (!quiet && ctx.record) ctx.record({label: '선 색', undo: function () { setStyle(old, true); }, redo: function () { setStyle(patch, true); }});
  }
  function openMenu(el) { el.hidden = false; el.classList.remove('is-closing'); el.classList.add('is-open'); }
  function closeMenu(el) {
    if (el.hidden) return;
    el.classList.remove('is-open'); el.classList.add('is-closing');
    setTimeout(function () { if (el.classList.contains('is-closing')) { el.classList.remove('is-closing'); el.hidden = true; } }, cssMs('--dropdown-close-dur', 150));
  }
  function ddOpen() { return !dd.hidden && !dd.classList.contains('is-closing'); }
  function openDropdown() {                          // 아래로 열림(버튼 아래 6px), 화면 고정 좌표
    closeMenu(sw); renderStyle();
    var r = ddb.getBoundingClientRect();
    dd.style.left = Math.max(8, Math.min(innerWidth - 222, r.left)) + 'px'; dd.style.top = (r.bottom + 6) + 'px';   // 오른쪽 도크 위쪽에 있으니 아래로
    openMenu(dd); ddb.setAttribute('aria-expanded', 'true');
  }
  function closeDropdown() { closeMenu(dd); ddb.setAttribute('aria-expanded', 'false'); }
  ddb.addEventListener('click', function (e) { e.preventDefault(); if (ddOpen()) closeDropdown(); else openDropdown(); });
  dd.addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    e.preventDefault();
    if (b.dataset.act === 'reset') { setStyle({custom: {}}); closeDropdown(); return; }
    var k = b.dataset.preset; if (!k) return;
    if (k === 'random') { setStyle({rand: S.randomSet(), preset: 'random'}); return; }   // 누를 때마다 다시 섞고, 메뉴는 그대로
    setStyle({preset: k}); closeDropdown();
  });
  function openSwatch(dot, key, cur) {
    popKey = key; closeDropdown();
    $('#lgSwG').innerHTML = S.swatches().map(function (c) { return '<button type="button" data-c="' + c + '" title="' + c + '" style="background:' + c + '"></button>'; }).join('');
    $('#lgSwC').value = S.isHex(cur) ? cur.toLowerCase() : '#6b7280';
    var r = dot.getBoundingClientRect();              // 범례 왼쪽 바깥에(범례는 스크롤되므로 화면 고정 좌표)
    sw.style.left = Math.max(8, r.left - 204) + 'px';
    sw.style.top = Math.max(8, Math.min(innerHeight - 190, r.top - 8)) + 'px';
    openMenu(sw);
  }
  function setPair(c) {
    if (!popKey) return;
    var cu = {}; for (var k in prefs.custom) cu[k] = prefs.custom[k];
    cu[popKey] = c; setStyle({custom: cu});
  }
  function rgbHex(c) { var m = String(c).match(/\d+/g); return m && m.length >= 3 ? '#' + m.slice(0, 3).map(function (x) { return ('0' + (+x).toString(16)).slice(-2); }).join('') : ''; }
  $('#lgSwG').addEventListener('click', function (e) { var b = e.target.closest('button[data-c]'); if (!b) return; e.preventDefault(); setPair(b.dataset.c); closeMenu(sw); });
  $('#lgSwC').addEventListener('input', function (e) { setPair(e.target.value.toUpperCase()); });
  $('#lgRows').addEventListener('click', function (e) {
    var dot = e.target.closest('.lgdot'); if (!dot) return;
    e.preventDefault(); e.stopPropagation();                // 줄(label)의 체크를 바꾸지 않는다
    var r = dot.closest('.lgrow[data-k]'), lk = state.links; if (!r || !lk) return;
    openSwatch(dot, lk.from + '>' + lk.order[+r.dataset.k], rgbHex(dot.style.backgroundColor));
  });
  function setWidth(w) { prefs.width = w; $('#lgW').value = String(w); $('#lgWv').textContent = w + 'px'; applyWidth(); if (ctx.savePrefs) ctx.savePrefs(); }
  var wFrom = prefs.width;                            // 끌기 한 번(change) = 되돌리기 한 단계
  $('#lgW').addEventListener('input', function (e) { setWidth(Math.max(1, Math.min(6, +e.target.value || 2.5))); });
  $('#lgW').addEventListener('change', function () {
    var a = wFrom, b = prefs.width; wFrom = b;
    if (a !== b && ctx.record) ctx.record({label: '선 굵기', undo: function () { setWidth(a); wFrom = a; }, redo: function () { setWidth(b); wFrom = b; }});
  });
  document.addEventListener('click', function (e) {          // 밖을 누르면 드롭다운·색판 닫기
    var t = e.target, cl = function (q) { return t && t.closest ? t.closest(q) : null; };
    if (!cl('#lgDdw')) closeDropdown();
    if (!cl('#lgSw') && !cl('.lgdot')) closeMenu(sw);
  }, true);
  addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeDropdown(); closeMenu(sw); } });
  applyWidth(); renderStyle();

  // 펼치기 보여 주기(전환 메뉴 ▶): 펼쳤다가 접기
  function demoExpand(id) {
    if (xpId) return;
    expand(id, Math.round(CARD.h * 1.4), function () { setTimeout(function () { if (xpId === id && state.focusId !== id) collapse(id); }, 500); });
  }

  function refresh() {                               // 편집이 바뀜 → 마지막 답에 다시 겹쳐 그린다(움직임 없이)
    if (!state.focusId || !lastD || lastD.screen !== state.focusId) return;
    var m = buildModel(lastD);
    state = F.reduce(state, {type: 'links', links: m});
    renderLinks(true);
  }
  // 편집(트리거·자르기)이 읽는 연결: 그룹 k = 한 도착 · 항목 i = 출발 요소 하나
  function item(i) { var lk = state.links, it = lk && lk.items[i]; return it ? {from: lk.from, to: it.to, path: it.path, text: it.text, rect: it.rect} : null; }
  function group(k) {
    var lk = state.links; if (!lk || lk.order[k] == null) return null;
    var its = []; lk.items.forEach(function (it, i) { if (it.ci === k) its.push(item(i)); });
    return {from: lk.from, to: lk.order[k], items: its};
  }

  return {dispatch: dispatch, render: renderLinks, focusId: function () { return state.focusId; }, state: function () { return state; },
          cardEl: cardEl, demoExpand: demoExpand, openDropdown: openDropdown, closeDropdown: closeDropdown, renameTag: renameTag, group: group, item: item, refresh: refresh};
}

HD.viewLinks = {mount: mount};
})();
