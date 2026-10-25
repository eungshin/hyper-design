/* View — 보낼 곳 고르기(#214): '#aichip' 칩(또는 옆 ▾)을 누르면 Paseo 에이전트 목록, 고르면 POST /api/attach — 칩은 view-sync 가 고친다('hd-agent' 의도).
   도우미가 없으면(ctx.api.on 거짓) 아무것도 만들지 않는다. 줄 규칙·제안은 HD.agents(Model).
   열 때마다 GET /api/agents → 줄마다 이름(40자) · 폴더 이름 · 상태 점, 지금 보낼 곳은 체크(aria-checked), 마지막 줄 '받는 곳 없음(대기열 파일만)'.
   도우미가 error 를 주면(Paseo 없음 등) 메뉴에 그 글. 고르기 실패 = 도우미의 한국어 까닭을 토스트, 칩은 그대로.
   자동: 열 때 보낼 곳이 없고(도우미 current 도 없음) HD.agents.suggest 가 하나를 찾으면 붙이고 토스트 — 붙어 있는 것은 바꾸지 않는다.
     사용자가 이 캔버스에서 '받는 곳 없음' 을 고르면 자동을 끈다(상태: ctx.local 키 ctx.key('hd-agent-off') = '1', 이 모듈만 — 에이전트를 고르면 지움).
   다른 자리의 칩(하단 대화창 받는 곳 칩, S1b)은 document 에 의도 'hd-agent-pick' {anchor} 를 보낸다 → 같은 메뉴를 그 칩 옆(아래 자리가 모자라면 위)에 연다,
     detail.done = true 로 받았음을 알린다. 열린 메뉴의 기준 칩에 aria-expanded.
   상태: 열린 메뉴·기준 칩 · 고르는 중(이 모듈만). HD.feature('agents', {needs: ['api', '$', 'esc', 'toast']}) → {open(), close(), auto() → Promise} | {} (도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#aichip{cursor:pointer}' +
  '#aibtn{border:0;background:none;color:#6b6b66;font-size:11px;padding:0 6px 0 0;cursor:pointer;margin-left:-4px}' +
  '#aibtn:hover,#aichip:hover{color:#2b2b28}' +
  '#amenu{min-width:300px;max-width:440px;max-height:60vh;overflow:auto}' +
  '#amenu .ag-row{min-height:36px;display:flex;align-items:center;gap:8px;padding:4px 10px;width:100%;text-align:left}' +
  '#amenu .ag-dot{flex:none;width:7px;height:7px;border-radius:50%;background:#b5b5b0}' +
  '#amenu .ag-row[data-status="running"] .ag-dot{background:var(--ui-ok, #7a9a7a)}' +
  '#amenu .ag-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#amenu .ag-dir{margin-left:auto;font-size:11.5px;color:#8a8a85;white-space:nowrap}' +
  '#amenu .ag-chk{flex:none;width:12px;font-size:12px}' +
  '#amenu .ag-row[aria-busy="true"]{cursor:progress;background:#F2F2EF}' +
  '#amenu .ag-none{border-top:1px solid #ececea;color:#6f6f6a}' +
  '#amenu .ag-msg{padding:8px 10px;font-size:13px;color:#6f6f6a;white-space:normal}';

function mount(ctx) {
  if (!ctx.api.on) return {};                       // file:// 또는 도우미 없음
  var $ = ctx.$, esc = ctx.esc, A = HD.agents;
  var chip = $('#aichip');
  if (!chip) throw new Error('보낼 곳 칩(#aichip)이 없어요');
  var offKey = ctx.key ? ctx.key('hd-agent-off') : null;

  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var btn = document.createElement('button');
  btn.type = 'button'; btn.id = 'aibtn'; btn.textContent = '▾'; btn.title = '보낼 곳(AI 터미널) 고르기';
  btn.setAttribute('aria-haspopup', 'menu'); btn.setAttribute('aria-expanded', 'false'); btn.setAttribute('aria-controls', 'amenu');
  chip.parentNode.insertBefore(btn, chip.nextSibling);
  var menu = document.createElement('div');
  menu.id = 'amenu'; menu.className = 'wm'; menu.setAttribute('role', 'menu'); menu.setAttribute('aria-label', '보낼 곳'); menu.hidden = true;
  document.body.appendChild(menu);

  var seq = 0, busy = false, anchor = btn;

  function place() {                                 // 기준 칩 아래(오른쪽 끝 맞춤), 아래 자리가 모자라면 위로
    var r = anchor.getBoundingClientRect(), h = menu.offsetHeight;
    menu.style.top = (r.bottom + 6 + h > innerHeight - 8 && r.top - 6 - h >= 8 ? r.top - 6 - h : r.bottom + 6) + 'px';
    menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, r.right - menu.offsetWidth)) + 'px';
  }
  function noneRow(cur) {
    return '<button type="button" class="wm-row ag-row ag-none" role="menuitemradio" data-id="" aria-checked="' + (cur ? 'false' : 'true') + '">' +
      '<span class="ag-chk">' + (cur ? '' : '✓') + '</span><span class="ag-name">받는 곳 없음(대기열 파일만)</span></button>';
  }
  function draw(r) {
    var head = r.error ? '<div class="ag-msg">' + esc(r.error) + '</div>' :
      !r.rows.length ? '<div class="ag-msg">떠 있는 Paseo 에이전트가 없어요</div>' : '';
    menu.innerHTML = head + r.rows.map(function (a) {
      return '<button type="button" class="wm-row ag-row" role="menuitemradio" data-id="' + esc(a.id) + '" data-name="' + esc(a.label) + '"' +
        ' data-status="' + esc(a.status) + '" aria-checked="' + (a.current ? 'true' : 'false') + '" title="' + esc(a.name + ' · ' + a.status + ' · ' + a.id) + '">' +
        '<span class="ag-chk">' + (a.current ? '✓' : '') + '</span><span class="ag-dot"></span>' +
        '<span class="ag-name">' + esc(a.label) + '</span><span class="ag-dir">' + esc(a.folder) + '</span></button>';
    }).join('') + noneRow(r.current);
    place();
  }
  function fetchRows() {
    return ctx.api.call('GET', '/api/agents').then(function (res) {
      if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      var r = A.rows(res.body);
      if (r.bad) console.warn('[hd] 보낼 곳 목록: 모양이 틀린 줄 ' + r.bad + '개를 뺐어요');
      return r;
    });
  }
  function load() {
    var my = ++seq;
    menu.innerHTML = '<div class="ag-msg">불러오는 중…</div>'; place();
    fetchRows().then(function (r) { if (my === seq && !menu.hidden) draw(r); }).catch(function (e) {
      if (my !== seq) return;
      var t = '보낼 곳 목록을 불러오지 못했어요 — ' + (e && e.message || e);
      menu.innerHTML = '<div class="ag-msg">' + esc(t) + '</div>'; place(); ctx.toast(t);
    });
  }
  function open(at) {
    if (anchor !== btn) anchor.setAttribute('aria-expanded', 'false');
    anchor = at || btn; menu.hidden = false; anchor.setAttribute('aria-expanded', 'true'); load();
  }
  function close() { seq++; menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); anchor.setAttribute('aria-expanded', 'false'); }

  // 보낼 곳 바꾸기 — 성공하면 칩에 의도('hd-agent'), 실패하면 도우미 까닭을 토스트(칩 그대로)
  function attach(id, name) {
    return ctx.api.call('POST', '/api/attach', {agent: id || null}).then(function (res) {
      if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      chip.dispatchEvent(new CustomEvent('hd-agent', {detail: {agent: res.body.agent || null, name: res.body.agent ? name : null}}));
      return res.body.agent || null;
    });
  }
  function choose(row) {
    if (busy) return;
    var id = row.dataset.id || null, name = row.dataset.name || null;
    busy = true; row.setAttribute('aria-busy', 'true');
    attach(id, name).then(function () {
      busy = false;
      if (offKey) { try { if (id) ctx.local.removeItem(offKey); else ctx.local.setItem(offKey, '1'); } catch (e) { /* 저장 실패 = 다음에 열 때 자동이 다시 고를 뿐 */ } }
      close();
      ctx.toast(id ? '보내기 → ' + name : '보내기 → 대기열 파일만(.hd-queue)');
    }).catch(function (e) {
      busy = false; row.removeAttribute('aria-busy');
      ctx.toast('보낼 곳을 바꾸지 못했어요 — ' + (e && e.message || e), false, 6000);
    });
  }

  // 자동: 붙은 것이 없고 이 저장소에 실행 중인 에이전트가 정확히 하나일 때만
  function auto() {
    if (window.__hdAgent) return Promise.resolve(null);
    var off = null;
    try { off = offKey && ctx.local.getItem(offKey); } catch (e) { /* 못 읽으면 꺼지지 않은 것으로 */ }
    if (off === '1') return Promise.resolve(null);
    return ctx.api.call('GET', '/api/agents?auto=1').then(function (res) {   // 붙어 있거나 저장소를 모르면 도우미가 paseo 를 띄우지 않는다
      if (res.status !== 200 || !res.body || res.body.current || res.body.skipped || window.__hdAgent) return null;
      if (res.body.error) { console.warn('[hd] 보낼 곳 자동 고르기: ' + res.body.error); return null; }
      var s = A.suggest(Array.isArray(res.body.agents) ? res.body.agents : [], res.body.repo), name = s && A.label(s);
      if (!s) return null;
      return attach(s.id, name).then(function () { ctx.toast('보내기 → ' + name + ' (바꾸려면 칩을 누르세요)', false, 6000); return s.id; });
    }).catch(function (e) {
      ctx.toast('보낼 곳을 자동으로 고르지 못했어요 — ' + (e && e.message || e));
      return null;
    });
  }

  function toggle(at) { at = at || btn; if (menu.hidden || anchor !== at) open(at); else close(); }
  btn.addEventListener('click', function () { toggle(btn); });
  chip.addEventListener('click', function () { toggle(btn); });
  document.addEventListener('hd-agent-pick', function (e) {   // 다른 자리의 받는 곳 칩(대화창) — 같은 메뉴를 그 옆에
    var d = e.detail || {}; if (!d.anchor || !d.anchor.getBoundingClientRect) return;
    d.done = true; toggle(d.anchor);
  });
  menu.addEventListener('click', function (e) {
    var b = e.target.closest('button.ag-row');
    if (b) choose(b);
  });
  document.addEventListener('pointerdown', function (e) {
    var t = e.target; if (menu.hidden || !t.closest || t.closest('#amenu, #aibtn, #aichip') || anchor.contains(t)) return;
    close();
  }, true);
  addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) close(); });
  var first = auto();
  return {open: open, close: close, auto: function () { return first; }};
}

HD.viewAgents = {mount: mount};
HD.feature('agents', {needs: ['api', '$', 'esc', 'toast', 'local', 'key'], mount: mount});
})();
