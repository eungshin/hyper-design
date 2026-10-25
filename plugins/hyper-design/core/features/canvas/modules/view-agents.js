/* View — 보낼 곳 고르기(#214): '#aichip' 칩(또는 옆 ▾)을 누르면 Paseo 에이전트 목록, 고르면 POST /api/attach — 칩은 view-sync 가 고친다('hd-agent' 의도).
   도우미가 없으면(ctx.api.on 거짓) 아무것도 만들지 않는다. 줄 규칙·제안은 HD.agents(Model).
   열 때마다 GET /api/agents → 줄마다 이름(40자) · 폴더 이름 · 상태 점, 지금 보낼 곳은 체크(aria-checked), 마지막 줄 '받는 곳 없음(대기열 파일만)'.
   도우미가 error 를 주면(Paseo 없음 등) 메뉴에 그 글. 고르기 실패 = 도우미의 한국어 까닭을 토스트, 칩은 그대로.
   자동: 열 때 보낼 곳이 없고(도우미 current 도 없음) HD.agents.suggest 가 하나를 찾으면 붙이고 토스트 — 붙어 있는 것은 바꾸지 않는다.
     사용자가 이 캔버스에서 '받는 곳 없음' 을 고르면 자동을 끈다(상태: ctx.local 키 ctx.key('hd-agent-off') = '1', 이 모듈만 — 에이전트를 고르면 지움).
   다른 자리의 칩(하단 대화창 받는 곳 칩, S1b)은 document 에 의도 'hd-agent-pick' {anchor} 를 보낸다 → 같은 메뉴를 그 칩 옆(아래 자리가 모자라면 위)에 연다,
     detail.done = true 로 받았음을 알린다. 열린 메뉴의 기준 칩에 aria-expanded.
   받는 곳 메뉴(47-5b, 규칙 HD.agents.menu): 위에서 아래로 '접속한 에이전트'(점 초록 = 접속 중 · 회색 = 자리 비움, 종류 · 진행 글) → 'Paseo 터미널' 줄 →
     목록에 없는 지금 받는 곳(예전에 붙인 것) → '받는 곳 없음(대기열 파일만)' → '＋ 새 터미널…'(.ag-spawn). 접속한 에이전트를 골라도 같은 /api/attach(서버가 이벤트로 보냄).
     새 터미널 = document 의도 'hd-spawn-ask' {repo} 만 보낸다(확인 창·부르기는 view-spawn) — 받는 쪽이 없으면 [hd] 경고 + 토스트.
     대화창 알약에서 열면 메뉴 왼쪽 끝을 알약 왼쪽에 맞춘다(Claude·ChatGPT 고르기 메뉴처럼), 위쪽 칩이면 지금처럼 오른쪽 끝.
   상태: 열린 메뉴·기준 칩 · 고르는 중 · 마지막 저장소(이 모듈만). HD.feature('agents', {needs: ['api', '$', 'esc', 'toast']}) → {open(), close(), auto() → Promise} | {} (도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '#aichip{cursor:pointer}' +
  '#aibtn{border:0;background:none;color:#6b6b66;font-size:11px;padding:0 6px 0 0;cursor:pointer;margin-left:-4px}' +
  '#aibtn:hover,#aichip:hover{color:#2b2b28}' +
  '#amenu{min-width:300px;max-width:440px;max-height:60vh;overflow:auto}' +
  '#amenu .ag-row{min-height:36px;display:flex;align-items:center;gap:8px;padding:4px 10px;width:100%;text-align:left}' +
  '#amenu .ag-dot{flex:none;width:7px;height:7px;border-radius:50%;background:#b5b5b0}' +
  '#amenu .ag-row[data-status="running"] .ag-dot,#amenu .ag-row[data-state="here"] .ag-dot{background:var(--ui-ok, #7a9a7a)}' +
  '#amenu .ag-sec{padding:6px 10px 2px;font-size:11px;font-weight:600;color:#8a8a85}' +
  '#amenu .ag-sub{display:block;font-size:11.5px;color:#8a8a85;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
  '#amenu .ag-txt{min-width:0;display:flex;flex-direction:column}' +
  '#amenu .ag-spawn{border-top:1px solid #ececea;color:#2b2b28}' +
  '#amenu .ag-spawn .ag-plus{flex:none;width:12px;text-align:center;font-size:14px;color:#6f6f6a}' +
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

  var seq = 0, busy = false, anchor = btn, repo = null;

  function place() {                                 // 기준 칩 아래(오른쪽 끝 맞춤), 아래 자리가 모자라면 위로
    var r = anchor.getBoundingClientRect(), h = menu.offsetHeight;
    menu.style.top = (r.bottom + 6 + h > innerHeight - 8 && r.top - 6 - h >= 8 ? r.top - 6 - h : r.bottom + 6) + 'px';
    var x = anchor === btn ? r.right - menu.offsetWidth : r.left;   // 대화창 알약 = 왼쪽 끝 맞춤(그 위로 펼침)
    menu.style.left = Math.max(8, Math.min(innerWidth - menu.offsetWidth - 8, x)) + 'px';
  }
  function noneRow(cur) {
    return '<button type="button" class="wm-row ag-row ag-none" role="menuitemradio" data-id="" aria-checked="' + (cur ? 'false' : 'true') + '">' +
      '<span class="ag-chk">' + (cur ? '' : '✓') + '</span><span class="ag-name">받는 곳 없음(대기열 파일만)</span></button>';
  }
  function check(on) { return ' aria-checked="' + (on ? 'true' : 'false') + '"><span class="ag-chk">' + (on ? '✓' : '') + '</span>'; }
  function draw(r) {
    var h = '';
    if (r.connected.length) {
      h += '<div class="ag-sec" role="presentation">접속한 에이전트</div>' + r.connected.map(function (a) {
        var sub = a.stateSay + ' · ' + a.kindSay + (a.state === 'here' && a.progress ? ' · ' + a.progress : '');
        return '<button type="button" class="wm-row ag-row ag-conn" role="menuitemradio" data-id="' + esc(a.id) + '" data-name="' + esc(a.label) + '" data-state="' + a.state + '"' +
          ' title="' + esc(a.name + ' · ' + sub + ' · ' + a.id) + '"' + check(a.current) + '<span class="ag-dot"></span>' +
          '<span class="ag-txt"><span class="ag-name">' + esc(a.label) + '</span><span class="ag-sub">' + esc(sub) + '</span></span></button>';
      }).join('');
    }
    if (r.rows.length) {
      if (r.connected.length) h += '<div class="ag-sec" role="presentation">Paseo 터미널</div>';
      h += r.rows.map(function (a) {
        return '<button type="button" class="wm-row ag-row" role="menuitemradio" data-id="' + esc(a.id) + '" data-name="' + esc(a.label) + '"' +
          ' data-status="' + esc(a.status) + '" title="' + esc(a.name + ' · ' + a.status + ' · ' + a.id) + '"' + check(a.current) + '<span class="ag-dot"></span>' +
          '<span class="ag-name">' + esc(a.label) + '</span><span class="ag-dir">' + esc(a.folder) + '</span></button>';
      }).join('');
    }
    if (r.orphan) {
      h += '<button type="button" class="wm-row ag-row ag-orphan" role="menuitemradio" data-id="' + esc(r.orphan.id) + '" data-name="' + esc(r.orphan.label) + '"' +
        ' title="지금 받는 곳 — 목록에 없어요(꺼졌거나 접속하지 않음)"' + check(true) + '<span class="ag-dot"></span>' +
        '<span class="ag-txt"><span class="ag-name">' + esc(r.orphan.label) + '</span><span class="ag-sub">지금 받는 곳 · 목록에 없음</span></span></button>';
    }
    if (r.error && !r.rows.length) h += '<div class="ag-msg">' + esc(r.error) + '</div>';
    if (r.empty) h += '<div class="ag-msg">접속한 에이전트가 없어요 — 터미널에서 hd attach 로 접속하거나 새 터미널을 여세요</div>';
    menu.innerHTML = h + noneRow(r.current) +
      '<button type="button" class="wm-row ag-spawn" role="menuitem" title="Paseo 로 새 AI 에이전트를 띄워요 — 먼저 물어봐요"><span class="ag-plus">+</span><span class="ag-name">새 터미널…</span></button>';
    place();
  }
  function fetchRows() {
    return ctx.api.call('GET', '/api/agents').then(function (res) {
      if (res.status !== 200) throw new Error(res.body && res.body.error || ('도우미 답 ' + res.status));
      var r = A.menu(res.body);
      if (r.bad) console.warn('[hd] 보낼 곳 목록: 모양이 틀린 줄 ' + r.bad + '개를 뺐어요');
      repo = r.repo;
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
  function spawnAsk() {                              // 새 터미널 — 묻고 부르기는 view-spawn(의도 하나)
    var d = {repo: repo, done: false};
    close();
    document.dispatchEvent(new CustomEvent('hd-spawn-ask', {detail: d}));
    if (!d.done) { console.warn('[hd] 새 터미널: 받는 기능(view-spawn)이 붙지 않았어요'); ctx.toast('새 터미널 열기가 붙지 않았어요 — 터미널에서 에이전트를 열고 hd attach 로 접속해 주세요'); }
  }
  menu.addEventListener('click', function (e) {
    if (e.target.closest('button.ag-spawn')) { spawnAsk(); return; }
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
