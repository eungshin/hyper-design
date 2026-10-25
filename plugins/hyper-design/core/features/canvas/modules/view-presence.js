/* View — 받는 곳 상태(47-5b): 위쪽 받는 곳 칩 #aichip 에 고른 에이전트의 지금 상태 — 점(접속 중 초록 · 자리 비움 회색, #aichip[data-state])과
   칩 옆 #aistate 한 줄(진행 글 · '접속 중' · '자리 비움'). 표 = GET /api/presence(열 때 · 받는 곳이 바뀔 때 · 실시간이 아닐 때 15초마다) +
   document 'hd-event'(view-live)의 agent.hello/away/progress. 규칙은 HD.presence(Model). 칩 글의 주인은 view-sync — 이름을 모르는 칩('AI 연결됨')이면
   의도 'hd-agent' {agent, name} 를 칩에 보내 이름을 채운다(직접 쓰지 않음). 대화창 알약은 #aichip 을 비추므로 data-state 를 따라간다.
   표에 없는 받는 곳(Paseo 만 · 받는 곳 없음) = data-state 없음 · #aistate 숨김(지금 모양 그대로). 도우미가 없으면 아무것도 만들지 않는다.
   상태: 접속 표(이 모듈만, 저장 안 함). HD.feature('presence', {needs: ['api', '$']}) → {state(), refresh() → Promise} | {} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var EVERY = 15000;

var CSS = '#aichip[data-state="away"]::before{background:#b5b5b0}' +
  '#aichip[data-state="here"]::before{background:var(--ui-ok,#4f7d5f)}' +
  '#aistate{max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11.5px;color:#8a8a85;padding:0 6px 0 2px}' +
  '#aistate[data-state="here"]{color:#4f7d5f}' +
  '#aistate[hidden]{display:none}';

function mount(ctx) {
  if (!ctx.api.on) return {};
  var P = HD.presence, chip = ctx.$('#aichip');
  if (!chip) throw new Error('받는 곳 칩(#aichip)이 없어요');
  var s = P.initial(), warned = false, timer = 0;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
  var line = document.createElement('span');
  line.id = 'aistate'; line.setAttribute('role', 'status'); line.setAttribute('aria-live', 'polite'); line.hidden = true;
  var after = ctx.$('#aibtn') || chip;
  after.parentNode.insertBefore(line, after.nextSibling);

  function paint() {
    var cur = window.__hdAgent || null, c = P.chip(s, cur);
    if (c) chip.dataset.state = c.state; else delete chip.dataset.state;
    line.hidden = !c || chip.hidden;
    line.textContent = c ? c.text : '';
    line.title = c ? c.title : '';
    if (c) line.dataset.state = c.state; else delete line.dataset.state;
    if (c && cur && chip.textContent === 'AI 연결됨' && c.name && c.name !== cur) {   // 새로고침 뒤 칩은 이름을 모른다 — 칩 주인(view-sync)에게 이름을 건넨다
      chip.dispatchEvent(new CustomEvent('hd-agent', {detail: {agent: cur, name: c.name}}));
    }
  }
  function refresh() {
    return ctx.api.call('GET', '/api/presence').then(function (res) {
      if (res.status !== 200) throw new Error((res.body && res.body.error) || ('도우미 답 ' + res.status));   // 옛 도우미(404) = 상태 없이
      var r = P.load(s, res.body);
      if (r.bad) console.warn('[hd] 받는 곳 상태: 모양이 틀린 줄 ' + r.bad + '개를 뺐어요');
      s = r.s; warned = false; paint();
    }).catch(function (e) {
      if (!warned) { warned = true; console.warn('[hd] 받는 곳 상태를 읽지 못했어요(칩은 상태 없이): ' + (e && e.message || e)); }
    });
  }
  function tick() {
    timer = setTimeout(tick, EVERY);
    var live = document.getElementById('livechip');
    if (document.hidden || (live && live.dataset.mode === 'live')) return;   // 실시간이면 이벤트가 맡는다
    refresh();
  }
  document.addEventListener('hd-event', function (e) {
    var n = P.apply(s, e.detail);
    if (n !== s) { s = n; paint(); }
  });
  chip.addEventListener('hd-agent', function () { setTimeout(paint, 0); });   // 받는 곳이 바뀜(view-sync 가 먼저 __hdAgent 를 고친 뒤)
  refresh();
  timer = setTimeout(tick, EVERY);
  return {state: function () { return s; }, refresh: refresh};
}

HD.feature('presence', {needs: ['api', '$'], mount: mount});
})();
