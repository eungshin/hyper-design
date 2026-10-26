/* View — 메모 창(#pop) 하나: 화면 전체·요소·크게 보기 고른 요소(hd-picked, Shift = 묶음에 더하기·빼기)의 메모 쓰기·고치기·지우기·사람 답, 범위·의도 고르기.
   메모 모양 = Model HD.annotation.make·makeId, 여러 장 = HD.memoBatch, 창 틀(옮기기·크기·저장한 자리) = 등록부 기능 popPlace(ctx.frame()) — 없으면 자동 자리만.
   HD.viewMemoPop.mount(ctx) → {card(id | [id]), element(id, h, x?, y?, note?), elem(id, h, note, inModal, at?), edit(id), del(id), reply(ids, kind, label),
     isOpen(), close(), draft() → 쓰는 중인 초안|null(핀이 고른 요소 테두리)}
   ctx = {$, $$, esc, notes(NS), save(), record(op), toast(msg), title(id), modal() → {open, screen, scale, box, picking, frame}, setScreen(id), frame() → popPlace|null,
          cardEl(id), pins()(핀 다시), focusPin(id)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, NS = ctx.notes, pop = $('#pop'), draft = null, editing = null;
  var newId = function () { return HD.annotation.makeId(Date.now(), Math.random()); };

  function popItem(dr, last) {
    var n = dr.targets.length;
    return {text: n > 1 ? n + '개 요소 · ' + (last.text || '') : last.text, path: dr.targets.map(function (t) { return t.path; }).join('\n'), rect: last.rect};
  }
  function place(rect, at, screen) {                 // at = 누른 자리(판 위 요소 메모) · 저장한 자리가 있으면 그것(popPlace)
    var auto = function () {
      var x = 24, y = 80, m = ctx.modal(), notesEl = $('#notes');
      if (at) { x = at.x + 14; y = at.y + 14; }
      else if (rect && m.open) {
        var b = m.box.getBoundingClientRect();
        x = b.left + rect.x * m.scale; y = b.top + (rect.y + rect.h) * m.scale + 8;
        if (y + 240 > innerHeight) y = Math.max(8, b.top + rect.y * m.scale - 248);
      } else if (notesEl && !notesEl.hidden) {
        var nb = notesEl.getBoundingClientRect(); x = nb.left - 312; y = nb.top;
      }
      return {x: Math.max(8, Math.min(innerWidth - 308, x)), y: Math.max(8, Math.min(innerHeight - 240, y))};
    };
    var PP = ctx.frame();
    if (PP) { PP.open(auto, screen ? ctx.cardEl(screen) : null); return; }
    var a = auto(); pop.style.left = a.x + 'px'; pop.style.top = a.y + 'px';   // 틀 기능이 붙지 못했으면(mountAll 이 [hd] 로 알림) 자동 자리만
  }
  function setIntent(v) { $$('#pintent button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.intent === v)); }); }
  function curIntent() { var b = $('#pintent button[aria-pressed="true"]'); return b ? b.dataset.intent : 'change'; }
  function setScope(v) { $$('#pscope button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.scope === v)); }); }
  function curScope() { var b = $('#pscope button[aria-pressed="true"]'); return b ? b.dataset.scope : 'element'; }
  function show(item, note, intent, at, scope) {     // scope 없음 = 기본(화면 전체 메모 = 이 화면, 그 밖 = 이 요소)
    $('#ptitle').textContent = item.text || '(글자 없음)';
    $('#ppath').textContent = item.path || '';
    $('#pnote').value = note || '';
    setIntent(intent || 'change');
    var many = !editing && HD.memoBatch.multi(draft), sw = {};   // 여러 장 = '이 요소' 없음 · '이 화면' → '고른 화면 N개'
    HD.memoBatch.scopes(many && draft, HD.annotation.SCOPES).forEach(function (s) { sw[s[0]] = s[1]; });
    $$('#pscope button').forEach(function (b) { var w = sw[b.dataset.scope]; b.hidden = !w; if (w) b.textContent = w; });
    setScope(scope || (many ? HD.memoBatch.defaultScope(draft) : item.path === 'body' ? 'screen' : 'element'));
    $('#padd').textContent = editing ? '저장' : '추가';
    var en = editing && NS.find(editing);
    pop.hidden = false; place(item.rect, at, en ? en.screen : draft && draft.screen);
    $('#pnote').focus();
  }
  function hide() {
    if (pop.contains(document.activeElement)) document.activeElement.blur();
    pop.hidden = true; draft = null; editing = null;
    var PP = ctx.frame(); if (PP) PP.close();
    ctx.pins();
  }
  function commit() {
    var note = $('#pnote').value.trim(), intent = curIntent(), scope = curScope();
    if (editing) {
      var n = NS.find(editing);
      if (n) { n.note = note; n.intent = intent; n.sent = false; if (scope === 'element') delete n.scope; else n.scope = scope; }   // 이 요소 = 칸 없음(옛 메모와 같음)
    } else if (draft && HD.memoBatch.multi(draft)) {   // 고른 화면마다 메모 하나(같은 batch) — 되돌리기 한 단계
      var ms = HD.memoBatch.build(draft, {note: note, intent: intent, scope: scope}, newId);
      var put = function () { ms.forEach(function (m) { NS.add(m); }); ctx.save(); };
      put();
      ctx.record({label: '메모 ' + ms.length + '개', redo: put,
                  undo: function () { var ids = ms.map(function (m) { return m.id; }); NS.remove(function (x) { return ids.indexOf(x.id) >= 0; }); ctx.save(); }});
    } else if (draft) {
      if (!ctx.modal().open) ctx.focusPin(draft.screen);   // 막 메모를 단 카드는 배율과 상관없이 핀을 바로 보인다
      NS.add(HD.annotation.make({id: newId(), screen: draft.screen, targets: draft.targets, note: note, intent: intent, scope: scope}));
    }
    hide(); ctx.save();
  }
  function card(id) {                                 // 메모 도구·빈 레이아웃 누르기: 그 화면 전체에 메모(요소 = body) · id 배열 = 고른 화면마다 같은 메모(memo-batch)
    editing = null; draft = HD.memoBatch.draft([].concat(id), ctx.title);
    show({text: HD.memoBatch.label(draft), path: 'body', rect: null}, '', 'change');
  }
  function element(id, h, x, y, note) {               // 주석 도구: 판 위 카드 안 요소 하나에 메모(크게 보기 없이) · note = 미리 채울 글(요소 막대, task 49a)
    editing = null; draft = {screen: id, targets: [{path: h.path, text: h.text, rect: h.rect, quote: h.quote || null, src: h.src || null}]};   // src = 앱 소스 줄(요청문 '소스:')
    show({text: h.text || h.path, path: h.path, rect: null}, note || '', 'change', x == null ? null : {x: x, y: y});
    ctx.pins();                                       // 메모 창이 열린 동안 그 카드에 고른 요소 테두리
  }
  function elem(id, h, note, inModal, at) {           // 요소 하나에 메모 창(note = 미리 채울 요청 글) — 판 = 그 자리 옆, 크게 보기 = 고른 요소 아래
    var it = {path: h.path, text: String(h.text || '').slice(0, 60), rect: h.rect || null, quote: h.quote || null, src: h.src || null};
    if (!inModal) { element(id, h, at ? at.x : null, at ? at.y : null, note); return; }
    editing = null; draft = {screen: id, targets: [it]};
    ctx.pins(); show(popItem(draft, it), note || '', 'change');
  }
  function edit(id) {                                 // 메모 고치기 — 메모 패널·카드 메모 묶음(#224)이 같이 쓴다
    var n = NS.find(id); if (!n) { ctx.toast('그 메모가 없어요 — 이미 지워졌어요'); return; }
    editing = id; draft = null;
    var ts = HD.notes.targets(n);
    show({text: ts.length > 1 ? ts.length + '개 요소 · ' + (ts[0].text || '') : ts[0].text, path: ts.map(function (t) { return t.path; }).join('\n'),
          rect: n.screen === ctx.modal().screen ? ts[0].rect : null}, n.note, n.intent, null, HD.annotation.scopeOf(n));
  }
  function del(id) {                                  // 메모 지우기·편집 빼기 — 메모 패널·카드 메모 묶음이 같이 쓴다, 되돌리기 한 단계(제자리로)
    var at = -1; NS.list().forEach(function (x, i) { if (x.id === id) at = i; });
    if (at < 0) { ctx.toast('그 메모가 없어요 — 이미 지워졌어요'); return; }
    var n = NS.list()[at];
    var drop = function () { NS.remove(function (x) { return x.id === id; }); if (editing === id) hide(); ctx.save(); };
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
  $('#pscope').innerHTML = HD.annotation.SCOPES.map(function (s) { return '<button type="button" data-scope="' + s[0] + '" aria-pressed="false">' + ctx.esc(s[1]) + '</button>'; }).join('');   // 범위(R7) 말은 annotation
  $$('#pscope button').forEach(function (b) { b.addEventListener('click', function () { setScope(b.dataset.scope); }); });
  $('#padd').addEventListener('click', commit);
  $('#pcancel').addEventListener('click', hide);
  $('#pnote').addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); commit(); } });
  addEventListener('message', function (e) {         // 크게 보기에서 고른 요소(palette.js hd-picked) — 주석 도구일 때만
    var d = e.data, m = ctx.modal(); if (!d || typeof d !== 'object' || e.source !== (m.frame && m.frame.contentWindow)) return;
    if (d.type !== 'hd-picked' || !m.picking) return;
    if (d.screen) ctx.setScreen(String(d.screen));
    var it = {path: String(d.path || ''), text: String(d.text || '').slice(0, 60), rect: d.rect || null, quote: d.quote || null, src: d.src || null};   // src = 앱 소스 위치(task 27)
    if (d.add && draft && !editing && !pop.hidden) {   // Shift+클릭: 고른 묶음에 더하거나 빼기
      var note = $('#pnote').value, intent = curIntent(), sc = curScope(), at = -1;
      draft.targets.forEach(function (t, i) { if (t.path === it.path) at = i; });
      if (at >= 0) draft.targets.splice(at, 1); else draft.targets.push(it);
      if (!draft.targets.length) { hide(); return; }
      ctx.pins(); show(popItem(draft, it), note, intent, null, sc);
      return;
    }
    editing = null;
    draft = {screen: String(d.screen || ctx.modal().screen || ''), targets: [it]};
    ctx.pins(); show(popItem(draft, it), '', 'change');
  });

  return {card: card, element: element, elem: elem, edit: edit, del: del, reply: reply,
          isOpen: function () { return !pop.hidden; }, close: hide, draft: function () { return draft; }};
}

HD.viewMemoPop = {mount: mount};
})();
