/* View — 아래쪽 프로젝트 탭 바(task 44, Xmind 시트 바 모양): 탭 하나 = 프로젝트 하나, 판 아래 왼쪽(S1b — 가운데는 대화창). 도우미가 없으면(file://) 만들지 않는다.
   시작: GET /api/tabs + GET /api/projects → HD.tabs.bar(차례·지금 것 더하기, 더했으면 PUT /api/tabs 로 남김). 지금 탭 = 지금 캔버스(aria-selected).
   누르기 → POST /api/open {name} → 이 탭이 그 주소로 · '+' → 고르기 창(의도 'hd-pick-project') · 두 번 누르기 → 제자리 이름 바꾸기(Enter·blur 확정, Esc 취소,
   빈 값·같은 값 무시 = HD.tabs.rename) → POST /api/project {name, title} → 지금 것이면 의도 'hd-project-title'(머리 제목) · 끌기 → 차례 → PUT /api/tabs.
   우클릭·탭의 ▾ → 메뉴: 이름 바꾸기 · 탭 닫기(하나뿐이면 끔) · 다른 탭 닫기 · 폴더 열기(POST /api/reveal) · 홈(의도 'hd-home'). 지금 탭을 닫으면 옆 탭으로 간다.
   넘치면 스크롤바 없이 ◀ ▶(끝이면 끔). Ctrl+Shift+[ / ] = 이전/다음 탭. 떠날 때 보내지 않은 상태 쓰기는 view-state-sync 의 pagehide 길이 마저 보낸다.
   실패(4xx/5xx {error}·끊김)는 토스트 + 되돌림. 상태: 탭 이름 차례·제목·끄는 중·이름 바꾸는 중·여는 중(이 View 만).
   HD.feature('tabs', {needs: ['api', '$', 'esc', 'toast']}) → {reload(), names()} | {} (도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#ptabs{position:fixed;bottom:10px;left:12px;z-index:6;display:flex;align-items:center;gap:2px;' +
    'height:32px;padding:3px;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.14);font-size:12px;color:#3a3a37;-webkit-user-select:none;user-select:none}' +
  '#ptabs[hidden],body.bare #ptabs,body.modal-open #ptabs{display:none}' +
  'body.has-ptabs #toast{bottom:56px}' +
  '#ptabs .pt-strip{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;min-width:0;position:relative}' +
  '#ptabs .pt-strip::-webkit-scrollbar{display:none}' +
  '#ptabs .pt-tab{flex:none;display:flex;align-items:center;gap:2px;height:26px;max-width:180px;padding:0 4px 0 10px;border-radius:7px;color:#6b6b66;cursor:pointer;position:relative}' +
  '#ptabs .pt-tab:hover{background:#F2F2EF;color:#2b2b29}' +
  '#ptabs .pt-tab[aria-selected="true"]{background:#ECECE8;color:#1c1c1c;font-weight:600}' +
  '#ptabs .pt-tab[data-state="missing"] .pt-name{color:#9a9a95;text-decoration:line-through}' +
  '#ptabs .pt-tab[aria-busy="true"]{cursor:progress;opacity:.6}' +
  '#ptabs .pt-tab.drag{opacity:.45}' +
  '#ptabs .pt-tab:focus-visible{outline:2px solid var(--ui-mark);outline-offset:-2px}' +
  '#ptabs .pt-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}' +
  '#ptabs .pt-in{width:140px;height:22px;border:2px solid var(--ui-mark);border-radius:5px;padding:0 4px;font:inherit;font-weight:600;color:#1c1c1c}' +
  '#ptabs .pt-more{flex:none;width:18px;height:18px;padding:0;border:0;border-radius:4px;background:none;color:#8a8a85;font-size:9px;cursor:pointer;visibility:hidden}' +
  '#ptabs .pt-tab:hover .pt-more,#ptabs .pt-tab[aria-selected="true"] .pt-more{visibility:visible}' +
  '#ptabs .pt-more:hover{background:#E1E1DC;color:#2b2b29}' +
  '#ptabs .pt-arrow,#ptabs .pt-add{flex:none;width:26px;height:26px;padding:0;border:0;border-radius:7px;background:none;color:#55554f;cursor:pointer;display:grid;place-items:center}' +
  '#ptabs .pt-arrow{font-size:9px}#ptabs .pt-arrow[hidden]{display:none}' +
  '#ptabs .pt-arrow:disabled{color:#c9c9c4;cursor:default;background:none}' +
  '#ptabs .pt-add{font-size:17px;font-weight:300;border-left:1px solid #eee;border-radius:0 7px 7px 0}' +
  '#ptabs .pt-arrow:not(:disabled):hover,#ptabs .pt-add:hover{background:#F2F2EF;color:#1c1c1c}' +
  '#ptabs .pt-drop{position:absolute;top:3px;bottom:3px;width:2px;background:var(--ui-mark);border-radius:1px;pointer-events:none}' +
  '#ptmenu .wm-row:disabled{color:#b5b5b0;cursor:default;background:none}';

function mount(ctx) {
  if (!ctx.api.on) return {};                       // file:// 또는 도우미 없음 — 탭 바 없음
  var $ = ctx.$, esc = ctx.esc, T = HD.tabs, P = HD.projects;

  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var nav = document.createElement('nav');
  nav.id = 'ptabs'; nav.setAttribute('aria-label', '프로젝트 탭'); nav.hidden = true;
  nav.innerHTML = '<button type="button" class="pt-arrow" data-dir="-1" aria-label="앞 탭 보기" hidden>◀</button>' +
    '<div class="pt-strip" role="tablist" aria-label="열어 둔 프로젝트"></div>' +
    '<button type="button" class="pt-arrow" data-dir="1" aria-label="뒤 탭 보기" hidden>▶</button>' +
    '<button type="button" class="pt-add" aria-label="프로젝트 더하기" title="프로젝트 열기·새로 만들기">+</button>';
  document.body.appendChild(nav);
  var strip = $('.pt-strip', nav), prevB = $('.pt-arrow[data-dir="-1"]', nav), nextB = $('.pt-arrow[data-dir="1"]', nav);
  var menu = document.createElement('div');
  menu.id = 'ptmenu'; menu.className = 'wm'; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', '탭'); menu.hidden = true;
  document.body.appendChild(menu);

  var names = [], tabs = {}, cur = null, opening = null, renaming = null, menuFor = null, drag = null;

  function fail(what, e) { ctx.toast(what + ' — ' + (e && e.message || e), false, 6000); }
  function check(res) {
    if (res.status !== 200 || !res.body || res.body.error) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
    return res.body;
  }
  function draw() {
    strip.innerHTML = names.map(function (n) {
      var t = tabs[n];
      return '<div class="pt-tab" role="tab" tabindex="' + (t.current ? 0 : -1) + '" data-name="' + esc(n) + '" data-state="' + esc(t.state) + '"' +
        ' aria-selected="' + (t.current ? 'true' : 'false') + '"' + (opening === n ? ' aria-busy="true"' : '') + ' title="' + esc(t.title) + '">' +
        '<span class="pt-name">' + esc(t.title) + '</span>' +
        '<button type="button" class="pt-more" tabindex="-1" aria-label="' + esc(t.title) + ' 탭 메뉴" aria-haspopup="menu">▼</button></div>';
    }).join('');
    nav.hidden = !names.length;
    document.body.classList.toggle('has-ptabs', !!names.length);
    place();
  }
  function place() {                                // 판(#screens) 아래 왼쪽, 가운데 대화창(#hdchat, 보일 때만) 앞에서 멈춤 — 규칙은 HD.tabs.place
    if (nav.hidden) return;
    nav.dataset.need = Math.ceil(strip.scrollWidth + 34);   // 다 보이는 데 드는 폭(탭들 + '+' 26 + 안쪽 여백 6 + 사이 2) — 대화창이 읽고 폭을 줄여 준다
    var pane = $('#screens'), chat = $('#hdchat');
    var pr = pane && pane.getClientRects().length ? pane.getBoundingClientRect() : {left: 0, right: innerWidth};
    var cl = chat && !chat.classList.contains('docked') && chat.getClientRects().length ? chat.getBoundingClientRect().left : null;   // 숨긴 대화창(display:none)·대화 패널 안 대화창(S3)은 판 아래 자리가 없다
    var p = T.place(pr, cl);
    nav.style.maxWidth = p.max + 'px';
    nav.style.left = p.left + 'px';
    arrows();
  }
  function arrows() {
    var a = T.arrows(strip.scrollLeft, strip.scrollWidth, strip.clientWidth);
    prevB.hidden = nextB.hidden = !a.over; prevB.disabled = !a.prev; nextB.disabled = !a.next;
  }
  function tabEl(n) {
    return strip.querySelector('.pt-tab[data-name="' + window.CSS.escape(n) + '"]');
  }
  function reveal(n) {
    var el = tabEl(n); if (!el) return;
    var l = el.offsetLeft, r = l + el.offsetWidth;
    if (l < strip.scrollLeft) strip.scrollLeft = l - 8;
    else if (r > strip.scrollLeft + strip.clientWidth) strip.scrollLeft = r - strip.clientWidth + 8;
    arrows();
  }
  function save(next, before) {                      // 차례를 도우미에 남긴다 — 실패하면 그대로 되돌린다
    names = next; draw();
    return ctx.api.call('PUT', '/api/tabs', {tabs: next}).then(check).catch(function (e) {
      names = before; draw();
      fail('탭을 저장하지 못했어요', e);
      throw e;
    });
  }

  function load() {
    return Promise.all([ctx.api.call('GET', '/api/tabs'), ctx.api.call('GET', '/api/projects')]).then(function (rs) {
      var tb = check(rs[0]);
      if (rs[1].status !== 200) throw new Error(rs[1].body && rs[1].body.error || ('도우미 답 ' + rs[1].status));
      var pr = P.rows(rs[1].body, window.__hdOut || null), me = P.current(pr.rows);
      if (pr.bad) console.warn('[hd] 프로젝트 목록: ' + pr.bad);
      if (!me) console.warn('[hd] 이 캔버스가 프로젝트 목록에 없어 탭에 더하지 않아요');
      cur = me ? me.name : null;
      var b = T.bar(tb.tabs, pr.rows, cur);
      if (b.dropped) console.warn('[hd] 탭 목록에서 모르는 프로젝트 ' + b.dropped + '개를 뺐어요');
      tabs = {}; b.tabs.forEach(function (t) { tabs[t.name] = t; });
      names = b.names; draw();
      if (cur) reveal(cur);
      if (b.added) return ctx.api.call('PUT', '/api/tabs', {tabs: names}).then(check).catch(function (e) { console.warn('[hd] 지금 프로젝트를 탭 목록에 남기지 못했어요: ' + (e && e.message || e)); });
    }).catch(function (e) {
      console.error('[hd] 프로젝트 탭: ' + (e && e.message || e));
      fail('프로젝트 탭을 불러오지 못했어요', e);
    });
  }

  function go(n) {                                   // 그 프로젝트로 이 탭이 간다
    if (!n || n === cur || opening) return;
    var t = tabs[n];
    if (t && t.state === 'missing') { ctx.toast('이 프로젝트의 폴더가 없어 열 수 없어요 — 홈에서 목록에서 뺄 수 있어요', false, 6000); return; }
    opening = n; draw();
    ctx.api.call('POST', '/api/open', {name: n}).then(check).then(function (b) {
      if (!b.url) throw new Error('도우미가 주소를 주지 않았어요');
      opening = null;
      location.assign(b.url);
    }).catch(function (e) { opening = null; draw(); fail('열지 못했어요', e); });
  }
  function intent(type, detail) {
    var ev = new CustomEvent(type, {cancelable: true, detail: detail});
    document.dispatchEvent(ev);
    return ev.defaultPrevented;
  }

  function rename(n) {
    var el = tabEl(n); if (!el || renaming) return;
    closeMenu();
    renaming = n;
    var nameEl = $('.pt-name', el), old = tabs[n].title;
    var inp = document.createElement('input');
    inp.className = 'pt-in'; inp.value = old; inp.maxLength = T.MAX; inp.setAttribute('aria-label', '탭 이름');
    nameEl.replaceWith(inp); inp.focus(); inp.select();
    var done = false;
    function finish(commit) {
      if (done) return; done = true; renaming = null;
      var r = commit ? T.rename(old, inp.value) : {ok: false};
      if (!r.ok) { draw(); return; }
      tabs[n].title = r.title; draw();
      ctx.api.call('POST', '/api/project', {name: n, title: r.title}).then(check).then(function () {
        if (n === cur) intent('hd-project-title', {name: n, title: r.title, current: true});
      }).catch(function (e) { tabs[n].title = old; draw(); fail('이름을 바꾸지 못했어요', e); });
    }
    inp.addEventListener('keydown', function (e) {
      e.stopPropagation();                           // 판 단축키(H·V·0…)가 받지 않게
      if (e.key === 'Enter') { e.preventDefault(); finish(true); }
      else if (e.key === 'Escape') { e.preventDefault(); finish(false); }
    });
    inp.addEventListener('blur', function () { finish(true); });
    inp.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
    inp.addEventListener('dblclick', function (e) { e.stopPropagation(); });
  }
  function closeTab(n) {
    var r = T.close(names, n, cur);
    if (!r.ok) { ctx.toast(r.why); return; }
    save(r.names, names.slice()).then(function () { if (r.go) go(r.go); }, function () {});
  }
  function closeOthers(n) {
    var r = T.others(names, n, cur);
    if (!r.ok) { ctx.toast(r.why); return; }
    save(r.names, names.slice()).then(function () { if (r.go) go(r.go); }, function () {});
  }
  function revealFolder(n) {
    ctx.api.call('POST', '/api/reveal', {name: n}).then(check).catch(function (e) { fail('폴더를 열지 못했어요', e); });
  }

  function openMenu(n, x, y) {
    menuFor = n;
    var one = names.length < 2;
    menu.innerHTML =
      '<button type="button" class="wm-row" role="menuitem" data-do="rename">이름 바꾸기</button>' +
      '<button type="button" class="wm-row" role="menuitem" data-do="close"' + (one ? ' disabled aria-disabled="true"' : '') + '>탭 닫기</button>' +
      '<button type="button" class="wm-row" role="menuitem" data-do="others"' + (one ? ' disabled aria-disabled="true"' : '') + '>다른 탭 닫기</button>' +
      '<hr><button type="button" class="wm-row" role="menuitem" data-do="reveal">폴더 열기</button>' +
      '<button type="button" class="wm-row" role="menuitem" data-do="home">홈</button>';
    menu.hidden = false;
    var w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(8, Math.min(innerWidth - w - 8, x)) + 'px';
    menu.style.top = Math.max(8, Math.min(innerHeight - h - 8, y - h - 4)) + 'px';   // 바가 아래에 있으니 위로 연다
    var first = menu.querySelector('.wm-row:not(:disabled)'); if (first) first.focus();
  }
  function closeMenu() { menu.hidden = true; menuFor = null; }
  menu.addEventListener('click', function (e) {
    var b = e.target.closest('button.wm-row'); if (!b || b.disabled) return;
    var n = menuFor, what = b.dataset.do;
    closeMenu();
    if (what === 'rename') rename(n);
    else if (what === 'close') closeTab(n);
    else if (what === 'others') closeOthers(n);
    else if (what === 'reveal') revealFolder(n);
    else if (what === 'home' && !intent('hd-home')) ctx.toast('홈 단추가 붙지 않아 홈을 열 수 없어요');
  });
  menu.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(); return; }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    var rows = Array.prototype.slice.call(menu.querySelectorAll('.wm-row:not(:disabled)')), i = rows.indexOf(document.activeElement);
    var nx = rows[(i + (e.key === 'ArrowDown' ? 1 : -1) + rows.length) % rows.length]; if (nx) nx.focus();
  });
  document.addEventListener('pointerdown', function (e) {
    if (menu.hidden || (e.target.closest && e.target.closest('#ptmenu, .pt-more'))) return;
    closeMenu();
  }, true);

  // 누르기·끌기: 4px 넘게 움직이면 끌기(차례 바꾸기), 아니면 누르기(열기). 이름 바꾸는 중엔 끌지 않는다
  strip.addEventListener('pointerdown', function (e) {
    var el = e.target.closest('.pt-tab');
    if (!el || e.button !== 0 || renaming || e.target.closest('.pt-more')) return;
    drag = {name: el.dataset.name, el: el, x: e.clientX, on: false, id: e.pointerId, mark: null};
  });
  addEventListener('pointermove', function (e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.on) {
      if (Math.abs(e.clientX - drag.x) < 4) return;
      drag.on = true; drag.el.classList.add('drag');
      drag.mark = document.createElement('div'); drag.mark.className = 'pt-drop'; strip.appendChild(drag.mark);
    }
    var els = Array.prototype.slice.call(strip.querySelectorAll('.pt-tab'));
    var mids = els.map(function (t) { var r = t.getBoundingClientRect(); return r.left + r.width / 2; });
    var s = T.slot(mids, e.clientX); drag.slot = s;
    var ref = els[s], sr = strip.getBoundingClientRect();
    var x = ref ? ref.getBoundingClientRect().left - 1 : els[els.length - 1].getBoundingClientRect().right + 1;
    drag.mark.style.left = (x - sr.left + strip.scrollLeft) + 'px';
    if (e.clientX < sr.left + 16) strip.scrollLeft -= 8; else if (e.clientX > sr.right - 16) strip.scrollLeft += 8;
  });
  function endDrag(e) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    var d = drag; drag = null;
    if (!d.on) return;                              // 누르기 — click 이 처리
    d.el.classList.remove('drag'); if (d.mark) d.mark.remove();
    d.dragged = true; strip.dataset.dragged = '1'; setTimeout(function () { delete strip.dataset.dragged; }, 0);
    var next = T.move(names, d.name, d.slot == null ? names.indexOf(d.name) : d.slot);
    if (next.join('\n') !== names.join('\n')) save(next, names.slice()).catch(function () {});
  }
  addEventListener('pointerup', endDrag);
  addEventListener('pointercancel', function (e) { if (drag && drag.on) { drag.el.classList.remove('drag'); if (drag.mark) drag.mark.remove(); } drag = null; });
  strip.addEventListener('click', function (e) {
    if (strip.dataset.dragged || renaming) return;
    var more = e.target.closest('.pt-more'), el = e.target.closest('.pt-tab');
    if (!el) return;
    if (more) { var r = more.getBoundingClientRect(); if (!menu.hidden && menuFor === el.dataset.name) closeMenu(); else openMenu(el.dataset.name, r.left, r.top); return; }
    if (e.detail > 1) return;                        // 두 번 누르기의 두 번째 — 이름 바꾸기가 받는다
    go(el.dataset.name);                             // 다른 탭은 한 번 누르면 바로 간다 — 두 번 눌러 이름 바꾸기는 지금 탭(다른 탭은 ▾ 메뉴)
  });
  strip.addEventListener('dblclick', function (e) {
    var el = e.target.closest('.pt-tab'); if (!el || e.target.closest('.pt-more')) return;
    rename(el.dataset.name);
  });
  strip.addEventListener('contextmenu', function (e) {
    var el = e.target.closest('.pt-tab'); if (!el) return;
    e.preventDefault(); openMenu(el.dataset.name, e.clientX, e.clientY);
  });
  strip.addEventListener('keydown', function (e) {
    var el = e.target.closest && e.target.closest('.pt-tab'); if (!el || e.target !== el) return;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(el.dataset.name); }
    else if (e.key === 'F2') { e.preventDefault(); rename(el.dataset.name); }
    else if (e.key === 'ContextMenu' || (e.shiftKey && e.key === 'F10')) { e.preventDefault(); var r = el.getBoundingClientRect(); openMenu(el.dataset.name, r.left, r.top); }
  });
  strip.addEventListener('scroll', arrows);
  addEventListener('resize', place);
  if (window.ResizeObserver) {                       // 도크 폭·대화창 크기·보이기가 바뀌면 다시 놓는다
    var ro = new ResizeObserver(function () { place(); });
    ['#screens', '#hdchat'].forEach(function (sel) { var el = $(sel); if (el) ro.observe(el); });
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);   // 글꼴이 늦게 오면 탭 글 폭이 바뀐다
  prevB.addEventListener('click', function () { strip.scrollLeft -= Math.max(80, strip.clientWidth * 0.6); arrows(); });
  nextB.addEventListener('click', function () { strip.scrollLeft += Math.max(80, strip.clientWidth * 0.6); arrows(); });
  $('.pt-add', nav).addEventListener('click', function () {
    if (!intent('hd-pick-project')) ctx.toast('프로젝트 고르기 창이 붙지 않았어요');
  });
  addEventListener('keydown', function (e) {        // Ctrl+Shift+[ / ] — 이전/다음 프로젝트 탭(Xmind 시트와 같은 키)
    if (!(e.ctrlKey || e.metaKey) || !e.shiftKey || e.altKey) return;
    if (e.code !== 'BracketLeft' && e.code !== 'BracketRight') return;
    var t = e.target, tag = t && t.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || (t && t.isContentEditable)) return;
    e.preventDefault();
    var n = T.step(names, cur, e.code === 'BracketLeft' ? -1 : 1);
    if (n) go(n);
  });

  load();
  return {reload: load, names: function () { return names.slice(); }};
}

HD.viewTabs = {mount: mount};
HD.feature('tabs', {needs: ['api', '$', 'esc', 'toast'], mount: mount});
})();
