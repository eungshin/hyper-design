/* View — 판의 연결선 하나뿐인 체계(E20 A): 화면 쌍마다 선 하나, 출발 줄마다 한 색(D6b), 양방향 = 양쪽 화살촉(D6c), 반영 대기 = 점선(E14),
   기획 갈래 = 얇은 회색 실선(D8, 글자 표시 없음). 선 태그 = 방향마다 하나 — 번호 + 연결 이름(없으면 버튼 글, 트리거 여럿이면 "첫 글 외 N", R46).
   태그 자리(R46, 규칙 HD.lineTags): 제 선이 출발 카드를 떠나는 점에서 선에 붙이고, 보이는 태그끼리 겹치면 제 선을 따라 바깥으로 비킨다(한도 안에서만).
   목록 창(#ltpop, R46): 트리거가 둘 이상이거나 이름 붙인 태그 · 그 선에 마우스를 올리면 태그 옆에 트리거 목록, 줄에 올리면 화면 안 그 버튼 표시가 진해진다(ctx.hilite).
   번호는 출발 화면마다 1, 2, 3 …(mark(from, to)) — 화면 안 출발 버튼의 테두리·번호(view-links)가 같은 색·같은 번호를 쓴다.
   강조: 고른 카드 전부(focus(ids), E21) 또는 Ctrl+클릭한 쌍 하나(pair) → 그 선·태그 진하게, 나머지 흐리게. 마우스를 올린 카드도 진하게(D6c ②).
   화살촉(#286): 채운 marker 라 선의 stroke-opacity 가 닿지 않는다 — 색마다 투명도 단계(HD.lineTone.TONES)별 marker(hd-ln-<색>-<단계>, data-tone)를 두고
     mark() 가 선마다 HD.lineTone.tone(상태) 단계의 화살촉을 단다(바뀐 선만 다시 씀). 선에 opacity 를 주지 않는다(래스터 그대로).
   쌍 목록은 HD.graph.overview(Model), 색은 HD.lineStyle.rowColor, 길은 HD.route.plan(지금 상자 자리 — 쪽·꺾는 곳·막혔을 때만 돌아가기). 표시 패널(보이기·투명도·굵기·색 프리셋)도 여기서.
   HD.viewLines.mount(ctx) → {render() → 가장 왼쪽 통로 x, apply(), focus(ids), pair(from, to), mark(from, to) → {n, color}|null, rename(from, to),
                              hits(stagePts, from) → 그은 선이 가로지른 path.ln[], openDropdown(), closeDropdown()}
   ctx = {rowsEl, svg, $, $$, esc, circled(n), CARD, LEFT, graph(), pending(), prefs, savePrefs(), names:{get(from,to), set(from,to,text)}, redraw(), record?({label, undo(), redo()}),
          title?(id), triggers?(from, to) → [{text, path}]|null(고른 화면 안 링크 — 없으면 판 데이터 글), hilite?(from, to, path|null)(화면 안 그 버튼 표시 진하게 · null = 되돌림),
          avoid?() → [{l, t, r, b}](태그가 비킬 떠 있는 막대 — 화면 px)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var PLAN = '#B5B8B2';

function mount(ctx) {
  var rowsEl = ctx.rowsEl, svg = ctx.svg, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, CARD = ctx.CARD, LEFT = ctx.LEFT, prefs = ctx.prefs;
  function dim(id) { return ctx.sizeOf ? ctx.sizeOf(id) : CARD; }   // 그 카드 크기(task 46 — 카드마다 크기, 없으면 프로젝트 카드)
  var R = HD.route, S = HD.lineStyle, LT = HD.lineTone, T = HD.lineTags, hov = null, foc = {}, pairKey = null, marks = {};

  // 그리기: 쌍(from>to)마다 선 하나·방향마다 태그 하나를 열쇠로 기억한다. 쌍·색 목록이 그대로면 바뀐 d·자리만 고쳐 쓰고,
  // 달라지면(편집·숨기기·색 프리셋) 전부 새로 넣는다. 카드 자리를 먼저 모두 읽고 그다음 쓴다(읽기·쓰기 번갈아 하지 않게).
  // 길(쪽·꺾는 곳·띄운 줄)은 HD.route.plan 이 지금 상자 자리로 정한다(DOM 줄이 아니라) — 여기서는 받아 쓰기만.
  // 카드 끌기(.card.moving 이 있는 동안): 첫 프레임에 상자·쌍 목록을 한 번 재 두고, 그다음 프레임은 DOM 자리를 읽지 않고
  // 움직인 카드의 style.left/top 만으로 그 카드에 닿은 선의 d·태그 자리만 고친다. 선을 숨겼으면 끄는 동안 아무것도 하지 않는다.
  var shape = null, lnEls = [], lbEls = [], last = null;
  svg.style.willChange = 'transform';              // 선 svg 를 제 층에 — 카드를 끌 때 선 전체를 다시 래스터하지 않게(task 38)
  function render() {
    var moving = $$('.card.moving', rowsEl);
    if (moving.length) {
      if (!prefs.lines) return last ? last.minX : LEFT;
      if (last && last.dragging) return dragFrame(moving);
      var m = full(); last.dragging = true; return m;
    }
    return full();
  }
  // 태그 기본 자리(R46) = 제 선이 그 태그 쪽 카드를 떠나는 점(ab = 선의 첫 점, ba = 끝 점), 태그 가운데를 그 점에. 보이는 태그는 seat() 가 제 선에 붙여 옮긴다.
  // (예전: 위·아래로 떠나는 선의 태그는 카드 오른쪽 틈에 44px 씩 쌓여 어느 선의 것인지 보이지 않았다)
  var MID = 'translate(-50%,-50%)';
  function labelAt(r, end) {
    var q = T.anchor(r, end);
    if (!q) { console.warn('[hd] 선 태그: 길이 없는 선 — 판 원점에 둠'); q = [0, 0]; }
    return {left: q[0] + 'px', top: q[1] + 'px', tf: MID};
  }
  function full() {
    var box = {}, base = {}, rowOf = {}, rows = $$('.flow', rowsEl);
    $$('.card:not(.hid):not(.del)', rowsEl).forEach(function (c) {   // 숨긴·삭제 대기 화면의 선은 그리지 않는다
      var ph = c.querySelector('.phone'), id = c.dataset.id;
      var b = {x: c.offsetLeft, y: c.offsetTop, w: c.offsetWidth || dim(id).w, h: Math.max(c.offsetHeight, ph ? ph.offsetHeight : 0) || dim(id).h};
      box[id] = b;
      base[id] = {x: b.x - (parseFloat(c.style.left) || 0), y: b.y - (parseFloat(c.style.top) || 0)};   // 끄는 동안 style 만으로 자리를 알게
      rowOf[id] = rows.indexOf(c.closest('.flow'));
    });
    var pairs = HD.graph.overview(ctx.graph(), ctx.pending()).filter(function (p) { return box[p.a] && box[p.b]; });
    var num = {}, cols = [], lns = [], lbs = [], minX = LEFT;
    marks = {};
    pairs.forEach(function (p) {
      if (!p.ab && p.ba) { var t = p.a; p.a = p.b; p.b = t; p.ab = true; p.ba = false; p.lab = {ab: p.lab.ba, ba: p.lab.ab}; p.n = {ab: p.n.ba, ba: p.n.ab}; }
    });
    var res = R.plan(box, pairs, {corridorX: LEFT - 56});
    pairs.forEach(function (p, i) {
      var r = res[i];
      if (r.mode === 'corridor') minX = Math.min(minX, r.pts[2][0]);
      var color = p.plan ? PLAN : S.rowColor(prefs, rowOf[p.a]);
      var ci = cols.indexOf(color); if (ci < 0) { ci = cols.length; cols.push(color); }
      lns.push({from: p.a, to: p.b, cls: 'ln' + (p.pend ? ' pd' : '') + (p.plan ? ' plan' : ''), both: p.ba ? 1 : 0, color: color, ci: ci, d: r.d});
      if (p.plan) return;
      [['ab', p.a, p.b], ['ba', p.b, p.a]].forEach(function (x) {   // 방향마다 번호 하나 + 태그 하나(트리거가 여럿이어도 하나 — "첫 글 외 N")
        var from = x[1], to = x[2]; if (!p[x[0]]) return;
        var end = x[0] === 'ba' ? 1 : 0, k = num[from] = (num[from] || 0) + 1;
        marks[from + '>' + to] = {n: k, color: color};
        var nm = ctx.names ? ctx.names.get(from, to) : '', tg = T.text({texts: p.lab[x[0]], n: p.n[x[0]], name: nm, pend: p.pend});
        var at = labelAt(r, end);
        lbs.push({from: from, to: to, pi: i, end: end, named: tg.named, more: tg.more, k: k, texts: p.lab[x[0]], left: at.left, top: at.top, tf: at.tf, color: color,
                  html: esc(ctx.circled(k)) + (tg.text ? ' ' + esc(tg.text) : '')});
      });
    });
    var key = cols.join(',') + '|' + lns.map(function (l) { return l.from + '>' + l.to; }).join('\n') + '|' + lbs.map(function (l) { return l.from + '>' + l.to; }).join('\n');
    var same = key === shape && lns.length === lnEls.length && lbs.length === lbEls.length &&
      lnEls.every(function (n) { return n.isConnected; }) && lbEls.every(function (n) { return n.isConnected; });
    if (same) { lns.forEach(function (l, i) { patchLine(lnEls[i], l); }); lbs.forEach(function (l, i) { patchLabel(lbEls[i], l); }); }
    else { rebuild(cols, lns, lbs); shape = key; }
    last = {box: box, base: base, pairs: pairs, res: res, lns: lns, lbs: lbs, minX: minX, dragging: false};
    mark();                                          // 태그 얹기(seat)가 지금 길(last.res)을 쓴다
    return minX;
  }
  function dragFrame(moving) {                       // 끄는 프레임: DOM 자리 읽기 없음 · 움직인 카드에 닿은 선·태그만 쓴다
    var only = {}, any = false;
    moving.forEach(function (c) {
      var id = c.dataset.id, b = last.box[id], o = last.base[id]; if (!b || !o) return;
      last.box[id] = {x: o.x + (parseFloat(c.style.left) || 0), y: o.y + (parseFloat(c.style.top) || 0), w: b.w, h: b.h};
      only[id] = 1; any = true;
    });
    if (!any) return last.minX;
    last.res = R.plan(last.box, last.pairs, {corridorX: LEFT - 56, only: only, prev: last.res});
    last.pairs.forEach(function (p, i) {
      if (!only[p.a] && !only[p.b]) return;
      var l = last.lns[i], n = lnEls[i], d = last.res[i].d;
      if (l && n && l.d !== d) { l.d = d; n.setAttribute('d', d); }
    });
    last.lbs.forEach(function (l, i) {
      var p = last.pairs[l.pi]; if (!only[p.a] && !only[p.b]) return;
      var at = labelAt(last.res[l.pi], l.end), n = lbEls[i];
      if (!n) return;
      n.style.left = l.left = at.left; n.style.top = l.top = at.top;
    });
    seat(true);                                      // 보이는 태그(고른 카드의 것 몇 개)만 다시 붙인다 — 크기·판 자리는 지난번 잰 값
    return last.minX;
  }
  function rebuild(cols, lns, lbs) {                  // 처음·쌍 목록이나 색이 바뀌었을 때: 전부 지우고 새로
    $$('.alabel', rowsEl).forEach(function (n) { n.remove(); });
    $$('path.ln, marker.lnm', svg).forEach(function (n) { n.remove(); });
    var defs = '', paths = '', labels = '';
    cols.forEach(function (c, i) {                    // 화살촉 색 = 선 색 · 양방향은 시작에도(반대로) · 투명도 단계마다 하나(#286)
      var head = '<path d="M0,0 L10,5 L0,10 z" fill="' + c + '"/>';
      LT.TONES.forEach(function (t) {
        defs += '<marker class="lnm" data-tone="' + t + '" id="hd-ln-' + i + '-' + t + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto">' + head + '</marker>' +
                '<marker class="lnm" data-tone="' + t + '" id="hd-lns-' + i + '-' + t + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">' + head + '</marker>';
      });
    });
    lns.forEach(function (l) {
      paths += '<path class="' + l.cls + '" data-from="' + esc(l.from) + '" data-to="' + esc(l.to) + '" data-both="' + l.both +
        '" stroke="' + l.color + '" d="' + l.d + '"/>';   // 화살촉은 mark() 가 단계에 맞춰 단다
    });
    lbs.forEach(function (l) {
      labels += '<div class="alabel' + (l.named ? ' named' : '') + '" data-from="' + esc(l.from) + '" data-to="' + esc(l.to) + '" data-more="' + l.more + '" style="left:' + l.left + ';top:' + l.top + (l.tf ? ';transform:' + l.tf : '') +
        ';border-color:' + l.color + '" title="두 번 눌러 이름 바꾸기">' + l.html + '</div>';
    });
    $('defs', svg).insertAdjacentHTML('beforeend', defs);
    svg.insertAdjacentHTML('beforeend', paths);
    rowsEl.insertAdjacentHTML('beforeend', labels);
    lnEls = $$('path.ln', svg); lbEls = $$('.alabel', rowsEl);
    lnEls.forEach(function (n, i) { n._hd = lns[i]; });
    lbEls.forEach(function (n, i) { n._hd = lbs[i]; });
  }
  function patchLine(n, l) {                          // 같은 쌍의 선: 달라진 속성만(대개 끈 카드에 닿은 선의 d 하나)
    var o = n._hd || {};
    if (o.cls !== l.cls) { n.classList.toggle('pd', l.cls.indexOf(' pd') >= 0); n.classList.toggle('plan', l.cls.indexOf(' plan') >= 0); }
    if (o.both !== l.both) n.setAttribute('data-both', String(l.both));
    if (o.color !== l.color) n.setAttribute('stroke', l.color);
    if (o.ci !== l.ci || o.both !== l.both) n._tone = null;   // 화살촉 색·양쪽이 바뀜 — mark() 가 다시 단다
    if (o.d !== l.d) n.setAttribute('d', l.d);
    n._hd = l;
  }
  function patchLabel(n, l) {                         // 같은 방향의 태그: 자리·색·글만(이름 고치던 칸이면 글을 되돌린다 — 예전처럼 새로 그린 것과 같게)
    var o = n._hd || {}, editing = n.classList.contains('editing');
    if (o.left !== l.left) n.style.left = l.left;
    if (o.top !== l.top) n.style.top = l.top;
    if (o.tf !== l.tf) n.style.transform = l.tf;
    if (o.color !== l.color) n.style.borderColor = l.color;
    if (o.named !== l.named) n.classList.toggle('named', l.named);
    if (o.more !== l.more) n.setAttribute('data-more', String(l.more));
    if (editing) n.classList.remove('editing');
    if (o.html !== l.html || editing) n.innerHTML = l.html;
    n._hd = l;
  }
  // 강조: 고른 카드(또는 Ctrl+클릭한 쌍)의 선·태그·이어진 카드 · 마우스를 올린 카드의 선·태그
  function touches(n, ids) { return !!ids[n.getAttribute('data-from')] || !!ids[n.getAttribute('data-to')]; }
  function inPair(n) {
    if (!pairKey) return false;
    var f = n.getAttribute('data-from'), t = n.getAttribute('data-to');
    return pairKey === f + '>' + t || (n.tagName.toLowerCase() === 'path' && pairKey === t + '>' + f);
  }
  function heads(n, st) {                            // 선 하나의 화살촉 = 그 선과 같은 투명도 단계(바뀐 선만 쓴다)
    var l = n._hd; if (!l) return;
    var t = LT.tone(st);
    if (n._tone === t) return;
    n._tone = t;
    n.setAttribute('marker-end', 'url(#hd-ln-' + l.ci + '-' + t + ')');
    if (l.both) n.setAttribute('marker-start', 'url(#hd-lns-' + l.ci + '-' + t + ')'); else n.removeAttribute('marker-start');
  }
  function mark() {
    var on = Object.keys(foc).length > 0 || !!pairKey, linked = {};
    rowsEl.classList.toggle('focusing', on);
    rowsEl.classList.toggle('lnhov', !!hov);
    for (var id in foc) linked[id] = 1;
    $$('path.ln, .alabel', rowsEl).forEach(function (n) {
      var lit = pairKey ? inPair(n) : touches(n, foc), em = !!hov && (n.getAttribute('data-from') === hov || n.getAttribute('data-to') === hov);
      n.classList.toggle('on', lit);
      n.classList.toggle('em', em);
      if (n.tagName.toLowerCase() === 'path') heads(n, {focusing: on, hover: !!hov, on: lit, em: em, pd: n.classList.contains('pd')});
      if (lit) { linked[n.getAttribute('data-from')] = 1; linked[n.getAttribute('data-to')] = 1; }
    });
    $$('.card', rowsEl).forEach(function (c) {
      c.classList.toggle('hl', on && !!linked[c.dataset.id]);
      c.classList.toggle('focus', !!foc[c.dataset.id]);
    });
    seat();
  }
  // R46: 보이는 태그(고른·올린 카드의 것뿐)를 제 선에 붙인다(선 옆, 가장자리가 선에 닿게) — 화면 px 로 재서 HD.lineTags.seat(겹치면 제 선을 따라 비킴, 한도 안에서만)
  // → 판 좌표로 되돌려 left/top. 판 배율이 멈춘 뒤(document 'hd-label-scale')에도 다시(태그는 화면 px 크기라 판 거리가 배율 따라 달라진다).
  // cached = 끄는 프레임: 보이는지·태그 크기·판 자리를 다시 재지 않는다(지난번 값)
  var view = null;
  function seat(cached) {
    if (!last) return;
    var shown = [];
    lbEls.forEach(function (n, i) { if (n.isConnected && (cached ? n._seen : (n._seen = getComputedStyle(n).display !== 'none'))) shown.push(i); });
    if (shown.length) {
      if (!cached || !view) {
        var rr = rowsEl.getBoundingClientRect(), z = rowsEl.offsetWidth ? rr.width / rowsEl.offsetWidth : 1;
        view = {x: rr.left, y: rr.top, z: z || 1};
      }
      var items = shown.map(function (i) {
        var n = lbEls[i], l = n._hd, pts = l && last.res[l.pi] ? T.from(last.res[l.pi], l.end) : null;
        if (!cached || !n._sz) { var b = n.getBoundingClientRect(); n._sz = {w: b.width, h: b.height}; }
        return pts ? {pts: pts.map(function (q) { return [view.x + q[0] * view.z, view.y + q[1] * view.z]; }), w: n._sz.w, h: n._sz.h} : null;
      });
      T.seat(items, {avoid: ctx.avoid ? ctx.avoid() : []}).forEach(function (s, j) {
        if (!s) return;
        var n = lbEls[shown[j]], x = ((s.x - view.x) / view.z).toFixed(1) + 'px', y = ((s.y - view.y) / view.z).toFixed(1) + 'px';
        if (n.style.left !== x) n.style.left = x;
        if (n.style.top !== y) n.style.top = y;
        n.classList.toggle('ltag-hid', !!s.hidden);    // 선 전체가 줄 제목·막대 밑 — 숨겨서 그 누르기를 가로막지 않는다
      });
    }
    if (pop.tag) placePop();
  }
  document.addEventListener('hd-label-scale', function () { if (rowsEl.classList.contains('focusing') || hov) seat(); });

  // 목록 창(#ltpop, R46): 한 태그 = 한 선 — 트리거가 둘 이상(data-more > 0)이거나 이름을 붙여 버튼 글이 가려진 태그에 마우스를 올리면(태그 또는 그 선)
  // 태그 옆에 그 선의 트리거(버튼 글)를 모두 보인다. 줄에 올리면 화면 안 그 버튼의 표시가 진해진다(ctx.hilite — 같은 번호 표시 길, palette.js hd-links-paint).
  // 자리 = HD.popSide.beside(태그 옆 → 판 칸 → 창 전체). 트리거 하나뿐인 태그는 창 없이 태그에 올리면 그 버튼 표시만 진하게.
  var pop = {el: null, tag: null, list: [], timer: 0, lit: null};
  function popEl() {
    if (pop.el) return pop.el;
    var d = document.createElement('div');
    d.id = 'ltpop'; d.className = 'ltpop'; d.hidden = true; d.setAttribute('role', 'tooltip');
    document.body.appendChild(d);
    d.addEventListener('mouseenter', keepPop);
    d.addEventListener('mouseleave', function () { lite(null); laterClose(); });
    d.addEventListener('mouseover', function (e) {
      var r = e.target.closest ? e.target.closest('[data-i]') : null;
      lite(r ? pop.list[+r.getAttribute('data-i')] || null : null);
      $$('[data-i]', d).forEach(function (x) { x.classList.toggle('on', x === r); });
    });
    pop.el = d;
    return d;
  }
  function triggersOf(n) {                           // 고른 화면이면 화면 안 링크(경로 있음 — 표시를 진하게 할 수 있다), 아니면 판 데이터의 버튼 글
    var l = n._hd, live = ctx.triggers ? ctx.triggers(l.from, l.to) : null;
    if (live && live.length) return live.map(function (t) { return {text: t.text, path: t.path || null}; });
    return (l.texts || []).map(function (t) { return {text: t, path: null}; });
  }
  function lite(t) {                                 // 화면 안 그 버튼 표시 진하게(t = 트리거 | null)
    var key = t && t.path && pop.from ? pop.from + '|' + pop.to + '|' + t.path : null;
    if (key === pop.lit) return;
    if (pop.lit && ctx.hilite) ctx.hilite(pop.lit.split('|')[0], pop.lit.split('|')[1], null);
    pop.lit = key;
    if (key && ctx.hilite) ctx.hilite(pop.from, pop.to, t.path);
  }
  function wantsPop(n) { return !!n && !!n._hd && !n.classList.contains('editing') && (+n.getAttribute('data-more') > 0 || n.classList.contains('named')); }
  function openPop(n) {
    keepPop();
    if (pop.tag === n && pop.el && !pop.el.hidden) return;
    closePop();
    var l = n._hd, d = popEl(), list = triggersOf(n), name = ctx.title ? ctx.title(l.to) : l.to;
    pop.tag = n; pop.from = l.from; pop.to = l.to; pop.list = list;
    d.style.setProperty('--lc', l.color);
    d.innerHTML = '<div class="lt-h"><span class="lt-n">' + esc(ctx.circled(l.k)) + '</span>' + esc(name || '') + '<span class="lt-c">버튼 ' + list.length + '개</span></div>' +
      list.map(function (t, i) { return '<div class="lt-i" data-i="' + i + '">' + (t.text ? esc(t.text) : '<i>(글 없는 버튼)</i>') + '</div>'; }).join('');
    d.hidden = false;
    placePop();
  }
  function placePop() {
    var d = pop.el, n = pop.tag;
    if (!d || !n) return;
    if (!n.isConnected || getComputedStyle(n).display === 'none') { closePop(); return; }
    var r = n.getBoundingClientRect(), pane = $('#screens'), pr = pane ? pane.getBoundingClientRect() : null;
    var areas = (pr ? [{x: pr.left, y: pr.top, w: pr.width, h: pr.height}] : []).concat([{x: 0, y: 0, w: innerWidth, h: innerHeight}]);
    var at = HD.popSide.beside({x: r.left, y: r.top, w: r.width, h: r.height}, {w: d.offsetWidth, h: d.offsetHeight}, areas, 6);
    d.style.left = at.x + 'px'; d.style.top = at.y + 'px';
  }
  function keepPop() { clearTimeout(pop.timer); pop.timer = 0; }
  function laterClose() { keepPop(); pop.timer = setTimeout(closePop, 220); }
  function closePop() {
    keepPop(); lite(null);
    if (pop.el) pop.el.hidden = true;
    pop.tag = null; pop.from = pop.to = null; pop.list = [];
  }
  function tagOfLine(pth, e) {                       // 선에 올림 → 그 선의 보이는 태그(양방향이면 마우스에 가까운 쪽)
    var f = pth.getAttribute('data-from'), t = pth.getAttribute('data-to'), best = null, bd = Infinity;
    lbEls.forEach(function (n) {
      var a = n.getAttribute('data-from'), b = n.getAttribute('data-to');
      if (!((a === f && b === t) || (a === t && b === f)) || getComputedStyle(n).display === 'none') return;
      var r = n.getBoundingClientRect(), dd = Math.hypot(r.left + r.width / 2 - e.clientX, r.top + r.height / 2 - e.clientY);
      if (dd < bd) { bd = dd; best = n; }
    });
    return best;
  }
  rowsEl.addEventListener('mouseover', function (e) {
    var n = e.target.closest ? e.target.closest('.alabel') : null, pth = !n && e.target.closest ? e.target.closest('path.ln:not(.plan)') : null;
    if (pth) n = tagOfLine(pth, e);
    if (!n || !n._hd) return;
    if (wantsPop(n)) { openPop(n); return; }
    var one = triggersOf(n);                         // 트리거 하나: 창 없이 그 버튼 표시만
    pop.from = n._hd.from; pop.to = n._hd.to;
    if (one.length === 1) lite(one[0]);
  });
  rowsEl.addEventListener('mouseout', function (e) {
    var from = e.target.closest ? e.target.closest('.alabel, path.ln') : null;
    if (!from) return;
    var to = e.relatedTarget && e.relatedTarget.closest ? e.relatedTarget.closest('.alabel, path.ln, #ltpop') : null;
    if (to) return;
    if (pop.tag) laterClose(); else { lite(null); pop.from = pop.to = null; }
  });
  addEventListener('keydown', function (e) { if (e.key === 'Escape' && pop.tag) closePop(); });
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
  // 올린 카드가 마우스 밑에서 없어지면(빈 카드 되돌리기 등) mouseleave 가 오지 않는다 — 판 밖에 올라서면 강조를 끈다
  document.addEventListener('mouseover', function (e) { if (hov && !rowsEl.contains(e.target)) { hov = null; mark(); } });

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
  var show = $('#lnShow'), op = $('#lnOp'), wEl = $('#lgW'), wv = $('#lgWv'), tagsEl = $('#lnTags');
  function apply() {
    rowsEl.classList.toggle('nolines', !prefs.lines);
    rowsEl.classList.toggle('notags', !prefs.tags);   // 선 태그 끄기 — 선은 그대로, 태그만 숨김
    if (tagsEl) { var tt = prefs.tags ? '선 태그(버튼 이름) 숨기기' : '선 태그(버튼 이름) 보이기'; tagsEl.setAttribute('aria-pressed', String(prefs.tags)); tagsEl.title = tt; tagsEl.setAttribute('aria-label', tt); }
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
  if (tagsEl) tagsEl.addEventListener('click', function () {
    var a = prefs.tags, b = !a;
    set({tags: b}); if (!b) closePop();
    if (ctx.record) ctx.record({label: b ? '선 태그 보이기' : '선 태그 숨기기', undo: function () { set({tags: a}); }, redo: function () { set({tags: b}); }});
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
