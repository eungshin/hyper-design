/* View — Foundation 탭 토큰 고르기·고치기(R55): 문서 탭 도구(손·선택 V) · 고른 견본 옆 작은 속성 창 · 저장(POST /api/token) · 모든 틀 토큰 다시 읽기 · 되돌리기 줄.
   규칙(종류·값 검사·칸·메시지 모양·주소)은 HD.dsEdit(Model), 창 자리는 HD.popPlace.clamp(R58 — 떠 있는 창 자리 함수 하나). 계약 contract/ds-edit.md.
   문서 탭(Foundation·Components)에서는 도구 막대(#tools)를 그 탭 칸으로 옮겨 손·선택만 보인다(다른 도구는 숨김) · H·V 키 · 선택이면 그 탭 iframe.doc 에 hd-pick(doc:true).
   palette.js 가 [data-var] 견본을 고르면 hd-sel + token → 속성 창(제목 = 견본 이름 + 토큰 이름, 색 = 색 판 + HEX · 길이 = 숫자 + 지금 단위 · 굵기·줄 높이 = 숫자 · 그림자 = 글).
   Enter·change = 저장, Esc·밖 누르기 = 닫기, 틀린 값 = 그 칸을 원래 값으로 + 까닭 한 줄. 저장 뒤: 의도 'hd-theme-project'(테마 미리 보기를 프로젝트 색으로) →
   모든 iframe 에 hd-css-reload {sheet:'tokens', v}(카드·크게 보기·DS 카드·문서 탭) · 기록 한 줄 '토큰 바꾸기 --이름'(되돌리기 = /api/restore, 다시 하기 = 같은 값 다시 쓰기).
   문서 안을 누른 뒤의 키(H·V·Esc·Ctrl+Z)는 palette.js 가 hd-key 로 넘기고 여기서 셸에 키 이벤트로 다시 낸다.
   다른 탭·AI 가 tokens.css·components.css 를 고침 = 의도 'hd-css-changed' {sheet}(view-busy 가 /api/files 의 '@tokens'·'@components' 로 보냄) → 다시 읽기만.
   읽기만 탭(html.hd-ro) = 고르기·창은 되고 저장만 막는다. 오류 탐지: iframe.doc 이 없거나 [data-var]·.spec-stage 가 둘 다 없는 문서 = [hd] 경고 한 번 뒤 그 탭은 그냥 문서(고르기 끔) ·
   저장 실패 = 도우미의 까닭 토스트 + 칸 되돌림.
   부품(phase C, Components 탭): palette.js 가 고른 부품(hd-sel part) → POST /api/component-slots 로 그 요소를 겨누는 components.css 규칙·바꿀 칸 →
   같은 창에 규칙마다 줄(바탕·변형 먼저, 상태 규칙은 '상태' 아래 누를 때·못 누를 때…, 다른 부품도 부르는 목록 = '버튼·칩 함께 바뀌어요').
   칸 = 쉬운 속성 이름 + 같은 묶음 토큰 목록(#dsList — 색 점·값 미리 보기 + 쉬운 이름). 고르면 POST /api/component → 모든 틀 components.css 다시 읽기 ·
   기록 한 줄 '부품 바꾸기 <부품> <속성>'. 자유 값은 없다(사용자 결정 — 값은 Foundation 탭에서만).
   상태(이 View 만): 문서 탭 도구 tool · 지금 탭 · 고른 토큰·부품 pick · 부품 칸 part · 경고한 탭.
   HD.feature('dsEdit', {needs: ['$', '$$', 'toast', 'warn', 'api', 'record']}) → {tab(name), tool(t), current() → {tab, tool, pick}} — 셸 showTab·setTool 이 한 줄씩 부른다 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var DOC_SEL = 'body[data-tab="foundation"],body[data-tab="components"]';
var CSS = ['foundation', 'components'].map(function (t) {
    return 'body[data-tab="' + t + '"] #tools [data-tool]:not([data-tool="hand"]):not([data-tool="move"]),body[data-tab="' + t + '"] #tools hr,body[data-tab="' + t + '"] #tools #thid';
  }).join(',') + '{display:none!important}' +
  ['foundation', 'components'].map(function (t) { return 'body[data-tab="' + t + '"]:not(.no-tools):not(.bare) #' + t + ' iframe.doc'; }).join(',') +
    '{margin-left:64px;width:calc(100% - 64px)}' +   // 도구 막대(왼쪽 12 + 48) 자리는 비운다 — 견본을 가리지 않게
  '#dsInsp{position:fixed;z-index:24;width:248px;box-sizing:border-box;background:#fff;border:1px solid var(--ui-line,#e3e3df);border-radius:10px;' +
    'box-shadow:0 10px 28px rgba(0,0,0,.16),0 1px 3px rgba(0,0,0,.08);font:12px/1.4 system-ui,-apple-system,"Pretendard",sans-serif;color:#1c1c1c;padding:0 0 8px}' +
  '#dsInsp[hidden]{display:none}' +
  '#dsInsp .di-head{display:flex;align-items:center;gap:8px;height:36px;padding:0 6px 0 12px;border-bottom:1px solid #efefec;margin-bottom:6px}' +
  '#dsInsp .di-title{flex:1;min-width:0;display:flex;flex-direction:column;line-height:1.2}' +
  '#dsInsp .di-title b{font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#dsInsp .di-title code{font:10.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:#8a8a85;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#dsInsp .di-x{flex:none;width:24px;height:24px;border:0;border-radius:6px;background:none;color:#6b6b66;font-size:15px;line-height:1;cursor:pointer}' +
  '#dsInsp .di-x:hover{background:#F1F1EE;color:#1c1c1c}' +
  '#dsInsp .di-row{display:grid;grid-template-columns:64px 1fr;align-items:center;gap:8px;padding:3px 12px}' +
  '#dsInsp .di-row>label{color:#6b6b66;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#dsInsp .di-ctl{display:flex;align-items:center;gap:6px;min-width:0;height:28px;border:1px solid transparent;border-radius:6px;background:#F5F5F2;padding:0 6px}' +
  '#dsInsp .di-ctl:hover{border-color:#e3e3df}#dsInsp .di-ctl:focus-within{border-color:var(--ui-mark,#2b2b29);background:#fff}' +
  '#dsInsp .di-ctl.bad{border-color:var(--ui-danger,#c8463f)}' +
  '#dsInsp input{min-width:0;flex:1;height:24px;border:0;background:none;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:#1c1c1c;padding:0;outline:0}' +
  '#dsInsp input[type="color"]{flex:none;width:18px;height:18px;padding:0;border:1px solid rgba(0,0,0,.12);border-radius:4px;cursor:pointer;background:none}' +
  '#dsInsp input[type="color"]::-webkit-color-swatch-wrapper{padding:0}#dsInsp input[type="color"]::-webkit-color-swatch{border:0;border-radius:3px}' +
  '#dsInsp input[type="number"]{-moz-appearance:textfield}#dsInsp input::-webkit-inner-spin-button,#dsInsp input::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}' +
  '#dsInsp .di-unit{flex:none;color:#8a8a85;font:11px ui-monospace,Menlo,monospace}' +
  '#dsInsp .di-msg{margin:4px 12px 0;color:var(--ui-danger,#c8463f);font-size:11.5px;min-height:0}#dsInsp .di-msg:empty{display:none}' +
  '#dsInsp .di-note{margin:4px 12px 0;color:#8a8a85;font-size:11px}' +
  // 부품(phase C) — Figma 속성 패널처럼: 규칙 = 작은 머리글, 칸 = 이름 · 토큰 고르기 단추
  '#dsInsp.part{width:288px}#dsInsp .di-body{max-height:min(560px,calc(100vh - 140px));overflow:auto;overscroll-behavior:contain}' +
  '#dsInsp .di-grp{padding:6px 0 4px}#dsInsp .di-grp+.di-grp{border-top:1px solid #f1f1ee}' +
  '#dsInsp .di-gh{display:flex;align-items:baseline;gap:8px;padding:0 12px 2px;min-width:0}' +
  '#dsInsp .di-gh b{flex:none;font-size:11.5px;font-weight:600;color:#3a3a37}#dsInsp .di-gh b:empty{display:none}' +
  '#dsInsp .di-gh code{flex:1;min-width:0;font:10.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:#8a8a85;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#dsInsp .di-gh .di-here{flex:none;font-size:10.5px;color:#2563eb}' +
  '#dsInsp .di-shared{margin:0 12px 2px;font-size:11px;color:#9a6a00}' +
  '#dsInsp .di-sec{margin:6px 12px 0;padding-top:8px;border-top:1px solid #e9e9e5;font-size:11px;font-weight:600;color:#8a8a85;letter-spacing:.02em}' +
  '#dsInsp .di-state .di-row>label{color:#8a8a85}' +
  '#dsInsp .di-tok{width:100%;cursor:pointer;text-align:left;font:inherit;color:#1c1c1c}' +
  '#dsInsp .di-tok .nm{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#dsInsp .di-tok .cv{flex:none;width:6px;height:6px;border-right:1.5px solid #8a8a85;border-bottom:1.5px solid #8a8a85;transform:translateY(-2px) rotate(45deg);margin:0 3px 0 4px}' +
  '.di-dot{flex:none;width:14px;height:14px;border-radius:4px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.14)}' +
  '.di-rad{flex:none;width:14px;height:14px;border:1.5px solid #6b6b66;border-right:0;border-bottom:0;box-sizing:border-box}' +
  '.di-v{flex:none;font:10.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:#8a8a85}' +
  '#dsInsp .di-empty{margin:8px 12px;color:#8a8a85}' +
  '#dsList{position:fixed;z-index:25;min-width:220px;max-width:300px;max-height:320px;overflow:auto;box-sizing:border-box;background:#fff;border:1px solid var(--ui-line,#e3e3df);border-radius:8px;' +
    'box-shadow:0 10px 28px rgba(0,0,0,.18);padding:4px;font:12px/1.3 system-ui,-apple-system,"Pretendard",sans-serif;color:#1c1c1c}#dsList[hidden]{display:none}' +
  '#dsList [role="option"]{display:flex;align-items:center;gap:8px;height:30px;padding:0 8px;border-radius:5px;cursor:pointer;outline:0}' +
  '#dsList [role="option"] .nm{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
  '#dsList [role="option"] code{flex:none;font:10.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:#8a8a85}' +
  '#dsList [role="option"].on,#dsList [role="option"]:hover{background:#F1F1EE}#dsList [role="option"][aria-selected="true"] .nm{font-weight:600}' +
  '#dsList [role="option"][aria-selected="true"]::after{content:"";flex:none;width:9px;height:5px;border-left:1.5px solid #1c1c1c;border-bottom:1.5px solid #1c1c1c;transform:rotate(-45deg) translateY(-2px)}';
var LABEL = {color: '색', size: '크기', weight: '굵기', line: '줄 높이', space: '간격', radius: '모서리', shadow: '그림자', other: '값'};

function mount(ctx) {
  var M = HD.dsEdit, P = HD.popPlace, $ = ctx.$;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var box = document.createElement('div');
  box.id = 'dsInsp'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', '토큰 고치기'); box.hidden = true;
  document.body.appendChild(box);
  var tools = $('#tools'), home = tools ? {parent: tools.parentNode, next: tools.nextSibling} : null;
  var list = document.createElement('div');
  list.id = 'dsList'; list.setAttribute('role', 'listbox'); list.setAttribute('aria-label', '토큰 고르기'); list.hidden = true;
  document.body.appendChild(list);
  var tab = document.body.dataset.tab || 'screens', tool = 'hand', pick = null, fields = [], warned = {}, answered = {}, loaded = {};
  var part = null, listAt = null;                    // 부품 칸: {rules, tokens} · 열린 토큰 목록의 칸 {g, s, btn}

  function frame(name) { return $('#' + (name || tab) + ' iframe.doc'); }
  function post(f, msg) { try { if (f && f.contentWindow) f.contentWindow.postMessage(msg, '*'); } catch (e) { ctx.warn('[hd] 문서 탭에 보내지 못함 — ' + (e && e.message || e)); } }
  function warnOnce(key, msg) { if (warned[key]) return; warned[key] = true; ctx.warn('[hd] ' + msg); }
  function sendPick() {
    if (!M.docTab(tab)) return;
    var f = frame();
    if (!f) { warnOnce('frame:' + tab, tab + ' 탭에 iframe.doc 이 없어요 — 토큰 고르기 없이 그냥 문서'); return; }
    if (warned['plain:' + tab]) { post(f, M.pickMsg(false)); return; }   // 토큰 견본이 없는 문서 = 그냥 문서
    var on = tool === 'move', at = tab;
    post(f, M.pickMsg(on));
    if (on && loaded[at]) setTimeout(function () {   // 실린 문서가 1.5초 안에 hd-pick-on 으로 답하지 않으면 palette.js 가 없는 문서
      if (!answered[at] && tab === at && tool === 'move') warnOnce('plain:' + at, at + ' 문서가 고르기에 답하지 않아요(palette.js 없음) — 그냥 문서');
    }, 1500);
  }
  function paintTools() {
    ctx.$$('#tools [data-tool]').forEach(function (b) { if (b.dataset.tool === 'hand' || b.dataset.tool === 'move') b.setAttribute('aria-pressed', String(b.dataset.tool === tool)); });
  }
  function setTool(t) {
    if (t !== 'hand' && t !== 'move') return;
    if (t !== tool) close(true);
    tool = t; paintTools(); sendPick();
  }
  function setTab(name) {
    var was = tab; tab = name;
    if (M.docTab(was) && was !== name) { close(true); post(frame(was), M.pickMsg(false)); }
    if (!tools || !home) return;
    if (M.docTab(name)) {
      var pane = $('#' + name);
      if (pane && tools.parentNode !== pane) pane.appendChild(tools);
      paintTools(); sendPick();
    } else if (tools.parentNode !== home.parent) home.parent.insertBefore(tools, home.next && home.next.parentNode === home.parent ? home.next : null);
  }
  ['foundation', 'components'].forEach(function (n) {   // 문서가 (다시) 실리면 지금 도구를 다시 알린다
    var f = frame(n); if (f) f.addEventListener('load', function () { loaded[n] = true; if (tab === n) sendPick(); });
  });

  // ---- 속성 창
  function frameRect() { var f = frame(); return f ? f.getBoundingClientRect() : {left: 0, top: 0, width: innerWidth, height: innerHeight}; }
  function place() {                                 // 견본 오른쪽 → 왼쪽 → 아래, 문서 칸(도크·대화창 밖) 안으로 — 자리 맞추기는 HD.popPlace.clamp 하나(R58)
    if (!pick) return;
    var fr = frameRect(), a = {x: pick.rect.x, y: pick.rect.y, w: pick.rect.w, h: pick.rect.h};   // 문서 칸 좌표
    var w = box.offsetWidth, h = box.offsetHeight, gap = 10, x, y = a.y;
    if (a.x + a.w + gap + w <= fr.width - P.MARGIN) x = a.x + a.w + gap;
    else if (a.x - gap - w >= P.MARGIN) x = a.x - gap - w;
    else { x = a.x + a.w - w; y = a.y + a.h + gap; if (y + h > fr.height - P.MARGIN) y = a.y - gap - h; }
    var p = P.clamp({x: x, y: y, w: w, h: h}, fr.width, fr.height, {w: w, h: h});
    box.style.left = Math.round(fr.left + p.x) + 'px'; box.style.top = Math.round(fr.top + p.y) + 'px';
  }
  function row(f, i) {
    var id = 'di-' + i, lab = '<label for="' + id + '">' + LABEL[f.kind] + '</label>';
    if (f.input === 'color') return '<div class="di-row" data-i="' + i + '">' + lab + '<span class="di-ctl"><input type="color" class="di-col" aria-label="색 고르기" value="' + (f.hex || '#000000').toLowerCase() + '">' +
      '<input id="' + id + '" class="di-val" spellcheck="false" maxlength="40" aria-label="' + LABEL[f.kind] + ' HEX"></span></div>';
    if (f.input === 'len') return '<div class="di-row" data-i="' + i + '">' + lab + '<span class="di-ctl"><input id="' + id + '" class="di-val" type="number" step="any" min="0">' +
      '<span class="di-unit">' + f.unit + '</span></span></div>';
    if (f.input === 'num') return '<div class="di-row" data-i="' + i + '">' + lab + '<span class="di-ctl"><input id="' + id + '" class="di-val" type="number" ' +
      (f.kind === 'weight' ? 'min="100" max="900" step="100"' : 'min="0.5" max="5" step="0.05"') + '></span></div>';
    return '<div class="di-row" data-i="' + i + '">' + lab + '<span class="di-ctl"><input id="' + id + '" class="di-val" spellcheck="false" maxlength="200"></span></div>';
  }
  function shown(f) { return f.input === 'len' ? f.num : f.input === 'color' ? (f.hex || f.value) : f.value; }
  function fill(i) {
    var f = fields[i], r = box.querySelector('.di-row[data-i="' + i + '"]'); if (!f || !r) return;
    r.querySelector('.di-val').value = shown(f);
    var c = r.querySelector('.di-col'); if (c && f.hex) c.value = f.hex.toLowerCase();
    r.querySelector('.di-ctl').classList.remove('bad');
  }
  function open(p) {
    if (p.kind === 'part') { openPart(p); return; }
    box.classList.remove('part'); part = null; hideList();
    pick = p; fields = M.fields(p);
    box.innerHTML = '<div class="di-head"><span class="di-title"><b>' + esc(p.label || p.token) + '</b><code>' + esc(p.token) + '</code></span>' +
      '<button type="button" class="di-x" aria-label="닫기" title="닫기 (Esc)">×</button></div>' + fields.map(row).join('') +
      '<p class="di-msg" role="status"></p>' + (document.documentElement.classList.contains('hd-ro') ? '<p class="di-note">읽기만 하는 탭이라 저장은 막혀 있어요</p>' : '');
    fields.forEach(function (f, i) { fill(i); });
    box.hidden = false; place();
    var first = box.querySelector('.di-val'); if (first) { first.focus({preventScroll: true}); first.select(); }
  }
  function close(keepSel) {
    if (box.hidden && !pick) return;
    box.hidden = true; box.innerHTML = ''; pick = null; fields = []; part = null; hideList();
    if (!keepSel) post(frame(), {type: 'hd-unpick'});
  }
  function say(m) { var e = box.querySelector('.di-msg'); if (e) e.textContent = m || ''; }

  function reloadAll(v, sheet) {                     // 모든 틀(카드·크게 보기·DS 카드·문서 탭·나눈 칸) 그 스타일 다시 읽기 + 셸 #tokens(토큰·프로젝트 색일 때)
    sheet = sheet || 'tokens';
    var msg = M.reloadMsg(sheet, v);
    ctx.$$('iframe').forEach(function (f) { post(f, msg); });
    if (sheet !== 'tokens') return;
    var l = $('#tokens'); if (!l) return;
    var b = l.getAttribute('data-base') || l.getAttribute('href'); l.setAttribute('data-base', b);
    if ((l.getAttribute('href') || '').split('?')[0] === b.split('?')[0]) l.setAttribute('href', M.href(b, '', v));
  }
  function after(sheet) {                            // 저장·되돌리기 뒤 — (토큰이면) 테마 미리 보기를 프로젝트 색으로, 그리고 다시 읽기
    if (sheet === 'components') { reloadAll('c' + Date.now(), 'components'); return false; }
    var ev = new CustomEvent('hd-theme-project', {detail: {changed: false}});
    document.dispatchEvent(ev);
    reloadAll('t' + Date.now());
    return ev.detail.changed;
  }
  function write(name, value) {                      // → Promise<답 몸통 | null(까닭은 알렸다)>
    return ctx.api.call('POST', '/api/token', {name: name, value: value}).then(function (r) {
      if (r.status === 200 && r.body && !r.body.error) return r.body;
      ctx.toast('토큰을 바꾸지 못했어요: ' + ((r.body && r.body.error) || r.status), false, 6000); return null;
    }, function (e) { ctx.toast('토큰을 바꾸지 못했어요 — 도우미에 닿지 않아요'); ctx.warn('[hd] 토큰 쓰기 실패: ' + (e && e.message || e)); return null; });
  }
  function restore(stamp, sheet) {
    return ctx.api.call('POST', '/api/restore', {stamp: stamp}).then(function (r) {
      if (r.body && r.body.error) { ctx.toast(r.body.reason === 'changed-since' ? '그 뒤에 ' + (sheet || 'tokens') + '.css 가 바뀌어 되돌릴 수 없어요' : '되돌리지 못했어요: ' + r.body.error); return false; }
      after(sheet); return true;
    }, function () { ctx.toast('되돌리지 못했어요 — 도우미에 닿지 않아요'); return false; });
  }
  function save(i) {
    var f = fields[i], r = box.querySelector('.di-row[data-i="' + i + '"]'); if (!f || !r) return;
    var raw = r.querySelector('.di-val').value, v = M.compose(f, raw), c = M.check(f.name, v);
    if (!c.ok) { fill(i); r.querySelector('.di-ctl').classList.add('bad'); say(c.why); return; }   // 틀린 값 = 그 칸을 원래 값으로
    say('');
    if (c.value === f.value) return;
    if (document.documentElement.classList.contains('hd-ro')) { fill(i); ctx.toast('이 탭은 읽기만 해요 — 위쪽 "여기서 편집하기"를 누르면 저장할 수 있어요'); return; }
    if (!ctx.api.on) { fill(i); ctx.toast('도우미로 열었을 때만 토큰을 바꿀 수 있어요(파일에 바로 쓰기)'); return; }
    var name = f.name, old = f.value, want = c.value, mine = pick;
    write(name, want).then(function (b) {
      if (!b) { if (pick === mine) fill(i); return; }
      f.value = b.value; if (f.input === 'color') f.hex = /^#[0-9A-F]{6}$/.test(b.value) ? b.value : f.hex;
      if (f.input === 'len') f.num = M.fields({token: name, vars: (function () { var o = {}; o[name] = b.value; return o; })()})[0].num;
      if (pick === mine) fill(i);
      var themed = after(), at = b.stamp;
      ctx.record({label: '토큰 바꾸기 ' + name, status: 'file',
        undo: function () { restore(at).then(function (ok) { if (ok) { f.value = old; if (pick === mine) close(); } }); },
        redo: function () { write(name, want).then(function (x) { if (x) { at = x.stamp; after(); } }); }});
      ctx.toast(themed ? '테마 미리 보기를 끄고 프로젝트 색으로 바꿨어요' : name + ' 을 바꿨어요 — 모든 화면에 반영', true);
    });
  }

  // ---- 부품(phase C): 규칙·칸 읽기 · 그리기 · 토큰 목록 · 저장
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function preview(t) {                              // 토큰 미리 보기(이름 앞): 색 = 점 · 모서리 = 모서리 조각
    if (!t) return '';
    if (t.family === 'color') return '<i class="di-dot" style="background:' + esc(t.value) + '"></i>';
    if (t.family === 'radius') return '<i class="di-rad" style="border-top-left-radius:' + esc(t.value) + '"></i>';
    return '';
  }
  function valueTail(t) { return t && t.family !== 'color' ? '<span class="di-v">' + esc(t.value) + '</span>' : ''; }   // 값(이름 뒤, 흐리게) — 색은 점이 값
  function tokLabel(name) { var t = part && part.tokens[name]; return t ? t.label : name; }
  function openPart(p) {
    pick = p; fields = []; part = null; hideList();
    box.classList.add('part');
    box.innerHTML = '<div class="di-head"><span class="di-title"><b>' + esc(p.part.title || p.label || '부품') + '</b><code>.' + esc(p.part.classes.join('.')) + '</code></span>' +
      '<button type="button" class="di-x" aria-label="닫기" title="닫기 (Esc)">×</button></div><div class="di-body"><p class="di-empty">규칙을 읽는 중…</p></div><p class="di-msg" role="status"></p>';
    box.hidden = false; place();
    loadPart(p, false);
  }
  function loadPart(p, keep) {
    if (!ctx.api.on) { paintPart(null, '도우미로 열었을 때만 부품을 고칠 수 있어요(파일에 바로 쓰기)'); return; }
    ctx.api.call('POST', '/api/component-slots', {classes: p.part.classes, tag: p.part.tag}).then(function (r) {
      if (pick !== p) return;
      if (r.status !== 200 || !r.body || r.body.error) { paintPart(null, '규칙을 읽지 못했어요: ' + ((r.body && r.body.error) || r.status)); return; }
      part = {rules: Array.isArray(r.body.rules) ? r.body.rules : [], tokens: r.body.tokens || {}};
      paintPart(part, '', keep);
    }, function (e) { ctx.warn('[hd] 부품 규칙 읽기 실패: ' + (e && e.message || e)); if (pick === p) paintPart(null, '도우미에 닿지 않아요'); });
  }
  function paintPart(d, msg, keep) {
    var body = box.querySelector('.di-body'); if (!body) return;
    var top = keep ? body.scrollTop : 0;
    if (!d) { body.innerHTML = '<p class="di-empty">' + esc(msg) + '</p>'; place(); return; }
    if (!d.rules.length) { body.innerHTML = '<p class="di-empty">이 요소에는 토큰으로 바꿀 칸이 없어요</p>'; place(); return; }
    var html = '', secDone = false, here = pick && pick.part.state === 'disabled' ? '못 누를 때' : pick && pick.part.state === 'checked' ? '켰을 때' : '';
    d.rules.forEach(function (g, gi) {
      if (g.state && !secDone) { secDone = true; html += '<p class="di-sec">상태</p>'; }
      html += '<div class="di-grp' + (g.state ? ' di-state' : '') + '"><div class="di-gh"><b>' + esc(g.state) + '</b><code title="' + esc(g.selector) + '">' + esc(g.selector) + '</code>' +
        (here && g.state && g.state.indexOf(here) >= 0 ? '<span class="di-here">이 견본</span>' : '') + '</div>' +
        (g.shared && g.shared.length ? '<p class="di-shared">' + esc(g.shared.join('·')) + ' 함께 바뀌어요</p>' : '');
      g.slots.forEach(function (s, si) {
        var t = d.tokens[s.token], id = 'dp-' + gi + '-' + si;
        html += '<div class="di-row" data-g="' + gi + '" data-s="' + si + '"><label for="' + id + '" title="' + esc(s.prop) + '">' + esc(s.label) + '</label>' +
          '<button type="button" id="' + id + '" class="di-ctl di-tok" aria-haspopup="listbox" title="' + esc(s.token) + '">' + preview(t) +
          '<span class="nm">' + esc(t ? t.label : s.token) + '</span>' + valueTail(t) + '<i class="cv"></i></button></div>';
      });
      html += '</div>';
    });
    body.innerHTML = html + (document.documentElement.classList.contains('hd-ro') ? '<p class="di-note">읽기만 하는 탭이라 저장은 막혀 있어요</p>' : '');
    body.scrollTop = top;
    if (!keep) place();
  }
  function hideList() { if (list.hidden) return; list.hidden = true; list.innerHTML = ''; listAt = null; }
  function showList(btn) {
    var row = btn.closest('.di-row'); if (!row || !part) return;
    var g = part.rules[+row.dataset.g], s = g && g.slots[+row.dataset.s]; if (!s) return;
    var names = Object.keys(part.tokens).filter(function (n) { return M.same(s.token, n); });   // 같은 묶음 토큰만(사용자 결정)
    if (names.indexOf(s.token) < 0) names.unshift(s.token);
    list.innerHTML = names.map(function (n) {
      var t = part.tokens[n];
      return '<div role="option" tabindex="-1" data-name="' + esc(n) + '" aria-selected="' + (n === s.token) + '">' + preview(t) +
        '<span class="nm">' + esc(t ? t.label : n) + '</span>' + valueTail(t) + '<code>' + esc(n) + '</code></div>';
    }).join('');
    listAt = {g: +row.dataset.g, s: +row.dataset.s, btn: btn};
    list.hidden = false;
    var r = btn.getBoundingClientRect(), w = Math.max(r.width, list.offsetWidth), h = list.offsetHeight;
    var y = r.bottom + 4 + h > innerHeight - P.MARGIN ? r.top - 4 - h : r.bottom + 4;
    var q = P.clamp({x: r.left, y: y, w: w, h: h}, innerWidth, innerHeight, {w: w, h: h});
    list.style.left = Math.round(q.x) + 'px'; list.style.top = Math.round(q.y) + 'px'; list.style.minWidth = Math.round(r.width) + 'px';
    var on = list.querySelector('[aria-selected="true"]') || list.firstElementChild;
    if (on) { on.classList.add('on'); on.focus({preventScroll: true}); on.scrollIntoView({block: 'nearest'}); }
  }
  function listKey(e) {
    e.stopPropagation();
    var opts = [].slice.call(list.querySelectorAll('[role="option"]')), cur = list.querySelector('.on'), i = opts.indexOf(cur);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault(); var n = opts[Math.max(0, Math.min(opts.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))];
      if (cur) cur.classList.remove('on'); if (n) { n.classList.add('on'); n.focus({preventScroll: true}); n.scrollIntoView({block: 'nearest'}); }
    } else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (cur) choose(cur.dataset.name); }
    else if (e.key === 'Escape' || e.key === 'Tab') { e.preventDefault(); var b = listAt && listAt.btn; hideList(); if (b) b.focus(); }
  }
  function choose(to) {
    var at = listAt; hideList(); if (!at || !part) return;
    var g = part.rules[at.g], s = g && g.slots[at.s]; if (!s || !to || to === s.token) return;
    if (!M.same(s.token, to)) { say('같은 묶음의 토큰만 고를 수 있어요'); return; }
    if (document.documentElement.classList.contains('hd-ro')) { ctx.toast('이 탭은 읽기만 해요 — 위쪽 "여기서 편집하기"를 누르면 저장할 수 있어요'); return; }
    if (!ctx.api.on) { ctx.toast('도우미로 열었을 때만 부품을 바꿀 수 있어요(파일에 바로 쓰기)'); return; }
    var body = {selector: g.selector, prop: s.prop, index: s.index, from: s.token, to: to}, mine = pick;
    var what = ((mine && mine.part.title) || '부품') + ' ' + s.label;
    say('');
    writePart(body).then(function (b) {
      if (!b) return;
      s.token = to; if (pick === mine) paintPart(part, '', true);
      after('components');
      var stamp = b.stamp;
      ctx.record({label: '부품 바꾸기 ' + what, status: 'file',
        undo: function () { restore(stamp, 'components').then(function (ok) { if (ok && pick === mine && mine) loadPart(mine, true); }); },
        redo: function () { writePart(body).then(function (x) { if (x) { stamp = x.stamp; after('components'); if (pick === mine && mine) loadPart(mine, true); } }); }});
      ctx.toast(what + ' → ' + tokLabel(to) + ' — 모든 화면에 반영', true);
    });
  }
  function writePart(body) {                         // → Promise<답 몸통 | null(까닭은 알렸다)>
    return ctx.api.call('POST', '/api/component', body).then(function (r) {
      if (r.status === 200 && r.body && !r.body.error) return r.body;
      ctx.toast('부품을 바꾸지 못했어요: ' + ((r.body && r.body.error) || r.status), false, 6000); return null;
    }, function (e) { ctx.toast('부품을 바꾸지 못했어요 — 도우미에 닿지 않아요'); ctx.warn('[hd] 부품 쓰기 실패: ' + (e && e.message || e)); return null; });
  }

  box.addEventListener('keydown', function (e) {
    e.stopPropagation();                             // 판·문서 탭 단축키(H·V·Ctrl+Z)가 받지 않게
    if (e.key === 'Escape') { e.preventDefault(); if (!list.hidden) { var b0 = listAt && listAt.btn; hideList(); if (b0) b0.focus(); } else close(); return; }
    if (e.target.classList && e.target.classList.contains('di-tok') && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); showList(e.target); return; }
    var r = e.target.closest && e.target.closest('.di-row');
    if (e.key === 'Enter' && r && e.target.classList.contains('di-val')) { e.preventDefault(); save(+r.dataset.i); }
  });
  box.addEventListener('change', function (e) {
    var r = e.target.closest('.di-row'); if (!r) return;
    if (e.target.classList.contains('di-col')) r.querySelector('.di-val').value = e.target.value.toUpperCase();
    save(+r.dataset.i);
  });
  box.addEventListener('input', function (e) {       // 색 판을 끄는 동안 HEX 칸도 따라 — 저장은 change 에서
    if (!e.target.classList.contains('di-col')) return;
    var r = e.target.closest('.di-row'); if (r) r.querySelector('.di-val').value = e.target.value.toUpperCase();
  });
  box.addEventListener('click', function (e) {
    if (e.target.closest('.di-x')) { close(); return; }
    var b = e.target.closest('.di-tok'); if (b) { if (!list.hidden && listAt && listAt.btn === b) hideList(); else showList(b); }
  });
  list.addEventListener('click', function (e) { var o = e.target.closest('[role="option"]'); if (o) choose(o.dataset.name); });
  list.addEventListener('keydown', listKey);
  document.addEventListener('pointerdown', function (e) {   // 밖 누르기 = 닫기(문서 탭 안 누르기는 palette.js 가 새 견본으로 답한다)
    if (!list.hidden && list.contains(e.target)) return;
    if (!list.hidden && !(e.target.closest && e.target.closest('.di-tok'))) hideList();
    if (box.hidden || box.contains(e.target)) return;
    close(true);
  }, true);
  addEventListener('resize', function () { hideList(); if (!box.hidden) place(); });
  addEventListener('keydown', function (e) {         // 문서 탭: H·V = 손·선택 · Esc = 속성 창 닫기(셸 도구 키는 Screens 탭만)
    if (!M.docTab(document.body.dataset.tab) || e.ctrlKey || e.metaKey || e.altKey) return;
    var t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
    if (typing) return;
    var k = (e.key || '').toLowerCase();
    if (k === 'escape' && !box.hidden) { e.preventDefault(); close(); return; }
    var want = HD.tools && HD.tools.byKey ? HD.tools.byKey(k) : (k === 'v' ? 'move' : k === 'h' ? 'hand' : null);
    if (want === 'hand' || want === 'move') { e.preventDefault(); setTool(want); }
  });
  addEventListener('message', function (e) {
    var d = e.data; if (!d || typeof d !== 'object' || !M.docTab(tab)) return;
    var f = frame(); if (!f || e.source !== f.contentWindow) return;
    if (d.type === 'hd-pick-on') {
      answered[tab] = true;
      if (d.on && !(d.tokens > 0) && !(d.parts > 0)) { warnOnce('plain:' + tab, tab + ' 문서에 토큰 견본([data-var])도 부품 견본(.spec-stage)도 없어요 — 그냥 문서'); post(f, M.pickMsg(false)); }
    } else if (d.type === 'hd-sel' && d.doc) {
      if (tool !== 'move') return;
      var p = M.readPick(d);
      if (p) open(p); else close(true);
    } else if (d.type === 'hd-scroll' && d.doc) close(true);
    else if (d.type === 'hd-key' && d.doc && typeof d.key === 'string') {   // 문서 안에서 누른 캔버스 키(H·V·Esc·Ctrl+Z) — 셸 키 처리기들이 그대로 받게 다시 낸다
      document.dispatchEvent(new KeyboardEvent('keydown', {key: d.key, ctrlKey: !!d.ctrl, metaKey: !!d.meta, shiftKey: !!d.shift, bubbles: true, cancelable: true}));
    }
  });
  document.addEventListener('hd-css-changed', function (e) {   // 다른 탭·AI 가 tokens.css·components.css 를 고침(/api/files '@tokens'·'@components')
    var s = e.detail && e.detail.sheet === 'components' ? 'components' : 'tokens';
    reloadAll('a' + Date.now(), s);
    if (s === 'components' && part && pick) loadPart(pick, true);
  });

  return {tab: setTab, tool: setTool, current: function () { return {tab: tab, tool: tool, pick: pick}; }};
}

HD.feature('dsEdit', {needs: ['$', '$$', 'toast', 'warn', 'api', 'record'], mount: mount});
})();
