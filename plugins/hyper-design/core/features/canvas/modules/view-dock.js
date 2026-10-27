/* View — 패널 도크(포토샵 오른쪽 창처럼 · S3 부터 왼쪽 도크도). 배치 상태는 modules/dock.js(리듀서)가 갖고, 여기는 그리기와 끌기만.
   HD.viewDock.mount(ctx) → {state, dispatch, width, lwidth, render, activate, isShown}
   ctx = {$, $$, root: #dock(오른쪽 도크 자리), lroot: #ldock(왼쪽 도크 자리 — 없으면 왼쪽 묶음은 그리지 않고 [hd] 경고), layer: 떠 있는 창을 놓을 판 위 층, panels: {id: 패널 요소}, icons: {id: svg},
          hold: 안 보이는 패널 보관함(#dkhold), narrow: 좁은 화면이면 접힌 채로 시작,
          absent: 이 페이지에 없는 패널 id 들(S3: 도우미 없이 연 캔버스의 대화 — 그리지 않을 뿐 저장된 배치는 그대로, 끌기 번호는 저장 배치로 옮겨 보낸다),
          hidden?() → 지금 그리지 않을 패널 id 들(absent 와 같은 뜻이지만 바뀐다 — 정렬 = 두 장 이상 골랐을 때만, R27 F02. 바뀌면 셸이 render()),
          title(id) → 탭에 붙일 수(숫자) · 이름, getItem/setItem(저장소), onLayout(state)(배치가 바뀐 뒤 — 판 너비 다시 재기 등)}
   패널 요소는 옮겨 붙이기만 한다(id·이벤트 그대로 — 기존 기능이 그대로 동작). 안 보이는 패널은 숨김 보관함(ctx.hold)으로.
   왼쪽 도크(S3): 같은 묶음·탭 규칙, 너비 끌기 = 오른쪽 가장자리, 접기·닫은 패널 단추는 오른쪽 도크에만. 비어 있으면 자리를 차지하지 않고,
   탭을 끄는 동안(body.dk-dragging)만 왼쪽 끝에 놓을 자리(#ldock.empty)가 보인다 — 오른쪽으로 옮긴 대화를 다시 왼쪽으로. */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var K = HD.dock, $ = ctx.$, root = ctx.root, lroot = ctx.lroot || null, layer = ctx.layer, hold = ctx.hold;
  if (!lroot) console.warn('[hd] 도크: 왼쪽 도크 자리(#ldock)가 없어요 — 왼쪽 묶음은 보이지 않아요');
  var st = K.load(ctx.getItem);
  if (ctx.narrow) st = K.reduce(st, {type: 'collapse', on: true});          // 좁은 화면은 접힌 채로 시작(저장하지 않음)
  var drag = null, menu = null;
  var absent = (ctx.absent || []).filter(function (p) { return K.PANELS.indexOf(p) >= 0; });
  // 보이는 배치(view) = 저장 배치에서 없는 패널을 뺀 것 + 보이는 번호 → 저장 번호(끌기·크기 의도를 저장 배치로 옮길 때)
  function gone() {                                  // 지금 그리지 않을 패널 = 이 페이지에 없는 것 + 지금 숨길 것(ctx.hidden — 정렬은 두 장 이상 골랐을 때만, R27 F02)
    var h = ctx.hidden ? ctx.hidden() || [] : [];
    return h.length ? absent.concat(h.filter(function (p) { return K.PANELS.indexOf(p) >= 0 && absent.indexOf(p) < 0; })) : absent;
  }
  function view() {
    var skip = gone();
    if (!skip.length) return {s: st, g: null, l: null, f: null};
    var strip = function (list) {
      var out = [], map = [];
      list.forEach(function (g, i) {
        var tabs = g.tabs.filter(function (q) { return skip.indexOf(q) < 0; }); if (!tabs.length) return;
        var b = {tabs: tabs, active: tabs.indexOf(g.active) >= 0 ? g.active : tabs[0], h: g.h};
        if (g.x != null) { b.x = g.x; b.y = g.y; b.w = g.w; b.h = g.h; }
        out.push(b); map.push(i);
      });
      return {out: out, map: map};
    };
    var gr = strip(st.groups), le = strip(st.left || []), fl = strip(st.floats);
    var v = {}; Object.keys(st).forEach(function (k) { v[k] = st[k]; });
    v.groups = gr.out; v.left = le.out; v.floats = fl.out;
    return {s: v, g: gr.map, l: le.map, f: fl.map};
  }
  function toSaved(a) {                              // 보이는 번호 → 저장 번호(없는 패널이 없으면 그대로)
    var V = view(); if (!V.g || !a) return a;
    var m = a.side === 'left' ? V.l : V.g, list = a.side === 'left' ? st.left : st.groups;
    if (a.type === 'move' && typeof a.to === 'number') a.to = m[a.to] == null ? -1 : m[a.to];
    if (a.type === 'move' && a.to === 'new' && a.at != null) a.at = m[a.at] == null ? list.length : m[a.at];
    if ((a.type === 'move' && a.fi != null) || a.type === 'float') a.fi = V.f[a.fi] == null ? -1 : V.f[a.fi];
    return a;
  }

  function save() { K.save(st, ctx.setItem); }
  function dispatch(a, quiet) {
    var n = K.reduce(st, a); if (n === st) return st;
    st = n; render(); if (!quiet) save();
    return st;
  }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  var ICON = {plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
              fold: '<svg viewBox="0 0 24 24"><path d="M7 6l6 6-6 6M13 6l6 6-6 6"/></svg>',
              unfold: '<svg viewBox="0 0 24 24"><path d="M17 6l-6 6 6 6M11 6l-6 6 6 6"/></svg>'};
  function tabHtml(id, on) {
    var t = ctx.title ? ctx.title(id) : {}, lab = K.LABEL[id];
    return '<button type="button" class="dk-tab' + (on ? ' on' : '') + '" role="tab" aria-selected="' + on + '" data-p="' + id + '" title="' + esc(lab) + '">' +
      (ctx.icons[id] || '') + '<span class="dk-tl">' + esc(lab) + '</span>' + (t.count ? '<span class="dk-cnt">' + t.count + '</span>' : '') +
      '<span class="dk-x" role="button" aria-label="' + esc(lab) + ' 닫기">×</span></button>';
  }
  function tabsHtml(box, extra) {
    return '<div class="dk-tabs" role="tablist">' + box.tabs.map(function (id) { return tabHtml(id, id === box.active); }).join('') +
      '<span class="dk-grip"></span>' + (extra || '') + '</div><div class="dk-body"></div>';
  }
  function place(boxEl, box) {                       // 활성 패널을 그 묶음 몸통에
    var body = boxEl.querySelector('.dk-body'), p = ctx.panels[box.active];
    if (p) body.appendChild(p);
  }
  // 배치 모양(묶음·탭 차례·떠 있는 창·접힘)이 그대로면 다시 만들지 않고 고른 탭·패널·탭 숫자만 고친다(P4)
  var built = null;
  function shape(v) {
    return JSON.stringify([v.collapsed, v.closed.length > 0, v.groups.map(function (g) { return [g.tabs, g.h]; }), (v.left || []).map(function (g) { return [g.tabs, g.h]; }),
                           v.floats.map(function (f) { return [f.tabs, f.x, f.y, f.w, f.h]; })]);
  }
  function setCount(b, id) {
    var t = ctx.title ? ctx.title(id) : {}, c = b.querySelector('.dk-cnt');
    if (!t.count) { if (c) c.remove(); return; }
    if (!c) { c = document.createElement('span'); c.className = 'dk-cnt'; b.insertBefore(c, b.querySelector('.dk-x')); }
    if (c.textContent !== String(t.count)) c.textContent = t.count;
  }
  function sync(boxEl, box) {
    if (!boxEl || !box) return;
    boxEl.querySelectorAll('.dk-tab').forEach(function (t) {
      var on = t.dataset.p === box.active;
      if (t.classList.contains('on') !== on) { t.classList.toggle('on', on); t.setAttribute('aria-selected', String(on)); }
    });
    var body = boxEl.querySelector('.dk-body'), p = ctx.panels[box.active];
    if (body.firstChild === p && body.childNodes.length === 1) return;
    while (body.firstChild) hold.appendChild(body.firstChild);
    if (p) body.appendChild(p);
  }
  function refresh() {
    var st = view().s;
    if (!st.collapsed && st.groups.length) {
      root.style.width = st.w + 'px';
      st.groups.forEach(function (g, i) { sync(root.querySelector('.dk-g[data-g="' + i + '"]'), g); });
    }
    if (lroot && st.left.length) {
      lroot.style.width = st.lw + 'px';
      st.left.forEach(function (g, i) { sync(lroot.querySelector('.dk-g[data-g="' + i + '"]'), g); });
      lroot.querySelectorAll('.dk-tab').forEach(function (b) { setCount(b, b.dataset.p); });
    }
    st.floats.forEach(function (f, i) { sync(layer.querySelector('.dk-f[data-f="' + i + '"]'), f); });
    root.querySelectorAll('.dk-tab, .dk-sb').forEach(function (b) { setCount(b, b.dataset.p); });
    layer.querySelectorAll('.dk-f .dk-tab').forEach(function (b) { setCount(b, b.dataset.p); });
    if (ctx.onLayout) ctx.onLayout(st);
  }
  function render() {
    var st = view().s, sh = shape(st);
    if (sh === built) { refresh(); return; }
    built = sh;
    Object.keys(ctx.panels).forEach(function (id) { hold.appendChild(ctx.panels[id]); });
    var ctl = '<button type="button" class="dk-ib dk-more" title="닫은 패널 다시 열기"' + (st.closed.length ? '' : ' disabled') + '>' + ICON.plus + '</button>' +
              '<button type="button" class="dk-ib dk-fold" title="패널 접기">' + ICON.fold + '</button>';
    root.classList.toggle('folded', st.collapsed);
    root.classList.toggle('empty', !st.groups.length);
    if (st.collapsed || !st.groups.length) {
      var ids = []; st.groups.forEach(function (g) { ids = ids.concat(g.tabs); });
      root.innerHTML = '<button type="button" class="dk-ib dk-unfold" title="패널 펴기">' + ICON.unfold + '</button>' +
        (st.groups.length ? '' : '<button type="button" class="dk-ib dk-more" title="닫은 패널 다시 열기">' + ICON.plus + '</button>') +
        ids.map(function (id) { var t = ctx.title ? ctx.title(id) : {};
          return '<button type="button" class="dk-sb" data-p="' + id + '" title="' + esc(K.LABEL[id]) + '">' + (ctx.icons[id] || '') + (t.count ? '<span class="dk-cnt">' + t.count + '</span>' : '') + '</button>'; }).join('');
      root.style.width = '';
    } else {
      root.style.width = st.w + 'px';
      root.innerHTML = '<div class="dk-edge" title="끌어서 너비 조절"></div>' + st.groups.map(function (g, i) {
        return (i ? '<div class="dk-split" data-i="' + (i - 1) + '"></div>' : '') +
          '<section class="dk-g" data-g="' + i + '" style="flex:' + g.h + ' 1 0">' + tabsHtml(g, i === 0 ? ctl : '') + '</section>';
      }).join('');
      st.groups.forEach(function (g, i) { place(root.querySelector('.dk-g[data-g="' + i + '"]'), g); });
    }
    if (lroot) {                                     // 왼쪽 도크(S3) — 오른쪽과 같은 묶음 모양, 너비 손잡이는 오른쪽 가장자리
      lroot.classList.toggle('empty', !st.left.length);
      if (st.left.length) {
        lroot.style.width = st.lw + 'px';
        lroot.innerHTML = '<div class="dk-edge" title="끌어서 너비 조절"></div>' + st.left.map(function (g, i) {
          return (i ? '<div class="dk-split" data-i="' + (i - 1) + '"></div>' : '') +
            '<section class="dk-g" data-g="' + i + '" style="flex:' + g.h + ' 1 0">' + tabsHtml(g) + '</section>';
        }).join('');
        st.left.forEach(function (g, i) { place(lroot.querySelector('.dk-g[data-g="' + i + '"]'), g); });
      } else { lroot.innerHTML = ''; lroot.style.width = ''; }
    }
    layer.querySelectorAll('.dk-f').forEach(function (n) { n.remove(); });
    st.floats.forEach(function (f, i) {
      var el = document.createElement('section');
      el.className = 'dk dk-f'; el.dataset.f = i;
      el.style.cssText = 'left:' + f.x + 'px;top:' + f.y + 'px;width:' + f.w + 'px;height:' + f.h + 'px';
      el.innerHTML = tabsHtml(f) + '<span class="dk-rs" title="끌어서 크기 조절"></span>';
      layer.appendChild(el); place(el, f);
    });
    if (ctx.onLayout) ctx.onLayout(st);
  }
  function width() { var v = view().s; return v.collapsed || !v.groups.length ? 44 : v.w; }
  function lwidth() { return lroot ? K.leftWidth(view().s) : 0; }

  /* ---------- 닫은 패널 메뉴 ---------- */
  function closeMenu() { if (menu) { menu.remove(); menu = null; } }
  function openMenu(btn) {
    closeMenu(); if (!st.closed.length) return;
    menu = document.createElement('div'); menu.className = 'cm dk-menu'; menu.setAttribute('role', 'menu');
    menu.innerHTML = st.closed.map(function (id) { return '<button type="button" data-p="' + id + '">' + (ctx.icons[id] || '') + esc(K.LABEL[id]) + '</button>'; }).join('');
    document.body.appendChild(menu);
    var r = btn.getBoundingClientRect();
    menu.style.left = Math.max(8, r.right - menu.offsetWidth) + 'px'; menu.style.top = (r.bottom + 4) + 'px';
  }
  document.addEventListener('pointerdown', function (e) { if (menu && !menu.contains(e.target) && !e.target.closest('.dk-more')) closeMenu(); }, true);
  document.addEventListener('click', function (e) {
    if (!menu || !menu.contains(e.target)) return;
    var b = e.target.closest('button[data-p]'); if (b) { closeMenu(); dispatch({type: 'activate', id: b.dataset.p}); }
  });

  /* ---------- 누르기 ---------- */
  function onClick(e) {
    var t = e.target;
    if (t.closest('.dk-x')) { dispatch({type: 'close', id: t.closest('.dk-tab').dataset.p}); return; }
    if (t.closest('.dk-more')) { if (menu) closeMenu(); else openMenu(t.closest('.dk-more')); return; }
    if (t.closest('.dk-fold')) { dispatch({type: 'collapse', on: true}); return; }
    if (t.closest('.dk-unfold')) { dispatch({type: 'collapse', on: false}); return; }
    var sb = t.closest('.dk-sb'); if (sb) { dispatch({type: 'activate', id: sb.dataset.p}); return; }
  }
  root.addEventListener('click', onClick);
  if (lroot) lroot.addEventListener('click', onClick);
  layer.addEventListener('click', function (e) { if (e.target.closest('.dk-f')) onClick(e); });

  /* ---------- 끌기: 탭(합치기·떼기·띄우기) · 떠 있는 창 옮기기·크기 · 너비 · 묶음 높이 ---------- */
  function rel(e) { var r = layer.getBoundingClientRect(); return {x: e.clientX - r.left, y: e.clientY - r.top}; }
  function dropAt(e) {                                // 놓을 자리 → 의도
    var el = document.elementFromPoint(e.clientX, e.clientY), tabs = el && el.closest('.dk-tabs');
    var box = tabs && tabs.parentElement, left = !!(lroot && el && lroot.contains(el));
    if (box && box.classList.contains('dk-g')) {
      var tbs = Array.prototype.slice.call(tabs.querySelectorAll('.dk-tab')), at = tbs.length;
      for (var i = 0; i < tbs.length; i++) { var r = tbs[i].getBoundingClientRect(); if (e.clientX < r.left + r.width / 2) { at = i; break; } }
      return left ? {type: 'move', side: 'left', to: +box.dataset.g, at: at, el: tabs} : {type: 'move', to: +box.dataset.g, at: at, el: tabs};
    }
    if (box && box.classList.contains('dk-f')) return {type: 'move', to: 'float', fi: +box.dataset.f, el: tabs};
    if (el && (el.closest('#dock') || left)) {
      var host = left ? lroot : root, gs = host.querySelectorAll('.dk-g'), k = gs.length;
      for (var j = 0; j < gs.length; j++) { var q = gs[j].getBoundingClientRect(); if (e.clientY < q.top + q.height / 2) { k = j; break; } }
      return left ? {type: 'move', side: 'left', to: 'new', at: k, el: lroot} : {type: 'move', to: 'new', at: k, el: root};
    }
    var p = rel(e);
    return {type: 'move', to: 'float', x: p.x - 40, y: p.y - 14, el: null};
  }
  function mark(t) {
    document.querySelectorAll('.dk-drop').forEach(function (n) { n.classList.remove('dk-drop'); });
    if (t && t.el) t.el.classList.add('dk-drop');
  }
  function start(e) {
    if (e.button !== 0) return;
    var t = e.target, tab = t.closest('.dk-tab'), f = t.closest('.dk-f');
    if (t.closest('.dk-x') || t.closest('.dk-ib')) return;
    var z = {x0: e.clientX, y0: e.clientY, moved: false, side: lroot && lroot.contains(t) ? 'left' : null};
    if (tab) { z.kind = 'tab'; z.id = tab.dataset.p; }
    else if (t.closest('.dk-rs')) { z.kind = 'resize'; z.fi = +f.dataset.f; z.f = view().s.floats[z.fi]; }
    else if (f && t.closest('.dk-grip')) { z.kind = 'fmove'; z.fi = +f.dataset.f; z.f = view().s.floats[z.fi]; }
    else if (t.closest('.dk-edge')) { z.kind = 'width'; z.w = z.side ? st.lw : st.w; }
    else if (t.closest('.dk-split')) {
      z.kind = 'split'; z.i = +t.closest('.dk-split').dataset.i;
      z.hs = Array.prototype.map.call((z.side ? lroot : root).querySelectorAll('.dk-g'), function (g) { return g.offsetHeight; });
    } else return;
    e.preventDefault(); drag = z;
    (t.closest('.dk-edge, .dk-split') || document.body).classList.add('dk-act');
  }
  function move(e) {
    var z = drag; if (!z) return;
    var dx = e.clientX - z.x0, dy = e.clientY - z.y0;
    if (!z.moved && Math.abs(dx) + Math.abs(dy) < 5) return;
    z.moved = true;
    if (z.kind === 'tab') {
      if (!z.ghost) { z.ghost = document.createElement('div'); z.ghost.className = 'dk-ghost'; z.ghost.innerHTML = (ctx.icons[z.id] || '') + esc(K.LABEL[z.id]); document.body.appendChild(z.ghost); document.body.classList.add('dk-dragging'); }
      z.ghost.style.left = (e.clientX + 10) + 'px'; z.ghost.style.top = (e.clientY + 6) + 'px';
      z.ghost.style.display = 'none'; z.drop = dropAt(e); z.ghost.style.display = ''; mark(z.drop);
    } else if (z.kind === 'width') {                 // 한 프레임에 한 번만 너비를 바꾼다(판 너비 다시 재기가 비싸다, P4)
      z.pw = z.side ? z.w + dx : z.w - dx; if (!z.raf) z.raf = requestAnimationFrame(function () { z.raf = 0; widthNow(z); });
    } else if (z.kind === 'split') {
      var hs = z.hs.slice(), a = Math.max(80, Math.min(hs[z.i] + hs[z.i + 1] - 80, hs[z.i] + dy));
      hs[z.i + 1] = hs[z.i] + hs[z.i + 1] - a; hs[z.i] = a;
      st = K.reduce(st, {type: 'heights', hs: hs, side: z.side || undefined});   // 없는 패널로 묶음 수가 다르면 그대로(리듀서가 거른다)
      var gl = z.side ? view().s.left : view().s.groups;
      Array.prototype.forEach.call((z.side ? lroot : root).querySelectorAll('.dk-g'), function (g, k) { g.style.flex = gl[k].h + ' 1 0'; });
    } else if (z.kind === 'fmove' || z.kind === 'resize') {
      var a2 = z.kind === 'fmove' ? {type: 'float', fi: z.fi, x: z.f.x + dx, y: z.f.y + dy} : {type: 'float', fi: z.fi, w: z.f.w + dx, h: z.f.h + dy};
      st = K.reduce(st, toSaved(a2));
      var el = layer.querySelector('.dk-f[data-f="' + z.fi + '"]'), b = view().s.floats[z.fi];
      if (el) el.style.cssText = 'left:' + b.x + 'px;top:' + b.y + 'px;width:' + b.w + 'px;height:' + b.h + 'px';
    }
  }
  function widthNow(z) {
    var n = K.reduce(st, {type: 'width', w: z.pw, side: z.side || undefined});
    if (z.side) { if (n.lw === st.lw) return; st = n; lroot.style.width = st.lw + 'px'; }
    else { if (n.w === st.w) return; st = n; root.style.width = st.w + 'px'; }
    if (ctx.onLayout) ctx.onLayout(st);
  }
  function end(e) {
    var z = drag; if (!z) return; drag = null;
    document.querySelectorAll('.dk-act').forEach(function (n) { n.classList.remove('dk-act'); });
    if (z.ghost) z.ghost.remove(); mark(null); document.body.classList.remove('dk-dragging');
    if (z.kind === 'tab') {
      if (!z.moved) { dispatch({type: 'activate', id: z.id}); return; }
      var d = z.drop || dropAt(e); delete d.el; d.id = z.id;
      dispatch(toSaved(d)); return;
    }
    if (z.raf) { cancelAnimationFrame(z.raf); z.raf = 0; widthNow(z); }   // 놓은 자리 너비로 끝낸다
    if (z.moved) { save(); if (z.kind !== 'width') render(); }
  }
  root.addEventListener('pointerdown', start);
  if (lroot) lroot.addEventListener('pointerdown', start);
  layer.addEventListener('pointerdown', function (e) { if (e.target.closest('.dk-f')) { e.stopPropagation(); start(e); } });
  addEventListener('pointermove', move);
  addEventListener('pointerup', end);
  addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });

  render();
  return {state: function () { return st; }, dispatch: dispatch, width: width, lwidth: lwidth, render: render,
          activate: function (id) { dispatch({type: 'activate', id: id}); },
          isShown: function (id) { return K.visible(view().s).indexOf(id) >= 0; },
          absent: function () { return absent.slice(); }};
}

HD.viewDock = {mount: mount};
})();
