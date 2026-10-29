/* View — 메모 패널(#nlist: AI 에 보내는 요청)과 반영 대기 패널(#plist: 기계적 편집, E5) 목록 · 카드 위 메모 배지·반영 대기 칩.
   나누기는 HD.edits.split(Model). 완료한 메모(HD.annotation.isOpen 이 아님)는 목록·배지 수·보내기 건수에서 빠진다(카드 메모 묶음의 '완료' 묶음에만). 보내기는 한 자리(#nsend, 위쪽 줄 배율 오른쪽 — 둘 다 보낸다, E16): 여기선 그 버튼의 건수·켜짐만.
   '결정 필요'(#232, 강조색 하나): 위쪽 줄 #decn '결정 필요 N'(0 이면 숨김, 누르면 메모 패널을 그것만으로 열기) · 메모 패널 단추 #ndec '결정 필요만'(거르기) ·
   결정 필요 메모가 있는 카드 배지에 .decide(강조색 — 수는 그대로 열린 메모 수). 거르기 상태 = 켜짐 하나(저장하지 않음, 결정 필요가 0 이 되면 꺼짐).
   보낸 메모 숨기기(task 29): 목록·카드 배지 수는 HD.annotation.visible(n, 켜짐)인 메모만 — 보낸 뒤 AI 차례·완료한 메모는 숨김. 이 View 가 메모 막대(.ntool, task 32 — 한 줄 아이콘:
     #ncnt '메모 N' · #nsent · #ndec · #nclear) 안에 눈 아이콘 #nsent '보낸 메모 보기 (N)'(title·aria-label, 수 배지 .ncb[data-n] — N = 숨김이 될 메모 수, 0 이면 꺼진 단추로 자리 유지)를 그린다.
     줄의 고치기·지우기 = 줄 오른쪽 위 연필·휴지통 아이콘(늘 흐리게 보이고 올리거나 포커스면 진하게 — 카드 메모 묶음과 같이, R26 · 자리는 늘 비워 둠). 켜짐 = 그 메모도 흐리게 + 상태 말(AI 작업 중·완료). 켜짐 상태의 주인 = 이 View, 키 ctx.key('hd-show-sent')('1'|'0', 깨진 값 = [hd] 경고 + 꺼짐).
     바뀌면 ctx.sentChanged(켜짐)(의도 — 셸이 핀·묶음을 다시 그리게 잇는다, #263). 다른 View 는 셸이 건네는 showSent() 로 읽는다.
   목록 모양(R27 F10 — 메모 묶음 #thread 와 한 식구): 화면마다 묶어 화면 이름(ctx.title)을 한 번만(그 화면 첫 줄 위 .ngh — 줄 수·li 는 메모 수 그대로),
     줄 = 작은 회색 메타 한 줄(.nl: 번호 #n.no · 의도 아이콘 .ni(이름은 title·aria-label) · 대상 .nt(화면 전체 | 요소 글) · 상태 말 · 끝에 연필·휴지통) + 메모 글(.nnote, 가장 또렷).
     내부 화면 id·영어 의도 말은 보이지 않는다. 묶음 차례 = 그 화면 메모가 처음 나온 차례, 묶음 안은 목록 차례.
   요소를 찾을 수 없음(#285): 화면이 다시 찾지 못한 대상(ctx.lost(n))이 있는 열린 메모 줄에 회색 말 .nlost(title = 까닭). 답이 오면 relost() — 바뀐 것이 있을 때만 목록을 다시.
   HD.viewNotes.mount(ctx) → {render(notes, ids?) → {memos, pending, decide}, filter(on), showSent(on?) → 켜짐, relost()}   ids = 메모가 바뀐 화면 — 카드 배지는 그 카드만(없으면 전부)
   ctx = {$, $$, esc, rowsEl, circled(n), title(id), edit(id), del(id), showNotes()(메모 패널을 앞으로), storage{getItem,setItem}, key(prefix) → 저장 키,
          sentChanged(on), lost(n) → 다시 찾지 못한 대상이 있나} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, E = HD.edits, A = HD.annotation;
  var only = false, last = [];                       // only = '결정 필요만' 켜짐 · last = 마지막 render 의 메모(거르기만 바꿀 때 다시 그리기)
  var store = ctx.storage, SKEY = ctx.key('hd-show-sent'), lostSig = '';
  var shown = readShown();                           // 보낸 메모 보기 켜짐(task 29) — 주인은 이 View
  function readShown() {
    var v = null;
    try { v = store.getItem(SKEY); } catch (e) { v = null; }   // 저장소를 못 읽으면(막힘) 기본 꺼짐
    if (v == null || v === '0') return false;
    if (v === '1') return true;
    console.warn('[hd] ' + SKEY + ' 값이 깨졌어요(' + String(v).slice(0, 20) + ') — 보낸 메모 보기 꺼짐으로');
    return false;
  }
  var ICON = {
    eye: '<svg viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    edit: '<svg viewBox="0 0 24 24"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/></svg>',
    del: '<svg viewBox="0 0 24 24"><path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/></svg>',
    change: '<svg viewBox="0 0 24 24"><path d="M4 8h13l-3.5-3.5"/><path d="M20 16H7l3.5 3.5"/></svg>',          // 의도 아이콘(F10) — 바꾸기 = 오가는 화살표
    question: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6"/><path d="M12 17.2v.1"/></svg>'};
  var INTENT = {change: '바꾸기', question: '질문'};
  var sbtn = document.createElement('button');        // 보낸 메모 보기 — 메모 막대(템플릿 .ntool)의 #ndec 앞
  sbtn.type = 'button'; sbtn.className = 'nib'; sbtn.id = 'nsent'; sbtn.setAttribute('aria-pressed', 'false'); sbtn.disabled = true;
  sbtn.innerHTML = ICON.eye + '<span class="ncb" data-n="0" hidden>0</span>';
  $('#ndec').parentNode.insertBefore(sbtn, $('#ndec'));
  var css = document.createElement('style'); css.id = 'hd-sent-css';
  css.textContent = '#notes li.nhid{opacity:.55}#notes .nsst,#notes .nlost{color:#888;font-size:11.5px}#notes .nlost{border-bottom:1px dashed #aaa;cursor:help}';
  var LOST = '화면이 바뀌어 같은 요소가 여러 개이거나 없어요';
  document.head.appendChild(css);

  function targets(n) { return n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text, rect: n.rect}]; }
  function where(n) {                                // 대상 말 — 메모 묶음(view-thread label)과 같이: 화면 전체 | 요소 글(40자) · N개 요소
    var ts = targets(n), k = ts.length;
    if (k === 1 && ts[0].path === 'body') return '화면 전체';
    var t = String(ts[0].text || ts[0].path || '').replace(/\s+/g, ' ');
    return (t.length > 40 ? t.slice(0, 40) + '…' : t) + (k > 1 ? ' · ' + k + '개 요소' : '');
  }
  function memoRow(n, i, first) {                    // first = 그 화면 묶음의 첫 줄 → 화면 이름 머리(.ngh)를 줄 안 위에(li = 메모 하나 그대로)
    var st = A.status(n), hid = !A.visible(n, false), cls = (first ? ' ng1' : '') + (n.sent ? ' sent' : '') + (hid ? ' nhid' : '');
    var iw = INTENT[n.intent] || INTENT.change, name = ctx.title(n.screen);
    return '<li data-id="' + esc(n.id) + '"' + (cls ? ' class="' + cls.slice(1) + '"' : '') + '>' +
      (first ? '<div class="ngh" title="' + esc(name) + '">' + esc(name) + '</div>' : '') +
      '<div class="nl"><span class="nn">' + (n.no != null ? '#' + esc(n.no) : ctx.circled(i + 1)) + '</span>' +
      '<span class="ni" role="img" title="' + iw + '" aria-label="' + iw + '">' + (ICON[n.intent] || ICON.change) + '</span>' +
      '<span class="nt">' + esc(where(n)) + '</span>' + (n.sent ? '<span class="nsnt">보냄</span>' : '') + (st === 'decide' ? '<span class="ndst">결정 필요</span>' : '') +
      (hid ? '<span class="nsst" data-st="' + st + '">' + esc(A.LABEL[st]) + '</span>' : '') +
      (st !== 'done' && ctx.lost(n) ? '<span class="nlost" title="' + LOST + '">요소를 찾을 수 없음</span>' : '') +
      '<span class="nact"><button type="button" class="nib" data-act="edit" title="고치기" aria-label="고치기">' + ICON.edit + '</button>' +
      '<button type="button" class="nib" data-act="del" title="지우기" aria-label="지우기">' + ICON.del + '</button></span></div>' +
      '<div class="nnote">' + esc(n.note) + '</div></li>';
  }
  function grouped(list) {                           // 화면마다 묶기(F10) — 묶음 차례 = 처음 나온 차례, 묶음 안은 목록 차례
    var order = [], by = {};
    list.forEach(function (n) { if (!by[n.screen]) { by[n.screen] = []; order.push(n.screen); } by[n.screen].push(n); });
    var html = '', i = 0;
    order.forEach(function (sid) { by[sid].forEach(function (n, j) { html += memoRow(n, i++, j === 0); }); });
    return html;
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
  function sig(notes) { return notes.filter(function (n) { return !n.edit && ctx.lost(n); }).map(function (n) { return n.id; }).join(','); }
  function render(notes, ids) {
    last = notes; lostSig = sig(notes);
    var open = notes.filter(A.isOpen), sp = E.split(open), memo = {}, dec = {}, pend = E.tally(open), nd = A.decideCount(sp.memos);
    var all = E.split(notes).memos, vis = all.filter(function (n) { return A.visible(n, shown); }), nh = A.hiddenCount(all);   // 목록·배지 = 보이는 메모(task 29)
    vis.forEach(function (n) { memo[n.screen] = (memo[n.screen] || 0) + 1; });
    sp.memos.forEach(function (n) { if (A.status(n) === 'decide') dec[n.screen] = 1; });
    if (!nd) only = false;
    $('#notes').hidden = !vis.length && !nh && !open.some(function (n) { return n.sent; }); $('#pend').hidden = !sp.pending.length;   // 보낸 것이 있으면 '보낸 것 완료로'·'보낸 메모 보기' 때문에 연다
    var sb = $('#nsent'), cb = $('.ncb', sb), sl = '보낸 메모 보기 (' + nh + ')';
    sb.title = sl; sb.setAttribute('aria-label', sl); cb.textContent = String(nh); cb.dataset.n = String(nh); cb.hidden = !nh;
    sb.disabled = !nh && !shown; sb.setAttribute('aria-pressed', String(shown));   // 0 이면 꺼진 단추(자리 유지) — 켜져 있으면 끌 수 있게 둔다
    $('#ncnt').textContent = '메모 ' + vis.length;
    var dn = $('#decn'); dn.hidden = !nd; dn.textContent = '결정 필요 ' + nd; dn.dataset.n = String(nd);
    var tg = $('#ndec'); tg.hidden = !nd; tg.setAttribute('aria-pressed', String(only));
    $('#nlist').innerHTML = grouped(only ? vis.filter(function (n) { return A.status(n) === 'decide'; }) : vis);
    $('#plist').innerHTML = sp.pending.map(pendRow).join('');
    $('#nclear').hidden = !open.some(function (n) { return n.sent; });
    var unsent = open.filter(function (n) { return !n.sent; }).length, sc = $('#nsendc');
    $('#nsend').disabled = !open.length; sc.hidden = !unsent; sc.textContent = String(unsent);   // 다 보냈으면 건수는 숨기고 다시 보내기는 그대로
    $$('.card', ctx.rowsEl).forEach(function (c) {
      var id = c.dataset.id; if (ids && ids.indexOf(id) < 0) return;
      badge(c, 'nbadge', memo[id] || 0, String(memo[id] || 0), {decide: !!dec[id]});
      badge(c, 'pchip', pend[id] || 0, '반영 대기 ' + (pend[id] || 0));     // 반영 대기 = 화면 파일을 바꾸는 편집(보냈어도 '보낸 것 완료로' 전까지)
    });
    return {memos: vis.length, pending: sp.pending.length, decide: nd};
  }
  function showSent(on) {                            // 보낸 메모 보기 켜기·끄기 → 저장 · 목록·배지 전부 다시 · ctx.sentChanged(핀·묶음)
    if (on === undefined) return shown;
    shown = !!on;
    try { store.setItem(SKEY, shown ? '1' : '0'); } catch (e) { console.warn('[hd] 보낸 메모 보기 상태를 저장하지 못했어요'); }
    render(last);
    ctx.sentChanged(shown);
    return shown;
  }
  function relost() { if (sig(last) !== lostSig) render(last, []); }   // 화면이 자리를 답함 — 찾을 수 없는 메모가 바뀌었을 때만 목록 다시(배지는 그대로)
  $('#nsent').addEventListener('click', function () { showSent(!shown); });
  function filter(on) { only = !!on; render(last, []); }   // 거르기만 바뀜 — 카드 배지는 그대로(ids 빈 목록)
  $('#ndec').addEventListener('click', function () { filter(!only); });
  $('#decn').addEventListener('click', function () { filter(true); ctx.showNotes(); });
  ['#nlist', '#plist'].forEach(function (sel) {
    $(sel).addEventListener('click', function (e) {
      var b = e.target.closest('button[data-act]'); if (!b) return;
      var id = b.closest('li').dataset.id;
      if (b.dataset.act === 'del') ctx.del(id); else ctx.edit(id);
    });
    $(sel).addEventListener('dblclick', function (e) {   // 메모 글 더블클릭 = 고치기 아이콘과 같다
      var t = e.target.closest ? e.target.closest('.nnote') : null, li = t && t.closest('li[data-id]');
      if (li) { e.preventDefault(); ctx.edit(li.dataset.id); }
    });
  });
  return {render: render, filter: filter, showSent: showSent, relost: relost};
}

HD.viewNotes = {mount: mount};
})();
