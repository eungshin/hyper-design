/* View — 프로젝트별 키 읽기·쓰기 주인(#228): 도우미로 열면 .hd-canvas.json 이 진실 원천이고 브라우저 저장소는 캐시, 아니면 브라우저 저장소 그대로.
   규칙(어떤 키·파일이 이기나·올리기·보낼 본문)은 modules/state-file.js(Model). 여기는 쓰기를 300ms 모아 PUT /api/state, 닫을 때 마저 보내기, 409 처리.
   409(다른 곳에서 바뀜) = 보내지 못한 이번 변경은 버리고 알린 뒤 ctx.reload()(새로 연 페이지가 파일 상태를 받는다).
   쓰기 대기 표시(hd-unsent:<hash> = {base: rev, names}) — 파일에 닿았다고 확인 못 한 이름(모으는 중·보내는 중·닫을 때 보낸 것)을 브라우저 저장소에 남긴다.
     닫을 때 보낸 PUT 이 새 페이지 GET 보다 늦게 닿거나 못 닿아도(300ms 안의 새로고침) 다음 시작 때 boot 가 그 값을 다시 올린다. 답(성공)·409 때 고쳐 쓰거나 지운다.
   보내기가 실패하면(도우미 꺼짐 등) 한 번 알리고 [hd] 경고, 바뀐 키는 다음 쓰기 때 같이 보낸다.
   살아 있는 새로 받기(A2a): 페이지가 보이는 동안 2초마다(숨으면 10초) GET /api/state. 파일 rev 가 더 크면 —
     보내지 않은 변경이 있으면 먼저 보낸다(409 = 위 충돌 길) · 바뀐 이름이 notes·note-seq·busy 뿐이면 제자리에서 받아(상태·캐시) ctx.onExternal(이름들) ·
     다른 이름(자리·폴더…)도 바뀌었으면 셸이 따로 들고 있으니 지금처럼 알리고 다시 불러오기. 네트워크 실패 3번 연속 = 멈추고 한 번 알림, 창에 돌아오면(focus) 다시.
   HD.viewStateSync.mount(ctx) → {mode, getItem(k), setItem(k, v), removeItem(k), flush(), rev(), poll()(지금 한 번 — 테스트·focus)}
     mode = 'off'(file:// · 토큰 없음) | 'local'(스냅숏 깨짐) | 'file' | 'migrate'. off·local 이면 모든 키가 ctx.storage 그대로(던지는 것도 그대로)
   ctx = {hash, on, token, snapshot(window.__hdState), storage{getItem,setItem,removeItem}, toast(msg), warn(msg), reload(), onExternal(names)?, delayMs?(기본 300), pollMs?(기본 2000), idleMs?(기본 10000)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CONFLICT = '다른 곳에서 바뀌어 다시 불러왔어요';
var FAILED = '캔버스 상태를 파일에 저장하지 못했어요 — 이 브라우저에만 남아요';
var LOST = '도우미에 닿지 않아 AI 답을 새로 받지 않아요 — 창을 다시 누르면 다시 시도해요';
var LIVE = {notes: 1, 'note-seq': 1, busy: 1};                // 셸이 상태에서 바로 다시 읽을 수 있는 이름 — 나머지는 다시 불러오기

function mount(ctx) {
  var S = HD.stateFile, store = ctx.storage, on = !!(ctx.on && ctx.token);
  var mode = 'off', rev = 0, state = {}, dirty = {}, inflight = [], timer = 0, busy = false, again = false, dead = false, failWarned = false, markWarned = false;

  function pass() {
    return {mode: mode, getItem: function (k) { return store.getItem(k); }, setItem: function (k, v) { store.setItem(k, v); },
            removeItem: function (k) { store.removeItem(k); }, flush: function () {}, rev: function () { return 0; }, poll: function () {}};
  }
  if (!on) return pass();
  var snap = S.snapshot(ctx.snapshot);
  if (!snap.ok) { mode = 'local'; ctx.warn('[hd] 상태 스냅숏이 깨져 브라우저 저장소만 써요: ' + snap.why); return pass(); }
  var local = S.fromLocal(function (k) { return store.getItem(k); }, ctx.hash);
  local.bad.forEach(function (n) { ctx.warn('[hd] 브라우저에 저장된 ' + n + ' 값이 깨져 버려요'); });
  var MARK = S.unsentKey(ctx.hash), markText = null;
  try { markText = store.getItem(MARK); } catch (e) { ctx.warn('[hd] 쓰기 대기 표시를 읽지 못했어요: ' + (e && e.message || e)); }
  var b = S.boot(snap, local.values, S.unsent(markText));
  mode = b.mode; rev = b.rev; state = b.state;
  Object.keys(b.cache).forEach(function (n) { cacheSet(n, b.cache[n]); });
  b.upload.forEach(function (n) { dirty[n] = 1; });
  if (b.lost.length) ctx.warn('[hd] 보내지 못한 변경이 그 사이 바뀐 파일에 밀려 버려져요: ' + b.lost.join(', '));
  mark();

  function cacheSet(n, text) {                      // 캐시일 뿐 — 못 써도(저장 공간 꽉 참) 파일이 진실 원천
    try { if (text == null) store.removeItem(S.keyOf(n, ctx.hash)); else store.setItem(S.keyOf(n, ctx.hash), text); } catch (e) {}
  }
  function names() { return Object.keys(dirty); }
  function mark() {                                 // 쓰기 대기 표시 = 모으는 중 ∪ 보내는 중, 기준 rev(보내는 중이면 그 답 전의 rev)
    var all = names(); inflight.forEach(function (n) { if (all.indexOf(n) < 0) all.push(n); });
    try {
      if (all.length) store.setItem(MARK, JSON.stringify({base: rev, names: all})); else store.removeItem(MARK);
    } catch (e) {
      if (!markWarned) { markWarned = true; ctx.warn('[hd] 쓰기 대기 표시를 남기지 못했어요 — 바로 새로고침하면 마지막 변경을 잃을 수 있어요: ' + (e && e.message || e)); }
    }
  }
  function req(body, keepalive) {
    return fetch('/api/state', {method: 'PUT', keepalive: !!keepalive, headers: {'Content-Type': 'application/json', 'X-HD-Token': ctx.token}, body: JSON.stringify(body)});
  }
  function schedule() {
    if (dead) return;
    clearTimeout(timer); timer = setTimeout(flush, ctx.delayMs == null ? 300 : ctx.delayMs);
  }
  function failed(sent, why) {                      // 다음 쓰기 때 같이 보낸다
    sent.forEach(function (n) { dirty[n] = 1; });
    inflight = []; mark();
    ctx.warn('[hd] 상태 파일 저장 실패: ' + why);
    if (!failWarned) { failWarned = true; ctx.toast(FAILED); }
  }
  function conflict() {
    dead = true; dirty = {}; inflight = []; clearTimeout(timer);
    mark();                                          // 409 = 이번 변경은 버린다(다시 연 페이지가 올리지 않게)
    ctx.toast(CONFLICT);
    ctx.reload();
  }
  function flush() {
    clearTimeout(timer);
    if (dead) return;
    if (busy) { again = true; return; }
    var sent = names(); if (!sent.length) return;
    dirty = {}; busy = true; inflight = sent;
    req(S.body(rev, state, sent)).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (r.status === 409) return conflict();
        if (!r.ok || typeof j.rev !== 'number') return failed(sent, 'HTTP ' + r.status);
        rev = j.rev; failWarned = false; inflight = []; mark();
      });
    }, function (e) { failed(sent, String(e && e.message || e)); }).then(function () {
      busy = false;
      if (again) { again = false; flush(); }
    });
  }
  function onLeave() {                               // 닫기·새로고침 — 모아 둔 변경을 마저(답은 못 받는다 — 쓰기 대기 표시는 그대로 둔다)
    if (dead) return;
    var sent = names(); if (!sent.length) return;
    dirty = {}; clearTimeout(timer);
    try { req(S.body(rev + (busy ? 1 : 0), state, sent), true).catch(function () {}); } catch (e) {}   // 보내는 중인 것이 있으면 그 답의 rev 를 미리(틀리면 409 — 페이지는 이미 떠남)
  }
  addEventListener('pagehide', onLeave);
  addEventListener('beforeunload', onLeave);
  if (b.upload.length) schedule();                  // 파일이 없을 때 브라우저 값 한 번 올리기(rev 0 → 1)

  var ptimer = 0, polling = false, fails = 0, stopped = false;
  function same(a, b) { return JSON.stringify(a == null ? null : a) === JSON.stringify(b == null ? null : b); }
  function next() {
    clearTimeout(ptimer); ptimer = 0;
    if (dead || stopped) return;
    ptimer = setTimeout(poll, document.hidden ? (ctx.idleMs || 10000) : (ctx.pollMs || 2000));
  }
  function lost(why) {
    fails++;
    if (fails < 3) return;
    stopped = true; ctx.warn('[hd] 상태 새로 받기 멈춤: ' + why);
    ctx.toast(LOST);
  }
  function take(j) {                                  // 파일 쪽이 새것 → 바뀐 이름만 받기
    var snap = S.snapshot(j);
    if (!snap.ok) { ctx.warn('[hd] /api/state 답이 깨졌어요: ' + snap.why); return; }
    if (snap.rev <= rev) return;
    var all = {}, changed = [];
    Object.keys(state).concat(Object.keys(snap.state)).forEach(function (n) { all[n] = 1; });
    Object.keys(all).forEach(function (n) { if (!same(state[n], snap.state[n])) changed.push(n); });
    if (changed.some(function (n) { return !LIVE[n]; })) { conflict(); return; }   // 자리·폴더 등은 셸이 따로 들고 있다 — 지금처럼 다시 불러오기
    rev = snap.rev; state = snap.state;
    changed.forEach(function (n) { cacheSet(n, S.read(state, n)); });
    if (changed.length && ctx.onExternal) ctx.onExternal(changed);
  }
  function poll() {
    clearTimeout(ptimer); ptimer = 0;
    if (dead || stopped || polling) return;
    if (busy) { next(); return; }                    // 보내는 중 — 그 답의 rev 를 받은 뒤에
    if (names().length) { flush(); next(); return; }  // 보내지 않은 변경 먼저(파일이 앞서 있으면 409 = 충돌 길)
    polling = true;
    fetch('/api/state', {headers: {'X-HD-Token': ctx.token}, cache: 'no-store'}).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      fails = 0;
      if (!dead && !busy && !names().length) take(j);   // 기다리는 사이 바뀐 것이 있으면 다음 번에
    }, function (e) { lost(String(e && e.message || e)); }).then(function () { polling = false; next(); });
  }
  function wake() {                                   // 창에 돌아옴 = 멈췄으면 다시, 숨어서 늦춰 둔 것은 바로
    if (dead) return;
    if (stopped) { stopped = false; fails = 0; }
    if (!document.hidden && !polling) poll();
  }
  addEventListener('focus', wake);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) wake(); });
  next();

  return {
    mode: mode,
    getItem: function (k) { var n = S.nameOf(k, ctx.hash); return n ? S.read(state, n) : store.getItem(k); },
    setItem: function (k, v) {
      var n = S.nameOf(k, ctx.hash);
      if (!n) { store.setItem(k, v); return; }
      var w = S.write(state, n, String(v));
      cacheSet(n, String(v));
      if (!w.ok) { ctx.warn('[hd] JSON 이 아닌 값은 파일에 쓰지 않아요: ' + k); return; }
      state = w.state; dirty[n] = 1; mark(); schedule();
    },
    removeItem: function (k) {
      var n = S.nameOf(k, ctx.hash);
      if (!n) { store.removeItem(k); return; }
      state = S.drop(state, n); cacheSet(n, null); dirty[n] = 1; mark(); schedule();
    },
    flush: flush,
    rev: function () { return rev; },
    poll: poll
  };
}

HD.viewStateSync = {mount: mount};
})();
