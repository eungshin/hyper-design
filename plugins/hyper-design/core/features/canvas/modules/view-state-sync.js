/* View — 프로젝트별 키 읽기·쓰기 주인(#228): 도우미로 열면 .hd-canvas.json 이 진실 원천이고 브라우저 저장소는 캐시, 아니면 브라우저 저장소 그대로.
   규칙(어떤 키·파일이 이기나·올리기·보낼 본문)은 modules/state-file.js(Model). 여기는 쓰기를 300ms 모아 PUT /api/state, 닫을 때 마저 보내기, 409 처리.
   409(다른 곳에서 바뀜 — hd reply·claim 은 rev 를 늘 올린다, #269) = 409 답의 서버 상태와 HD.saveMerge.resolve(Model)로 합친다:
     보낸 이름이 서버에서 안 바뀌었으면(메모는 id 마다 칸끼리, busy 는 카드마다) 서버의 나머지를 받고 내 값을 지켜 새 rev 로 한 번 다시 보낸다
     (받은 이름 중 notes·note-seq·busy 는 ctx.onExternal, 그 밖이 바뀌었으면 다시 보낸 뒤 다시 불러오기 — 잃는 것 없음).
     둘 다 바꾼 이름이 있거나 다시 보낸 것도 409 면 이번 변경은 버리고 잃은 것을 토스트로 말한 뒤 ctx.reload().
   쓰기 대기 표시(hd-unsent:<hash> = {base: rev, names}) — 파일에 닿았다고 확인 못 한 이름(모으는 중·보내는 중·닫을 때 보낸 것)을 브라우저 저장소에 남긴다.
     닫을 때 보낸 PUT 이 새 페이지 GET 보다 늦게 닿거나 못 닿아도(300ms 안의 새로고침) 다음 시작 때 boot 가 그 값을 다시 올린다. 답(성공)·409 때 고쳐 쓰거나 지운다.
   보내기가 실패하면(도우미 꺼짐 등) 한 번 알리고 [hd] 경고, 바뀐 키는 다음 쓰기 때 같이 보낸다.
   살아 있는 새로 받기(A2a): 페이지가 보이는 동안 2초마다(숨으면 10초) GET /api/state. 파일 rev 가 더 크면 —
     보내지 않은 변경이 있으면 먼저 보낸다(409 = 위 충돌 길) · 바뀐 이름이 notes·note-seq·busy 뿐이면 제자리에서 받아(상태·캐시) ctx.onExternal(이름들) ·
     다른 이름(자리·폴더…)도 바뀌었으면 셸이 따로 들고 있으니 지금처럼 알리고 다시 불러오기. 네트워크 실패 3번 연속 = 멈추고 한 번 알림, 창에 돌아오면(focus) 다시.
     묻기는 GET /api/state?since=<rev>(#273) — 파일 rev 가 같으면 도우미가 {rev, unchanged:true} 만 답하고 아무것도 하지 않는다(옛 도우미의 전체 답도 그대로 받는다).
   413(상태가 너무 큼, #273) = 도우미의 {error} 글을 토스트로 한 번(성공할 때까지 다시 알리지 않음), 다음 변경까지 다시 보내지 않고 완료 메모 보관을 바로 해 본다.
   완료 메모 보관(#273): 쓰는 탭이 열 때와 그 뒤 한 시간에 한 번 HD.archive.pickArchive(Model) 로 고른 메모를 POST /api/archive {notes} →
     {ok} 일 때만 보낸 그대로인 메모를 notes 에서 빼고(HD.archive.without) 한 번 저장 + ctx.onExternal(['notes']). 실패 = [hd] 경고(다음 시간에 다시).
   두 탭(#274): BroadcastChannel('hd:' + hash) — 규칙은 HD.stateFile.tab(Model). 새 탭이 hello 를 알리고 쓰는 탭이 답하면 새 탭은 읽기만:
     PUT·닫을 때 보내기·보관·쓰기 대기 표시를 하지 않고(새로 받기는 그대로), 역할을 <html data-hd-tab> + document 'hd-tab-role' {role} 로 알린다 —
     편집은 view-read-only 가 처음부터 막고(흐린 조작부·aria-disabled·줄 가리키기), 그래도 닿은 프로젝트 키 쓰기는 버린다(토스트 한 번, 안전망). 위쪽에 '다른 탭에서 열려 있어요 — 여기서 편집하기' 줄,
     누르면 이 탭이 쓰는 탭(take — 다른 탭이 읽기만)이 되고, 읽기만일 때 버린 쓰기가 있었으면 파일 상태로 다시 불러온다. 정하기 전(tabWaitMs, 기본 150ms)에는 보내지 않는다.
   실시간(47-4b): live(true) = 2초 읽기를 멈추고 서버 이벤트(notes.changed·claim·release, rev 가 새것)가 poll() 을 부른다(view-live) · live(false) = 흐름이 끊김 → 2초 읽기 다시.
   HD.viewStateSync.mount(ctx) → {mode, getItem(k), setItem(k, v), removeItem(k), flush(), rev(), poll()(지금 한 번 — 테스트·focus·이벤트), role()('writer'|'reader'|'pending'), archive(force?), live(on)}
     mode = 'off'(file:// · 토큰 없음) | 'local'(스냅숏 깨짐) | 'file' | 'migrate'. off·local 이면 모든 키가 ctx.storage 그대로(던지는 것도 그대로)
   ctx = {hash, on, token, snapshot(window.__hdState), storage{getItem,setItem,removeItem}, toast(msg), warn(msg), reload(), onExternal(names)?, delayMs?(기본 300), pollMs?(기본 2000), idleMs?(기본 10000), tabWaitMs?(기본 150)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var CONFLICT = '다른 곳에서 바뀌어 다시 불러왔어요';
var FAILED = '캔버스 상태를 파일에 저장하지 못했어요 — 이 브라우저에만 남아요';
var LOST = '도우미에 닿지 않아 AI 답을 새로 받지 않아요 — 창을 다시 누르면 다시 시도해요';
var TOO_BIG = '캔버스 상태가 너무 커서 파일에 저장하지 못했어요 — 완료 메모를 보관으로 옮기세요';
var READ_ONLY = '다른 탭에서 편집 중이라 여기서 바꾼 것은 저장되지 않아요';
var HOUR = 3600000;

function mount(ctx) {
  var S = HD.stateFile, store = ctx.storage, on = !!(ctx.on && ctx.token);
  var mode = 'off', rev = 0, state = {}, base = {}, retried = false, reloadAfter = false, dirty = {}, inflight = [], timer = 0, busy = false, again = false, dead = false, failWarned = false, markWarned = false;

  function pass() {
    return {mode: mode, getItem: function (k) { return store.getItem(k); }, setItem: function (k, v) { store.setItem(k, v); },
            removeItem: function (k) { store.removeItem(k); }, flush: function () {}, rev: function () { return 0; }, poll: function () {},
            role: function () { return 'writer'; }, archive: function () {}, live: function () {}};
  }
  if (!on) return pass();
  var snap = S.snapshot(ctx.snapshot);
  if (!snap.ok) { mode = 'local'; ctx.warn('[hd] 상태 스냅숏이 깨져 브라우저 저장소만 써요: ' + snap.why); return pass(); }
  var local = S.fromLocal(function (k) { return store.getItem(k); }, ctx.hash);
  local.bad.forEach(function (n) { ctx.warn('[hd] 브라우저에 저장된 ' + n + ' 값이 깨져 버려요'); });
  var MARK = S.unsentKey(ctx.hash), markText = null;
  try { markText = store.getItem(MARK); } catch (e) { ctx.warn('[hd] 쓰기 대기 표시를 읽지 못했어요: ' + (e && e.message || e)); }
  var b = S.boot(snap, local.values, S.unsent(markText));
  var tabS = S.tabStart(Math.random().toString(36).slice(2) + Date.now().toString(36), Date.now() + (performance.now() % 1)), chan = null, dropped = false, roWarned = false, bar = null;
  var big = false, bigWarned = false, archiving = false, archivedAt = 0;
  function writer() { return tabS.role === 'writer'; }
  mode = b.mode; rev = b.rev; state = b.state; base = snap.state;   // base = 마지막으로 안 서버 상태(409 때 무엇이 서버에서 바뀌었나)
  Object.keys(b.cache).forEach(function (n) { cacheSet(n, b.cache[n]); });
  b.upload.forEach(function (n) { dirty[n] = 1; });
  if (b.lost.length) ctx.warn('[hd] 보내지 못한 변경이 그 사이 바뀐 파일에 밀려 버려져요: ' + b.lost.join(', '));
  mark();

  function cacheSet(n, text) {                      // 캐시일 뿐 — 못 써도(저장 공간 꽉 참) 파일이 진실 원천
    try { if (text == null) store.removeItem(S.keyOf(n, ctx.hash)); else store.setItem(S.keyOf(n, ctx.hash), text); } catch (e) {}
  }
  function names() { return Object.keys(dirty); }
  function mark() {                                 // 쓰기 대기 표시 = 모으는 중 ∪ 보내는 중, 기준 rev(보내는 중이면 그 답 전의 rev)
    if (!writer()) return;                           // 표시는 탭끼리 같은 저장소 — 쓰는 탭의 것을 지우지 않게(정하기 전에도)
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
  function conflict(lost) {
    dead = true; dirty = {}; inflight = []; clearTimeout(timer);
    mark();                                          // 이번 변경은 버린다(다시 연 페이지가 올리지 않게)
    if (lost && lost.length) {
      ctx.warn('[hd] 다른 곳에서 같이 바뀌어 보내지 못한 변경을 버려요: ' + lost.join(', '));
      ctx.toast(CONFLICT + ' — 잃은 변경: ' + HD.saveMerge.lostText(lost));
    } else ctx.toast(CONFLICT);
    ctx.reload();
  }
  function union(a, b) { var r = a.slice(); b.forEach(function (n) { if (r.indexOf(n) < 0) r.push(n); }); return r; }
  function rejected(j, sent) {                       // 409 — 서버 상태와 합쳐 한 번 다시 보내거나(잃는 것 없음), 둘 다 바꾼 이름을 알리고 다시 불러오기
    var d = union(sent, names()), snap = S.snapshot(j);
    if (!snap.ok) { ctx.warn('[hd] 409 답이 깨졌어요: ' + snap.why); return conflict(d); }
    if (retried) return conflict(d);
    var r = HD.saveMerge.resolve(d, base, state, snap.state);
    if (!r.ok) return conflict(r.lost);
    retried = true; rev = snap.rev; base = snap.state; state = r.state;
    d.forEach(function (n) { dirty[n] = 1; });
    inflight = []; mark();
    r.adopt.forEach(function (n) { cacheSet(n, S.read(state, n)); });
    if (r.adopt.some(function (n) { return !S.LIVE[n] && d.indexOf(n) < 0; })) reloadAfter = true;   // 자리·폴더 등은 셸이 따로 들고 있다 — 다시 보낸 뒤 다시 불러오기
    var live = r.adopt.filter(function (n) { return S.LIVE[n]; });
    if (live.length && ctx.onExternal) ctx.onExternal(live);
    again = true;                                    // 지금 보내는 중(busy) — 끝나면 바로 다시
  }
  function tooBig(sent, j) {                         // 413 — 다음 변경까지 다시 보내지 않는다(poll 도), 알림은 성공할 때까지 한 번
    sent.forEach(function (n) { dirty[n] = 1; });
    inflight = []; mark(); big = true;
    var msg = j && typeof j.error === 'string' && j.error ? j.error : TOO_BIG;
    ctx.warn('[hd] 상태 파일 저장 실패(413): ' + msg);
    if (!bigWarned) { bigWarned = true; ctx.toast(msg); }
    archive(true);
  }
  function flush() {
    clearTimeout(timer);
    if (dead || !writer()) return;                   // 정하기 전(pending) 것은 쓰는 탭이 되면 보낸다 · 읽기만이면 보내지 않는다
    if (busy) { again = true; return; }
    var sent = names(); if (!sent.length) return;
    dirty = {}; busy = true; inflight = sent;
    var bd = S.body(rev, state, sent);
    req(bd).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (r.status === 409) return rejected(j, sent);
        if (r.status === 413) return tooBig(sent, j);
        if (!r.ok || typeof j.rev !== 'number') return failed(sent, 'HTTP ' + r.status);
        rev = j.rev; failWarned = false; bigWarned = false; retried = false; inflight = []; mark();
        base = Object.assign({}, base);
        sent.forEach(function (n) { if (bd.state[n] == null) delete base[n]; else base[n] = bd.state[n]; });
        if (reloadAfter) { reloadAfter = false; conflict(names()); }   // 합쳐 다시 보냄 — 이제 파일 상태로 다시 불러오기
      });
    }, function (e) { failed(sent, String(e && e.message || e)); }).then(function () {
      busy = false;
      if (again) { again = false; flush(); }
    });
  }
  function onLeave() {                               // 닫기·새로고침 — 모아 둔 변경을 마저(답은 못 받는다 — 쓰기 대기 표시는 그대로 둔다)
    if (dead || !writer()) return;
    var sent = names(); if (!sent.length) return;
    dirty = {}; clearTimeout(timer);
    try { req(S.body(rev + (busy ? 1 : 0), state, sent), true).catch(function () {}); } catch (e) {}   // 보내는 중인 것이 있으면 그 답의 rev 를 미리(틀리면 409 — 페이지는 이미 떠남)
  }
  addEventListener('pagehide', onLeave);
  addEventListener('beforeunload', onLeave);
  if (b.upload.length) schedule();                  // 파일이 없을 때 브라우저 값 한 번 올리기(rev 0 → 1)

  var ptimer = 0, polling = false, fails = 0, stopped = false, liveOn = false;
  function same(a, b) { return JSON.stringify(a == null ? null : a) === JSON.stringify(b == null ? null : b); }
  function next(soon) {                               // 실시간(47-4b)이면 주기 읽기 없음 — 이벤트가 poll() 을 부른다(보내는 중이라 미룬 것만 soon 뒤 한 번)
    clearTimeout(ptimer); ptimer = 0;
    if (dead || stopped) return;
    if (liveOn) { if (soon) ptimer = setTimeout(poll, soon); return; }
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
    if (changed.some(function (n) { return !S.LIVE[n]; })) { conflict(); return; }   // 자리·폴더 등은 셸이 따로 들고 있다 — 지금처럼 다시 불러오기
    rev = snap.rev; state = snap.state; base = snap.state;
    changed.forEach(function (n) { cacheSet(n, S.read(state, n)); });
    if (changed.length && ctx.onExternal) ctx.onExternal(changed);
  }
  function poll() {
    clearTimeout(ptimer); ptimer = 0;
    if (dead || stopped || polling) return;
    if (busy) { next(500); return; }                 // 보내는 중 — 그 답의 rev 를 받은 뒤에
    if (names().length) { if (!big && writer()) flush(); next(500); return; }  // 보내지 않은 변경 먼저(파일이 앞서 있으면 409 = 충돌 길) · 413 뒤엔 다음 변경까지 쉰다
    archive(false);
    polling = true;
    fetch('/api/state?since=' + rev, {headers: {'X-HD-Token': ctx.token}, cache: 'no-store'}).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      fails = 0;
      if (j && j.unchanged === true) return;          // 파일 rev 가 그대로(#273) — 본문 없음
      if (!dead && !busy && !names().length) take(j);   // 기다리는 사이 바뀐 것이 있으면 다음 번에
    }, function (e) { if (liveOn) ctx.warn('[hd] 상태 다시 읽기 실패: ' + String(e && e.message || e)); else lost(String(e && e.message || e)); }).then(function () { polling = false; next(); });
  }
  function archive(force) {                          // 완료 메모 보관(#273) — 쓰는 탭만, 한 시간에 한 번(413 이면 바로)
    if (dead || archiving || !writer() || !HD.archive) return;
    var now = Date.now();
    if (!force && archivedAt && now - archivedAt < HOUR) return;
    archivedAt = now;
    var picks = HD.archive.pickArchive(state.notes, now);
    if (!picks.length) return;
    archiving = true;
    fetch('/api/archive', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-HD-Token': ctx.token}, body: JSON.stringify({notes: picks})}).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok || !j || j.ok !== true) { ctx.warn('[hd] 완료 메모 보관 실패: HTTP ' + r.status + (j && j.error ? ' ' + j.error : '')); return; }
        if (dead || !writer()) { ctx.warn('[hd] 보관한 완료 메모를 이 탭에서 빼지 못했어요(쓰는 탭이 아님) — 다음 보관 때 다시 보내요'); return; }
        var left = HD.archive.without(state.notes, picks);
        if (!Array.isArray(state.notes) || left.length === state.notes.length) return;
        var gone = state.notes.length - left.length;
        state = S.write(state, 'notes', JSON.stringify(left)).state;
        cacheSet('notes', S.read(state, 'notes')); dirty.notes = 1; big = false; mark(); schedule();
        ctx.warn('[hd] 완료 메모 ' + gone + '개를 보관으로 옮겼어요(.hd-notes-archive.jsonl)');
        if (ctx.onExternal) ctx.onExternal(['notes']);
      });
    }, function (e) { ctx.warn('[hd] 완료 메모 보관 실패: ' + String(e && e.message || e)); }).then(function () { archiving = false; });
  }

  function showBar(on) {                              // 읽기만인 탭 위쪽 줄 — 누르면 이 탭에서 편집
    if (!on) { if (bar) { bar.hidden = true; bar.style.display = 'none'; } return; }   // 글 안 display:flex 가 hidden 을 이긴다 — 같이 끈다
    if (!bar) {
      bar = document.createElement('div'); bar.id = 'hd-tab-lock'; bar.setAttribute('role', 'status');
      bar.style.cssText = 'position:fixed;top:40px;left:50%;transform:translateX(-50%);z-index:45;background:var(--ui-primary);color:#fff;border-radius:10px;padding:7px 12px;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,.2);display:flex;gap:8px;align-items:center';
      var t = document.createElement('span'); t.textContent = '다른 탭에서 열려 있어요 —';
      var btn = document.createElement('button'); btn.type = 'button'; btn.textContent = '여기서 편집하기';
      btn.style.cssText = 'border:0;background:none;color:#fff;text-decoration:underline;font:inherit;font-weight:700;cursor:pointer;padding:0';
      btn.addEventListener('click', function () { tabEvent({type: 'click'}); });
      bar.appendChild(t); bar.appendChild(btn);
      (document.body || document.documentElement).appendChild(bar);
    }
    bar.hidden = false; bar.style.display = 'flex';
  }
  function tabEvent(ev) {
    var prev = tabS.role, r = S.tab(tabS, ev);
    tabS = r.s;
    if (r.send && chan) { try { chan.postMessage(r.send); } catch (e) { ctx.warn('[hd] 다른 탭에 알리지 못했어요: ' + (e && e.message || e)); } }
    if (tabS.role === prev) return;
    announce(tabS.role);
    if (tabS.role === 'reader') {
      clearTimeout(timer); dirty = {};               // 정하기 전에 모은 것(시작 때 고친 값)은 쓰는 탭이 이미 가졌다
      showBar(true);
      return;
    }
    showBar(false);                                   // writer
    if (prev === 'reader' && dropped) { dead = true; ctx.reload(); return; }   // 읽기만일 때 버린 쓰기 = 셸이 든 값이 파일과 다름 — 파일 상태로 다시
    mark();
    if (names().length) schedule();
    if (prev === 'reader') poll();
    archive(false);
  }
  function announce(r) {                              // 역할을 화면에 알림 — 편집 막기(view-read-only)가 읽는다
    try { document.documentElement.dataset.hdTab = r; document.dispatchEvent(new CustomEvent('hd-tab-role', {detail: {role: r}})); }
    catch (e) { ctx.warn('[hd] 탭 역할을 알리지 못했어요: ' + (e && e.message || e)); }
  }
  function readOnly(k) {                              // 안전망 — 편집은 view-read-only 가 먼저 막는다. 그래도 닿은 쓰기는 버리고 한 번 알림
    dropped = true;
    ctx.warn('[hd] 다른 탭이 쓰는 중이라 버려요: ' + k);
    if (!roWarned) { roWarned = true; ctx.toast(READ_ONLY); }
  }
  if (typeof BroadcastChannel === 'function') {
    try {
      chan = new BroadcastChannel('hd:' + ctx.hash);
      chan.onmessage = function (e) { tabEvent(e.data); };
      chan.postMessage({type: 'hello', id: tabS.id, t: tabS.t});
      setTimeout(function () { tabEvent({type: 'timeout'}); }, ctx.tabWaitMs == null ? 150 : ctx.tabWaitMs);
    } catch (e) { chan = null; ctx.warn('[hd] 탭 사이 알림을 못 써 이 탭이 씁니다: ' + (e && e.message || e)); tabEvent({type: 'timeout'}); }
  } else tabEvent({type: 'timeout'});

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
      if (tabS.role === 'reader') { readOnly(k); return; }
      big = false;
      var w = S.write(state, n, String(v));
      cacheSet(n, String(v));
      if (!w.ok) { ctx.warn('[hd] JSON 이 아닌 값은 파일에 쓰지 않아요: ' + k); return; }
      state = w.state; dirty[n] = 1; mark(); schedule();
    },
    removeItem: function (k) {
      var n = S.nameOf(k, ctx.hash);
      if (!n) { store.removeItem(k); return; }
      if (tabS.role === 'reader') { readOnly(k); return; }
      big = false;
      state = S.drop(state, n); cacheSet(n, null); dirty[n] = 1; mark(); schedule();
    },
    flush: flush,
    rev: function () { return rev; },
    poll: poll,
    role: function () { return tabS.role; },
    archive: archive,
    live: function (on) { liveOn = !!on; if (!liveOn && !polling) { if (stopped) { stopped = false; fails = 0; } next(); } else if (liveOn) next(); }   // 실시간 켜기 = 주기 읽기 멈춤 · 끄기 = 2초 읽기 다시
  };
}

HD.viewStateSync = {mount: mount};
})();
