/* Model — 요소 막대 규칙(블록 편집, task 49a·49b): 고른 요소에 띄울 단추·켜짐·앱 카드면 AI 요청·단축키·상위 고르기·속성 칸·부품 요청 글. DOM·저장소·메시지를 쓰지 않는다.
   h = palette.js hd-hit 답 {path, text, full, textOk, prev, next, root, up, tag, attrs, rect, src?} · o = {app}(앱 카드 = 개발 서버 주소 화면, 또는 h.src 가 있음)
HD.blocks = {ACTS, bar(h, o) → [{act, label, title, on, ask}](모든 동작 — 요소 메뉴·단축키),
                grip(h, o) → {on, title} — 끌어서 순서 바꾸기 손잡이(49c: 앱 카드·화면 뿌리·형제 없음 = 꺼짐), isApp(file), keyAct({key, code, alt, ctrl, meta, shift}) → act|null(Alt+↑↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete 지우기 · [·Shift+Enter 상위 · Enter 'enter' · Tab 'next' · Shift+Tab 'prev'),
                enterOf(h) → 'text'|'down'(Enter: 글자면 그 자리 고치기, 아니면 첫 자식),
                askText(act, h) → 요청 글(앱 카드), chainOf(h, chain) → '고르기 ▸' 목록(그 요소 + 조상, 같은 상자 감싸기는 건너뜀, 51-3),
                tone(h, o) → 'app'|''(요소 상자 색 — 앱 카드 = 요청으로만, Figma 인스턴스 보라 자리, 51-3), parentPick(h, chain) → 고를 상위 hit|null,
                ATTRS, attrOk(tag, name), attrFields(h) → [{name, label, value}], partAsk(kind, title) → 부품 요청 글,
                R17 시안 A · R50: icons(h, o) → 막대 아이콘 [{act, label, key, ask, on, title}](o.pins = 고정 목록, 없으면 메모·글자·AI — 차례 그대로 + 전체 메뉴 ⋯ 맨 끝, 못 쓰는 동작 = on:false + 까닭 title),
                menu(h, o) → 요소 메뉴 묶음 [{head:'고르기'|'고치기'|'요청', items:[{act, label, key, on, ask, title, pinned?, pinOk?, pinWhy?, sub?:[같은 모양]}]}](sub = 옆 목록 '부품 ▸', pin 칸 = 실제 동작 줄만), keyOf(act, h, where) → 실제로 듣는 키 힌트|'',
                R50 고정: PIN_MAX(6) · PINS_DEFAULT · pins(raw) → {list, warn}(없음 = 기본 · 배열 아님 = 기본 + 경고 · 모르는 act 버림 + 경고 · 중복 제거 · 6개 자르기) ·
                pin(list, act) → {pins} | {why}(토글 — 새로 고정 = 끝에, 6개면 거절) · pinState(list, act) → {on, ok, why}(메뉴 줄 핀)}
   o.links = 셸이 '연결' 묶음으로 덧붙일 항목 수 — 메뉴 전체가 MENU_MAX(10) 를 넘으면 '주소 복사'(R30, Ctrl+L 로도 됨)만 뺀다(안전줄 — '부품 ▸' 로 합친 뒤로는 넘지 않음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var ACTS = ['parent', 'text', 'attr', 'remove', 'dup', 'up', 'down', 'swap', 'insert', 'memo'];
var SPEC = {
  parent: {label: '상위', title: '감싼 요소 고르기 ([ · Shift+Enter)'},
  text:   {label: '글자', title: '글자 고치기 (T · 더블클릭)'},
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

function grip(h, o) {
  h = h || {}; o = o || {};
  if (o.app || (h.src && h.src.file)) return {on: false, title: '앱 카드는 끌어서 옮길 수 없어요 — 메모로 AI에게 요청하세요'};
  if (h.root) return {on: false, title: WHY.root};
  if (h.prev === false && h.next === false) return {on: false, title: '옮길 형제 요소가 없어요'};
  return {on: true, title: '끌어서 순서 바꾸기 (Alt+↑/↓)'};
}

function keyAct(e) {
  if (!e || typeof e.key !== 'string') return null;
  var mod = !!(e.ctrl || e.meta);
  if ((e.key === 'Enter' || e.key === 'Tab') && !mod && !e.alt) {   // Figma(51-2): Enter 안으로 · Shift+Enter 부모 · Tab/Shift+Tab 형제
    return e.key === 'Enter' ? (e.shift ? 'parent' : 'enter') : (e.shift ? 'prev' : 'next');
  }
  if (e.shift) return null;
  if ((e.code === 'BracketLeft' || e.key === '[') && !mod && !e.alt) return 'parent';   // 자판 자리(한글 자판도) — Ctrl+Shift+[ 는 프로젝트 탭(view-tabs)
  if ((e.key === 'Delete' || e.key === 'Backspace') && !mod && !e.alt) return 'remove';   // Backspace 도(Figma)
  if (e.alt && !mod) return e.key === 'ArrowUp' ? 'up' : e.key === 'ArrowDown' ? 'down' : null;
  if (mod && !e.alt && e.key.toLowerCase() === 'd') return 'dup';
  return null;
}

// Enter(51-2): 글을 바꿀 수 있고 글이 있는 요소 = 그 자리 글자 고치기('text'), 아니면 첫 자식 요소 고르기('down')
function enterOf(h) {
  if (!h || h.textOk !== true) return 'down';
  return String(h.full || h.text || '').trim() ? 'text' : 'down';
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
  if (act === 'ai') return '바꿔 주세요: ';                    // AI에게 바꿔 달라기(R17) — 메모 창(의도 = 바꾸기)에 미리 채움
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

// '고르기 ▸'(51-3, Figma F6 Select layer): 그 요소 + 조상(가까운 것부터) — 앞에 남긴 것과 상자가 같으면(감싸기만 한 요소) 건너뛴다
function chainOf(h, chain) {
  if (!h || !h.path) return [];
  var out = [h], last = h.rect;
  (Array.isArray(chain) ? chain : []).forEach(function (c) {
    if (!c || !c.path || same(c.rect, last)) return;
    out.push(c); last = c.rect;
  });
  return out;
}
// 요소 상자 색(51-3): 앱 카드(개발 서버 화면 또는 소스 줄이 있는 요소) = 'app' — 막대의 앱 카드 판정(bar)과 같은 규칙
function tone(h, o) { return (o && o.app) || (h && h.src && h.src.file) ? 'app' : ''; }

// ---- R17 시안 A: 작은 아이콘 막대 + 전체 메뉴(오른쪽 클릭 = ⋯). 힌트는 실제로 듣는 키만(keyAct · 크게 보기 hd-dbl)
var MENU = {parent: '상위 고르기', inner: '안쪽 고르기', chain: '레이어 고르기',
            text: '글자 고치기', attr: '속성 고치기…', dup: '복제', remove: '지우기', up: '위로 옮기기', down: '아래로 옮기기',
            insert: '아래에 넣기…', swap: '다른 부품으로 바꾸기…', part: '부품', memo: '메모 달기', ai: 'AI에게 바꿔 달라기', addr: '주소 복사'};
// R27 F05: 요소 메뉴는 10개 이하 · 겹침 없이 — 상위(Shift+Enter · [)·안쪽(Enter)·위/아래로 옮기기(Alt+↑/↓ · 막대 손잡이)는 키로, AI에게 바꿔 달라기는 막대 AI 아이콘·메모 창 '바꾸기'로.
//   레이어 고르기 ▸ 목록이 그 요소 + 조상(상위 고르기와 같은 길)을 준다. R30: 아래에 넣기·다른 부품으로 바꾸기 = '부품 ▸' 옆 목록 하나(sub) — 주소 복사 자리
var GROUPS = [['고르기', ['chain']], ['고치기', ['text', 'attr', 'dup', 'remove', 'part']], ['요청', ['memo', 'addr']]];
var SUB = {part: ['insert', 'swap']};               // 옆 목록 항목 = 그 안 동작들(켜진 것만, 하나도 없으면 항목째 빠짐)
var PICK_ONLY = {inner: 1, chain: 1, ai: 1, addr: 1};   // bar 에 없는 항목 — 고르기·요청이라 늘 켜짐(앱 카드도 그대로) · addr = 주소 복사(R30, 읽기만)
var MENU_MAX = 10;                                   // 셸의 연결 항목(o.links)까지 센 한도 — 넘으면 주소 복사만 빠짐(지금 묶음으로는 넘지 않는다, 안전줄)
var KEY = {parent: 'Shift+Enter', dup: 'Ctrl+D', remove: 'Del', up: 'Alt+↑', down: 'Alt+↓', addr: 'Ctrl+L'};   // keyAct 와 같은 키 · addr = view-address 가 듣는 키
function keyOf(act, h, where) {
  if (act === 'inner') return enterOf(h) === 'down' ? 'Enter' : '';
  if (act === 'text') return where === 'modal' ? '더블클릭' : enterOf(h) === 'text' ? 'Enter' : '';   // 크게 보기 손·선택 두 번 누르기(R52 — 판도 V 두 번 누르기지만 고른 요소에는 Enter 가 가깝다)
  return KEY[act] || '';
}
function menu(h, o) {
  h = h || {}; o = o || {};
  var by = {};
  bar(h, o).forEach(function (b) { by[b.act] = b; });
  function withPin(it) {                             // R50: 실제 동작 줄 = 핀 칸(pinned·pinOk), 묶음 머리·고르기 목록은 없음
    if (!it || it.sub || PINNABLE.indexOf(it.act) < 0) return it;
    var ps = pinState(o.pins, it.act); it.pinned = ps.on; it.pinOk = ps.ok; it.pinWhy = ps.why; return it;
  }
  function item(act) { return withPin(item0(act)); }
  function item0(act) {
    if (PICK_ONLY[act]) return {act: act, label: MENU[act], key: keyOf(act, h, o.where), on: true, ask: false, title: ''};
    if (SUB[act]) {
      var sub = SUB[act].map(item).filter(Boolean);
      return sub.length ? {act: act, label: MENU[act], key: '', on: true, ask: false, title: '', sub: sub} : null;
    }
    var b = by[act];
    if (!b || (!b.on && act !== 'text')) return null;   // 꺼진 것은 빼되 글자 고치기는 남긴다(누르면 까닭)
    return {act: act, label: MENU[act] + (b.ask ? ' — AI에게 요청' : ''), key: b.ask || !b.on ? '' : keyOf(act, h, o.where), on: b.on, ask: b.ask, title: b.title};
  }
  var gs = GROUPS.map(function (g) { return {head: g[0], items: g[1].map(item).filter(Boolean)}; });
  var n = (+o.links || 0) + gs.reduce(function (s, g) { return s + g.items.length; }, 0);
  if (n > MENU_MAX) gs.forEach(function (g) { g.items = g.items.filter(function (it) { return it.act !== 'addr'; }); });
  return gs.filter(function (g) { return g.items.length; });
}
// ---- R50 막대에 고정하기(Chrome 확장 메뉴의 줄마다 핀 · Office 빠른 실행 '막대에서 빼기'): 고정 목록 = prefs.elbarPins(정리는 여기, 저장은 View)
//   고정할 수 있는 것 = 메뉴의 실제 동작 줄(옆 목록 '부품 ▸' 안 항목 포함 — 묶음 머리 chain·part 는 아님) + 기본 막대의 AI(메뉴에는 없음, R27 F05)
var PINNABLE = ['memo', 'text', 'ai', 'attr', 'dup', 'remove', 'insert', 'swap', 'addr'];
var PINS_DEFAULT = ['memo', 'text', 'ai'];            // 칸 없음 = 지금 막대 그대로
var PIN_MAX = 6;
var PIN_FULL = '막대에는 ' + PIN_MAX + '개까지 — 하나를 빼고 고정해 주세요';
var PIN_NO = '이 동작은 막대에 고정할 수 없어요';
var NO_ATTR = '이 요소에는 고칠 속성이 없어요';
function pins(raw) {                                 // 저장값 → {list, warn}(warn = '[hd] …' 한 줄 | '' — 콘솔에 남기는 일은 View)
  if (raw === undefined || raw === null) return {list: PINS_DEFAULT.slice(), warn: ''};
  if (!Array.isArray(raw)) return {list: PINS_DEFAULT.slice(), warn: '[hd] 요소 막대 고정 목록이 깨졌어요(배열 아님) — 기본 막대로 보여요'};
  var list = [], bad = [];
  raw.forEach(function (a) {
    if (typeof a !== 'string' || PINNABLE.indexOf(a) < 0) { bad.push(String(a)); return; }
    if (list.indexOf(a) < 0) list.push(a);
  });
  var cut = list.length > PIN_MAX;
  list = list.slice(0, PIN_MAX);
  var warn = bad.length ? '[hd] 요소 막대 고정 목록에서 모르는 동작을 뺐어요: ' + bad.join(', ') : cut ? '[hd] 요소 막대 고정 목록이 ' + PIN_MAX + '개를 넘어 뒤를 잘랐어요' : '';
  return {list: list, warn: warn};
}
function pinState(list, act) {                       // 메뉴 줄 핀: on = 고정됨 · ok = 누를 수 있음 · why = 못 누르는 까닭
  var l = pins(list).list, on = l.indexOf(act) >= 0;
  if (PINNABLE.indexOf(act) < 0) return {on: false, ok: false, why: PIN_NO};
  if (!on && l.length >= PIN_MAX) return {on: false, ok: false, why: PIN_FULL};
  return {on: on, ok: true, why: ''};
}
function pin(list, act) {                            // 토글 → {pins: 새 목록} | {why: 거절 까닭} — 새로 고정 = 끝에
  var l = pins(list).list, st = pinState(l, act);
  if (!st.ok) return {why: st.why};
  return {pins: st.on ? l.filter(function (a) { return a !== act; }) : l.concat([act])};
}
// 막대 아이콘 = 고정 차례 그대로 + ⋯(손잡이 맨 앞은 View) · 그 요소에 못 쓰는 동작은 숨기지 않고 꺼짐 + 까닭(막대 모양이 요소마다 흔들리지 않게 — '글자' 숨김도 이 규칙으로)
function icons(h, o) {
  h = h || {}; o = o || {};
  var by = {};
  bar(h, o).forEach(function (b) { by[b.act] = b; });
  var out = pins(o.pins).list.map(function (act) {
    if (PICK_ONLY[act] || act === 'memo') return {act: act, label: MENU[act], key: keyOf(act, h, o.where), ask: false, on: true, title: ''};
    var b = by[act];
    if (!b) return {act: act, label: MENU[act], key: '', ask: false, on: false, title: act === 'attr' ? NO_ATTR : PIN_NO};
    return {act: act, label: MENU[act] + (b.ask ? ' — AI에게 요청' : ''), key: b.ask || !b.on ? '' : keyOf(act, h, o.where), ask: b.ask, on: b.on, title: b.on ? '' : b.title};
  });
  out.push({act: 'more', label: '전체 메뉴', key: '오른쪽 클릭', ask: false, on: true, title: ''});
  return out;
}

HD.blocks = {ACTS: ACTS, ATTRS: ATTRS, PIN_MAX: PIN_MAX, PINS_DEFAULT: PINS_DEFAULT, pins: pins, pin: pin, pinState: pinState, bar: bar, grip: grip, isApp: isApp, keyAct: keyAct, enterOf: enterOf, askText: askText, parentPick: parentPick, chainOf: chainOf, tone: tone,
             attrOk: attrOk, attrFields: attrFields, partAsk: partAsk, icons: icons, menu: menu, keyOf: keyOf};
})();
