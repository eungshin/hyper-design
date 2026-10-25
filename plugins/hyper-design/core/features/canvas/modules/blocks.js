/* Model — 요소 막대 규칙(블록 편집, task 49a·49b): 고른 요소에 띄울 단추·켜짐·앱 카드면 AI 요청·단축키·막대 자리·상위 고르기·속성 칸·부품 요청 글. DOM·저장소·메시지를 쓰지 않는다.
   h = palette.js hd-hit 답 {path, text, full, textOk, prev, next, root, up, tag, attrs, rect, src?} · o = {app}(앱 카드 = 개발 서버 주소 화면, 또는 h.src 가 있음)
   HD.blocks = {ACTS, bar(h, o) → [{act, label, title, on, ask}](모든 동작 — 요소 메뉴·단축키), shown(items) → 막대에 보일 것(↑·↓ 는 단축키·메뉴만, 49c),
                grip(h, o) → {on, title} — 끌어서 순서 바꾸기 손잡이(49c: 앱 카드·화면 뿌리·형제 없음 = 꺼짐), isApp(file), keyAct({key, code, alt, ctrl, meta, shift}) → act|null(Alt+↑↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete 지우기 · [ 상위),
                askText(act, h) → 요청 글(앱 카드), place(anchor, size, view, avoid, others?) → {x, y, below, side, over}(others = 둘레 글 상자, 무르게 비킴), parentPick(h, chain) → 고를 상위 hit|null,
                barLimit(anchor, view) → 막대 최대 너비, fit(widths, limit, more) → 막대에 남길 단추 수(나머지는 ⋯),
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

var OFF_BAR = {up: 1, down: 1};                     // 막대에서 뺀 단추(49c) — 끌어서 옮기기 손잡이가 대신, Alt+↑/↓·요소 메뉴는 그대로
function shown(items) { return (Array.isArray(items) ? items : []).filter(function (it) { return it && !OFF_BAR[it.act]; }); }
function grip(h, o) {
  h = h || {}; o = o || {};
  if (o.app || (h.src && h.src.file)) return {on: false, title: '앱 카드는 끌어서 옮길 수 없어요 — 메모로 AI에게 요청하세요'};
  if (h.root) return {on: false, title: WHY.root};
  if (h.prev === false && h.next === false) return {on: false, title: '옮길 형제 요소가 없어요'};
  return {on: true, title: '끌어서 순서 바꾸기 (Alt+↑/↓)'};
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

// 막대 자리(화면 좌표): 위(왼쪽 맞춤 → 오른쪽 맞춤) → 아래(같은 차례) → 오른쪽 옆 → 왼쪽 옆 — 고른 요소 위에는 놓지 않는다(요소가 보이는 칸을 다 덮을 때만 over).
// view = 보이는 칸 {x, y, w, h}(크게 보기 = 그 창 · 판 = 판 칸) · avoid = 비킬 사각형 하나 또는 목록(창 제목 막대·카드 선택 막대·도구 막대 — 절대)
// others = 둘레 글 상자들(화면 좌표, 선택) — 무르게 비킨다: 아무 글도 덮지 않는 첫 자리, 없으면 덮는 넓이가 가장 작은 자리(같으면 차례). 고른 요소 안 상자는 셈하지 않는다
function area(a, b) {
  var w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}
function box(r) { return !!r && isFinite(r.x) && isFinite(r.y) && isFinite(r.w) && isFinite(r.h) && r.w > 0 && r.h > 0; }
function place(anchor, size, view, avoid, others) {
  var gap = 6, m = 8, vx = view.x || 0, vy = view.y || 0, vr = vx + view.w, vb = vy + view.h;
  var clampX = function (x) { return Math.max(vx + m, Math.min(vr - size.w - m, x)); };
  var clampY = function (y) { return Math.max(vy + m, Math.min(vb - size.h - m, y)); };
  var x = clampX(anchor.x + size.w > vr - m ? anchor.x + anchor.w - size.w : anchor.x), xr = clampX(anchor.x + anchor.w - size.w);
  var hard = (Array.isArray(avoid) ? avoid : [avoid]).filter(box);
  var hit = function (xx, yy) { return hard.some(function (a) { return xx < a.x + a.w && xx + size.w > a.x && yy < a.y + a.h && yy + size.h > a.y; }); };
  var obs = (Array.isArray(others) ? others : []).filter(function (o) {
    return box(o) && !(o.x >= anchor.x - 1 && o.y >= anchor.y - 1 && o.x + o.w <= anchor.x + anchor.w + 1 && o.y + o.h <= anchor.y + anchor.h + 1);
  });
  var cover = function (c) { var r = {x: c.x, y: c.y, w: size.w, h: size.h}; return obs.reduce(function (s, o) { return s + area(r, o); }, 0); };
  var above = anchor.y - size.h - gap, below = anchor.y + anchor.h + gap, y = clampY(anchor.y), rx = anchor.x + anchor.w + gap, lx = anchor.x - size.w - gap;
  var cs = [];
  var add = function (ok, c) { if (ok && !hit(c.x, c.y) && !cs.some(function (d) { return d.x === c.x && d.y === c.y; })) cs.push(c); };
  [x, xr].forEach(function (xx) { add(above >= vy + m, {x: xx, y: above, below: false, side: '', over: false}); });
  [x, xr].forEach(function (xx) { add(below + size.h <= vb - m, {x: xx, y: below, below: true, side: '', over: false}); });
  add(rx + size.w <= vr - m, {x: rx, y: y, below: false, side: 'right', over: false});
  add(lx >= vx + m, {x: lx, y: y, below: false, side: 'left', over: false});
  var best = null, bs = Infinity;
  for (var i = 0; i < cs.length; i++) { var s = cover(cs[i]); if (s < bs) { best = cs[i]; bs = s; if (!s) break; } }
  return best || {x: x, y: vy + m, below: false, side: '', over: true};
}

// 막대 너비: 요소 칸(요소 너비, 너무 좁으면 220)까지 — 보이는 칸 안. 넘으면 뒤 단추를 "⋯" 로(fit)
function barLimit(anchor, view) { return Math.max(0, Math.min(view.w - 16, Math.max(anchor.w || 0, 220))); }
// widths = 단추마다 너비(앞 구분선 포함) · more = "⋯" 너비 → 막대에 남길 단추 수(다 들어가면 전부, 아니면 ⋯ 자리를 남기고 앞에서부터, 최소 1)
function fit(widths, limit, more) {
  var sum = widths.reduce(function (s, w) { return s + w; }, 0);
  if (sum <= limit) return widths.length;
  var n = 0, acc = more;
  while (n < widths.length && acc + widths[n] <= limit) { acc += widths[n]; n++; }
  return Math.max(Math.min(1, widths.length), n);
}

HD.blocks = {ACTS: ACTS, ATTRS: ATTRS, bar: bar, shown: shown, grip: grip, isApp: isApp, keyAct: keyAct, askText: askText, place: place, parentPick: parentPick,
             attrOk: attrOk, attrFields: attrFields, partAsk: partAsk, barLimit: barLimit, fit: fit};
})();
