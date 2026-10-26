/* Model — 그림 카드(R18) 찍기 규칙: 크기·밀도·상한, 찍을 수 있는 문서인가, 요소 지도 모양, 계산된 스타일 줄이기, url·글꼴 고르기, 결과 판정. DOM·네트워크를 쓰지 않는다.
   size(w, h, density, max) → {w, h, density, scale, pw, ph, capped} — 카드 CSS px(w×h) × 밀도(1|2, 그 밖 = 1)를 긴 변 max(기본 MAX 4096) 안으로. scale = 실제 그림 px / CSS px. 0·숫자 아님 = {error}
   reach({doc, frameSrc, href, ready, protocol}) → null | {code, why} — 찍을 수 없는 까닭(오류 탐지): 'unreachable'(contentDocument 를 못 읽음 — 다른 출처·file://) · 'unloaded'(about:blank·data-src 만 있는 내린 카드) · 'loading'(다 실리지 않음)
   pickable({tag, hd, w, h, hidden, x, y, vw, vh}) → 요소 지도에 넣나 — 고르기(V)·hd-sel 의 deep 과 같은 뜻(그 자리 아무 요소, html·body·머리 요소·캔버스가 넣은 data-hd-* 빼고) + 보이고 카드 안에 걸침
   elementMap(items, max) → [{path, rect:{x,y,w,h}}] — path 없음·같은 path 두 번째는 뺌, rect 는 palette.js rectOf 처럼 정수, 문서 차례 앞에서 max(기본 MAX_ELEMENTS)개
   INHERITED · skipProp(name)(그림에 안 보이거나 물리 속성과 겹치는 속성) · styleText(names, own, parent, dflt) → 'p:v;…' — 이어받는 속성은 부모와 다를 때(부모 없음 = 뿌리 = 늘), 나머지는 태그 기본값과 다를 때만, 선 굵기(border-*-width·outline-width)는 늘
   urls(text) → 'url(…)' 안 주소(data: 빼고, 한 번씩) · swapUrls(text, map) → 주소를 map 값(data URL)으로
   imports(cssText, base) → @import 주소(절대) · fontFaces(cssText, base) → [{family, weight, slant, range, src:[{url, format}]}] · usedFaces(faces, loaded) → 실린 글꼴(family·weight·slant·range 가 같음)만
   oneLine(rects) → 요소 글 상자들(Range.getClientRects)이 한 줄인가 — 그러면 그림에서 줄바꿈을 끈다(SVG 글자 너비 차이로 줄이 바뀌지 않게) ·
   faceCss(face, dataUrl) → '@font-face{…}' · canvasBg(htmlBg, bodyBg) → 'html'|'body'|null(CSS 처럼 html 바탕이 없으면 body 바탕이 판 전체)
   svg(w, h, pw, ph, inner) → SVG foreignObject 문자열 · verdict(missing) → {ok, lines} — 넣지 못한 자원이 있으면 ok=false, 줄마다 무엇·왜(숨기지 않는다)
   HD.snapshot = {MAX, MAX_ELEMENTS, BUDGET, TIMEOUT, INHERITED, size, reach, pickable, elementMap, skipProp, styleText, urls, swapUrls, imports, fontFaces, usedFaces, faceCss, canvasBg, oneLine, svg, verdict} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function size(w, h, density, max) {
  w = +w; h = +h;
  if (!(w > 0) || !(h > 0)) return {error: 'size'};
  var d = density === 2 ? 2 : 1, m = max > 0 ? max : HD.snapshot.MAX;
  var s = d, capped = false;
  if (Math.max(w, h) * s > m) { s = m / Math.max(w, h); capped = true; }
  return {w: Math.round(w), h: Math.round(h), density: d, scale: s, pw: Math.max(1, Math.floor(w * s)), ph: Math.max(1, Math.floor(h * s)), capped: capped};
}

function reach(o) {
  if (!o.doc) return {code: 'unreachable', why: o.protocol === 'file:' ? 'file:// 로 열린 캔버스는 카드 문서를 읽을 수 없다(브라우저가 막음) — 라이브 카드로 둔다' : '카드 문서를 읽을 수 없다(다른 출처)'};
  var href = String(o.href || '');
  if (!o.frameSrc || href === 'about:blank' || href === '') return {code: 'unloaded', why: '카드 iframe 이 실려 있지 않다'};
  if (o.ready !== 'complete') return {code: 'loading', why: '카드 문서가 아직 다 실리지 않았다'};
  return null;
}

var NOPICK = /^(html|body|head|script|style|link|meta|title|template|noscript|base)$/;
function pickable(n) {
  if (!n || !n.tag || NOPICK.test(String(n.tag).toLowerCase()) || n.hd || n.hidden) return false;
  if (!(n.w > 0) || !(n.h > 0)) return false;
  if (n.vw > 0 && n.vh > 0 && (n.x >= n.vw || n.y >= n.vh || n.x + n.w <= 0 || n.y + n.h <= 0)) return false;
  return true;
}

function elementMap(items, max) {
  var m = max > 0 ? max : HD.snapshot.MAX_ELEMENTS, seen = {}, out = [];
  (items || []).forEach(function (it) {
    if (out.length >= m || !it || !it.path || seen[it.path]) return;
    var r = it.rect || {};
    seen[it.path] = 1;
    out.push({path: it.path, rect: {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.w), h: Math.round(r.h)}});
  });
  return out;
}

var INHERITED = {};
('color font-family font-size font-style font-variant font-weight font-stretch font-kerning font-feature-settings font-variation-settings ' +
 'font-optical-sizing font-size-adjust font-synthesis-weight font-synthesis-style font-synthesis-small-caps font-variant-ligatures font-variant-caps ' +
 'font-variant-numeric font-variant-east-asian font-variant-alternates font-variant-position font-palette letter-spacing line-height text-align text-align-last ' +
 'text-indent text-transform text-shadow text-rendering text-size-adjust text-underline-position text-underline-offset text-decoration-skip-ink ' +
 'text-emphasis-color text-emphasis-position text-emphasis-style text-wrap text-wrap-mode text-wrap-style white-space white-space-collapse word-spacing word-break ' +
 'overflow-wrap line-break hyphens hyphenate-character tab-size direction writing-mode text-orientation visibility cursor ' +
 'list-style-type list-style-position list-style-image border-collapse border-spacing caption-side empty-cells quotes orphans widows ' +
 'paint-order fill fill-opacity fill-rule stroke stroke-width stroke-linecap stroke-linejoin stroke-miterlimit stroke-dasharray stroke-dashoffset stroke-opacity ' +
 'marker-start marker-mid marker-end clip-rule color-interpolation color-interpolation-filters color-rendering shape-rendering image-rendering ' +
 'pointer-events color-scheme print-color-adjust ruby-position math-depth math-style -webkit-font-smoothing -webkit-text-fill-color -webkit-text-stroke-color ' +
 '-webkit-text-stroke-width -webkit-text-security -webkit-locale -webkit-hyphenate-character -webkit-line-break -webkit-rtl-ordering -webkit-user-modify ' +
 '-webkit-text-emphasis-color -webkit-text-emphasis-position -webkit-text-emphasis-style -webkit-text-orientation -webkit-writing-mode -webkit-border-horizontal-spacing ' +
 '-webkit-border-vertical-spacing -webkit-print-color-adjust -webkit-tap-highlight-color text-spacing-trim').split(' ').forEach(function (n) { INHERITED[n] = 1; });

// 빼는 속성: 변수·움직임·입력·스크롤·페이지 나눔(그림에 안 보임) · backdrop-filter(SVG 그림 안에서는 흐림 자리가 둘레까지 번져 덮는다 — 10-26 측정, 그 요소 바탕색만 남김) + 논리 속성(-block-·-inline-, block-size·inline-size — 계산값은 같은 물리 속성 margin-top 등에 이미 있음)
var SKIP = /^(--|transition|animation|will-change$|backdrop-filter$|view-transition|view-timeline|scroll-(?!.*-gutter)|overscroll-|anchor-|position-(anchor|area|try|visibility)|timeline-|touch-action$|user-select$|-webkit-user-|resize$|speak$|app-region$|interactivity$|caret-|cursor$|reading-|break-|orphans$|widows$|page$)|^(block-size|inline-size|min-block-size|min-inline-size|max-block-size|max-inline-size)$|-(block|inline)(-(start|end))?(-(width|style|color|radius))?$|-(start-start|start-end|end-start|end-end)-radius$/;
function skipProp(name) { return SKIP.test(name); }
// 늘 쓰는 속성: 선 굵기는 선 모양이 none 이면 계산값이 기본값(0px)과 같아 빠지는데, 모양(solid 등)만 쓰면 굵기가 medium(3px)로 돌아간다(Tailwind preflight)
var ALWAYS = /^(border-(top|right|bottom|left)-width|outline-width|column-rule-width)$/;

function styleText(names, own, parent, dflt) {
  var out = [];
  for (var i = 0; i < names.length; i++) {
    var n = names[i], v = own[i];
    if (v == null || v === '' || SKIP.test(n)) continue;
    var write = ALWAYS.test(n) || (INHERITED[n] ? (!parent || parent[i] !== v) : (!dflt || dflt[i] !== v));
    if (write) out.push(n + ':' + v);
  }
  return out.join(';');
}

var URL_RE = /url\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|([^)'"\s]+))\s*\)/g;
function urlsIn(text, fn) {
  return String(text || '').replace(URL_RE, function (m, a, b, c) { return fn(a != null ? a : b != null ? b : c, m); });
}
function urls(text) {
  var seen = {}, out = [];
  urlsIn(text, function (u, m) { if (!/^data:/i.test(u) && !seen[u]) { seen[u] = 1; out.push(u); } return m; });
  return out;
}
function swapUrls(text, map) {
  return urlsIn(text, function (u, m) { return map && map[u] ? 'url("' + map[u] + '")' : m; });
}

function abs(u, base) { try { return new URL(u, base).href; } catch (e) { return null; } }
function imports(cssText, base) {
  var out = [], re = /@import\s+(?:url\(\s*)?["']?([^"')\s;]+)["']?\s*\)?[^;]*;/g, m;
  while ((m = re.exec(String(cssText || '')))) { var a = abs(m[1], base); if (a) out.push(a); }
  return out;
}
function unquote(v) { return String(v || '').trim().replace(/^["']|["']$/g, '').trim(); }
function decl(body, name) {
  var m = new RegExp('(?:^|[;{\\s])' + name + '\\s*:\\s*([^;}]+)', 'i').exec(body);
  return m ? m[1].trim() : '';
}
function fontFaces(cssText, base) {
  var out = [], re = /@font-face\s*\{([^}]*)\}/gi, m;
  while ((m = re.exec(String(cssText || '')))) {
    var body = m[1], src = [];
    decl(body, 'src').split(/,(?=(?:[^"']|"[^"]*"|'[^']*')*$)/).forEach(function (part) {
      var u = /url\(\s*["']?([^"')]+)["']?\s*\)/.exec(part), f = /format\(\s*["']?([^"')]+)["']?\s*\)/.exec(part);
      var a = u && abs(u[1], base);
      if (a) src.push({url: a, format: f ? f[1].toLowerCase() : ''});
    });
    out.push({family: unquote(decl(body, 'font-family')), weight: decl(body, 'font-weight') || '400',
              slant: decl(body, 'font-style') || 'normal', range: decl(body, 'unicode-range'), src: src});
  }
  return out;
}
function normWeight(w) {
  return String(w || '400').trim().toLowerCase().replace(/\bnormal\b/g, '400').replace(/\bbold\b/g, '700').split(/\s+/)
    .filter(function (x, i, a) { return a.indexOf(x) === i; }).join(' ');
}
function normSlant(s) { s = String(s || 'normal').trim().toLowerCase(); return /^oblique/.test(s) ? 'oblique' : s; }
function normRange(r) {
  r = String(r || '').trim();
  if (!r) return 'U+0-10FFFF';
  return r.split(',').map(function (p) {
    p = p.trim().toUpperCase().replace(/^U\+/, '');
    var ab = p.split('-'), lo, hi;
    if (ab.length === 2) { lo = parseInt(ab[0], 16); hi = parseInt(ab[1], 16); }
    else if (/\?/.test(p)) { lo = parseInt(p.replace(/\?/g, '0'), 16); hi = parseInt(p.replace(/\?/g, 'F'), 16); }
    else { lo = hi = parseInt(p, 16); }
    return 'U+' + lo.toString(16).toUpperCase() + (hi !== lo ? '-' + hi.toString(16).toUpperCase() : '');
  }).join(',');
}
function faceKey(f, slant) { return unquote(f.family).toLowerCase() + '|' + normWeight(f.weight) + '|' + normSlant(slant) + '|' + normRange(f.range); }
function usedFaces(faces, loaded) {
  var want = {}, seen = {};
  (loaded || []).forEach(function (l) { want[faceKey(l, l.slant)] = 1; });
  return (faces || []).filter(function (f) {
    var k = faceKey(f, f.slant);
    if (!want[k] || seen[k] || !f.src.length) return false;
    seen[k] = 1; return true;
  });
}
function faceCss(face, dataUrl) {
  return '@font-face{font-family:"' + face.family.replace(/"/g, '\\"') + '";font-weight:' + face.weight + ';font-style:' + face.slant +
    (face.range ? ';unicode-range:' + face.range : '') + ';src:url("' + dataUrl + '")}';
}

// 한 줄 글은 그림에서도 한 줄: SVG 그림 안 글자 너비가 라이브보다 조금 넓어 딱 맞는 칸(자리 고정된 auto 여백 옆)에서 줄이 바뀐다 → 라이브에서 한 줄이면 줄바꿈을 끈다
function oneLine(rects) {
  var r = (rects || []).filter(function (x) { return x && x.width > 0 && x.height > 0; });
  if (!r.length) return false;
  var top = r[0].top, bottom = r[0].top + r[0].height;
  return r.every(function (x) { var c = x.top + x.height / 2; return c > top && c < bottom; });
}

function clear(bg) { return !bg || /^(transparent|rgba\(0, 0, 0, 0\))$/.test(String(bg).trim()); }
function canvasBg(htmlBg, bodyBg) { return !clear(htmlBg) ? 'html' : !clear(bodyBg) ? 'body' : null; }

function svg(w, h, pw, ph, inner) {
  return '<svg xmlns="http://www.w3.org/2000/svg" width="' + pw + '" height="' + ph + '" viewBox="0 0 ' + w + ' ' + h + '">' +
    '<foreignObject x="0" y="0" width="' + w + '" height="' + h + '">' + inner + '</foreignObject></svg>';
}

function verdict(missing) {
  var lines = (missing || []).map(function (m) { return (m.kind || '?') + ' ' + (m.url || m.path || '') + ' — ' + (m.why || ''); });
  return {ok: !lines.length, lines: lines};
}

HD.snapshot = {MAX: 4096, MAX_ELEMENTS: 3000, BUDGET: 8, TIMEOUT: 5000, INHERITED: INHERITED,
               size: size, reach: reach, pickable: pickable, elementMap: elementMap, skipProp: skipProp, styleText: styleText,
               urls: urls, swapUrls: swapUrls, imports: imports, fontFaces: fontFaces, usedFaces: usedFaces, faceCss: faceCss,
               canvasBg: canvasBg, oneLine: oneLine, svg: svg, verdict: verdict};
})();
