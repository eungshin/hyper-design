/* Model — 판 글 레이어(t51-9): 카드 iframe 밖 판 위 글 묶음(소개·끝 글·DS 카드)과 그 출처 칸·되는 일, 고치기·지우기 규칙. DOM·저장소를 쓰지 않는다.
   서버 쪽 같은 규칙 = board_text.py(도우미 /api/apply 의 'board' 편집). 칸 키는 hd-data(D) 의 자리 그대로(정한 것·시장 관례 = 판 차례).
   blocks(D, {dscard}) → [{key, layer('@intro-…'|'@foot-…'|'@dscard'), area('intro'|'foot'|'ds'), name, del('file'|'hide'), src, fields:[{key, value, line}]}]
     del 'file' = Delete 가 파일에서 뺀다(story·ideas·people = screens.json, decisions·market = decisions.json) · 'hide' = 만든 글·출처·DS 카드는 판에서 숨기기만
   apply(D, ops) → 새 D(복사) — ops = [{op:'set', to: 칸 키, value} | {op:'delete', to: 묶음 키}] (반영 대기·바로 반영 미리보기). 없는 자리는 건너뜀
   pending(notes) → 메모 중 edit 'board' 를 차례대로 [{id, op, to, value}]
   check(key, text) → {value}(정리한 글) | {error} — 한 줄 칸(제목·이름) = 빈칸 한 칸, 이름은 비울 수 없음, 2000자
   keepEm(raw, text) → 원래 제목의 <em>강조</em> 글이 새 글에도 있으면 다시 감싼다 · plain(raw) = 태그 뺀 글
   captionDelete(field, values) → {changes:[{field, value, old}]} | {error} — 카드 아래 글 Delete: 제목 = 거절, 설명 = '', 정책 = []
   layers(blocks, hidden) → [{id, name}] 레이어 패널 줄(+ 예전에 숨겨 둔 '@intro'·'@foot' 은 다시 보이게 할 수 있게)
   say(op) → {path, text, note} 요청문 글(도우미 없이 보낼 때) · blockOf(key) → 묶음 키 | null
   HD.boardText = {IDS, NAMES, CAPTION, blocks, apply, pending, check, keepEm, plain, captionDelete, layers, say, blockOf} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var NAMES = {hint: '소개 · 안내 줄', story: '소개 · 제목·요약', ideas: '소개 · 아이디어', people: '소개 · 사람', decisions: '정한 것 · 뺀 것',
             market: '시장 관례', palettes: '끝 글 · 색 출처', credits: '끝 글 · 사진 출처', dscard: '디자인 시스템'};
var CAPTION = {title: '카드 제목', purpose: '카드 설명', policies: '카드 정책'};
var LAYER = {hint: '@intro-hint', story: '@intro-story', ideas: '@intro-ideas', people: '@intro-people', decisions: '@intro-decisions',
             market: '@intro-market', palettes: '@foot-palettes', credits: '@foot-credits', dscard: '@dscard'};
var SRC = {story: 'screens.json > story > headline·summary', ideas: 'screens.json > story > ideas', people: 'screens.json > people',
           decisions: 'decisions.json > core · 정한 것(items)', market: 'decisions.json > 시장 관례(items)'};
var IDS = ['@intro-hint', '@intro-story', '@intro-ideas', '@intro-people', '@intro-decisions', '@intro-market', '@foot-palettes', '@foot-credits'];
var KEY = /^(story\.(headline|summary)|story\.ideas\.\d+\.(title|desc)|people\.\d+\.(name|why|win)|decisions\.core|decisions\.items\.\d+\.(name|how|why)|decisions\.market\.\d+\.name)$/;
var LINE = /\.(headline|title|name)$/, NAMED = /\.(title|name)$/, MAX = 2000;

function arr(x) { return Array.isArray(x) ? x : []; }
function obj(x) { return x && typeof x === 'object' && !Array.isArray(x) ? x : null; }
function str(x) { return x == null ? '' : String(x); }

function blocks(D, opt) {
  D = D || {}; opt = opt || {};
  var out = [], st = obj(D.story) || {}, dc = obj(D.decisions) || {};
  var add = function (key, area, fields, del) { out.push({key: key, layer: LAYER[key], area: area, name: NAMES[key], del: del || 'file', src: SRC[key] || null, fields: fields}); };
  add('hint', 'intro', [], 'hide');
  if (st.headline || st.summary) add('story', 'intro', [{key: 'story.headline', value: str(st.headline), line: true}, {key: 'story.summary', value: str(st.summary)}]);
  var ideas = arr(st.ideas).slice(0, 3);
  if (ideas.length) add('ideas', 'intro', [].concat.apply([], ideas.map(function (d, i) {
    return [{key: 'story.ideas.' + i + '.title', value: str(d && d.title), line: true}, {key: 'story.ideas.' + i + '.desc', value: str(d && d.desc)}]; })));
  var ppl = arr(D.people);
  if (ppl.length) add('people', 'intro', [].concat.apply([], ppl.map(function (p, i) {
    return ['name', 'why', 'win'].map(function (f) { return {key: 'people.' + i + '.' + f, value: str(p && p[f]), line: f === 'name'}; }); })));
  var items = arr(dc.items);
  if (items.length || dc.core) add('decisions', 'intro', (dc.core ? [{key: 'decisions.core', value: str(dc.core)}] : []).concat([].concat.apply([], items.map(function (it, i) {
    return [{key: 'decisions.items.' + i + '.name', value: str(it && it.name), line: true}]
      .concat(it && it.how ? [{key: 'decisions.items.' + i + '.how', value: str(it.how)}] : [])
      .concat([{key: 'decisions.items.' + i + '.why', value: str(it && it.why)}]); }))));
  var mk = arr(dc.market);
  if (mk.length) add('market', 'intro', mk.map(function (it, i) { return {key: 'decisions.market.' + i + '.name', value: str(it && it.name), line: true}; }));
  var P = obj(D.palettes);
  if (P && arr(P.options).length) add('palettes', 'foot', [], 'hide');
  if (arr(D.credits).length) add('credits', 'foot', [], 'hide');
  if (opt.dscard) add('dscard', 'ds', [], 'hide');
  return out;
}

function blockOf(key) {
  var k = str(key);
  if (!KEY.test(k)) return null;
  if (/^story\.ideas\./.test(k)) return 'ideas';
  if (/^story\./.test(k)) return 'story';
  if (/^people\./.test(k)) return 'people';
  if (/^decisions\.market\./.test(k)) return 'market';
  return 'decisions';
}

function setAt(D, key, value) {                     // D 자리 = 키 그대로(정한 것·시장 관례는 D 의 판 차례) — 없는 자리면 false
  var p = key.split('.'), o = D;
  for (var i = 0; i < p.length - 1; i++) {
    var k = /^\d+$/.test(p[i]) ? +p[i] : p[i];
    if (o == null || typeof o !== 'object' || o[k] == null) return false;
    o = o[k];
  }
  if (typeof o !== 'object') return false;
  o[p[p.length - 1]] = value; return true;
}

function apply(D, ops) {
  var n = JSON.parse(JSON.stringify(D || {}));
  arr(ops).forEach(function (o) {
    if (!o) return;
    if (o.op === 'set' && KEY.test(str(o.to))) { setAt(n, o.to, str(o.value)); return; }
    if (o.op !== 'delete') return;
    var st = obj(n.story), dc = obj(n.decisions);
    if (o.to === 'story' && st) { delete st.headline; delete st.summary; }
    else if (o.to === 'ideas' && st) delete st.ideas;
    else if (o.to === 'people') n.people = [];
    else if (o.to === 'decisions' && dc) { dc.core = ''; dc.items = []; }
    else if (o.to === 'market' && dc) dc.market = [];
  });
  return n;
}

function pending(notes) {
  return arr(notes).filter(function (n) { return n && n.edit === 'board'; })
    .map(function (n) { return {id: n.id, op: n.op, to: n.to, value: n.op === 'set' ? str(n.value) : null}; });
}

function normalise(key, text) {
  var s = str(text);
  if (LINE.test(key)) return s.replace(/\s+/g, ' ').trim();
  return s.replace(/\r\n?/g, '\n').replace(/[ \t]+/g, ' ').replace(/ *\n */g, '\n').trim();
}
function check(key, text) {
  if (!KEY.test(str(key))) return {error: '고칠 수 없는 판 글 칸이에요: ' + key};
  var v = normalise(key, text);
  if (v.length > MAX) return {error: '판 글이 ' + MAX + '자를 넘어요'};
  if (!v && NAMED.test(key)) return {error: '이름은 비울 수 없어요 — 지우려면 그 묶음을 고르고 Delete'};
  return {value: v};
}

function plain(raw) { return str(raw).replace(/<\/?em>/g, ''); }
function keepEm(raw, text) {
  var m = /<em>([\s\S]*?)<\/em>/.exec(str(raw)), t = str(text);
  if (!m || !m[1] || t.indexOf(m[1]) < 0) return t;
  var i = t.indexOf(m[1]);
  return t.slice(0, i) + '<em>' + m[1] + '</em>' + t.slice(i + m[1].length);
}

function captionDelete(field, v) {
  v = v || {};
  if (field === 'title') return {error: '제목은 비울 수 없어요 — 카드를 지우려면 카드를 고르고 Delete'};
  if (field === 'purpose') return str(v.purpose) ? {changes: [{field: 'purpose', value: '', old: str(v.purpose)}]} : {error: '설명이 이미 비어 있어요'};
  if (field === 'policies') return arr(v.policies).length ? {changes: [{field: 'policies', value: [], old: arr(v.policies).slice()}]} : {error: '정책이 이미 비어 있어요'};
  return {error: '모르는 카드 글 칸이에요: ' + field};
}

function layers(bs, hidden) {
  var h = hidden || {};
  var out = arr(bs).map(function (b) { return {id: b.layer, name: b.name}; });
  if (h['@intro']) out.push({id: '@intro', name: '판 글 · 소개 전체(예전 숨김)'});
  if (h['@foot']) out.push({id: '@foot', name: '판 글 · 끝 전체(예전 숨김)'});
  return out;
}

function say(o) {
  o = o || {};
  if (o.op === 'delete') {
    var src = SRC[o.to] || o.to;
    return {path: src, text: NAMES[o.to] || o.to, note: '판 글 지우기: ' + (NAMES[o.to] || o.to) + ' — ' + src + ' 에서 빼기'};
  }
  var k = str(o.to), p = k.split('.'), path;
  if (p[0] === 'decisions' && p[1] !== 'core') path = 'decisions.json > ' + (p[1] === 'market' ? '시장 관례' : 'items') + '(판 차례 ' + (+p[2] + 1) + ') > ' + p[3];
  else if (p[0] === 'decisions') path = 'decisions.json > core';
  else path = 'screens.json > ' + p.join(' > ');
  return {path: path, text: '', note: '판 글 고치기: ' + (NAMES[blockOf(k)] || k) + ' 의 ' + p[p.length - 1] + ' 을 "' + str(o.value) + '"(으)로 (' + path + ')'};
}

HD.boardText = {IDS: IDS, NAMES: NAMES, CAPTION: CAPTION, blocks: blocks, apply: apply, pending: pending, check: check, keepEm: keepEm, plain: plain,
                captionDelete: captionDelete, layers: layers, say: say, blockOf: blockOf};
})();
