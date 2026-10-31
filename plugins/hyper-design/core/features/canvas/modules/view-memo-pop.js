/* View — 메모 창(#pop) 하나: 화면 전체·요소·크게 보기 고른 요소(hd-picked, Shift = 묶음에 더하기·빼기)의 메모 쓰기·고치기·지우기·사람 답, 범위·의도 고르기.
   메모 모양 = Model HD.annotation.make·makeId, 여러 장 = HD.memoBatch, 창 틀(옮기기·크기·저장한 자리) = 등록부 기능 popPlace(ctx.frame()) — 없으면 자동 자리만.
   HD.viewMemoPop.mount(ctx) → {card(id | [id]), addCard(id)(메모 화면 모드 Shift+클릭 = 열린 화면 메모에 화면 더하기·빼기), element(id, h, x?, y?, note?), addElement(id, h, x?, y?), elem(id, h, note, inModal, at?), edit(id), del(id), reply(ids, kind, label),
     isOpen(), close(), draft() → 쓰는 중인 초안|null(핀이 고른 요소 테두리), typed() → 열린 창에 사람이 쓴 글이 있나(R52 — 셸은 도구를 바꿀 때 빈 창만 닫는다),
     layer(떠 있는 층 'pop' — view-float-stack: 바깥 누르기 = 빈 창이면 닫기 · 쓴 글이 있으면 남김 · 메모 도구가 누르는 카드·크게 보기 틀은 여는 것)}
   쓰던 글 지키기(U1): 추가하지 않고 닫으면(Esc · × · 크게 보기 닫기 · 탭 바꾸기) 사람이 쓴 글을 그 대상 열쇠로 하나 맡겨 두고(HD.floatStack.stash),
     같은 메모 고치기·같은 대상 새 메모를 다시 열면 되살린다 + 토스트.
   ctx = {$, $$, esc, notes(NS), save(), record(op), toast(msg), title(id), modal() → {open, screen, scale, box, picking, frame}, setScreen(id), frame() → popPlace|null,
          cardEl(id), pins()(핀 다시), focusPin(id), feeds(target) → 그 누르기가 메모 도구로 이 창을 다시 정하나}
   첨부 이미지(R22): #pop 이 [data-hd-attach] 상자(칩 자리·📎 는 mount 가 만든다) — 붙이기·저장·칩은 등록부 기능 attach(view-attach), 여기서는 의도만:
     열 때 'hd-attach-set'(새 메모 = 비움 · 고치기 = 메모의 attach) · 추가/저장 때 'hd-attach-get' → 메모 칸 attach:[{path, rel, type, size, name}] + 글 끝 '첨부 이미지: <경로>' 줄(HD.attach.withText)
     · 올리는 중이면 토스트하고 기다림 · 닫으면 비움
   쓰는 창 모양(R27 F09 — 메모 묶음 #thread 와 한 식구): 머리 줄 = 대상 이름(끌기 손잡이, 내부 경로는 꼬리말 title 만 — #ppath 는 숨김) + 닫기 ×(#pcancel),
     글 칸, 아이콘 한 줄 = 의도 [바꾸기|질문] · 범위 아이콘 셋(#pscope, 이름은 aria-label + 꼬리말 #poptip — #thtip 과 같은 모양, 기본값이 이미 골라져 있다) · 📎 · 추가.
     자동 자리 = 대상(크게 보기 고른 요소 · 판 위 요소 · 카드) 옆, 덮지 않게 — 규칙은 Model HD.popSide.beside(판 자리 → 화면 차례) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, NS = ctx.notes, pop = $('#pop'), draft = null, editing = null;
  var typed = false;                                  // 이 창을 연 뒤 사람이 글 칸에 쳤나(미리 채운 글은 아님) — 열 때마다 처음으로, Shift+클릭 묶음 바꾸기는 그대로
  var kept = null;                                    // 추가하지 않고 닫은 쓰던 글 하나(HD.floatStack.stash) — 저장하지 않음
  var newId = function () { return HD.annotation.makeId(Date.now(), Math.random()); };
  var AT = HD.attach;
  var ICON = {                                        // 범위·닫기 아이콘(R27 F09) — 메모 묶음 아이콘과 같은 선 굵기
    element: '<svg viewBox="0 0 24 24"><rect x="3.5" y="3.5" width="17" height="17" rx="2.5" stroke-dasharray="3 2.6"/><rect x="8.5" y="8.5" width="7" height="7" rx="1.2"/></svg>',
    screen: '<svg viewBox="0 0 24 24"><rect x="6" y="3" width="12" height="18" rx="2.5"/></svg>',
    all: '<svg viewBox="0 0 24 24"><rect x="3" y="7" width="10" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-4"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>'};
  var WORD = {change: '바꾸기', question: '질문'}, PH = {change: '무엇을 바꿀지 적어 주세요…', question: '무엇이 궁금한지 적어 주세요…'};
  var tip = null;
  (function compose() {                               // 템플릿 마크업을 한 식구 모양으로 다시 놓기(R27 F09) — 머리 줄(이름 + ×) · 아이콘 한 줄
    if (typeof document.createElement !== 'function' || !pop.insertBefore) return;
    var title = $('#ptitle'), path = $('#ppath'), cancel = $('#pcancel'), intent = $('#pintent'), scope = $('#pscope');
    var head = document.createElement('div'); head.className = 'phead';
    pop.insertBefore(head, title); head.appendChild(title);
    cancel.className = 'pib pclose'; cancel.type = 'button'; cancel.innerHTML = ICON.close;
    cancel.setAttribute('aria-label', '닫기'); cancel.dataset.tip = '닫기 (Esc)'; head.appendChild(cancel);
    if (path) path.hidden = true;                     // 내부 경로는 꼬리말(#ptitle title)만
    var row = intent.parentNode, old = scope.parentNode;
    row.insertBefore(scope, intent.nextSibling);
    if (old !== row && old.parentNode && !old.children.length) old.parentNode.removeChild(old);
    intent.setAttribute('aria-label', '의도');
    $$('#pintent button').forEach(function (b) { b.type = 'button'; b.textContent = WORD[b.dataset.intent] || b.dataset.intent; });
    tip = document.createElement('div'); tip.id = 'poptip'; tip.hidden = true; tip.setAttribute('role', 'tooltip');
    document.body.appendChild(tip);
  })();
  function showTip(b) {                               // 꼬리말 — #thtip 과 같은 자리 규칙(단추 위, 넘치면 아래)
    if (!tip || !b || !b.dataset.tip || pop.hidden) { hideTip(); return; }
    tip.textContent = b.dataset.tip; tip.hidden = false;
    var r = b.getBoundingClientRect(), x = Math.max(4, Math.min(innerWidth - tip.offsetWidth - 4, r.left + r.width / 2 - tip.offsetWidth / 2)), y = r.top - tip.offsetHeight - 6;
    if (y < 4) y = r.bottom + 6;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  function hideTip() { if (tip) tip.hidden = true; }

  function att(type, items) {                         // 첨부 상자 의도(view-attach) — 그 기능이 없으면(붙지 못함·테스트) done=false, 첨부 없음
    var d = {items: items || [], busy: 0, done: false};
    if (typeof CustomEvent === 'function' && pop.dispatchEvent) pop.dispatchEvent(new CustomEvent(type, {bubbles: true, detail: d}));
    return d;
  }
  (function attachBox() {                             // 칩 자리(글 칸 아래) · 클립 단추(취소 앞) — 마크업은 셸이 아니라 이 창의 것
    if (!pop.setAttribute || typeof document.createElement !== 'function') return;
    pop.setAttribute('data-hd-attach', 'memo');
    var note = $('#pnote'), cancel = $('#pcancel');
    var slot = document.createElement('div'); slot.className = 'hd-att pattach'; slot.setAttribute('data-hd-attach-slot', ''); slot.hidden = true; slot.style.marginTop = '6px';
    if (note && note.parentNode) note.parentNode.insertBefore(slot, note.nextSibling);
    var b = document.createElement('button'); b.type = 'button'; b.className = 'nbtn patt'; b.setAttribute('data-hd-attach-pick', '');
    b.title = '이미지 첨부 — 붙여넣기(Ctrl+V)·끌어 놓기도 돼요'; b.setAttribute('aria-label', '이미지 첨부');
    b.innerHTML = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" style="display:block;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round">' +
      '<path d="M21 11.5l-8.6 8.6a5 5 0 0 1-7.1-7.1l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.9-7.9"/></svg>';
    b.className = 'pib patt'; b.dataset.tip = '이미지 첨부 (붙여넣기·끌어 놓기도 돼요)';
    var scope = $('#pscope');                          // 아이콘 한 줄(의도 · 범위 · 📎 · 추가)의 범위 뒤 — 창 안(R22)
    if (scope && scope.parentNode) scope.parentNode.insertBefore(b, scope.nextSibling);
    else if (cancel && cancel.parentNode) cancel.parentNode.insertBefore(b, cancel);
  })();

  function popItem(dr, last) {
    var n = dr.targets.length;
    return {text: n > 1 ? n + '개 요소 · ' + (last.text || '') : last.text, path: dr.targets.map(function (t) { return t.path; }).join('\n'), rect: last.rect};
  }
  function target(rect, at, screen) {               // 창을 옆에 둘 대상 상자(화면 px): 크게 보기 고른 요소 · 판 위 요소 · 카드 · 누른 점 — 화면 밖이면 null
    var m = ctx.modal(), t = null, pt = at ? {x: at.x, y: at.y, w: 1, h: 1} : null;
    if (m.open) {
      if (rect && m.box && (!screen || screen === m.screen)) { var b = m.box.getBoundingClientRect(), s = m.scale; t = {x: b.left + rect.x * s, y: b.top + rect.y * s, w: rect.w * s, h: rect.h * s}; }
      else t = pt;
    } else {
      var c = screen ? ctx.cardEl(screen) : null, ph = c && c.querySelector ? c.querySelector('.phone') : null, f = ph ? ph.querySelector('iframe') : null;
      if (rect && f && f.offsetWidth) { var fr = f.getBoundingClientRect(), k = fr.width / f.offsetWidth; t = {x: fr.left + rect.x * k, y: fr.top + rect.y * k, w: rect.w * k, h: rect.h * k}; }
      else if (pt) t = pt;
      else if (ph) { var pr = ph.getBoundingClientRect(); t = {x: pr.left, y: pr.top, w: pr.width, h: pr.height}; }
    }
    if (!t || t.x + t.w < 0 || t.y + t.h < 0 || t.x > innerWidth || t.y > innerHeight) return null;
    return t;
  }
  function place(rect, at, screen) {                 // at = 누른 자리(판 위 요소 메모) · 저장한 자리가 있으면 그것(popPlace)
    var auto = function () {
      var w = pop.offsetWidth || 320, h = pop.offsetHeight || 240, t = target(rect, at, screen), m = ctx.modal();
      var view = {x: 8, y: 8, w: innerWidth - 16, h: innerHeight - 16};
      if (t) {                                        // 대상 옆(F09) — 판 자리(도크·대화 패널 밖) 먼저, 안 되면 화면 안
        var areas = [view], sc = !m.open ? $('#screens') : null;
        if (sc && sc.getBoundingClientRect) {
          var r = sc.getBoundingClientRect(), top = Math.max(8, r.top + 8), bot = Math.min(r.bottom, innerHeight) - 8;
          if (r.width > w + 16 && bot - top > h) areas.unshift({x: r.left + 8, y: top, w: r.width - 16, h: bot - top});
        }
        var p = HD.popSide.beside(t, {w: w, h: h}, areas);
        return {x: p.x, y: p.y};
      }
      var x = 24, y = 80, notesEl = $('#notes');      // 대상이 화면에 없음 = 메모 패널 왼쪽(고치기를 누른 자리 가까이) · 기본 24,80
      if (notesEl && !notesEl.hidden && notesEl.getBoundingClientRect) { var nb = notesEl.getBoundingClientRect(); x = nb.left - w - 12; y = nb.top; }
      return {x: Math.max(8, Math.min(innerWidth - w - 8, x)), y: Math.max(8, Math.min(innerHeight - h - 8, y))};
    };
    var PP = ctx.frame();
    if (PP) { PP.open(auto, screen ? ctx.cardEl(screen) : null); return; }
    var a = auto(); pop.style.left = a.x + 'px'; pop.style.top = a.y + 'px';   // 틀 기능이 붙지 못했으면(mountAll 이 [hd] 로 알림) 자동 자리만
  }
  function setIntent(v) {
    $$('#pintent button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.intent === v)); });
    var t = $('#pnote'); if (t) t.placeholder = PH[v] || PH.change;   // 글 칸 안내가 고른 의도를 말한다
  }
  function curIntent() { var b = $('#pintent button[aria-pressed="true"]'); return b ? b.dataset.intent : 'change'; }
  function setScope(v) { $$('#pscope button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.scope === v)); }); }
  function curScope() { var b = $('#pscope button[aria-pressed="true"]'); return b ? b.dataset.scope : 'element'; }
  function keyOf() {                                  // 쓰던 글 열쇠 = 고치는 메모 · 새 메모의 화면 + 대상 경로
    if (editing) return 'e:' + editing;
    if (!draft) return null;
    return 'd:' + [].concat(draft.screens || draft.screen).join(',') + '|' + draft.targets.map(function (t) { return t.path; }).join(',');
  }
  function show(item, note, intent, at, scope, keep) {
    if (!keep) typed = false;     // scope 없음 = 기본(화면 전체 메모 = 이 화면, 그 밖 = 이 요소)
    if (!keep) {                                      // 같은 대상에 맡겨 둔 쓰던 글이 있으면 되살린다
      var back = HD.floatStack.take(kept, keyOf()); kept = back.slot;
      if (back.text != null) { note = back.text; typed = true; ctx.toast('쓰던 글을 되살렸어요'); }
    }
    $('#ptitle').textContent = item.text || '(글자 없음)';
    $('#ptitle').title = item.path && item.path !== 'body' ? item.path : '';   // 내부 경로는 꼬리말만(F09)
    $('#pnote').value = note || '';
    setIntent(intent || 'change');
    var many = !editing && HD.memoBatch.multi(draft), sw = {};   // 여러 장 = '이 요소' 없음 · '이 화면' → '고른 화면 N개'
    HD.memoBatch.scopes(many && draft, HD.annotation.SCOPES).forEach(function (s) { sw[s[0]] = s[1]; });
    $$('#pscope button').forEach(function (b) { var w = sw[b.dataset.scope]; b.hidden = !w; if (w) { b.setAttribute('aria-label', w); b.dataset.tip = '범위: ' + w; } });
    setScope(scope || (many ? HD.memoBatch.defaultScope(draft) : item.path === 'body' ? 'screen' : 'element'));
    $('#padd').textContent = editing ? '저장' : '추가';
    var en = editing && NS.find(editing);
    pop.hidden = false; place(item.rect, at, en ? en.screen : draft && draft.screen);
    $('#pnote').focus();
  }
  function hide(done) {                               // done = 추가·저장으로 닫음(맡기지 않음) · 아니면 쓴 글을 맡겨 둔다
    if (!pop.hidden && !done && typed && $('#pnote').value.trim()) kept = HD.floatStack.stash(kept, keyOf(), $('#pnote').value);
    if (pop.contains(document.activeElement)) document.activeElement.blur();
    att('hd-attach-set', []);
    pop.hidden = true; draft = null; editing = null; hideTip();
    var PP = ctx.frame(); if (PP) PP.close();
    ctx.pins();
  }
  function commit() {
    var a = att('hd-attach-get');
    if (a.busy) { ctx.toast('이미지를 올리는 중이에요 — 끝나면 다시 눌러 주세요'); return; }
    var items = a.items || [], note = AT.withText($('#pnote').value.trim(), items), intent = curIntent(), scope = curScope();
    var withAtt = function (m) { if (items.length) m.attach = items.slice(); else delete m.attach; return m; };   // 메모가 첨부 목록을 지닌다(다시 열면 썸네일)
    if (editing) {
      var n = NS.find(editing);
      if (n) { n.note = note; n.intent = intent; n.sent = false; withAtt(n); if (scope === 'element') delete n.scope; else n.scope = scope; }   // 이 요소 = 칸 없음(옛 메모와 같음)
    } else if (draft && HD.memoBatch.multi(draft)) {   // 고른 화면마다 메모 하나(같은 batch) — 되돌리기 한 단계
      var ms = HD.memoBatch.build(draft, {note: note, intent: intent, scope: scope}, newId).map(withAtt);
      var put = function () { ms.forEach(function (m) { NS.add(m); }); ctx.save(); };
      put();
      ctx.record({label: '메모 ' + ms.length + '개', redo: put,
                  undo: function () { var ids = ms.map(function (m) { return m.id; }); NS.remove(function (x) { return ids.indexOf(x.id) >= 0; }); ctx.save(); }});
    } else if (draft) {
      if (!ctx.modal().open) ctx.focusPin(draft.screen);   // 막 메모를 단 카드는 배율과 상관없이 핀을 바로 보인다
      NS.add(withAtt(HD.annotation.make({id: newId(), screen: draft.screen, targets: draft.targets, note: note, intent: intent, scope: scope, view: draft.view || null})));
    }
    hide(true); ctx.save();
  }
  function card(id) {                                 // 메모 도구·빈 레이아웃 누르기: 그 화면 전체에 메모(요소 = body) · id 배열 = 고른 화면마다 같은 메모(memo-batch)
    editing = null; draft = HD.memoBatch.draft([].concat(id), ctx.title); att('hd-attach-set', []);
    show({text: HD.memoBatch.label(draft), path: 'body', rect: null}, '', 'change');
  }
  function addCard(id) {                              // 메모 도구 화면 모드 Shift+클릭: 열린 새 화면 전체 메모에 그 화면 더하기·빼기(memo-batch) — 쓰던 글·의도·범위 그대로, 다 빼면 닫힘
    if (!(draft && !editing && !pop.hidden && draft.screens && draft.targets.every(function (t) { return t.path === 'body'; }))) { card(id); return; }
    var note = $('#pnote').value, intent = curIntent(), sc = curScope(), ids = HD.memoBatch.toggle(draft.screens, id);
    if (!ids.length) { hide(true); return; }
    draft = HD.memoBatch.draft(ids, ctx.title);
    show({text: HD.memoBatch.label(draft), path: 'body', rect: null}, note, intent, null, HD.memoBatch.multi(draft) && sc === 'element' ? null : sc);
  }
  function element(id, h, x, y, note) {               // 주석 도구: 판 위 카드 안 요소 하나에 메모(크게 보기 없이) · note = 미리 채울 글(요소 막대, task 49a)
    editing = null; draft = {screen: id, targets: [{path: h.path, text: h.text, rect: h.rect, quote: h.quote || null, src: h.src || null}], view: HD.memoState.capture(h.view)};   // src = 앱 소스 줄(요청문 '소스:') · view = 단 때 화면 상태(memo-state)
    att('hd-attach-set', []);
    show({text: h.text || h.path, path: h.path, rect: h.rect || null}, note || '', 'change', x == null ? null : {x: x, y: y});   // rect = 그 요소 옆에 창(F09)
    ctx.pins();                                       // 메모 창이 열린 동안 그 카드에 고른 요소 테두리
  }
  function toggleTarget(it) {                         // Shift+클릭: 열린 요소 메모 묶음에 더하거나 빼기(판 주석 도구 · 크게 보기 같은 규칙) — 쓰던 글·의도·범위 그대로
    var note = $('#pnote').value, intent = curIntent(), sc = curScope(), at = -1;
    draft.targets.forEach(function (t, i) { if (t.path === it.path) at = i; });
    if (at >= 0) draft.targets.splice(at, 1); else draft.targets.push(it);
    if (!draft.targets.length) { hide(true); return; }
    ctx.pins(); show(popItem(draft, it), note, intent, null, sc, true);
  }
  function addElement(id, h, x, y) {                  // 판 주석 도구 Shift+클릭: 같은 화면 요소 메모가 열려 있으면 묶음에 더하기·빼기, 아니면 새 메모
    if (draft && !editing && !pop.hidden && draft.screen === id && draft.targets.every(function (t) { return t.path !== 'body'; })) {
      toggleTarget({path: h.path, text: String(h.text || '').slice(0, 60), rect: h.rect || null, quote: h.quote || null, src: h.src || null});
      return;
    }
    element(id, h, x, y);
  }
  function elem(id, h, note, inModal, at) {           // 요소 하나에 메모 창(note = 미리 채울 요청 글) — 판 = 그 자리 옆, 크게 보기 = 고른 요소 아래
    var it = {path: h.path, text: String(h.text || '').slice(0, 60), rect: h.rect || null, quote: h.quote || null, src: h.src || null};
    if (!inModal) { element(id, h, at ? at.x : null, at ? at.y : null, note); return; }
    editing = null; draft = {screen: id, targets: [it], view: HD.memoState.capture(h.view)}; att('hd-attach-set', []);
    ctx.pins(); show(popItem(draft, it), note || '', 'change');
  }
  function edit(id) {                                 // 메모 고치기 — 메모 패널·카드 메모 묶음(#224)이 같이 쓴다
    var n = NS.find(id); if (!n) { ctx.toast('그 메모가 없어요 — 이미 지워졌어요'); return; }
    editing = id; draft = null; att('hd-attach-set', n.attach || []);   // 메모의 첨부 = 칩(썸네일은 view-attach 가 도우미에서)
    var ts = HD.notes.targets(n);
    show({text: ts.length > 1 ? ts.length + '개 요소 · ' + (ts[0].text || '') : ts[0].text, path: ts.map(function (t) { return t.path; }).join('\n'),
          rect: ts[0].rect || null}, AT.strip(n.note), n.intent, null, HD.annotation.scopeOf(n));
  }
  function del(id) {                                  // 메모 지우기·편집 빼기 — 메모 패널·카드 메모 묶음이 같이 쓴다, 되돌리기 한 단계(제자리로)
    var at = -1; NS.list().forEach(function (x, i) { if (x.id === id) at = i; });
    if (at < 0) { ctx.toast('그 메모가 없어요 — 이미 지워졌어요'); return; }
    var n = NS.list()[at];
    var drop = function () { NS.remove(function (x) { return x.id === id; }); if (editing === id) hide(true); ctx.save(); };
    drop();
    ctx.record({label: n.edit ? '편집 빼기' : '메모 지우기', redo: drop,
                undo: function () { var l = NS.list().slice(); l.splice(Math.min(at, l.length), 0, n); NS.set(l); ctx.save(); }});
  }
  function reply(ids, kind, label) {                  // 사람 답(완료 = 확인 · 다시 열기 = 다시, 보내기 전으로) — 메모 안 n.replies 에 덧붙임, 되돌리기 한 단계
    var at = new Date().toISOString(), hit = ids.map(function (id) { return NS.find(id); }).filter(Boolean);
    if (!hit.length) { ctx.toast('그 메모가 없어요 — 이미 지워졌어요'); return; }
    var was = hit.map(function (n) { return {n: n, sent: n.sent, k: (n.replies || []).length}; });
    var go = function () { hit.forEach(function (n) { n.replies = (n.replies || []).concat([HD.annotation.reply(kind, at)]); if (kind === '다시') n.sent = false; }); ctx.save(); };
    go();
    ctx.record({label: label, redo: go, undo: function () { was.forEach(function (w) { w.n.replies = (w.n.replies || []).slice(0, w.k); w.n.sent = w.sent; }); ctx.save(); }});
  }

  $$('#pintent button').forEach(function (b) { b.addEventListener('click', function () { setIntent(b.dataset.intent); }); });
  $('#pscope').innerHTML = HD.annotation.SCOPES.map(function (s) {   // 범위(R7) 말은 annotation — 아이콘 + 이름(aria-label·꼬리말, F09)
    return '<button type="button" class="pib" data-scope="' + s[0] + '" aria-pressed="false" aria-label="' + ctx.esc(s[1]) + '" data-tip="범위: ' + ctx.esc(s[1]) + '">' + (ICON[s[0]] || '') + '</button>'; }).join('');
  $$('#pscope button').forEach(function (b) { b.addEventListener('click', function () { setScope(b.dataset.scope); }); });
  $('#padd').addEventListener('click', commit);
  $('#pcancel').addEventListener('click', function () { hide(); });
  pop.addEventListener('pointerover', function (e) { var b = e.target.closest ? e.target.closest('button[data-tip]') : null; if (b) showTip(b); else hideTip(); });
  pop.addEventListener('pointerleave', hideTip);
  pop.addEventListener('focusin', function (e) { var b = e.target.closest ? e.target.closest('button[data-tip]') : null; if (b && b.matches(':focus-visible')) showTip(b); else hideTip(); });
  $('#pnote').addEventListener('input', function () { typed = true; });
  $('#pnote').addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); commit(); } });
  addEventListener('message', function (e) {         // 크게 보기에서 고른 요소(palette.js hd-picked) — 주석 도구일 때만
    var d = e.data, m = ctx.modal(); if (!d || typeof d !== 'object' || e.source !== (m.frame && m.frame.contentWindow)) return;
    if (d.type !== 'hd-picked' || !m.picking) return;
    if (d.screen) ctx.setScreen(String(d.screen));
    var it = {path: String(d.path || ''), text: String(d.text || '').slice(0, 60), rect: d.rect || null, quote: d.quote || null, src: d.src || null};   // src = 앱 소스 위치(task 27)
    if (d.add && draft && !editing && !pop.hidden) { toggleTarget(it); return; }   // Shift+클릭: 고른 묶음에 더하거나 빼기
    editing = null; att('hd-attach-set', []);
    draft = {screen: String(d.screen || ctx.modal().screen || ''), targets: [it], view: HD.memoState.capture(d.view)};   // view = 단 때 화면 상태(memo-state)
    ctx.pins(); show(popItem(draft, it), '', 'change');
  });

  var isTyped = function () { return typed && !pop.hidden && $('#pnote').value.trim() !== ''; };
  var layer = {id: 'pop', isOpen: function () { return !pop.hidden; }, close: function () { hide(); }, keep: isTyped,   // 떠 있는 층(view-float-stack)
    hit: function (t) {
      if (!t) return 'outside';
      if (pop.contains(t) || (tip && tip.contains(t))) return 'inside';
      return ctx.feeds && ctx.feeds(t) ? 'opener' : 'outside';   // 메모 도구로 카드·크게 보기 틀을 누름 = 그 도구가 이 창을 다시 정한다(Shift = 더하기)
    }};
  return {card: card, addCard: addCard, element: element, addElement: addElement, elem: elem, edit: edit, del: del, reply: reply,
          isOpen: function () { return !pop.hidden; }, close: function () { hide(); }, draft: function () { return draft; },
          typed: isTyped, layer: layer};
}

HD.viewMemoPop = {mount: mount};
})();
