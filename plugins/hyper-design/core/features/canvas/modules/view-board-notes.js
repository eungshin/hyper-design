/* View — 판 메모(R23): 빈 판에 사람이 둔 글 상자 그리기·만들기·제자리 쓰기·고르기·끌어 옮기기·지우기. 상태 이름 board-notes(hd-board-notes:<hash>)의 주인.
   규칙(모양·빈 메모 버리기·합치기·빈 자리)은 modules/board-notes.js(Model). 상자는 #stage 안 #bnotes 층 = 카드와 같은 변형(확대하면 같이 커짐).
   만들기: 글자 도구(T)로 빈 판 누르기 · 선택(V)으로 빈 판 두 번 누르기 → 그 자리에 빈 메모가 열리고 바로 쓴다. T 로 만들었으면 끝낸 뒤 V 로.
   쓰기: 판을 READ(0.6) 배율보다 작게 보고 있으면 그 메모 자리를 둔 채 0.6 으로 · Enter = 줄바꿈(한글 조합 중 Enter 는 그대로) · Esc · Ctrl+Enter · 밖 누르기 = 끝. 빈 채로 끝내면 버린다(기록 줄 없음). 만들기+쓰기 = 기록 한 줄.
   V: 누르기 = 고르기(파란 테두리) · 끌기 = 옮기기(기록 한 줄) · 두 번 누르기·Enter = 고치기 · Delete·Backspace = 지우기(되돌리면 돌아옴) · Esc = 풀기. T 로 메모 누르기 = 고치기.
   크기(R25): V 로 고른 메모 오른쪽 아래 손잡이 끌기 = 폭(+ 4px 넘게 아래위로 끌었으면 최소 높이 h — 글이 길면 더 커진다), 기록 한 줄 · 손잡이 두 번 누르기 = 높이를 글 높이대로.
   레이어 패널(R25): 의도 'hd-note-pick' {id: 'note:<id>'} 를 받으면 그 메모를 고르고 보이게(배율 1 이하로 맞춤). 그릴 때·고른 것이 바뀔 때 A.changed()(셸 = 레이어 다시 그리기).
   읽기만인 탭(html[data-hd-tab=reader])에서는 만들기·옮기기·고치기·지우기를 하지 않는다. 쓰기 = ctx.store(상태 파일 · file:// 이면 브라우저 저장소).
   등록부 기능 'boardNotes'(needs $ · store · key · record · toast · warn · view · selected) → {attach(A), reload(), selected(), map(), layers(), layerSel(), extent(ext), reveal(id)}
     A(셸이 attach 로 건넴) = {tool() → 지금 도구, setTool(t), changed()?(레이어 패널), clear()?(카드 고르기 풀기)}. 셸은 adoptState 의 'board-notes' 에서 reload() 만 부른다
     layers() → 레이어 줄 [{id, name}] · layerSel() → 고른 메모의 레이어 id | null · extent(ext) → 메모까지 넓힌 판 범위(전체 보기) · reveal(id) → 고르고 보이게 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var READ = 0.6;                                         // 쓰기를 시작할 때 이보다 작게 보고 있으면 이 배율로(누른 자리는 그대로)
var CSS = '#bnotes{position:absolute;left:0;top:0;width:0;height:0;z-index:4}' +
  '.bnote{position:absolute;box-sizing:border-box;min-height:52px;padding:10px 14px;font:22px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#2b2a26;' +
  'background:#fff7c2;border:1px solid #eadb85;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.10);white-space:pre-wrap;word-break:break-word;user-select:none;cursor:default}' +
  '#screens.t-move .bnote{cursor:move}#screens.t-text .bnote{cursor:text}' +
  '.bnote.sel{outline:3px solid #0f7ec2;outline-offset:2px}' +
  '.bn-rs{display:none;position:absolute;right:calc(-9px * var(--bnk,1));bottom:calc(-9px * var(--bnk,1));width:calc(14px * var(--bnk,1));height:calc(14px * var(--bnk,1));' +
  'box-sizing:border-box;background:#fff;border:calc(2px * var(--bnk,1)) solid #0f7ec2;border-radius:2px;cursor:nwse-resize;touch-action:none}' +
  '#screens.t-move .bnote.sel:not(.editing) .bn-rs{display:block}html[data-hd-tab=reader] .bn-rs{display:none!important}' +
  '.bnote.editing{cursor:text;user-select:text}.bnote.editing .bn-text{display:none}' +
  '.bnote textarea{display:block;width:100%;min-height:1.45em;border:0;padding:0;margin:0;font:inherit;line-height:inherit;color:inherit;background:transparent;resize:none;outline:none;overflow:hidden;white-space:pre-wrap}';

function mount(ctx) {
  var B = HD.boardNotes, KEY = ctx.key('hd-' + B.NAME), pane = ctx.view.pane, stage = ctx.$('#stage');
  var A = null, map = {}, sel = null, editing = null, drag = null, rs = null;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var layer = document.createElement('div'); layer.id = 'bnotes'; stage.appendChild(layer);

  function reader() { return document.documentElement.dataset.hdTab === 'reader'; }
  function elOf(id) { return layer.querySelector('.bnote[data-id="' + String(id).replace(/["\\]/g, '') + '"]'); }
  function load() {
    var t = null;
    try { t = ctx.store.getItem(KEY); } catch (e) { t = null; }   // 저장소를 못 읽으면 빈 판(쓰기 실패는 state-sync 가 알린다)
    var p = B.parse(t);
    if (p.bad === 'broken') ctx.warn('[hd] 판 메모 저장값이 깨져 빈 판으로 엽니다');
    else if (p.bad === 'dropped') ctx.warn('[hd] 판 메모 중 모양이 틀린 것을 뺐습니다');
    map = p.map;
    render();
  }
  function place(el, n) {
    el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; el.style.width = n.w + 'px';
    el.style.minHeight = n.h ? n.h + 'px' : '';          // h = 최소 높이(글이 길면 더 커져 잘리지 않는다)
  }
  function render() {                                   // 바뀔 때만(만들기·고치기·옮기기 끝·지우기·다시 읽기) — 쉬는 동안 하는 일 없음
    var keep = editing ? elOf(editing.id) : null;
    Array.prototype.slice.call(layer.children).forEach(function (el) { if (el !== keep) el.remove(); });
    Object.keys(map).forEach(function (id) {
      if (keep && id === editing.id) { place(keep, map[id]); return; }
      var n = map[id], el = document.createElement('div'), tx = document.createElement('div');
      el.className = 'bnote' + (id === sel ? ' sel' : ''); el.dataset.id = id;
      el.setAttribute('role', 'note'); el.setAttribute('aria-label', '판 메모');
      tx.className = 'bn-text'; tx.textContent = n.text; el.appendChild(tx);
      var k = document.createElement('div'); k.className = 'bn-rs'; k.title = '크기 (두 번 누르면 높이 자동)'; k.setAttribute('aria-hidden', 'true'); el.appendChild(k);
      place(el, n); layer.appendChild(el);
    });
    if (sel && !map[sel]) sel = null;
    tell();
  }
  function tell() { if (A && A.changed) A.changed(); }   // 레이어 패널 줄·고른 줄(바뀔 때만)
  function scaleKnob() { layer.style.setProperty('--bnk', (1 / (ctx.view.get().z || 1)).toFixed(3)); }   // 손잡이를 화면에서 같은 크기로(고를 때·올릴 때만 잰다)
  function write() {
    try { ctx.store.setItem(KEY, JSON.stringify(map)); }
    catch (e) { ctx.toast('판 메모를 저장하지 못했어요'); ctx.warn('[hd] 판 메모 저장 실패: ' + (e && e.message || e)); }
  }
  function put(m) { map = m; write(); render(); }
  function commit(after, before, label) {               // 쓰기 + 기록 한 줄(같은 차례 — view-history 의 차이 잡기)
    put(after);
    ctx.record({label: label, undo: function () { put(before); }, redo: function () { put(after); }});
  }
  function select(id) {
    var was = sel; sel = id;
    if (id) scaleKnob();
    Array.prototype.forEach.call(layer.children, function (el) { el.classList.toggle('sel', el.dataset.id === id); });
    if (was !== id) tell();
  }
  function boxes() {                                      // 메모 상자(판 좌표) — 높이는 그려진 상자(글 높이)에서. 전체 보기 때만 잰다
    return Object.keys(map).map(function (id) { var el = elOf(id), n = map[id]; return {x: n.x, y: n.y, w: n.w, h: el ? el.offsetHeight : (n.h || 52)}; });
  }
  function reveal(id) {                                   // 고르고 보이게 — 메모가 판에 꽉 차되 배율 1 보다 크게는 안 함
    if (!map[id] || !elOf(id)) { ctx.warn('[hd] 없는 판 메모: ' + id); return; }
    if (editing) end();
    if (A && A.clear) A.clear();
    select(id);
    var n = map[id], h = elOf(id).offsetHeight;
    var c = HD.viewport.fit({x0: n.x, y0: n.y, x1: n.x + n.w, y1: n.y + h}, pane.clientWidth, pane.clientHeight, 160, function (z) { return Math.min(1, Math.max(0.1, z)); });
    ctx.view.set(c.z, c.tx, c.ty);
    scaleKnob();
  }
  function point(cx, cy) {                               // 화면 px → 판(#stage) 좌표
    var r = stage.getBoundingClientRect(), z = ctx.view.get().z || 1;
    return {x: (cx - r.left) / z, y: (cy - r.top) / z};
  }
  function spotOf(t) {                                   // 누른 자리 → 'note' | 'empty' | 'busy'(규칙 B.spot)
    var chain = [];
    for (var el = t; el && el.nodeType === 1; el = el.parentElement) {
      var tags = [el.tagName.toLowerCase()];
      if (el.id) tags.push('#' + el.id);
      if (el.classList) for (var i = 0; i < el.classList.length; i++) tags.push('.' + el.classList[i]);
      chain.push(tags);
      if (el === pane) break;
    }
    return B.spot(chain);
  }

  // ------------------------------------------------ 제자리 쓰기
  function grow(ta) { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; }
  function readable(n) {                                 // 작게 보는 중이면 그 메모 자리를 그대로 두고 READ 배율로(Obsidian startEditing — 쓰는 글이 읽히게)
    var v = ctx.view.get(); if (!v || v.z >= READ) return;
    ctx.view.set(READ, v.tx + n.x * (v.z - READ), v.ty + n.y * (v.z - READ));
  }
  function edit(id, isNew, before) {
    if (editing) end();
    var el = elOf(id); if (!el || !map[id]) return;
    select(id); readable(map[id]);
    var ta = document.createElement('textarea');
    ta.value = map[id].text; ta.rows = 1; ta.setAttribute('aria-label', '판 메모 쓰기'); ta.spellcheck = false;
    el.classList.add('editing'); el.appendChild(ta);
    editing = {id: id, isNew: !!isNew, ta: ta, before: before || map};
    ta.addEventListener('input', function () { grow(ta); });
    ta.addEventListener('keydown', function (e) {
      e.stopPropagation();                               // 셸의 Esc·도구 키로 새지 않게
      if (e.isComposing || e.keyCode === 229) return;    // 한글 조합 중 Enter·Esc 는 조합 끝내기
      if (e.key === 'Escape' || (e.key === 'Enter' && (e.ctrlKey || e.metaKey))) { e.preventDefault(); ta.blur(); }
    });
    ta.addEventListener('blur', function () { if (editing && editing.ta === ta) end(); });
    ['pointerdown', 'click', 'dblclick'].forEach(function (n) { ta.addEventListener(n, function (e) { e.stopPropagation(); }); });
    grow(ta); ta.focus({preventScroll: true});
    ta.setSelectionRange(ta.value.length, ta.value.length);
  }
  function end() {
    var ed = editing; if (!ed) return;
    editing = null;
    var r = B.finish(map, ed.id, ed.ta.value, Date.now());
    ed.ta.remove();
    var el = elOf(ed.id); if (el) el.classList.remove('editing');
    if (r.kind === 'drop' && ed.isNew) { map = r.map; render(); }   // 빈 새 메모 = 아무 일도 없었던 것(저장·기록 없음)
    else if (r.kind === 'drop') commit(r.map, ed.before, '판 메모 지우기');
    else if (r.kind === 'keep') commit(r.map, ed.before, ed.isNew ? '판 메모 쓰기' : '판 메모 고치기');
    else render();
    if (map[ed.id]) select(ed.id);
    if (ed.isNew && A && A.tool() === 'text') A.setTool('move');   // T 로 하나 쓰면 V 로(Excalidraw·Figma 와 같게)
  }
  function start(cx, cy) {
    if (reader() || !A) return;
    var p = point(cx, cy), z = ctx.view.get().z || 1, r = stage.getBoundingClientRect(), boxes = [];
    Array.prototype.forEach.call(stage.querySelectorAll('.card'), function (c) {   // 카드 상자(판 좌표) — 만들 때 한 번만 잰다
      var b = c.getBoundingClientRect(); if (!b.width) return;
      var o = {x0: b.left, y0: b.top, x1: b.right, y1: b.bottom};
      Array.prototype.forEach.call(c.querySelectorAll('.ftitle, .cbody'), function (t) {   // 카드 아래 이름·설명은 카드 상자 밖으로 나온다
        var q = t.getBoundingClientRect(); if (!q.width) return;
        o.x0 = Math.min(o.x0, q.left); o.y0 = Math.min(o.y0, q.top); o.x1 = Math.max(o.x1, q.right); o.y1 = Math.max(o.y1, q.bottom);
      });
      boxes.push({x0: (o.x0 - r.left) / z, y0: (o.y0 - r.top) / z, x1: (o.x1 - r.left) / z, y1: (o.y1 - r.top) / z});
    });
    var at = B.room(p, boxes); if (!at.free) return;
    var id = B.newId(Date.now()), before = map;
    map = B.create(map, id, at, Date.now());           // 누른 자리 = 첫 줄 글자 자리, 폭 = 오른쪽 카드 앞까지
    render(); edit(id, true, before);
  }

  // ------------------------------------------------ 누르기 · 끌기 · 두 번 누르기
  pane.addEventListener('click', function (e) {
    if (!A || editing) return;
    var s = spotOf(e.target);
    if (s === 'note') return;
    if (sel) select(null);
    if (s === 'empty' && A.tool() === 'text' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); start(e.clientX, e.clientY); }
  });
  pane.addEventListener('dblclick', function (e) {
    if (!A || editing || A.tool() !== 'move' || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
    var s = spotOf(e.target), el = e.target.closest && e.target.closest('.bnote');
    if (s === 'note' && el) { e.preventDefault(); if (!reader()) edit(el.dataset.id); }
    else if (s === 'empty') { e.preventDefault(); start(e.clientX, e.clientY); }
  });
  layer.addEventListener('pointerover', function (e) { if (sel && e.target.closest && e.target.closest('.bnote.sel')) scaleKnob(); });
  layer.addEventListener('pointerdown', function (e) {
    var el = e.target.closest('.bnote'); if (!el || !A) return;
    if (e.target.closest('.bn-rs')) {                     // 크기 손잡이(R25) — V 로 고른 메모에만 보인다
      e.stopPropagation(); e.preventDefault();
      var rid = el.dataset.id; if (e.button !== 0 || reader() || !map[rid]) return;
      rs = {id: rid, el: el, pid: e.pointerId, x0: e.clientX, y0: e.clientY, w0: map[rid].w, h0: el.offsetHeight, w: map[rid].w, h: undefined, moved: false};
      try { e.target.setPointerCapture(e.pointerId); } catch (err) {}   // 잡지 못해도 창 밖으로 나가기 전까지는 끌린다
      return;
    }
    if (editing && editing.id === el.dataset.id) { e.stopPropagation(); return; }
    var t = A.tool();
    if (e.button !== 0 || (t !== 'move' && t !== 'text') || pane.classList.contains('space')) return;   // 손·다른 도구·Space = 판 끌기 그대로
    e.stopPropagation();
    var id = el.dataset.id; select(id);
    if (t !== 'move' || reader() || !map[id]) return;
    drag = {id: id, el: el, pid: e.pointerId, x0: e.clientX, y0: e.clientY, ox: map[id].x, oy: map[id].y, moved: false};
    try { el.setPointerCapture(e.pointerId); } catch (err) {}   // 잡지 못해도 창 밖으로 나가기 전까지는 끌린다
  });
  layer.addEventListener('pointermove', function (e) {
    if (rs && e.pointerId === rs.pid) {
      var k = ctx.view.get().z || 1, rx = e.clientX - rs.x0, ry = e.clientY - rs.y0;
      if (!rs.moved && Math.hypot(rx, ry) < 4) return;
      rs.moved = true;
      rs.w = Math.max(B.MIN_W, Math.min(B.MAX_W, Math.round(rs.w0 + rx / k))); rs.el.style.width = rs.w + 'px';
      if (rs.h !== undefined || Math.abs(ry) >= 4) { rs.h = Math.max(B.MIN_H, Math.round(rs.h0 + ry / k)); rs.el.style.minHeight = rs.h + 'px'; }
      return;
    }
    if (!drag || e.pointerId !== drag.pid) return;
    var z = ctx.view.get().z || 1, dx = (e.clientX - drag.x0) / z, dy = (e.clientY - drag.y0) / z;
    if (!drag.moved && Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) < 4) return;
    drag.moved = true;
    drag.el.style.left = Math.round(drag.ox + dx) + 'px'; drag.el.style.top = Math.round(drag.oy + dy) + 'px';
  });
  function dragEnd(e) {
    if (rs && e.pointerId === rs.pid) {
      var r = rs; rs = null;
      if (!r.moved || !map[r.id]) return;
      var was = map, after = B.resize(map, r.id, r.w, r.h, Date.now());
      if (after !== map) commit(after, was, '판 메모 크기'); else place(r.el, map[r.id]);
      select(r.id); return;
    }
    if (!drag || e.pointerId !== drag.pid) return;
    var d = drag; drag = null;
    if (!d.moved || !map[d.id]) return;
    var z = ctx.view.get().z || 1, before = map;
    commit(B.move(map, d.id, d.ox + (e.clientX - d.x0) / z, d.oy + (e.clientY - d.y0) / z, Date.now()), before, '판 메모 옮기기');
    select(d.id);
  }
  layer.addEventListener('pointerup', dragEnd);
  layer.addEventListener('pointercancel', function (e) {
    if (rs && e.pointerId === rs.pid) { if (map[rs.id]) place(rs.el, map[rs.id]); rs = null; }
    if (drag && e.pointerId === drag.pid) { place(drag.el, map[drag.id]); drag = null; }
  });
  layer.addEventListener('dblclick', function (e) {      // 손잡이 두 번 누르기 = 높이를 글 높이대로(고치기로 새지 않게)
    var el = e.target.closest && e.target.closest('.bn-rs') && e.target.closest('.bnote'); if (!el) return;
    e.stopPropagation(); e.preventDefault();
    var id = el.dataset.id; if (reader() || !map[id]) return;
    var was = map, after = B.resize(map, id, undefined, null, Date.now());
    if (after !== map) { commit(after, was, '판 메모 높이 자동'); select(id); }
  });
  document.addEventListener('hd-note-pick', function (e) {   // 레이어 패널의 판 메모 줄 누르기(R25)
    var lid = String(e.detail && e.detail.id || '');
    if (lid.indexOf(B.LAYER) === 0) reveal(lid.slice(B.LAYER.length));
  });
  layer.addEventListener('click', function (e) {
    var el = e.target.closest('.bnote'); if (!el || !A || editing) return;
    if (A.tool() === 'text' && !reader()) edit(el.dataset.id);
  });

  // ------------------------------------------------ 글쇠(고른 메모 — 셸의 카드 지우기·Esc 보다 먼저)
  addEventListener('keydown', function (e) {
    if (!sel || editing || !A) return;
    var t = e.target, modal = document.getElementById('modal');
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
    if ((modal && !modal.hidden) || document.body.dataset.tab !== 'screens') return;
    if (!map[sel] || (ctx.selected() || []).length) { select(null); return; }   // 그 사이 카드를 골랐으면 카드 쪽 글쇠
    var k = e.key, plain = !e.ctrlKey && !e.metaKey && !e.altKey;
    if ((k === 'Delete' || k === 'Backspace') && plain) {
      if (reader()) return;                              // 읽기만 = view-read-only 가 막고 알린다
      e.preventDefault(); e.stopImmediatePropagation();
      var before = map; commit(B.remove(map, sel), before, '판 메모 지우기');
    } else if (k === 'Enter' && plain) {
      if (reader()) return;
      e.preventDefault(); e.stopImmediatePropagation(); edit(sel);
    } else if (k === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); select(null); }
  }, true);

  load();
  return {
    attach: function (a) { A = a; return this; },
    reload: function () { if (editing) end(); load(); },   // 기록 줄 오가기·다른 곳에서 바뀐 상태 파일
    selected: function () { return sel; },
    map: function () { return JSON.parse(JSON.stringify(map)); },
    layers: function () { return B.layers(map); },
    layerSel: function () { return sel ? B.LAYER + sel : null; },
    extent: function (ext) { return B.extent(ext, boxes()); },
    reveal: reveal
  };
}

HD.feature('boardNotes', {needs: ['$', 'store', 'key', 'record', 'toast', 'warn', 'view', 'selected'], mount: mount});
})();
