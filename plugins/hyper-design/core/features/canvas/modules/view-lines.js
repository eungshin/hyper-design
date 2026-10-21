/* View — 판의 연결선 하나뿐인 체계(E20 A): 화면 쌍마다 선 하나, 출발 줄마다 한 색(D6b), 양방향 = 양쪽 화살촉(D6c), 반영 대기 = 점선(E14),
   기획 갈래 = 얇은 회색 실선(D8, 글자 표시 없음). 선 태그 = 방향마다 하나(출발 카드 옆) — 번호 + 연결 이름(없으면 버튼 글).
   번호는 출발 화면마다 1, 2, 3 …(mark(from, to)) — 화면 안 출발 버튼의 테두리·번호(view-links)가 같은 색·같은 번호를 쓴다.
   강조: 고른 카드 전부(focus(ids), E21) 또는 Ctrl+클릭한 쌍 하나(pair) → 그 선·태그 진하게, 나머지 흐리게. 마우스를 올린 카드도 진하게(D6c ②).
   쌍 목록은 HD.graph.overview(Model), 색은 HD.lineStyle.rowColor, 모양은 HD.route.routeCurve. 표시 패널(보이기·투명도·굵기·색 프리셋)도 여기서.
   HD.viewLines.mount(ctx) → {render() → 가장 왼쪽 통로 x, apply(), focus(ids), pair(from, to), mark(from, to) → {n, color}|null, rename(from, to),
                              hits(stagePts, from) → 그은 선이 가로지른 path.ln[], openDropdown(), closeDropdown()}
   ctx = {rowsEl, svg, $, $$, esc, circled(n), CARD, LEFT, graph(), pending(), prefs, savePrefs(), names:{get(from,to), set(from,to,text)}, redraw(), record?({label, undo(), redo()})} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var PLAN = '#B5B8B2';

function mount(ctx) {
  var rowsEl = ctx.rowsEl, svg = ctx.svg, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, CARD = ctx.CARD, LEFT = ctx.LEFT, prefs = ctx.prefs;
  var R = HD.route, S = HD.lineStyle, RADIUS = R.RADIUS, hov = null, foc = {}, pairKey = null, marks = {};

  function render() {
    var box = {}, rowOf = {}, rows = $$('.flow', rowsEl);
    $$('.card:not(.hid):not(.del)', rowsEl).forEach(function (c) {   // 숨긴·삭제 대기 화면의 선은 그리지 않는다
      box[c.dataset.id] = {x: c.offsetLeft, y: c.offsetTop, row: c.parentNode};
      rowOf[c.dataset.id] = rows.indexOf(c.closest('.flow'));
    });
    $$('.alabel', rowsEl).forEach(function (n) { n.remove(); });
    $$('path.ln, marker.lnm', svg).forEach(function (n) { n.remove(); });
    var pairs = HD.graph.overview(ctx.graph(), ctx.pending()).filter(function (p) { return box[p.a] && box[p.b]; });
    var per = {}, seen = {}, lab = {}, num = {}, cols = [], paths = '', labels = '', cross = 0, minX = LEFT;
    marks = {};
    pairs.forEach(function (p) {
      if (!p.ab && p.ba) { var t = p.a; p.a = p.b; p.b = t; p.ab = true; p.ba = false; p.lab = {ab: p.lab.ba, ba: p.lab.ab}; }
      per[p.a] = (per[p.a] || 0) + 1;
    });
    pairs.forEach(function (p) {
      var s = box[p.a], t = box[p.b];
      var j = seen[p.a] || 0, n = per[p.a]; seen[p.a] = j + 1;
      var sx = s.x + CARD.w / 2 + (j - (n - 1) / 2) * 28, tx = t.x + CARD.w / 2, d;
      if (Math.abs(sx - tx) < 3 * RADIUS) sx = tx + (tx > s.x + CARD.w / 2 - 1 ? -1 : 1) * (CARD.w / 2 - 40);   // 같은 칸(위아래 줄): 세로선이 겹치지 않게
      if (s.row === t.row) d = R.routeCurve({x: sx, y: s.y - 6, dir: 'up'}, {x: tx, y: t.y - 10}, {lift: 54, apex: 14 * j});
      else {                                        // 다른 줄: 왼쪽 통로(LEFT − 56 − 22·k)로 우회
        var ck = cross++, lane = LEFT - 56 - 22 * (ck % 4);
        sx = s.x + 60 + 24 * (ck % 3); tx = t.x + 60 + 24 * (ck % 3);
        d = R.routeCurve({x: sx, y: s.y - 6, dir: 'up'}, {x: tx, y: t.y - 8}, {lift: 16, apex: 10 * (ck % 4), laneX: lane});
        minX = Math.min(minX, lane);
      }
      var color = p.plan ? PLAN : S.rowColor(prefs, rowOf[p.a]);
      var ci = cols.indexOf(color); if (ci < 0) { ci = cols.length; cols.push(color); }
      paths += '<path class="ln' + (p.pend ? ' pd' : '') + (p.plan ? ' plan' : '') + '" data-from="' + esc(p.a) + '" data-to="' + esc(p.b) + '" data-both="' + (p.ba ? 1 : 0) +
        '" stroke="' + color + '" marker-end="url(#hd-ln-' + ci + ')"' + (p.ba ? ' marker-start="url(#hd-lns-' + ci + ')"' : '') + ' d="' + d + '"/>';
      if (p.plan) return;
      [['ab', p.a, p.b], ['ba', p.b, p.a]].forEach(function (x) {   // 방향마다 번호 하나 + 태그 하나(출발 카드 오른쪽에 쌓음)
        var from = x[1], to = x[2]; if (!p[x[0]]) return;
        var k = num[from] = (num[from] || 0) + 1, f = box[from], li = lab[from] || 0; lab[from] = li + 1;
        marks[from + '>' + to] = {n: k, color: color};
        var nm = ctx.names ? ctx.names.get(from, to) : '', tx2 = nm || p.lab[x[0]].slice(0, 2).join(' · ') || (p.pend ? '반영 대기' : '');
        labels += '<div class="alabel' + (nm ? ' named' : '') + '" data-from="' + esc(from) + '" data-to="' + esc(to) + '" style="left:' + (f.x + CARD.w + 10) + 'px;top:' + (f.y + 24 + li * 44) +
          'px;border-color:' + color + '" title="두 번 눌러 이름 바꾸기">' + esc(ctx.circled(k)) + (tx2 ? ' ' + esc(tx2) : '') + '</div>';
      });
    });
    var defs = '';
    cols.forEach(function (c, i) {                    // 화살촉 색 = 선 색 · 양방향은 시작에도(반대로)
      var head = '<path d="M0,0 L10,5 L0,10 z" fill="' + c + '"/>';
      defs += '<marker class="lnm" id="hd-ln-' + i + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto">' + head + '</marker>' +
              '<marker class="lnm" id="hd-lns-' + i + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">' + head + '</marker>';
    });
    $('defs', svg).insertAdjacentHTML('beforeend', defs);
    svg.insertAdjacentHTML('beforeend', paths);
    rowsEl.insertAdjacentHTML('beforeend', labels);
    mark();
    return minX;
  }
  // 강조: 고른 카드(또는 Ctrl+클릭한 쌍)의 선·태그·이어진 카드 · 마우스를 올린 카드의 선·태그
  function touches(n, ids) { return !!ids[n.getAttribute('data-from')] || !!ids[n.getAttribute('data-to')]; }
  function inPair(n) {
    if (!pairKey) return false;
    var f = n.getAttribute('data-from'), t = n.getAttribute('data-to');
    return pairKey === f + '>' + t || (n.tagName.toLowerCase() === 'path' && pairKey === t + '>' + f);
  }
  function mark() {
    var on = Object.keys(foc).length > 0 || !!pairKey, linked = {};
    rowsEl.classList.toggle('focusing', on);
    rowsEl.classList.toggle('lnhov', !!hov);
    for (var id in foc) linked[id] = 1;
    $$('path.ln, .alabel', rowsEl).forEach(function (n) {
      var lit = pairKey ? inPair(n) : touches(n, foc);
      n.classList.toggle('on', lit);
      n.classList.toggle('em', !!hov && (n.getAttribute('data-from') === hov || n.getAttribute('data-to') === hov));
      if (lit) { linked[n.getAttribute('data-from')] = 1; linked[n.getAttribute('data-to')] = 1; }
    });
    $$('.card', rowsEl).forEach(function (c) {
      c.classList.toggle('hl', on && !!linked[c.dataset.id]);
      c.classList.toggle('focus', !!foc[c.dataset.id]);
    });
  }
  // 자르기: 그은 선(판 좌표 점, from 번째 마디부터)이 가로지른 선들(기획 갈래·숨긴 선 빼고)
  function segX(a, b, c, d) {
    function o(p, q, r) { return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]); }
    return o(a, b, c) * o(a, b, d) < 0 && o(c, d, a) * o(c, d, b) < 0;
  }
  function pointsOf(pth) {                           // 선 → 판 좌표 점 목록(12px 간격, 모양이 바뀔 때만 다시 잰다)
    if (pth._pts && pth._d === pth.getAttribute('d')) return pth._pts;
    var L = pth.getTotalLength(), out = [];
    for (var s = 0; s <= L; s += 12) { var q = pth.getPointAtLength(s); out.push([q.x, q.y]); }
    var e = pth.getPointAtLength(L); out.push([e.x, e.y]);
    pth._pts = out; pth._d = pth.getAttribute('d');
    return out;
  }
  function hits(cs, from) {
    if (!prefs.lines) return [];
    return $$('path.ln:not(.plan)', svg).filter(function (pth) {
      var q = pointsOf(pth);
      for (var i = 1; i < q.length; i++) for (var j = Math.max(1, from || 1); j < cs.length; j++) if (segX(q[i - 1], q[i], cs[j - 1], cs[j])) return true;
      return false;
    });
  }
  function focus(ids) { foc = {}; (ids || []).forEach(function (id) { foc[id] = 1; }); pairKey = null; mark(); }
  function pair(from, to) { pairKey = from && to ? from + '>' + to : null; mark(); }
  rowsEl.addEventListener('mouseover', function (e) {
    var c = e.target.closest ? e.target.closest('.card') : null, id = c ? c.dataset.id : null;
    if (id !== hov) { hov = id; mark(); }
  });
  rowsEl.addEventListener('mouseleave', function () { if (hov) { hov = null; mark(); } });

  /* 태그 이름 바꾸기(두 번 누르기): 이 이동이 무슨 맥락인지 — 버튼 글은 그대로, 비우면 버튼 글로 돌아간다(hd-link-names) */
  rowsEl.addEventListener('dblclick', function (e) {
    var n = e.target.closest && e.target.closest('.alabel');
    if (!n || $('input', n)) return;
    e.preventDefault(); e.stopPropagation();
    startRename(n);
  });
  function rename(from, to) {
    var n = $$('.alabel', rowsEl).filter(function (x) { return x.getAttribute('data-from') === from && x.getAttribute('data-to') === to; })[0];
    if (n && !$('input', n)) startRename(n);
  }
  function startRename(n) {
    var from = n.getAttribute('data-from'), to = n.getAttribute('data-to'), old = ctx.names ? ctx.names.get(from, to) : '';
    var shown = n.textContent.replace(/^\S+\s?/, ''), base = old ? '' : shown;   // 번호를 뺀 글 — 이름이 없을 때 보이던 버튼 글은 그대로 두면 이름을 만들지 않는다
    var inp = document.createElement('input');
    inp.className = 'ltag-in'; inp.value = old || shown; inp.setAttribute('aria-label', '연결 이름');
    inp.style.width = Math.max(6, inp.value.length + 2) + 'em';
    n.textContent = ''; n.appendChild(inp); n.classList.add('editing'); inp.focus(); inp.select();
    var done = false, finish = function (save) {
      if (done) return; done = true;
      var v = inp.value.replace(/\s+/g, ' ').trim();
      if (save && ctx.names) ctx.names.set(from, to, v === base ? '' : v);
      ctx.redraw();
    };
    inp.addEventListener('keydown', function (ev) {
      ev.stopPropagation();                             // Esc 가 고르기를 풀지 않게 · 캔버스 단축키도 막는다
      if (ev.key === 'Enter') { ev.preventDefault(); finish(true); } else if (ev.key === 'Escape') { ev.preventDefault(); finish(false); }
    });
    inp.addEventListener('input', function () { inp.style.width = Math.max(6, inp.value.length + 2) + 'em'; });
    inp.addEventListener('blur', function () { finish(true); });
    ['pointerdown', 'click', 'dblclick', 'contextmenu'].forEach(function (ev) { inp.addEventListener(ev, function (x) { x.stopPropagation(); }); });
  }

  // 표시 패널: 보이기 · 투명도 · 굵기(끌기 한 번 = 되돌리기 한 단계) · 색 프리셋
  var show = $('#lnShow'), op = $('#lnOp'), wEl = $('#lgW'), wv = $('#lgWv');
  function apply() {
    rowsEl.classList.toggle('nolines', !prefs.lines);
    rowsEl.style.setProperty('--lnop', String(prefs.op));
    rowsEl.style.setProperty('--lnk', (prefs.width / 2.5).toFixed(2));
    if (show) { show.setAttribute('aria-pressed', String(prefs.lines)); show.title = prefs.lines ? '선 숨기기' : '선 보이기'; }
    if (op) op.value = String(prefs.op);
    if (wEl) { wEl.value = String(prefs.width); if (wv) wv.textContent = prefs.width + 'px'; }
  }
  function set(patch) { for (var k in patch) prefs[k] = patch[k]; ctx.savePrefs(); apply(); }
  function slider(el, key, label, clamp) {
    if (!el) return;
    var from = prefs[key];
    el.addEventListener('input', function () { var p = {}; p[key] = clamp(+el.value); set(p); });
    el.addEventListener('change', function () {
      var a = from, b = prefs[key]; from = b;
      var to = function (v) { return function () { var p = {}; p[key] = v; set(p); from = v; }; };
      if (a !== b && ctx.record) ctx.record({label: label, undo: to(a), redo: to(b)});
    });
  }
  if (show) show.addEventListener('click', function () {
    var a = prefs.lines, b = !a; set({lines: b});
    if (ctx.record) ctx.record({label: b ? '선 보이기' : '선 숨기기', undo: function () { set({lines: a}); }, redo: function () { set({lines: b}); }});
  });
  slider(op, 'op', '선 투명도', function (v) { return Math.max(0.15, Math.min(1, v || 0.55)); });
  slider(wEl, 'width', '선 굵기', function (v) { return Math.max(1, Math.min(6, v || 2.5)); });

  /* 색 프리셋 드롭다운(줄 색이 이 팔레트에서 나온다) */
  var dd = $('#lgDd'), ddb = $('#lgDdb');
  function cssMs(name, dflt) { return HD.camera.ms(getComputedStyle(document.documentElement).getPropertyValue(name), dflt); }
  function swatchHtml(cs) { return '<span class="sw">' + cs.map(function (c) { return '<i style="background:' + c + '"></i>'; }).join('') + '</span>'; }
  function presetName() { return prefs.preset === 'random' ? '🎲 랜덤' : (S.PRESETS[prefs.preset] || S.PRESETS.calm).name; }
  function renderStyle() {
    if (!ddb) return;
    ddb.innerHTML = swatchHtml(S.paletteOf(prefs).slice(0, 6)) + '<b>' + esc(presetName()) + '</b> ▾';
    dd.innerHTML = S.ORDER.map(function (k) {
      return '<button type="button" data-preset="' + k + '"' + (prefs.preset === k ? ' class="on"' : '') + '>' + esc(S.PRESETS[k].name) + swatchHtml(S.PRESETS[k].c.slice(0, 6)) + '</button>';
    }).join('') + '<button type="button" data-preset="random"' + (prefs.preset === 'random' ? ' class="on"' : '') + '>🎲 랜덤 섞기' + (prefs.rand ? swatchHtml(prefs.rand.slice(0, 6)) : '') + '</button>';
  }
  function setStyle(patch, quiet) {                 // quiet: 되돌리기·다시 하기에서 부를 때(기록하지 않음)
    var old = {};
    for (var k in patch) { old[k] = prefs[k]; prefs[k] = patch[k]; }
    ctx.savePrefs(); renderStyle(); ctx.redraw();
    if (!quiet && ctx.record) ctx.record({label: '선 색', undo: function () { setStyle(old, true); }, redo: function () { setStyle(patch, true); }});
  }
  function ddOpen() { return dd && !dd.hidden && !dd.classList.contains('is-closing'); }
  function openDropdown() {                          // 아래로 열림(버튼 아래 6px), 화면 고정 좌표
    if (!dd) return;
    renderStyle();
    var r = ddb.getBoundingClientRect();
    dd.style.left = Math.max(8, Math.min(innerWidth - 222, r.left)) + 'px'; dd.style.top = (r.bottom + 6) + 'px';
    dd.hidden = false; dd.classList.remove('is-closing'); dd.classList.add('is-open'); ddb.setAttribute('aria-expanded', 'true');
  }
  function closeDropdown() {
    if (!dd || dd.hidden) return;
    dd.classList.remove('is-open'); dd.classList.add('is-closing'); ddb.setAttribute('aria-expanded', 'false');
    setTimeout(function () { if (dd.classList.contains('is-closing')) { dd.classList.remove('is-closing'); dd.hidden = true; } }, cssMs('--dropdown-close-dur', 150));
  }
  if (ddb) {
    ddb.addEventListener('click', function (e) { e.preventDefault(); if (ddOpen()) closeDropdown(); else openDropdown(); });
    dd.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      e.preventDefault();
      var k = b.dataset.preset; if (!k) return;
      if (k === 'random') { setStyle({rand: S.randomSet(), preset: 'random'}); return; }   // 누를 때마다 다시 섞고, 메뉴는 그대로
      setStyle({preset: k}); closeDropdown();
    });
    document.addEventListener('click', function (e) { if (!(e.target.closest && e.target.closest('#lgDdw'))) closeDropdown(); }, true);
    addEventListener('keydown', function (e) { if (e.key === 'Escape') closeDropdown(); });
  }
  apply(); renderStyle();
  return {render: render, apply: apply, focus: focus, pair: pair, rename: rename, hits: hits, openDropdown: openDropdown, closeDropdown: closeDropdown,
          mark: function (from, to) { return marks[from + '>' + to] || null; }};
}

HD.viewLines = {mount: mount};
})();
