/* View — 요소 막대(블록 편집, task 49a·49b·49c): 고른 요소 옆 [⠿][상위][글자][속성][지우기][복제][바꾸기][아래에 넣기][메모] · 속성 칸 · 부품 고르기 · 단축키(Alt+↑/↓ 옮기기 포함) · 끌어서 순서 바꾸기 · 쓴 뒤 같은 요소 다시 고르기.
   규칙(켜짐·앱 = AI 요청·자리·너비/⋯·상위 고르기·속성 허용 목록·부품 요청 글)은 HD.blocks(Model). 자리를 고를 때 같은 출처 화면의 둘레 글 상자를 읽어 넘긴다(못 읽으면 없이).
   상태 = 지금 고른 요소 하나 {screen, h, app, where:'board'|'modal', anchor() → 화면 좌표 사각형|null, frame() → 그 화면 iframe|null, view?() → 보이는 칸, avoid?() → 비킬 사각형}
     + 따라갈 요소 하나 follow {screen, path, v, where}(쓴 뒤 다시 실린 화면에서 찾을 것, 15초) — 막대가 그 주인, 저장하지 않음.
   편집 자체는 셸이 한다 — 단추는 onAct(fn) 로 받은 fn(act, sel) 하나로만 나간다(sel.attrs = 바꿀 속성 {이름: 값} · sel.part = 고른 부품 {key, title, ok}|null).
   상위·따라가기로 새 요소를 고르면 onPick(fn) 의 fn({screen, h, where}) — 셸이 그 자리 테두리·막대를 다시 그린다(View 끼리 부르지 않음).
   Figma 고르기 키(51-2, 막대가 떠 있고 입력 칸·메뉴 밖): Enter = 글자면 [글자](그 자리 고치기), 아니면 첫 자식(hd-down) · Shift+Enter = [상위] · Tab/Shift+Tab = 다음·앞 형제(hd-sib, 끝에서 돈다).
   화면 메시지(palette.js): hd-up → hd-upchain · hd-down·hd-sib → hd-hop · 다시 실린 화면의 hd-here → hd-find → hd-found. 부품 목록 = ctx.api GET /api/parts(도우미 없으면 AI 요청).
   끌어서 순서 바꾸기(49c): 손잡이 [⠿] 를 누른 채 끌기 · 크게 보기에서 고른 요소를 눌러 끌기(palette.js hd-grab) → 화면에 hd-sibs(형제 상자) → 끼울 선 #eldrop(HD.reorder.slot·line)
     → 놓으면 fn('reorder', sel + {dirs, from, to, h: sel.h + {drop: {from, slot, copy}}}) — 같은 부모 안만. Esc = 끌기 취소
     Alt(51-5): 놓을 때 Alt 를 누르고 있으면 복제해 놓기(원본은 제자리) — 끄는 중 Alt = 커서 copy + 끼울 선 옆 '+' 배지 #eldrop-copy. 도우미 없으면 거절(토스트).
       셸은 아직 OP.moves(…, h, dirs) 만 넘기므로 놓기 계획은 h.drop 에 싣는다(dirs 는 셸의 빈 목록 거르기를 지나게 — 51-3 이 셸을 h.drop 으로 바꿀 때까지)
   HD.feature('blocks', {needs: ['$', 'toast', 'esc', 'api', 'cardEl']}) → {show(sel), hide(where?), place(), sel(), onAct(fn), onPick(fn), wrote(res, list)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '#elbar{position:fixed;z-index:35;display:flex;flex-wrap:nowrap;gap:1px;padding:2px;background:#1c1c1c;border-radius:7px;box-shadow:0 3px 10px rgba(0,0,0,.22);font:600 12px/16px system-ui,sans-serif;opacity:.82;transition:opacity .12s}' +
  '#elbar:hover,#elbar:focus-within,#elbar.open{opacity:1}' +
  '#elbar[hidden],#elpop[hidden],#elbar [hidden]{display:none}' +
  '#elbar button{border:0;background:none;color:#fff;font:inherit;padding:2px 7px;border-radius:5px;cursor:pointer;white-space:nowrap}' +
  '#elbar button:hover{background:#3a3a3a}' +
  '#elbar button[aria-disabled="true"]{opacity:.35;cursor:not-allowed}' +
  '#elbar button.ask{color:#f5c26b}' +
  '#elbar .eb-sep{width:1px;margin:3px 2px;background:#444}' +
  '#elbar button.eb-grip{cursor:grab;padding:2px 5px;touch-action:none}' +
  '#elbar.dragging button.eb-grip,body.hd-dragging-el,body.hd-dragging-el *{cursor:grabbing!important}' +
  '#eldrop{position:fixed;z-index:37;pointer-events:none;background:#2563eb;border-radius:2px;box-shadow:0 0 0 2px rgba(255,255,255,.9)}' +
  '#eldrop[hidden],#eldrop-copy[hidden]{display:none}' +
  '#eldrop-copy{position:fixed;z-index:38;pointer-events:none;width:18px;height:18px;border-radius:50%;background:#2563eb;color:#fff;font:700 15px/18px system-ui,sans-serif;text-align:center;box-shadow:0 0 0 2px #fff,0 2px 6px rgba(0,0,0,.3)}' +
  'body.hd-dragging-el.hd-drag-copy,body.hd-dragging-el.hd-drag-copy *{cursor:copy!important}' +
  '#elpop .ep-acts{display:flex;flex-direction:column;gap:2px}' +
  '#elpop .ep-act{border:0;background:none;text-align:left;color:#1c1c1c;border-radius:6px;padding:6px 8px;font:600 12.5px system-ui,sans-serif;cursor:pointer}' +
  '#elpop .ep-act:hover{background:#f0f0f0}' +
  '#elpop .ep-act[aria-disabled="true"]{opacity:.4;cursor:not-allowed}' +
  '#elpop .ep-act.ask{color:#8a5a00}' +
  '#elpop{position:fixed;z-index:36;min-width:240px;max-width:340px;max-height:60vh;overflow:auto;padding:10px;background:#fff;color:#1c1c1c;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.28);font:13px system-ui,sans-serif}' +
  '#elpop .ep-h{font-weight:700;margin:0 0 8px}' +
  '#elpop label{display:block;margin:0 0 8px;color:#555;font-size:12px}' +
  '#elpop input{display:block;width:100%;box-sizing:border-box;margin-top:3px;padding:6px 8px;border:1px solid #ccc;border-radius:6px;font:13px system-ui,sans-serif;color:#1c1c1c}' +
  '#elpop .ep-row{display:flex;gap:6px;justify-content:flex-end}' +
  '#elpop .ep-row button,#elpop .ep-part{border:1px solid #ddd;background:#fafafa;color:#1c1c1c;border-radius:7px;padding:6px 10px;font:600 12.5px system-ui,sans-serif;cursor:pointer}' +
  '#elpop .ep-row button.go{background:#1c1c1c;color:#fff;border-color:#1c1c1c}' +
  '#elpop .ep-list{display:flex;flex-wrap:wrap;gap:6px}' +
  '#elpop .ep-part.ask{border-style:dashed;color:#8a5a00}' +
  '#elpop .ep-note{margin:8px 0 0;color:#777;font-size:12px}' +
  'html[data-hd-tab="reader"] #elbar button{opacity:.35;cursor:not-allowed}';
var RO = '이 탭은 읽기만 해요 — 위쪽 "여기서 편집하기"를 누르면 여기서 편집할 수 있어요';
var FOLLOW_MS = 15000;

function mount(ctx) {
  var B = HD.blocks, cur = null, act = null, picked = null, follow = null, upWait = null, hopWait = null, navQ = [], seq = 0, done = null;   // navQ = 묻는 중에 더 누른 고르기 키(빠르게 Tab 여러 번 — 답이 오면 차례로)   // done = 막 단추를 누른 요소(셸이 막대를 걷은 뒤에도 쓴 결과를 따라가게)
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var bar = document.createElement('div');
  bar.id = 'elbar'; bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', '고른 요소'); bar.hidden = true;
  var pop = document.createElement('div');
  pop.id = 'elpop'; pop.setAttribute('role', 'dialog'); pop.hidden = true;
  var dropLine = document.createElement('div');
  dropLine.id = 'eldrop'; dropLine.hidden = true; dropLine.setAttribute('aria-hidden', 'true');
  var copyBadge = document.createElement('div');
  copyBadge.id = 'eldrop-copy'; copyBadge.hidden = true; copyBadge.textContent = '+'; copyBadge.setAttribute('aria-hidden', 'true');
  document.body.appendChild(bar); document.body.appendChild(pop); document.body.appendChild(dropLine); document.body.appendChild(copyBadge);

  function reader() { return document.documentElement.dataset.hdTab === 'reader'; }
  function items() { return B.bar(cur.h, {app: cur.app}); }
  function paint() {
    var g = B.grip(cur.h, {app: cur.app});
    bar.innerHTML = '<button type="button" class="eb-grip" data-grip="1"' + (g.on ? '' : ' aria-disabled="true"') + ' title="' + ctx.esc(g.title) + '" aria-label="' + ctx.esc(g.title) + '">⠿</button>' +
      B.shown(items()).map(function (it) {
      return (it.act === 'memo' || it.act === 'swap' ? '<span class="eb-sep" data-for="' + it.act + '"></span>' : '') +
        '<button type="button" data-act="' + it.act + '"' + (it.on ? '' : ' aria-disabled="true"') + (it.ask ? ' class="ask" data-ask="1"' : '') +
        ' title="' + ctx.esc(it.title) + '" aria-label="' + ctx.esc(it.title) + '">' + ctx.esc(it.label) + '</button>';
    }).join('') + '<button type="button" class="eb-more" data-more="1" title="단추 더 보기" aria-label="단추 더 보기" aria-haspopup="true" hidden>⋯</button>';
    bar.dataset.screen = cur.screen; bar.dataset.path = cur.h.path; bar.dataset.where = cur.where; bar.dataset.app = cur.app ? '1' : '';
  }
  function viewRect() {
    var v = cur && cur.view && cur.view();
    return v && v.w > 0 && v.h > 0 ? v : {x: 0, y: 0, w: innerWidth, h: innerHeight};
  }
  // 막대가 요소 칸(blocks.barLimit)보다 넓으면 뒤 단추를 "⋯" 로 — 숨긴 단추는 ⋯ 를 누르면 목록(단축키는 그대로)
  function fitBar(a, v) {
    var bs = Array.prototype.slice.call(bar.querySelectorAll('button[data-act]')), more = bar.querySelector('.eb-more');
    var sepOf = function (b) { return bar.querySelector('.eb-sep[data-for="' + b.dataset.act + '"]'); };
    bs.forEach(function (b) { b.hidden = false; var sp = sepOf(b); if (sp) sp.hidden = false; });
    if (more) more.hidden = false;
    var cs = getComputedStyle(bar), pad = (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0), gap = parseFloat(cs.columnGap) || 0;
    var ws = bs.map(function (b) { var sp = sepOf(b); return b.offsetWidth + gap + (sp ? sp.offsetWidth + (parseFloat(getComputedStyle(sp).marginLeft) || 0) * 2 + gap : 0); });
    var gr = bar.querySelector('.eb-grip'), gw = gr ? gr.offsetWidth + gap : 0;
    var n = B.fit(ws, B.barLimit(a, v) - pad - gw, more ? more.offsetWidth + gap : 0);
    bs.forEach(function (b, i) { b.hidden = i >= n; var sp = sepOf(b); if (sp) sp.hidden = i >= n; });
    if (more) more.hidden = n >= bs.length;
    bar.dataset.more = bs.slice(n).map(function (b) { return b.dataset.act; }).join(' ');
  }
  // 둘레 글 상자(화면 좌표) — 같은 출처 화면만 읽는다(다른 출처·file:// 는 못 읽음 → null, 막대는 예전 자리 규칙). 글 마디·그림·입력 칸, 1초 동안 문서 좌표를 기억
  var boxes = null;
  function others(v) {
    var f = cur && cur.frame && cur.frame(), doc = null;
    if (!f) return null;
    try { doc = f.contentDocument; } catch (e) { return null; }   // 다른 출처 — 읽을 수 없으면 글 상자 없이
    if (!doc || !doc.body) return null;
    var w = doc.defaultView, sx = w ? w.scrollX : 0, sy = w ? w.scrollY : 0;
    if (!boxes || boxes.doc !== doc || boxes.sx !== sx || boxes.sy !== sy || Date.now() - boxes.at > 1000) {
      var list = [], rg = doc.createRange(), tw = doc.createTreeWalker(doc.body, 4), n;
      var push = function (r) { if (r.width > 0 && r.height > 0) list.push({x: r.left, y: r.top, w: r.width, h: r.height}); };
      while ((n = tw.nextNode()) && list.length < 600) {
        var pe = n.parentElement;
        if (!/\S/.test(n.nodeValue) || !pe || /^(SCRIPT|STYLE|TEMPLATE|NOSCRIPT)$/.test(pe.tagName)) continue;
        rg.selectNodeContents(n); push(rg.getBoundingClientRect());
      }
      Array.prototype.slice.call(doc.querySelectorAll('img,svg,input,textarea,select,video,canvas'), 0, 200).forEach(function (e) { push(e.getBoundingClientRect()); });
      boxes = {doc: doc, sx: sx, sy: sy, at: Date.now(), list: list};
    }
    var fr = f.getBoundingClientRect(), sc = f.offsetWidth ? fr.width / f.offsetWidth : 1, ox = fr.left + f.clientLeft * sc, oy = fr.top + f.clientTop * sc;
    return boxes.list.map(function (r) { return {x: ox + r.x * sc, y: oy + r.y * sc, w: r.w * sc, h: r.h * sc}; }).filter(function (r) {
      return r.x < v.x + v.w && r.x + r.w > v.x && r.y < v.y + v.h && r.y + r.h > v.y;
    });
  }
  function place() {
    if (!cur) return;
    var a = cur.anchor && cur.anchor();
    if (!a || !a.w && !a.h) { bar.hidden = true; pop.hidden = true; return; }
    bar.hidden = false;
    var v = viewRect(); fitBar(a, v);
    var sb = ctx.$('#selbar'), r = sb && !sb.hidden ? sb.getBoundingClientRect() : null;
    var tl = ctx.$('#tools'), tr = tl && !tl.hidden && tl.offsetWidth ? tl.getBoundingClientRect() : null;
    var avoid = [cur.avoid ? cur.avoid() : r ? {x: r.left, y: r.top, w: r.width, h: r.height} : null,   // 비킬 것(절대): 크게 보기 = 창 제목 막대 · 판 = 카드 선택 막대 · 왼쪽 도구 막대 — 둘레 글은 무르게
                 tr ? {x: tr.left, y: tr.top, w: tr.width, h: tr.height} : null];
    var os = null; try { os = others(v); } catch (e) { console.warn('[hd] 요소 막대: 둘레 글 상자를 읽지 못했어요 — ' + (e && e.message || e)); }
    var p = B.place(a, {w: bar.offsetWidth, h: bar.offsetHeight}, v, avoid, os);
    bar.style.left = p.x + 'px'; bar.style.top = p.y + 'px';
    bar.dataset.side = p.over ? 'over' : p.side || (p.below ? 'below' : 'above');
    if (!pop.hidden) placePop();
  }
  function placePop() {                               // 막대 바로 아래(막대가 요소 아래면 막대 위가 아니라 그 아래 그대로) — 창 안
    var r = bar.getBoundingClientRect(), x = Math.max(8, Math.min(innerWidth - pop.offsetWidth - 8, r.left));
    var y = r.bottom + 6; if (y + pop.offsetHeight > innerHeight - 8) y = Math.max(8, r.top - pop.offsetHeight - 6);
    pop.style.left = x + 'px'; pop.style.top = y + 'px';
  }
  function closePop() { pop.hidden = true; pop.innerHTML = ''; pop.dataset.kind = ''; bar.classList.remove('open'); }
  function openMore() {                               // ⋯ = 막대에 들어가지 못한 단추들(같은 켜짐·까닭)
    var hid = (bar.dataset.more || '').split(' ').filter(Boolean), its = items().filter(function (x) { return hid.indexOf(x.act) >= 0; });
    if (!its.length) return;
    pop.dataset.kind = 'more';
    pop.innerHTML = '<div class="ep-acts">' + its.map(function (it) {
      return '<button type="button" class="ep-act' + (it.ask ? ' ask' : '') + '" data-act="' + it.act + '"' + (it.on ? '' : ' aria-disabled="true"') + ' title="' + ctx.esc(it.title) + '">' + ctx.esc(it.label) + '</button>';
    }).join('') + '</div>';
    pop.hidden = false; bar.classList.add('open'); placePop();
  }
  function show(sel) {
    if (!sel || !sel.h || !sel.h.path) { hide(); return; }
    closePop(); cur = sel; paint(); bar.hidden = false; place();
  }
  function hide(where) {
    if (where && cur && cur.where !== where) return;
    cur = null; bar.hidden = true; closePop(); upWait = null; hopWait = null; navQ = []; dragStop();
  }
  function run(a, extra) {
    var s = Object.assign({}, cur, extra || {});
    done = {screen: cur.screen, h: cur.h, where: cur.where, at: Date.now()};
    try { act(a, s); } catch (e) { console.error('[hd] 요소 막대 ' + a + ': ' + (e && e.message || e)); ctx.toast('요소 편집을 하지 못했어요 — ' + (e && e.message || e)); }
  }
  function fire(a) {
    if (!cur || !act) return;
    var it = items().filter(function (x) { return x.act === a; })[0];
    if (!it) return;
    if (reader() && a !== 'parent') { ctx.toast(RO); return; }
    if (!it.on) { ctx.toast(it.title); return; }   // 꺼진 단추 = 까닭을 알린다
    if (a === 'parent') { goUp(); return; }
    if (a === 'attr' && !it.ask) { openAttr(); return; }
    if (a === 'swap' || a === 'insert') { openParts(a, it.ask); return; }
    closePop(); run(a, {ask: it.ask});
  }

  // ---- 상위 고르기: 화면에 조상들을 묻고(hd-up) 상자가 다른 첫 조상(blocks.parentPick)
  function goUp() {
    var f = cur.frame && cur.frame(), w = f && f.contentWindow;
    if (!w) { ctx.toast('이 화면에 물을 수 없어요 — 다시 골라 주세요'); return; }
    upWait = {tag: 'up:' + (++seq), win: w, screen: cur.screen, where: cur.where, h: cur.h};
    try { w.postMessage({type: 'hd-up', path: cur.h.path, tag: upWait.tag}, '*'); } catch (e) { upWait = null; ctx.toast('이 화면에 물을 수 없어요'); }
  }
  // ---- Figma 고르기 키(51-2): 첫 자식(hd-down) · 형제(hd-sib) — 답 hd-hop 을 상위 고르기와 같은 길(pick)로
  function hop(type, dir) {
    var f = cur.frame && cur.frame(), w = f && f.contentWindow;
    if (!w) { ctx.toast('이 화면에 물을 수 없어요 — 다시 골라 주세요'); return; }
    hopWait = {tag: 'hop:' + (++seq), win: w, screen: cur.screen, where: cur.where, type: type};
    try { w.postMessage({type: type, path: cur.h.path, dir: dir, tag: hopWait.tag}, '*'); } catch (e) { hopWait = null; ctx.toast('이 화면에 물을 수 없어요'); }
  }
  function nav(a) {
    if (a === 'next' || a === 'prev') { hop('hd-sib', a === 'next' ? 1 : -1); return; }
    if (B.enterOf(cur.h) === 'text') fire('text'); else hop('hd-down');
  }
  function step(a) { if (NAV[a]) nav(a); else fire(a); }
  function pickThen(sel) { var q = navQ; pick(sel); navQ = q; var a = navQ.shift(); if (a && cur) step(a); }   // 셸이 다시 그리며 막대를 걷었다 붙인다(hide 가 줄을 비움) — 줄은 이어 간다
  function pick(sel) { if (picked) picked(sel); else show(Object.assign({}, cur || {}, sel)); }

  // ---- 속성 칸(허용 목록만)
  function openAttr() {
    var fs = B.attrFields(cur.h);
    if (!fs.length) { ctx.toast('이 요소에는 고칠 속성이 없어요'); return; }
    pop.dataset.kind = 'attr';
    pop.innerHTML = '<p class="ep-h">속성</p>' + fs.map(function (f) {
      return '<label>' + ctx.esc(f.label) + ' · ' + ctx.esc(f.name) + '<input data-name="' + f.name + '" value="' + ctx.esc(f.value) + '" spellcheck="false"></label>';
    }).join('') + '<div class="ep-row"><button type="button" data-ep="cancel">취소</button><button type="button" class="go" data-ep="apply">적용</button></div>';
    pop.hidden = false; placePop();
    var first = pop.querySelector('input'); if (first) { first.focus(); first.select(); }
  }
  function applyAttr() {
    var was = {}; B.attrFields(cur.h).forEach(function (f) { was[f.name] = f.value; });
    var ch = {}, n = 0;
    Array.prototype.forEach.call(pop.querySelectorAll('input[data-name]'), function (i) {
      var v = i.value.replace(/[\r\n]+/g, ' ');
      if (v !== was[i.dataset.name]) { ch[i.dataset.name] = v; n++; }
    });
    closePop();
    if (!n) { ctx.toast('바뀐 속성이 없어요'); return; }
    run('attr', {attrs: ch});
  }

  // ---- 부품 고르기(Components 견본) — 뼈대를 뽑을 수 있으면 넣기·바꾸기, 아니면 AI 요청
  function openParts(kind, ask) {
    var api = ctx.api;
    if (!api || !api.on) { closePop(); run(kind, {ask: true, part: null}); return; }   // 도우미 없음 = 목록을 못 읽음 → AI 요청 메모
    pop.dataset.kind = kind;
    pop.innerHTML = '<p class="ep-h">' + (kind === 'swap' ? '바꿀 부품' : '아래에 넣을 부품') + '</p><p class="ep-note">부품 목록을 읽는 중…</p>';
    pop.hidden = false; placePop();
    var mine = ++seq; pop.dataset.seq = String(mine);
    api.call('GET', '/api/parts').then(function (r) {
      if (pop.dataset.seq !== String(mine) || pop.hidden) return;
      var ps = r && r.body && Array.isArray(r.body.parts) ? r.body.parts : [];
      if (!ps.length) { closePop(); ctx.toast('부품 견본이 없어요 — AI에게 요청으로 열어요'); run(kind, {ask: true, part: null}); return; }
      pop.innerHTML = '<p class="ep-h">' + (kind === 'swap' ? '바꿀 부품' : '아래에 넣을 부품') + '</p><div class="ep-list">' + ps.map(function (p, i) {
        var a = ask || !p.ok;
        return '<button type="button" class="ep-part' + (a ? ' ask' : '') + '" data-i="' + i + '" title="' + (a ? 'AI에게 요청 — 뼈대를 바로 넣지 않아요' : '뼈대(중립 글)를 바로 넣어요') + '">' + ctx.esc(p.title) + '</button>';
      }).join('') + '</div><p class="ep-note">글은 "텍스트"로 들어가요 — 데이터는 화면에 맞게 고치거나 AI에게 맡기세요</p>';
      pop.parts = ps; placePop();
    }, function (e) {
      if (pop.dataset.seq !== String(mine)) return;
      closePop(); console.error('[hd] 부품 목록: ' + (e && e.message || e)); ctx.toast('부품 목록을 읽지 못했어요 — AI에게 요청으로 열어요');
      run(kind, {ask: true, part: null});
    });
  }

  // ---- 쓴 뒤 같은 요소 다시 고르기: 도우미가 준 새 경로를 다시 실린 화면(hd-here, ?v=stamp)에 묻는다
  function wrote(res, list) {
    var c = cur || (done && Date.now() - done.at < FOLLOW_MS ? done : null);
    if (!c || !res || !res.paths || !res.stamp) return;
    var n = (list || []).filter(function (x) { return x.screen === c.screen && x.path === c.h.path && res.paths[x.id]; })[0];
    if (!n) return;
    follow = {screen: c.screen, path: res.paths[n.id], v: String(res.stamp), where: c.where, until: Date.now() + FOLLOW_MS, tag: 'follow:' + res.stamp};
  }
  function frameOf(win, f) {                          // 그 창이 따라갈 화면의 새 틀(?v=stamp)인가
    if (f.where === 'modal') { var m = ctx.$('#mframe'); return m && m.contentWindow === win && (m.getAttribute('src') || '').indexOf('v=' + f.v) >= 0; }
    var c = ctx.cardEl(f.screen); if (!c) return false;
    return Array.prototype.some.call(c.querySelectorAll('.phone iframe'), function (fr) { return fr.contentWindow === win && (fr.getAttribute('src') || '').indexOf('v=' + f.v) >= 0; });
  }
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object') return;
    if (d.type === 'hd-upchain' && upWait && d.tag === upWait.tag && e.source === upWait.win) {
      var u = upWait; upWait = null;
      if (!cur || cur.screen !== u.screen) return;
      var p = B.parentPick(u.h, d.chain);
      if (!p) { navQ = []; ctx.toast('맨 바깥 요소예요 — 더 위가 없어요'); return; }
      pickThen({screen: u.screen, h: p, where: u.where});
    } else if (d.type === 'hd-hop' && hopWait && d.tag === hopWait.tag && e.source === hopWait.win) {
      var hw = hopWait; hopWait = null;
      if (!cur || cur.screen !== hw.screen) return;
      if (!d.path) { navQ = []; ctx.toast(hw.type === 'hd-down' ? '안에 고를 요소가 없어요' : '옆에 고를 요소가 없어요'); return; }
      pickThen({screen: hw.screen, h: d, where: hw.where});
    } else if (d.type === 'hd-here' && follow) {
      if (Date.now() > follow.until) { follow = null; return; }
      if (String(d.screen) !== follow.screen || !frameOf(e.source, follow)) return;
      follow.win = e.source;
      try { e.source.postMessage({type: 'hd-find', path: follow.path, tag: follow.tag}, '*'); } catch (err) { follow = null; }
    } else if (d.type === 'hd-found' && follow && d.tag === follow.tag && e.source === follow.win) {
      var f = follow; follow = null;
      if (!d.path) { console.warn('[hd] 쓴 뒤 고른 요소를 찾지 못했어요: ' + f.path); return; }
      pick({screen: f.screen, h: d, where: f.where});
    }
  });

  // ---- 끌어서 순서 바꾸기(49c): 형제 상자(틀 좌표)를 화면에 묻고, 포인터(틀 좌표)로 끼울 자리 → 선. 같은 부모 안만
  var R = HD.reorder, dr = null;
  function frameBox(f) {                              // 틀 좌표 → 화면 좌표(크게 보기·판 카드 모두 — 틀이 줄어 있으면 그 배율)
    var fr = f.getBoundingClientRect(), sc = f.offsetWidth ? fr.width / f.offsetWidth : 1;
    return {ox: fr.left + f.clientLeft * sc, oy: fr.top + f.clientTop * sc, sc: sc || 1};
  }
  function dragStart(by) {                            // by = 'grip' | 'frame'(고른 요소를 화면 안에서 눌러 끌기)
    if (!cur || !act || dr) return false;
    var g = B.grip(cur.h, {app: cur.app});
    if (reader()) { ctx.toast(RO); return false; }
    if (!g.on) { ctx.toast(g.title); return false; }
    var f = cur.frame && cur.frame(), w = f && f.contentWindow;
    if (!w) { ctx.toast('이 화면에 물을 수 없어요 — 다시 골라 주세요'); return false; }
    closePop();
    dr = {sel: cur, f: f, win: w, tag: 'sibs:' + (++seq), rects: null, from: -1, slot: -1, pt: null, by: by, copy: false};
    bar.classList.add('dragging'); document.body.classList.add('hd-dragging-el');
    try { w.postMessage({type: 'hd-sibs', path: cur.h.path, tag: dr.tag}, '*'); } catch (e) { dragStop(); ctx.toast('이 화면에 물을 수 없어요'); return false; }
    return true;
  }
  function copyMode(on) {                             // Alt = 복제해 놓기 표시(커서 copy · '+' 배지) — 끄는 중에만
    if (!dr) return;
    dr.copy = !!on;
    document.body.classList.toggle('hd-drag-copy', dr.copy);
    dropLine.dataset.copy = dr.copy ? '1' : '';
    if (dr.pt) dragAt(dr.pt);
  }
  function dragAt(pt, alt) {                          // pt = 틀 좌표 · alt = 그 포인터 사건의 Alt(모르면 undefined)
    if (!dr) return;
    if (alt !== undefined && !!alt !== dr.copy) { dr.pt = pt; copyMode(alt); return; }
    dr.pt = pt;
    var b = frameBox(dr.f);
    copyBadge.style.left = (b.ox + pt.x * b.sc + 12) + 'px'; copyBadge.style.top = (b.oy + pt.y * b.sc + 10) + 'px';
    copyBadge.hidden = !dr.copy;
    if (!dr.rects) return;
    dr.slot = R.slot(pt, dr.rects);
    var ln = dr.slot >= 0 ? R.line(dr.slot, dr.rects) : null, still = !R.plan(dr.from, dr.slot, dr.copy);
    if (!ln) { dropLine.hidden = true; return; }
    dropLine.style.left = (b.ox + ln.x * b.sc) + 'px'; dropLine.style.top = (b.oy + ln.y * b.sc) + 'px';
    dropLine.style.width = Math.max(2, ln.w * b.sc) + 'px'; dropLine.style.height = Math.max(2, ln.h * b.sc) + 'px';
    dropLine.dataset.slot = String(dr.slot); dropLine.dataset.dir = ln.dir; dropLine.style.opacity = still ? '.35' : '1';   // 제자리 = 흐리게
    dropLine.hidden = false;
  }
  function dragStop() {
    dr = null; dropLine.hidden = true; dropLine.dataset.slot = ''; dropLine.dataset.copy = ''; copyBadge.hidden = true;
    bar.classList.remove('dragging'); document.body.classList.remove('hd-dragging-el', 'hd-drag-copy');
  }
  function dragDrop() {
    var d = dr; dragStop();
    if (!d || !d.rects || d.from < 0 || d.slot < 0 || !cur || cur !== d.sel) return;
    var p = R.plan(d.from, d.slot, d.copy);
    if (!p) return;                                    // 제자리
    if (p.dup && !(ctx.api && ctx.api.on)) { ctx.toast('Alt 로 복제해 놓기는 도우미로 열었을 때만 돼요 — [복제] 뒤 끌어 옮겨 주세요'); return; }
    var dirs = R.moves(d.from, d.slot);
    run('reorder', {dirs: dirs.length ? dirs : ['down'], from: d.from, to: p.to, h: Object.assign({}, d.sel.h, {drop: {from: d.from, slot: d.slot, copy: d.copy}})});
  }
  function screenPt(e) { var b = frameBox(dr.f); return {x: (e.clientX - b.ox) / b.sc, y: (e.clientY - b.oy) / b.sc}; }
  bar.addEventListener('pointerdown', function (e) {
    var gp = e.target.closest && e.target.closest('button[data-grip]');
    if (!gp || e.button !== 0 || gp.getAttribute('aria-disabled') === 'true') return;
    e.preventDefault();
    if (!dragStart('grip')) return;
    try { gp.setPointerCapture(e.pointerId); } catch (err) { console.warn('[hd] 손잡이 포인터 잡기 실패 — ' + err); }
    dragAt(screenPt(e), e.altKey);
  });
  bar.addEventListener('pointermove', function (e) { if (dr && dr.by === 'grip') dragAt(screenPt(e), e.altKey); });
  bar.addEventListener('pointerup', function (e) { if (dr && dr.by === 'grip') { dragAt(screenPt(e), e.altKey); dragDrop(); } });
  bar.addEventListener('pointercancel', function () { if (dr && dr.by === 'grip') dragStop(); });
  addEventListener('keydown', function (e) { if (dr && e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); dragStop(); } }, true);
  var altKey = function (e) { if (dr && e.key === 'Alt') { e.preventDefault(); e.stopPropagation(); copyMode(e.type === 'keydown'); } };   // 끄는 중 Alt 누름·뗌(포인터를 움직이지 않아도)
  addEventListener('keydown', altKey, true); addEventListener('keyup', altKey, true);
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object') return;
    if (d.type === 'hd-sibs' && dr && d.tag === dr.tag && e.source === dr.win) {
      if (!Array.isArray(d.rects) || !(d.index >= 0)) { dragStop(); ctx.toast('이 요소의 형제를 찾지 못했어요 — 다시 골라 주세요'); return; }
      dr.rects = d.rects; dr.from = d.index;
      if (dr.pt) dragAt(dr.pt);
    } else if (d.type === 'hd-grab' && cur && cur.frame) {   // 크게 보기: 고른 요소를 화면 안에서 눌러 끌기
      var f = cur.frame(); if (!f || e.source !== f.contentWindow) return;
      var pt = {x: +d.x || 0, y: +d.y || 0}, alt = d.alt === undefined ? undefined : !!d.alt;
      if (d.phase === 'start') { if (dragStart('frame')) dragAt(pt, alt); }
      else if (!dr || dr.by !== 'frame') return;
      else if (d.phase === 'move') dragAt(pt, alt);
      else if (d.phase === 'end') { dragAt(pt, alt); dragDrop(); }
      else dragStop();
    }
  });

  bar.addEventListener('pointerdown', function (e) { e.stopPropagation(); });   // 판 끌기·고르기 풀기로 새지 않게
  pop.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
  bar.addEventListener('click', function (e) {
    e.stopPropagation();
    var gp = e.target.closest('button[data-grip]');
    if (gp) {                                          // 손잡이는 끌기 — 꺼진 손잡이를 누르면 까닭
      if (reader()) ctx.toast(RO); else if (gp.getAttribute('aria-disabled') === 'true') ctx.toast(B.grip(cur.h, {app: cur.app}).title);
      return;
    }
    if (e.target.closest('button[data-more]')) { if (pop.dataset.kind === 'more' && !pop.hidden) closePop(); else { closePop(); openMore(); } return; }
    var b = e.target.closest('button[data-act]'); if (b) fire(b.dataset.act);
  });
  pop.addEventListener('click', function (e) {
    e.stopPropagation();
    var b = e.target.closest('button'); if (!b || !cur) return;
    if (b.dataset.ep === 'cancel') { closePop(); return; }
    if (b.dataset.ep === 'apply') { applyAttr(); return; }
    if (b.classList.contains('ep-act')) { closePop(); fire(b.dataset.act); return; }
    if (b.classList.contains('ep-part')) {
      var p = (pop.parts || [])[+b.dataset.i], kind = pop.dataset.kind, ask = b.classList.contains('ask');
      closePop(); if (p) run(kind, {ask: ask, part: p});
    }
  });
  pop.addEventListener('keydown', function (e) {
    e.stopPropagation();
    if (e.key === 'Escape') { e.preventDefault(); closePop(); }
    else if (e.key === 'Enter' && pop.dataset.kind === 'attr' && e.target.tagName === 'INPUT') { e.preventDefault(); applyAttr(); }
  });
  var NAV = {enter: 1, next: 1, prev: 1};
  addEventListener('keydown', function (e) {        // 고른 요소가 있을 때만: [·Shift+Enter 상위 · Enter 안으로 · Tab 형제 · Alt+↑↓ 옮기기 · Ctrl+D 복제 · Delete 지우기
    if (!cur || bar.hidden) return;
    var t = e.target; if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
    var a = B.keyAct({key: e.key, code: e.code, alt: e.altKey, ctrl: e.ctrlKey, meta: e.metaKey, shift: e.shiftKey});
    if (!a) return;
    if ((e.key === 'Enter' || e.key === 'Tab') && t && t.closest && t.closest('[role=menu], [role=dialog], dialog, #elpop, #cmenu')) return;   // 메뉴·창 안 Enter/Tab 은 그 메뉴 것
    e.preventDefault(); e.stopPropagation();
    if ((NAV[a] || a === 'parent') && (hopWait || upWait)) { navQ.push(a); return; }   // 앞 고르기의 답을 기다리는 중 — 그 뒤에 차례로
    step(a);
  }, true);
  addEventListener('resize', place);
  return {show: show, hide: hide, place: place, sel: function () { return cur; }, wrote: wrote,
          onAct: function (fn) { act = typeof fn === 'function' ? fn : null; },
          onPick: function (fn) { picked = typeof fn === 'function' ? fn : null; }};
}

HD.feature('blocks', {needs: ['$', 'toast', 'esc', 'api', 'cardEl'], mount: mount});
})();
