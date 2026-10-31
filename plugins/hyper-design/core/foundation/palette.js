/* 원클릭 팔레트 교체 — 화면은 <link id="tokens" href="tokens.css"> 하나만 바꾼다.
   캔버스가 postMessage({type:'hd-palette', slug})를 보내거나, 마지막 선택(localStorage)·?p= 를 따른다.
   {type:'hd-theme-vars', vars:{'--c-brand': '#RRGGBB', …}} 는 캔버스 '내 테마' 색 네 칸 덮어쓰기({} 이면 지움).
   요소 고르기(캔버스 크게 보기): {type:'hd-pick', on} 을 받으면 마우스 올린 요소에 테두리를 그리고
   {type:'hd-hover', rect} / 클릭 시 {type:'hd-picked', screen, path, text, rect, add} 를 부모에게 보낸다(add = Shift 로 여러 개 고르기).
   연결 보기: {type:'hd-links', on:true} 를 받으면 다른 화면으로 가는 링크 목록을
   {type:'hd-links', screen, accent, docHeight, links:[{to, path, text, rect}]} 로 답하고(docHeight = 화면 전체 높이),
   {type:'hd-links-paint', items:[{path, color, n, hi?}]} 로 그 요소들에 색 테두리·번호를 그린다(items:[] 이면 지움). hi = 그 하나만 진하게(2px 실선 + 옅은 색 바탕 — R46 선 태그 목록 창에서 고른 버튼).
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
   예외 아이콘 + 글(R15): 자식 요소가 글이 없거나(svg·img·빈 i/span) 글 든 인라인만이면 글 조각만 바꾸고 아이콘은 그대로 — 바뀐 곳이 글 마디 하나 안이면 그 마디만(textMode 'icon', html_edit._icon_text_patch).
   불러올 때 {type:'hd-here', screen} 을 보낸다 — 크게 보기 안에서 다른 화면으로 넘어가도 캔버스가 지금 화면을 안다.
   글자 고치기(크게 보기): {type:'hd-edit', on} 을 받으면 두 번 누른 글자 요소를 {type:'hd-dbl', …hd-hit 과 같은 칸} 으로 보낸다 — 선택(hd-pick mode 'select') 도구만(R52 · 손 = 화면 체험이라 보내지 않음).
    그 자리 고치기 중 선택 도구로 다른 곳 누르기(R52): 글자 = 그 글자를 hd-dbl 로(캔버스의 hd-inline 이 지금 것을 저장으로 끝낸다) · 글자 아님 = 저장하고 끝(hd-inline-done away:true).
  블록 편집(task 49a): hd-hit 답에 prev·next(앞·뒤 형제 요소가 있나 — script·style·template·link·meta 는 빼고, helper.py SIB_SKIP) · root(화면 뿌리).
    hd-pick 의 mode: 'text' = 누른 글자 요소를 hd-dbl 로 · 'select' = 누른 요소를 {type:'hd-sel', …hd-hit 칸, add?} 으로(Shift = add:true, 여러 요소 R19 · 없으면 그대로 hd-picked).
    hd-edit 이 켜져 있으면 오른쪽 클릭 = {type:'hd-ctx', …hd-hit 칸, x, y}(브라우저 메뉴 대신), 고르는 중 스크롤 = {type:'hd-scroll'},
    왼쪽 누름 = {type:'hd-press'}(캔버스 우클릭 메뉴 닫기 — 틀 안 누름은 캔버스 문서에 오지 않는다).
    hd-pending 항목 {path, dup:true}(바로 뒤에 점선 복사본) · {path, move:'up'|'down'}(형제와 자리 바꿈) · {path, to}(형제 사이 자리 — hd-opt 의 to 와 같은 뜻, 51-3) — 경로는 모두 바꾸기 전 문서에서 찾는다.
  블록 조립(task 49b): hd-hit 계열 답에 up(감싼 요소가 있나 — body·html 은 아님) · tag · attrs(허용 목록 ATTR_OK 의 지금 값).
    {type:'hd-up', path, tag} → {type:'hd-upchain', tag, path, chain:[조상 hd-hit 칸…](가까운 것부터 8개)} ·
    {type:'hd-find', path, tag} → 문서가 다 실린 뒤 {type:'hd-found', tag, …hd-hit 칸}(없으면 path null) — 쓴 뒤 같은 요소 다시 고르기 ·
    hd-pending 항목 {path, attr, value}(허용 목록 속성을 잠시 바꿈).
  Figma 고르기 키(51-2): {type:'hd-down', path, tag} → 첫 자식 요소 · {type:'hd-sib', path, dir:1|-1, tag} → 다음·앞 형제(끝에서 돈다) —
    둘 다 {type:'hd-hop', tag, …hd-hit 칸} 로 답한다(없으면 path null). 자식·형제 = script·style·template·link·meta·data-hd-dup·data-hd-pick·data-hd-links 를 뺀 요소(옮기기 sibsOf 와 같은 규칙).
    hd-hit-at 에 deep:true = 그 자리 가장 안쪽 요소 그대로(Alt+클릭) · 크게 보기 고르기(select)에서 Alt+클릭도 가장 안쪽 요소.
  바로 반영(task 49c — 캔버스가 화면을 먼저 바꾸고 도우미 답이 실패면 되돌린다):
    {type:'hd-inline', path, tag} → 그 요소 하나만 contenteditable(글꼴·크기 그대로, 글 전체 선택) · {type:'hd-inline-on', tag, screen} 로 알림(없으면 캔버스는 예전 글 칸).
      Enter · Ctrl/Cmd+Enter · Esc = 저장하고 끝(R52 — 되돌리기는 캔버스 Ctrl+Z, 규칙 textKey = modules/text-edit.js key) · Shift+Enter = 줄바꿈(br) · 요소 밖으로 나가기(blur) = 저장.
      끝나면 {type:'hd-inline-done', tag, ok, text, old, path, why?, away}(away = 다른 곳을 눌러 끝냄 — 캔버스가 이 요소를 다시 고르지 않는다)
      (ok:false = 그대로·못 고침 — 원래 글 그대로. text = 글(br = \n, 공백 하나로) · 바뀐 글은 helper.py 글 바꾸기와 같은 모양(글 + br)으로 남기고 tag 로 되돌릴 수 있다)
    {type:'hd-opt', tag, items:[{path, text} | {path, dup:true, to?} | {path, move:'up'|'down', n?} | {path, to} | {path, remove:true}]} → 점선 없이 바로 바꾸고(되돌릴 것은 tag 로 기억) {type:'hd-opt-done', tag, ok, hit(바꾼 요소의 hd-hit 칸)|null}
      to(51-5) = 형제 요소(kids() 규칙 = helper.py SIB_SKIP + 캔버스가 넣은 것 뺌) 사이 자리 — {path, to} = 그 요소를 옮긴 뒤 자리 to(helper move op:to 와 같은 뜻) ·
      {path, dup:true, to} = 원본은 제자리, 복사본을 원래 형제 목록의 to 번째 앞(끝이면 맨 뒤)에(Alt 끌기) — hit 은 복사본
      remove(49d) = 그 요소를 문서에서 떼어 둔다(숨김이 아님 — 도우미가 쓴 새 파일과 나무가 같아 교체가 조용하다) · hit 은 null · 되돌리면 제자리로
    {type:'hd-opt-undo', tag} → 그 tag 의 바꿈을 처음대로 · {type:'hd-sibs', path, tag} → {type:'hd-sibs', tag, index, rects:[형제 상자…]}(형제 = sib() 규칙, 화면 CSS px)
    고르기(select) 도구로 고른 요소를 누른 채 4px 넘게 끌면 {type:'hd-grab', phase:'start'|'move'|'end'|'cancel', x, y, alt}(화면 CSS px, alt = Alt 누름 — 끄는 중 Alt 를 누르고 떼도 move 로 알림, 51-5) — 놓은 뒤 클릭은 먹는다
   메모 자리(W3C Web Annotation 처럼 선택자 여럿): hd-picked·hd-hit 답에 quote:{exact, prefix, suffix} — 요소 글(≤200자)과 문서 글에서 그 앞·뒤 32자.
   다시 찾기: {type:'hd-locate', items:[{key, path, quote}]} → {type:'hd-located', items:[{key, rect|null, how}]} — path 가 있고(quote 가 없거나 그 요소 글에 quote.exact 가 있음) = 'path',
   아니면 문서 글에서 quote.exact 를 찾아(앞·뒤 글이 맞는 곳 먼저) 그 글을 감싼 가장 작은 요소 = 'quote', 못 찾으면 'none'(rect:null).
   스크롤(R16): 마지막 hd-locate 항목을 기억했다가 화면 안 스크롤(문서·안쪽 칸)마다 한 애니메이션 프레임에 한 번 hd-located 를 다시 보낸다(점선·핀이 요소를 따라가게).
   움직이는 화면(memo-state — canvas contract/memo-state.md): hd-located 에 view:{hd}(documentElement.dataset.hdState, 없으면 null)와 항목마다 now:{text(textOf), shown}(path 가
     요소 하나에 맞을 때, 아니면 {text:null, shown:false}). 문서가 바뀌면(MutationObserver · transitionend, 120ms 에 한 번) 마지막 hd-locate 를 다시 재고 답이 달라졌을 때만 보낸다.
     클릭 기록 trail = 고르기 중이 아닌 클릭의 요소 경로(최근 30개, 이 페이지를 읽은 뒤) — hd-picked·hd-hit/sel/dbl 답에 view:{hd, trail}.
     {type:'hd-goto', tag, state} → window.hdGoto(state) 를 부르고 {type:'hd-gone', tag, ok, how:'hd'|'none'}(함수 없음 = none, false 를 돌려주거나 던지면 ok:false).
     {type:'hd-replay', tag, trail} → 문서가 다 실린 뒤 경로마다(요소가 하나가 될 때까지 1.5초 기다림) el.click()(고르기 막기 건너뜀), 사이 250ms → {type:'hd-replayed', tag, ok, done}.
   소스 위치(앱 카드, Svelte 개발 서버): 요소나 그 조상에 __svelte_meta.loc 이 있으면 hd-picked·hd-hit·hd-dbl 답과 hd-located 항목에
   src:{file, line, column}(window.__hdSrc = {root, base} 가 있으면 저장소 기준 경로) · comp:[안쪽 컴포넌트부터] 를 더한다. 없으면 두 칸 모두 없다.
   판 모드(?hd-mode=board — 캔버스 판 위 카드만, 크게 보기는 아님): 화면 스크립트보다 먼저 reduced-motion 을 켜고 움직임을 멈춘다
   (유한 = 끝 상태, 무한 = 한 번 뒤 멈춤 · load 뒤 WAAPI 도). contract/board-motion.md
   토큰 고르기(R55, Foundation 탭 — contract/ds-edit.md): hd-pick 에 doc:true 면 {type:'hd-pick-on', on, tokens: [data-var] 수} 로 답한다.
     고르기(select) 중 [data-var] 안을 누르면 그 견본(closest)으로 hd-sel + token('--이름')·tokenKind·label(견본이 보이는 이름)·vars(그 토큰과 글자 줄 짝 --fw/--lh 의 지금 값),
     견본에 고른 테두리(스크롤을 따라감) · 캔버스로 초점(H·V·Ctrl+Z 가 캔버스로). {type:'hd-unpick'} = 테두리 걷기. 토큰을 고른 동안 스크롤 = hd-scroll.
     문서 탭(doc:true 를 받은 뒤)에서 H·V·Esc·Ctrl/Cmd+Z/Y 는 {type:'hd-key', key, ctrl, meta, shift} 로 캔버스에 넘긴다(입력 칸 안은 아님).
     {type:'hd-css-reload', sheet:'tokens'|'components', v} = 그 스타일 파일만 다시 읽는다(저장 뒤) — tokens = #tokens 를 지금 팔레트 주소 + ?v=,
     components = components.css 링크 + ?v=(옛 이름 hd-tokens-reload = tokens). hd-palette 의 slug '@project' = 프로젝트 tokens.css 그대로
   부품 고르기(R55 phase C, Components 탭): [data-var] 가 없고 .spec-stage 가 있는 문서 = 부품 문서(hd-pick-on 의 parts = .spec-stage 수).
     고르기 중 .spec-stage 안을 누르면 components.css 규칙이 겨누는 요소(클래스가 그 규칙 클래스를 모두 가짐) 가운데 그 견본 묶음(section data-key)
     클래스를 가진 가장 가까운 요소, 없으면 가장 가까운 것(Alt = 가장 안쪽) → hd-sel + part {key, title, classes, tag, state('disabled'|'checked'|'')}·label·rect */
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
  var curSlug = '', tokV = 0;                        // 지금 바탕 팔레트('' · '@project' = 프로젝트 tokens.css) · 다시 읽기 표(R55)
  function tokHref(base) {                            // modules/ds-edit.js href 와 같은 규칙
    var b = String(base).split('?')[0], h = curSlug && curSlug !== '@project' ? b.replace(/tokens(-[^/]*)?\.css$/, 'tokens-' + curSlug + '.css') : b;
    return tokV ? h + '?v=' + tokV : h;
  }
  function apply(slug) {
    var l = document.getElementById('tokens'); if (!l || !slug) return;
    var base = l.getAttribute('data-base') || l.getAttribute('href'); l.setAttribute('data-base', base);
    curSlug = String(slug); l.setAttribute('href', tokHref(base));
  }
  function reloadSheet(sheet, v) {                   // R55 phase C — 한 메시지(hd-css-reload)로 그 스타일 파일만
    if (sheet === 'tokens') { reloadTokens(v); return; }
    if (sheet !== 'components') return;
    var ver = String(v || Date.now()).replace(/[^\w-]/g, '');
    Array.prototype.forEach.call(document.querySelectorAll('link[rel~="stylesheet"]'), function (l) {
      var base = l.getAttribute('data-base') || l.getAttribute('href') || '';
      if (!/(^|\/)components\.css(\?|$)/.test(base)) return;
      l.setAttribute('data-base', base.split('?')[0]); l.setAttribute('href', base.split('?')[0] + '?v=' + ver);
      l.addEventListener('load', function () { partRules = null; if (tokEl) tselShow(tokEl); }, {once: true});
    });
  }
  function reloadTokens(v) {
    var l = document.getElementById('tokens'); if (!l) return;
    var base = l.getAttribute('data-base') || l.getAttribute('href'); l.setAttribute('data-base', base);
    tokV = String(v || Date.now()).replace(/[^\w-]/g, ''); l.setAttribute('href', tokHref(base));
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
  var picking = false, pickMode = '', box = null, last = null;   // pickMode: '' = 메모(hd-picked) · 'text' = 글자(hd-dbl) · 'select' = 요소 고르기(hd-sel)
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
  var lastLoc = null, locRaf = 0, locSent = '', domT = 0, domObs = null;
  function shownOf(el) { if (!el.getClientRects().length) return false; return getComputedStyle(el).visibility !== 'hidden'; }
  function nowOf(path) {                              // 움직이는 화면(memo-state): 지금 그 대상이 보이나·보이는 글 — 메모를 단 때 글(textOf)과 견준다
    var el = path ? find(path) : null;
    if (!el || el === document.body || el === document.documentElement) return {text: null, shown: false};
    return {text: textOf(el), shown: shownOf(el)};
  }
  function hdState() { var v = document.documentElement.getAttribute('data-hd-state'); return v ? String(v) : null; }
  function locate(items, quiet) {                     // quiet = 문서가 바뀌어 다시 잼 — 답이 같으면 보내지 않는다
    lastLoc = items && items.length ? items : null;   // 스크롤 뒤 다시 답할 것(R16)
    var d = docText();
    var msg = {type: 'hd-located', screen: screenId(), view: {hd: hdState()}, items: (items || []).map(function (it) {
      var r = locateOne(it || {}, d); r.now = nowOf((it || {}).path); return r; })};
    var sig = JSON.stringify(msg);
    if (quiet && sig === locSent) return;
    locSent = sig; send(msg);
    watchDom();
  }
  function domChanged() { if (!lastLoc || domT) return; domT = setTimeout(function () { domT = 0; if (lastLoc) locate(lastLoc, true); }, 120); }
  function watchDom() {                               // 단계가 바뀌면(같은 요소의 글만 바뀜·요소 교체·숨김) 다시 잰다 — 스크롤이 없어도
    if (domObs || typeof MutationObserver !== 'function' || !document.body || !window.parent || window.parent === window) return;
    domObs = new MutationObserver(domChanged);
    domObs.observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['class', 'style', 'hidden']});
    domObs.observe(document.documentElement, {attributes: true, attributeFilter: ['data-hd-state']});
    addEventListener('transitionend', domChanged, true);
  }
  var trail = [], replaying = false, TRAIL_MAX = 30;  // 클릭 기록(memo-state) — 규칙은 canvas modules/memo-state.js record 와 같다
  function viewNow() { return {hd: hdState(), trail: trail.slice()}; }
  addEventListener('click', function (e) {             // window 잡는 단계 = 아래 고르기 막기(document)보다 먼저
    if (picking && !replaying) return;
    var t = e.target; if (!t || t.nodeType !== 1 || t === box || (t.closest && t.closest('[data-hd-pick],[data-hd-links]'))) return;
    var p = pathOf(t); if (!p) return;
    trail.push(p); if (trail.length > TRAIL_MAX) trail.splice(0, trail.length - TRAIL_MAX);
  }, true);
  function gotoState(d) {
    var has = typeof window.hdGoto === 'function', ok = false;
    if (has && d.state != null) {
      try { ok = window.hdGoto(String(d.state)) !== false; } catch (err) { console.warn('[hd] hdGoto 실패: ' + (err && err.message || err)); ok = false; }
    }
    send({type: 'hd-gone', screen: screenId(), tag: d.tag || '', ok: ok, how: has ? 'hd' : 'none'});
  }
  function replay(d) {
    var steps = (Array.isArray(d.trail) ? d.trail : []).filter(function (p) { return typeof p === 'string' && p; }).slice(-TRAIL_MAX), k = 0, wait = 0;
    function end(ok) { send({type: 'hd-replayed', screen: screenId(), tag: d.tag || '', ok: ok, done: k}); }
    function step() {
      if (k >= steps.length) { end(true); return; }
      var el = find(steps[k]);
      if (!el) { if (++wait > 15) { end(false); return; } setTimeout(step, 100); return; }   // 앞 클릭 뒤 요소가 늦게 생길 수 있다
      wait = 0; replaying = true;
      try { el.click(); } catch (err) { console.warn('[hd] 다시 하기 클릭 실패: ' + steps[k]); } finally { replaying = false; }
      k++; setTimeout(step, 250);
    }
    whenLoaded(function () { setTimeout(step, 300); });
  }
  addEventListener('scroll', function () {             // R16: 메모 점선·핀은 화면 좌표라 스크롤(문서·안쪽 칸)하면 자리를 다시 답한다 — 한 애니메이션 프레임에 한 번
    if (!lastLoc || locRaf || !window.parent || window.parent === window) return;
    locRaf = requestAnimationFrame(function () { locRaf = 0; if (lastLoc) locate(lastLoc); });
  }, true);
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
    if (!picking || inEdit(e)) return;
    var t = target(e);
    if (t && pickDoc) { t = partsDoc() ? partEl(t, e.altKey) : t.closest ? t.closest('[data-var]') : null; if (!t) { last = null; if (box) box.style.display = 'none'; return; } }   // 문서 탭: 토큰 견본·부품만 비춘다(R55)
    if (!t || t === last) return;
    last = t; send({type: 'hd-hover', rect: showBox(t)});
  }, true);
  function inEdit(e) { return !!(inl && e.target && e.target.nodeType && inl.el.contains(e.target)); }   // 그 자리 글자 고치기 중인 요소 안(49c) — 커서·선택은 그대로
  function block(e) { if (!picking || replaying || inEdit(e)) return; e.preventDefault(); e.stopPropagation(); if (e.stopImmediatePropagation) e.stopImmediatePropagation(); }
  ['mousedown', 'mouseup', 'pointerdown', 'pointerup', 'submit'].forEach(function (ev) { document.addEventListener(ev, block, true); });   // dblclick 은 아래 글자 고치기 리스너가 막고 받는다
  var pressInl = false;                               // 그 자리 고치기 중 선택(V)으로 다른 곳을 누르기 시작함(pointerdown — 고르는 중엔 mousedown 이 막혀 blur 가 없다)
  function retarget(e) {                              // 고치는 중 다른 곳 누르기(R52 — HD.textEdit.press 와 같은 뜻): 글자 = 캔버스에 hd-dbl(→ hd-inline 이 지금 것을 저장으로 끝내고 그 글자로) · 글자 아님 = 저장하고 끝(away)
    var t = target(e), lf = t ? leafOf(t) : null;
    if (lf && lf !== document.body && lf !== document.documentElement) {
      e.preventDefault(); e.stopPropagation(); if (e.stopImmediatePropagation) e.stopImmediatePropagation();
      sendHit(lf, true, 'hd-dbl'); return true;
    }
    if (inl) inlineEnd(true, true);
    return false;
  }
  document.addEventListener('dblclick', function (e) {   // 두 번 누른 글자 → 캔버스가 그 자리에 고치기 칸 — 크게 보기 고르기(V, select)일 때만(Figma, R52 HD.textEdit.dbl 'modal').
    if (!picking || inEdit(e)) return;                   // 손 도구(체험, picking 아님) = 화면 그대로 — 버튼을 빠르게 두 번 눌러도 고치기로 빠지지 않는다(사용자 10-29)
    block(e);
    if (pickMode !== 'select' || !editOn || !window.parent || window.parent === window) return;
    var el = leafOf(e.target); if (el) sendHit(el, true, 'hd-dbl');
  }, true);
  document.addEventListener('click', function (e) {
    if (pressInl) { pressInl = false; if (!inEdit(e) && retarget(e)) return; }
    if (!picking || replaying || inEdit(e)) return;
    block(e);
    if (grabbed) { grabbed = false; return; }        // 끌어 놓은 뒤의 클릭 = 고르기 아님(49c)
    var t = target(e); if (!t) return;
    if (pickMode === 'text') { sendHit(t, true, 'hd-dbl'); return; }   // 크게 보기 글자 도구(task 49a)
    if (pickMode === 'select' && pickDoc) { if (partsDoc()) pickPart(t, e.altKey); else pickToken(t); return; }   // 문서 탭(R55) — 토큰 견본·부품(phase C)만 고른다
    if (pickMode === 'select') { selEl = e.altKey ? t : linkAt(t) || (t.closest ? t.closest(HIT_SEL) : null) || t; sendHit(t, false, 'hd-sel', e.altKey, e.shiftKey); return; }   // Alt = 가장 안쪽 요소(51-2)   // 크게 보기 고르기 도구 → 요소 막대(고른 것 = 눌러 끌 수 있음, 49c)
    send(withSrc({type: 'hd-picked', screen: screenId(), path: pathOf(t), text: textOf(t), rect: showBox(t), quote: quoteOf(t), add: !!e.shiftKey, view: viewNow()}, t));
  }, true);

  /* ---------- 토큰 고르기(R55, Foundation 탭) ---------- */
  /* hd-token-kind — modules/ds-edit.js 의 kindOf 와 같은 규칙(화면 안이라 그 파일을 못 읽음 · test_canvas_unit_ds_edit 이 같은 표로 견준다) */
  function tokenKind(name) {
    var n = String(name || ''), pre = [['--c-', 'color'], ['--fs-', 'size'], ['--fw-', 'weight'], ['--lh-', 'line'], ['--r-', 'radius'], ['--shadow-', 'shadow'],
                                       ['--stack-', 'space'], ['--space-', 'space'], ['--gap-', 'space'], ['--h-', 'size'], ['--w-', 'size']];
    if (['--page-x', '--block-pad', '--block-gap', '--row-py'].indexOf(n) >= 0) return 'space';
    for (var i = 0; i < pre.length; i++) if (n.indexOf(pre[i][0]) === 0) return pre[i][1];
    return 'other';
  }
  /* /hd-token-kind */
  var pickDoc = false, tokEl = null, tsel = null;
  function tokVars(name) {                            // 그 토큰 + 글자 줄 짝(--fw-·--lh-)의 지금 값
    var cs = getComputedStyle(document.documentElement), o = {}, names = [name];
    if (name.indexOf('--fs-') === 0) names.push('--fw-' + name.slice(5), '--lh-' + name.slice(5));
    names.forEach(function (n) { var v = cs.getPropertyValue(n).trim(); if (v) o[n] = v; });
    return o;
  }
  function tselShow(el) {                             // 고른 견본 테두리 — 문서 좌표라 스크롤을 따라간다
    if (!tsel) {
      tsel = document.createElement('div'); tsel.setAttribute('data-hd-pick', '');
      tsel.style.cssText = 'position:absolute;z-index:2147483646;pointer-events:none;border:2px solid #2563eb;border-radius:6px;box-sizing:border-box;display:none';
      document.documentElement.appendChild(tsel);
    }
    var r = el.getBoundingClientRect();
    tsel.style.left = (r.left + scrollX - 2) + 'px'; tsel.style.top = (r.top + scrollY - 2) + 'px';
    tsel.style.width = (r.width + 4) + 'px'; tsel.style.height = (r.height + 4) + 'px'; tsel.style.display = 'block';
  }
  function unpick() { tokEl = null; if (tsel) tsel.style.display = 'none'; }
  function pickToken(t) {
    var el = t.closest ? t.closest('[data-var]') : null;
    if (!el) { unpick(); send({type: 'hd-sel', screen: screenId(), path: null, doc: true}); return; }
    var name = el.getAttribute('data-var'), lab = el.querySelector('.nm, .lb b, b');
    tokEl = el; tselShow(el); if (box) box.style.display = 'none';
    send({type: 'hd-sel', screen: screenId(), path: pathOf(el), doc: true, token: name, tokenKind: tokenKind(name),
          label: lab ? lab.textContent.replace(/\s+/g, ' ').trim() : '', rect: rectOf(el), vars: tokVars(name)});
    try { window.parent.focus(); } catch (e) { console.warn('[hd] 캔버스로 초점 돌리기 실패 — ' + e); }   // H·V·Ctrl+Z 가 캔버스로
  }
  /* 부품 고르기(R55 phase C, Components 탭) */
  var partRules = null;                               // components.css 맨 위 규칙의 겹 선택자 클래스 묶음들 [[클래스…]] — 다시 읽으면 비움
  function partsDoc() { return !document.querySelector('[data-var]') && !!document.querySelector('.spec-stage'); }
  function rulesOf() {
    if (partRules) return partRules;
    var out = [];
    Array.prototype.forEach.call(document.styleSheets, function (sh) {
      if (!/(^|\/)components\.css(\?|$)/.test(String(sh.href || '').replace(/^.*\//, '/'))) return;
      var rs; try { rs = sh.cssRules; } catch (e) { console.warn('[hd] components.css 규칙을 읽지 못함 — ' + e); return; }
      Array.prototype.forEach.call(rs || [], function (r) {
        if (r.type !== 1) return;
        r.selectorText.split(',').forEach(function (p) {
          p = p.trim(); if (/[\s>+~]/.test(p.replace(/\[[^\]]*\]|\([^)]*\)/g, ''))) return;   // 다른 요소 안을 겨누는 규칙은 아님
          var c = p.match(/\.[\w-]+/g); if (c) out.push(c.map(function (x) { return x.slice(1); }));
        });
      });
    });
    return (partRules = out);
  }
  function hasRule(el) {
    var cl = el.classList; if (!cl || !cl.length) return false;
    return rulesOf().some(function (cs) { return cs.every(function (c) { return cl.contains(c); }); });
  }
  function partEl(t, deep) {                          // 견본 칸 안: Alt = 규칙이 있는 가장 안쪽 요소 · 아니면 그 견본 묶음(data-key) 클래스 요소, 없으면 가장 안쪽
    var stage = t.closest ? t.closest('.spec-stage') : null; if (!stage) return null;
    var sec = stage.closest('[data-key]'), key = sec ? sec.getAttribute('data-key') : '', first = null;
    for (var el = t; el && el !== stage; el = el.parentElement) {
      if (!hasRule(el)) continue;
      if (!first) { first = el; if (deep) return el; }
      if (key && el.classList.contains(key)) return el;
    }
    return first;
  }
  function pickPart(t, deep) {
    var el = partEl(t, deep);
    if (!el) { unpick(); send({type: 'hd-sel', screen: screenId(), path: null, doc: true}); return; }
    var sec = el.closest('[data-key]'), title = sec ? sec.getAttribute('data-title') || '' : '';
    var state = el.disabled || el.getAttribute('aria-disabled') === 'true' ? 'disabled' : el.getAttribute('aria-checked') === 'true' ? 'checked' : '';
    tokEl = el; tselShow(el); if (box) box.style.display = 'none';
    send({type: 'hd-sel', screen: screenId(), path: pathOf(el), doc: true, label: title, rect: rectOf(el),
          part: {key: sec ? sec.getAttribute('data-key') || '' : '', title: title, classes: Array.prototype.slice.call(el.classList), tag: el.tagName.toLowerCase(), state: state}});
    try { window.parent.focus(); } catch (e) { console.warn('[hd] 캔버스로 초점 돌리기 실패 — ' + e); }
  }
  addEventListener('scroll', function () { if (tokEl && window.parent && window.parent !== window) send({type: 'hd-scroll', screen: screenId(), doc: true}); }, true);
  document.addEventListener('keydown', function (e) {  // 문서 탭(손·선택 모두): 캔버스 키(H·V·Esc·Ctrl+Z/Y)를 캔버스로 — 문서 안을 누른 뒤에도 도구 키가 듣게
    if (!pickDoc || !window.parent || window.parent === window || e.isComposing) return;
    var t = e.target; if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || ''))) return;
    var k = e.key || '', low = k.toLowerCase(), mod = e.ctrlKey || e.metaKey;
    if (!(mod && !e.altKey && (low === 'z' || low === 'y')) && !(!mod && !e.altKey && (low === 'h' || low === 'v' || k === 'Escape'))) return;
    e.preventDefault();
    send({type: 'hd-key', screen: screenId(), doc: true, key: k, ctrl: e.ctrlKey, meta: e.metaKey, shift: e.shiftKey});
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
  function sendHit(at, leaf, type, deep, add) {                 // 편집할 요소: 화면 링크 → 누를 수 있는 요소 → 그 요소(html·body 는 없음). leaf = 글자를 가진 그 요소 · deep = 그 자리 요소 그대로(51-2)
    var el = leaf ? leafOf(at) : deep ? at : linkAt(at) || (at && at.closest ? at.closest(HIT_SEL) : null) || at;
    var m;
    if (!el || el === document.documentElement || el === document.body || el.hasAttribute('data-hd-links')) m = {type: type || 'hd-hit', screen: screenId(), path: null};
    else { m = hitMsg(el, type || 'hd-hit'); m.view = viewNow(); }   // view = 메모를 단 때 화면 상태(memo-state)
    if (add) m.add = true;                            // hd-sel 의 Shift = 더하기·빼기(여러 요소 R19)
    send(m);
  }
  function hitMsg(el, type) {                         // hd-hit·hd-dbl·hd-sel·hd-ctx 답 칸(같은 것)
    return withSrc({type: type, screen: screenId(), path: pathOf(el), text: textOf(el).slice(0, 40), full: String(el.innerText || el.value || '').trim().slice(0, 500),
          rect: rectOf(el), to: toOf(el), kind: kindOf(el), quote: quoteOf(el), textOk: textOk(el),
          prev: !!sib(el, -1), next: !!sib(el, 1), root: isRoot(el), up: !!upOf(el), tag: el.tagName.toLowerCase(), attrs: attrsOf(el)}, el);
  }
  // 속성 칸(task 49b) — helper.py ATTR_OK · blocks.js ATTRS 와 같은 허용 목록(on*·style 은 절대)
  var ATTR_OK = {img: ['src', 'alt'], a: ['href'], input: ['placeholder'], textarea: ['placeholder']};
  function attrsOf(el) {
    var o = {}; (ATTR_OK[el.tagName.toLowerCase()] || []).forEach(function (n) { o[n] = el.getAttribute(n) || ''; }); return o;
  }
  function upOf(el) {                                 // 고를 수 있는 감싼 요소(body·html 은 아님)
    var p = el.parentElement; return p && p !== document.body && p !== document.documentElement ? p : null;
  }
  function upChain(el) {                              // 상위 고르기(task 49b): 조상 hit 들(가까운 것부터, 8개까지) — 어느 것을 고를지는 캔버스(blocks.parentPick)
    var out = [];
    for (var p = upOf(el); p && out.length < 8; p = upOf(p)) out.push(hitMsg(p, 'hd-up'));
    return out;
  }
  function whenLoaded(fn) { if (document.readyState === 'complete') fn(); else addEventListener('load', fn, {once: true}); }
  var SIB_SKIP = /^(script|style|template|link|meta)$/;   // helper.py SIB_SKIP 과 같은 규칙
  function sib(el, d) {                               // 앞(-1)·뒤(1) 형제 요소 | null
    for (var n = d < 0 ? el.previousElementSibling : el.nextElementSibling; n; n = d < 0 ? n.previousElementSibling : n.nextElementSibling) {
      if (!SIB_SKIP.test(n.tagName.toLowerCase()) && !n.hasAttribute('data-hd-dup')) return n;
    }
    return null;
  }
  function isRoot(el) {                               // helper.py _is_root 과 같은 규칙: body 바로 아래 유일한 요소
    var p = el.parentElement; if (!p || p !== document.body) return false;
    return Array.prototype.filter.call(p.children, function (c) { return !SIB_SKIP.test(c.tagName.toLowerCase()) && !c.hasAttribute('data-hd-pick') && !c.hasAttribute('data-hd-links'); }).length === 1;
  }
  // 글자만 바꿔도 되는 요소 — 안의 자식이 모두 인라인(글이 든 b·span…, 또는 br·wbr)일 때. helper.py INLINE·_inline_only 와 같은 규칙
  var INLINE = /^(b|strong|i|em|span|small|u|s|mark|sub|sup|code|abbr|cite|q|kbd|var|time|font|del|ins|br|wbr)$/;
  var VOIDS = /^(area|base|br|col|embed|hr|img|input|link|meta|source|track|wbr)$/;
  function allText(el) {
    if (!el || el.nodeType !== 1 || VOIDS.test(el.tagName.toLowerCase())) return false;
    return Array.prototype.every.call(el.querySelectorAll('*'), function (c) {
      var t = c.tagName.toLowerCase();
      return INLINE.test(t) && (t === 'br' || t === 'wbr' || !!c.textContent.trim());
    });
  }
  // R15 아이콘 + 글: 글이 있고 자식 요소는 글이 없거나(svg·img·빈 i/span = 아이콘) 글 든 인라인만으로 된 것(b·span…) — 글 조각만 바꾸고 아이콘은 그대로
  // (helper 쪽 html_edit._icon_text 와 같은 규칙). 글 든 자식이 블록·링크이거나 글 안에 아이콘이 들었으면 '' = 못 바꿈.
  function iconText(el) {
    if (!el || el.nodeType !== 1 || VOIDS.test(el.tagName.toLowerCase()) || !el.textContent.trim()) return false;
    return Array.prototype.every.call(el.children, function (c) {
      return /^(script|style)$/i.test(c.tagName) || !c.textContent.trim() || (INLINE.test(c.tagName.toLowerCase()) && allText(c));
    });
  }
  function textMode(el) { return allText(el) ? 'all' : iconText(el) ? 'icon' : ''; }   // 'all' = 안 내용 전부 · 'icon' = 글 조각만 · '' = 못 바꿈
  function textOk(el) { return !!textMode(el); }
  function textRuns(el) {                             // 글 묶음: 바로 아래 글·br·글 든 인라인 요소가 이어진 것(글 없는 요소 = 아이콘에서 끊김) — 보이는 글이 있는 묶음만(html_edit._text_runs)
    var runs = [], cur = null;
    for (var c = el.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 3) (cur = cur || []).push(c);
      else if (c.nodeType === 1 && /^(br|wbr)$/i.test(c.tagName)) { if (cur) cur.push(c); }
      else if (c.nodeType === 1 && c.textContent.trim() && !/^(script|style)$/i.test(c.tagName)) (cur = cur || []).push(c);
      else if (c.nodeType === 1) { if (cur) runs.push(cur); cur = null; }
    }
    if (cur) runs.push(cur);
    return runs.filter(function (r) { return runChars(r).chars.length; });
  }
  function runChars(nodes) {                          // 글 묶음 → {leaves: [[글 마디…]], chars: [[글자, 마디 번호(br = -1)]]} — plainOf 와 같은 정리(html_edit._run_chars)
    var leaves = [], order = [];
    (function walk(list) {
      var last = -1;
      list.forEach(function (n) {
        if (n.nodeType === 3) { if (last < 0) { leaves.push([]); last = leaves.length - 1; order.push(last); } leaves[last].push(n); return; }
        if (n.nodeType !== 1) return;
        last = -1;
        var t = n.tagName.toLowerCase();
        if (t === 'br') order.push(-1);
        else if (t !== 'wbr') walk(Array.prototype.slice.call(n.childNodes));
      });
    })(nodes);
    var chars = [];
    order.forEach(function (i) {
      if (i < 0) { chars.push(['\n', -1]); return; }
      leaves[i].map(function (n) { return n.nodeValue; }).join('').replace(/\s+/g, ' ').split('').forEach(function (ch) { chars.push([ch, i]); });
    });
    var out = [], k = 0;                              // .replace(/ *\n */g,'\n').replace(/ {2,}/g,' ').trim() — 글자마다 주인 마디를 지닌 채
    while (k < chars.length) {
      if (chars[k][0] !== ' ') { out.push(chars[k]); k++; continue; }
      var j = k; while (j < chars.length && chars[j][0] === ' ') j++;
      if (!((k > 0 && chars[k - 1][0] === '\n') || (j < chars.length && chars[j][0] === '\n'))) out.push(chars[k]);
      k = j;
    }
    while (out.length && /^[ \n]$/.test(out[0][0])) out.shift();
    while (out.length && /^[ \n]$/.test(out[out.length - 1][0])) out.pop();
    return {leaves: leaves, chars: out};
  }
  function oneLeaf(chars, v) {                        // html_edit._one_leaf: 바뀐 곳이 글 마디 하나 안이면 [마디, 새 글(앞뒤 공백 뺌)] · 그대로면 'same' · 아니면 null
    var old = chars.map(function (c) { return c[0]; }).join('');
    if (old === v) return 'same';
    var p = 0, s = 0, m = Math.min(old.length, v.length);
    while (p < m && old[p] === v[p]) p++;
    while (s < m - p && old[old.length - 1 - s] === v[v.length - 1 - s]) s++;
    var q = old.length - s, chunk = v.slice(p, v.length - s), own = {};
    for (var k = p; k < q; k++) own[chars[k][1]] = 1;
    if (p === q) {
      if (p > 0 && chars[p - 1][1] >= 0) own[chars[p - 1][1]] = 1; else if (p < chars.length) own[chars[p][1]] = 1;
    }
    var ks = Object.keys(own);
    if (ks.length !== 1 || ks[0] === '-1') return null;
    var leaf = +ks[0], at = [];
    chars.forEach(function (c, i) { if (c[1] === leaf) at.push(i); });
    var was = old.slice(at[0], at[at.length - 1] + 1), now = old.slice(at[0], p) + chunk + old.slice(q, at[at.length - 1] + 1);
    if (!now.trim() || (was[0] === ' ') !== (now[0] === ' ') || (was.slice(-1) === ' ') !== (now.slice(-1) === ' ')) return null;
    return [leaf, now.trim()];
  }
  function linesFrag(frag, v) {                       // 글(\n = br) → 조각에 붙이기
    String(v == null ? '' : v).split('\n').forEach(function (line, i) {
      if (i) frag.appendChild(document.createElement('br'));
      if (line) frag.appendChild(document.createTextNode(line));
    });
  }
  function setIconText(el, v) {
    // html_edit._icon_text_patch 와 같은 규칙: 글 묶음이 하나이고 바뀐 곳이 글 마디 하나 안이면 그 마디만(b·span 꾸밈 그대로),
    // 아니면 첫 글 묶음 = 앞뒤 공백 + 새 글(\n = br, 꾸밈 없음), 뒤 묶음은 지움. 아이콘은 늘 그대로
    var runs = textRuns(el); if (!runs.length) return;
    v = String(v == null ? '' : v);
    if (runs.length === 1) {
      var rc = runChars(runs[0]), hit = oneLeaf(rc.chars, v);
      if (hit === 'same') return;
      if (hit) {
        var ns = rc.leaves[hit[0]], dec = ns.map(function (n) { return n.nodeValue; }).join(''), par = ns[0].parentNode, nx = ns[ns.length - 1].nextSibling;
        var lead1 = dec.slice(0, dec.length - dec.replace(/^\s+/, '').length), trail1 = dec.slice(dec.replace(/\s+$/, '').length);
        var f1 = document.createDocumentFragment();
        if (lead1) f1.appendChild(document.createTextNode(lead1));
        linesFrag(f1, hit[1]);
        if (trail1) f1.appendChild(document.createTextNode(trail1));
        ns.forEach(function (n) { par.removeChild(n); });
        par.insertBefore(f1, nx && nx.parentNode === par ? nx : null);
        return;
      }
    }
    var first = runs[0], at = first[first.length - 1].nextSibling;
    var raw = first.map(function (n) { return n.nodeType === 3 ? n.nodeValue : '\u0000'; }).join('');
    var lead = raw.slice(0, raw.length - raw.replace(/^\s+/, '').length), trail = raw.slice(raw.replace(/\s+$/, '').length);
    runs.forEach(function (r) { r.forEach(function (n) { el.removeChild(n); }); });
    var frag = document.createDocumentFragment();
    if (lead) frag.appendChild(document.createTextNode(lead));
    linesFrag(frag, v);
    if (trail) frag.appendChild(document.createTextNode(trail));
    el.insertBefore(frag, at && at.parentNode === el ? at : null);
  }
  function putText(el, v) { if (textMode(el) === 'icon') setIconText(el, v); else setText(el, v); }
  /* ---------- 바로 반영(task 49c): 그 자리 글자 고치기 · 먼저 바꾸고 tag 로 되돌리기 · 형제 상자 · 고른 요소 끌기 ---------- */
  var inl = null, opts = {}, selEl = null, grab = null, grabbed = false;
  function plainOf(el) {                              // 요소 글 → 저장할 글: 글 마디의 공백은 하나로, br(·고치며 생긴 div/p 줄) = \n — helper.py 가 \n 을 br 로 쓴다
    var out = '';
    (function walk(n) {
      for (var c = n.firstChild; c; c = c.nextSibling) {
        if (c.nodeType === 3) out += c.nodeValue.replace(/[\s ]+/g, ' ');
        else if (c.nodeType === 1) {
          var t = c.tagName.toLowerCase();
          if (t === 'br') out += '\n';
          else { if ((t === 'div' || t === 'p') && out && out.slice(-1) !== '\n') out += '\n'; walk(c); }
        }
      }
    })(el);
    return out.replace(/ *\n */g, '\n').replace(/ {2,}/g, ' ').trim();
  }
  function setText(el, v) {                           // 글 + br — helper.py 글 바꾸기와 같은 모양
    while (el.firstChild) el.removeChild(el.firstChild);
    String(v == null ? '' : v).split('\n').forEach(function (line, i) {
      if (i) el.appendChild(document.createElement('br'));
      if (line) el.appendChild(document.createTextNode(line));
    });
  }
  function keepKids(el) { return Array.prototype.map.call(el.childNodes, function (k) { return k.cloneNode(true); }); }
  function putKids(el, kids) { while (el.firstChild) el.removeChild(el.firstChild); kids.forEach(function (k) { el.appendChild(k.cloneNode(true)); }); }
  function optRec(tag, q) { (opts[tag] = opts[tag] || []).push(q); }
  function optUndo(tag) {
    if (inl && inl.tag === tag) inlineEnd(false);
    (opts[tag] || []).reverse().forEach(function (q) {
      if (q.added && q.added.parentNode) q.added.parentNode.removeChild(q.added);
      if (q.back) q.back.parent.insertBefore(q.el, q.back.next && q.back.next.parentNode === q.back.parent ? q.back.next : null);
      if (q.kids) putKids(q.el, q.kids);
    });
    delete opts[tag];
    reBox();
  }
  function reBox() { if (box && box.style.display === 'block' && selEl && selEl.isConnected) showBox(selEl); }   // 고른 테두리가 옮긴·되돌린 요소를 따라가게
  function stripIds(cp) {                             // 복사본과 그 안의 id·data-region 은 뺀다(helper.py _strip_ids)
    [cp].concat(Array.prototype.slice.call(cp.querySelectorAll('[id],[data-region]'))).forEach(function (n) { n.removeAttribute('id'); n.removeAttribute('data-region'); });
  }
  function placeAt(node, list, to, parent) {         // list(node 뺀 형제 요소) 의 to 번째 앞 | to = 길이면 마지막 뒤 — 자리가 밖이면 false
    to = +to;
    if (!parent || !(to >= 0) || to > list.length || Math.floor(to) !== to) return false;
    if (to < list.length) parent.insertBefore(node, list[to]);
    else if (list.length) parent.insertBefore(node, list[list.length - 1].nextSibling);
    else parent.appendChild(node);
    return true;
  }
  function opt(tag, items) {                          // 점선 없이 바로 — 경로는 모두 바꾸기 전 문서에서 찾는다(도우미도 한 원문에서 고른다)
    var els = (items || []).map(function (it) { return find(it.path); }), ok = true, first = null;
    (items || []).forEach(function (it, i) {
      var el = els[i];
      if (!el) { ok = false; return; }
      if (it.dup) {
        var cp = el.cloneNode(true); stripIds(cp);
        if (it.to == null) el.parentNode.insertBefore(cp, el.nextSibling);
        else if (!placeAt(cp, kids(el.parentElement), it.to, el.parentNode)) { ok = false; return; }
        optRec(tag, {el: el, added: cp});
        if (it.to != null) { if (!first) first = cp; return; }   // Alt 끌기 = 복사본이 골라진다(Figma)
      } else if (it.to != null) {                    // 자리로 옮기기(51-5) — 끌기 한 번
        var back = {el: el, back: {parent: el.parentNode, next: el.nextSibling}};
        if (!placeAt(el, kids(el.parentElement).filter(function (c) { return c !== el; }), it.to, el.parentNode)) { ok = false; return; }
        optRec(tag, back);
      } else if (it.move) {
        var q = {el: el, back: {parent: el.parentNode, next: el.nextSibling}}, n = Math.max(1, +it.n || 1), moved = 0;
        for (var k = 0; k < n; k++) {
          var to = sib(el, it.move === 'up' ? -1 : 1); if (!to) break;
          el.parentNode.insertBefore(el, it.move === 'up' ? to : to.nextSibling); moved++;
        }
        if (moved < n) ok = false;
        if (moved) optRec(tag, q);
      } else if (it.remove) {                        // 지우기(49d) — 떼어 두고 되돌리면 제자리로. 고른 테두리도 걷는다
        optRec(tag, {el: el, back: {parent: el.parentNode, next: el.nextSibling}}); el.parentNode.removeChild(el);
        if (box && selEl && !selEl.isConnected) box.style.display = 'none';
        return;
      } else if (it.text != null) {
        if (!textOk(el)) { ok = false; return; }
        optRec(tag, {el: el, kids: keepKids(el)}); putText(el, it.text);
      } else return;
      if (!first) first = el;
    });
    reBox();
    send({type: 'hd-opt-done', screen: screenId(), tag: tag || '', ok: ok, hit: first ? hitMsg(first, 'hd-opt-done') : null});
  }
  /* hd-text-key — modules/text-edit.js 의 key 와 같은 규칙(화면 안이라 그 파일을 못 읽음 · test_canvas_unit_text_edit 이 같은 표로 견준다) */
  function textKey(e) {                              // 'save'(Enter · Ctrl/Cmd+Enter · Esc = 저장하고 끝) | 'br'(Shift+Enter) | null
    if (!e || e.isComposing || e.keyCode === 229) return null;   // 한글 조합 중 Enter = 조합 끝내기
    if (e.key === 'Escape') return 'save';
    if (e.key !== 'Enter') return null;
    if (e.shiftKey && !e.ctrlKey && !e.metaKey) return 'br';
    return 'save';
  }
  /* /hd-text-key */
  function inlineKey(e) {
    e.stopPropagation();                               // 화면 스크립트의 단축키로 새지 않게
    var k = textKey(e); if (!k) return;
    e.preventDefault();
    if (k === 'br') document.execCommand('insertLineBreak'); else inlineEnd(true);
  }
  function inlinePaste(e) {                           // 붙여 넣기 = 글만(서식·요소 없이)
    var t = e.clipboardData && e.clipboardData.getData('text/plain');
    if (t == null) return;
    e.preventDefault(); document.execCommand('insertText', false, t);
  }
  function inlineBlur() { if (inl) inlineEnd(true); }
  function iconEditor(el) {                           // 첫 글 묶음(앞뒤 공백 뺀 글)을 span 하나로 감싸 돌려준다 — 끝나면 inlineEnd 가 원래 마디로 되돌린다
    var first = textRuns(el)[0], raw = first.map(function (n) { return n.nodeType === 3 ? n.nodeValue : '\u0000'; }).join('');
    var lead = raw.slice(0, raw.length - raw.replace(/^\s+/, '').length), trail = raw.slice(raw.replace(/\s+$/, '').length);
    var sp = document.createElement('span'); sp.setAttribute('data-hd-txt', '');
    el.insertBefore(sp, first[0]);
    first.forEach(function (n) { sp.appendChild(n); });
    var a = sp.firstChild, z = sp.lastChild;           // 앞뒤 공백은 칸 밖으로(고르기·자리는 글만)
    if (lead && a && a.nodeType === 3) { a.nodeValue = a.nodeValue.slice(lead.length); el.insertBefore(document.createTextNode(lead), sp); }
    if (trail && z && z.nodeType === 3) { z.nodeValue = z.nodeValue.slice(0, z.nodeValue.length - trail.length); el.insertBefore(document.createTextNode(trail), sp.nextSibling); }
    return sp;
  }
  function inlineStart(d) {
    if (inl) inlineEnd(true);
    var el = find(d.path), tag = d.tag || '';
    if (!el || !textOk(el)) { send({type: 'hd-inline-done', screen: screenId(), tag: tag, ok: false, why: el ? 'text' : 'missing', path: d.path || null}); return; }
    var kids0 = keepKids(el), ed = el;
    if (textMode(el) === 'icon') ed = iconEditor(el);    // 아이콘 + 글(R15): 글 조각만 감싼 칸을 고친다 — 아이콘은 칸 밖이라 지워지지 않는다
    inl = {el: el, ed: ed, tag: tag, kids: kids0, was: plainOf(ed), ce: ed.getAttribute('contenteditable'), o: el.style.outline, oo: el.style.outlineOffset};
    if (box) box.style.display = 'none';
    ed.setAttribute('contenteditable', 'true');
    el.style.outline = '2px solid #2563eb'; el.style.outlineOffset = '2px';
    ed.addEventListener('keydown', inlineKey, true); ed.addEventListener('paste', inlinePaste); ed.addEventListener('blur', inlineBlur);
    ed.focus({preventScroll: true});
    try { var r = document.createRange(); r.selectNodeContents(ed); var sl = getSelection(); sl.removeAllRanges(); sl.addRange(r); } catch (e) { console.warn('[hd] 글 전체를 고르지 못함 — ' + e); }
    send({type: 'hd-inline-on', screen: screenId(), tag: tag, path: d.path});
  }
  function inlineEnd(save, away) {                    // away = 다른 곳을 눌러 끝냄(R52) — 캔버스가 이 요소를 다시 고르지 않는다(누른 것이 골라진다)
    var q = inl; if (!q) return; inl = null;
    var el = q.el, ed = q.ed || el;
    ed.removeEventListener('keydown', inlineKey, true); ed.removeEventListener('paste', inlinePaste); ed.removeEventListener('blur', inlineBlur);
    if (q.ce === null) ed.removeAttribute('contenteditable'); else ed.setAttribute('contenteditable', q.ce);
    el.style.outline = q.o; el.style.outlineOffset = q.oo;
    try { var sl = getSelection(); if (sl && sl.anchorNode && el.contains(sl.anchorNode)) sl.removeAllRanges(); } catch (e) { console.warn('[hd] 선택 풀기 실패 — ' + e); }
    if (document.activeElement === ed) ed.blur();
    try { if (window.parent && window.parent !== window) window.parent.focus(); } catch (e) { console.warn('[hd] 캔버스로 초점 돌리기 실패 — ' + e); }   // 다음 키(도구 키·Tab·Enter)가 이 틀이 아니라 캔버스로(답 메시지보다 먼저, 51-2)
    var v = plainOf(ed), path = pathOf(el);
    if (!save || v === q.was) {                        // 취소·그대로 = 원래 마디로
      putKids(el, q.kids);
      send({type: 'hd-inline-done', screen: screenId(), tag: q.tag, ok: false, why: save ? 'same' : 'cancel', path: path, text: q.was, old: q.was, away: !!away});
      return;
    }
    if (ed !== el) { putKids(el, q.kids); setIconText(el, v); } else setText(el, v);   // 아이콘 + 글: 원래 마디로 되돌린 뒤 글 조각만(도우미가 쓸 모양과 같게)
    optRec(q.tag, {el: el, kids: q.kids});
    send({type: 'hd-inline-done', screen: screenId(), tag: q.tag, ok: true, path: path, text: v, old: q.was, away: !!away});
  }
  function kids(p) {                                 // 고를 수 있는 자식 요소(51-2) — 옮기기 sibsOf 와 같은 빼기
    return p ? Array.prototype.filter.call(p.children, function (c) {
      return !SIB_SKIP.test(c.tagName.toLowerCase()) && !c.hasAttribute('data-hd-dup') && !c.hasAttribute('data-hd-pick') && !c.hasAttribute('data-hd-links');
    }) : [];
  }
  function hop(d) {                                   // hd-down(첫 자식) · hd-sib(다음·앞 형제, 끝에서 돈다) → hd-hop
    var el = find(d.path), to = null;
    if (el && d.type === 'hd-down') to = kids(el)[0] || null;
    else if (el && el.parentElement && el.parentElement !== document.documentElement) {
      var list = kids(el.parentElement), i = list.indexOf(el), n = list.length;
      if (i >= 0 && n > 1) to = list[(i + (+d.dir < 0 ? -1 : 1) + n) % n];
    }
    var m = to ? hitMsg(to, 'hd-hop') : {type: 'hd-hop', screen: screenId(), path: null};
    m.tag = d.tag || ''; send(m);
  }
  function sibsOf(d) {
    var el = find(d.path), p = el && el.parentElement, list = [];
    if (p) Array.prototype.forEach.call(p.children, function (c) {
      if (c === el || (!SIB_SKIP.test(c.tagName.toLowerCase()) && !c.hasAttribute('data-hd-dup') && !c.hasAttribute('data-hd-pick') && !c.hasAttribute('data-hd-links'))) list.push(c);
    });
    send({type: 'hd-sibs', screen: screenId(), tag: d.tag || '', path: d.path || null, index: el ? list.indexOf(el) : -1, rects: list.map(rectOf)});
  }
  addEventListener('pointerdown', function (e) {   // window 단계 = block() 보다 먼저 · 고른 요소를 눌러 끌기(크게 보기 고르기 도구) — 끼울 자리는 캔버스가 그린다
    grab = null;
    pressInl = !!(inl && editOn && e.button === 0 && !inEdit(e) && picking && pickMode === 'select' && window.parent && window.parent !== window);   // 선택(V)만(HD.textEdit.press — 글자 도구는 누르면 원래 고치고, 손은 화면 체험)
    if (editOn && e.button === 0 && window.parent && window.parent !== window) send({type: 'hd-press', screen: screenId()});   // 캔버스 우클릭 메뉴 닫기
    if (!picking || pickMode !== 'select' || !selEl || !selEl.isConnected || inEdit(e) || e.button !== 0) return;
    if (!(e.target && e.target.nodeType === 1 && selEl.contains(e.target))) return;
    grab = {x: e.clientX, y: e.clientY, on: false};
  }, true);
  addEventListener('pointermove', function (e) {
    if (!grab) return;
    if (!grab.on) {
      if (Math.abs(e.clientX - grab.x) + Math.abs(e.clientY - grab.y) < 4) return;
      grab.on = true; send({type: 'hd-grab', screen: screenId(), phase: 'start', x: grab.x, y: grab.y, alt: e.altKey});
    }
    grab.cx = e.clientX; grab.cy = e.clientY;
    send({type: 'hd-grab', screen: screenId(), phase: 'move', x: e.clientX, y: e.clientY, alt: e.altKey});
  }, true);
  function grabAlt(e) {                               // 끄는 중 Alt 누름·뗌 = 복제 표시를 바로(포인터를 움직이지 않아도, 51-5) — 브라우저 메뉴로 새지 않게
    if (!grab || !grab.on || e.key !== 'Alt') return;
    e.preventDefault();
    send({type: 'hd-grab', screen: screenId(), phase: 'move', x: grab.cx == null ? grab.x : grab.cx, y: grab.cy == null ? grab.y : grab.cy, alt: e.type === 'keydown'});
  }
  addEventListener('keydown', grabAlt, true);
  addEventListener('keyup', grabAlt, true);
  function grabEnd(e) {
    var g = grab; grab = null;
    if (!g || !g.on) return;
    grabbed = e.type === 'pointerup';
    send({type: 'hd-grab', screen: screenId(), phase: e.type === 'pointerup' ? 'end' : 'cancel', x: e.clientX, y: e.clientY, alt: e.altKey});
  }
  addEventListener('pointerup', grabEnd, true);
  addEventListener('pointercancel', grabEnd, true);
  var pend = [];
  function pending(items) {                           // 반영 대기: 글 = 안의 마디를 떼어 두고 새 글로 · 지우기 = 숨김 — 다음 호출에서 처음대로(떼어 둔 마디를 그대로 되돌림)
    pend.reverse().forEach(function (q) {
      if (q.added && q.added.parentNode) q.added.parentNode.removeChild(q.added);
      if (q.back) q.back.parent.insertBefore(q.el, q.back.next && q.back.next.parentNode === q.back.parent ? q.back.next : null);
      if (q.kids) { while (q.el.firstChild) q.el.removeChild(q.el.firstChild); q.kids.forEach(function (k) { q.el.appendChild(k); }); }
      if (q.disp !== undefined) q.el.style.display = q.disp;
      if (q.attr) { if (q.attr.had) q.el.setAttribute(q.attr.name, q.attr.v); else q.el.removeAttribute(q.attr.name); }
      q.el.style.outline = q.o; q.el.style.outlineOffset = q.oo;
    });
    pend = [];
    var els = (items || []).map(function (it) { return find(it.path); });   // 모두 바꾸기 전 문서에서 찾는다(도우미도 한 원문에서 고른다)
    (items || []).forEach(function (it, i) {
      var el = els[i];
      if (!el) return;
      var q = {el: el, o: el.style.outline, oo: el.style.outlineOffset};
      if (it.remove) { q.disp = el.style.display; el.style.display = 'none'; pend.push(q); return; }
      if (it.attr) {                                   // 속성(task 49b): 허용 목록만 잠시 바꿔 점선
        if ((ATTR_OK[el.tagName.toLowerCase()] || []).indexOf(it.attr) < 0) return;
        q.attr = {name: it.attr, had: el.hasAttribute(it.attr), v: el.getAttribute(it.attr)};
        el.setAttribute(it.attr, String(it.value == null ? '' : it.value));
        el.style.outline = '2px dashed #f59e0b'; el.style.outlineOffset = '2px'; pend.push(q); return;
      }
      if (it.dup) {                                    // 복제: 바로 뒤에 점선 복사본(id·data-region 뺌)
        var cp = el.cloneNode(true);
        [cp].concat(Array.prototype.slice.call(cp.querySelectorAll('[id],[data-region]'))).forEach(function (n) { n.removeAttribute('id'); n.removeAttribute('data-region'); });
        cp.setAttribute('data-hd-dup', ''); cp.style.outline = '2px dashed #f59e0b'; cp.style.outlineOffset = '2px';
        el.parentNode.insertBefore(cp, el.nextSibling); q.added = cp; pend.push(q); return;
      }
      if (it.to != null) {                             // 자리로 옮기기(51-3, 도우미 없이 끈 반영 대기) — hd-opt {path, to} 와 같은 자리, 되돌릴 때 원래 다음 마디 앞으로
        var back = {parent: el.parentNode, next: el.nextSibling};
        if (!placeAt(el, kids(el.parentElement).filter(function (c) { return c !== el; }), it.to, el.parentNode)) return;
        q.back = back; el.style.outline = '2px dashed #f59e0b'; el.style.outlineOffset = '2px'; pend.push(q); return;
      }
      if (it.move) {                                   // 옮기기: 형제와 자리 바꿈 — 되돌릴 때 원래 다음 마디 앞으로
        var to = sib(el, it.move === 'up' ? -1 : 1); if (!to) return;
        q.back = {parent: el.parentNode, next: el.nextSibling};
        el.parentNode.insertBefore(el, it.move === 'up' ? to : to.nextSibling);
        el.style.outline = '2px dashed #f59e0b'; el.style.outlineOffset = '2px'; pend.push(q); return;
      }
      if (!textOk(el)) return;                         // 도우미도 거절할 요소 — 일부만 바꿔 보이지 않는다
      q.kids = Array.prototype.slice.call(el.childNodes);
      var icon = textMode(el) === 'icon';                // 아이콘 + 글(R15): 떼어 둔 마디의 복사본을 다시 놓고 글 조각만 바꾼다
      q.kids.forEach(function (k) { el.removeChild(k); });
      if (icon) { q.kids.forEach(function (k) { el.appendChild(k.cloneNode(true)); }); setIconText(el, it.text); }
      else setText(el, it.text);
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
      var o = 2 + 4 * (seen[it.path] || 0);            // 같은 요소의 두 번째 쌍부터 바깥으로(2px 틈)
      seen[it.path] = (seen[it.path] || 0) + 1;
      var r = el.getBoundingClientRect(), d = document.createElement('div');
      d.setAttribute('data-hd-links', '');
      d.style.cssText = 'position:absolute;z-index:2147483646;pointer-events:none;border-radius:6px;box-sizing:border-box;' +
        'left:' + (r.left + scrollX - o) + 'px;top:' + (r.top + scrollY - o) + 'px;width:' + (r.width + 2 * o) + 'px;height:' + (r.height + 2 * o) + 'px;' +
        (it.hi ? 'border:2px solid ' + it.color + ';box-shadow:0 0 0 3px rgba(255,255,255,.85),0 0 0 5px ' + it.color + '55;background:' + it.color + '1f'   // R46: 목록 창에서 고른 버튼
               : 'border:1px dashed ' + it.color + ';box-shadow:0 0 0 1px rgba(255,255,255,.6)');   // R27 F08: 화면 내용 위 표시는 얇은 점선 하나 — 디자인과 다투지 않게
      if (it.n) {
        var b = document.createElement('span');
        b.textContent = it.n <= 20 ? String.fromCharCode(0x245F + it.n) : '(' + it.n + ')';
        b.style.cssText = 'position:absolute;right:-8px;top:-9px;min-width:16px;height:16px;padding:0 2px;box-sizing:border-box;border-radius:999px;background:' + it.color +
          ';color:#fff;font:600 10px/16px sans-serif;text-align:center';
        d.appendChild(b);
      }
      document.documentElement.appendChild(d); paints.push(d);
    });
  }

  send({type: 'hd-here', screen: screenId()});
  var editOn = false;                                   // 크게 보기(hd-edit) — 두 번 누르기 고치기·오른쪽 메뉴·스크롤 알림
  document.addEventListener('contextmenu', function (e) {   // 크게 보기 오른쪽 클릭 → 캔버스 요소 메뉴(task 49a)
    if (!editOn || !window.parent || window.parent === window) return;
    e.preventDefault(); e.stopPropagation();
    var at = e.target && e.target.nodeType === 1 ? e.target : null;
    var x = e.clientX, y = e.clientY;
    if (!at || at === document.documentElement || at === document.body) { send({type: 'hd-ctx', screen: screenId(), path: null, x: x, y: y}); return; }
    var m = hitMsg(linkAt(at) || (at.closest ? at.closest(HIT_SEL) : null) || at, 'hd-ctx');   // 판 우클릭(hd-hit-at)과 같은 요소 고르기
    m.x = x; m.y = y; send(m);
  }, true);
  var scrollT = 0;
  addEventListener('scroll', function () {             // 고른 요소 막대는 화면 좌표라 스크롤하면 캔버스가 걷는다
    if (!editOn || !window.parent || window.parent === window || scrollT) return;
    scrollT = setTimeout(function () { scrollT = 0; }, 150); send({type: 'hd-scroll', screen: screenId()});
  }, true);
  addEventListener('message', function (e) {
    var d = e.data; if (!d) return;
    if (d.type === 'hd-palette') apply(d.slug);
    else if (d.type === 'hd-theme-vars') themeVars(d.vars || {});
    else if (d.type === 'hd-links') { if (d.on) send({type: 'hd-links', screen: screenId(), accent: accent(), docHeight: docHeight(), links: links()}); else paint([]); }
    else if (d.type === 'hd-links-paint') paint(d.items);
    else if (d.type === 'hd-link-at') sendGo(linkAt(document.elementFromPoint(+d.x || 0, +d.y || 0)));
    else if (d.type === 'hd-hit-at') sendHit(document.elementFromPoint(+d.x || 0, +d.y || 0), !!d.leaf, 'hd-hit', !!d.deep);
    else if (d.type === 'hd-down' || d.type === 'hd-sib') hop(d);
    else if (d.type === 'hd-pending') pending(d.items);
    else if (d.type === 'hd-inline') inlineStart(d);
    else if (d.type === 'hd-opt') opt(d.tag, d.items);
    else if (d.type === 'hd-opt-undo') optUndo(d.tag);
    else if (d.type === 'hd-sibs') sibsOf(d);
    else if (d.type === 'hd-up') {                     // 상위 고르기(task 49b) → {type:'hd-upchain', tag, path, chain}
      var ue = find(d.path);
      send({type: 'hd-upchain', screen: screenId(), tag: d.tag || '', path: d.path || null, chain: ue ? upChain(ue) : []});
    } else if (d.type === 'hd-find') {                 // 쓴 뒤 다시 실린 화면에서 같은 요소 찾기(task 49b) → {type:'hd-found', tag, …hd-hit 칸} | path null
      whenLoaded(function () {
        var fe = find(d.path), m = fe ? hitMsg(fe, 'hd-found') : {type: 'hd-found', screen: screenId(), path: null};
        m.tag = d.tag || ''; send(m);
      });
    }
    else if (d.type === 'hd-locate') locate(d.items);
    else if (d.type === 'hd-goto') gotoState(d);
    else if (d.type === 'hd-replay') replay(d);
    else if (d.type === 'hd-edit') editOn = !!d.on;
    else if (d.type === 'hd-pick') {
      picking = !!d.on; last = null; pickMode = picking && (d.mode === 'text' || d.mode === 'select') ? d.mode : '';
      if (!picking && box) box.style.display = 'none';
      document.documentElement.style.cursor = picking ? 'crosshair' : '';
      pickDoc = !!d.doc;
      if (d.doc) { if (!picking) unpick(); send({type: 'hd-pick-on', screen: screenId(), on: picking, tokens: document.querySelectorAll('[data-var]').length, parts: document.querySelectorAll('.spec-stage').length}); }
    }
    else if (d.type === 'hd-unpick') unpick();
    else if (d.type === 'hd-css-reload') reloadSheet(d.sheet, d.v);
    else if (d.type === 'hd-tokens-reload') reloadTokens(d.v);   // 옛 이름(R55 phase F) — 옛 캔버스가 보내도 받는다
  });
})();
