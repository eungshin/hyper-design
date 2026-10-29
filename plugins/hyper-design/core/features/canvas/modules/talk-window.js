/* Model — 대화 창 하나(R53)의 규칙: 접힘↔펼침 · 판 끝 붙기 판정 · 붙은 폭 · 붙기/떼기를 도크 의도로. DOM·저장소를 쓰지 않는다.
   창 자리의 진실은 도크 배치(dock.js 상태, 키 hd-dock) 하나 — 대화(talk)가 왼쪽 묶음 = 왼쪽에 붙음 · 오른쪽 묶음 = 오른쪽 · 떠 있는 창 = 떠 있음,
   떠 있을 때 접힘/펼침·기본 자리 여부는 도크 상태 talk {mode, auto}. 떠 있는 창 크기·자리 맞추기는 HD.popPlace.clamp(R58 — 떠 있는 창 자리 함수는 하나).
   where(st) → 'left'|'right'|'float'|'none'   mode(st) → 'docked'|'expanded'|'compact'   fi(st) → 떠 있는 창 번호|-1
   toggle(st) → 접힘↔펼침 의도들(붙은 창 = [])   snap(x, board{left, right}, gap?) → 'left'|'right'|null — 누른 x 가 판 끝 SNAP(40)px 안(도크 위 포함)
   width(w) → 붙은 폭 DW_MIN..DW_MAX(깨진 값 = DW 360)   dock(st, side) → 붙이기 의도들(이미 그 쪽이면 [])
   undock(st, box|null, mode) → 떼기 의도들(box 없음 = 기본 자리, auto)   skip(st) → 도크가 그리지 않을 패널(['talk'] = 떠 있음·창 숨김)
   box0(area{w, h}) → 펼친 창 기본 자리(판 아래 가운데, 아래 12px)   box(st, area) → 지금 펼친 창 자리(맞추기 전)
   HD.talkWindow = {SNAP, DW, DW_MIN, DW_MAX, MIN, BOX, where, mode, fi, toggle, snap, width, dock, undock, skip, box0, box} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var SNAP = 40, DW = 360, DW_MIN = 320, DW_MAX = 560, MIN = {w: 320, h: 240}, BOX = {w: 440, h: 640}, ID = 'talk';

function num(v) { return typeof v === 'number' && isFinite(v); }
function has(list) { return (list || []).some(function (g) { return g && Array.isArray(g.tabs) && g.tabs.indexOf(ID) >= 0; }); }
function fi(st) {
  var fs = st && st.floats || [];
  for (var i = 0; i < fs.length; i++) if (fs[i] && Array.isArray(fs[i].tabs) && fs[i].tabs.indexOf(ID) >= 0) return i;
  return -1;
}
function where(st) {
  if (!st) return 'none';
  if (has(st.left)) return 'left';
  if (has(st.groups)) return 'right';
  return fi(st) >= 0 ? 'float' : 'none';
}
function mode(st) {
  var w = where(st);
  if (w === 'left' || w === 'right') return 'docked';
  return st && st.talk && st.talk.mode === 'expanded' && w === 'float' ? 'expanded' : 'compact';
}
function toggle(st) {
  var m = mode(st);
  if (m === 'docked') return [];
  return [{type: 'talk', mode: m === 'compact' ? 'expanded' : 'compact'}];
}
function snap(x, board, gap) {
  if (!num(x) || !board || !num(board.left) || !num(board.right)) return null;
  var g = num(gap) ? gap : SNAP;
  if (x <= board.left + g) return 'left';
  if (x >= board.right - g) return 'right';
  return null;
}
function width(w) { return num(w) ? Math.round(Math.max(DW_MIN, Math.min(DW_MAX, w))) : DW; }
function dock(st, side) {
  if (where(st) === side || (side !== 'left' && side !== 'right')) return [];
  if (side === 'left') return [{type: 'move', id: ID, side: 'left', to: 'new', at: 0}, {type: 'width', side: 'left', w: width(st.lw)}];
  return [{type: 'move', id: ID, to: 'new', at: (st.groups || []).length}];
}
function undock(st, box, m) {
  var b = box && num(box.x) && num(box.y) ? box : null;
  var w = b && num(b.w) ? b.w : BOX.w, h = b && num(b.h) ? b.h : BOX.h;
  return [{type: 'move', id: ID, to: 'float', x: b ? b.x : 0, y: b ? b.y : 0, w: w, h: h},
          {type: 'talk', mode: m === 'compact' ? 'compact' : 'expanded', auto: !b}];
}
function skip(st) { return st && (st.chat === false || where(st) === 'float') ? [ID] : []; }
function box0(area) {
  var W = area && num(area.w) ? area.w : 0, H = area && num(area.h) ? area.h : 0;
  var w = Math.max(0, Math.min(BOX.w, W - 16)), h = Math.max(0, Math.min(BOX.h, H - 20));
  return {x: Math.round((W - w) / 2), y: Math.round(H - 12 - h), w: Math.round(w), h: Math.round(h)};
}
function box(st, area) {
  var i = fi(st);
  if (i < 0 || !st.talk || st.talk.auto !== false) return box0(area);
  var f = st.floats[i];
  return {x: f.x, y: f.y, w: f.w, h: f.h};
}

HD.talkWindow = {SNAP: SNAP, DW: DW, DW_MIN: DW_MIN, DW_MAX: DW_MAX, MIN: MIN, BOX: BOX,
                 where: where, mode: mode, fi: fi, toggle: toggle, snap: snap, width: width, dock: dock, undock: undock, skip: skip, box0: box0, box: box};
})();
