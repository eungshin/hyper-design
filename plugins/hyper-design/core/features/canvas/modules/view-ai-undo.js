/* View — AI 되돌리기(48c): AI 가 덮개(hd claim) 동안 쓴 화면마다 기록 패널에 'AI 반영 · <화면>' 한 줄(파일에 씀)을 올리고, 되돌리기·다시 하기 = 도우미 되살리기.
   상태: since(마지막 seq) · seen(올린 stamp) · 줄마다 cur(다음에 되살릴 stamp — 되살릴 때마다 반대쪽 stamp 를 받는다). 규칙은 HD.aiUndo(Model).
   ctx = {api{on, call}, record(op), toast(msg), warn?(msg), cardEl?(id)} — 도우미가 없으면(api.on 거짓) 아무것도 하지 않는다.
   되살린 카드는 이 기능이 바로 다시 싣는다(cardEl 의 .phone iframe, 주소 = HD.aiUndo.again) — 지켜보기(notify)만 믿으면 AI 반영 직후 5초 안의 되돌리기가 view-busy 의 건너뛰기에 막힌다.
   2초마다(숨은 탭은 건너뜀) GET /api/ai-writes?since=. HD.feature('aiUndo') → {poll()} | {} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var A = HD.aiUndo;
  if (!ctx.api || !ctx.api.on) return {};
  var since = null, seen = {}, timer = 0, warned = false;
  var warn = function (m) { if (ctx.warn) ctx.warn(m); else console.warn(m); };

  function restore(row) {
    return ctx.api.call('POST', '/api/restore', A.body(row.cur)).then(function (res) {
      var o = A.outcome(res);
      if (o.ok) { row.cur = o.next; reload(res.body.changed); } else ctx.toast(o.msg);
    }, function (e) { ctx.toast('되돌리지 못했어요 — 도우미에 닿지 않아요: ' + row.label); warn('[hd] AI 반영 되살리기: ' + (e && e.message || e)); });
  }

  function reload(ids) {
    if (!ctx.cardEl || !Array.isArray(ids)) return;
    ids.forEach(function (id) {
      var c = ctx.cardEl(id), f = c && c.querySelector('.phone iframe'), url = f && A.again(f.getAttribute('src') || f.getAttribute('data-src'), Date.now());
      if (url) f.setAttribute('src', url);
    });
  }

  function add(w) {
    seen[w.stamp] = 1;
    var row = {cur: w.stamp, label: w.label};
    ctx.record({label: w.label, status: 'file', undo: function () { restore(row); }, redo: function () { restore(row); }});
  }

  function poll() {
    timer = 0;
    if (typeof document !== 'undefined' && document.hidden) { next(); return Promise.resolve(); }
    return ctx.api.call('GET', '/api/ai-writes?since=' + (since == null ? -1 : since)).then(function (res) {
      var b = res && res.body;
      if (!res || res.status !== 200 || !b || typeof b.seq !== 'number') { if (!warned) { warned = true; warn('[hd] /api/ai-writes 답이 깨졌어요'); } return; }
      warned = false;
      var base = A.first(since, b.seq);
      since = b.seq;
      if (!base) A.fresh(seen, b.writes).forEach(add);
    }, function (e) {
      if (!warned) { warned = true; warn('[hd] AI 반영 기록을 받지 못했어요(다시 시도): ' + (e && e.message || e)); }
    }).then(next, next);
  }
  function next() { clearTimeout(timer); timer = setTimeout(poll, A.EVERY); }

  poll();
  return {poll: poll};
}

HD.feature('aiUndo', {needs: ['api', 'record', 'toast'], mount: mount});
})();
