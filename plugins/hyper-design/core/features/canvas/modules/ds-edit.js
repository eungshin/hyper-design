/* Model — Foundation 토큰 고치기 규칙(R55): 토큰 종류·값 검사(Python token_edit 와 같은 표)·고칠 칸·문서 탭 고르기 메시지 모양·토큰 주소. DOM·저장소를 쓰지 않는다.
   kindOf(이름) → 'color'|'size'|'weight'|'line'|'radius'|'space'|'shadow'|'other'   (palette.js tokenKind 와 같은 표 — 테스트가 견준다)
   check(이름, 값, 있는 이름들?) → {ok, value(정리한 값), why}   없는 이름·자유 CSS(; { } < > \ url( expression 주석) 거절, 종류마다 모양(tests/fixtures/token-values.json)
   fields(pick) → [{name, kind, input:'color'|'len'|'num'|'text', value, hex?, num?, unit?}]   글자 줄(--fs-X) = --fs-X · --fw-X · --lh-X(pick.vars 에 있는 것만)
   compose(field, 입력) → 저장할 값 글   len = 숫자 + 지금 단위 · color = hex 면 대문자
   pickMsg(on) → {type:'hd-pick', on, mode, doc:true}(문서 탭 iframe 에) · readPick(hd-sel) → {token, kind, label, rect, vars} | null(토큰을 고르지 않음·모양이 틀림)
   href(base, slug, v) → 토큰 css 주소: slug(바탕 팔레트, '@project' = 프로젝트 tokens.css) · v = 다시 읽기 표(?v=) · docTab(이름) → Foundation·Components 인가
   부품(phase C, Components 탭): family(이름) → 'color'|'radius'|'space'|'font-size'|'box'|'weight'|'line'|'shadow'|null · same(가, 나) — Python component_edit 와 같은 표
     (tests/fixtures/component-families.json). 부품 칸은 같은 묶음 토큰만 고른다(사용자 결정 — 자유 값 없음).
     readPick 은 hd-sel 의 part {key, title, classes, tag, state} 도 받는다 → {kind:'part', part, label, rect}.
   reloadMsg(sheet, v) → {type:'hd-css-reload', sheet:'tokens'|'components', v} | null — 저장 뒤 모든 틀이 그 스타일 파일만 다시 읽는다(한 메시지)
   HD.dsEdit = {PROJECT, kindOf, check, fields, compose, pickMsg, readPick, href, docTab, family, same, reloadMsg} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var PROJECT = '@project', MAX = 200;
var NAME = /^--[A-Za-z0-9-]+$/, BAD = /[;{}<>\\\x00-\x1f]/, BAD_WORDS = ['url(', 'expression', '/*', '*/', 'javascript:', '@import'];
var SPACE_EXACT = ['--page-x', '--block-pad', '--block-gap', '--row-py'];
var KINDS = [['--c-', 'color'], ['--fs-', 'size'], ['--fw-', 'weight'], ['--lh-', 'line'], ['--r-', 'radius'], ['--shadow-', 'shadow'],
             ['--stack-', 'space'], ['--space-', 'space'], ['--gap-', 'space'], ['--h-', 'size'], ['--w-', 'size']];
var HEX = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/, FUNC = /^(rgb|rgba|hsl|hsla)\(\s*[0-9.,%\s/+-]+\)$/i;
var LEN = /^(\d+(\.\d+)?|\.\d+)(px|rem|em|%|vw|vh)$/, NUM = /^(\d+(\.\d+)?|\.\d+)$/, SHADOW = /^[#\w\s.,()%/-]+$/;
var DOC = {foundation: 1, components: 1};

function kindOf(name) {
  var n = String(name || '');
  if (SPACE_EXACT.indexOf(n) >= 0) return 'space';
  for (var i = 0; i < KINDS.length; i++) if (n.indexOf(KINDS[i][0]) === 0) return KINDS[i][1];
  return 'other';
}
function no(why) { return {ok: false, value: null, why: why}; }
function yes(v) { return {ok: true, value: v, why: ''}; }

function check(name, value, names) {
  if (typeof name !== 'string' || !NAME.test(name)) return no('토큰 이름이 아니에요');
  if (Array.isArray(names) && names.indexOf(name) < 0) return no('없는 토큰: ' + name);
  if (typeof value !== 'string') return no('값이 글이 아니에요');
  var v = value.trim();
  if (!v) return no('값이 비었어요');
  if (v.length > MAX) return no('값이 ' + MAX + '자를 넘어요');
  var b = BAD.exec(v); if (b) return no('쓸 수 없는 글자가 있어요: ' + b[0]);
  var low = v.toLowerCase();
  for (var i = 0; i < BAD_WORDS.length; i++) if (low.indexOf(BAD_WORDS[i]) >= 0) return no('쓸 수 없는 값이에요: ' + BAD_WORDS[i]);
  var k = kindOf(name);
  if (k === 'color') return HEX.test(v) ? yes(v.toUpperCase()) : FUNC.test(v) ? yes(v) : no('색은 #RRGGBB 처럼 써요');
  if (k === 'size' || k === 'space' || k === 'radius') return v === '0' || LEN.test(v) ? yes(v) : no('숫자와 단위(px·rem·em·%)로 써요');
  if (k === 'weight') return NUM.test(v) && v.indexOf('.') < 0 && +v >= 100 && +v <= 900 ? yes(v) : no('굵기는 100~900 사이 숫자예요');
  if (k === 'line') return (NUM.test(v) && +v >= 0.5 && +v <= 5) || LEN.test(v) ? yes(v) : no('줄 높이는 0.5~5 사이 숫자예요');
  if (k === 'shadow') return SHADOW.test(v) ? yes(v) : no('그림자 값에 쓸 수 없는 글자가 있어요');
  return yes(v);
}

function hex6(v) {
  var m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(v || '').trim()); if (!m) return '';
  var h = m[1].length === 3 ? m[1].replace(/./g, function (c) { return c + c; }) : m[1];
  return '#' + h.toUpperCase();
}
function field(name, value) {
  var k = kindOf(name), v = String(value == null ? '' : value).trim(), f = {name: name, kind: k, value: v};
  if (k === 'color') { f.input = 'color'; f.hex = hex6(v); return f; }
  if (k === 'weight') { f.input = 'num'; return f; }
  var m = LEN.exec(v);
  if (k === 'line' && !m) { f.input = 'num'; return f; }
  if (k === 'size' || k === 'space' || k === 'radius' || k === 'line') {
    f.input = 'len'; f.num = m ? v.slice(0, v.length - m[3].length) : (v === '0' ? '0' : v); f.unit = m ? m[3] : 'px'; return f;
  }
  f.input = 'text'; return f;
}
function fields(pick) {
  if (!pick || typeof pick.token !== 'string') return [];
  var vars = pick.vars || {}, t = pick.token;
  if (t.indexOf('--fs-') === 0) {                   // 글자 줄: 크기 · 굵기 · 줄 높이 — 어느 칸을 고치나가 종류
    var tail = t.slice(5), out = [field(t, vars[t])];
    ['--fw-', '--lh-'].forEach(function (p) { if (vars[p + tail] != null && String(vars[p + tail]).trim()) out.push(field(p + tail, vars[p + tail])); });
    return out;
  }
  return [field(t, vars[t])];
}
function compose(f, raw) {
  var s = String(raw == null ? '' : raw).trim();
  if (!f) return s;
  if (f.input === 'len') return s === '0' && !f.unit ? '0' : s + (f.unit || 'px');
  if (f.input === 'color') return HEX.test(s) ? s.toUpperCase() : s;
  return s;
}
function pickMsg(on) { return {type: 'hd-pick', on: !!on, mode: on ? 'select' : '', doc: true}; }
function isRect(r) { return !!r && typeof r === 'object' && ['x', 'y', 'w', 'h'].every(function (k) { return typeof r[k] === 'number' && isFinite(r[k]); }); }
var CLS = /^[A-Za-z0-9_-]{1,60}$/, SHEETS = {tokens: 1, components: 1};
function clean(s, n) { return String(s == null ? '' : s).replace(/\s+/g, ' ').trim().slice(0, n); }
function readPart(d) {
  var p = d.part;
  if (!p || typeof p !== 'object' || Array.isArray(p) || !Array.isArray(p.classes) || !isRect(d.rect)) return null;
  var cls = p.classes.filter(function (c) { return typeof c === 'string' && CLS.test(c); }).slice(0, 40);
  if (!cls.length) return null;
  return {kind: 'part', label: clean(d.label || p.title, 60), rect: {x: d.rect.x, y: d.rect.y, w: d.rect.w, h: d.rect.h},
          part: {key: clean(p.key, 40), title: clean(p.title, 60), classes: cls, tag: /^[a-z][a-z0-9-]*$/i.test(p.tag || '') ? p.tag.toLowerCase() : '', state: clean(p.state, 20)}};
}
function family(name) {
  if (typeof name !== 'string' || !NAME.test(name)) return null;
  var k = kindOf(name);
  if (k === 'size') return name.indexOf('--fs-') === 0 ? 'font-size' : 'box';
  return k === 'other' ? null : k;
}
function same(a, b) { var f = family(a); return f !== null && f === family(b); }
function reloadMsg(sheet, v) { return SHEETS[sheet] === 1 ? {type: 'hd-css-reload', sheet: sheet, v: String(v)} : null; }
function readPick(d) {
  if (d && typeof d === 'object' && d.part !== undefined && d.token === undefined) return readPart(d);
  if (!d || typeof d !== 'object' || typeof d.token !== 'string' || !NAME.test(d.token) || !isRect(d.rect)) return null;
  var vars = {};
  if (d.vars && typeof d.vars === 'object') Object.keys(d.vars).forEach(function (k) { if (NAME.test(k) && typeof d.vars[k] === 'string') vars[k] = d.vars[k]; });
  return {token: d.token, kind: kindOf(d.token), label: String(d.label || '').replace(/\s+/g, ' ').trim().slice(0, 60),
          rect: {x: d.rect.x, y: d.rect.y, w: d.rect.w, h: d.rect.h}, vars: vars};
}
function href(base, slug, v) {
  var b = String(base || '').split('?')[0];
  var h = slug && slug !== PROJECT ? b.replace(/tokens(-[^/]*)?\.css$/, 'tokens-' + slug + '.css') : b;
  return v ? h + '?v=' + v : h;
}
function docTab(name) { return typeof name === 'string' && DOC[name] === 1; }

HD.dsEdit = {PROJECT: PROJECT, kindOf: kindOf, check: check, fields: fields, compose: compose, pickMsg: pickMsg, readPick: readPick, href: href, docTab: docTab,
             family: family, same: same, reloadMsg: reloadMsg};
})();
