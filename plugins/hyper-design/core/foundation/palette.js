/* 원클릭 팔레트 교체 — 화면은 <link id="tokens" href="tokens.css"> 하나만 바꾼다.
   캔버스가 postMessage({type:'hd-palette', slug})를 보내거나, 마지막 선택(localStorage)·?p= 를 따른다.
   {type:'hd-theme-vars', vars:{'--c-brand': '#RRGGBB', …}} 는 캔버스 '내 테마' 색 네 칸 덮어쓰기({} 이면 지움).
   요소 고르기(캔버스 크게 보기): {type:'hd-pick', on} 을 받으면 마우스 올린 요소에 테두리를 그리고
   {type:'hd-hover', rect} / 클릭 시 {type:'hd-picked', screen, path, text, rect, add} 를 부모에게 보낸다(add = Shift 로 여러 개 고르기).
   연결 보기: {type:'hd-links', on:true} 를 받으면 다른 화면으로 가는 링크 목록을
   {type:'hd-links', screen, accent, docHeight, links:[{to, path, text, rect}]} 로 답하고(docHeight = 화면 전체 높이),
   {type:'hd-links-paint', items:[{path, color, n}]} 로 그 요소들에 색 테두리·번호를 그린다(items:[] 이면 지움).
   한 요소에 쌍이 여럿이면 테두리를 3px 간격 동심으로 겹친다.
   어디로 가나(Ctrl/Cmd+클릭): 링크 요소를 Ctrl/Cmd+클릭하면 이동하지 않고 {type:'hd-link-go', screen, to, path, rect} 를 보낸다.
   캔버스가 {type:'hd-link-at', x, y} 를 보내면 그 자리의 링크로 같은 답을 보낸다(링크가 없으면 to:null). 그냥 클릭은 그대로.
   편집(트리거·도착 바꾸기): {type:'hd-hit-at', x, y} 를 받으면 그 자리의 요소(링크 → 누를 수 있는 요소 → 그 요소 순)로
   {type:'hd-hit', screen, path, text, full, rect, to, kind} 를 보낸다(to = 지금 가는 화면 id 또는 null, full = 고칠 글 전체,
   kind = link·button·field·text·box — 캔버스가 종류별 테두리를 그린다, 요소가 없으면 path:null).
   leaf:true 면 그 자리 요소 그대로(글자 고치기).
   반영 대기 미리보기: {type:'hd-pending', items:[{path, text} | {path, remove:true}]} 를 받으면 그 요소 안 내용 전부(글 + 인라인 자식)를 잠시 새 글로(\n = 줄바꿈, '' = 비움)
   바꿔 점선으로, remove 는 그 요소를 숨겨 보여 준다(items:[] 이면 되돌린다). 글 바꾸기 규칙은 helper.py edit_html 과 같다: 안에 인라인(글 있는 b·span…, br) 아닌
   자식이 있으면 바꾸지 않는다 — hd-hit·hd-dbl 답의 textOk 가 그 판정(false = 글자만 바꿀 수 없음).
   불러올 때 {type:'hd-here', screen} 을 보낸다 — 크게 보기 안에서 다른 화면으로 넘어가도 캔버스가 지금 화면을 안다.
   글자 고치기(크게 보기): {type:'hd-edit', on} 을 받으면 두 번 누른 글자 요소를 {type:'hd-dbl', …hd-hit 과 같은 칸} 으로 보낸다.
   메모 자리(W3C Web Annotation 처럼 선택자 여럿): hd-picked·hd-hit 답에 quote:{exact, prefix, suffix} — 요소 글(≤200자)과 문서 글에서 그 앞·뒤 32자.
   다시 찾기: {type:'hd-locate', items:[{key, path, quote}]} → {type:'hd-located', items:[{key, rect|null, how}]} — path 가 있고(quote 가 없거나 그 요소 글에 quote.exact 가 있음) = 'path',
   아니면 문서 글에서 quote.exact 를 찾아(앞·뒤 글이 맞는 곳 먼저) 그 글을 감싼 가장 작은 요소 = 'quote', 못 찾으면 'none'(rect:null).
   소스 위치(앱 카드, Svelte 개발 서버): 요소나 그 조상에 __svelte_meta.loc 이 있으면 hd-picked·hd-hit·hd-dbl 답과 hd-located 항목에
   src:{file, line, column}(window.__hdSrc = {root, base} 가 있으면 저장소 기준 경로) · comp:[안쪽 컴포넌트부터] 를 더한다. 없으면 두 칸 모두 없다.
   판 모드(?hd-mode=board — 캔버스 판 위 카드만, 크게 보기는 아님): 화면 스크립트보다 먼저 reduced-motion 을 켜고 움직임을 멈춘다
   (유한 = 끝 상태, 무한 = 한 번 뒤 멈춤 · load 뒤 WAAPI 도). contract/board-motion.md */
(function () {
  if (new URLSearchParams(location.search).get('hd-mode') !== 'board') return;
  var mm = window.matchMedia;
  if (mm) window.matchMedia = function (q) {        // 앱의 reduced-motion 경로를 켠다(다른 질의는 그대로)
    var m = /prefers-reduced-motion\s*:\s*(reduce|no-preference)/.exec(String(q));
    return mm.call(window, m ? (m[1] === 'reduce' ? 'all' : 'not all') : q);
  };
  var st = document.createElement('style'); st.setAttribute('data-hd-board', '');
  st.textContent = '*,*::before,*::after{transition-duration:0s!important;transition-delay:0s!important;animation-duration:1ms!important;' +
    'animation-delay:-1ms!important;animation-iteration-count:1!important}';
  (document.head || document.documentElement).appendChild(st);
  function still() {
    if (!document.getAnimations) return;
    document.getAnimations().forEach(function (a) {
      try { var t = a.effect && a.effect.getComputedTiming(); if (t && t.endTime === Infinity) a.pause(); else a.finish(); }
      catch (e) { console.warn('[hd] 판 모드: 움직임을 멈추지 못함 — ' + e); }
    });
  }
  addEventListener('load', function () { still(); setTimeout(still, 500); });   // 늦게 붙는 컴포넌트까지 한 번 더
})();
(function () {
  var KEY = 'hd-palette';
  function apply(slug) {
    var l = document.getElementById('tokens'); if (!l || !slug) return;
    var base = l.getAttribute('data-base') || l.getAttribute('href'); l.setAttribute('data-base', base);
    l.setAttribute('href', base.replace(/tokens(-[^/]*)?\.css$/, 'tokens-' + slug + '.css'));
  }
  var setVars = [];                                   // 캔버스 내 테마: 색 네 칸을 :root 변수로 덮어쓴다({} 이면 지움)
  function themeVars(v) {
    var st = document.documentElement.style;
    setVars.forEach(function (k) { st.removeProperty(k); }); setVars = [];
    Object.keys(v).forEach(function (k) { if (/^--c-[a-z0-9-]+$/.test(k) && /^#[0-9a-f]{6}$/i.test(v[k])) { st.setProperty(k, v[k]); setVars.push(k); } });
  }
  var s = new URLSearchParams(location.search).get('p');
  try { s = s || localStorage.getItem(KEY); } catch (e) {}
  if (s) apply(s);

  /* ---------- 요소 고르기 ---------- */
  var picking = false, box = null, last = null;
  function send(msg) { try { if (window.parent && window.parent !== window) window.parent.postMessage(msg, '*'); } catch (e) {} }
  function rectOf(el) { var r = el.getBoundingClientRect(); return {x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)}; }
  function cssEsc(v) { return window.CSS && CSS.escape ? CSS.escape(v) : String(v).replace(/[^\w-]/g, '\\$&'); }
  /* 요소 경로 규칙(helper.py SEG·select 와 같은 것, 공유 fixture canvas/tests/fixtures/paths.json): 조각 ' > ' 조각(자식 관계)만,
     조각 = #id | tag[data-region="…"] | tag(.첫class)?(:nth-of-type(n))? | body. .cls 는 첫 class 만 본다(CSS 의 '아무 class' 아님).
     여럿이 맞으면 고르지 않는다(querySelector 처럼 첫 것을 잡으면 미리보기와 도우미 편집이 다른 요소를 본다). */
  var SEG = /^(?:#(.+)|([a-zA-Z][\w-]*)(?:\[data-region="((?:[^"\\]|\\.)*)"\]|(?:\.((?:[^:\\]|\\.)+))?(?::nth-of-type\((\d+)\))?))$/;
  function unesc(v) { return v.replace(/\\([0-9a-fA-F]{1,6}) ?/g, function (m, h) { return String.fromCodePoint(parseInt(h, 16)); }).replace(/\\(.)/g, '$1'); }
  function segOk(n, seg) {
    if (seg === 'body') return n.localName.toLowerCase() === 'body';
    var m = SEG.exec(seg);
    if (m[1] != null) return n.getAttribute('id') === unesc(m[1]);
    if (n.localName.toLowerCase() !== m[2].toLowerCase()) return false;
    if (m[3] != null) return n.getAttribute('data-region') === m[3].replace(/\\"/g, '"');
    if (m[4] != null && ((n.getAttribute('class') || '').trim().split(/\s+/)[0] || '') !== unesc(m[4])) return false;
    if (m[5] != null) {
      var i = 1, p = n.previousElementSibling;
      for (; p; p = p.previousElementSibling) if (p.localName === n.localName) i++;
      if (i !== +m[5]) return false;
    }
    return true;
  }
  function match(path) {                              // 경로에 맞는 요소 전부(문서 차례) — 모르는 조각이면 []
    var segs = String(path || '').split(' > ').map(function (x) { return x.trim(); }).filter(Boolean);
    if (!segs.length || !segs.every(function (x) { return x === 'body' || SEG.test(x); })) return [];
    return Array.prototype.filter.call(document.getElementsByTagName('*'), function (el) {
      var cur = el;
      for (var k = segs.length - 1; k >= 0; k--, cur = cur.parentNode) if (!cur || cur.nodeType !== 1 || !segOk(cur, segs[k])) return false;
      return true;
    });
  }
  function find(path) { var m = match(path); return m.length === 1 ? m[0] : null; }   // 하나만 맞을 때만
  function pathOf(el) {
    var segs = [], n = el;
    while (n && n.nodeType === 1 && n !== document.body && n !== document.documentElement) {
      var tag = n.tagName.toLowerCase();
      if (n.id) { segs.unshift('#' + cssEsc(n.id)); break; }
      var reg = n.getAttribute('data-region');
      if (reg != null) { segs.unshift(tag + '[data-region="' + reg.replace(/"/g, '\\"') + '"]'); break; }
      var cls = (n.getAttribute('class') || '').trim().split(/\s+/)[0];
      var i = 1, p = n.previousElementSibling;
      for (; p; p = p.previousElementSibling) if (p.tagName === n.tagName) i++;
      segs.unshift(tag + (cls ? '.' + cssEsc(cls) : '') + ':nth-of-type(' + i + ')');
      n = n.parentElement;
    }
    if (!segs.length) return 'body';
    for (var k = 1; k <= segs.length; k++) {           // 끝에서부터 가장 짧은 유일한 경로
      var sel = segs.slice(segs.length - k).join(' > ');
      if (find(sel) === el) return sel;
    }
    var full = segs.join(' > ');
    return segs[0].charAt(0) === '#' || segs[0].indexOf('[data-region') > 0 ? full : 'body > ' + full;
  }
  function textOf(el) {
    var t = el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('alt') || '';
    return String(t).replace(/\s+/g, ' ').trim().slice(0, 60);
  }
  /* 문서 글: 글 마디를 차례로 이어 붙인 한 줄(공백은 하나로) + 마디마다 시작·끝 자리 — quote 를 만들고 다시 찾는 데 같이 쓴다 */
  var SKIP = {SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEMPLATE: 1};
  function docText() {
    var t = '', nodes = [], root = document.body; if (!root) return {t: t, nodes: nodes};
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: function (n) {
      for (var p = n.parentElement; p && p !== root; p = p.parentElement) if (SKIP[p.tagName] || p.hasAttribute('data-hd-links') || p.hasAttribute('data-hd-pick')) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }}), n;
    while ((n = w.nextNode())) {
      var v = n.nodeValue.replace(/\s+/g, ' ');
      if (!v || v === ' ' && (!t || t.charAt(t.length - 1) === ' ')) continue;
      if (v.charAt(0) === ' ' && t.charAt(t.length - 1) === ' ') v = v.slice(1);
      nodes.push({n: n, s: t.length, e: t.length + v.length}); t += v;
    }
    return {t: t, nodes: nodes};
  }
  function spanOf(el, d) {                            // 그 요소 글이 문서 글에서 차지하는 [s, e)(앞뒤 공백 뺌)
    var s = -1, e = -1;
    d.nodes.forEach(function (x) { if (el.contains(x.n)) { if (s < 0) s = x.s; e = x.e; } });
    if (s < 0) return null;
    while (s < e && d.t.charAt(s) === ' ') s++;
    while (e > s && d.t.charAt(e - 1) === ' ') e--;
    return {s: s, e: e};
  }
  function quoteOf(el, d) {
    d = d || docText();
    var sp = el && spanOf(el, d); if (!sp || sp.e <= sp.s) return {exact: '', prefix: '', suffix: ''};
    var e = Math.min(sp.e, sp.s + 200);
    return {exact: d.t.slice(sp.s, e), prefix: d.t.slice(Math.max(0, sp.s - 32), sp.s), suffix: d.t.slice(e, e + 32)};
  }
  function common(a, b, fromEnd) {                    // 앞(또는 끝)부터 같은 글자 수
    var k = 0, n = Math.min(a.length, b.length);
    while (k < n && (fromEnd ? a.charAt(a.length - 1 - k) === b.charAt(b.length - 1 - k) : a.charAt(k) === b.charAt(k))) k++;
    return k;
  }
  function locateOne(it, d) {
    var q = it.quote && it.quote.exact ? String(it.quote.exact) : '', el = null;
    el = it.path ? find(it.path) : null;
    if (el && el !== document.body && el !== document.documentElement) {
      var sp = q ? spanOf(el, d) : null;
      if (!q || (sp && d.t.slice(sp.s, sp.e).indexOf(q) >= 0)) return withSrc({key: it.key, rect: rectOf(el), how: 'path'}, el);
    }
    if (!q) return {key: it.key, rect: null, how: 'none'};
    var best = -1, score = -1, at = d.t.indexOf(q), pre = String(it.quote.prefix || ''), suf = String(it.quote.suffix || '');
    while (at >= 0) {                                 // 같은 글이 여럿이면 앞·뒤 글이 가장 많이 맞는 곳
      var sc = common(d.t.slice(Math.max(0, at - pre.length), at), pre, true) + common(d.t.slice(at + q.length, at + q.length + suf.length), suf, false);
      if (sc > score) { score = sc; best = at; }
      at = d.t.indexOf(q, at + 1);
    }
    if (best < 0) return {key: it.key, rect: null, how: 'none'};
    var hit = d.nodes.filter(function (x) { return x.e > best && x.s < best + q.length; });
    var box = hit[0].n.parentElement;                 // 그 글을 모두 감싼 가장 작은 요소
    while (box && box !== document.body && !hit.every(function (x) { return box.contains(x.n); })) box = box.parentElement;
    if (!box || box === document.body) return {key: it.key, rect: null, how: 'none'};
    return withSrc({key: it.key, rect: rectOf(box), how: 'quote'}, box);
  }
  function locate(items) {
    var d = docText();
    send({type: 'hd-located', screen: screenId(), items: (items || []).map(function (it) { return locateOne(it || {}, d); })});
  }
  /* 소스 위치: 가장 가까운 __svelte_meta.loc(Svelte 5 개발 런타임, 비공개 API) → {src, comp} | null */
  function srcPath(f) {
    f = slash(f); var cfg = window.__hdSrc || null; if (!cfg) return f;
    var root = slash(cfg.root).replace(/\/+$/, ''), base = slash(cfg.base).replace(/^\/+|\/+$/g, '');
    if (root && f.toLowerCase().indexOf(root.toLowerCase() + '/') === 0) return f.slice(root.length + 1);
    if (/^([a-z]:)?\//i.test(f)) return f;              // 저장소 밖 절대 경로는 그대로
    return (base ? base + '/' : '') + f.replace(/^\.\//, '');
  }
  function slash(f) { return String(f || '').split(String.fromCharCode(92)).join('/'); }   // 역슬래시 → '/'
  function baseName(f) { return slash(f).split('/').pop().replace(/\.svelte$/i, ''); }
  function srcOf(el) {
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      var m = n.__svelte_meta, loc = m && m.loc;
      if (!loc || !loc.file) continue;
      var comp = [baseName(loc.file)];
      for (var s = m.parent, k = 0; s && k < 50; s = s.parent, k++) {
        if (s.type === 'component' && s.file) { var c = baseName(s.file); if (c && c !== comp[comp.length - 1]) comp.push(c); }
      }
      return {src: {file: srcPath(loc.file), line: +loc.line || 0, column: +loc.column || 0}, comp: comp.slice(0, 8)};
    }
    return null;
  }
  function withSrc(msg, el) { var s = el ? srcOf(el) : null; if (s) { msg.src = s.src; msg.comp = s.comp; } return msg; }
  window.__hdSrcOf = srcOf;                           // 테스트·디버그용(읽기만)
  function screenId() {
    var f = decodeURIComponent(location.pathname.split('/').pop() || '');
    return f.replace(/\.html?$/i, '');
  }
  function showBox(el) {
    if (!box) {
      box = document.createElement('div');
      box.setAttribute('data-hd-pick', '');
      box.style.cssText = 'position:fixed;z-index:2147483647;pointer-events:none;border:2px solid #2563eb;background:rgba(37,99,235,.10);border-radius:4px;display:none';
      document.documentElement.appendChild(box);
    }
    var r = rectOf(el);
    box.style.left = r.x + 'px'; box.style.top = r.y + 'px'; box.style.width = r.w + 'px'; box.style.height = r.h + 'px';
    box.style.display = 'block';
    return r;
  }
  function target(e) { var t = e.target; return t && t.nodeType === 1 && t !== box ? t : null; }
  document.addEventListener('mousemove', function (e) {
    if (!picking) return;
    var t = target(e); if (!t || t === last) return;
    last = t; send({type: 'hd-hover', rect: showBox(t)});
  }, true);
  function block(e) { if (!picking) return; e.preventDefault(); e.stopPropagation(); if (e.stopImmediatePropagation) e.stopImmediatePropagation(); }
  ['mousedown', 'mouseup', 'pointerdown', 'pointerup', 'submit', 'dblclick'].forEach(function (ev) { document.addEventListener(ev, block, true); });
  document.addEventListener('click', function (e) {
    if (!picking) return;
    block(e);
    var t = target(e); if (!t) return;
    send(withSrc({type: 'hd-picked', screen: screenId(), path: pathOf(t), text: textOf(t), rect: showBox(t), quote: quoteOf(t), add: !!e.shiftKey}, t));
  }, true);

  /* ---------- 연결 보기: 다른 화면으로 가는 링크 ---------- */
  function hex(v) {
    v = String(v || '').trim(); if (!v) return '';
    var t = document.createElement('i'); t.style.color = v; document.documentElement.appendChild(t);
    var c = getComputedStyle(t).color; t.remove();
    var m = c.match(/\d+(\.\d+)?/g); if (!m || m.length < 3) return '';
    return '#' + m.slice(0, 3).map(function (x) { return ('0' + Math.round(+x).toString(16)).slice(-2); }).join('');
  }
  function accent() {
    var cs = getComputedStyle(document.documentElement);
    var names = ['--c-brand', '--c-accent', '--c-primary', '--primary', '--accent'];
    for (var i = 0; i < names.length; i++) { var v = hex(cs.getPropertyValue(names[i])); if (v) return v; }
    return '';
  }
  function hrefOf(el) {
    var h = el.getAttribute('href') || el.getAttribute('data-href');
    if (!h) { var m = (el.getAttribute('onclick') || '').match(/['"]([^'"]+\.html?)(?:[?#][^'"]*)?['"]/i); h = m && m[1]; }
    return h;
  }
  var LINK_SEL = 'a[href], [data-href], [onclick]';
  function linkTo(h, here) {                          // 링크 주소 → here 와 같은 폴더의 화면 id | null(build_canvas.link_target 과 같은 규칙)
    if (!h || /^(#|javascript:|mailto:|tel:)/i.test(h)) return null;
    here = here.split(/[?#]/)[0]; var dir = here.replace(/[^\/]*$/, ''), u;
    try { u = new URL(h, here).href.split(/[?#]/)[0]; } catch (e) { return null; }
    if (u.indexOf(dir) !== 0 || !/\.html?$/i.test(u)) return null;
    var rest; try { rest = decodeURIComponent(u.slice(dir.length)); } catch (e) { return null; }   // 깨진 %xx
    if (rest.indexOf('/') >= 0) return null;          // 같은 폴더의 화면만
    return rest.replace(/\.html?$/i, '') || null;
  }
  function toOf(el) {                                 // 같은 폴더의 다른 화면으로 가는 링크면 그 화면 id
    var to = linkTo(hrefOf(el), location.href); return to === screenId() ? null : to;
  }
  window.__hdRules = {pathOf: pathOf, match: match, find: find, hrefOf: hrefOf, linkTo: linkTo};
  function links() {
    var res = [];
    document.querySelectorAll(LINK_SEL).forEach(function (el) {
      var to = toOf(el); if (!to) return;
      res.push({to: to, path: pathOf(el), text: textOf(el).slice(0, 40), rect: rectOf(el)});
    });
    return res;
  }
  function linkAt(el) {                               // el 또는 그 조상 중 화면 링크
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) { if (n.matches && n.matches(LINK_SEL) && toOf(n)) return n; }
    return null;
  }
  function sendGo(el) {
    send(el ? {type: 'hd-link-go', screen: screenId(), to: toOf(el), path: pathOf(el), rect: rectOf(el)} : {type: 'hd-link-go', screen: screenId(), to: null});
  }
  var HIT_SEL = 'button, a, input, select, textarea, label, [role=button], [role=link], [role=tab], [tabindex], li';
  function ownText(el) { for (var c = el.firstChild; c; c = c.nextSibling) if (c.nodeType === 3 && c.nodeValue.trim()) return true; return false; }
  function leafOf(at) {                               // 글자 고치기: 자기 글자가 있는 요소. 없으면 글자 가진 자손이 딱 하나일 때만 그것
    if (!at || at.nodeType !== 1 || ownText(at)) return at;
    var hits = Array.prototype.filter.call(at.querySelectorAll('*'), ownText);
    return hits.length === 1 ? hits[0] : null;
  }
  function kindOf(el) {                               // 요소 종류: 화면 링크 · 버튼 · 입력칸 · 글자 · 영역
    var t = el.tagName.toLowerCase(), role = el.getAttribute('role') || '';
    if (toOf(el)) return 'link';
    if (t === 'a' || t === 'button' || /^(button|link|tab|menuitem)$/.test(role)) return 'button';
    if (t === 'input' || t === 'select' || t === 'textarea') return 'field';
    return ownText(el) ? 'text' : 'box';
  }
  function sendHit(at, leaf, type) {                       // 편집할 요소: 화면 링크 → 누를 수 있는 요소 → 그 요소(html·body 는 없음). leaf = 글자를 가진 그 요소
    var el = leaf ? leafOf(at) : linkAt(at) || (at && at.closest ? at.closest(HIT_SEL) : null) || at;
    if (!el || el === document.documentElement || el === document.body || el.hasAttribute('data-hd-links')) { send({type: type || 'hd-hit', screen: screenId(), path: null}); return; }
    send(withSrc({type: type || 'hd-hit', screen: screenId(), path: pathOf(el), text: textOf(el).slice(0, 40), full: String(el.innerText || el.value || '').trim().slice(0, 500),
          rect: rectOf(el), to: toOf(el), kind: kindOf(el), quote: quoteOf(el), textOk: textOk(el)}, el));
  }
  // 글자만 바꿔도 되는 요소 — 안의 자식이 모두 인라인(글이 든 b·span…, 또는 br·wbr)일 때. helper.py INLINE·_inline_only 와 같은 규칙
  var INLINE = /^(b|strong|i|em|span|small|u|s|mark|sub|sup|code|abbr|cite|q|kbd|var|time|font|del|ins|br|wbr)$/;
  var VOIDS = /^(area|base|br|col|embed|hr|img|input|link|meta|source|track|wbr)$/;
  function textOk(el) {
    if (!el || el.nodeType !== 1 || VOIDS.test(el.tagName.toLowerCase())) return false;
    return Array.prototype.every.call(el.querySelectorAll('*'), function (c) {
      var t = c.tagName.toLowerCase();
      return INLINE.test(t) && (t === 'br' || t === 'wbr' || !!c.textContent.trim());
    });
  }
  var pend = [];
  function pending(items) {                           // 반영 대기: 글 = 안의 마디를 떼어 두고 새 글로 · 지우기 = 숨김 — 다음 호출에서 처음대로(떼어 둔 마디를 그대로 되돌림)
    pend.reverse().forEach(function (q) {
      if (q.kids) { while (q.el.firstChild) q.el.removeChild(q.el.firstChild); q.kids.forEach(function (k) { q.el.appendChild(k); }); }
      if (q.disp !== undefined) q.el.style.display = q.disp;
      q.el.style.outline = q.o; q.el.style.outlineOffset = q.oo;
    });
    pend = [];
    (items || []).forEach(function (it) {
      var el = find(it.path);
      if (!el) return;
      var q = {el: el, o: el.style.outline, oo: el.style.outlineOffset};
      if (it.remove) { q.disp = el.style.display; el.style.display = 'none'; pend.push(q); return; }
      if (!textOk(el)) return;                         // 도우미도 거절할 요소 — 일부만 바꿔 보이지 않는다
      q.kids = Array.prototype.slice.call(el.childNodes);
      q.kids.forEach(function (k) { el.removeChild(k); });
      String(it.text == null ? '' : it.text).split('\n').forEach(function (line, i) {
        if (i) el.appendChild(document.createElement('br'));
        if (line) el.appendChild(document.createTextNode(line));
      });
      el.style.outline = '2px dashed #f59e0b'; el.style.outlineOffset = '2px';
      pend.push(q);
    });
  }
  document.addEventListener('click', function (e) {    // Ctrl/Cmd+클릭: 이동 대신 '어디로 가나'
    if (picking || !(e.ctrlKey || e.metaKey) || !window.parent || window.parent === window) return;
    var el = linkAt(e.target); if (!el) return;
    e.preventDefault(); e.stopPropagation();
    sendGo(el);
  }, true);
  function docHeight() {
    var de = document.documentElement, b = document.body;
    return Math.max(de.scrollHeight, de.offsetHeight, b ? b.scrollHeight : 0, b ? b.offsetHeight : 0);
  }
  var paints = [];
  function paint(items) {
    paints.forEach(function (n) { n.remove(); }); paints = [];
    var seen = {};
    (items || []).forEach(function (it) {
      var el = find(it.path);
      if (!el) return;
      var o = 3 + 6 * (seen[it.path] || 0);            // 같은 요소의 두 번째 쌍부터 바깥으로(3px 틈)
      seen[it.path] = (seen[it.path] || 0) + 1;
      var r = el.getBoundingClientRect(), d = document.createElement('div');
      d.setAttribute('data-hd-links', '');
      d.style.cssText = 'position:absolute;z-index:2147483646;pointer-events:none;border-radius:6px;box-sizing:border-box;' +
        'left:' + (r.left + scrollX - o) + 'px;top:' + (r.top + scrollY - o) + 'px;width:' + (r.width + 2 * o) + 'px;height:' + (r.height + 2 * o) + 'px;' +
        'border:3px solid ' + it.color + ';box-shadow:0 0 0 2px rgba(255,255,255,.85)';
      if (it.n) {
        var b = document.createElement('span');
        b.textContent = it.n <= 20 ? String.fromCharCode(0x245F + it.n) : '(' + it.n + ')';
        b.style.cssText = 'position:absolute;right:-10px;top:-12px;min-width:22px;height:22px;padding:0 3px;border-radius:999px;background:' + it.color +
          ';color:#fff;font:700 14px/22px sans-serif;text-align:center';
        d.appendChild(b);
      }
      document.documentElement.appendChild(d); paints.push(d);
    });
  }

  send({type: 'hd-here', screen: screenId()});
  var editOn = false;
  document.addEventListener('dblclick', function (e) {    // 크게 보기에서 두 번 누른 글자 → 캔버스가 그 자리에 고치기 칸
    if (!editOn || picking || !window.parent || window.parent === window) return;
    var el = leafOf(e.target); if (!el) return;
    e.preventDefault(); e.stopPropagation();
    sendHit(el, true, 'hd-dbl');
  }, true);
  addEventListener('message', function (e) {
    var d = e.data; if (!d) return;
    if (d.type === 'hd-palette') apply(d.slug);
    else if (d.type === 'hd-theme-vars') themeVars(d.vars || {});
    else if (d.type === 'hd-links') { if (d.on) send({type: 'hd-links', screen: screenId(), accent: accent(), docHeight: docHeight(), links: links()}); else paint([]); }
    else if (d.type === 'hd-links-paint') paint(d.items);
    else if (d.type === 'hd-link-at') sendGo(linkAt(document.elementFromPoint(+d.x || 0, +d.y || 0)));
    else if (d.type === 'hd-hit-at') sendHit(document.elementFromPoint(+d.x || 0, +d.y || 0), !!d.leaf);
    else if (d.type === 'hd-pending') pending(d.items);
    else if (d.type === 'hd-locate') locate(d.items);
    else if (d.type === 'hd-edit') editOn = !!d.on;
    else if (d.type === 'hd-pick') {
      picking = !!d.on; last = null;
      if (!picking && box) box.style.display = 'none';
      document.documentElement.style.cursor = picking ? 'crosshair' : '';
    }
  });
})();
