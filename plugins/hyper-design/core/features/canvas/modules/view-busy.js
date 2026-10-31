/* View — 화면 파일 보기: "AI 수정 중" 상태 칩 그리기(Q2b, D14 · #254 · task 37)와 도우미가 알린 바뀐 화면 카드만 다시 싣기. 규칙은 modules/busy.js(Model).
   화면을 가리지 않는다: 칩 = 카드 제목 줄 오른쪽 끝(.card 바로 아래, 화면 밖 — R27) — 예전엔 카드 .phone 오른쪽 위 <div class="busy bchip" data-via data-kind="working|queued" role="status" title=전체 글>
   (도는 표시 또는 점 + HD.busy.look 의 짧은 글 + [×](data-act=lift, 걷기)) · working 이면 .phone[data-busy=working] 에 강조 테두리, queued 는 칩만.
   크게 보기가 그 화면이면 같은 칩을 #modal .mbar 에(덮개 없음). 칩 모양 CSS 는 여기서 <style id="hd-busy-css"> 로 넣는다(템플릿 .busy 덮개 규칙을 덮어씀).
   화면 파일이 바뀌면 걷고 그 카드만 다시 부른다. 칩이 하나라도 있는 동안만 ctx.watch 를 2000ms 마다 부른다. 상태는 ctx.key 로 저장해 새로 고쳐도 남는다.
   adopt() = 상태 파일에서 busy 가 바뀜(hd claim·release, view-state-sync onExternal) → 다시 읽어 그리기(새로고침 없음).
   ctx.files 가 있으면 1000ms 마다(보일 때만) 도우미의 바뀐 화면 목록을 받아 HD.busy.refresh 로 고른 카드만 ctx.reload,
   크게 보기가 그 화면이면 ctx.reloadModal. wrote(ids) = 판이 방금 스스로 쓴·다시 실은 화면(5초 동안 다시 싣지 않음).
   앱 카드(#272): 카드 iframe 이 보낸 hd-here(palette.js 로드 · 감싸개 HMR {hmr:true}) → HD.busy 'here'(shouldLift). 화면 id = d.screen,
   보낸 창이 그 카드의 iframe 일 때만(크게 보기 등은 무시). 이 판에서 그 카드의 첫 로드는 first(걷지 않음). 걷어도 다시 싣지 않는다(이미 새 화면).
   hd-here {error}(감싸개가 앱의 비공개 모듈을 못 읽음, #280) = 그 카드 화면 밑에 빨간 한 줄 .cerr(role=alert, title = 전체) + [hd] 경고 —
     토스트가 아니고 카드마다 같은 글은 한 번(HD.busy.hereError), 그 카드가 다시 잘 실리면(error 없는 hd-here) 걷는다. 덮개는 걷지 않는다.
   "방금 반영됨 ✓"(48a): 화면 파일이 바뀌어 걷힌 카드(손 걷기 × 는 아님)의 교체가 끝나면(document 'hd-swap' {id, phase:'done'} — view-swap) 같은 자리에
     칩 <div class="busy bchip" data-kind="done"> 을 HD.busy.DONE_MS 동안(규칙 HD.busy.landed) · 앱 카드가 hd-here 로 걷히면 바로(이미 새 화면).
     'hd-swap' failed {why} = 그 카드 .cerr 한 줄(앱 카드 실패 줄과 같은 길) — 그 카드의 다음 done 이 걷는다.
     전/후 보기(48b): done 에 before(옛 화면 스냅숏 있음)면 칩에 [전/후](button.bcmp[data-act=compare][aria-pressed]) — HD.busy.doneMs(true)(10초) 동안,
     누르면 'hd-swap-compare' {id, on:true}(view-swap 이 옛 화면을 겹침, 칩 글 '바뀌기 전 화면', 보는 동안 칩이 남음) · 다시 누르면 off 와 10초 다시.
     칩이 걷히면(새 교체 'hd-swap' start · 덮개 다시 씀) 켜져 있던 전/후 보기도 off.
   실시간(47-4b, view-live): live(true) = /api/files 1초 읽기 멈춤(덮개 칩의 /api/watch 는 칩이 있는 동안 그대로) · changed(ids, seq) = 이벤트 screen.written by ai
     (폴링 답과 같은 길 — seq 를 기준으로 삼아 폴링으로 돌아가도 이어짐) · resync() = /api/files 한 번(reset 뒤 놓친 것) · since() = 지금 파일 seq|null
   공용 스타일 파일(R55): 바뀐 목록에 '@tokens'·'@components'(도우미가 tokens.css·components.css 를 따로 봄)가 있으면 의도 'hd-css-changed' {sheet}(모든 틀 그 스타일 다시 읽기 — view-ds-inspect)
   칩 글의 에이전트 이름(R27 F12): document 'hd-agent' {agent, name}(잡는 단계)로 모은 이름 — 모르면 "AI 수정 중"(날 id 는 title 에만, HD.busy.look).
   HD.viewBusy.mount(ctx) → {mark(screens:[{id, file}], via), render(), lift(id), adopt(), wrote(ids), live(on), changed(ids, seq), resync(), since()}
   ctx = {cardEl(id) → .card|null, watch(files) → Promise<{mtimes}>, reload(ids), getItem(k), setItem(k, v), key, toast(msg), warn(msg)?,
          files(since)? → Promise<{seq, changed:[id]}>, known()? → [id], modalScreen()? → id|null, reloadModal()?} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var EVERY = 2000, FILES_EVERY = 1000, SKIP_MS = 5000;
var has = function (o, k) { return Object.prototype.hasOwnProperty.call(o, k); };
var CSS = '.busy.bchip{position:absolute;inset:auto;top:calc(8px * var(--lz,1));right:calc(8px * var(--lz,1));z-index:4;display:inline-flex;flex-direction:row;align-items:center;justify-content:flex-start;' +
  'gap:calc(5px * var(--lz,1));box-sizing:border-box;height:calc(22px * var(--lz,1));max-width:calc(100% - 16px * var(--lz,1));padding:0 calc(2px * var(--lz,1)) 0 calc(8px * var(--lz,1));' +
  'border:1px solid rgba(0,0,0,.12);border-radius:999px;background:rgba(255,255,255,.95);color:#2b2b29;box-shadow:0 1px 4px rgba(0,0,0,.14);' +
  'font:600 calc(12px * var(--lz,1))/1 system-ui,sans-serif;white-space:nowrap;pointer-events:auto;cursor:default}' +
  '.busy.bchip[data-kind=queued]{background:rgba(241,241,238,.95);color:#6b6b66;font-weight:500}' +
  '.busy.bchip .busy-txt{min-width:0;overflow:hidden;text-overflow:ellipsis;padding:0;text-align:left}' +
  '.busy.bchip .bspin{flex:none;box-sizing:border-box;width:calc(11px * var(--lz,1));height:calc(11px * var(--lz,1));border:calc(1.5px * var(--lz,1)) solid #d6d6d1;' +
  'border-top-color:var(--ui-accent,#c2590a);border-radius:50%;animation:hd-bchip-spin .9s linear infinite}' +
  '.busy.bchip .bdot{flex:none;width:calc(6px * var(--lz,1));height:calc(6px * var(--lz,1));border-radius:50%;background:#a3a39d}' +
  '.busy.bchip [data-act=lift]{flex:none;display:grid;place-items:center;width:calc(16px * var(--lz,1));height:calc(16px * var(--lz,1));padding:0;margin:0;border:0;border-radius:50%;' +
  'background:transparent;color:inherit;font:inherit;font-size:calc(13px * var(--lz,1));line-height:1;cursor:pointer;pointer-events:auto}' +
  '.busy.bchip [data-act=lift]:hover,.busy.bchip [data-act=lift]:focus-visible{background:rgba(0,0,0,.09)}' +
  '@keyframes hd-bchip-spin{to{transform:rotate(360deg)}}@media (prefers-reduced-motion:reduce){.busy.bchip .bspin{animation:none}}' +
  '.phone[data-busy=working]{box-shadow:0 0 0 calc(2px * var(--lz,1)) var(--ui-accent,#c2590a),0 3px 14px rgba(0,0,0,.10)}' +
  '.busy.bchip[data-kind=done]{transition:opacity .3s ease-out}.busy.bchip[data-kind=done].bout{opacity:0}' +
  '.busy.bchip .bcmp{flex:none;height:calc(16px * var(--lz,1));padding:0 calc(6px * var(--lz,1));margin:0;border:1px solid rgba(0,0,0,.16);border-radius:999px;background:#fff;' +
  'color:inherit;font:inherit;font-size:calc(10px * var(--lz,1));line-height:1;cursor:pointer;pointer-events:auto}' +
  '.busy.bchip .bcmp:hover,.busy.bchip .bcmp:focus-visible{background:rgba(0,0,0,.07)}' +
  '.busy.bchip .bcmp[aria-pressed=true]{background:#2b2b29;border-color:#2b2b29;color:#fff}' +
  '.busy.bchip[data-kind=done] .bok{flex:none;color:var(--ui-accent,#c2590a);font-weight:700}' +
  '@media (prefers-reduced-motion:reduce){.busy.bchip[data-kind=done]{transition:none}}' +
  '#modal .mbar .busy.bchip{position:static;--lz:1;flex:none;max-width:45%}' +
  // R27 F01·F12: 칩은 화면에서 늘 같은 크기(--lz = 1/판 배율, view-label-scale) · 고른 카드·이어진 카드(focusing 그림자)에서도 강조 테두리가 보이게 · 메모 배지(오른쪽 위)와 겹치지 않게
  '#rows.focusing .card.focus .phone[data-busy=working]{box-shadow:0 0 0 calc(2px * var(--lz,1)) var(--ui-accent,#c2590a),0 0 0 calc(10px + 2px * var(--lz,1)) #1c1c1c,0 3px 14px rgba(0,0,0,.10)}' +
  '#rows.focusing .card.hl:not(.focus) .phone[data-busy=working]{box-shadow:0 0 0 calc(2px * var(--lz,1)) var(--ui-accent,#c2590a),0 0 0 calc(6px + 2px * var(--lz,1)) #8a8d86,0 3px 14px rgba(0,0,0,.10)}' +
  // R27(main 결정): 칩은 화면 밖 — 카드 제목 줄 오른쪽 끝(제목 왼쪽 · 메모 배지가 있으면 그 왼쪽), 화면에서 18px 고정. 판 칩 크기 규칙은 위 .busy.bchip 을 덮어쓴다
  '#rows .card > .busy.bchip{top:calc(100% - 46px);right:0;height:18px;gap:4px;max-width:calc(70% / var(--lz,1));padding:0 1px 0 6px;font:600 11px/1 system-ui,sans-serif;' +
  'transform-origin:100% 0;transform:translateY(calc(3px * var(--lz,1))) scale(var(--lz,1));box-shadow:0 1px 2px rgba(0,0,0,.10)}' +
  '#rows .card > .busy.bchip .bspin{width:10px;height:10px;border-width:1.5px}#rows .card > .busy.bchip .bdot{width:6px;height:6px}' +
  '#rows .card > .busy.bchip [data-act=lift]{width:14px;height:14px;font-size:12px}#rows .card > .busy.bchip .bcmp{height:14px;padding:0 5px;font-size:10px}' +
  // 펼친 긴 화면(.card.xp — 제목 줄은 화면 밑에 가려 숨김): 칩·배지는 카드 위 오른쪽 줄로 올려 계속 보인다
  '#rows .card.xp > .busy.bchip,#rows .card.xp > .nbadge{visibility:visible;top:0;transform:translateY(calc(-22px * var(--lz,1))) scale(var(--lz,1))}' +
  '#rows .card:has(> .nbadge) > .busy.bchip{right:calc(24px * var(--lz,1));max-width:calc(70% / var(--lz,1) - 24px)}' +
  '.card .cerr{margin-top:calc(8px * var(--ts,1));font:500 calc(12px * var(--ts,1))/1.35 system-ui,sans-serif;color:var(--ui-danger,#b42318);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%}';

function style() {
  if (typeof document === 'undefined' || document.getElementById('hd-busy-css')) return;
  var css = document.createElement('style'); css.id = 'hd-busy-css'; css.textContent = CSS;
  document.head.appendChild(css);
}

function mount(ctx) {
  var B = HD.busy, warn = ctx.warn || function (m) { console.warn(m); };
  var st = B.load(ctx.getItem, ctx.key, warn), els = {}, timer = 0, skip = {}, mel = null;
  var names = {};                                     // R27 F12 — 판이 아는 에이전트 이름 {id: 이름}('hd-agent' 의도에서 모음, 저장 안 함)
  var landedRec = {}, dones = {}, swapErr = {};          // 48a — 파일이 바뀌어 걷힌 카드 · 지금 보이는 "방금 반영됨" 칩 · 교체 실패 줄을 단 카드

  function dispatch(a) {
    var n = B.reduce(st, a);
    if (n !== st) { st = n; B.save(st, ctx.setItem, ctx.key); }
    return st;
  }
  function ids() { return Object.keys(st.items); }

  function chip(id, it) {                             // 칩 하나 — 점/도는 표시 + 짧은 글 + [×]
    var lk = B.look(it, names), el = document.createElement('div');
    el.className = 'busy bchip'; el.setAttribute('data-via', it.via); el.setAttribute('data-kind', lk.kind); el.setAttribute('data-id', id);
    el.setAttribute('data-label', B.label(it, names)); el.setAttribute('role', 'status'); el.title = lk.title;
    var dot = document.createElement('span'); dot.className = lk.kind === 'working' ? 'bspin' : 'bdot'; dot.setAttribute('aria-hidden', 'true'); el.appendChild(dot);
    var tx = document.createElement('span'); tx.className = 'busy-txt'; tx.textContent = lk.text; el.appendChild(tx);
    var b = document.createElement('button'); b.type = 'button'; b.setAttribute('data-act', 'lift'); b.setAttribute('aria-label', '걷기'); b.title = '걷기(지우기)'; b.textContent = '×';
    b.addEventListener('click', function (e) { e.stopPropagation(); e.preventDefault(); lift(id); });
    el.appendChild(b);
    el.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 칩은 자기 누르기만(카드 끌기·고르기로 새지 않게)
    return el;
  }
  function same(el, host, it, id) {
    return !!el && el.parentNode === host && el.getAttribute('data-id') === String(id) && el.getAttribute('data-via') === it.via && el.getAttribute('data-label') === B.label(it, names);
  }
  function phoneOf(el) { var h = el && el.parentNode; return h && h.querySelector ? (h.querySelector(':scope > .phone') || h) : null; }
  function unmark(el) { var h = phoneOf(el); if (h && h.removeAttribute) h.removeAttribute('data-busy'); }

  function draw(id, it) {                             // 카드 하나에 칩(이미 맞게 있으면 그대로) — 화면은 가리지 않는다
    var card = ctx.cardEl(id), host = card, ph = card && (card.querySelector(':scope > .phone') || card), el = els[id];   // 칩 = 카드 제목 줄 오른쪽 끝(R27, 화면 밖) · 테두리 = 화면(.phone)
    if (!host) { if (el) { unmark(el); el.remove(); delete els[id]; } return; }
    if (!same(el, host, it, id)) {
      if (el) { unmark(el); el.remove(); }
      undone(id);
      el = chip(id, it); host.appendChild(el); els[id] = el;
    }
    if (B.look(it, names).kind === 'working') ph.setAttribute('data-busy', 'working'); else ph.removeAttribute('data-busy');
  }
  function drawModal() {                              // 크게 보기 제목 막대에 같은 칩(그 화면이 바쁠 때만, 덮개 없음)
    if (typeof document === 'undefined') return;
    var bar = document.querySelector('#modal .mbar'), box = document.getElementById('modal');
    var id = ctx.modalScreen ? ctx.modalScreen() : null;
    var it = id != null && box && !box.hidden && has(st.items, id) ? st.items[id] : null;
    if (!bar || !it) { if (mel) { mel.remove(); mel = null; } return; }
    if (same(mel, bar, it, id)) return;
    if (mel) mel.remove();
    mel = chip(id, it);
    var t = bar.querySelector('#mtitle');
    bar.insertBefore(mel, t ? t.nextSibling : bar.firstChild);
  }
  function render() {                                 // 지금 상태대로 칩 그리기·지우기(여러 번 불러도 같음)
    var k;
    for (k in els) if (!has(st.items, k)) { unmark(els[k]); els[k].remove(); delete els[k]; }
    for (k in st.items) draw(k, st.items[k]);
    drawModal();
  }
  // 받는 곳 칩이 이름을 알게 되면(view-agents 고르기 · view-presence 새로고침 뒤) 'hd-agent' {agent, name} — 칩 위에서 나고 올라오지 않으므로 잡는 단계에서 듣는다.
  // 그 에이전트의 덮개 칩 글이 날 id 대신 이름이 된다(HD.busy.label). 이름이 바뀔 때만 다시 그린다
  document.addEventListener('hd-agent', function (e) {
    var d = e.detail || {};
    if (typeof d.agent !== 'string' || !d.agent || typeof d.name !== 'string' || !d.name.trim() || names[d.agent] === d.name) return;
    names[d.agent] = d.name; render();
  }, true);
  function compareTo(id, on) { document.dispatchEvent(new CustomEvent('hd-swap-compare', {detail: {id: id, on: on}})); }   // view-swap 이 옛 화면을 겹친다·걷는다
  function undone(id) { var d = dones[id]; if (d) { clearTimeout(d.t); d.el.remove(); delete dones[id]; if (d.on) compareTo(id, false); } }
  function showDone(id, canCompare) {                 // "방금 반영됨 ✓" — DONE_MS(전/후 보기가 있으면 COMPARE_MS) 뒤 사라짐(덮개가 다시 씌면 그 칩이 대신)
    var card = ctx.cardEl(id), host = card;            // 같은 제목 줄 자리(R27)
    if (!host || has(st.items, id)) return;
    undone(id);
    var lk = B.lookDone(), el = document.createElement('div');
    el.className = 'busy bchip'; el.setAttribute('data-kind', 'done'); el.setAttribute('data-id', id); el.setAttribute('role', 'status'); el.title = lk.title;
    var ok = document.createElement('span'); ok.className = 'busy-txt'; ok.textContent = lk.text; el.appendChild(ok);
    el.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
    el.addEventListener('click', function (e) { e.stopPropagation(); });   // 칩 누르기가 카드 고르기·크게 보기로 새지 않게
    host.appendChild(el);
    var d = dones[id] = {el: el, on: false, t: 0};
    function expire() {
      clearTimeout(d.t);
      d.t = setTimeout(function () {
        el.classList.add('bout');
        d.t = setTimeout(function () { if (dones[id] === d) { el.remove(); delete dones[id]; } }, 320);
      }, B.doneMs(!!canCompare));
    }
    if (canCompare) {                                 // [전/후] — 누르면 바뀌기 전 화면을 겹쳐 보고, 다시 누르면 새 화면(보는 동안은 칩이 사라지지 않는다)
      var bt = document.createElement('button');
      bt.type = 'button'; bt.className = 'bcmp'; bt.setAttribute('data-act', 'compare');
      var look = function () { var c = B.lookCompare(d.on); bt.textContent = c.btn; bt.setAttribute('aria-pressed', String(c.pressed)); ok.textContent = c.text; el.title = c.title; bt.title = c.title; };
      bt.addEventListener('click', function (e) {
        e.stopPropagation(); e.preventDefault();
        d.on = !d.on; look(); compareTo(id, d.on);
        if (d.on) { clearTimeout(d.t); el.classList.remove('bout'); } else expire();
      });
      look(); el.appendChild(bt);
    }
    expire();
  }
  function onSwap(e) {                                // view-swap 의 의도 — 교체가 끝남·실패
    var d = e.detail || {}, id = d.id;
    if (typeof id !== 'string' || !id) return;
    if (d.phase === 'failed') { swapErr[id] = 1; errLine(id, d.why || '새 버전을 싣지 못했어요'); return; }
    if (d.phase === 'start') { undone(id); return; }   // 새 교체가 시작됨 — 지난 반영 칩·전/후 보기는 걷는다
    if (d.phase !== 'done') return;
    if (has(swapErr, id)) { delete swapErr[id]; errLine(id, null); }
    var r = B.landed(landedRec, {type: 'swapped', id: id, at: Date.now()});
    landedRec = r.rec;
    if (r.show) showDone(id, !!d.before);
  }
  function wrote(list) { var until = Date.now() + SKIP_MS; (list || []).forEach(function (id) { skip[id] = until; }); }

  function poll() {
    clearTimeout(timer); timer = 0;
    if (!ids().length) return;
    var before = ids();
    Promise.resolve().then(function () { return ctx.watch(B.files(st)); }).then(function (r) {
      var m = (r && r.mtimes) || {};
      dispatch({type: 'baseline', mtimes: m});        // 기준을 못 잡았던 것은 여기서 잡는다
      dispatch({type: 'seen', mtimes: m});
      var gone = before.filter(function (id) { return !has(st.items, id); });
      if (gone.length) { landedRec = B.landed(landedRec, {type: 'lifted', ids: gone, at: Date.now()}).rec; render(); wrote(gone); ctx.reload(gone); }
    }, function () { /* 도우미가 잠깐 안 되면 다음 차례에 다시 */ }).then(schedule, schedule);
  }
  function schedule() { if (!timer && ids().length) timer = setTimeout(poll, EVERY); }

  function mark(screens, via) {
    var list = (screens || []).filter(function (s) { return s && s.id && s.file; });
    if (!list.length) return;
    dispatch({type: 'mark', screens: list, via: via, now: Date.now()});
    render();
    var fs = list.map(function (s) { return s.file; });
    Promise.resolve().then(function () { return ctx.watch(fs); }).then(function (r) {
      dispatch({type: 'baseline', mtimes: (r && r.mtimes) || {}});
    }, function () { /* 기준은 다음 차례 poll 에서 */ }).then(schedule, schedule);
  }
  function lift(id) {
    dispatch({type: 'lift', id: id});
    render();
  }
  function adopt() {                                  // 상태 파일 쪽이 바뀜 — 저장하지 않고 읽기만(쓴 곳이 이미 파일에 있다)
    st = B.load(ctx.getItem, ctx.key, warn);
    render();
    if (ids().some(function (id) { return st.items[id].mtime == null; })) poll(); else schedule();
  }

  // 앱 카드(#272) — 카드 iframe 의 hd-here 로 걷기(mtime 이 없는 카드)
  var loaded = {};                                    // 이 판에서 로드를 본 카드 id(첫 로드 = 판 새로 고침·처음 보임)
  function frameOf(id) { var c = ctx.cardEl(id), f = c && c.querySelector('iframe'); return f && f.contentWindow; }
  var errSeen = {};                                   // 카드마다 보인 실패 글(HD.busy.hereError) — 같은 글은 한 번
  function errLine(id, text) {                        // 카드 아래 작은 한 줄(.cerr) — 화면(.phone) 바로 밑, 제목 위
    var c = ctx.cardEl(id), el = c && c.querySelector('.cerr');
    if (!c) return;
    if (text == null) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('div'); el.className = 'cerr'; el.setAttribute('role', 'alert');
      var ph = c.querySelector('.phone'); if (ph && ph.nextSibling) c.insertBefore(el, ph.nextSibling); else c.appendChild(el);
    }
    el.textContent = '⚠ ' + text; el.title = '앱 화면을 싣지 못했어요 — ' + text;
  }
  function onHere(e) {
    var d = e.data;
    if (!d || d.type !== 'hd-here' || typeof d.screen !== 'string' || !d.screen) return;
    var id = d.screen, w = frameOf(id);
    if (!w || w !== e.source) return;
    var r = B.hereError(errSeen, d);                  // 감싸개의 실패 알림(#280) = 카드에 한 줄(토스트 아님) · 다시 잘 실리면 걷기
    errSeen = r.seen;
    if (r.show != null) { warn('[hd] 앱 카드 ' + id + ': ' + r.show); errLine(id, r.show); }
    else if (r.clear) errLine(id, null);
    else if (d.error != null && has(errSeen, id) && !(ctx.cardEl(id) || document).querySelector('.cerr')) errLine(id, errSeen[id]);   // 카드를 다시 그렸으면 다시 붙임(알림은 그대로 한 번)
    if (d.error != null) return;                      // 실패 알림으로는 걷지 않는다(로드는 palette.js 가 따로 알린다)
    var kind = d.hmr ? 'hmr' : 'load', first = kind === 'load' && !has(loaded, id);
    if (kind === 'load') loaded[id] = 1;
    if (!has(st.items, id)) return;
    var before = st;
    dispatch({type: 'here', id: id, kind: kind, at: Date.now(), first: first});
    if (st !== before) { render(); showDone(id); }      // 앱 카드 = 이미 새 화면(다시 싣지 않음)
  }

  // 도우미가 지켜본 화면 파일(GET /api/files) — 바뀐 카드만 다시
  var since = null, ftimer = 0, fwarned = false, liveOn = false;
  function changed(list) {                            // 바뀐 화면 파일(폴링 답 · 이벤트 screen.written by ai) → 고른 카드만 다시 · 칩 카드는 걷는 길을 바로
    if (!Array.isArray(list) || !list.length) return;
    ['tokens', 'components'].forEach(function (s) { if (list.indexOf('@' + s) >= 0) document.dispatchEvent(new CustomEvent('hd-css-changed', {detail: {sheet: s}})); });   // tokens.css·components.css 가 바뀜(R55) — 다시 읽기는 view-ds-inspect
    var now = Date.now(), t = B.refresh(list, {known: ctx.known ? ctx.known() : [], busy: st, skip: skip, now: now,
                                              modal: ctx.modalScreen ? ctx.modalScreen() : null});
    if (t.cards.length) { wrote(t.cards); ctx.reload(t.cards); }
    if (t.modal && ctx.reloadModal) ctx.reloadModal();
    if (list.some(function (id) { return has(st.items, id); })) poll();
  }
  function fpoll(once) {
    ftimer = 0;
    if (!once && typeof document !== 'undefined' && document.hidden) { fnext(); return; }
    Promise.resolve().then(function () { return ctx.files(since == null ? -1 : since); }).then(function (r) {
      fwarned = false;
      if (!r || typeof r.seq !== 'number') { warn('[hd] /api/files 답이 깨졌어요'); return; }
      var first = since == null || r.seq < since;     // 처음 · 도우미가 다시 떴음 = 기준만 잡기
      since = r.seq;
      if (!first) changed(r.changed);
    }, function (e) {
      if (!fwarned) { fwarned = true; warn('[hd] 바뀐 화면 파일을 받지 못했어요(다시 시도): ' + (e && e.message || e)); }
    }).then(once ? null : fnext, once ? null : fnext);
  }
  function fnext() { clearTimeout(ftimer); ftimer = 0; if (!liveOn) ftimer = setTimeout(fpoll, FILES_EVERY); }   // 실시간(47-4b)이면 주기 읽기 없음

  style(); render(); schedule();
  if (typeof addEventListener === 'function') addEventListener('message', onHere);
  if (typeof document !== 'undefined') document.addEventListener('hd-swap', onSwap);
  if (ctx.files) fpoll();
  if (typeof MutationObserver !== 'undefined' && typeof document !== 'undefined') {   // 크게 보기를 열고·닫고·화면을 바꿀 때 칩도 따라
    var box = document.getElementById('modal'), title = document.getElementById('mtitle'), ob = new MutationObserver(drawModal);
    if (box) ob.observe(box, {attributes: true, attributeFilter: ['hidden']});
    if (title) ob.observe(title, {childList: true, characterData: true, subtree: true});
  }
  return {mark: mark, render: render, lift: lift, adopt: adopt, wrote: wrote,
          live: function (on) { liveOn = !!on; if (!ctx.files) return; if (liveOn) { clearTimeout(ftimer); ftimer = 0; } else if (!ftimer) fnext(); },
          changed: function (list, seq) { if (typeof seq === 'number' && (since == null || seq > since)) since = seq; changed(list); },
          resync: function () { if (ctx.files) fpoll(true); },
          since: function () { return since; }};
}

HD.viewBusy = {mount: mount};
})();
