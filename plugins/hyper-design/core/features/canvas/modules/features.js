/* ViewModel — 기능 등록부: 기능마다 이름·필요한 ctx 칸(needs)·mount 를 받아 두고, 셸이 한 번 mountAll(ctx) 로 붙인다. DOM·저장소를 쓰지 않는다.
   새 기능은 셸·빌드·conftest 를 고치지 않는다 — View 모듈이 읽힐 때 등록하면 끝(빌드는 modules/*.js 를 모두 끼우고, 이 파일이 view-* 보다 먼저 읽힌다).
   HD.feature(name, {needs: ['$', 'toast', …], mount(ctx) → api})   같은 이름 두 번 = 뒤의 것은 버리고 [hd] 오류
   HD.mountAll(ctx) → {이름: api}   등록 차례대로 한 번만. needs 칸이 ctx 에 없거나 mount 가 던지면 그 기능만 건너뛰고
     [hd] console.error + ctx.toast(있으면) — 나머지 기능은 그대로 붙는다. 두 번 부르면 처음 것을 돌려주고 [hd] 오류.
   HD.features = {names(), missing(needs, ctx) → 없는 칸 이름들, errors() → 지금까지의 오류 글}
   셸이 건네는 ctx 칸(canvas_template.html 의 mountAll 한 곳): $ · $$ · esc · toast(msg, withUndo, ms) · warn(msg) · rowsEl · CARD ·
     title(id) · cardEl(id) · notes{list(), find(id), save()} · store{getItem, setItem, removeItem}(프로젝트 키 = 상태 파일) ·
     local{getItem, setItem, removeItem}(전역 설정 키) · key(prefix) → 'prefix:' + 프로젝트 해시 · record(op) · prefs() · savePrefs() ·
     frameLoaded(id, frame) — 카드 iframe 이 막 실림: 셸이 테마(hd-palette·hd-theme-vars)·반영 대기(hd-pending)·메모 자리(hd-locate)를 보낸다(48a 교체가 만든 새 틀) ·
     cardPos(view-card-pos api: at·put·place·move·group) · locked(id) · lines()(끄는 중 선 다시) — R31 폴더째 옮기기 ·
     selected() → 고른 카드 id 목록 · picked() → 고른 요소 {screen, h, app}|null(요소 막대) · pickedAll() → 판에서 고른 요소 모두 [{screen, h, app}](고른 차례, 마지막 = 막대, R19) · sendNotes(list) → 메모를 더하고 바로 보내기(보내는 중이면 false, S1 대화창) · boardNotes() → 고른 판 메모 [{id, text, x, y, w, h}](판 좌표, R25 대화창 노트 칩 — 읽기만) · boardLinks() → 판 메모 선 map(R47, 없으면 {} — 읽기만)
     · dock{state(), dispatch(a, quiet?), absent(), render()} — 도크 배치(dock.js) 읽기·의도(R53 대화 창 붙이기·떼기 — 배치의 주인은 view-dock)
     · focus(ids, maxZ?) — 그 카드들로 판 옮기기(fitCards, maxZ 없으면 지금 배율보다 크게는 안 함)
     · api{on, call(method, path, body)} · reload(ids, opt?{stamp, echo}) — 그 카드들을 교체 길로 다시 싣기(실시간 알림이 같은 쓰기를 이미 실었으면 건너뜀, echo = 되살리기 notify 의 메아리 한 번 먹기 — 47-4b) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};
var list = [], byName = {}, errs = [], done = null;

function fail(msg, ctx) {
  errs.push(msg);
  if (typeof console !== 'undefined') console.error('[hd] ' + msg);
  if (ctx && typeof ctx.toast === 'function') { try { ctx.toast('기능을 붙이지 못했어요 — ' + msg); } catch (e) {} }   // 알림이 실패해도 콘솔에는 남았다
}

function feature(name, spec) {
  if (typeof name !== 'string' || !name) { fail('기능 이름이 없어요', null); return; }
  if (byName[name]) { fail('같은 이름의 기능을 두 번 등록했어요: ' + name, null); return; }
  if (!spec || typeof spec.mount !== 'function') { fail(name + ': mount(ctx) 가 없어요', null); return; }
  var f = {name: name, needs: Array.isArray(spec.needs) ? spec.needs.slice() : [], mount: spec.mount};
  byName[name] = f; list.push(f);
}

function missing(needs, ctx) {
  return (needs || []).filter(function (k) { return !ctx || ctx[k] == null; });
}

function mountAll(ctx) {
  if (done) { fail('mountAll 을 두 번 불렀어요 — 처음 붙인 것을 돌려줘요', null); return done; }
  done = {};
  list.forEach(function (f) {
    var lack = missing(f.needs, ctx);
    if (lack.length) { fail(f.name + ': ctx 에 없는 칸 ' + lack.join(', '), ctx); return; }
    try { done[f.name] = f.mount(ctx); }
    catch (e) { fail(f.name + ': mount 실패 — ' + (e && e.message || e), ctx); }
  });
  return done;
}

HD.feature = feature;
HD.mountAll = mountAll;
HD.features = {
  names: function () { return list.map(function (f) { return f.name; }); },
  missing: missing,
  errors: function () { return errs.slice(); }
};
})();
