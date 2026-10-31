/* View — 카드 옮긴 자리(hd-card-pos)의 주인: 읽기·거르기·저장, 카드 놓기, 판 좌표 상자 재기 하나(boxOf), 옮기기·정렬 한 단계(되돌리기).
   줄 배치는 그대로, 카드마다 옮긴 거리만 별도 키에(prefs 가 아닌 키 — prefs.normalize 가 모르는 칸을 버린다). 거르기 규칙 = Model HD.rows.cleanPos,
   줄 이름 옮기기 = HD.rows.rekeyPos('hd-rows-changed' 를 듣는다), 정렬 계산 = HD.align.
   HD.viewCardPos.mount(ctx) → {load(), reload(), save(), place(card), placeAll(), at(id) → {dx, dy, g}|undefined(읽기만), put(id, p)(저장 없이 — 끄는 중),
     set(id, p)(놓고 저장·선 다시 — 되돌리기), map() → 자리 전체, replace(m)(승격), group(card) → 줄 이름, boxOf(card, origin{left, top}) → 판 좌표 상자,
     extent(left) → 옮긴 카드까지 넣은 판 범위, boxes(ids) → {boxes, locked}, move(moves, label) → 옮겼나, arrange(ids, op) → 옮겼나}
   ctx = {$, $$, rowsEl, stage, getItem(k), setItem(k, v), hash, zoom() → z, cardEl(id), locked(id), record(op), toast(msg), redraw()(선), moved()(선택 막대)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var AL_NAME = {left: '왼쪽', hcenter: '가로 가운데', right: '오른쪽', top: '위', vcenter: '세로 가운데', bottom: '아래'};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, rowsEl = ctx.rowsEl;
  var PKEY = 'hd-card-pos:' + ctx.hash, cardPos = {};

  function group(c) { var f = c.closest('.flow'), g = f ? $('.glabel', f) : null; return g ? g.textContent : ''; }
  function liveGroups() { var live = {}; $$('.card', rowsEl).forEach(function (c) { live[c.dataset.id] = group(c); }); return live; }
  function save() { try { ctx.setItem(PKEY, JSON.stringify(cardPos)); } catch (e) {} }   // 저장 실패는 state-sync 가 알린다
  function place(c) {
    var p = cardPos[c.dataset.id];
    if (c.classList.contains('draft')) { c.style.left = (+c.dataset.x + (p ? p.dx : 0)) + 'px'; c.style.top = (+c.dataset.y + (p ? p.dy : 0)) + 'px'; return; }   // 빈 레이아웃: 놓은 자리 + 옮긴 거리
    c.style.left = p ? p.dx + 'px' : ''; c.style.top = p ? p.dy + 'px' : ''; c.classList.toggle('moved', !!p);
  }
  function placeAll() { $$('.card', rowsEl).forEach(place); }
  function load(keepAbsent) {                       // 시작(빈 레이아웃 카드까지 그린 뒤) — 없는 화면·다른 줄로 간 화면의 값은 버리고 다시 쓴다
    var r = HD.rows.cleanPos(ctx.getItem(PKEY), liveGroups(), keepAbsent);
    if (r.bad) console.warn('[hd] card-pos 저장값이 깨져 옮긴 자리를 비웠어요');
    Object.keys(r.pos).forEach(function (id) { cardPos[id] = r.pos[id]; });
    if (r.dirty) save();
    placeAll();
  }
  function reload() { cardPos = {}; load(true); }   // 다시 읽기(기록 줄로 오갈 때 · 밖에서 바뀐 자리, W10 F1) — 아직 판에 없는 카드의 자리는 들고 있다(데이터가 오면 place 가 쓴다)
  function set(id, p) {                             // 되돌리기·다시 하기에서: 그 자리로 놓고 저장·화살표 다시
    if (p) cardPos[id] = {dx: p.dx, dy: p.dy, g: p.g}; else delete cardPos[id];
    $$('.card', rowsEl).forEach(function (c) { if (c.dataset.id === id) place(c); });
    save(); ctx.redraw();
  }
  function boxOf(c, o) {                            // 카드 상자 → o(화면 좌표 원점 {left, top}) 기준 판 좌표(배율 뺀 값) — 정렬·선 끝·맞추기가 같은 셈
    var r = c.getBoundingClientRect(), z = ctx.zoom();
    return {x: (r.left - o.left) / z, y: (r.top - o.top) / z, w: r.width / z, h: r.height / z};
  }
  function extent(left) {                           // 옮긴 카드까지 넣은 판 범위(판 좌표, 레이아웃 상자 — 변형 전) · left = 지금 내용 왼쪽 끝
    var st = ctx.stage, x0 = left, y0 = 0, x1 = st.offsetWidth, y1 = st.offsetHeight, ox = rowsEl.offsetLeft, oy = rowsEl.offsetTop;
    $$('.card:not(.hid):not(.del)', rowsEl).forEach(function (c) {
      x0 = Math.min(x0, ox + c.offsetLeft); y0 = Math.min(y0, oy + c.offsetTop);
      x1 = Math.max(x1, ox + c.offsetLeft + c.offsetWidth); y1 = Math.max(y1, oy + c.offsetTop + c.offsetHeight);
    });
    return {x0: x0, y0: y0, x1: x1, y1: y1};
  }
  function boxes(ids) {                             // 옮길 수 있는 카드의 판 좌표 상자 · 잠긴 카드는 세기만, 숨김·삭제 대기는 뺀다
    var rr = rowsEl.getBoundingClientRect(), out = {boxes: [], locked: 0};
    ids.forEach(function (id) {
      var c = ctx.cardEl(id); if (!c || c.classList.contains('hid') || c.classList.contains('del') || !c.offsetWidth) return;
      if (ctx.locked(id)) { out.locked++; return; }
      var b = boxOf(c, rr); b = {id: id, x: b.x, y: b.y, w: b.w, h: b.h};
      out.boxes.push(b);
    });
    return out;
  }
  function move(moves, label) {                     // moves = {id: [mx, my]} → 옮긴 거리에 더하고 저장 · 기록 한 단계(끌어 옮기기와 같은 저장·되돌리기)
    var before = {}, after = {}, ids = Object.keys(moves).filter(function (id) { return ctx.cardEl(id); });
    if (!ids.length) return false;
    ids.forEach(function (id) {
      var p = cardPos[id], m = moves[id];
      before[id] = p ? {dx: p.dx, dy: p.dy, g: p.g} : null;
      after[id] = {dx: (p ? p.dx : 0) + m[0], dy: (p ? p.dy : 0) + m[1], g: group(ctx.cardEl(id))};
    });
    var put = function (to) {
      ids.forEach(function (id) { if (to[id]) cardPos[id] = to[id]; else delete cardPos[id]; var c = ctx.cardEl(id); if (c) place(c); });
      save(); ctx.redraw(); ctx.moved();
    };
    put(after);
    ctx.record({label: label, undo: function () { put(before); }, redo: function () { put(after); }});
    return true;
  }
  function arrange(ids, op) {                       // op = 정렬 패널 의도 {op:'align'|'distribute'|'stack', …} — 고른 카드든 폴더 카드든
    var b = boxes(ids), A = HD.align, mv = {}, label = '', g;
    if (op.op === 'align') { mv = A.align(b.boxes, op.how); label = '정렬: ' + (AL_NAME[op.how] || op.how); }
    else if (op.op === 'distribute') { mv = A.distribute(b.boxes, op.axis); label = '간격 같게'; }
    else if (op.op === 'stack') { g = Number(op.gap); mv = A.stack(b.boxes, op.axis, g); label = '늘어놓기 (' + (isFinite(g) ? g : 80) + 'px)'; }
    var moved = move(mv, label);
    if (b.locked) ctx.toast('잠긴 화면 ' + b.locked + '개는 그대로 뒀어요');
    else if (!moved && b.boxes.length >= 2) ctx.toast('이미 그렇게 놓여 있어요');
    return moved;
  }

  if (typeof document !== 'undefined') document.addEventListener('hd-rows-changed', function () {   // 줄 이름 바꾸기·줄만 걷기(view-rows 의도) 뒤 옮긴 카드 자리의 줄 이름을 지금 줄로 — 새로고침 뒤에도 그 자리(S1c)
    var r = HD.rows.rekeyPos(cardPos, liveGroups()); if (r.changed) { cardPos = r.pos; save(); }
  });

  return {load: load, reload: reload, save: save, place: place, placeAll: placeAll,
          at: function (id) { return cardPos[id]; }, put: function (id, p) { cardPos[id] = p; }, set: set,
          map: function () { return cardPos; }, replace: function (m) { cardPos = m; save(); placeAll(); },
          group: group, boxOf: boxOf, extent: extent, boxes: boxes, move: move, arrange: arrange};
}

HD.viewCardPos = {mount: mount};
})();
