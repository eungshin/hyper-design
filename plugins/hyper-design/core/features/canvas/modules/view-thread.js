/* View — 카드 메모 배지(.nbadge)를 누르면 그 화면 메모 묶음(Word 메모처럼, #224): 배지 옆 작은 창에 요소·종류·글 전체, 줄마다 [고치기]·[지우기], 아래 [메모 추가].
   메모 나누기(배지 수와 같은 것)는 HD.edits.split(Model). 고치기·지우기·더하기는 셸이 메모 패널과 같은 함수를 건넨다(여기서 메모를 바꾸지 않는다).
   상태 = 지금 연 화면 id 하나(저장하지 않음). 배지 누르기는 카드 고르기·끌기로 가지 않는다. Esc(셸이 close 를 부른다)·바깥 누르기 = 닫기.
   HD.viewThread.mount(ctx) → {open(id, badgeEl), close() → 열려 있었나, refresh(), isOpen()}
   ctx = {rowsEl, esc, list() → 메모 전부, title(id), edit(noteId), del(noteId), add(screenId)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var INTENT = {change: '바꾸기', question: '질문'};

function mount(ctx) {
  var esc = ctx.esc, cur = null;                     // cur = {id, badge}
  var box = document.createElement('div');
  box.id = 'thread'; box.className = 'thr'; box.hidden = true;
  box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', '이 화면 메모');
  document.body.appendChild(box);

  function memosOf(id) { return HD.edits.split(ctx.list()).memos.filter(function (n) { return n.screen === id; }); }
  function label(n) {
    var ts = n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text}];
    if (ts.length === 1 && ts[0].path === 'body') return '화면 전체';
    var t = String(ts[0].text || ts[0].path || '').replace(/\s+/g, ' ');
    return (t.length > 40 ? t.slice(0, 40) + '…' : t) + (ts.length > 1 ? ' 외 ' + (ts.length - 1) + '개' : '');
  }
  function row(n) {
    return '<li data-id="' + esc(n.id) + '"' + (n.sent ? ' class="sent"' : '') + '><div class="thl"><span class="the">' + esc(label(n)) + '</span><span class="thi">' +
      esc(INTENT[n.intent] || n.intent || '') + (n.sent ? ' · 보냄' : '') + '</span></div><div class="tht">' + esc(n.note || '') + '</div>' +
      '<div class="tha"><button type="button" class="nbtn" data-act="edit">고치기</button><button type="button" class="nbtn" data-act="del">지우기</button></div></li>';
  }
  function draw() {
    var ms = memosOf(cur.id);
    box.innerHTML = '<div class="thh">' + esc(ctx.title(cur.id)) + ' · 메모 ' + ms.length + '건</div><ol class="thlist">' + ms.map(row).join('') + '</ol>' +
      '<div class="thf"><button type="button" class="nbtn pri" data-act="add">메모 추가</button></div>';
  }
  function place() {                                 // 배지 아래 오른쪽 끝을 맞춤, 창 안으로
    var r = cur.badge.getBoundingClientRect(), w = box.offsetWidth, h = box.offsetHeight;
    var x = Math.max(8, Math.min(innerWidth - w - 8, r.right - w)), y = r.bottom + 6;
    if (y + h > innerHeight - 8) y = Math.max(8, r.top - h - 6);
    box.style.left = x + 'px'; box.style.top = y + 'px';
  }
  function open(id, badge) {
    cur = {id: id, badge: badge};
    box.hidden = false; draw(); place();
    badge.setAttribute('aria-expanded', 'true');
    var b = box.querySelector('button'); if (b) b.focus({preventScroll: true});
  }
  function close() {
    if (!cur) return false;
    if (cur.badge) cur.badge.setAttribute('aria-expanded', 'false');
    cur = null; box.hidden = true; box.innerHTML = '';
    return true;
  }
  function refresh() {                               // 메모가 바뀌면(셸 renderNotes) 다시 — 다 지웠거나 배지가 없어지면 닫는다
    if (!cur) return;
    var card = cur.badge.closest ? cur.badge.closest('.card') : null;
    var badge = card && card.isConnected ? card.querySelector('.nbadge') : null;
    if (!badge || !memosOf(cur.id).length) { close(); return; }
    cur.badge = badge; badge.setAttribute('aria-expanded', 'true');
    draw(); place();
  }

  function hit(e) { var b = e.target.closest ? e.target.closest('.nbadge') : null; return b && ctx.rowsEl.contains(b) ? b : null; }
  function toggle(b) {
    var id = b.closest('.card').dataset.id;
    if (cur && cur.id === id) close(); else open(id, b);
  }
  ctx.rowsEl.addEventListener('pointerdown', function (e) { if (hit(e)) e.stopPropagation(); });   // 판 끌기·카드 옮기기로 가지 않게
  document.addEventListener('click', function (e) {  // 판의 click(잡는 단계)보다 먼저 — 카드 고르기·도구 동작으로 가지 않게
    var b = hit(e); if (!b) return;
    e.preventDefault(); e.stopPropagation(); toggle(b);
  }, true);
  ctx.rowsEl.addEventListener('dblclick', function (e) { if (hit(e)) e.stopPropagation(); });
  ctx.rowsEl.addEventListener('keydown', function (e) {
    var b = hit(e); if (!b || (e.key !== 'Enter' && e.key !== ' ')) return;
    e.preventDefault(); e.stopPropagation(); toggle(b);
  });
  document.addEventListener('pointerdown', function (e) {   // 바깥 누르기 = 닫기(배지 누르기는 위 click 이 정한다)
    if (cur && !box.contains(e.target) && !hit(e)) close();
  }, true);
  box.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act]'); if (!b || !cur) return;
    var li = b.closest('li'), id = cur.id;
    if (b.dataset.act === 'add') { close(); ctx.add(id); }
    else if (b.dataset.act === 'edit') { close(); ctx.edit(li.dataset.id); }
    else if (b.dataset.act === 'del') ctx.del(li.dataset.id);   // 목록은 셸 renderNotes → refresh 로 다시
  });
  ['pointerdown', 'wheel', 'keydown', 'contextmenu'].forEach(function (n) { box.addEventListener(n, function (e) { if (n !== 'keydown' || e.key !== 'Escape') e.stopPropagation(); }); });

  return {open: open, close: close, refresh: refresh, isOpen: function () { return !!cur; }};
}

HD.viewThread = {mount: mount};
})();
