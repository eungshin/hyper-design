/* View — 카드 아래 글 한 상자(H16). 비교 규칙은 modules/caption.js(Model), 여기는 상자 그리기·글쇠·저장/취소.
   상자 = <div class="capbox" role="group" aria-label="카드 글 고치기">: 첫 줄 = 상태 칩(고칠 수 없음) + 제목 [data-f="title"],
   그다음 설명 [data-f="purpose"], 정책 줄 목록 ul[data-f="policies"] > li, 아래 안내 .capfoot. 상자는 카드의 .phone 바로 뒤에 들어간다.
   글쇠: 제목에서 Enter·Shift+Enter = 설명으로(제목은 한 줄) · 설명에서 Shift+Enter = 줄바꿈(Enter = 다음 칸) · 정책 줄에서 Enter·Shift+Enter = 아래에 새 줄(allowAdd) 또는 다음 줄로(#226)
         ↑/↓ = 칸의 첫/마지막 줄이면 앞/뒤 칸으로 · 빈 새 정책 줄에서 Backspace = 그 줄 지우기 · Esc = 취소 · Ctrl+Enter = 저장
   밖을 누르면 저장, 다른 카드 상자를 열면 열린 상자를 먼저 저장. 붙여넣기는 글만.
   HD.viewCaption.mount(ctx) → {open(cardEl, focus), close(save), isOpen()}  focus = {field: 'title'|'purpose'|'policy', index?}
   ctx = {values(id) → {title, purpose, policies}(반영 대기 포함 지금 값), badge(cardEl) → 칩 Node|null, commit(id, changes), allowAdd, onClose(),
          hint(id) → {title?, purpose?} 빈 칸 안내 글(선택 — 빈 레이아웃은 목적·메모의 몫을 여기서 말한다),
          toast(msg)(선택 — 제목을 비우고 닫으면 알림, 없으면 말없이 원래 제목)}
   지우기(#243): 비운 정책 줄 = 지우기 편집 · 비운 설명 = '' 편집 · 비운 제목 = 편집 없음(원래 이름) · 빈 새 줄 = 버림(비교는 caption.diff) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var STOP = ['pointerdown', 'mousedown', 'click', 'dblclick', 'contextmenu', 'wheel', 'keydown', 'keyup', 'keypress'];
var TITLE_KEEP = '제목은 비울 수 없어요 — 원래 이름으로 둘게요';
var FOOT = '제목 · 설명 · 정책 한 상자 · 설명은 Shift+Enter 줄바꿈 · Esc 취소 · Ctrl+Enter 저장 · 밖을 누르면 저장';

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
  var C = HD.caption, cur = null;                   // cur = {card, id, box, title, purpose, list}

  function fields() {                               // 위에서 아래 순서의 고칠 칸들
    return [cur.title, cur.purpose].concat([].slice.call(cur.list.children));
  }
  function move(el, by, atEnd) {
    var fs = fields(), i = fs.indexOf(el), t = fs[i + by];
    if (t) caretTo(t, atEnd); return !!t;
  }
  function policyLi(text, isNew) {
    var li = document.createElement('li');
    li.setAttribute('contenteditable', 'true'); li.setAttribute('aria-label', '정책 줄');
    if (isNew) li.dataset.new = '1';
    setText(li, text); return li;
  }
  function onKey(e) {
    e.stopPropagation();                            // 캔버스 단축키·Esc 사슬을 막는다
    if (e.isComposing || e.keyCode === 229) return;  // 한글 조합 중
    var el = e.target.closest ? e.target.closest('[data-f="title"], [data-f="purpose"], [data-f="policies"] > li') : null;
    var k = e.key, mod = e.ctrlKey || e.metaKey;
    if (k === 'Escape') { e.preventDefault(); close(false); return; }
    if (k === 'Enter' && mod) { e.preventDefault(); close(true); return; }
    if (mod && /^[biu]$/i.test(k)) { e.preventDefault(); return; }   // 글꼴 꾸미기 없음
    if (!el) return;
    var f = el.dataset.f || 'policy';
    if (k === 'Enter') {
      if (f === 'purpose' && e.shiftKey) { e.preventDefault(); document.execCommand('insertLineBreak'); return; }   // 줄바꿈은 설명(목적)에서만
      e.preventDefault();                           // 제목·정책 줄의 Shift+Enter 는 Enter 와 같다 — 삼키지 않고 다음 칸으로
      if (f === 'policy' && ctx.allowAdd) {
        var li = policyLi('', true); cur.list.insertBefore(li, el.nextSibling); caretTo(li, false); return;
      }
      if (f === 'title' || f === 'purpose' || f === 'policy') move(el, 1, false);
      return;
    }
    if (k === 'ArrowUp' || k === 'ArrowDown') {
      var up = k === 'ArrowUp';
      if (e.shiftKey || !atEdge(el, up)) return;
      if (move(el, up ? -1 : 1, up)) e.preventDefault();
      return;
    }
    if (k === 'Backspace' && f === 'policy' && el.dataset.new && !readText(el).trim()) {
      e.preventDefault();
      if (!move(el, -1, true)) caretTo(cur.title, true);
      el.remove();
    }
  }
  function onPaste(e) {                             // 붙여넣기는 글만(제목·정책 줄은 한 줄로)
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
    setText(purpose, v.purpose);
    purpose.dataset.ph = hint.purpose || '설명 · Shift+Enter 줄바꿈';
    var list = document.createElement('ul'); list.dataset.f = 'policies'; list.className = 'capp';
    (v.policies || []).forEach(function (p) { list.appendChild(policyLi(p, false)); });
    var foot = document.createElement('div'); foot.className = 'capfoot'; foot.textContent = FOOT;
    box.appendChild(head); box.appendChild(purpose); box.appendChild(list); box.appendChild(foot);
    STOP.forEach(function (n) { box.addEventListener(n, function (e) { e.stopPropagation(); }); });
    box.addEventListener('keydown', onKey);
    box.addEventListener('paste', onPaste);
    box.addEventListener('drop', function (e) { e.preventDefault(); });
    var ph = cardEl.querySelector('.phone');
    if (ph && ph.parentNode) ph.parentNode.insertBefore(box, ph.nextSibling); else cardEl.appendChild(box);
    return {card: cardEl, box: box, title: title, purpose: purpose, list: list};
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
    else if (f.field === 'policy') el = cur.list.children[f.index || 0] || cur.title;
    caretTo(el, true);
  }
  function close(save) {
    if (!cur) return;
    var c = cur; cur = null;                        // 다시 들어와도 한 번만
    document.removeEventListener('pointerdown', onOutside, true);
    if (save) {
      var edited = {title: readText(c.title), purpose: readText(c.purpose),
                    policies: [].map.call(c.list.children, function (li) { return readText(li); })};
      var before = ctx.values(c.id) || {};
      var changes = C.diff(before, edited, {allowAdd: !!ctx.allowAdd});
      if (!C.normalise('title', edited.title) && C.normalise('title', before.title) && ctx.toast) ctx.toast(TITLE_KEEP);
      if (changes.length) ctx.commit(c.id, changes);
    }
    c.box.remove();
    if (ctx.onClose) ctx.onClose(c.card);
  }

  return {open: open, close: close, isOpen: function () { return !!cur; }};
}

HD.viewCaption = {mount: mount};
})();
