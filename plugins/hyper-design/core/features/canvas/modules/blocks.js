/* Model — 요소 막대 규칙(블록 편집, task 49a·49b): 고른 요소에 띄울 단추·켜짐·앱 카드면 AI 요청·단축키·막대 자리·상위 고르기·속성 칸·부품 요청 글. DOM·저장소·메시지를 쓰지 않는다.
   h = palette.js hd-hit 답 {path, text, full, textOk, prev, next, root, up, tag, attrs, rect, src?} · o = {app}(앱 카드 = 개발 서버 주소 화면, 또는 h.src 가 있음)
   HD.blocks = {ACTS, bar(h, o) → [{act, label, title, on, ask}], isApp(file), keyAct({key, code, alt, ctrl, meta, shift}) → act|null(Alt+↑↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete 지우기 · [ 상위),
                askText(act, h) → 요청 글(앱 카드), place(anchor, size, view, avoid) → {x, y, below, side, over}, parentPick(h, chain) → 고를 상위 hit|null,
                ATTRS, attrOk(tag, name), attrFields(h) → [{name, label, value}], partAsk(kind, title) → 부품 요청 글} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ACTS = ['parent', 'text', 'attr', 'remove', 'dup', 'up', 'down', 'swap', 'insert', 'memo'];
var SPEC = {
  parent: {label: '상위', title: '감싼 요소 고르기 ([)'},
  text:   {label: '글자', title: '글자 고치기 (T · 크게 보기에서 더블클릭)'},
  attr:   {label: '속성', title: '이미지 주소·대체 글 · 링크 주소 · 안내 글 고치기'},
  remove: {label: '지우기', title: '요소 지우기 (Del)'},
  dup:    {label: '복제', title: '요소 복제 — 바로 뒤에 (Ctrl+D)'},
  up:     {label: '↑', title: '위로 옮기기 (Alt+↑)'},
  down:   {label: '↓', title: '아래로 옮기기 (Alt+↓)'},
  swap:   {label: '바꾸기', title: '이 요소를 Components 부품으로 바꾸기'},
  insert: {label: '아래에 넣기', title: '이 요소 아래에 Components 부품 넣기'},
  memo:   {label: '메모', title: '이 요소에 메모 (AI에게 요청)'}
};
var WHY = {
  text: '안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요',   // helper.py BLOCK_REASON · palette.js textOk 와 같은 규칙
  root: '화면 뿌리(맨 바깥 요소)는 지우거나 복제·옮기거나 부품으로 바꿀 수 없어요',
  first: '맨 위 요소라 더 위로 옮길 수 없어요',
  last: '맨 아래 요소라 더 아래로 옮길 수 없어요',
  top: '맨 바깥 요소예요 — 더 위가 없어요'
};
var DEV = /^https?:\/\/(127\.0\.0\.1|localhost)(:\d{1,5})?\//i;   // build_canvas.DEV_URL 과 같은 규칙(앱 카드)
var SELECT_ONLY = {parent: 1, memo: 1};              // 파일을 바꾸지 않는 단추 — 앱 카드에서도 그대로

// 속성 칸 허용 목록 — helper.py ATTR_OK · palette.js ATTR_OK 와 같은 규칙(on*·style 은 절대)
var ATTRS = {img: ['src', 'alt'], a: ['href'], input: ['placeholder'], textarea: ['placeholder']};
var ATTR_LABEL = {src: '이미지 주소', alt: '대체 글', href: '링크 주소', placeholder: '안내 글'};
function attrOk(tag, name) { return (ATTRS[String(tag || '').toLowerCase()] || []).indexOf(name) >= 0; }
function attrFields(h) {
  var tag = h && h.tag, a = (h && h.attrs) || {};
  return (ATTRS[String(tag || '').toLowerCase()] || []).map(function (n) {
    return {name: n, label: ATTR_LABEL[n], value: typeof a[n] === 'string' ? a[n] : ''};
  });
}

function isApp(file) { return typeof file === 'string' && DEV.test(file); }

function why(act, h) {                               // 꺼진 까닭 | '' (켜짐)
  if (act === 'memo' || act === 'attr') return '';
  if (act === 'parent') return h.up === false ? WHY.top : '';
  if (act === 'text') return h.textOk === false ? WHY.text : '';
  if (h.root) return WHY.root;
  if (act === 'up' && h.prev === false) return WHY.first;
  if (act === 'down' && h.next === false) return WHY.last;
  return '';
}

function bar(h, o) {
  h = h || {}; o = o || {};
  var app = !!o.app || !!(h.src && h.src.file), hasAttr = attrFields(h).length > 0;
  return ACTS.filter(function (act) { return act !== 'attr' || hasAttr; }).map(function (act) {
    var s = SPEC[act];
    if (app && !SELECT_ONLY[act]) return {act: act, label: s.label, title: 'AI에게 요청 — ' + s.title.replace(/ \(.*\)$/, '') + '(앱 카드는 파일에 바로 쓰지 않아요)', on: true, ask: true};
    var w = why(act, h);
    return {act: act, label: s.label, title: w || s.title, on: !w, ask: false};
  });
}

function keyAct(e) {
  if (!e || typeof e.key !== 'string' || e.shift) return null;
  var mod = !!(e.ctrl || e.meta);
  if ((e.code === 'BracketLeft' || e.key === '[') && !mod && !e.alt) return 'parent';   // 자판 자리(한글 자판도) — Ctrl+Shift+[ 는 프로젝트 탭(view-tabs)
  if (e.key === 'Delete' && !mod && !e.alt) return 'remove';
  if (e.alt && !mod) return e.key === 'ArrowUp' ? 'up' : e.key === 'ArrowDown' ? 'down' : null;
  if (mod && !e.alt && e.key.toLowerCase() === 'd') return 'dup';
  return null;
}

function partAsk(kind, title) {                      // 부품 넣기·바꾸기를 AI 에게(뼈대를 못 뽑았거나 앱 카드·도우미 없음) — 견본 글은 넣지 않고 데이터는 화면에 맞게
  var t = String(title || '').trim() || '부품';
  return kind === 'swap' ? '이 요소를 ' + t + '(으)로 바꾸기 — 데이터는 화면에 맞게' : '이 자리에 ' + t + ' 넣기 — 데이터는 화면에 맞게';
}

function askText(act, h) {                           // 앱 카드: 파일 대신 AI 에게 보낼 요청 글(메모 창에 미리 채움)
  var S = HD.edits && HD.edits.say;
  if (act === 'text') return '글자 바꾸기: "' + String((h && (h.full || h.text)) || '').replace(/\s+/g, ' ').trim() + '" → ""';
  if (act === 'attr') return '속성 바꾸기: ' + attrFields(h || {}).map(function (f) { return f.name + '="' + f.value + '" → ""'; }).join(' · ');
  if (act === 'swap' || act === 'insert') return partAsk(act, '');
  if (!S) return '';
  return act === 'remove' ? S.remove() : act === 'dup' ? S.duplicate() : act === 'up' || act === 'down' ? S.move(act) : '';
}

// 상위 고르기: chain = 고른 요소의 조상 hit(가까운 것부터, body·html 은 없음) → 상자가 다른 첫 조상(같은 상자 = 감싸기만 한 요소라 눌러도 바뀌어 보이지 않음)
function same(a, b) {
  return !!a && !!b && Math.abs(a.x - b.x) <= 1 && Math.abs(a.y - b.y) <= 1 && Math.abs(a.w - b.w) <= 1 && Math.abs(a.h - b.h) <= 1;
}
function parentPick(h, chain) {
  if (!Array.isArray(chain)) return null;
  for (var i = 0; i < chain.length; i++) {
    var c = chain[i];
    if (c && c.path && !same(c.rect, h && h.rect)) return c;
  }
  return null;
}

// 막대 자리(화면 좌표): 요소 위(왼쪽 맞춤, 넘치면 오른쪽 맞춤) → 아래 → 오른쪽 옆 → 왼쪽 옆 — 고른 요소 위에는 놓지 않는다(요소가 보이는 칸을 다 덮을 때만 over).
// view = 보이는 칸 {x, y, w, h}(크게 보기 = 그 창 · 판 = 판 칸) · avoid = 비킬 사각형(카드 선택 막대)
function place(anchor, size, view, avoid) {
  var gap = 6, m = 8, vx = view.x || 0, vy = view.y || 0, vr = vx + view.w, vb = vy + view.h;
  var clampX = function (x) { return Math.max(vx + m, Math.min(vr - size.w - m, x)); };
  var clampY = function (y) { return Math.max(vy + m, Math.min(vb - size.h - m, y)); };
  var x = anchor.x + size.w > vr - m ? anchor.x + anchor.w - size.w : anchor.x;
  x = clampX(x);
  var hit = function (xx, yy) { return avoid && xx < avoid.x + avoid.w && xx + size.w > avoid.x && yy < avoid.y + avoid.h && yy + size.h > avoid.y; };
  var above = anchor.y - size.h - gap, below = anchor.y + anchor.h + gap;
  if (above >= vy + m && !hit(x, above)) return {x: x, y: above, below: false, side: '', over: false};
  if (below + size.h <= vb - m && !hit(x, below)) return {x: x, y: below, below: true, side: '', over: false};
  var y = clampY(anchor.y), rx = anchor.x + anchor.w + gap, lx = anchor.x - size.w - gap;
  if (rx + size.w <= vr - m && !hit(rx, y)) return {x: rx, y: y, below: false, side: 'right', over: false};
  if (lx >= vx + m && !hit(lx, y)) return {x: lx, y: y, below: false, side: 'left', over: false};
  return {x: x, y: vy + m, below: false, side: '', over: true};
}

HD.blocks = {ACTS: ACTS, ATTRS: ATTRS, bar: bar, isApp: isApp, keyAct: keyAct, askText: askText, place: place, parentPick: parentPick,
             attrOk: attrOk, attrFields: attrFields, partAsk: partAsk};
})();
