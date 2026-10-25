/* View — 실시간 알림(47-4b): 프로젝트마다 EventSource 하나(/api/events?hd=<토큰>, 다시 붙을 때 &since=<마지막 id>)로 서버 이벤트를 받아 HD.live.plan(Model)의 할 일을 셸 길로 넘긴다.
   흐름이 열리면 '실시간' — 셸이 2초 상태 읽기·/api/files·AI 기록 폴링을 끈다(ctx.polling(false)). 오류면 '2초 확인'으로 물러나(ctx.polling(true)) HD.live.backoff 뒤 다시 붙는다(1·2·4…30초).
   상태 칩: #mode(파일에 바로 씀) 바로 뒤 <span class="mchip" id="livechip" data-mode="live|polling|connecting" role="status"> — 점 + '실시간' | '2초 확인'.
   모든 이벤트를 document 의도 'hd-event' {detail: 이벤트} 로도 알린다(대화창 진행 줄 — View 끼리 직접 부르지 않음). 깨진 이벤트 = [hd] 경고 한 줄, 건너뜀.
   가진 상태: HD.live 상태(마지막 id · 본 stamp · 메아리 · 흐름 모드) · EventSource 하나 · 다시 붙기 타이머. 저장 없음.
   HD.viewLive.mount(ctx) → {mode() → 'off'|'connecting'|'live'|'polling', own(stamp, ids, echo) → 다시 실을까(bool), reload(ids, opt{stamp, echo}), close()}
   ctx = {on, token, chip(#mode — 그 뒤에 칩), url?(기본 '/api/events'), warn(msg), polling(on), rev() → 상태 rev, files() → 파일 seq|null,
          state() 상태 다시 읽기, resync() 놓친 화면 파일 다시 맞추기, cards(ids, seq) AI 가 쓴 카드 다시, data(ids, stamp) 판 데이터 + 바뀐 카드,
          aiWrites() AI 기록 다시 읽기, built(ids), revert(ids, why, screens), reloadCards(ids) 카드만 다시(교체 길)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var SAY = {live: '실시간', polling: '2초 확인', connecting: '연결 중'};
var TITLE = {live: '터미널(AI)이 쓴 것이 바로 반영돼요 — 서버 알림(SSE)', polling: '서버 알림이 끊겨 2초마다 확인해요 — 다시 붙는 중', connecting: '서버 알림에 붙는 중'};

function mount(ctx) {
  var L = HD.live, st = L.initial(), es = null, timer = 0, closed = false, chip = null;
  var warn = ctx.warn || function (m) { console.warn(m); };
  if (!ctx.on || !ctx.token || typeof EventSource !== 'function') {
    return {mode: function () { return 'off'; }, own: function () { return true; }, reload: function (ids) { ctx.reloadCards(ids || []); }, close: function () {}};
  }
  if (ctx.chip && ctx.chip.parentNode) {
    chip = document.createElement('span'); chip.className = 'mchip'; chip.id = 'livechip'; chip.setAttribute('role', 'status');
    ctx.chip.parentNode.insertBefore(chip, ctx.chip.nextSibling);
  }
  function paint() {
    if (!chip) return;
    chip.dataset.mode = st.mode; chip.textContent = SAY[st.mode] || ''; chip.title = TITLE[st.mode] || '';
    chip.classList.toggle('on', st.mode === 'live');
  }
  function linked(type) {
    var r = L.link(st, {type: type}), was = st.mode;
    st = r.s; paint();
    if (st.mode !== was) ctx.polling(r.poll);        // 처음(연결 중)은 폴링이 켜진 채 — 열리면 끄고, 끊기면 켠다
    return r;
  }
  function act(a) {
    try {
      if (a.do === 'state') ctx.state();
      else if (a.do === 'files') ctx.resync();
      else if (a.do === 'cards') ctx.cards(a.ids, a.seq);
      else if (a.do === 'data') ctx.data(a.ids, a.stamp);
      else if (a.do === 'aiWrites') ctx.aiWrites();
      else if (a.do === 'built') ctx.built(a.ids);
      else if (a.do === 'revert') ctx.revert(a.ids, a.why, a.screens);
    } catch (e) { warn('[hd] 실시간 알림 처리 실패(' + a.do + '): ' + (e && e.message || e)); }
  }
  function onEvent(e) {
    var ev;
    try { ev = JSON.parse(e.data); } catch (x) { warn('[hd] 실시간 알림이 깨졌어요: ' + String(e.data).slice(0, 80)); return; }
    var r = L.plan(st, ev, {rev: ctx.rev(), files: ctx.files(), t: Date.now()});
    st = r.s;
    r.acts.forEach(act);
    try { document.dispatchEvent(new CustomEvent('hd-event', {detail: ev})); } catch (x) { warn('[hd] hd-event 알림 실패: ' + (x && x.message || x)); }
  }
  function connect() {
    timer = 0;
    if (closed) return;
    var url = (ctx.url || '/api/events') + '?hd=' + encodeURIComponent(ctx.token) + (st.last != null ? '&since=' + st.last : '');
    try { es = new EventSource(url); }
    catch (e) { warn('[hd] 서버 알림을 열지 못했어요: ' + (e && e.message || e)); fail(); return; }
    es.onopen = function () { var first = st.last == null; linked('open'); if (first) act({do: 'state'}); };   // 처음 열림 = 페이지를 받은 뒤 흐름이 열리기 전 것을 한 번 맞춤(since=rev, 같으면 몸통 없음)
    es.onerror = function () { fail(); };
    L.TYPES.forEach(function (t) { es.addEventListener(t, onEvent); });
  }
  function fail() {                                    // 브라우저의 자동 다시 붙기 대신 우리 backoff(폴링으로 물러나 있는 동안)
    if (es) { try { es.close(); } catch (e) {} es = null; }   // 닫기 실패는 버림(이미 닫힘)
    if (closed || timer) return;
    var r = linked('error');
    if (st.fails === 1) warn('[hd] 서버 알림이 끊겨 2초 확인으로 물러나요 — ' + r.retry + 'ms 뒤 다시 붙어요');
    timer = setTimeout(connect, r.retry);
  }
  function own(stamp, ids, echo) {
    var r = L.own(st, stamp, ids, echo, Date.now());
    st = r.s; return r.fresh;
  }
  paint();
  connect();
  addEventListener('pagehide', function () { closed = true; if (es) es.close(); });
  return {
    mode: function () { return st.mode; },
    own: own,
    reload: function (ids, opt) {                      // 캔버스가 스스로 다시 싣기(ctx.reload) — 이벤트로 이미 실은 쓰기면 건너뜀
      opt = opt || {};
      if (!own(opt.stamp || null, ids, !!opt.echo)) return;
      ctx.reloadCards(ids || []);
    },
    close: function () { closed = true; clearTimeout(timer); if (es) es.close(); }
  };
}

HD.viewLive = {mount: mount};
})();
