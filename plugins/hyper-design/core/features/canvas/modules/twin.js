/* Model — 캔버스 화면 ↔ 앱 카드 맞음 검증(V2)의 짝·기억 열쇠·결과·카드 표·목록 줄·고쳐 달라는 짧은 요청 글. 순수(DOM·저장소·메시지·AI 없음).
   pair(id, links, cards) → {app, part, how}|null — links = HD.chatBoth.links(/api/app-parts) {화면 id: {file, parts:[{file}]}}, cards = [{id, file}](판 카드).
     차례: 그 화면이 끌어 쓰는 부품 파일을 그대로 싣는 다른 카드(how 'part') → 부품 파일 이름(.html 뺀 것)이 id 인 앱 무대 카드(개발 서버 주소 —
     app.json 무대 이름, how 'stage'). 없으면 null = NO_PAIR('견줄 앱 화면 없음').
   key(fp, stamp) → 기억 열쇠 '지문\n도장' | null(지문 없음 = 기억하지 않음) — 화면 파일 지문(카드 주소 ?v=) · 앱 부품 도장(parts 도장 + 앱 카드 주소 + HMR 수).
   result(screen, app, d, meta{size, capped, ms}) → {status: match|differ, screen, app, count, match, missing, extra, style, unsure, size, capped, ms}
   noPair(screen) · failed(screen, app, why) → {status: 'no-pair'|'error', …, why} — hd verify 종료 코드 2.
   badge(res) → {text: '앱과 일치'|'다름 N'|'검증 못 함', tone: ok|diff|none, title}|null(짝 없음·결과 없음 = 표 없음).
   lines(res) → [{kind: missing|extra|style|unsure, a, b, label}](목록 창 줄 — a·b = 두 카드 스냅숏 차례 번호, 강조에 씀).
   request(res, titleOf) → 짧은 요청 글(머리 한 줄 + '- 줄' 20개까지 + '- 외 N개') | ''(다른 곳 없음). 스크린샷·스냅숏 원본은 넣지 않는다.
   HD.twin = {NO_PAIR, MAX_LINES, pair, key, result, noPair, failed, badge, lines, request} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var NO_PAIR = '견줄 앱 화면 없음', MAX_LINES = 20;
var ROLE = {button: '버튼', heading: '제목', link: '링크', input: '입력칸', img: '그림', text: '글'};
var PROP = {color: '글자색', bg: '바탕색', fs: '글자 크기', fw: '글자 굵기', radius: '모서리'};
var WHY = {role: '역할 다름', text: '글자 다름', dup: '같은 글자 수가 다름'};

function rel(f) {
  if (typeof f !== 'string' || !f) return '';
  return f.replace(/\\/g, '/').split('?')[0].split('/').filter(function (s) { return s && s !== '.'; }).join('/');
}
function isDev(f) { return typeof f === 'string' && /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//i.test(f); }

function pair(id, links, cards) {
  var l = links && typeof links === 'object' ? links[id] : null;
  if (!l || !Array.isArray(l.parts) || !Array.isArray(cards)) return null;
  var others = cards.filter(function (c) { return c && c.id != null && String(c.id) !== String(id); });
  for (var i = 0; i < l.parts.length; i++) {
    var f = rel(l.parts[i] && l.parts[i].file);
    if (!f) continue;
    var c = others.filter(function (c) { return !isDev(c.file) && rel(c.file) === f; })[0];
    if (c) return {app: String(c.id), part: f, how: 'part'};
    var stem = f.split('/').pop().replace(/\.html?$/i, '');
    var s = others.filter(function (c) { return isDev(c.file) && String(c.id) === stem; })[0];
    if (s) return {app: String(s.id), part: f, how: 'stage'};
  }
  return null;
}

function key(fp, stamp) { return fp ? String(fp) + '\n' + (stamp == null ? '' : String(stamp)) : null; }

function result(screen, app, d, meta) {
  meta = meta || {};
  var n = HD.twinDiff.count(d);
  return {status: n ? 'differ' : 'match', screen: screen, app: app, count: n, match: d.match, missing: d.missing, extra: d.extra,
          style: d['style'], unsure: d.unsure, size: meta.size || null, capped: !!meta.capped, ms: meta.ms == null ? null : meta.ms};
}
function noPair(screen) { return {status: 'no-pair', screen: screen, app: null, why: NO_PAIR}; }
function failed(screen, app, why) { return {status: 'error', screen: screen, app: app || null, why: String(why || '잴 수 없어요')}; }

function badge(res) {
  if (!res || typeof res !== 'object') return null;
  if (res.status === 'match') return {text: '앱과 일치', tone: 'ok', title: '앱 화면 ' + res.app + ' 과 글자·구조·스타일 토큰이 같아요'};
  if (res.status === 'differ') return {text: '다름 ' + res.count, tone: 'diff', title: '앱 화면 ' + res.app + ' 과 다른 곳 ' + res.count + '개 — 눌러서 목록'};
  if (res.status === 'error') return {text: '검증 못 함', tone: 'none', title: res.why};
  return null;
}

function q(t) { return "'" + t + "'"; }
function what(e) { return (ROLE[e.role] || e.role) + ' ' + q(e.text); }
function lines(res) {
  if (!res || typeof res !== 'object') return [];
  var out = [];
  (res.missing || []).forEach(function (e) { out.push({kind: 'missing', a: e.a, b: null, label: '앱에 없음 · ' + what(e)}); });
  (res.extra || []).forEach(function (e) { out.push({kind: 'extra', a: null, b: e.b, label: '앱에만 있음 · ' + what(e)}); });
  (res['style'] || []).forEach(function (e) {
    var ps = (e.props || []).map(function (p) { return (PROP[p.prop] || p.prop) + ' ' + p.a + ' → ' + p.b; }).join(', ');
    out.push({kind: 'style', a: e.a, b: e.b, label: '스타일 다름 · ' + what(e) + ' — ' + ps});
  });
  (res.unsure || []).forEach(function (e) {
    var tail = e.other ? (e.other.role !== e.role ? ' ↔ ' + what(e.other) : ' ↔ ' + q(e.other.text)) : '';
    out.push({kind: 'unsure', a: e.a, b: e.b, label: '확실하지 않음 · ' + what(e) + tail + ' (' + (WHY[e.why] || e.why) + ')'});
  });
  return out;
}

function name(id, titleOf) { var t = titleOf ? titleOf(id) : null; return t == null || t === '' ? String(id) : t + '(' + id + ')'; }
function request(res, titleOf) {
  var ls = lines(res);
  if (!ls.length) return '';
  var head = '캔버스 화면 ' + name(res.screen, titleOf) + ' ↔ 앱 화면 ' + name(res.app, titleOf) + ': 다른 곳 ' + ls.length + '개 — 캔버스(디자인)에 맞게 앱을 고친 뒤 `hd verify ' + res.screen + '` 으로 확인';
  var body = ls.slice(0, MAX_LINES).map(function (l) { return '- ' + l.label; });
  if (ls.length > MAX_LINES) body.push('- 외 ' + (ls.length - MAX_LINES) + '개');
  return [head].concat(body).join('\n');
}

HD.twin = {NO_PAIR: NO_PAIR, MAX_LINES: MAX_LINES, pair: pair, key: key, result: result, noPair: noPair, failed: failed, badge: badge, lines: lines, request: request};
})();
