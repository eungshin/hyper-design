/* View — 빈 레이아웃 승격을 판에 적용(#241 R2): AI 가 만든 화면이 빈 레이아웃 카드 자리·폴더·선·메모를 이어받고 빈 카드는 사라진다, 되돌리기 한 단계 + 알림.
   규칙(언제·무엇이 바뀌나)은 modules/promote.js(Model). 상태 없음 — 메모·카드 자리·폴더의 주인은 셸이고 여기는 attach 로 받은 읽기/쓰기만 부른다.
   HD.viewPromote.mount(ctx) → {attach(shell) → {check() → 승격한 수}}
     ctx = 기능 등록부 공통 칸 $$ · rowsEl · notes{list, save} · toast · record · title · warn
     shell = {pos: {get() → 카드 옮긴 거리 {id: {dx, dy, g}}, set(map)}, folders: {get(), set(state)}, group(id) → 그 카드의 줄 이름,
              size?: {get() → 카드 크기 맵, set(map)} — 있으면 빈 레이아웃 크기를 화면으로(artboard.carry, task 46)}
   check 는 셸이 데이터·메모가 바뀐 뒤 부른다(시작 · 파일에서 온 메모 · 화면 파일을 다시 받은 뒤) — 승격할 것이 없으면 아무것도 하지 않는다.
   붙이기: 기능 등록부(modules/features.js)에 'promote' 로 등록, 셸은 mountAll 결과의 promote.attach 로 카드 자리·폴더를 넘긴다 */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var P = HD.promote;
  function card(id) { var hit = null; ctx.$$('.card', ctx.rowsEl).forEach(function (c) { if (c.dataset.id === id) hit = c; }); return hit; }
  function box(c, rr, z) {                           // 카드 화면(.phone) 왼쪽 위의 판 좌표 — 빈 카드와 화면 카드를 같은 기준점으로
    var ph = c && (c.querySelector('.phone') || c); if (!ph || !c.offsetWidth) return null;
    var r = ph.getBoundingClientRect();
    return {x: (r.left - rr.left) / z, y: (r.top - rr.top) / z};
  }
  function measure(sh, draft, screen) {
    var rr = ctx.rowsEl.getBoundingClientRect(), z = ctx.rowsEl.offsetWidth ? rr.width / ctx.rowsEl.offsetWidth : 1;
    var d = box(card(draft), rr, z || 1), s = box(card(screen), rr, z || 1);
    if (!d || !s) { ctx.warn('[hd] 승격: 카드 자리를 잴 수 없어 화면 자리는 그대로 둬요 — ' + draft + ' → ' + screen); return null; }
    return {draft: d, screen: s, g: sh.group(screen)};
  }
  function put(list) {                               // 메모는 셸이 붙잡고 있는 객체 그대로 두고 칸만 바꾼다(되돌리기 기록이 객체를 붙잡고 있다) — id, 없으면 같은 자리
    var cur = ctx.notes.list(), byId = {};
    list.forEach(function (m) { if (m && m.id != null) byId[m.id] = m; });
    cur.forEach(function (n, i) {
      var m = n && n.id != null ? byId[n.id] : list[i]; if (!m || !n) return;
      Object.keys(n).forEach(function (k) { if (!Object.prototype.hasOwnProperty.call(m, k)) delete n[k]; });
      Object.keys(m).forEach(function (k) { n[k] = JSON.parse(JSON.stringify(m[k])); });
    });
  }
  function attach(sh) {
    function apply(st) { put(st.notes); ctx.notes.save(); sh.pos.set(st.cardPos); sh.folders.set(st.folders); if (sh.size && st.sizes) sh.size.set(st.sizes); }
    function check() {
      var ids = ctx.$$('.card:not(.draft)', ctx.rowsEl).map(function (c) { return c.dataset.id; });
      var todo = P.promotable(ctx.notes.list(), ids); if (!todo.length) return 0;
      var st = {notes: ctx.notes.list(), cardPos: sh.pos.get(), folders: sh.folders.get()}, first = null, done = [];
      todo.forEach(function (p) {
        var r = P.promote(st, p.draft, p.screen, measure(sh, p.draft, p.screen)); if (!r) return;
        if (!first) first = r.undo;
        st = r.state; done.push({p: p, r: r});
      });
      if (!done.length) return 0;
      var after = st, before = first;
      if (sh.size && HD.artboard) {                  // 빈 레이아웃 크기(task 46) → 이어받는 화면 — 되돌리면 빈 카드로
        var s0 = sh.size.get(), s1 = s0;
        done.forEach(function (d) { s1 = HD.artboard.carry(s1, d.p.draft, d.p.screen); });
        before = Object.assign({}, before, {sizes: s0}); after = Object.assign({}, after, {sizes: s1});
      }
      apply(after);
      ctx.record({label: done.length > 1 ? '빈 레이아웃 ' + done.length + '개 자리에 화면' : '빈 레이아웃 자리에 화면',
                  undo: function () { apply(before); }, redo: function () { apply(after); }});
      var d0 = done[0];
      ctx.toast(P.say(d0.r.name, ctx.title(d0.p.screen), d0.r.moved) + (done.length > 1 ? ' 외 ' + (done.length - 1) + '개' : ''), true, 8000);
      return done.length;
    }
    return {check: check};
  }
  return {attach: attach};
}

HD.viewPromote = {mount: mount};
HD.feature('promote', {needs: ['$$', 'rowsEl', 'notes', 'toast', 'record', 'title', 'warn'], mount: mount});
})();
