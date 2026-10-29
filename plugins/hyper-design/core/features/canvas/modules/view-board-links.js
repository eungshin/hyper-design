/* View — 판 메모 선(R47): 판 메모 변의 점을 끌어 메모·화면 카드·줄(폴더) 제목에 잇고, 카드 아래 옅은 선·누르는 띠·이름을 그린다. 상태 이름 board-links(hd-board-links:<hash>)의 주인.
   규칙(모양·잇기·끊기·이름·거두기·따라가기·합치기·경로)은 modules/board-links.js(Model). 메모는 DOM(#bnotes .bnote[data-id])과 ctx.boardNotes() 로 읽기만 — board-notes 를 부르지 않는다.
   층: 보이는 선 svg#blk-l(#stage 안, 카드 아래 z -1) · 누르는 띠와 이름 svg#blk-h(카드 위 z 3, 카드 상자를 뚫은 clip — 카드 누르기는 그대로 카드로) · 점 #blk-dots(z 5, 메모 위).
   잇기: 선택(V)에서 메모에 올리거나 고르면 네 변 가운데 점 → 점을 끌어 메모·화면 카드·줄 제목(.glabel)에 놓기 = 선 하나 + 기록 한 줄('판 메모 선 잇기'). 같은 쌍·자기 자신은 잇지 않음(같은 쌍 = 토스트).
   선 누르기 = 고르기 · Delete·Backspace = 끊기(기록 한 줄) · 두 번 누르기·Enter = 이름(40자, 기록 한 줄) · Esc·다른 곳 누르기 = 풀기. 읽기만인 탭(html[data-hd-tab=reader])은 고르기만.
   메모를 지우면(셸이 메모 바뀜을 notesChanged() 로 알림) 그 메모에 닿은 선을 거두고(기록 없이 — 메모 지우기 줄의 차이에 함께 든다), 같은 메모가 되돌아오면 거둔 선도 되돌린다.
   줄 이름 바꾸기(document 'hd-rows-changed' {renamed: {from, to}} — view-rows) = folder:<옛 이름> 끝을 새 이름으로(retarget, 기록 없이 — 그 줄의 되돌리기가 다시 바꿔 따라온다).
   화면 id 가 바뀌는 신호는 아직 없다 — 그런 화면 끝은 저장에 남고 그리지 않는다.
   쉬는 동안 하는 일 없음: 선이 없으면 그리지 않는다. 메모·카드 자리·배율이 바뀌면(MutationObserver) 한 프레임에 한 번 다시.
   등록부 기능 'boardLinks'(needs $ · $$ · store · key · record · toast · warn · view · rowsEl · boardNotes) → {attach(A), reload(), map(), notesChanged(), selected(), schedule()}
     A(셸이 attach 로 건넴) = {tool() → 지금 도구, changed()?(선 map 이 바뀜 — 레이어 배지)}. 셸은 adoptState 의 'board-links' 에서 reload(), 메모 바뀜(BN changed)에서 notesChanged() 를 부른다. ctx.boardLinks() = map() */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var SVGNS = 'http://www.w3.org/2000/svg', MIN_PX = 18;   // 메모가 화면에서 이보다 작으면(높이 px, 폭은 두 배) 변의 점을 숨긴다
var CSS = '#blk-l,#blk-h{position:absolute;left:0;top:0;overflow:visible;pointer-events:none}' +
  '#blk-l{z-index:-1}#blk-h{z-index:3}#blk-dots{position:absolute;left:0;top:0;width:0;height:0;z-index:5}' +
  '#blk-l path.blk{fill:none;stroke:#B4B8B1;stroke-width:calc(1.5px * var(--blk,1));stroke-linecap:round;marker-end:url(#blk-head)}' +
  '#blk-l path.blk.sel{stroke:#6b7a8f;stroke-width:calc(2px * var(--blk,1))}#blk-l marker path{fill:context-stroke}#blk-l path.blk-tmp{stroke-dasharray:calc(5px * var(--blk,1))}' +
  '#blk-h path.blk-hit{fill:none;stroke:transparent;stroke-width:calc(14px * var(--blk,1));pointer-events:stroke;cursor:pointer}' +
  '#blk-h text.blk-lab{font:500 calc(12px * var(--blk,1)) system-ui,sans-serif;fill:#7d827a;text-anchor:middle;dominant-baseline:middle;paint-order:stroke;stroke:#f4f4f2;stroke-width:calc(4px * var(--blk,1));pointer-events:all;cursor:pointer}' +
  '#blk-h .sel text.blk-lab{fill:#4d5868}' +
  '.blk-dot{position:absolute;width:calc(10px * var(--blk,1));height:calc(10px * var(--blk,1));margin:calc(-5px * var(--blk,1)) 0 0 calc(-5px * var(--blk,1));box-sizing:border-box;border-radius:50%;' +
  'background:#fff;border:calc(1.5px * var(--blk,1)) solid #9aa3ad;cursor:crosshair;touch-action:none}.blk-dot:hover{background:#6b7a8f;border-color:#6b7a8f}' +
  '.blk-target{outline:2px solid #9aa3ad!important;outline-offset:4px}' +
  '.blk-in{position:absolute;transform:translate(-50%,-50%);width:calc(160px * var(--blk,1));font:calc(13px * var(--blk,1)) system-ui,sans-serif;padding:calc(2px * var(--blk,1)) calc(6px * var(--blk,1));' +
  'border:1px solid #9aa3ad;border-radius:4px;background:#fff;color:#2b2b29;outline:none}' +
  '#rows.focusing~#blk-l,#rows.focusing~#blk-h{opacity:.2}html[data-hd-tab=reader] #blk-dots{display:none}';

function mount(ctx) {
  var M = HD.boardLinks, KEY = ctx.key('hd-' + M.NAME), pane = ctx.view.pane, stage = ctx.$('#stage'), rowsEl = ctx.rowsEl, $$ = ctx.$$;
  var A = null, map = {}, sel = null, link = null, raf = 0, dotsOf = null, target = null, grave = {}, known = null, naming = null;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  function svgLayer(id) { var s = document.createElementNS(SVGNS, 'svg'); s.id = id; s.setAttribute('width', '1'); s.setAttribute('height', '1'); return s; }
  var svgL = svgLayer('blk-l'), svgH = svgLayer('blk-h'), dots = document.createElement('div'); dots.id = 'blk-dots';
  svgL.innerHTML = '<defs><marker id="blk-head" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>' +
                   '<g class="blk-all"></g><path class="blk blk-tmp" style="display:none"/>';
  svgH.innerHTML = '<defs><clipPath id="blk-clip" clipPathUnits="userSpaceOnUse"><path clip-rule="evenodd"/></clipPath></defs><g class="blk-hall" clip-path="url(#blk-clip)"></g>';
  M.SIDES.forEach(function (s) { var d = document.createElement('i'); d.className = 'blk-dot'; d.dataset.side = s; d.title = '끌어서 메모·화면·폴더에 잇기'; d.hidden = true; dots.appendChild(d); });
  stage.appendChild(svgL); stage.appendChild(svgH); stage.appendChild(dots);
  var all = svgL.querySelector('g.blk-all'), tmp = svgL.querySelector('path.blk-tmp'), hall = svgH.querySelector('g.blk-hall'), clip = svgH.querySelector('#blk-clip path');

  function reader() { return document.documentElement.dataset.hdTab === 'reader'; }
  function iso() { return new Date().toISOString(); }
  function z() { return ctx.view.get().z || 1; }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]; }); }
  function scale() { stage.style.setProperty('--blk', (1 / z()).toFixed(4)); }

  // ------------------------------------------------ 저장
  function load() {
    var t = null;
    try { t = ctx.store.getItem(KEY); } catch (e) { t = null; }   // 저장소를 못 읽으면 선 없음(쓰기 실패는 state-sync 가 알린다)
    var p = M.parse(t);
    if (p.bad === 'broken') ctx.warn('[hd] 판 메모 선 저장값이 깨져 선 없이 엽니다');
    else if (p.bad === 'dropped') ctx.warn('[hd] 판 메모 선 중 모양이 틀린 것을 뺐습니다');
    map = p.map;
    if (sel && !map[sel]) sel = null;
  }
  function write() {
    try { ctx.store.setItem(KEY, JSON.stringify(map)); }
    catch (e) { ctx.toast('판 메모 선을 저장하지 못했어요'); ctx.warn('[hd] 판 메모 선 저장 실패: ' + (e && e.message || e)); }
  }
  function tell() { if (A && A.changed) A.changed(); }   // 선이 바뀜(셸 = 레이어 '카드 N' 배지 다시)
  function put(m) { map = m; if (sel && !map[sel]) sel = null; write(); schedule(); tell(); }
  function commit(after, before, label) { put(after); ctx.record({label: label, undo: function () { put(before); }, redo: function () { put(after); }}); }

  // ------------------------------------------------ 자리(판 좌표)
  function boxOf(el) {
    var r = el.getBoundingClientRect(), s = stage.getBoundingClientRect(), k = z();
    return r.width || r.height ? {x: (r.left - s.left) / k, y: (r.top - s.top) / k, w: r.width / k, h: r.height / k} : null;
  }
  function noteEl(id) { return $$('#bnotes .bnote').filter(function (n) { return n.dataset.id === id; })[0] || null; }
  function cardEl(id) { return $$('.card', rowsEl).filter(function (c) { return c.dataset.id === id && !c.classList.contains('del'); })[0] || null; }
  function folderEl(name) { return $$('#rows > .flow > .glabel').filter(function (g) { return g.textContent === name; })[0] || null; }
  function endEl(s) {
    var e = M.end(s); if (!e) return null;
    if (e.kind === 'note') return noteEl(e.id);
    if (e.kind === 'screen') { var c = cardEl(e.id); return c ? (c.querySelector('.phone') || c) : null; }
    return folderEl(e.id);
  }
  function endBox(s) { var el = endEl(s); return el ? boxOf(el) : null; }
  function endAt(el) {                                   // 놓은 자리 요소 → 끝 글 | null
    if (!el || !el.closest) return null;
    var n = el.closest('#bnotes .bnote'); if (n) return 'note:' + n.dataset.id;
    var g = el.closest('.glabel'); if (g && g.parentNode && g.parentNode.parentNode === rowsEl) return 'folder:' + g.textContent;
    var c = el.closest('.card'); if (c && rowsEl.contains(c) && c.dataset.id && !c.classList.contains('del')) return 'screen:' + c.dataset.id;
    return null;
  }

  // ------------------------------------------------ 그리기
  function render() {
    raf = 0; scale();
    var boxes = {}, box = function (s) { if (!(s in boxes)) boxes[s] = endBox(s); return boxes[s]; };
    var lines = Object.keys(map).length ? M.live(map, function (s) { return !!box(s); }) : [];
    if (!lines.length) { all.innerHTML = ''; hall.innerHTML = ''; }
    else {
      var holes = 'M-1000000,-1000000 H1000000 V1000000 H-1000000 Z';
      $$('.card', rowsEl).forEach(function (c) { var b = boxOf(c); if (b) holes += ' M' + b.x.toFixed(1) + ',' + b.y.toFixed(1) + ' h' + b.w.toFixed(1) + ' v' + b.h.toFixed(1) + ' h' + (-b.w).toFixed(1) + ' Z'; });
      clip.setAttribute('d', holes);
      var h = '', hh = '';
      lines.forEach(function (l) {
        var a = box(l.from), b = box(l.to), fs = l.fromSide || M.nearSide(a, {x: b.x + b.w / 2, y: b.y + b.h / 2});
        var p = M.anchor(a, fs), ts = l.toSide || M.nearSide(b, p), q = M.anchor(b, ts), d = M.path(p, fs, q, ts), on = l.id === sel ? ' sel' : '', id = esc(l.id);
        h += '<path class="blk' + on + '" data-id="' + id + '" d="' + d + '"/>';
        var mp = M.mid(p, fs, q, ts);
        hh += '<g class="blk-e' + on + '" data-id="' + id + '"><path class="blk-hit" d="' + d + '"/>' +
              (l.label ? '<text class="blk-lab" x="' + mp.x + '" y="' + mp.y + '">' + esc(l.label) + '</text>' : '') + '</g>';
      });
      all.innerHTML = h; hall.innerHTML = hh;
    }
    paintDots();
  }
  function schedule() { if (!raf) raf = requestAnimationFrame(render); }

  // ------------------------------------------------ 변의 점(고르거나 올린 메모 하나)
  function dotEls() { return Array.prototype.slice.call(dots.querySelectorAll('.blk-dot')); }
  function paintDots() {
    var id = dotsOf, el = id && noteEl(id);
    if (!el || link || reader() || !A || A.tool() !== 'move' || el.classList.contains('editing')) { dotEls().forEach(function (d) { d.hidden = true; }); return; }
    var b = boxOf(el), k = z();
    if (!b || b.w * k < MIN_PX * 2 || b.h * k < MIN_PX) { dotEls().forEach(function (d) { d.hidden = true; }); return; }   // 작게 보는 중 = 점이 메모를 덮으니 안 보임(크게 보면 나온다)
    dotEls().forEach(function (d) { var p = M.anchor(b, d.dataset.side); d.style.left = p.x + 'px'; d.style.top = p.y + 'px'; d.dataset.note = id; d.hidden = false; });
  }
  function hoverDots(t) {
    if (link) return;
    if (t && t.closest && t.closest('#blk-dots')) return;           // 점 위 = 그대로
    var n = t && t.closest && t.closest('#bnotes .bnote'), s = document.querySelector('#bnotes .bnote.sel');
    var id = n ? n.dataset.id : s ? s.dataset.id : null;
    if (id !== dotsOf || id) { dotsOf = id; scale(); paintDots(); }
  }
  pane.addEventListener('pointermove', function (e) { if (!e.buttons) hoverDots(e.target); });

  function mark(el) { if (target === el) return; if (target) target.classList.remove('blk-target'); target = el; if (el) el.classList.add('blk-target'); }
  function targetEl(s) { var e = M.end(s); if (!e) return null; return e.kind === 'screen' ? cardEl(e.id) : e.kind === 'note' ? noteEl(e.id) : folderEl(e.id); }
  function under(cx, cy) { return document.elementFromPoint(cx, cy); }
  dots.addEventListener('pointerdown', function (e) {
    var d = e.target.closest('.blk-dot'); if (!d) return;
    e.stopPropagation(); e.preventDefault();
    if (e.button !== 0 || reader() || !d.dataset.note) return;
    link = {from: 'note:' + d.dataset.note, side: d.dataset.side, pid: e.pointerId, el: d};
    try { d.setPointerCapture(e.pointerId); } catch (err) {}   // 잡지 못해도 창 밖으로 나가기 전까지는 끌린다
  });
  dots.addEventListener('pointermove', function (e) {
    if (!link || e.pointerId !== link.pid) return;
    var a = endBox(link.from); if (!a) return;
    var r = stage.getBoundingClientRect(), k = z(), q = {x: (e.clientX - r.left) / k, y: (e.clientY - r.top) / k}, p = M.anchor(a, link.side);
    var to = endAt(under(e.clientX, e.clientY)), tb = to && to !== link.from ? endBox(to) : null, ts = tb ? M.nearSide(tb, p) : M.nearSide({x: q.x, y: q.y, w: 0, h: 0}, p);
    if (tb) q = M.anchor(tb, ts);
    tmp.setAttribute('d', M.path(p, link.side, q, ts)); tmp.style.display = '';
    mark(tb ? targetEl(to) : null);
  });
  function dropLink(e) {
    if (!link || e.pointerId !== link.pid) return;
    var l = link; link = null; tmp.style.display = 'none'; mark(null);
    var to = e.type === 'pointerup' ? endAt(under(e.clientX, e.clientY)) : null;
    if (to && to !== l.from) {
      var src = endBox(l.from), dst = endBox(to), before = map;
      var r = M.add(map, M.newId(Date.now()), {from: l.from, fromSide: l.side, to: to, toSide: dst && src ? M.nearSide(dst, M.anchor(src, l.side)) : undefined}, iso());
      if (r.ok) commit(r.map, before, '판 메모 선 잇기');
      else if (r.why === 'dup') ctx.toast('이미 이은 선이에요');
      else if (r.why !== 'self') ctx.warn('[hd] 판 메모 선을 잇지 못함: ' + r.why);
    }
    schedule();
  }
  dots.addEventListener('pointerup', dropLink);
  dots.addEventListener('pointercancel', dropLink);

  // ------------------------------------------------ 선 고르기 · 이름 · 끊기
  function select(id) { if (sel === id) return; sel = id; schedule(); }
  pane.addEventListener('pointerdown', function (e) { if (sel && !(e.target.closest && e.target.closest('#blk-h g.blk-e'))) select(null); }, true);
  svgH.addEventListener('pointerdown', function (e) { if (e.target.closest('g.blk-e') && e.button === 0) e.stopPropagation(); });   // 판 끌기·고르기 상자로 새지 않게
  svgH.addEventListener('click', function (e) { var g = e.target.closest('g.blk-e'); if (!g) return; e.stopPropagation(); select(g.dataset.id); });
  svgH.addEventListener('dblclick', function (e) {
    var g = e.target.closest('g.blk-e'); if (!g) return;
    e.stopPropagation(); e.preventDefault(); select(g.dataset.id); name(g.dataset.id);
  });
  function name(id) {
    if (reader() || naming || !map[id]) return;
    var l = map[id], a = endBox(l.from), b = endBox(l.to); if (!a || !b) return;
    var fs = l.fromSide || M.nearSide(a, {x: b.x + b.w / 2, y: b.y + b.h / 2}), p = M.anchor(a, fs), ts = l.toSide || M.nearSide(b, p), mp = M.mid(p, fs, M.anchor(b, ts), ts);
    var inp = document.createElement('input');
    inp.className = 'blk-in'; inp.value = l.label || ''; inp.maxLength = M.LABEL_MAX; inp.setAttribute('aria-label', '선 이름'); inp.spellcheck = false;
    inp.style.left = mp.x + 'px'; inp.style.top = mp.y + 'px';
    dots.appendChild(inp); naming = inp; scale();
    var ended = false;
    function fin(keep) {
      if (ended) return; ended = true; naming = null; inp.remove();
      if (keep && map[id]) { var before = map, after = M.rename(map, id, inp.value, iso()); if (after !== before) commit(after, before, '판 메모 선 이름'); }
    }
    inp.addEventListener('keydown', function (ev) {
      ev.stopPropagation();
      if (ev.isComposing || ev.keyCode === 229) return;  // 한글 조합 중 Enter·Esc 는 조합 끝내기
      if (ev.key === 'Enter') { ev.preventDefault(); fin(true); } else if (ev.key === 'Escape') { ev.preventDefault(); fin(false); }
    });
    inp.addEventListener('blur', function () { fin(true); });
    ['pointerdown', 'click', 'dblclick'].forEach(function (n) { inp.addEventListener(n, function (ev) { ev.stopPropagation(); }); });
    inp.focus({preventScroll: true}); inp.select();
  }
  addEventListener('keydown', function (e) {             // 고른 선 — 메모·카드 글쇠보다 먼저
    if (!sel || naming) return;
    var t = e.target, modal = document.getElementById('modal');
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
    if ((modal && !modal.hidden) || document.body.dataset.tab !== 'screens') return;
    if (!map[sel]) { select(null); return; }
    var k = e.key, plain = !e.ctrlKey && !e.metaKey && !e.altKey;
    if ((k === 'Delete' || k === 'Backspace') && plain) {
      e.preventDefault(); e.stopImmediatePropagation();
      if (reader()) { ctx.toast('읽기만인 탭이에요 — 선을 끊을 수 없어요'); return; }
      var before = map; commit(M.remove(map, sel), before, '판 메모 선 끊기');
    } else if (k === 'Enter' && plain) { e.preventDefault(); e.stopImmediatePropagation(); name(sel); }
    else if (k === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); select(null); }
  }, true);

  // ------------------------------------------------ 바뀜 따라가기
  function notesChanged() {                               // 메모가 지워지면 닿은 선을 거두고, 되돌아오면 거둔 선을 되돌린다(기록 없이)
    var list = []; try { list = (ctx.boardNotes() || []).map(function (n) { return String(n.id); }); } catch (e) { ctx.warn('[hd] 판 메모 선: 메모 목록을 읽지 못함'); return; }
    var now = {}; list.forEach(function (id) { now[id] = 1; });
    if (known) {
      var gone = Object.keys(known).filter(function (id) { return !now[id]; }), back = Object.keys(grave).filter(function (id) { return now[id]; });
      if (gone.length || back.length) {
        load();
        var m = map;
        back.forEach(function (n) {
          var ls = grave[n]; delete grave[n];
          Object.keys(ls).forEach(function (id) { if (!m[id]) { var r = M.add(m, id, ls[id], ls[id].at); if (r.ok) { m = r.map; m[id] = ls[id]; } } });
        });
        if (gone.length) { var t = M.touching(m, gone); gone.forEach(function (n) { var mine = {}; Object.keys(t).forEach(function (id) { if (t[id].from === 'note:' + n || t[id].to === 'note:' + n) mine[id] = t[id]; }); if (Object.keys(mine).length) grave[n] = mine; }); m = M.prune(m, gone); }
        if (m !== map) put(m);
      }
    }
    known = now; schedule();
  }
  document.addEventListener('hd-rows-changed', function (e) {   // 줄(폴더) 이름 바꾸기 — 끝 따라가기(view-rows 의 신호)
    var r = e.detail && e.detail.renamed; if (!r || typeof r.from !== 'string' || typeof r.to !== 'string') { schedule(); return; }
    load();
    var after = M.retarget(map, 'folder:' + r.from, 'folder:' + r.to, iso());
    if (after !== map) put(after); else schedule();
  });
  function watch() {
    if (typeof MutationObserver === 'undefined') return;
    var mo = new MutationObserver(function () { if (Object.keys(map).length || dotsOf) schedule(); });
    var bn = document.getElementById('bnotes');
    if (bn) mo.observe(bn, {childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class']});
    mo.observe(rowsEl, {childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class']});
    new MutationObserver(function () { if (dotsOf || naming) scale(); }).observe(stage, {attributes: true, attributeFilter: ['style']});   // 배율 — 점·글 크기만
  }

  load();
  return {
    attach: function (a) { A = a; watch(); notesChanged(); return this; },
    reload: function () { load(); schedule(); tell(); },      // 기록 줄 오가기·다른 곳에서 바뀐 상태 파일
    map: function () { return JSON.parse(JSON.stringify(map)); },
    notesChanged: notesChanged,
    selected: function () { return sel; },
    schedule: schedule
  };
}

HD.feature('boardLinks', {needs: ['$', '$$', 'store', 'key', 'record', 'toast', 'warn', 'view', 'rowsEl', 'boardNotes'], mount: mount});
})();
