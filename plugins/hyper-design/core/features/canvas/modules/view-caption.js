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
   지우기(#243): 비운 설명 = '' 편집 · 비운 제목 = 편집 없음(원래 이름) · 정책 메모를 다 비우면 빈 목록 */
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

HD.viewCaption = {mount: mount};
})();
