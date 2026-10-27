/* View — 카드(아트보드) 크기(task 46): 카드마다 크기 상태(card-size)의 주인 · 판 카드에 크기 입히기 · 새 화면 대화상자 · 고른 카드 크기 팝오버.
   규칙(프리셋·검사·최근·내 프리셋)은 modules/artboard.js(Model). 크기를 바꾸면 카드 틀·iframe·핀 배율·선·맞추기·크게 보기가 그 크기를 따른다(셸이 of(id) 를 읽는다).
   상태: 카드 크기 맵 = 프로젝트 키 hd-card-size:<hash>(상태 파일 이름 card-size, 되돌리기 TRACK) · 최근 크기·내 프리셋 = 전역 키 hd-artboard(파일로 가지 않음).
   HD.viewArtboard.mount(ctx) → {attach(shell) → api}
     ctx = 기능 등록부 공통 칸 $ · $$ · esc · toast · warn · rowsEl · CARD · store · local · key · record
     shell = {changed(ids) — 크기가 바뀐 뒤 선·선택 막대·실을 카드 다시, guard(ids) → 바꿀 수 있는 id(잠긴 카드는 셸이 알리고 뺌)}
     api = {of(id) → {w, h, preset?, custom}, paint(ids?), reload(), apply(ids, size|null), map(), put(map), seed(id, size), label(ids), sizes(ids?) → {id: 'W×H(프리셋)'}(기본 아닌 카드만),
            openNew(done(size, name)) — 새 화면 대화상자(만들기 = done, 취소 = 아무것도), popover(ids, anchorEl), close() → 닫은 것이 있었나, closePop(), isOpen()} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS =
  '.ab-back{position:fixed;inset:0;z-index:60;background:rgba(20,20,18,.32);display:grid;place-items:center}.ab-back[hidden]{display:none}' +
  '.ab-dlg{width:min(860px,calc(100vw - 32px));max-height:calc(100vh - 48px);display:flex;flex-direction:column;background:#fff;color:var(--ui-primary,#2b2b29);border-radius:12px;box-shadow:0 18px 48px rgba(0,0,0,.24);font:13px system-ui,sans-serif;overflow:hidden}' +
  '.ab-head{padding:14px 18px;border-bottom:1px solid var(--ui-line,#e6e6e2);font-size:15px;font-weight:700}' +
  '.ab-body{display:grid;grid-template-columns:150px minmax(0,1fr) 240px;min-height:0;flex:1}' +
  '.ab-cats{display:flex;flex-direction:column;gap:2px;padding:10px;border-right:1px solid var(--ui-line,#e6e6e2);background:#fafaf8}' +
  '.ab-cat{border:0;background:none;text-align:left;padding:8px 10px;border-radius:7px;font:inherit;color:inherit;cursor:pointer}' +
  '.ab-cat:hover{background:#efefeb}.ab-cat[aria-selected="true"]{background:var(--ui-primary,#2b2b29);color:#fff;font-weight:600}' +
  '.ab-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:10px;padding:14px;overflow:auto;align-content:start}' +
  '.ab-card{display:flex;flex-direction:column;align-items:center;gap:6px;border:1px solid var(--ui-line,#e3e3df);background:#fff;border-radius:9px;padding:12px 8px;cursor:pointer;font:inherit;color:inherit}' +
  '.ab-card:hover{border-color:#bdbdb6}.ab-card[aria-selected="true"]{border-color:var(--ui-primary,#2b2b29);box-shadow:0 0 0 1px var(--ui-primary,#2b2b29)}' +
  '.ab-thumb{display:block;border:1.5px solid #8a8d86;border-radius:3px;background:#f4f4f1}' +
  '.ab-card b{font-weight:600;font-size:12.5px;text-align:center}.ab-card span.ab-wh{color:#77776f;font:12px ui-monospace,Menlo,monospace}' +
  '.ab-empty{grid-column:1/-1;color:#999;margin:8px 2px}' +
  '.ab-det{display:flex;flex-direction:column;gap:10px;padding:14px;border-left:1px solid var(--ui-line,#e6e6e2);background:#fafaf8}' +
  '.ab-det h4{margin:0;font-size:12px;color:#77776f;font-weight:600}' +
  '.ab-f{display:flex;flex-direction:column;gap:4px;font-size:12px;color:#55554f}' +
  '.ab-f input{width:100%;box-sizing:border-box;font:13px system-ui,sans-serif;border:1px solid var(--ui-line,#d6d6d0);border-radius:6px;padding:6px 8px;color:var(--ui-primary,#2b2b29);background:#fff;min-width:0}' +
  '.ab-f input[aria-invalid="true"]{border-color:var(--ui-danger,#c8463f)}' +
  '.ab-wh2{display:grid;grid-template-columns:1fr 1fr;gap:8px}.ab-num{font-family:ui-monospace,Menlo,monospace !important}' +
  '.ab-seg{display:flex;border:1px solid var(--ui-line,#d6d6d0);border-radius:7px;overflow:hidden}' +
  '.ab-seg button{flex:1;border:0;background:#fff;padding:6px 0;font:inherit;color:inherit;cursor:pointer}.ab-seg button[aria-pressed="true"]{background:var(--ui-primary,#2b2b29);color:#fff}' +
  '.ab-err{margin:0;min-height:16px;color:var(--ui-danger,#c8463f);font-size:12px;line-height:1.35}' +
  '.ab-save{display:flex;gap:6px}.ab-save[hidden]{display:none}.ab-save input{flex:1}' +
  '.ab-link{border:0;background:none;padding:0;color:var(--ui-primary,#2b2b29);text-decoration:underline;font:12px system-ui,sans-serif;cursor:pointer;align-self:flex-start}' +
  '.ab-foot{display:flex;justify-content:flex-end;gap:8px;padding:12px 18px;border-top:1px solid var(--ui-line,#e6e6e2)}' +
  '.ab-btn{border:1px solid var(--ui-line,#d6d6d0);background:#fff;color:var(--ui-primary,#2b2b29);border-radius:7px;padding:7px 16px;font:600 13px system-ui,sans-serif;cursor:pointer}' +
  '.ab-btn.pri{background:var(--ui-primary,#2b2b29);border-color:var(--ui-primary,#2b2b29);color:#fff}' +
  '#abPop{position:fixed;z-index:40;width:268px;max-height:min(460px,calc(100vh - 80px));display:flex;flex-direction:column;background:#1c1c1c;color:#f2f2ef;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.32);font:12.5px system-ui,sans-serif;overflow:hidden}' +
  '#abPop[hidden]{display:none}' +
  '#abPop .abp-top{display:flex;align-items:center;gap:6px;padding:10px 10px 4px}' +
  '#abPop label{display:flex;align-items:center;gap:4px;color:#a9a9a3}' +
  '#abPop input{width:58px;background:#2c2c2a;border:1px solid #3d3d3a;color:#fff;border-radius:5px;padding:4px 6px;font:12.5px ui-monospace,Menlo,monospace}' +
  '#abPop input[aria-invalid="true"]{border-color:var(--ui-danger,#c8463f)}' +
  '#abPop .abp-ib{border:0;background:none;color:#fff;border-radius:6px;width:28px;height:28px;display:grid;place-items:center;cursor:pointer;margin-left:auto}' +
  '#abPop .abp-ib:hover,#abPop .abp-row:hover,#abPop .abp-foot button:hover{background:#3a3a3a}' +
  '#abPop svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}' +
  '#abPop .ab-err{padding:0 10px;color:#ff8a80}' +
  '#abPop .abp-list{overflow:auto;padding:2px 4px 6px;border-top:1px solid #333}' +
  '#abPop .abp-h{margin:8px 6px 2px;color:#8f8f88;font-size:11px;font-weight:600}' +
  '#abPop .abp-row{display:flex;justify-content:space-between;width:100%;border:0;background:none;color:inherit;padding:5px 6px;border-radius:5px;font:inherit;cursor:pointer;text-align:left}' +
  '#abPop .abp-row span{color:#a9a9a3;font:12px ui-monospace,Menlo,monospace}#abPop .abp-row[aria-current="true"]{background:#33332f;font-weight:600}' +
  '#abPop .abp-foot{display:flex;gap:4px;padding:6px;border-top:1px solid #333}' +
  '#abPop .abp-foot button{flex:1;border:0;background:none;color:#fff;border-radius:6px;padding:6px;font:inherit;cursor:pointer}' +
  '#abPop .abp-foot button.pri{background:#f2f2ef;color:#1c1c1c;font-weight:600}' +
  '.card.ab-now .phone{transition:none !important}' +
  '#selbar .ab-size{font:400 11px system-ui,sans-serif;color:#6b6b66;padding:5px 6px;font-variant-numeric:tabular-nums}';   // R27 F06: 크기는 메타 — 11px 회색 글(막대 끝)

var SWAP_SVG = '<svg viewBox="0 0 24 24"><path d="M7 4v13M3 13l4 4 4-4"/><path d="M17 20V7M13 11l4-4 4 4"/></svg>';

function mount(ctx) {
  var A = HD.artboard, $ = ctx.$, $$ = ctx.$$, esc = ctx.esc, DEF = {w: ctx.CARD.w, h: ctx.CARD.h};
  var KEY = ctx.key('hd-card-size'), PKEY = 'hd-artboard';
  var sizes = {}, sh = {changed: function () {}, guard: function (ids) { return ids; }};

  (function () { var st = document.createElement('style'); st.id = 'hd-artboard-css'; st.textContent = CSS; document.head.appendChild(st); })();

  function load() {
    var t = null; try { t = ctx.store.getItem(KEY); } catch (e) { t = null; }   // 저장소를 못 읽으면 기본 크기
    var raw = null;
    if (t != null) { try { raw = JSON.parse(t); } catch (e) { ctx.warn('[hd] card-size 저장값이 깨져 기본 크기로 둬요'); raw = null; } }
    var n = A.norm(raw);
    if (n.bad.length) ctx.warn('[hd] card-size 의 깨진 항목을 버렸어요: ' + n.bad.join(', '));
    sizes = n.sizes;
  }
  function save() {
    try { if (Object.keys(sizes).length) ctx.store.setItem(KEY, JSON.stringify(sizes)); else ctx.store.removeItem(KEY); }
    catch (e) { ctx.toast('카드 크기를 저장하지 못했어요 — 새로고침하면 사라질 수 있어요'); }
  }
  function prefs() { var t = null; try { t = ctx.local.getItem(PKEY); } catch (e) { t = null; } var r = null; try { r = t ? JSON.parse(t) : null; } catch (e) { ctx.warn('[hd] hd-artboard 설정이 깨져 비웠어요'); } return A.prefs(r); }
  function savePrefs(p) { try { ctx.local.setItem(PKEY, JSON.stringify(p)); } catch (e) {} }   // 최근·내 프리셋은 편의 — 못 써도 크기 바꾸기는 그대로
  function remember(size) { var p = prefs(); p.recent = A.pushRecent(p.recent, size); savePrefs(p); }

  function of(id) { return A.of(sizes, id, DEF); }
  function paint(ids) {                              // 바로(펼치기 움직임 없이) — 선·맞추기가 같은 프레임에 새 크기를 잰다
    $$('.card', ctx.rowsEl).forEach(function (c) {
      if (ids && ids.indexOf(c.dataset.id) < 0) return;
      var s = of(c.dataset.id), was = c.dataset.size || '';
      if (was === (s.custom ? A.label(s) : '')) return;
      c.classList.add('ab-now'); void c.offsetWidth;
      if (s.custom) { c.style.setProperty('--card-w', s.w + 'px'); c.style.setProperty('--card-h', s.h + 'px'); c.dataset.size = A.label(s); }
      else { c.style.removeProperty('--card-w'); c.style.removeProperty('--card-h'); delete c.dataset.size; }
      void c.offsetWidth; c.classList.remove('ab-now');
    });
  }
  function put(m, ids) { sizes = m; save(); paint(); sh.changed(ids || null); }
  function apply(ids, size) {                        // 고른 카드 모두에(왼쪽 위 그대로 — 카드 자리 = 줄 자리 + 옮긴 거리) · 되돌리기 한 단계
    ids = sh.guard(ids || []); if (!ids.length) return false;
    var before = sizes, after = A.set(sizes, ids, size, DEF);
    if (JSON.stringify(before) === JSON.stringify(after)) return false;
    put(after, ids);
    if (size) remember(size);
    var s = size ? A.full(size) : '기본 크기';
    ctx.record({label: (ids.length > 1 ? '카드 ' + ids.length + '장 크기: ' : '카드 크기: ') + s,
                undo: function () { put(before, ids); }, redo: function () { put(after, ids); }});
    return true;
  }
  function label(ids) { var c = A.common(sizes, ids, DEF); return c ? A.label(c) : '여러 크기'; }
  function requestSizes(ids) {
    var o = {};
    Object.keys(sizes).forEach(function (id) { if (!ids || ids.indexOf(id) >= 0) o[id] = A.full(of(id)); });
    return o;
  }

  // 숫자 칸 공통: 화살표 ±1 · Shift ±10 · Enter = ok() · Esc = 닫기
  function numKeys(inp, ok, close) {
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { var v = A.nudge(inp.value, e.key, e.shiftKey); if (v != null) { e.preventDefault(); inp.value = v; inp.dispatchEvent(new Event('input')); } }
      else if (e.key === 'Enter') { e.preventDefault(); ok(); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); }
    });
  }

  /* ---------- 새 화면 대화상자(Photoshop 새 문서) ---------- */
  var dlg = null, dl = null;                          // dl = {cat, w, h, preset, done}
  function buildDlg() {
    dlg = document.createElement('div'); dlg.className = 'ab-back'; dlg.id = 'abNew'; dlg.hidden = true;
    dlg.innerHTML = '<div class="ab-dlg" role="dialog" aria-modal="true" aria-labelledby="abNewT">' +
      '<div class="ab-head" id="abNewT">새 화면</div>' +
      '<div class="ab-body"><div class="ab-cats" role="tablist" aria-label="크기 묶음"></div><div class="ab-grid" role="listbox" aria-label="프리셋"></div>' +
      '<div class="ab-det"><h4>프리셋 상세</h4>' +
      '<label class="ab-f">이름<input id="abName" maxlength="60"></label>' +
      '<div class="ab-wh2"><label class="ab-f">너비 (px)<input id="abW" class="ab-num" inputmode="numeric"></label><label class="ab-f">높이 (px)<input id="abH" class="ab-num" inputmode="numeric"></label></div>' +
      '<div class="ab-f">방향<div class="ab-seg" role="group" aria-label="방향"><button type="button" data-o="portrait">세로</button><button type="button" data-o="landscape">가로</button></div></div>' +
      '<p class="ab-err" id="abErr" role="alert"></p>' +
      '<button type="button" class="ab-link" id="abSaveOpen">프리셋으로 저장</button>' +
      '<div class="ab-save" id="abSaveRow" hidden><label class="ab-f" style="flex:1">프리셋 이름<input id="abPName" maxlength="40"></label><button type="button" class="ab-btn" id="abSave" style="align-self:flex-end">저장</button></div>' +
      '</div></div>' +
      '<div class="ab-foot"><button type="button" class="ab-btn" id="abCancel">취소</button><button type="button" class="ab-btn pri" id="abMake">만들기</button></div></div>';
    document.body.appendChild(dlg);
    dlg.addEventListener('click', function (e) {
      if (e.target === dlg) { closeDlg(); return; }
      var cat = e.target.closest('.ab-cat'); if (cat) { dl.cat = cat.dataset.cat; renderDlg(); return; }
      var card = e.target.closest('.ab-card'); if (card) { pick(+card.dataset.w, +card.dataset.h, card.dataset.name); if (e.detail >= 2) make(); return; }
      var o = e.target.closest('.ab-seg button'); if (o) { var c = readWH(); if (c.ok && A.orient(c) !== o.dataset.o) { var s = A.swap(c, prefs().saved); pick(s.w, s.h, s.preset || ''); } return; }
    });
    $('#abCancel', dlg).addEventListener('click', closeDlg);
    $('#abMake', dlg).addEventListener('click', make);
    $('#abSaveOpen', dlg).addEventListener('click', function () { var r = $('#abSaveRow', dlg); r.hidden = false; $('#abPName', dlg).value = dl.preset && !A.presetOf(dl.w, dl.h) ? dl.preset : ''; $('#abPName', dlg).focus(); });
    $('#abSave', dlg).addEventListener('click', savePreset);
    $('#abPName', dlg).addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); savePreset(); } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeDlg(); } });
    ['abW', 'abH'].forEach(function (k) {
      var inp = $('#' + k, dlg);
      numKeys(inp, make, closeDlg);
      inp.addEventListener('input', function () { var c = readWH(); err(c.ok ? '' : c.error, c); if (c.ok) { dl.w = c.w; dl.h = c.h; dl.preset = A.presetOf(c.w, c.h, prefs().saved); marks(); } });
    });
    $('#abName', dlg).addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); make(); } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeDlg(); } });
    dlg.addEventListener('keydown', function (e) {    // Esc = 취소 · Enter = 만들기(프리셋 카드에서는 그 카드로) — 칸 안 Enter 는 칸이 이미 처리
      e.stopPropagation();                           // 판 단축키(도구 키·Del·0)가 대화상자 뒤에서 돌지 않게
      if (e.defaultPrevented) return;
      if (e.key === 'Escape') { e.preventDefault(); closeDlg(); return; }
      if (e.key !== 'Enter') return;
      var t = e.target, card = t.closest && t.closest('.ab-card');
      if (!card && t.closest && t.closest('.ab-cat, .ab-seg, #abCancel, #abSaveOpen, #abSave')) return;   // 그 단추 그대로
      e.preventDefault(); e.stopPropagation();
      if (card) pick(+card.dataset.w, +card.dataset.h, card.dataset.name);
      make();
    });
  }
  function readWH() { return A.check($('#abW', dlg).value, $('#abH', dlg).value); }
  function err(msg, c) {
    $('#abErr', dlg).textContent = msg || '';
    var bad = msg && /너비/.test(msg) ? 'abW' : msg && /높이/.test(msg) ? 'abH' : '';
    ['abW', 'abH'].forEach(function (k) { $('#' + k, dlg).setAttribute('aria-invalid', String(k === bad)); });
  }
  function pick(w, h, name) {
    dl.w = w; dl.h = h; dl.preset = name || A.presetOf(w, h, prefs().saved);
    $('#abW', dlg).value = w; $('#abH', dlg).value = h; err('');
    marks();
  }
  function marks() {
    $$('.ab-card', dlg).forEach(function (c) { c.setAttribute('aria-selected', String(+c.dataset.w === dl.w && +c.dataset.h === dl.h)); });
    $$('.ab-seg button', dlg).forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.o === A.orient(dl))); });
  }
  function thumb(w, h) { var k = 46 / Math.max(w, h); return '<span class="ab-thumb" style="width:' + Math.max(8, Math.round(w * k)) + 'px;height:' + Math.max(8, Math.round(h * k)) + 'px"></span>'; }
  function renderDlg() {
    var pf = prefs();
    $('.ab-cats', dlg).innerHTML = A.CATS.map(function (c) {
      return '<button type="button" class="ab-cat" role="tab" data-cat="' + c.id + '" aria-selected="' + (c.id === dl.cat) + '">' + esc(c.name) + '</button>';
    }).join('');
    var items = A.list(dl.cat, pf);
    $('.ab-grid', dlg).innerHTML = items.length ? items.map(function (p) {
      return '<button type="button" class="ab-card" role="option" data-w="' + p.w + '" data-h="' + p.h + '" data-name="' + esc(p.name) + '">' + thumb(p.w, p.h) +
        '<b>' + esc(p.name) + '</b><span class="ab-wh">' + p.w + ' × ' + p.h + '</span></button>';
    }).join('') : '<p class="ab-empty">' + (dl.cat === 'recent' ? '아직 쓴 크기가 없어요' : '저장한 프리셋이 없어요 — 오른쪽 [프리셋으로 저장]') + '</p>';
    marks();
  }
  function savePreset() {
    var c = readWH(); if (!c.ok) { err(c.error, c); return; }
    var p = prefs(), r = A.savePreset(p.saved, $('#abPName', dlg).value, c.w, c.h);
    if (!r.ok) { err(r.error); $('#abPName', dlg).focus(); return; }
    p.saved = r.saved; savePrefs(p);
    $('#abSaveRow', dlg).hidden = true; dl.cat = 'saved'; dl.preset = $('#abPName', dlg).value.trim(); renderDlg();
    ctx.toast('프리셋 "' + dl.preset + '"을 저장했어요');
  }
  function make() {
    var c = readWH(); if (!c.ok) { err(c.error, c); $('#' + (/높이/.test(c.error) ? 'abH' : 'abW'), dlg).focus(); return; }
    var name = $('#abName', dlg).value.trim() || '빈 레이아웃', size = {w: c.w, h: c.h}, pr = A.presetOf(c.w, c.h, prefs().saved), done = dl.done;
    if (pr) size.preset = pr;
    closeDlg();
    remember(size);
    done(size, name);
  }
  function catOf(w, h) { var p = A.PRESETS.filter(function (x) { return x.w === w && x.h === h; })[0]; return p ? p.cat : 'mobile'; }
  function openNew(done) {
    if (!dlg) buildDlg();
    closePop();
    dl = {cat: catOf(DEF.w, DEF.h), w: DEF.w, h: DEF.h, preset: '', done: done, back: document.activeElement};
    $('#abName', dlg).value = '빈 레이아웃'; $('#abSaveRow', dlg).hidden = true;
    renderDlg(); pick(DEF.w, DEF.h);
    dlg.hidden = false;
    var sel = $('.ab-card[aria-selected="true"]', dlg); (sel || $('#abW', dlg)).focus();
  }
  function closeDlg() {                             // 닫으면 연 자리로 초점(판 단축키가 다시 판에 닿게)
    if (!dlg || dlg.hidden) return false;
    var back = dl && dl.back; dlg.hidden = true; dl = null;
    if (dlg.contains(document.activeElement)) { if (back && back.isConnected && back !== document.body) back.focus(); else document.activeElement.blur(); }
    return true;
  }

  /* ---------- 고른 카드 크기 팝오버(Figma 오른쪽 패널 · Illustrator 컨트롤 막대) ---------- */
  var pop = null, pp = null;                          // pp = {ids, anchor}
  function buildPop() {
    pop = document.createElement('div'); pop.id = 'abPop'; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', '카드 크기');
    pop.innerHTML = '<div class="abp-top"><label>W<input id="abPW" inputmode="numeric" aria-label="너비(px)"></label><label>H<input id="abPH" inputmode="numeric" aria-label="높이(px)"></label>' +
      '<button type="button" class="abp-ib" id="abPSwap" title="가로·세로 바꾸기" aria-label="가로·세로 바꾸기">' + SWAP_SVG + '</button></div>' +
      '<p class="ab-err" id="abPErr" role="alert"></p><div class="abp-list" role="listbox" aria-label="프리셋"></div>' +
      '<div class="abp-foot"><button type="button" id="abPDef"></button><button type="button" class="pri" id="abPOk">적용</button></div>';
    document.body.appendChild(pop);
    pop.addEventListener('click', function (e) {
      var r = e.target.closest('.abp-row'); if (r) { var s = {w: +r.dataset.w, h: +r.dataset.h}; if (r.dataset.name) s.preset = r.dataset.name; apply(pp.ids, s); closePop(); }
    });
    $('#abPSwap', pop).addEventListener('click', function () { var c = popWH(); if (!c.ok) return; apply(pp.ids, A.swap(c, prefs().saved)); fillPop(); });
    $('#abPDef', pop).addEventListener('click', function () { apply(pp.ids, null); closePop(); });
    $('#abPOk', pop).addEventListener('click', popOk);
    ['abPW', 'abPH'].forEach(function (k) {
      var inp = $('#' + k, pop);
      numKeys(inp, popOk, closePop);
      inp.addEventListener('input', function () { var c = popWH(); popErr(c.ok ? '' : c.error); });
    });
    pop.addEventListener('keydown', function (e) { e.stopPropagation(); if (e.key === 'Escape') { e.preventDefault(); closePop(); } });   // 판 단축키가 팝오버 뒤에서 돌지 않게
    document.addEventListener('pointerdown', function (e) {   // 바깥 누르기 = 닫기(크기 단추는 다시 누르면 닫힘 — 셸이 popover 를 다시 부름)
      if (!pop.hidden && !pop.contains(e.target) && !(pp && pp.anchor && pp.anchor.contains(e.target))) closePop();
    }, true);
  }
  function popWH() { return A.check($('#abPW', pop).value, $('#abPH', pop).value); }
  function popErr(msg) {
    $('#abPErr', pop).textContent = msg || '';
    var bad = msg && /너비/.test(msg) ? 'abPW' : msg && /높이/.test(msg) ? 'abPH' : '';
    ['abPW', 'abPH'].forEach(function (k) { $('#' + k, pop).setAttribute('aria-invalid', String(k === bad)); });
  }
  function popOk() {
    var c = popWH(); if (!c.ok) { popErr(c.error); return; }
    var s = {w: c.w, h: c.h}, pr = A.presetOf(c.w, c.h, prefs().saved); if (pr) s.preset = pr;
    apply(pp.ids, s); closePop();
  }
  function fillPop() {
    var c = A.common(sizes, pp.ids, DEF), pf = prefs();
    $('#abPW', pop).value = c ? c.w : ''; $('#abPH', pop).value = c ? c.h : ''; popErr('');
    $('#abPDef', pop).textContent = '기본 크기로 (' + A.label(DEF) + ')';
    var cats = A.CATS.filter(function (k) { return A.list(k.id, pf).length; });
    $('.abp-list', pop).innerHTML = cats.map(function (k) {
      return '<p class="abp-h">' + esc(k.name) + '</p>' + A.list(k.id, pf).map(function (p) {
        var cur = !!c && c.w === p.w && c.h === p.h;
        return '<button type="button" class="abp-row" role="option" data-w="' + p.w + '" data-h="' + p.h + '" data-name="' + esc(p.name === A.label(p) ? '' : p.name) + '" aria-current="' + cur + '">' +
          esc(p.name) + '<span>' + p.w + '×' + p.h + '</span></button>';
      }).join('');
    }).join('');
  }
  function placePop() {
    var r = pp.anchor.getBoundingClientRect(), w = 268, x = Math.min(innerWidth - w - 8, Math.max(8, r.left + r.width / 2 - w / 2));
    pop.style.left = x + 'px';
    var below = r.bottom + 8, h = pop.offsetHeight || 300;
    pop.style.top = (below + h > innerHeight - 8 ? Math.max(8, r.top - h - 8) : below) + 'px';
  }
  function popover(ids, anchor) {
    if (!pop) buildPop();
    if (!pop.hidden && pp && pp.anchor === anchor) { closePop(); return; }   // 같은 단추 다시 = 닫기
    pp = {ids: ids.slice(), anchor: anchor};
    fillPop(); pop.hidden = false; placePop();
    anchor.setAttribute('aria-expanded', 'true');
    var i = $('#abPW', pop); i.focus(); i.select();
  }
  function closePop() {                             // 닫으면 크기 단추로 초점(Esc·0 같은 판 키가 바로 닿게)
    if (!pop || pop.hidden) return false;
    var inside = pop.contains(document.activeElement); pop.hidden = true;
    if (pp && pp.anchor) { pp.anchor.setAttribute('aria-expanded', 'false'); if (inside && pp.anchor.isConnected && pp.anchor.offsetParent) pp.anchor.focus(); else if (inside) document.activeElement.blur(); }
    pp = null; return true;
  }

  load();
  return {attach: function (shell) {
    sh = {changed: shell.changed || sh.changed, guard: shell.guard || sh.guard};
    paint();
    return {of: of, paint: paint, reload: function () { load(); paint(); sh.changed(null); }, apply: apply, label: label, sizes: requestSizes,
            map: function () { return JSON.parse(JSON.stringify(sizes)); }, put: function (m) { put(A.norm(m).sizes); },
            seed: function (id, size) { sizes = A.set(sizes, [id], size, DEF); save(); paint([id]); sh.changed([id]); },   // 막 만든 카드(새 화면·복제) — 기록 없이(카드 만들기가 한 단계)
            openNew: openNew, popover: popover, close: function () { return closeDlg() || closePop(); }, closePop: closePop,
            isOpen: function () { return !!(dlg && !dlg.hidden) || !!(pop && !pop.hidden); }};
  }};
}

HD.viewArtboard = {mount: mount, CSS: CSS};
HD.feature('artboard', {needs: ['$', '$$', 'esc', 'toast', 'warn', 'rowsEl', 'CARD', 'store', 'local', 'key', 'record'], mount: mount});
})();
