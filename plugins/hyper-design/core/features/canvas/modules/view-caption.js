/* View — 카드 아래 글 한 상자(H16)와 판의 카드 아래 글 접기(task 31). 비교·보일 칸 규칙은 modules/caption.js(Model), 여기는 그리기·글쇠·저장/취소.
   상자 = <div class="capbox" role="group" aria-label="카드 글 고치기">: 첫 줄 = 상태 칩(고칠 수 없음) + 제목 [data-f="title"],
   그다음 설명 [data-f="purpose"], 정책 메모 [data-f="policies"](여러 줄 글 한 칸 — 글머리표 없음, 한 줄 = 정책 하나), 아래 안내 .capfoot. 상자는 카드의 .phone 바로 뒤에 들어간다.
   글쇠: 제목에서 Enter·Shift+Enter = 설명으로(제목은 한 줄) · 설명에서 Shift+Enter = 줄바꿈(Enter = 정책 메모로) · 정책 메모에서 Enter·Shift+Enter = 새 줄(그 밖은 보통 글 고치기)
         ↑/↓ = 칸의 첫/마지막 줄이면 앞/뒤 칸으로 · Esc = 취소 · Ctrl+Enter = 저장
   밖을 누르면 저장, 다른 카드 상자를 열면 열린 상자를 먼저 저장. 붙여넣기는 글만(제목은 한 줄로, 설명·정책 메모는 줄바꿈 그대로).
   저장: 정책 메모 = caption.lines(줄마다 정리, 빈 줄 버림) → caption.diff 가 목록이 다르면 policies 편집 하나
   HD.viewCaption.mount(ctx) → {open(cardEl, focus), close(save), isOpen(), fold(cardEl, show)}  focus = {field: 'title'|'purpose'|'policy', index?}
     fold(cardEl, {purpose, policies, mark}) = 판의 카드 아래 글 접기(caption.shown 의 답을 그리기만 — 클래스 capfold-d·capfold-p + 작은 표시 .capmark)
   ctx = {values(id) → {title, purpose, policies}(반영 대기 포함 지금 값), badge(cardEl) → 칩 Node|null, commit(id, changes), onClose(),
          hasPolicies(id) → 정책 메모를 둘지(선택, 기본 예 — 빈 레이아웃은 아니오),
          hint(id) → {title?, purpose?} 빈 칸 안내 글(선택 — 빈 레이아웃은 목적·메모의 몫을 여기서 말한다),
          toast(msg)(선택 — 제목을 비우고 닫으면 알림, 없으면 말없이 원래 제목)}
   지우기(#243): 비운 설명 = '' 편집 · 비운 제목 = 편집 없음(원래 이름) · 정책 메모를 다 비우면 빈 목록
   판의 카드 글(셸 C8): HD.viewCaption.cards(ctx) → {setOrig(rows), orig(id), put(id, o), cardsOf(ids?), paint(ids?), fold(ids?), open(el, focus), values(id), commit(id, changes)}
     원래 글(ORIG = HD.caption.origOf, 처음·쓴 뒤 데이터를 합쳐 쌓음)의 주인 · 카드 제목·설명·정책 줄 그리기(반영 대기 = .pend) · 접기 · 위 상자(mount)를 그 값으로 열기 ·
     카드 글 두 번 누르기. 바뀐 칸마다 편집 메모 하나 → ctx.add 한 번(되돌리기 한 번) · 빈 레이아웃 = ctx.editLayout
     ctx = {$, $$, rowsEl, pane, notes(NS), polHtml(pol, cls), space(), selected() → 고른 id|null(고르기가 붙기 전), typing(e), guard(ids), closeMenus(), toast(msg),
            placed()(닫은 뒤 판 글 다시 놓기), layoutOf(id), editLayout(id, changes), note(id, h, text), add(label, list)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var STOP = ['pointerdown', 'mousedown', 'click', 'dblclick', 'contextmenu', 'wheel', 'keydown', 'keyup', 'keypress'];
var TITLE_KEEP = '제목은 비울 수 없어요 — 원래 이름으로 둘게요';
var FOOT = '제목 · 설명 · 정책 한 상자 · 정책은 한 줄에 하나(Enter 새 줄, 빈 줄은 버림) · 설명은 Shift+Enter 줄바꿈 · Esc 취소 · Ctrl+Enter 저장 · 밖을 누르면 저장';
var MARK = '설명·정책 고침';

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
  var C = HD.caption, cur = null;                   // cur = {card, id, box, title, purpose, note}

  function fields() {                               // 위에서 아래 순서의 고칠 칸들
    return cur.note ? [cur.title, cur.purpose, cur.note] : [cur.title, cur.purpose];
  }
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
      if (f === 'policies' || (f === 'purpose' && e.shiftKey)) { document.execCommand('insertLineBreak'); return; }   // 정책 메모 = 늘 새 줄 · 설명 = Shift+Enter
      move(el, 1, false);                           // 제목(Shift+Enter 도)·설명 Enter = 다음 칸
      return;
    }
    if (k === 'ArrowUp' || k === 'ArrowDown') {
      var up = k === 'ArrowUp';
      if (e.shiftKey || !atEdge(el, up)) return;
      if (move(el, up ? -1 : 1, up)) e.preventDefault();
      return;
    }
  }
  function onPaste(e) {                             // 붙여넣기는 글만(제목은 한 줄로, 설명·정책 메모는 줄바꿈 그대로)
    e.preventDefault();
    var t = (e.clipboardData || window.clipboardData).getData('text/plain') || '';
    var el = e.target.closest ? e.target.closest('[data-f="purpose"], [data-f="policies"]') : null;
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
    setText(purpose, v.purpose);
    purpose.dataset.ph = hint.purpose || '설명 · Shift+Enter 줄바꿈';
    var note = null;
    if (!ctx.hasPolicies || ctx.hasPolicies(cardEl.dataset.id)) {
      note = document.createElement('div'); note.dataset.f = 'policies'; note.className = 'capp';
      note.setAttribute('contenteditable', 'true'); note.setAttribute('aria-label', '정책 — 한 줄에 하나');
      setText(note, (v.policies || []).join('\n'));
      note.dataset.ph = '정책 — 한 줄에 하나 · Enter 새 줄';
    }
    var foot = document.createElement('div'); foot.className = 'capfoot'; foot.textContent = FOOT;
    box.appendChild(head); box.appendChild(purpose); if (note) box.appendChild(note); box.appendChild(foot);
    STOP.forEach(function (n) { box.addEventListener(n, function (e) { e.stopPropagation(); }); });
    box.addEventListener('keydown', onKey);
    box.addEventListener('paste', onPaste);
    box.addEventListener('drop', function (e) { e.preventDefault(); });
    var ph = cardEl.querySelector('.phone');
    if (ph && ph.parentNode) ph.parentNode.insertBefore(box, ph.nextSibling); else cardEl.appendChild(box);
    return {card: cardEl, box: box, title: title, purpose: purpose, note: note};
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
    var f = focus || {field: 'title'}, el = cur.title;
    if (f.field === 'purpose') el = cur.purpose;
    else if (f.field === 'policy' && cur.note) { lineEnd(cur.note, f.index || 0); return; }
    caretTo(el, true);
  }
  function lineEnd(el, i) {                         // 정책 메모의 i 번째 줄 끝에 글자 자리
    var br = el.querySelectorAll('br')[i];
    if (!br) { caretTo(el, true); return; }
    el.focus();
    var sel = window.getSelection(); if (!sel) return;
    var r = document.createRange(); r.setStartBefore(br); r.collapse(true);
    sel.removeAllRanges(); sel.addRange(r);
  }
  function close(save) {
    if (!cur) return;
    var c = cur; cur = null;                        // 다시 들어와도 한 번만
    document.removeEventListener('pointerdown', onOutside, true);
    if (save) {
      var edited = {title: readText(c.title), purpose: readText(c.purpose),
                    policies: c.note ? C.lines(readText(c.note)) : null};
      var before = ctx.values(c.id) || {};
      if (!c.note) edited.policies = before.policies;
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
    cardEl.classList.toggle('capfold-p', !show.policies);
    var m = cardEl.querySelector(':scope > .capmark');
    if (show.mark && !m) {
      m = document.createElement('span'); m.className = 'capmark'; m.textContent = MARK; m.title = '설명이나 정책에 반영 대기 편집이 있어요 — 카드를 고르면 보여요';
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
  function commit(id, changes) {                     // 바뀐 칸마다 편집 메모 하나(title·purpose·policies = 정책 목록 통째로, task 31) → 한 번의 add = 되돌리기 한 번
    if (!ORIG[id]) { ctx.editLayout(id, changes); return; }
    var list = changes.map(function (ch) {
      var path = 'screens.json > screens[id=' + id + '] > ' + ch.field, old = Array.isArray(ch.old) ? ch.old.join(' · ') : ch.old;
      var n = ctx.note(id, {path: path, text: old, rect: null}, HD.edits.say.field(ch.field, ch.value, null, ch.old));
      n.edit = ch.field; n.value = ch.value;           // policies = 줄 목록 통째로
      return n;
    });
    ctx.add('카드 글', list);
  }
  function fold(ids) {                               // 판의 카드 아래 글 접기(task 31): 고르지 않은 카드 = 제목만(+ 반영 대기 표시) · 고른 카드·빈 레이아웃 = 다
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
      [['title', '.ftitle'], ['purpose', '.fdesc']].forEach(function (fs) {
        var el = $(fs[1], c); if (!el || $('input, textarea', el)) return;
        var v = pendingOf(id, fs[0]), keep = $('.state', el);
        el.textContent = v != null ? v : o[fs[0]]; if (keep) el.insertBefore(keep, el.firstChild);
        el.classList.toggle('pend', v != null);
        if (v != null) el.title = '반영 대기 · 원래: ' + o[fs[0]]; else el.removeAttribute('title');
      });
      var pp = polPending(id), pol = pp || o.policies;   // 정책 = 반영 대기 목록 하나(task 31) 또는 원래 목록
      var cls = pp ? function (i) { return pol[i] === o.policies[i] ? '' : 'pend'; } : null;
      var key = JSON.stringify([pol, pp ? pol.map(function (x, i) { return cls(i); }) : 0]);
      if (c.dataset.polKey !== key) {                  // 바뀐 때만 다시(다른 칸 그리기가 정책 줄을 건드리지 않게)
        var open = !!$('details.more[open]', c);
        var body = $(':scope > .cbody', c), d = body && $(':scope > .fdesc', body);
        if (body) { $$(':scope > .pol, :scope > .more', body).forEach(function (x) { x.remove(); }); body.insertAdjacentHTML(d ? 'beforeend' : 'afterbegin', ctx.polHtml(pol, cls)); }
        if (open && $('details.more', c)) $('details.more', c).open = true;
        c.dataset.polKey = key;
      }
    });
    fold(ids);
    ctx.space();                                      // 카드 글이 바뀌면 줄 사이도(펼친 설명 자리, t51-8)
  }
  var CAP = mount({values: values, badge: function (c) { return $('.ftitle .state', c); }, commit: commit,
    hasPolicies: function (id) { return !!ORIG[id]; },   // 빈 레이아웃은 이름·목적만(#225)
    toast: function (m) { ctx.toast(m); },
    hint: function (id) { return ORIG[id] ? null : {title: '새 화면 이름', purpose: '이 화면의 목적 — 무엇을 하는 화면인지 (자세한 지시는 메모로) · Shift+Enter 줄바꿈'}; },
    onClose: function (c) { if (c) c.classList.remove('capopen'); paint(c ? [c.dataset.id] : null); ctx.placed(); }});   // 닫은 뒤에도 그 카드 글이 골라진 채(F14, t51-9)
  function open(el, focus) {                         // el = 카드 안 아무 글(.ftitle·.fdesc·.pol li) · focus = 글자 자리를 둘 칸
    ctx.closeMenus();
    var c = el && el.closest('.card'); if (!c) return;
    var id = c.dataset.id;
    if (ctx.guard([id])) return;
    if (focus.field === 'policy') focus = {field: 'policy', index: $$('.pol li', c).indexOf(el)};
    c.classList.add('capopen');
    CAP.open(c, focus);
  }
  ctx.pane.addEventListener('dblclick', function (e) {   // 카드 이름·설명·정책 줄 두 번 누르기 = 그 칸에서 상자 열기
    var t = e.target, cl = function (q) { return t && t.closest ? t.closest(q) : null; };
    if (cl('#tools') || cl('.alabel') || ctx.typing(e)) return;
    var ft = cl('.ftitle'), fd = cl('.fdesc'), fp = cl('.pol li');
    if (fp) { e.preventDefault(); open(fp, {field: 'policy'}); return; }
    if (ft) { e.preventDefault(); open(ft, {field: 'title'}); return; }
    if (fd) { e.preventDefault(); open(fd, {field: 'purpose'}); return; }
  });
  return {setOrig: setOrig, orig: function (id) { return ORIG[id]; }, put: function (id, o) { ORIG[id] = o; },
          cardsOf: cardsOf, paint: paint, fold: fold, open: open, values: values, commit: commit};
}

HD.viewCaption = {mount: mount, cards: cards};
})();
