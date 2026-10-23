/* View — 메모 패널(#nlist: AI 에 보내는 요청)과 반영 대기 패널(#plist: 기계적 편집, E5) 목록 · 카드 위 메모 배지·반영 대기 칩.
   나누기는 HD.edits.split(Model). 완료한 메모(HD.annotation.isOpen 이 아님)는 목록·배지 수·보내기 건수에서 빠진다(카드 메모 묶음의 '완료' 묶음에만). 보내기는 한 자리(#nsend, 위쪽 줄 배율 오른쪽 — 둘 다 보낸다, E16): 여기선 그 버튼의 건수·켜짐만.
   '결정 필요'(#232, 강조색 하나): 위쪽 줄 #decn '결정 필요 N'(0 이면 숨김, 누르면 메모 패널을 그것만으로 열기) · 메모 패널 단추 #ndec '결정 필요만'(거르기) ·
   결정 필요 메모가 있는 카드 배지에 .decide(강조색 — 수는 그대로 열린 메모 수). 거르기 상태 = 켜짐 하나(저장하지 않음, 결정 필요가 0 이 되면 꺼짐).
   HD.viewNotes.mount(ctx) → {render(notes, ids?) → {memos, pending, decide}, filter(on)}   ids = 메모가 바뀐 화면 — 카드 배지는 그 카드만(없으면 전부)
   ctx = {$, $$, esc, rowsEl, circled(n), title(id), edit(id), del(id), showNotes()(메모 패널을 앞으로)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, E = HD.edits, A = HD.annotation;
  var only = false, last = [];                       // only = '결정 필요만' 켜짐 · last = 마지막 render 의 메모(거르기만 바꿀 때 다시 그리기)

  function targets(n) { return n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text, rect: n.rect}]; }
  function memoRow(n, i) {
    var k = targets(n).length;
    return '<li data-id="' + esc(n.id) + '"' + (n.sent ? ' class="sent"' : '') + '><div><span class="nn">' + ctx.circled(i + 1) + '</span><span class="ns">' + esc(n.screen) +
      ' · ' + esc(n.intent) + (k > 1 ? ' · ' + k + '개 요소' : '') + (n.sent ? ' · 보냄' : '') + '</span>' + (A.status(n) === 'decide' ? '<span class="ndst">결정 필요</span>' : '') + '</div><div class="nt">"' + esc(n.text) + '"</div><div class="nnote">' + esc(n.note) + '</div>' +
      '<div class="nact"><button class="nbtn" data-act="edit">고치기</button><button class="nbtn" data-act="del">지우기</button></div></li>';
  }
  function pendRow(n) {
    return '<li data-id="' + esc(n.id) + '"' + (n.sent ? ' class="sent"' : '') + '><div class="ns">' + esc(ctx.title(n.screen)) + (n.sent ? ' · 보냄' : '') + '</div>' +
      '<div class="nnote">' + esc(n.note) + '</div><div class="nact"><button class="nbtn" data-act="del" title="이 편집 빼기">빼기</button></div></li>';
  }
  function badge(c, cls, k, text, title) {
    var b = $('.' + cls, c);
    if (!k) { if (b) b.remove(); return; }
    if (!b) { b = document.createElement('span'); b.className = cls; $('.phone', c).appendChild(b); }
    b.textContent = text; if (typeof title === 'string') b.title = title;   // nbadge 는 title 자리에 {decide}
    if (cls === 'nbadge') {                           // 누르면 그 화면 메모 묶음(view-thread, #224)
      b.classList.toggle('decide', !!(title && title.decide));
      b.setAttribute('role', 'button'); b.tabIndex = 0; b.setAttribute('aria-haspopup', 'dialog');
      var dz = title && title.decide ? ' · 결정 필요' : '';   // 색만으로 말하지 않게
      b.setAttribute('aria-label', '메모 ' + k + '건 보기' + dz); b.title = '메모 ' + k + '건 — 눌러서 보기' + dz;
    }
  }
  function render(notes, ids) {
    last = notes;
    var open = notes.filter(A.isOpen), sp = E.split(open), memo = {}, dec = {}, pend = E.tally(open), nd = A.decideCount(sp.memos);
    sp.memos.forEach(function (n) { memo[n.screen] = (memo[n.screen] || 0) + 1; if (A.status(n) === 'decide') dec[n.screen] = 1; });
    if (!nd) only = false;
    $('#notes').hidden = !sp.memos.length && !open.some(function (n) { return n.sent; }); $('#pend').hidden = !sp.pending.length;   // 보낸 것이 있으면 '보낸 것 완료로' 때문에 연다
    var dn = $('#decn'); dn.hidden = !nd; dn.textContent = '결정 필요 ' + nd; dn.dataset.n = String(nd);
    var tg = $('#ndec'); tg.hidden = !nd; tg.setAttribute('aria-pressed', String(only));
    $('#nlist').innerHTML = (only ? sp.memos.filter(function (n) { return A.status(n) === 'decide'; }) : sp.memos).map(memoRow).join('');
    $('#plist').innerHTML = sp.pending.map(pendRow).join('');
    $('#nclear').hidden = !open.some(function (n) { return n.sent; });
    var unsent = open.filter(function (n) { return !n.sent; }).length, sc = $('#nsendc');
    $('#nsend').disabled = !open.length; sc.hidden = !unsent; sc.textContent = String(unsent);   // 다 보냈으면 건수는 숨기고 다시 보내기는 그대로
    $$('.card', ctx.rowsEl).forEach(function (c) {
      var id = c.dataset.id; if (ids && ids.indexOf(id) < 0) return;
      badge(c, 'nbadge', memo[id] || 0, String(memo[id] || 0), {decide: !!dec[id]});
      badge(c, 'pchip', pend[id] || 0, '반영 대기 ' + (pend[id] || 0));     // 반영 대기 = 화면 파일을 바꾸는 편집(보냈어도 '보낸 것 완료로' 전까지)
    });
    return {memos: sp.memos.length, pending: sp.pending.length, decide: nd};
  }
  function filter(on) { only = !!on; render(last, []); }   // 거르기만 바뀜 — 카드 배지는 그대로(ids 빈 목록)
  $('#ndec').addEventListener('click', function () { filter(!only); });
  $('#decn').addEventListener('click', function () { filter(true); ctx.showNotes(); });
  ['#nlist', '#plist'].forEach(function (sel) {
    $(sel).addEventListener('click', function (e) {
      var b = e.target.closest('button[data-act]'); if (!b) return;
      var id = b.closest('li').dataset.id;
      if (b.dataset.act === 'del') ctx.del(id); else ctx.edit(id);
    });
  });
  return {render: render, filter: filter};
}

HD.viewNotes = {mount: mount};
})();
