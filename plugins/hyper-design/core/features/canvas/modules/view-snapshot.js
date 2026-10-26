/* View — 그림 카드(R18) 찍기 끝단: 같은 출처 카드 iframe 문서를 부모 페이지에서 복제 → 계산된 스타일·그림·글꼴을 안에 넣고 → SVG foreignObject → canvas → WebP/PNG, 요소 지도(palette.js 경로 + 카드 좌표 상자)와 함께. 규칙(크기·상한·고를 요소·스타일 줄이기·글꼴 고르기·판정)은 Model HD.snapshot.
   부모에서 도는 까닭: 같은 출처면 contentDocument 를 바로 읽고(palette.js·메시지 형식을 바꾸지 않음), 큰 그림을 postMessage 로 넘기지 않으며, 글꼴·그림 data URL 저장을 카드끼리 함께 쓴다(한 프로젝트 = 같은 글꼴 파일). 경로는 카드의 palette.js 가 내놓은 __hdRules.pathOf 그대로(hd-picked·hd-locate 와 같은 형식, 두 번째 형식을 만들지 않음).
   HD.viewSnapshot.capture(frame, {density 1|2, type 'image/webp'|'image/png', quality, max, timeout, strict, onImage(res)}) → Promise<{blob, type, w, h, density, scale, pw, ph, capped, elements:[{path, rect}], missing:[{kind, url|path, why}], ok, imageMs, ms, stages}>
     onImage = 그림이 나오자마자(요소 지도 경로를 채우기 전, elements 빈 채) 한 번 · stages = 단계별 ms(wait·walk·images·fonts·build·decode·draw·encode·map — 측정용)
     오류 탐지: 찍을 수 없으면 Error(code = 'unreachable'(다른 출처·file://) | 'unloaded' | 'loading' | 'size' | 'render'(SVG 그림이 안 그려짐) | 'tainted' | 'missing'(strict 이고 넣지 못한 자원)) 로 거절한다 — 빈 그림을 내지 않는다.
     넣지 못한 자원(그림·글꼴·CSS·iframe·canvas·video·안쪽 스크롤)은 missing 에 줄마다 남기고 ok=false + 콘솔 '[hd] snapshot' 경고 한 줄. palette.js 가 없으면 elements = [] + missing {kind:'map'}.
   HD.viewSnapshot.clearCache() — data URL 저장을 비움. 가진 상태: 주소 → data URL 약속 저장(이 모듈 하나), 태그 기본 스타일 저장(숨은 빈 iframe 하나). 아직 아무도 부르지 않는다(R18 1단계 — 판 동작 그대로). */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var S = HD.snapshot;
var dataCache = new Map(), textCache = new Map(), dflt = new Map(), sandbox = null, NAMES = null;

function fail(code, why) { var e = new Error('[hd] snapshot ' + code + ': ' + why); e.code = code; return e; }
function within(p, ms, what) {
  return Promise.race([p, new Promise(function (_, rej) { setTimeout(function () { rej(fail('timeout', what + ' ' + ms + 'ms')); }, ms); })]);
}
var chan = null, waiting = [];
function yieldNow() {                                  // 긴 일을 잘게 — setTimeout 은 겹치면 4ms 로 늦어져서 MessageChannel
  if (!chan) { chan = new MessageChannel(); chan.port1.onmessage = function () { var f = waiting.shift(); if (f) f(); }; }
  return new Promise(function (r) { waiting.push(r); chan.port2.postMessage(0); });
}
function blobData(b) {
  return new Promise(function (res, rej) { var fr = new FileReader(); fr.onload = function () { res(fr.result); }; fr.onerror = function () { rej(fr.error); }; fr.readAsDataURL(b); });
}
function toData(url) {
  if (/^data:/i.test(url)) return Promise.resolve(url);
  if (!dataCache.has(url)) {
    var p = fetch(url).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.blob(); }).then(blobData);
    p.catch(function () { dataCache.delete(url); });   // 실패는 저장하지 않는다(다음에 다시)
    dataCache.set(url, p);
  }
  return dataCache.get(url);
}
function fetchText(url) {
  if (!textCache.has(url)) {
    var p = fetch(url).then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); });
    p.catch(function () { textCache.delete(url); });
    textCache.set(url, p);
  }
  return textCache.get(url);
}

function defaults(el) {                                // 태그 기본 계산 스타일(스타일시트 없는 숨은 iframe) — 이어받지 않는 속성의 비교 기준
  var svgNs = el.namespaceURI === 'http://www.w3.org/2000/svg', key = (svgNs ? 'svg:' : '') + el.localName;
  if (dflt.has(key)) return dflt.get(key);
  if (!sandbox) {
    sandbox = document.createElement('iframe');
    sandbox.setAttribute('aria-hidden', 'true'); sandbox.tabIndex = -1;
    sandbox.style.cssText = 'position:fixed;left:-9999px;top:0;width:400px;height:400px;visibility:hidden;border:0';
    document.body.appendChild(sandbox);
    sandbox.contentDocument.open(); sandbox.contentDocument.write('<!doctype html><html><body></body></html>'); sandbox.contentDocument.close();
  }
  var d = sandbox.contentDocument, host = svgNs ? d.createElementNS('http://www.w3.org/2000/svg', 'svg') : d.body;
  if (svgNs) d.body.appendChild(host);
  var e = svgNs ? d.createElementNS('http://www.w3.org/2000/svg', el.localName) : d.createElement(el.localName);
  host.appendChild(e);
  var cs = sandbox.contentWindow.getComputedStyle(e), vals = NAMES.map(function (n) { return cs.getPropertyValue(n); });
  (svgNs ? host : e).remove();
  dflt.set(key, vals);
  return vals;
}
function values(cs) { var v = new Array(NAMES.length); for (var i = 0; i < NAMES.length; i++) v[i] = cs.getPropertyValue(NAMES[i]); return v; }

async function sheetFaces(sheet, base, faces, missing, depth) {
  var rules = null;
  try { rules = sheet.cssRules; } catch (e) { rules = null; }   // 다른 출처 스타일시트(@import 등)는 규칙을 못 읽는다 → 글로 다시 받는다
  if (!rules) {
    if (!sheet.href) return;
    await cssTextFaces(sheet.href, faces, missing, depth);
    return;
  }
  for (var i = 0; i < rules.length; i++) {
    var r = rules[i], b = sheet.href || base;
    if (r.type === 3 && r.styleSheet) await sheetFaces(r.styleSheet, absUrl(r.href, b) || b, faces, missing, depth + 1);   // @import
    else if (r.type === 5) S.fontFaces(r.cssText, b).forEach(function (f) { faces.push(f); });
    else if (r.cssRules) await sheetFaces({cssRules: r.cssRules, href: sheet.href}, b, faces, missing, depth);
  }
}
async function cssTextFaces(url, faces, missing, depth) {
  if (depth > 4) return;
  var text;
  try { text = await fetchText(url); } catch (e) { missing.push({kind: 'css', url: url, why: '스타일시트를 받지 못함(' + e.message + ') — 그 안 글꼴이 빠질 수 있다'}); return; }
  S.fontFaces(text, url).forEach(function (f) { faces.push(f); });
  for (var u of S.imports(text, url)) await cssTextFaces(u, faces, missing, depth + 1);
}
async function fontCss(doc, missing) {
  var loaded = [];
  doc.fonts.forEach(function (f) { if (f.status === 'loaded') loaded.push({family: f.family, weight: f.weight, slant: f.style, range: f.unicodeRange}); });
  if (!loaded.length) return '';
  var faces = [];
  for (var i = 0; i < doc.styleSheets.length; i++) await sheetFaces(doc.styleSheets[i], doc.baseURI, faces, missing, 0);
  var used = S.usedFaces(faces, loaded);
  var found = {}; used.forEach(function (f) { found[f.family.toLowerCase()] = 1; });
  loaded.forEach(function (l) {
    var fam = String(l.family).replace(/^["']|["']$/g, '');
    if (!found[fam.toLowerCase()]) { found[fam.toLowerCase()] = 1; missing.push({kind: 'font', url: fam, why: '실린 글꼴의 @font-face 원본을 찾지 못함(스크립트로 만든 글꼴?) — 대체 글꼴로 그려진다'}); }
  });
  var css = await Promise.all(used.map(function (f) {
    var src = f.src.filter(function (s) { return s.format === 'woff2'; })[0] || f.src[0];
    return toData(src.url).then(function (d) { return S.faceCss(f, d); },
      function (e) { missing.push({kind: 'font', url: src.url, why: '글꼴 파일을 받지 못함(' + e.message + ')'}); return ''; });
  }));
  return css.join('');
}

async function waitReady(doc, win, timeout, missing) {
  try { await within(doc.fonts.ready, timeout, '글꼴'); } catch (e) { missing.push({kind: 'font', url: '', why: '글꼴이 ' + timeout + 'ms 안에 실리지 않음'}); }
  var imgs = Array.prototype.filter.call(doc.images, function (im) { return im.loading !== 'lazy' || im.complete; });
  await Promise.all(imgs.map(function (im) {
    if (im.complete && im.naturalWidth) return im.decode().catch(function () {});
    return within(im.decode(), timeout, '그림').catch(function (e) { missing.push({kind: 'image', url: im.currentSrc || im.src, why: '그림이 실리지 않음(' + (e.message || e) + ')'}); });
  }));
  await new Promise(function (r) { var t = setTimeout(r, 100); win.requestAnimationFrame(function () { win.requestAnimationFrame(function () { clearTimeout(t); r(); }); }); });   // 두 프레임 — 마지막 배치까지(가려진 iframe 은 프레임이 멈출 수 있어 100ms 상한)
}

function ownText(el) { for (var c = el.firstChild; c; c = c.nextSibling) if (c.nodeType === 3 && c.nodeValue.trim()) return true; return false; }
function absUrl(u, base) { if (!u) return null; try { return new URL(u, base).href; } catch (e) { return null; } }   // 깨진 주소 = 넣지 않음(그 그림은 원래도 안 보임)
function textRects(doc, el) {                         // 요소 안 글 마디들의 줄 상자(그림·아이콘 상자는 빼고 글만)
  var out = [], w = doc.createTreeWalker(el, 4), n, rg = doc.createRange();
  while ((n = w.nextNode())) { if (!n.nodeValue.trim()) continue; rg.selectNodeContents(n); Array.prototype.push.apply(out, Array.prototype.slice.call(rg.getClientRects())); }
  return out;
}
var DROP = /^(script|noscript|template|link|meta|style|title|base|head)$/;
async function capture(frame, opt) {
  opt = opt || {};
  var t0 = performance.now(), missing = [], timeout = opt.timeout > 0 ? opt.timeout : S.TIMEOUT;
  var doc = null, win = null;
  try { win = frame.contentWindow; doc = frame.contentDocument; if (doc) void doc.documentElement; } catch (e) { doc = null; }
  var bad = S.reach({doc: !!(doc && doc.documentElement), frameSrc: frame.getAttribute('src') || '', href: doc ? doc.URL : '', ready: doc ? doc.readyState : '', protocol: location.protocol});
  if (bad) throw fail(bad.code, bad.why);
  var sz = S.size(win.innerWidth, win.innerHeight, opt.density, opt.max);
  if (sz.error) throw fail('size', '카드 크기가 0');
  var st = {}, mark = performance.now();
  function lap(k) { var n = performance.now(); st[k] = Math.round(n - mark); mark = n; }
  await waitReady(doc, win, timeout, missing); lap('wait');

  var root = doc.documentElement, body = doc.body;
  if (!NAMES) { var c0 = win.getComputedStyle(root); NAMES = Array.prototype.filter.call(c0, function (n) { return !S.skipProp(n); }); }
  var copy = root.cloneNode(true);
  var origs = [root].concat(Array.prototype.slice.call(root.querySelectorAll('*')));
  var clones = [copy].concat(Array.prototype.slice.call(copy.querySelectorAll('*')));
  if (origs.length !== clones.length) throw fail('render', '복제 차례가 원본과 다르다');
  var rules = win.__hdRules, vals = new Map(), styles = new Array(origs.length), urlSet = new Set(), pseudo = [], items = [], drop = [];
  var sliceAt = performance.now(), budget = S.BUDGET, hasRules = !!(rules && rules.pathOf);
  if (!hasRules) missing.push({kind: 'map', path: '', why: '카드에 palette.js(__hdRules)가 없어 요소 지도를 만들 수 없다'});
  for (var i = 0; i < origs.length; i++) {
    if (performance.now() - sliceAt > budget) { await yieldNow(); sliceAt = performance.now(); }
    var el = origs[i], cl = clones[i], tag = el.localName;
    if (DROP.test(tag) || el.hasAttribute('data-hd-pick') || el.hasAttribute('data-hd-links')) { drop.push(cl); continue; }
    var cs = win.getComputedStyle(el), own = values(cs);
    vals.set(el, own);
    var parentVals = el === root ? null : vals.get(el.parentElement) || null;
    var text = S.styleText(NAMES, own, parentVals, defaults(el));
    S.urls(text).forEach(function (u) { urlSet.add(u); });
    if (ownText(el) && S.oneLine(textRects(doc, el))) text += (text ? ';' : '') + 'text-wrap-mode:nowrap';
    styles[i] = text;
    ['::before', '::after'].forEach(function (ps) {
      var pc = win.getComputedStyle(el, ps), ct = pc.getPropertyValue('content');
      if (!ct || ct === 'none' || ct === 'normal') return;
      var pt = S.styleText(NAMES, values(pc), own, defaults({localName: 'span', namespaceURI: ''}));
      S.urls(pt).forEach(function (u) { urlSet.add(u); });
      pseudo.push({i: i, ps: ps, text: pt});
    });
    if (tag === 'img') { var src = el.currentSrc || el.src; if (src) urlSet.add(src); }
    else if (tag === 'image') { var h = absUrl(el.getAttribute('href') || el.getAttribute('xlink:href'), doc.baseURI); if (h) urlSet.add(h); }
    if (hasRules && el !== root && el !== body) {
      var r = el.getBoundingClientRect(), hidden = own[NAMES.indexOf('display')] === 'none' || own[NAMES.indexOf('visibility')] === 'hidden';
      if (S.pickable({tag: tag, hd: el.hasAttribute('data-hd-dup'), w: r.width, h: r.height, hidden: hidden, x: r.left, y: r.top, vw: sz.w, vh: sz.h}))
        items.push({el: el, rect: {x: r.left, y: r.top, w: r.width, h: r.height}});   // 상자는 지금(그림과 같은 순간), 경로는 그림 뒤에(palette.js pathOf 가 요소마다 문서를 훑어 느림)
    }
  }

  lap('walk');
  var map = {}, urlList = Array.from(urlSet);
  await Promise.all(urlList.map(function (u) {
    return toData(u).then(function (d) { map[u] = d; }, function (e) { missing.push({kind: 'image', url: u, why: '그림을 넣지 못함(' + e.message + ') — 다른 출처면 CORS 가 필요'}); });
  }));
  lap('images');
  var fonts = await fontCss(doc, missing); lap('fonts');

  var pcss = '';
  for (var k = 0; k < origs.length; k++) {
    if (styles[k] == null) continue;
    var o = origs[k], c = clones[k], tg = o.localName;
    c.setAttribute('style', S.swapUrls(styles[k], map));
    if (tg === 'img') { var s2 = o.currentSrc || o.src; c.removeAttribute('srcset'); c.removeAttribute('sizes'); c.removeAttribute('loading'); if (map[s2]) c.setAttribute('src', map[s2]); }
    else if (tg === 'image') { var h2 = absUrl(o.getAttribute('href') || o.getAttribute('xlink:href'), doc.baseURI); if (h2 && map[h2]) { c.setAttribute('href', map[h2]); c.removeAttribute('xlink:href'); } }
    else if (tg === 'source' && o.parentElement && o.parentElement.localName === 'picture') drop.push(c);
    else if (tg === 'input') { if (o.type === 'checkbox' || o.type === 'radio') { if (o.checked) c.setAttribute('checked', ''); else c.removeAttribute('checked'); } else c.setAttribute('value', o.value); }
    else if (tg === 'textarea') c.textContent = o.value;
    else if (tg === 'select') Array.prototype.forEach.call(c.options, function (op, j) { if (o.options[j] && o.options[j].selected) op.setAttribute('selected', ''); else op.removeAttribute('selected'); });
    else if (tg === 'canvas') {
      var im = doc.createElement('img');
      try { im.src = o.toDataURL(); } catch (e) { missing.push({kind: 'canvas', path: hasRules ? rules.pathOf(o) : 'canvas', why: '다른 출처 그림이 든 canvas 라 읽을 수 없다'}); }
      im.setAttribute('style', c.getAttribute('style')); c.replaceWith(im);
    } else if (tg === 'iframe' || tg === 'video' || tg === 'object' || tg === 'embed') {
      var box = doc.createElement('div'); box.setAttribute('style', c.getAttribute('style')); c.replaceWith(box);
      missing.push({kind: tg, path: hasRules ? rules.pathOf(o) : tg, why: tg + ' 안 내용은 그림에 넣지 않는다(빈 상자)'});
    }
    if (o.scrollTop || o.scrollLeft) {
      if (o !== root && o !== body) missing.push({kind: 'scroll', path: hasRules ? rules.pathOf(o) : tg, why: '안쪽 스크롤 자리는 그림에서 맨 위로 보인다'});
    }
    c.removeAttribute('class');
  }
  pseudo.forEach(function (p, n) { var c = clones[p.i]; c.setAttribute('data-hd-snap', String(n)); pcss += '[data-hd-snap="' + n + '"]' + p.ps + '{' + S.swapUrls(p.text, map) + '}'; });
  drop.forEach(function (c) { if (c !== copy && c.parentNode) c.parentNode.removeChild(c); });
  if (frame.isConnected === false) throw fail('unloaded', '찍는 동안 카드가 내려졌다');

  var which = S.canvasBg(win.getComputedStyle(root).backgroundColor, body ? win.getComputedStyle(body).backgroundColor : '');
  var bgEl = which === 'html' ? root : which === 'body' ? body : null, bg = '';
  if (bgEl) { var bc = win.getComputedStyle(bgEl); bg = 'background-color:' + bc.backgroundColor + ';'; }
  var sx = win.scrollX || 0, sy = win.scrollY || 0;
  var inner = '<div xmlns="http://www.w3.org/1999/xhtml" style="position:relative;overflow:hidden;width:' + sz.w + 'px;height:' + sz.h + 'px;' + bg + '">' +
    '<style>' + fonts + pcss + '</style>' +
    '<div style="position:absolute;left:0;top:0;width:' + sz.w + 'px;' + (sx || sy ? 'transform:translate(' + (-sx) + 'px,' + (-sy) + 'px);' : '') + '">' +
    new XMLSerializer().serializeToString(copy) + '</div></div>';
  var svgText = S.svg(sz.w, sz.h, sz.pw, sz.ph, inner); lap('build');
  await yieldNow();

  var img = new Image();                              // data: 주소 — blob: SVG 는 Chromium 이 foreignObject 를 이유로 canvas 를 더럽힌다(꺼낼 수 없음, 10-26 측정)
  try { img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgText); await img.decode(); } catch (e) { throw fail('render', 'SVG 그림이 그려지지 않음(' + (e.message || e) + ')'); }
  lap('decode');
  var cv = document.createElement('canvas'); cv.width = sz.pw; cv.height = sz.ph;
  var cx = cv.getContext('2d');
  cx.drawImage(img, 0, 0, sz.pw, sz.ph); lap('draw');
  var type = opt.type === 'image/png' ? 'image/png' : 'image/webp', blob;
  try { blob = await new Promise(function (res) { cv.toBlob(res, type, opt.quality > 0 ? opt.quality : 0.92); }); }
  catch (e) { throw fail('tainted', '그림을 꺼낼 수 없다(' + e.message + ')'); }
  if (!blob) throw fail('render', '그림 인코딩 실패');
  lap('encode'); st.svgKb = Math.round(svgText.length / 1024);

  var out = {blob: blob, type: blob.type || type, w: sz.w, h: sz.h, density: sz.density, scale: sz.scale, pw: sz.pw, ph: sz.ph, capped: sz.capped,
             elements: [], missing: missing, ok: false, imageMs: Math.round(performance.now() - t0), stages: st};
  if (typeof opt.onImage === 'function') { try { opt.onImage(out); } catch (e) { console.error('[hd] snapshot onImage', e); } }
  sliceAt = performance.now();
  for (var q = 0; q < items.length; q++) {                 // 요소 지도 경로 — 카드의 palette.js 규칙 그대로, 잘게 나눠(긴 일 없게)
    if (performance.now() - sliceAt > budget) { await yieldNow(); sliceAt = performance.now(); }
    items[q] = {path: items[q].el.isConnected ? rules.pathOf(items[q].el) : null, rect: items[q].rect};
  }
  lap('map');
  out.elements = S.elementMap(items);
  var v = S.verdict(missing);
  if (!v.ok) console.warn('[hd] snapshot: 넣지 못한 것 ' + v.lines.length + '개 — ' + v.lines.slice(0, 3).join(' · '));
  if (!v.ok && opt.strict) throw fail('missing', v.lines.join(' · '));
  out.ok = v.ok; out.ms = Math.round(performance.now() - t0);
  return out;
}

function clearCache() { dataCache.clear(); textCache.clear(); }

HD.viewSnapshot = {capture: capture, clearCache: clearCache};
})();
