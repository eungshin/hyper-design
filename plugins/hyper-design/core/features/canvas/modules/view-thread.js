/* View — 카드 메모 배지(.nbadge)를 누르면 그 화면 메모 묶음(Word 메모처럼, #224): 배지 옆 작은 창에 요소·종류·글 전체, 줄마다 [고치기]·[지우기], 아래 [메모 추가].
   메모 나누기(배지 수와 같은 것)는 HD.edits.split(Model). 고치기·지우기·더하기는 셸이 메모 패널과 같은 함수를 건넨다(여기서 메모를 바꾸지 않는다).
   상태 = 지금 연 화면 id 하나(저장하지 않음). 배지 누르기는 카드 고르기·끌기로 가지 않는다. Esc(셸이 close 를 부른다)·바깥 누르기 = 닫기.
   줄마다 번호 #n.no · 범위 말(이 요소가 아닐 때만, HD.annotation.scopeWord — R7) · 상태 말(HD.annotation.label — 받는 곳 없이 보낸 것 = '대기열', decide 만 강조색) · 답(답마다 회색 한 줄 HD.annotation.says, 마지막 것 펼침, 앞 것 접힘,
   반영됨 줄에 올리면 화면·캡처 · 사람 답은 작게 '완료함/다시 엶' + 시각) · 빈 레이아웃에서 옮겨 온 메모면 회색 한 줄(HD.promote.movedSay) · 기다리는 질문이면 고를 것 단추(누르기 = ctx.choose) · [완료](사람 답 '확인'). 닫힌 메모는 아래 접힌 '완료 N' 묶음에 [다시 열기].
   보낸 메모 숨기기(task 29): 줄은 HD.annotation.visible(n, 켜짐)인 메모만(켜짐 = document.documentElement.dataset.hdShowSent === '1', 주인 view-notes) — 꺼짐이면 AI 작업 중·완료 메모는 빠지고
   ('완료 N' 묶음도 켜졌을 때만) 숨긴 수를 회색 한 줄로. document 의 'hd-show-sent' 이벤트 = refresh.
   다시 찾지 못한 대상(ctx.lost)이 있고 닫히지 않은 메모 = "대상이 바뀌었어요". 줄에 올리면 ctx.highlight(화면, no) — 그 핀·요소 테두리.
   핀 누르기(셸이 open(id, 핀, no)) = 그 메모로 스크롤하고 펼침. 배지가 없어져도(열린 메모 0) 메모가 남아 있으면 그 자리에 둔다.
   HD.viewThread.mount(ctx) → {open(id, anchorEl, no?), close() → 열려 있었나, refresh(), isOpen()}
   ctx = {rowsEl, esc, list() → 메모 전부, title(id), edit(noteId), del(noteId), add(screenId), done(noteId), reopen(noteId), lost(n), highlight(id, no|null),
          choose(noteId, choice), queued() → 보내기가 대기열 파일에만 가나} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var INTENT = {change: '바꾸기', question: '질문'};

function mount(ctx) {
  var esc = ctx.esc, cur = null, A = HD.annotation;  // cur = {id, badge, no, at(마지막 자리)}
  var box = document.createElement('div');
  box.id = 'thread'; box.className = 'thr'; box.hidden = true;
  box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', '이 화면 메모');
  document.body.appendChild(box);
  var css = document.createElement('style'); css.id = 'hd-thread-sent-css';
  css.textContent = '#thread .thhid{padding:6px 12px;color:#888;font-size:12px}';
  document.head.appendChild(css);
  document.addEventListener('hd-show-sent', function () { refresh(); });   // 보낸 메모 보기가 바뀜(view-notes)

  function memosOf(id) { return HD.edits.split(ctx.list()).memos.filter(function (n) { return n.screen === id; }); }
  function label(n) {
    var ts = n.targets && n.targets.length ? n.targets : [{path: n.path, text: n.text}];
    if (ts.length === 1 && ts[0].path === 'body') return '화면 전체';
    var t = String(ts[0].text || ts[0].path || '').replace(/\s+/g, ' ');
    return (t.length > 40 ? t.slice(0, 40) + '…' : t) + (ts.length > 1 ? ' 외 ' + (ts.length - 1) + '개' : '');
  }
  function when(at) {                                // 'MM/DD HH:MM'(이 컴퓨터 시각) — 못 읽으면 빈 글
    var d = at ? new Date(at) : null; if (!d || isNaN(d.getTime())) return '';
    var p = function (v) { return (v < 10 ? '0' : '') + v; };
    return p(d.getMonth() + 1) + '/' + p(d.getDate()) + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }
  function reps(n) {
    var rs = (n.replies || []).filter(function (r) { return r && typeof r === 'object'; }); if (!rs.length) return '';
    var line = function (r) {
      var me = A.USER.indexOf(r.kind) >= 0, t = A.tip(r), w = me ? when(r.at) : '';
      return '<div class="thr1' + (me ? ' me' : '') + '" data-kind="' + esc(r.kind) + '"' + (t ? ' title="' + esc(t) + '"' : '') + '>' + esc(A.says(r)) + (w ? ' · ' + esc(w) : '') + '</div>';
    };
    var older = rs.slice(0, -1);
    return '<div class="threp">' + (older.length ? '<details class="thold"><summary>이전 답 ' + older.length + '개</summary>' + older.map(line).join('') + '</details>' : '') + line(rs[rs.length - 1]) + '</div>';
  }
  function choices(n) {                              // 기다리는 질문: 고를 것마다 단추
    var q = A.question(n); if (!q) return '';
    return '<div class="thq" role="group" aria-label="고르기">' + q.choices.map(function (c, i) { return '<button type="button" class="nbtn thc" data-act="choose" data-i="' + i + '">' + esc(c) + '</button>'; }).join('') + '</div>';
  }
  function moved(n) {                                // 빈 레이아웃에서 이 화면으로 옮겨 온 메모(승격, #241) — HD.promote.movedSay
    var t = HD.promote ? HD.promote.movedSay(n) : '';
    return t ? '<div class="thr1 thmv">' + esc(t) + '</div>' : '';
  }
  function row(n) {
    var st = A.status(n), open = st !== 'done';
    return '<li data-id="' + esc(n.id) + '" data-no="' + esc(n.no) + '"' + (n.sent && open ? ' class="sent"' : '') + '><div class="thl"><span class="thn">#' + esc(n.no) + '</span><span class="the">' + esc(label(n)) + '</span>' +
      '<span class="ths" data-st="' + st + '"' + (st === 'working' && ctx.queued() ? ' data-q="1"' : '') + '>' + esc(A.label(n, ctx.queued())) + '</span>' + (A.scopeWord(n) ? '<span class="thsc">' + esc(A.scopeWord(n)) + '</span>' : '') +
      '<span class="thi">' + esc(INTENT[n.intent] || n.intent || '') + '</span></div>' +
      (open && ctx.lost(n) ? '<div class="thlost">대상이 바뀌었어요</div>' : '') +
      '<div class="tht">' + esc(n.note || '') + '</div>' + moved(n) + reps(n) + choices(n) +
      '<div class="tha">' + (open ? '<button type="button" class="nbtn" data-act="edit">고치기</button><button type="button" class="nbtn" data-act="del">지우기</button><button type="button" class="nbtn" data-act="done">완료</button>'
                                 : '<button type="button" class="nbtn" data-act="reopen">다시 열기</button>') + '</div></li>';
  }
  function on() { return document.documentElement.dataset.hdShowSent === '1'; }
  function draw() {
    var all = memosOf(cur.id), sh = on(), ms = all.filter(function (n) { return A.visible(n, sh); }), nh = all.length - ms.length;
    var open = ms.filter(A.isOpen), done = ms.filter(function (n) { return !A.isOpen(n); });
    var keep = box.querySelector('details.thdone'), wasOpen = keep && keep.open;
    box.innerHTML = '<div class="thh">' + esc(ctx.title(cur.id)) + ' · 메모 ' + open.length + '건</div><div class="thbody"><ol class="thlist">' + open.map(row).join('') + '</ol>' +
      (nh ? '<div class="thhid">보낸 메모 ' + nh + '건 숨김 — 메모 패널 [보낸 메모 보기]</div>' : '') +
      (done.length ? '<details class="thdone"' + (wasOpen ? ' open' : '') + '><summary>완료 ' + done.length + '</summary><ol class="thlist thdl">' + done.map(row).join('') + '</ol></details>' : '') + '</div>' +
      '<div class="thf"><button type="button" class="nbtn pri" data-act="add">메모 추가</button></div>';
  }
  function focusRow(no) {                            // 핀으로 열었으면 그 메모로(접힌 묶음·답도 편다)
    if (no == null) return;
    var li = box.querySelector('li[data-no="' + no + '"]'); if (!li) return;
    var d = li.closest('details.thdone'); if (d) d.open = true;
    var o = li.querySelector('details.thold'); if (o) o.open = true;
    li.classList.add('focus');
    li.scrollIntoView({block: 'nearest'});
  }
  function place() {                                 // 배지(또는 핀) 아래 오른쪽 끝을 맞춤, 창 안으로 — 붙을 것이 없어졌으면 그 자리 그대로
    if (cur.badge && cur.badge.isConnected) { var b = cur.badge.getBoundingClientRect(); cur.at = {left: b.left, right: b.right, top: b.top, bottom: b.bottom}; }
    var r = cur.at || {left: 8, right: 328, top: 8, bottom: 8}, w = box.offsetWidth, h = box.offsetHeight;
    var x = Math.max(8, Math.min(innerWidth - w - 8, r.right - w)), y = r.bottom + 6;
    if (y + h > innerHeight - 8) y = Math.max(8, r.top - h - 6);
    box.style.left = x + 'px'; box.style.top = y + 'px';
  }
  function open(id, badge, no) {
    if (cur && cur.badge && cur.badge !== badge) cur.badge.setAttribute('aria-expanded', 'false');
    cur = {id: id, badge: badge, no: no == null ? null : no};
    box.hidden = false; draw(); place();
    badge.setAttribute('aria-expanded', 'true');
    focusRow(cur.no);
    var b = (cur.no != null && box.querySelector('li.focus button')) || box.querySelector('button'); if (b) b.focus({preventScroll: true});
  }
  function close() {
    if (!cur) return false;
    if (cur.badge) cur.badge.setAttribute('aria-expanded', 'false');
    cur = null; box.hidden = true; box.innerHTML = ''; ctx.highlight(null, null);
    return true;
  }
  function refresh() {                               // 메모가 바뀌면(셸 renderNotes) 다시 — 다 지웠으면 닫는다, 배지가 없어지면(열린 메모 0) 그 자리에 둔다
    if (!cur) return;
    if (!memosOf(cur.id).length) { close(); return; }
    var card = null;
    Array.prototype.forEach.call(ctx.rowsEl.querySelectorAll('.card'), function (c) { if (c.dataset.id === cur.id) card = c; });
    var badge = card ? card.querySelector('.nbadge') : null;
    if (badge) { cur.badge = badge; badge.setAttribute('aria-expanded', 'true'); }
    var y = box.querySelector('.thbody'), top = y ? y.scrollTop : 0;
    draw(); place();
    if (cur.no != null) { var li = box.querySelector('li[data-no="' + cur.no + '"]'); if (li) li.classList.add('focus'); }
    y = box.querySelector('.thbody'); if (y) y.scrollTop = top;
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
    else if (b.dataset.act === 'done') ctx.done(li.dataset.id);
    else if (b.dataset.act === 'reopen') ctx.reopen(li.dataset.id);
    else if (b.dataset.act === 'choose') {           // 고른 답 = 질문 메모 닫기 + 그 답을 새 메모로 보내기(셸)
      var q = A.question(ctx.list().filter(function (n) { return n.id === li.dataset.id; })[0]);
      if (q && q.choices[+b.dataset.i] != null) ctx.choose(li.dataset.id, q.choices[+b.dataset.i]);
    }
  });
  box.addEventListener('mouseover', function (e) {   // 줄에 올리면 그 핀·요소 테두리
    var li = e.target.closest ? e.target.closest('li[data-no]') : null;
    if (cur) ctx.highlight(cur.id, li ? +li.dataset.no : null);
  });
  box.addEventListener('mouseleave', function () { if (cur) ctx.highlight(cur.id, null); });
  ['pointerdown', 'wheel', 'keydown', 'contextmenu'].forEach(function (n) { box.addEventListener(n, function (e) { if (n !== 'keydown' || e.key !== 'Escape') e.stopPropagation(); }); });

  return {open: open, close: close, refresh: refresh, isOpen: function () { return !!cur; }};
}

HD.viewThread = {mount: mount};
})();
