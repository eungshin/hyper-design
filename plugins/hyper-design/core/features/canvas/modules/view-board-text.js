/* View — 판 글 레이어(t51-9, Figma F1·F9·F10·F12·F14·F15): 판 위 소개·끝 글 그리기와 그 글 묶음·카드 아래 글·DS 카드를 이동 도구(V)로 고르기·고치기·지우기.
   묶음·칸·되는 일 규칙은 modules/board-text.js(Model). 줄 제목은 view-rows 'rowHeads'(51-4)가 그대로 맡는다.
   HD.viewBoardText.paint({intro, foot, esc}, D, hidden) — 소개(#intro)·끝 글(#foot)을 묶음마다 요소 하나(id = 레이어 id 에서 '@' 뺀 것, data-bt = 묶음 키,
     고칠 칸 = data-bk 칸 키)로 그린다. 셸이 처음 그릴 때 부르고, 등록부 기능이 데이터·반영 대기가 바뀔 때 다시 부른다.
   등록부 기능 'boardText'(needs $ · $$ · esc · toast · warn · notes · selected) → {attach(A), data(nd), paint(), place(), reverted(ids) → [id], layers(), selected()}
     A(셸이 attach 로 건넴) = {data: D, on() → 도우미로 바로 쓰나, write(label, list) → Promise(view-sync write), queue(label, list, msg)(반영 대기로),
       hide(ids, on), hidden() → 숨김 표, tool() → 지금 도구, pickCard(id), guard(ids) → 잠김이면 true,
       caption: {values(id), commit(id, changes), open(el, focus)}, reload()(판 글 다시 불러오기 — 뒤 빌드 실패로 되돌린 뒤), changed()(판 높이·레이어가 바뀜)}
   상태 = 고른 판 글 하나 {kind: 'block', key} | {kind: 'cap', id, field}(저장 안 함) · 바로 반영 중인 편집(id → op) · 받은 데이터(base).
   고르기 = 파란 상자 #btsel(이름표 data-label) · 올리기 = 얇은 테두리 #bthov(둘 다 #stage 안, --ts 배율 = 줄과 같은 화면 크기).
   글쇠(window capture — 셸의 카드 지우기·Esc 보다 먼저): Delete·Backspace = 지우기(파일 묶음 = 파일에서 빼기 · 만든 글 = 숨기기 · 카드 제목 = 거절 · 설명·정책 = 비우기),
     Enter = 고치기(소개 칸 = 그 자리 · 카드 글 = 카드 글 상자 · DS 카드 = Foundation 탭), Esc = 풀기(카드 글이면 카드는 골라진 채 — Figma 부모 고르기).
   그 자리 고치기: Enter 저장 · Shift+Enter 줄바꿈(여러 줄 칸) · Esc 취소 · 밖 누르기 저장. 고친 뒤에도 골라진 채(F14).
   의도 받음: 'hd-board-pick' {id: 레이어 id}(레이어 패널 줄 누르기) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var BLUE = '#0f7ec2';

function introHtml(D, esc) {
  var B = HD.boardText, bs = B.blocks(D, {}), has = {};
  bs.forEach(function (b) { has[b.key] = 1; });
  var st = D.story || {}, dc = D.decisions || {};
  var bk = function (k, tag, cls, v) { return '<' + tag + (cls ? ' class="' + cls + '"' : '') + ' data-bk="' + k + '">' + v + '</' + tag + '>'; };
  var h = '<p class="hint bt" id="intro-hint" data-bt="hint">끌어서 둘러보고, 화면을 누르면 크게 보고 직접 눌러볼 수 있어요 · 점선은 주요 흐름' +
    (D.stage === 'go' && D.pending ? ' · 오류·확인·빈 화면 같은 상태 ' + D.pending + '개는 <b>/hyper-design:max</b>로 더할 수 있어요' : '') + '</p>';
  var g = '';
  if (has.story || has.ideas || has.people) {
    g += '<section class="story">';
    if (has.story) g += '<div class="bt" id="intro-story" data-bt="story">' +
      (st.headline ? bk('story.headline', 'h2', '', esc(st.headline).replace(/&lt;(\/?)em&gt;/g, '<$1em>')) : '') +
      (st.summary ? bk('story.summary', 'p', 'sum', esc(st.summary)) : '') + '</div>';
    if (has.ideas) g += '<div class="ideas bt" id="intro-ideas" data-bt="ideas">' + (st.ideas || []).slice(0, 3).map(function (d, i) {
      return '<div class="idea">' + bk('story.ideas.' + i + '.title', 'b', '', esc(d.title)) + bk('story.ideas.' + i + '.desc', 'p', '', esc(d.desc)) + '</div>'; }).join('') + '</div>';
    if (has.people) g += '<div class="people bt" id="intro-people" data-bt="people"><h3>누구를 위한 앱인가</h3><ul>' + D.people.map(function (p, i) {
      return '<li><b>' + bk('people.' + i + '.name', 'span', '', esc(p.name)) + (p.core ? ' · 핵심' : '') + '</b>' + bk('people.' + i + '.why', 'span', '', esc(p.why)) +
        '<span class="win">→ ' + bk('people.' + i + '.win', 'span', '', esc(p.win)) + '</span></li>'; }).join('') + '</ul></div>';
    g += '</section>';
  }
  if (has.decisions || has.market) {
    g += '<section class="decisions">';
    if (has.decisions) g += '<div class="bt" id="intro-decisions" data-bt="decisions"><h3>정한 것 · 뺀 것</h3>' + (dc.core ? bk('decisions.core', 'p', 'core', esc(dc.core)) : '') +
      '<ul>' + (dc.items || []).map(function (it, i) {
        return '<li><span class="v v-' + esc(it.verdict) + '">' + esc(it.label) + '</span>' + bk('decisions.items.' + i + '.name', 'b', '', esc(it.name)) +
          (it.how ? ' → ' + bk('decisions.items.' + i + '.how', 'span', '', esc(it.how)) : '') + bk('decisions.items.' + i + '.why', 'span', 'why', esc(it.why)) + '</li>'; }).join('') + '</ul></div>';
    if (has.market) g += '<div class="bt" id="intro-market" data-bt="market"><h3 class="mk">시장 관례 — 따른 것 · 벗어난 것</h3><ul>' + dc.market.map(function (it, i) {
      return '<li><span class="v v-' + esc(it.verdict) + '">' + esc(it.label) + '</span>' + bk('decisions.market.' + i + '.name', 'b', '', esc(it.name)) +
        '<span class="why">' + esc(it.verdict === 'cut' ? it.why : (it.how || it.why)) + '</span></li>'; }).join('') + '</ul></div>';
    g += '</section>';
  }
  return h + '<div class="intro-grid">' + g + '</div>';
}
function footHtml(D, esc) {
  var f = '', P = D.palettes;
  if (P && P.options && P.options.length) f += '<p class="bt" id="foot-palettes" data-bt="palettes">색 출처: ' + P.options.map(function (o) { return esc(o.name) + ' 웹 팔레트'; }).join(' · ') +
    ' — 시안용 참고. 출시 전 자체 브랜드 색으로 바꾸세요.</p>';
  if (D.credits && D.credits.length) f += '<details class="bt" id="foot-credits" data-bt="credits"><summary>사진 출처 ' + D.credits.length + '장</summary><ul>' + D.credits.map(function (c) {
    var t = esc(c.title || c.file || c.slot);
    var link = c.url ? '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">' + t + '</a>' : t;
    return '<li>' + (c.slot ? esc(c.slot) + ' — ' : '') + link + (c.author ? ' · ' + esc(c.author) : '') + (c.license ? ' · ' + esc(c.license) : '') + '</li>';
  }).join('') + '</ul></details>';
  return f;
}
function paint(els, D, hidden) {
  D = D || {}; hidden = hidden || {};
  var open = els.foot.querySelector('#foot-credits[open]');
  els.intro.innerHTML = introHtml(D, els.esc);
  els.foot.innerHTML = footHtml(D, els.esc);
  if (open && els.foot.querySelector('#foot-credits')) els.foot.querySelector('#foot-credits').open = true;
  HD.boardText.IDS.forEach(function (id) { var t = document.getElementById(id.slice(1)); if (t) t.hidden = !!hidden[id]; });
}

var CSS =
  '#btsel,#bthov{position:absolute;pointer-events:none;box-sizing:border-box;z-index:7;border-radius:calc(4px * var(--ts,1))}\n' +
  '#btsel[hidden],#bthov[hidden]{display:none}\n' +
  '#btsel{border:calc(2px * var(--ts,1)) solid ' + BLUE + ';background:rgba(15,126,194,.04)}\n' +
  '#btsel::before{content:attr(data-label);position:absolute;left:calc(-2px * var(--ts,1));bottom:100%;margin-bottom:calc(2px * var(--ts,1));background:' + BLUE +
    ';font:600 11px/1.5 system-ui,sans-serif;color:#fff;padding:0 6px;border-radius:4px;white-space:nowrap;transform:scale(var(--ts,1));transform-origin:0 100%}\n' +
  '#bthov{border:calc(1px * var(--ts,1)) solid ' + BLUE + '}\n' +
  '#screens.t-move .bt,#screens.t-move #dscard,#screens.t-move .card>.ftitle,#screens.t-move .cbody>.fdesc,#screens.t-move .cbody>.pol{cursor:default}\n' +
  '#stage [data-bk][contenteditable]{cursor:text;outline:calc(2px * var(--ts,1)) solid ' + BLUE + ';outline-offset:calc(3px * var(--ts,1));border-radius:2px;white-space:pre-wrap}\n';

function mount(ctx) {
  var B = HD.boardText, $ = ctx.$, $$ = ctx.$$, A = null, base = null, cur = null, opt = {}, mine = {}, editing = null, later = false, drawn = null;
  var intro = $('#intro'), foot = $('#foot'), stage = intro ? intro.parentNode : null, pane = stage ? stage.parentNode : null;
  if (!intro || !foot || !stage) throw new Error('판 글 자리(#intro·#foot)가 없어요');
  if (!document.getElementById('hd-bt-css')) { var cs = document.createElement('style'); cs.id = 'hd-bt-css'; cs.textContent = CSS; document.head.appendChild(cs); }
  var sel = document.createElement('div'); sel.id = 'btsel'; sel.hidden = true; sel.setAttribute('aria-hidden', 'true');
  var hov = document.createElement('div'); hov.id = 'bthov'; hov.hidden = true; hov.setAttribute('aria-hidden', 'true');
  stage.appendChild(hov); stage.appendChild(sel);

  function dscard() { return document.getElementById('dscard'); }
  function blocks(D) { return B.blocks(D || shown(), {dscard: !!dscard()}); }
  function blockByKey(k) { return blocks().filter(function (b) { return b.key === k; })[0] || null; }
  function elOf(b) { return b ? document.getElementById(b.layer.slice(1)) : null; }
  function shown() {                                 // 받은 데이터 + 반영 대기 + 바로 반영 중
    var ops = B.pending(ctx.notes.list()).concat(Object.keys(opt).map(function (k) { return opt[k]; }));
    return B.apply(base || {}, ops);
  }
  function capEls(id, field) {
    var c = ctx.cardEl ? ctx.cardEl(id) : $('.card[data-id="' + id + '"]'); if (!c) return [];
    if (field === 'title') return $$(':scope > .ftitle', c);
    if (field === 'purpose') return $$(':scope > .cbody > .fdesc', c);
    return $$(':scope > .cbody > .pol, :scope > .cbody > .more', c);
  }
  function curEls() {
    if (!cur) return [];
    if (cur.kind === 'cap') return capEls(cur.id, cur.field);
    var e = elOf(blockByKey(cur.key)); return e ? [e] : [];
  }
  function label() { return !cur ? '' : cur.kind === 'cap' ? B.CAPTION[cur.field] : B.NAMES[cur.key]; }
  function ts() { return (getComputedStyle(ctx.rowsEl || stage).getPropertyValue('--ts') || '1').trim() || '1'; }
  function box(el, els) {                            // 화면 상자 → 판(#stage) 좌표
    var rs = els.filter(function (e) { return e && e.isConnected && !e.hidden && e.getClientRects().length; }).map(function (e) { return e.getBoundingClientRect(); })
      .filter(function (r) { return r.width || r.height; });
    if (!rs.length) { el.hidden = true; return false; }
    var sr = stage.getBoundingClientRect(), k = stage.offsetWidth ? sr.width / stage.offsetWidth : 1, pad = 4;
    var l = Math.min.apply(null, rs.map(function (r) { return r.left; })), t = Math.min.apply(null, rs.map(function (r) { return r.top; }));
    var r = Math.max.apply(null, rs.map(function (x) { return x.right; })), b = Math.max.apply(null, rs.map(function (x) { return x.bottom; }));
    el.style.left = ((l - sr.left) / k - pad) + 'px'; el.style.top = ((t - sr.top) / k - pad) + 'px';
    el.style.width = ((r - l) / k + pad * 2) + 'px'; el.style.height = ((b - t) / k + pad * 2) + 'px';
    el.style.setProperty('--ts', ts()); el.hidden = false;
    return true;
  }
  function place() {
    if (!cur || (editing && cur.kind === 'cap')) { sel.hidden = true; return; }
    var c = cur.kind === 'cap' && (ctx.cardEl ? ctx.cardEl(cur.id) : null);
    if (c && c.classList.contains('capopen')) { sel.hidden = true; return; }   // 카드 글 상자를 여는 동안
    sel.dataset.label = label();
    if (!box(sel, curEls())) { if (cur.kind === 'block') drop(); else sel.hidden = true; }
  }
  function select(s) { cur = s; hov.hidden = true; place(); }
  function drop() { cur = null; sel.hidden = true; }
  function same(a, b) { return a.length === b.length && a.every(function (x, i) { return x === b[i]; }); }
  function stillOn() {                               // 다른 것을 고르면 풀린다: 판 글 = 고른 카드 없음 · 카드 글 = 그 카드 하나만
    if (!cur) return false;
    var s = ctx.selected();
    if (cur.kind === 'block' ? s.length : !same(s, [cur.id])) drop();
    else if (!curEls().length) drop();
    return !!cur;
  }

  // ------------------------------------------------ 그리기
  function repaint() {
    if (editing) { later = true; return; }
    var d = shown(), k = JSON.stringify([d.story, d.people, d.decisions, d.palettes, d.credits, d.stage, d.pending]);
    if (k === drawn) { place(); return; }            // 메모가 바뀔 때마다 부른다 — 판 글이 같으면 다시 그리지 않는다
    drawn = k;
    paint({intro: intro, foot: foot, esc: ctx.esc}, d, A ? A.hidden() : {});
    if (cur && cur.kind === 'block' && !blockByKey(cur.key)) drop();
    place();
    if (A && A.changed) A.changed();
  }

  // ------------------------------------------------ 쓰기 — 바로(도우미) | 반영 대기(없음)
  function commit(op, label, done) {
    var s = B.say(op), n = HD.edits.note('@board', {path: s.path, text: s.text, rect: null}, s.note, op.op, op.to);
    n.edit = 'board'; if (op.op === 'set') n.value = op.value;
    if (!A || !A.on()) { if (A) A.queue(label, [n], label + ' — 반영 대기(도우미로 열면 파일에 바로 써요)'); if (done) done(); return; }
    opt[n.id] = {op: op.op, to: op.to, value: op.value}; n.opt = true; mine[n.id] = 1;
    repaint(); if (done) done();
    A.write(label, [n]).then(function (res) {
      var ok = (res && res.applied || []).indexOf(n.id) >= 0;
      delete opt[n.id];
      if (!ok) {                                       // 거절 = 판을 되돌리고 까닭
        var f = (res && res.failed || []).filter(function (x) { return x.id === n.id; })[0];
        ctx.toast(label + ' — 파일에 쓰지 못했어요' + (f && f.reason ? ': ' + f.reason : ''), false, 6000);
      }
      repaint();
    }, function (e) {                                  // 도우미에 닿지 않음 = 반영 대기로
      delete opt[n.id]; delete n.opt;
      ctx.warn('[hd] 판 글 쓰기 실패: ' + (e && e.message || e));
      A.queue(label, [n], label + ' — 도우미에 닿지 않아 반영 대기로 남겼어요');
      repaint();
    });
  }

  // ------------------------------------------------ 지우기 · 고치기
  function remove() {
    if (!cur) return;
    if (cur.kind === 'cap') {
      var r = B.captionDelete(cur.field, A.caption.values(cur.id));
      if (r.error) { ctx.toast(r.error); return; }
      if (A.guard([cur.id])) return;
      var id = cur.id; drop(); A.caption.commit(id, r.changes); return;
    }
    var b = blockByKey(cur.key); if (!b) { drop(); return; }
    drop();
    if (b.del === 'hide') {
      A.hide([b.layer], true);
      ctx.toast(b.name + ' — 판에서 숨겼어요(만든 글이라 고칠 파일이 없어요) · 레이어 패널에서 다시 보이기', true);
      return;
    }
    commit({op: 'delete', to: b.key}, '판 글 지우기 · ' + b.name);
  }
  function edit(fieldEl) {
    if (!cur) return;
    if (cur.kind === 'cap') { var c = capEls(cur.id, cur.field)[0]; if (c && !A.guard([cur.id])) { sel.hidden = true; A.caption.open(c.matches('.pol, .more') ? c.querySelector('li') || c : c, {field: cur.field === 'policies' ? 'policy' : cur.field}); } return; }
    if (cur.key === 'dscard') { var t = document.querySelector('.tab[data-tab="foundation"]'); if (t) t.click(); return; }
    var b = blockByKey(cur.key), el = elOf(b);
    if (!b || !el) return;
    if (!b.fields.length) { ctx.toast(b.name + ' — 만든 글이라 고칠 수 없어요 · 숨기기만 돼요(Delete)'); return; }
    fieldEl = fieldEl || el.querySelector('[data-bk]');
    if (fieldEl) inPlace(b, fieldEl);
  }
  function inPlace(b, el) {
    var key = el.dataset.bk, f = b.fields.filter(function (x) { return x.key === key; })[0]; if (!f || editing) return;
    var old = el.innerHTML, done = false;
    editing = el; hov.hidden = true;
    el.textContent = key === 'story.headline' ? B.plain(f.value) : f.value;
    try { el.contentEditable = 'plaintext-only'; } catch (e) { el.contentEditable = 'true'; }
    el.setAttribute('role', 'textbox'); el.setAttribute('aria-label', b.name + ' 고치기');
    el.focus();
    var rg = document.createRange(); rg.selectNodeContents(el); var s = getSelection(); s.removeAllRanges(); s.addRange(rg);
    place();
    function end(save) {
      if (done) return; done = true; editing = null;
      var text = el.innerText;
      el.removeAttribute('contenteditable'); el.removeAttribute('role'); el.removeAttribute('aria-label');
      el.removeEventListener('keydown', key_); el.removeEventListener('blur', blur);
      el.innerHTML = old;
      var after = function () { if (later) { later = false; repaint(); } else place(); };
      if (!save) { after(); return; }
      var r = B.check(key, text);
      if (r.error) { ctx.toast(r.error); after(); return; }
      var v = key === 'story.headline' ? B.keepEm(f.value, r.value) : r.value;
      if (v === f.value || (key === 'story.headline' && r.value === B.plain(f.value))) { after(); return; }
      later = false;
      commit({op: 'set', to: key, value: v}, '판 글 고치기 · ' + b.name, after);
    }
    function key_(e) {
      e.stopPropagation();
      if (e.isComposing || e.keyCode === 229) return;
      if (e.key === 'Escape') { e.preventDefault(); end(false); }
      else if (e.key === 'Enter' && !(e.shiftKey && !f.line)) { e.preventDefault(); end(true); }
      else if (e.key === 'Enter') { e.preventDefault(); document.execCommand('insertLineBreak'); }
    }
    function blur() { end(true); }
    el.addEventListener('keydown', key_);
    el.addEventListener('blur', blur);
  }

  // ------------------------------------------------ 누르기 · 올리기
  function hit(t) {                                  // 누른 자리 → {kind, …, el, field?} | null
    if (!t || !t.closest || t.closest('.capbox, #tools, .ly-menu')) return null;
    var b = t.closest('[data-bt]');
    if (b && (intro.contains(b) || foot.contains(b))) return {s: {kind: 'block', key: b.dataset.bt}, el: b, field: t.closest('[data-bk]')};
    var d = t.closest('#dscard'); if (d) return {s: {kind: 'block', key: 'dscard'}, el: d};
    var c = t.closest('.card'); if (!c || c.classList.contains('draft')) return null;
    var cap = t.closest('.card > .ftitle') ? 'title' : t.closest('.cbody > .fdesc') ? 'purpose' : t.closest('.cbody > .pol, .cbody > .more') ? 'policies' : null;
    return cap ? {s: {kind: 'cap', id: c.dataset.id, field: cap}, el: t.closest('.ftitle, .fdesc, .pol, .more')} : null;
  }
  function isCur(s) { return !!cur && s.kind === cur.kind && s.key === cur.key && s.id === cur.id && s.field === cur.field; }
  pane.addEventListener('click', function (e) {
    if (!A || editing) return;
    var h = hit(e.target), tool = A.tool();
    if (tool === 'text' && h && h.s.kind === 'block' && h.field) { select(h.s); edit(h.field); return; }   // 글자 도구 = 바로 그 자리 고치기
    if (tool !== 'move' || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) { if (cur) stillOn(); return; }
    if (!h) { drop(); return; }
    if (h.s.kind === 'cap') A.pickCard(h.s.id);      // 카드 글 = 그 카드 하나 고른 채(설명·정책이 보이는 자리 — task 31)
    select(h.s);
  });
  pane.addEventListener('dblclick', function (e) {
    if (!A || editing) return;
    var h = hit(e.target); if (!h) return;
    var tool = A.tool(); if (tool !== 'move' && tool !== 'text' && tool !== 'hand') return;
    if (h.s.kind === 'cap') { if (tool === 'move') { cur = h.s; sel.hidden = true; } return; }   // 카드 글 상자는 셸 두 번 누르기가 연다 — 이동 도구면 닫은 뒤 다시 고른 채(F14)
    if (h.s.key === 'dscard') return;
    e.preventDefault(); select(h.s); edit(h.field);
  });
  pane.addEventListener('pointermove', function (e) {
    if (!A || editing || e.buttons || A.tool() !== 'move') { hov.hidden = true; return; }
    var h = hit(e.target);
    if (!h || isCur(h.s)) { hov.hidden = true; return; }
    box(hov, h.s.kind === 'cap' ? capEls(h.s.id, h.s.field) : [h.el]);
  });
  pane.addEventListener('pointerleave', function () { hov.hidden = true; });
  pane.addEventListener('pointerdown', function (e) { if (editing && editing.contains(e.target)) e.stopPropagation(); });   // 고치는 중에는 판을 끌지 않는다
  addEventListener('keydown', function (e) {
    if (!cur || editing || !A) return;
    var t = e.target, modal = document.getElementById('modal');
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
    if ((modal && !modal.hidden) || document.body.dataset.tab !== 'screens' || !stillOn()) return;
    var k = e.key;
    if ((k === 'Delete' || k === 'Backspace') && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); e.stopImmediatePropagation(); remove(); }
    else if (k === 'Enter' && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); e.stopImmediatePropagation(); edit(null); }
    else if (k === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); drop(); }
  }, true);
  document.addEventListener('hd-board-pick', function (e) {   // 레이어 패널의 판 글 줄 누르기
    var id = e.detail && e.detail.id, b = blocks().filter(function (x) { return x.layer === id; })[0];
    if (!b || !elOf(b) || elOf(b).hidden || !A) return;
    A.pickCard(null); select({kind: 'block', key: b.key});
  });
  new MutationObserver(function () { if (!sel.hidden) sel.style.setProperty('--ts', ts()); }).observe(ctx.rowsEl || stage, {attributes: true, attributeFilter: ['style']});
  addEventListener('resize', function () { place(); });

  return {
    attach: function (a) { A = a; base = a.data || {}; return this; },
    data: function (nd) { base = nd || {}; repaint(); },
    paint: repaint,
    place: place,
    reverted: function (ids) {                        // 뒤 빌드가 깨져 도우미가 되돌린 편집 중 내 것 → 판 글을 파일대로 다시
      var got = (ids || []).filter(function (id) { return mine[id]; });
      got.forEach(function (id) { delete opt[id]; delete mine[id]; });
      if (got.length && A && A.reload) A.reload();
      return got;
    },
    layers: function () { return B.layers(blocks(), A ? A.hidden() : {}); },
    selected: function () { return cur; }
  };
}

HD.viewBoardText = {paint: paint};
HD.feature('boardText', {needs: ['$', '$$', 'esc', 'toast', 'warn', 'notes', 'selected', 'rowsEl'], mount: mount});
})();
