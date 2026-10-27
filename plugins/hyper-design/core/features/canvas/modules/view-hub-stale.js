/* View — 허브 옛 코드 칩(R34): 위쪽 상태 자리(R27 F11 '예외만', 받는 곳 칩 묶음 끝 · 첫 구분선 앞)에 '허브 옛 코드 · 다시 켜기' 한 줄, 누르면 허브를 다시 켜고 이 프로젝트를 다시 연다.
   판단·글은 HD.hubStale(Model) — 서버 판단(code_stamp.hub_stale)을 그대로 보인다. 받는 곳: 처음 window.__hdHubStale(허브가 페이지에 끼움) ·
   그 뒤 document 'hd-hub-stale' {detail: hubStale}(view-state-sync 가 GET /api/state 답마다 — 창에 돌아올 때도 읽는다). 칸이 없는 답(도우미) = 모름, 칩 그대로.
   다시 켜기 = 홈 화면 [다시 켜기]와 같은 서버 길(POST /api/hub/restart → spawn_restart): GET / 의 지금 허브 토큰을 잡고 → POST(세션 토큰) →
     / 를 0.5초마다 읽어 토큰이 바뀌면(새 허브) POST /api/open {name: out}(새 허브 토큰) → 그 주소로. 보내지 않은 상태 쓰기는 쓰기 대기 표시가 다음 시작에 올린다.
     못 하면(이 서버에 그 주소가 없음 · 20초 안에 안 뜸 · 다시 열기 실패) 토스트 + 명령 'hd home --restart' 를 클립보드로(복사 실패면 토스트 글에만).
   상태: 지금 판단(이 모듈만) · 다시 켜는 중(한 번에 하나). 자동으로 다시 켜지 않는다(R34 — 사람이 누를 때만).
   HD.feature('hubStale', {needs: ['$', 'toast', 'api']}) → {show(v)}(테스트·셸 — hubStale 값 하나) | {}(도우미 없음) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CSS = '.hd .mchip.hubstale{border:0;background:none;font:inherit;font-size:11.5px;height:24px;border-radius:5px;cursor:pointer;color:#5c5a52}' +
  '.hd .mchip.hubstale::before{background:#c9932a}' +
  '.hd .mchip.hubstale:hover,.hd .mchip.hubstale:focus-visible{background:#E6E6E1;color:#2b2b29}' +
  '.hd .mchip.hubstale[aria-busy="true"]{cursor:progress;color:#9a9a95}' +
  '.hd .mchip.hubstale[hidden]{display:none}';
var TRIES = 40, EVERY = 500;

function mount(ctx) {
  if (!ctx.api.on) return {};                       // file:// · 도우미 없음 — 허브가 아니다
  var M = HD.hubStale, $ = ctx.$;
  var after = $('#aichip') || $('#mode');
  if (!after || !after.parentNode) throw new Error('위쪽 상태 칩 자리(#aichip · #mode)가 없어요');
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var chip = document.createElement('button');
  chip.type = 'button'; chip.className = 'mchip hubstale'; chip.id = 'hubstale'; chip.hidden = true;
  var sep = after.nextElementSibling;               // 상태 묶음 끝(받는 곳 칩 · ▾ · 상태 글 뒤, 첫 구분선 앞)
  while (sep && !sep.classList.contains('sep')) sep = sep.nextElementSibling;
  after.parentNode.insertBefore(chip, sep);

  var going = false;
  function show(v) {
    var r = M.read(v);
    if (r === null) return;                         // 답에 칸이 없음(도우미 · 옛 허브) — 보던 것 그대로
    if (r.bad) console.warn('[hd] 허브 옛 코드 판단을 읽지 못했어요: ' + r.bad);
    if (going) return;
    chip.hidden = !r.stale;
    if (r.stale) { chip.textContent = r.label; chip.title = r.title; chip.setAttribute('aria-label', r.title); }
  }
  function idle() { going = false; chip.removeAttribute('aria-busy'); chip.textContent = M.LABEL; }
  function fallback(why) {                          // 이 화면에서 못 하면 터미널 명령을 건넨다
    idle();
    var say = function (copied) { ctx.toast('허브를 다시 켜지 못했어요(' + why + ') — 터미널에서 ' + M.CMD + (copied ? ' (복사했어요)' : ''), false, 8000); };
    try { navigator.clipboard.writeText(M.CMD).then(function () { say(true); }, function () { say(false); }); }
    catch (e) { say(false); }
    console.warn('[hd] 허브 다시 켜기 실패: ' + why);
  }
  function homeToken() {
    return fetch('/', {cache: 'no-store'}).then(function (r) { return r.ok ? r.text() : ''; }).then(M.tokenOf);
  }
  function reopen(token) {                          // 새 허브에서 이 프로젝트를 다시 연다(허브 토큰 — 홈 화면이 여는 것과 같은 /api/open)
    var body = {name: window.__hdOut || ''};
    if (typeof window.__hdAgent === 'string' && window.__hdAgent) body.agent = window.__hdAgent;
    return fetch('/api/open', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-HD-Token': token}, body: JSON.stringify(body)})
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || !j.url) throw new Error(j.error || ('HTTP ' + r.status)); return j.url; }); });
  }
  function restart() {
    if (going) return;
    going = true; chip.setAttribute('aria-busy', 'true'); chip.textContent = '허브 다시 켜는 중…';
    homeToken().catch(function () { return null; }).then(function (old) {
      if (!old) { fallback('지금 허브 토큰을 읽지 못함'); return; }
      return ctx.api.call('POST', '/api/hub/restart', {}).then(function (res) {
        if (res.status !== 200 || !res.body || res.body.restarting !== true) { fallback(res.body && res.body.error || ('이 서버에는 없는 기능 · ' + res.status)); return; }
        var tries = 0;
        (function poll() {
          if (++tries > TRIES) { fallback('20초 안에 새 허브가 뜨지 않음'); return; }
          homeToken().then(function (t) {
            if (!t || t === old) { setTimeout(poll, EVERY); return; }
            reopen(t).then(function (url) { location.assign(url); }, function (e) {   // 다시 열기 실패 = 새 허브의 홈으로(거기서 열면 된다)
              console.warn('[hd] 새 허브에서 프로젝트를 다시 열지 못해 홈으로 가요: ' + (e && e.message || e));
              location.assign('/');
            });
          }, function () { setTimeout(poll, EVERY); });   // 바뀌는 동안은 닿지 않는다 — 다시
        })();
      });
    }).catch(function (e) { fallback(String(e && e.message || e)); });
  }

  chip.addEventListener('click', restart);
  document.addEventListener('hd-hub-stale', function (e) { show(e.detail); });
  show(window.__hdHubStale);
  return {show: show};
}

HD.feature('hubStale', {needs: ['$', 'toast', 'api'], mount: mount});
})();
