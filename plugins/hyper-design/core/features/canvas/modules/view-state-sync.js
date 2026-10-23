/* View — 프로젝트별 키 읽기·쓰기 주인(#228): 도우미로 열면 .hd-canvas.json 이 진실 원천이고 브라우저 저장소는 캐시, 아니면 브라우저 저장소 그대로.
   규칙(어떤 키·파일이 이기나·올리기·보낼 본문)은 modules/state-file.js(Model). 여기는 쓰기를 300ms 모아 PUT /api/state, 닫을 때 마저 보내기, 409 처리.
   409(다른 곳에서 바뀜) = 보내지 못한 이번 변경은 버리고 알린 뒤 ctx.reload()(새로 연 페이지가 파일 상태를 받는다).
   보내기가 실패하면(도우미 꺼짐 등) 한 번 알리고 [hd] 경고, 바뀐 키는 다음 쓰기 때 같이 보낸다.
   HD.viewStateSync.mount(ctx) → {mode, getItem(k), setItem(k, v), removeItem(k), flush(), rev()}
     mode = 'off'(file:// · 토큰 없음) | 'local'(스냅숏 깨짐) | 'file' | 'migrate'. off·local 이면 모든 키가 ctx.storage 그대로(던지는 것도 그대로)
   ctx = {hash, on, token, snapshot(window.__hdState), storage{getItem,setItem,removeItem}, toast(msg), warn(msg), reload(), delayMs?(기본 300)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CONFLICT = '다른 곳에서 바뀌어 다시 불러왔어요';
var FAILED = '캔버스 상태를 파일에 저장하지 못했어요 — 이 브라우저에만 남아요';

function mount(ctx) {
  var S = HD.stateFile, store = ctx.storage, on = !!(ctx.on && ctx.token);
  var mode = 'off', rev = 0, state = {}, dirty = {}, timer = 0, busy = false, again = false, dead = false, failWarned = false;

  function pass() {
    return {mode: mode, getItem: function (k) { return store.getItem(k); }, setItem: function (k, v) { store.setItem(k, v); },
            removeItem: function (k) { store.removeItem(k); }, flush: function () {}, rev: function () { return 0; }};
  }
  if (!on) return pass();
  var snap = S.snapshot(ctx.snapshot);
  if (!snap.ok) { mode = 'local'; ctx.warn('[hd] 상태 스냅숏이 깨져 브라우저 저장소만 써요: ' + snap.why); return pass(); }
  var local = S.fromLocal(function (k) { return store.getItem(k); }, ctx.hash);
  local.bad.forEach(function (n) { ctx.warn('[hd] 브라우저에 저장된 ' + n + ' 값이 깨져 버려요'); });
  var b = S.boot(snap, local.values);
  mode = b.mode; rev = b.rev; state = b.state;
  Object.keys(b.cache).forEach(function (n) { cacheSet(n, b.cache[n]); });
  b.upload.forEach(function (n) { dirty[n] = 1; });

  function cacheSet(n, text) {                      // 캐시일 뿐 — 못 써도(저장 공간 꽉 참) 파일이 진실 원천
    try { if (text == null) store.removeItem(S.keyOf(n, ctx.hash)); else store.setItem(S.keyOf(n, ctx.hash), text); } catch (e) {}
  }
  function names() { return Object.keys(dirty); }
  function req(body, keepalive) {
    return fetch('/api/state', {method: 'PUT', keepalive: !!keepalive, headers: {'Content-Type': 'application/json', 'X-HD-Token': ctx.token}, body: JSON.stringify(body)});
  }
  function schedule() {
    if (dead) return;
    clearTimeout(timer); timer = setTimeout(flush, ctx.delayMs == null ? 300 : ctx.delayMs);
  }
  function failed(sent, why) {                      // 다음 쓰기 때 같이 보낸다
    sent.forEach(function (n) { dirty[n] = 1; });
    ctx.warn('[hd] 상태 파일 저장 실패: ' + why);
    if (!failWarned) { failWarned = true; ctx.toast(FAILED); }
  }
  function conflict() {
    dead = true; dirty = {}; clearTimeout(timer);
    ctx.toast(CONFLICT);
    ctx.reload();
  }
  function flush() {
    clearTimeout(timer);
    if (dead) return;
    if (busy) { again = true; return; }
    var sent = names(); if (!sent.length) return;
    dirty = {}; busy = true;
    req(S.body(rev, state, sent)).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (r.status === 409) return conflict();
        if (!r.ok || typeof j.rev !== 'number') return failed(sent, 'HTTP ' + r.status);
        rev = j.rev; failWarned = false;
      });
    }, function (e) { failed(sent, String(e && e.message || e)); }).then(function () {
      busy = false;
      if (again) { again = false; flush(); }
    });
  }
  function onLeave() {                               // 닫기·새로고침 — 모아 둔 변경을 마저(답은 못 받는다)
    if (dead) return;
    var sent = names(); if (!sent.length) return;
    dirty = {}; clearTimeout(timer);
    try { req(S.body(rev + (busy ? 1 : 0), state, sent), true).catch(function () {}); } catch (e) {}   // 보내는 중인 것이 있으면 그 답의 rev 를 미리(틀리면 409 — 페이지는 이미 떠남)
  }
  addEventListener('pagehide', onLeave);
  addEventListener('beforeunload', onLeave);
  if (b.upload.length) schedule();                  // 파일이 없을 때 브라우저 값 한 번 올리기(rev 0 → 1)

  return {
    mode: mode,
    getItem: function (k) { var n = S.nameOf(k, ctx.hash); return n ? S.read(state, n) : store.getItem(k); },
    setItem: function (k, v) {
      var n = S.nameOf(k, ctx.hash);
      if (!n) { store.setItem(k, v); return; }
      var w = S.write(state, n, String(v));
      cacheSet(n, String(v));
      if (!w.ok) { ctx.warn('[hd] JSON 이 아닌 값은 파일에 쓰지 않아요: ' + k); return; }
      state = w.state; dirty[n] = 1; schedule();
    },
    removeItem: function (k) {
      var n = S.nameOf(k, ctx.hash);
      if (!n) { store.removeItem(k); return; }
      state = S.drop(state, n); cacheSet(n, null); dirty[n] = 1; schedule();
    },
    flush: flush,
    rev: function () { return rev; }
  };
}

HD.viewStateSync = {mount: mount};
})();
