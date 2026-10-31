/* Model — 접근성 검사(R59) 결과를 디자이너 말로: axe-core 결과 → 문제 목록(차례·한국어 제목·고치는 법·AI 요청 글·요소 경로)·요약·핀 색·결과 창 자리. DOM·저장소·메시지를 쓰지 않는다.
   입력 = palette.js hd-a11y 의 result {violations:[{id, impact, help, nodes:[{impact, target, any:[{id, data}], hd?}]}]} — hd = 그 요소의 hd-hit 칸(path·text·rect·kind·quote·tag·attrs).
   RULES = v1 규칙 8개(이 상수 하나 — 페이지 단위 규칙(문서 제목·랜드마크·region·html lang)은 디자인 시안에서 잡음이라 뺀다).
   items(raw) → [{rule, impact, count, title, hint, group, nodes:[{path|null, label, detail, text, ask, impact, hit|null}]}]
     차례 = impact critical > serious > moderate > minor, 같으면 RULES 차례(모르는 규칙은 뒤) · 노드는 axe 차례(문서 차례).
     path = hd.path, 없으면 axe target 이 편집 경로 모양(' > ' 조각: #id | tag(.cls)?(:nth-of-type(n))? | body)일 때만, 아니면 null(목록에는 남고 핀·테두리만 없다).
     모르는 규칙 = 제목·글 모두 axe 의 help(영어 그대로), 요청 글 = '이 요소의 접근성 문제를 고쳐 줘 — <help>'.
   summary(items) → '문제 5 · 이름 1 · 대체 글 1 · 대비 1 · 크기 2'(묶음 = 처음 나온 차례) · total(items) → 노드 수
   check(raw) → null | 까닭 글(결과 모양이 깨짐 — View 가 [hd] 경고 + 토스트)
   tone(impact) → 'var(--ui-danger)'|'var(--ui-accent)'|'var(--ui-muted)'(있는 토큰만)
   place(win{left, top, right, bottom}, size{w, h}, vw, vh) → {x, y, w, h} — 크게 보기 창 오른쪽(12px 띄움), 모자라면 왼쪽, 둘 다 모자라면 창 오른쪽 안 → HD.popPlace.clamp
   HD.a11y = {RULES, ORDER, EMPTY, MISSING, CROSS, NO_PALETTE, items, summary, total, check, tone, place, pathOk} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var RULES = ['color-contrast', 'button-name', 'link-name', 'image-alt', 'input-image-alt', 'label', 'select-name', 'target-size'];
var ORDER = {critical: 0, serious: 1, moderate: 2, minor: 3};
var EMPTY = '접근성 문제 없음 (v1 규칙 ' + RULES.length + '개 기준)';
var MISSING = '접근성 검사 파일이 없어요 — 다시 빌드해 주세요';
var CROSS = '앱 화면(개발 서버 주소)은 다른 출처라 접근성 검사를 할 수 없어요';
var NO_PALETTE = '이 화면은 검사할 수 없어요 — 화면에 palette.js 가 없거나 옛것이에요(다시 빌드해 주세요)';
var CUT = 20;

function flat(v) { return String(v == null ? '' : v).replace(/\s+/g, ' ').trim(); }
function up(c) { return /^#[0-9a-f]{3,8}$/i.test(flat(c)) ? flat(c).toUpperCase() : flat(c); }
function dataOf(n, id) {                                 // 그 노드 검사 결과 중 data 가 있는 첫 것(id 가 있으면 그것)
  var all = [].concat(n && n.any || [], n && n.all || [], n && n.none || []);
  for (var i = 0; i < all.length; i++) if (all[i] && all[i].data && typeof all[i].data === 'object' && (!id || all[i].id === id)) return all[i].data;
  return {};
}
function ratio(v) { var x = +v; return isFinite(x) && x > 0 ? (Math.round(x * 10) / 10) + ':1' : ''; }

// 규칙마다: 묶음 이름(요약) · 제목 · 고치는 법 한 줄 · 노드 글(text) · 자세히(detail) · AI 요청 글(ask)
var TEXT = {
  'color-contrast': {group: '대비', title: '글자와 배경 대비가 낮아요', hint: '글자를 더 진하게 하거나 배경을 바꿔요',
    text: function (d) { var now = ratio(d.contrastRatio), need = flat(d.expectedContrastRatio) || '4.5:1'; return '글자와 배경 대비가 낮아요 — ' + (now ? '지금 ' + now + ', ' : '') + need + ' 이상 필요'; },
    detail: function (d) { return d.fgColor || d.bgColor ? '글자 ' + up(d.fgColor) + ' · 배경 ' + up(d.bgColor) : ''; },
    ask: function (d) { var need = flat(d.expectedContrastRatio) || '4.5:1'; return '이 글자 대비를 ' + need + ' 이상으로' + (d.fgColor || d.bgColor ? ' — 지금 ' + up(d.fgColor) + ' on ' + up(d.bgColor) : ''); }},
  'button-name': {group: '이름', title: '이름 없는 단추 — 화면 읽기 도구가 "단추"라고만 읽어요', hint: '단추에 보이는 글자나 aria-label 을 붙여요',
    ask: function () { return '이 단추에 이름을 붙여 줘 — 보이는 글자나 aria-label (지금 화면 읽기 도구가 "단추"라고만 읽어요)'; }},
  'link-name': {group: '이름', title: '이름 없는 링크 — 어디로 가는지 읽히지 않아요', hint: '링크에 글자나 aria-label 을 붙여요',
    ask: function () { return '이 링크에 어디로 가는지 이름을 붙여 줘 — 글자나 aria-label'; }},
  'image-alt': {group: '대체 글', title: '그림에 설명(alt)이 없어요 — 화면 읽기 도구가 파일 이름을 읽어요', hint: '그림에 alt 글을 붙여요(꾸밈 그림이면 alt="")',
    ask: function () { return '이 그림에 alt 설명을 붙여 줘 — 꾸밈 그림이면 alt=""'; }},
  'input-image-alt': {group: '대체 글', title: '그림 단추에 설명(alt)이 없어요', hint: 'alt 에 단추가 하는 일을 적어요',
    ask: function () { return '이 그림 단추의 alt 에 하는 일을 적어 줘'; }},
  'label': {group: '이름', title: '이름표 없는 입력칸 — 무엇을 적는 칸인지 읽히지 않아요', hint: '<label> 이나 aria-label 을 붙여요',
    ask: function () { return '이 입력칸에 이름표를 붙여 줘 — <label> 이나 aria-label'; }},
  'select-name': {group: '이름', title: '이름표 없는 고르기 칸 — 무엇을 고르는지 읽히지 않아요', hint: '<label> 이나 aria-label 을 붙여요',
    ask: function () { return '이 고르기 칸에 이름표를 붙여 줘 — <label> 이나 aria-label'; }},
  'target-size': {group: '크기', title: '누르는 칸이 작아요 — 24×24 이상', hint: '누르는 칸을 24×24px 이상으로 키우거나 옆 칸과 띄워요',
    text: function (d) { var m = +d.minSize || 24, now = +d.width > 0 && +d.height > 0 ? '지금 ' + Math.round(d.width) + '×' + Math.round(d.height) + ', ' : ''; return '누르는 칸이 작아요 — ' + now + m + '×' + m + ' 이상'; },
    ask: function (d) { var m = +d.minSize || 24; return '이 누르는 칸을 ' + m + '×' + m + 'px 이상으로 키우거나 옆 칸과 띄워 줘' + (+d.width > 0 ? ' — 지금 ' + Math.round(d.width) + '×' + Math.round(d.height) : ''); }}
};

var KIND = {text: '글자', button: '버튼', link: '링크', field: '입력칸', box: '영역', image: '그림'};
var TAGKIND = {a: 'link', button: 'button', input: 'field', textarea: 'field', select: 'field', img: 'image', svg: 'image', picture: 'image', video: 'image', canvas: 'image'};
function label(h) {                                      // 대화창 요소 칩과 같은 말(HD.chat.elLabel) — 종류 · 글(20자), 그림은 파일 이름
  if (!h || typeof h !== 'object') return '요소';
  var tag = flat(h.tag).toLowerCase(), k = TAGKIND[tag] === 'image' ? 'image' : KIND[h.kind] ? h.kind : TAGKIND[tag] || '';
  var t = flat(h.quote && h.quote.exact) || flat(h.text);
  if (!t && k === 'image' && h.attrs && h.attrs.src) t = flat(h.attrs.src).split(/[\/\\?#]/).filter(Boolean).pop() || '';
  var name = KIND[k] || '요소';
  return t ? name + ' · ' + (t.length > CUT ? t.slice(0, CUT) + '…' : t) : name;
}

var SEG = /^(?:body|#[A-Za-z_][\w-]*|[a-z][a-z0-9-]*(?:\.[A-Za-z_][\w-]*)?(?::nth-of-type\(\d+\))?)$/;
function pathOk(p) {                                     // 편집·첨부 길의 경로 모양(html_edit.select · palette.js match 와 같은 조각)
  if (typeof p !== 'string' || !p.trim()) return false;
  return p.split(' > ').every(function (s) { return SEG.test(s.trim()); });
}
function pathOf(n) {
  if (n && n.hd && typeof n.hd.path === 'string' && n.hd.path) return n.hd.path;
  var t = n && Array.isArray(n.target) && n.target.length === 1 ? n.target[0] : null;   // 길이 2 이상 = iframe·shadow 안 — 고를 수 없다
  return typeof t === 'string' && pathOk(t) ? t : null;
}

function check(raw) {
  if (!raw || typeof raw !== 'object') return '검사 결과가 없어요';
  if (!Array.isArray(raw.violations)) return '검사 결과 모양이 달라요(violations 없음)';
  return null;
}

function items(raw) {
  if (check(raw)) return [];
  var out = raw.violations.filter(function (v) { return v && typeof v.id === 'string' && Array.isArray(v.nodes) && v.nodes.length; }).map(function (v) {
    var T = TEXT[v.id], help = flat(v.help) || v.id, impact = ORDER.hasOwnProperty(v.impact) ? v.impact : 'minor';
    var nodes = v.nodes.map(function (n) {
      var d = dataOf(n, v.id === 'color-contrast' ? 'color-contrast' : null);
      var text = T ? (T.text ? T.text(d) : T.title) : help;
      return {path: pathOf(n), label: label(n && n.hd), detail: T && T.detail ? T.detail(d) : '', text: text,
              ask: T ? T.ask(d) : '이 요소의 접근성 문제를 고쳐 줘 — ' + help, impact: ORDER.hasOwnProperty(n && n.impact) ? n.impact : impact,
              hit: n && n.hd && typeof n.hd === 'object' ? n.hd : null};
    });
    return {rule: v.id, impact: impact, count: nodes.length, title: T ? T.title : help, hint: T ? T.hint : '', group: T ? T.group : '기타', nodes: nodes};
  });
  function rank(r) { var i = RULES.indexOf(r); return i < 0 ? RULES.length : i; }
  return out.sort(function (a, b) { return ORDER[a.impact] - ORDER[b.impact] || rank(a.rule) - rank(b.rule); });
}

function total(list) { return (list || []).reduce(function (s, i) { return s + (i.count || 0); }, 0); }
function summary(list) {
  var by = {}, keys = [];
  (list || []).forEach(function (i) { if (!by[i.group]) { by[i.group] = 0; keys.push(i.group); } by[i.group] += i.count || 0; });
  return ['문제 ' + total(list)].concat(keys.map(function (k) { return k + ' ' + by[k]; })).join(' · ');
}

function tone(impact) { return impact === 'critical' || impact === 'serious' ? 'var(--ui-danger)' : impact === 'moderate' ? 'var(--ui-accent)' : 'var(--ui-muted)'; }

function place(win, size, vw, vh) {
  var G = 12, M = 8, w = size.w, x = win.right + G;
  if (x + w > vw - M) x = win.left - G - w;
  if (x < M) x = vw - M - w;
  var p = {x: x, y: win.top, w: w, h: size.h};
  return HD.popPlace && HD.popPlace.clamp ? HD.popPlace.clamp(p, vw, vh, {w: Math.min(w, 220), h: 120}) : p;
}

HD.a11y = {RULES: RULES, ORDER: ORDER, EMPTY: EMPTY, MISSING: MISSING, CROSS: CROSS, NO_PALETTE: NO_PALETTE,
           items: items, summary: summary, total: total, check: check, tone: tone, place: place, pathOk: pathOk, label: label};
})();
