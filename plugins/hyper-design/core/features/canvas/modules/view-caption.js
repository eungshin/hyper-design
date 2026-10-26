/* View — 카드 아래 글 한 상자(H16 · R21)와 판의 카드 아래 글 접기(task 31). 비교·보일 칸 규칙은 modules/caption.js(Model), 여기는 그리기·글쇠·저장/취소.
   상자 = <div class="capbox" role="group" aria-label="카드 글 고치기">: 첫 줄 = 상태 칩(고칠 수 없음) + 제목 [data-f="title"](한 줄),
   그다음 본문 [data-f="purpose"](여러 줄 자유 글 한 칸 — 옛 정책 줄은 caption.body 로 '- ' 줄이 되어 함께 들어온다). 상자는 카드의 .phone 바로 뒤에 들어간다.
   글쇠: 제목에서 Enter·Shift+Enter = 본문으로 · 본문에서 Enter·Shift+Enter = 줄바꿈
         ↑/↓ = 칸의 첫/마지막 줄이면 앞/뒤 칸으로 · Esc = 취소 · Ctrl+Enter = 저장
   밖을 누르면 저장, 다른 카드 상자를 열면 열린 상자를 먼저 저장. 붙여넣기는 글만(제목은 한 줄로, 본문은 줄바꿈 그대로).
   저장: caption.diff(지금 값, {title, body}) — 본문이 바뀌면 purpose 하나 + 옛 정책 줄이 있었으면 policies [] (접기)
   HD.viewCaption.mount(ctx) → {open(cardEl, focus), close(save), isOpen(), fold(cardEl, show)}  focus = {field: 'title'|'purpose'}
     fold(cardEl, {purpose, mark}) = 판의 카드 아래 글 접기(caption.shown 의 답을 그리기만 — 클래스 capfold-d + 작은 표시 .capmark)
   ctx = {values(id) → {title, purpose, policies}(반영 대기 포함 지금 값), badge(cardEl) → 칩 Node|null, commit(id, changes), onClose(),
          hint(id) → {title?, purpose?} 빈 칸 안내 글(선택 — 빈 레이아웃은 목적·메모의 몫을 여기서 말한다),
          toast(msg)(선택 — 제목을 비우고 닫으면 알림, 없으면 말없이 원래 제목)}
   지우기(#243): 본문을 다 비우면 '' · 비운 제목 = 편집 없음(원래 이름)
   판의 카드 글(셸 C8): HD.viewCaption.cards(ctx) → {setOrig(rows), orig(id), put(id, o), cardsOf(ids?), paint(ids?), fold(ids?), open(el, focus), values(id), commit(id, changes)}
     원래 글(ORIG = HD.caption.origOf, 처음·쓴 뒤 데이터를 합쳐 쌓음)의 주인 · 카드 제목·본문 그리기(반영 대기 = .pend) · 접기 · 위 상자(mount)를 그 값으로 열기 ·
     카드 글 두 번 누르기. 바뀐 칸마다 편집 메모 하나 → ctx.add 한 번(되돌리기 한 번) · 빈 레이아웃 = ctx.editLayout
     ctx = {$, $$, rowsEl, pane, notes(NS), space(), selected() → 고른 id|null(고르기가 붙기 전), typing(e), guard(ids), closeMenus(), toast(msg),
            placed()(닫은 뒤 판 글 다시 놓기), layoutOf(id), editLayout(id, changes), note(id, h, text), add(label, list)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var STOP = ['pointerdown', 'mousedown', 'click', 'dblclick', 'contextmenu', 'wheel', 'keydown', 'keyup', 'keypress'];
var TITLE_KEEP = '제목은 비울 수 없어요 — 원래 이름으로 둘게요';
var MARK = '설명 고침';

function readText(el) {                             // 칸의 글: 글 마디 그대로, <br>·블록 = 줄바꿈(화면 배치와 무관)
  var s = '';
  (function walk(n) {
    for (var c = n.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 3) s += c.data;
      else if (c.nodeType === 1) {
        if (c.tagName === 'BR') { s += '\n'; continue; }
        var block = /^(DIV|P|LI)$/.test(c.tagName);
        if (block && s && s.charAt(s.length - 1) !== '\n') s += '\n';
        walk(c);
      }
    }
  })(el);
  return s;
}
function setText(el, text) {                        // 줄바꿈은 <br> 로
  el.textContent = '';
  String(text || '').split('\n').forEach(function (ln, i) {
    if (i) el.appendChild(document.createElement('br'));
    if (ln) el.appendChild(document.createTextNode(ln));
  });
}
function caretTo(el, atEnd) {
  el.focus();
  var sel = window.getSelection(); if (!sel) return;
  var r = document.createRange(); r.selectNodeContents(el); r.collapse(!atEnd);
  sel.removeAllRanges(); sel.addRange(r);
}
function atEdge(el, up) {                           // 글자 자리가 칸의 첫(up)/마지막 줄인가
  var sel = window.getSelection(); if (!sel || !sel.rangeCount) return true;
  var r = sel.getRangeAt(0).cloneRange(); r.collapse(up);
  var rs = r.getClientRects(), cr = rs.length ? rs[0] : null;
  if (!cr || (!cr.width && !cr.height)) {          // 빈 줄 등: 글 앞/뒤 위치로 판단
    var pre = document.createRange(); pre.selectNodeContents(el);
    if (up) pre.setEnd(r.startContainer, r.startOffset); else pre.setStart(r.startContainer, r.startOffset);
    var frag = pre.cloneContents();
    return !frag.querySelector('br') && !/\n/.test(frag.textContent);
  }
  var er = el.getBoundingClientRect(), lh = parseFloat(getComputedStyle(el).lineHeight) || cr.height || 20;
  return up ? cr.top - er.top < lh * 0.8 : er.bottom - cr.bottom < lh * 0.8;
}

function mount(ctx) {
  var C = HD.caption, cur = null;                   // cur = {card, id, box, title, purpose}

  function fields() { return [cur.title, cur.purpose]; }   // 위에서 아래 순서의 고칠 칸들
  function move(el, by, atEnd) {
    var fs = fields(), i = fs.indexOf(el), t = fs[i + by];
    if (t) caretTo(t, atEnd); return !!t;
  }
  function onKey(e) {
    e.stopPropagation();                            // 캔버스 단축키·Esc 사슬을 막는다
    if (e.isComposing || e.keyCode === 229) return;  // 한글 조합 중
    var el = e.target.closest ? e.target.closest('[data-f]') : null;
    var k = e.key, mod = e.ctrlKey || e.metaKey;
    if (k === 'Escape') { e.preventDefault(); close(false); return; }
    if (k === 'Enter' && mod) { e.preventDefault(); close(true); return; }
    if (mod && /^[biu]$/i.test(k)) { e.preventDefault(); return; }   // 글꼴 꾸미기 없음
    if (!el) return;
    var f = el.dataset.f;
    if (k === 'Enter') {
      e.preventDefault();
      if (f === 'purpose') { document.execCommand('insertLineBreak'); return; }   // 본문 = 늘 줄바꿈(R21)
      move(el, 1, false);                           // 제목 Enter(Shift+Enter 도) = 본문으로
      return;
    }
    if (k === 'ArrowUp' || k === 'ArrowDown') {
      var up = k === 'ArrowUp';
      if (e.shiftKey || !atEdge(el, up)) return;
      if (move(el, up ? -1 : 1, up)) e.preventDefault();
      return;
    }
  }
  function onPaste(e) {                             // 붙여넣기는 글만(제목은 한 줄로, 본문은 줄바꿈 그대로)
    e.preventDefault();
    var t = (e.clipboardData || window.clipboardData).getData('text/plain') || '';
    var el = e.target.closest ? e.target.closest('[data-f="purpose"]') : null;
    t = el ? t.replace(/\r\n?/g, '\n') : t.replace(/\s+/g, ' ');
    if (el && /\n/.test(t)) {
      t.split('\n').forEach(function (ln, i) { if (i) document.execCommand('insertLineBreak'); if (ln) document.execCommand('insertText', false, ln); });
    } else document.execCommand('insertText', false, t);
  }
  function onOutside(e) {                           // 상자 밖 누르기 = 저장
    if (cur && !cur.box.contains(e.target)) close(true);
  }

  function build(cardEl, v, hint) {
    var box = document.createElement('div');
    box.className = 'capbox'; box.setAttribute('role', 'group'); box.setAttribute('aria-label', '카드 글 고치기');
    var head = document.createElement('div'); head.className = 'capttl';
    var b = ctx.badge ? ctx.badge(cardEl) : null;
    if (b) { b = b.cloneNode(true); b.setAttribute('contenteditable', 'false'); head.appendChild(b); }
    var title = document.createElement('div');
    title.dataset.f = 'title'; title.className = 'capt'; title.setAttribute('contenteditable', 'true'); title.setAttribute('aria-label', '제목');
    setText(title, v.title); head.appendChild(title);
    if (hint.title) title.dataset.ph = hint.title;
    var purpose = document.createElement('div');
    purpose.dataset.f = 'purpose'; purpose.className = 'capd'; purpose.setAttribute('contenteditable', 'true'); purpose.setAttribute('aria-label', '설명');
    setText(purpose, C.body(v.purpose, v.policies));   // 본문 한 칸 = 설명 + 옛 정책 줄(R21)
    purpose.dataset.ph = hint.purpose || '설명';
    box.appendChild(head); box.appendChild(purpose);
    STOP.forEach(function (n) { box.addEventListener(n, function (e) { e.stopPropagation(); }); });
    box.addEventListener('keydown', onKey);
    box.addEventListener('paste', onPaste);
    box.addEventListener('drop', function (e) { e.preventDefault(); });
    var ph = cardEl.querySelector('.phone');
    if (ph && ph.parentNode) ph.parentNode.insertBefore(box, ph.nextSibling); else cardEl.appendChild(box);
    return {card: cardEl, box: box, title: title, purpose: purpose};
  }

  function open(cardEl, focus) {
    if (!cardEl) return;
    if (cur) { if (cur.card === cardEl) { place(focus); return; } close(true); }
    var id = cardEl.dataset.id, v = ctx.values(id) || {title: '', purpose: '', policies: []};
    cur = build(cardEl, v, (ctx.hint && ctx.hint(id)) || {}); cur.id = id;
    document.addEventListener('pointerdown', onOutside, true);
    place(focus);
  }
  function place(focus) {
    var f = focus || {field: 'title'};
    caretTo(f.field === 'title' ? cur.title : cur.purpose, true);
  }
  function close(save) {
    if (!cur) return;
    var c = cur; cur = null;                        // 다시 들어와도 한 번만
    document.removeEventListener('pointerdown', onOutside, true);
    if (save) {
      var edited = {title: readText(c.title), body: readText(c.purpose)};
      var before = ctx.values(c.id) || {};
      var changes = C.diff(before, edited);
      if (!C.normalise('title', edited.title) && C.normalise('title', before.title) && ctx.toast) ctx.toast(TITLE_KEEP);
      if (changes.length) ctx.commit(c.id, changes);
    }
    c.box.remove();
    if (ctx.onClose) ctx.onClose(c.card);
  }

  function fold(cardEl, show) {                     // 판의 카드 아래 글 접기 — 무엇을 보일지는 caption.shown(Model)
    if (!cardEl) return;
    cardEl.classList.toggle('capfold-d', !show.purpose);
    var m = cardEl.querySelector(':scope > .capmark');
    if (show.mark && !m) {
      m = document.createElement('span'); m.className = 'capmark'; m.textContent = MARK; m.title = '설명에 반영 대기 편집이 있어요 — 카드를 고르면 보여요';
      var t = cardEl.querySelector(':scope > .ftitle');
      if (t) t.parentNode.insertBefore(m, t.nextSibling); else cardEl.appendChild(m);
    } else if (!show.mark && m) m.remove();
  }

  return {open: open, close: close, isOpen: function () { return !!cur; }, fold: fold};
}

function cards(ctx) {
  var $ = ctx.$, $$ = ctx.$$, NS = ctx.notes, ORIG = {};
  function setOrig(rows) { var o = HD.caption.origOf(rows); Object.keys(o).forEach(function (id) { ORIG[id] = o[id]; }); }   // 합쳐 쌓는다(데이터에서 빠진 화면 글도 남음)
  function pendingOf(id, field, index) { return HD.notes.pendingOf(NS.list(), id, field, index); }   // 그 화면·그 칸의 마지막 편집 값(없으면 null)
  function polPending(id) { return HD.caption.pending(NS.list(), id, (ORIG[id] || {}).policies || []); }   // 그 화면의 반영 대기 정책 목록(없으면 null)
  function cardsOf(ids) {                            // ids 없음 = 판의 카드 전부 · 있으면 그 화면 카드만(메모 저장은 닿은 카드만 다시 그린다)
    var all = $$('.card', ctx.rowsEl);
    return ids ? all.filter(function (c) { return ids.indexOf(c.dataset.id) >= 0; }) : all;
  }
  function values(id) {
    var o = ORIG[id];
    if (!o) { var dn = ctx.layoutOf(id); return dn ? {title: dn.value, purpose: dn.purpose || '', policies: []} : null; }   // 빈 레이아웃 = 그 메모의 이름·목적
    var t = pendingOf(id, 'title'), d = pendingOf(id, 'purpose');
    return {title: t != null ? t : o.title, purpose: d != null ? d : o.purpose, policies: polPending(id) || o.policies.slice()};
  }
  function commit(id, changes) {                     // 바뀐 칸마다 편집 메모 하나(title·purpose · policies [] = 옛 정책 줄을 본문에 접음, R21) → 한 번의 add = 되돌리기 한 번
    if (!ORIG[id]) { ctx.editLayout(id, changes); return; }
    var list = changes.map(function (ch) {
      var path = 'screens.json > screens[id=' + id + '] > ' + ch.field, old = Array.isArray(ch.old) ? ch.old.join(' · ') : ch.old;
      var n = ctx.note(id, {path: path, text: old, rect: null}, HD.edits.say.field(ch.field, ch.value, null, ch.old));
      n.edit = ch.field; n.value = ch.value;
      return n;
    });
    ctx.add('카드 글', list);
  }
  function fold(ids) {                               // 판의 카드 아래 글 접기(task 31): 고르지 않은 카드 = 제목만(+ 반영 대기 표시) · 고른 카드·빈 레이아웃 = 본문까지
    var sel = ctx.selected(); if (!sel) return;       // 셸이 다 붙기 전(처음 그리기) — 고르기를 붙인 뒤 한 번 부른다
    var on = {}; sel.forEach(function (x) { on[x] = 1; });
    cardsOf(ids).forEach(function (c) {
      var id = c.dataset.id;
      CAP.fold(c, HD.caption.shown({selected: !!on[id], blank: !ORIG[id], pending: {purpose: pendingOf(id, 'purpose') != null, policies: polPending(id) != null}}));
    });
  }
  function paint(ids) {
    cardsOf(ids).forEach(function (c) {
      var id = c.dataset.id, o = ORIG[id]; if (!o) return;
      var el = $(':scope > .ftitle', c), v = pendingOf(id, 'title');
      if (el && !$('input, textarea', el)) {
        var keep = $('.state', el);
        el.textContent = v != null ? v : o.title; if (keep) el.insertBefore(keep, el.firstChild);
        el.classList.toggle('pend', v != null);
        if (v != null) el.title = '반영 대기 · 원래: ' + o.title; else el.removeAttribute('title');
      }
      var cb = $(':scope > .cbody', c); if (!cb) return;   // 본문 한 칸(R21) = 설명 + 옛 정책 줄 — 반영 대기가 이긴다
      var d = pendingOf(id, 'purpose'), pp = polPending(id), pend = d != null || pp != null;
      var text = HD.caption.body(d != null ? d : o.purpose, pp || o.policies), was = HD.caption.body(o.purpose, o.policies);
      var fd = $(':scope > .fdesc', cb);
      if (!text) { if (fd) fd.remove(); return; }
      if (!fd) { fd = document.createElement('div'); fd.className = 'fdesc'; cb.insertBefore(fd, cb.firstChild); }
      fd.textContent = text;
      fd.classList.toggle('pend', pend);
      if (pend) fd.title = '반영 대기 · 원래: ' + (was || '(비어 있음)'); else fd.removeAttribute('title');
    });
    fold(ids);
    ctx.space();                                      // 카드 글이 바뀌면 줄 사이도(펼친 설명 자리, t51-8)
  }
  var CAP = mount({values: values, badge: function (c) { return $('.ftitle .state', c); }, commit: commit,
    toast: function (m) { ctx.toast(m); },
    hint: function (id) { return ORIG[id] ? null : {title: '새 화면 이름', purpose: '이 화면의 목적 — 무엇을 하는 화면인지 (자세한 지시는 메모로)'}; },
    onClose: function (c) { if (c) c.classList.remove('capopen'); paint(c ? [c.dataset.id] : null); ctx.placed(); }});   // 닫은 뒤에도 그 카드 글이 골라진 채(F14, t51-9)
  function open(el, focus) {                         // el = 카드 안 아무 글(.ftitle·.fdesc) · focus = 글자 자리를 둘 칸
    ctx.closeMenus();
    var c = el && el.closest('.card'); if (!c) return;
    var id = c.dataset.id;
    if (ctx.guard([id])) return;
    c.classList.add('capopen');
    CAP.open(c, focus);
  }
  ctx.pane.addEventListener('dblclick', function (e) {   // 카드 이름·본문 두 번 누르기 = 그 칸에서 상자 열기
    var t = e.target, cl = function (q) { return t && t.closest ? t.closest(q) : null; };
    if (cl('#tools') || cl('.alabel') || ctx.typing(e)) return;
    var ft = cl('.ftitle'), fd = cl('.fdesc');
    if (ft) { e.preventDefault(); open(ft, {field: 'title'}); return; }
    if (fd) { e.preventDefault(); open(fd, {field: 'purpose'}); return; }
  });
  return {setOrig: setOrig, orig: function (id) { return ORIG[id]; }, put: function (id, o) { ORIG[id] = o; },
          cardsOf: cardsOf, paint: paint, fold: fold, open: open, values: values, commit: commit};
}

HD.viewCaption = {mount: mount, cards: cards};
})();
