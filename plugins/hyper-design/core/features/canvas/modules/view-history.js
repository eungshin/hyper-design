/* View — 기록 패널(#hlist)과 되돌리기·다시 하기: 시간줄 하나(E8)의 주인. 상태는 HD.history 리듀서, 줄을 누르면 그 단계로(E2).
   되돌리기 Ctrl+Z · 버튼 · 줄 누르기가 모두 여기 하나로 온다. 보낸 자리 앞은 경계선 — 되돌릴 수 없다.
   HD.viewHistory.mount(ctx) → {record(op), undo(), redo(), go(to), sent(), applied(), state()}   op = {label, undo(), redo(), status?}
   ctx = {$, esc, list, undoBtn, redoBtn, toast(msg), getItem(k), setItem(k, v), key} — key 에 지난 줄을 남긴다(최근 200) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var H = HD.history, esc = ctx.esc, list = ctx.list, st;
  try { st = H.initial(JSON.parse(ctx.getItem(ctx.key) || '[]')); } catch (e) { st = H.initial([]); }

  function time() { var d = new Date(); return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  function set(next) {
    st = next;
    try { ctx.setItem(ctx.key, JSON.stringify(H.saved(st))); } catch (e) {}
    render();
  }
  function render() {
    var lu = st.rows[st.at - 1], lr = st.rows[st.at];
    ctx.undoBtn.disabled = !H.canUndo(st); ctx.redoBtn.disabled = !H.canRedo(st);
    ctx.undoBtn.title = '되돌리기' + (H.canUndo(st) ? ': ' + lu.label : '') + ' (Ctrl+Z)';
    ctx.redoBtn.title = '다시 하기' + (lr ? ': ' + lr.label : '') + ' (Ctrl+Shift+Z)';
    var h = '<li data-i="0" class="hstart' + (st.lock > 0 ? ' lock' : '') + '"><span class="hl">시작</span></li>';
    st.rows.forEach(function (r, k) {
      var i = k + 1;
      h += '<li data-i="' + i + '" class="' + (i > st.at ? 'undone' : '') + (i < st.lock ? ' lock' : '') + (i === st.at ? ' now' : '') + '">' +
        '<span class="hl">' + esc(r.label) + '</span><span class="hs hs-' + r.status + '">' + esc(H.STATUS[r.status]) + '</span><span class="ht">' + esc(r.at) + '</span></li>';
      if (i === st.lock && st.lock > 0) h += '<li class="hbound" aria-label="되돌릴 수 없는 경계">↑ 보냈거나 지난 일 — 되돌릴 수 없어요</li>';
    });
    list.innerHTML = h;
    var now = list.querySelector('li.now'); if (now && now.scrollIntoView) now.scrollIntoView({block: 'nearest'});
  }
  function go(to) {
    var s = H.steps(st, to);
    s.undo.forEach(function (r) { r.op.undo(); });
    s.redo.forEach(function (r) { r.op.redo(); });
    set(H.reduce(st, {type: 'go', to: to}));
  }
  function record(op) { set(H.reduce(st, {type: 'record', row: {label: op.label, status: op.status || 'canvas', at: time(), op: op}})); }
  function undo() {
    if (!H.canUndo(st)) { if (st.at > 0) ctx.toast('보냈거나 지난 일은 되돌릴 수 없어요'); return; }
    var r = st.rows[st.at - 1]; go(st.at - 1); ctx.toast('되돌렸어요: ' + r.label);
  }
  function redo() {
    if (!H.canRedo(st)) return;
    var r = st.rows[st.at]; go(st.at + 1); ctx.toast('다시 했어요: ' + r.label);
  }
  list.addEventListener('click', function (e) {
    var li = e.target.closest && e.target.closest('li[data-i]');
    if (!li || li.classList.contains('lock')) return;
    go(+li.dataset.i);
  });
  render();
  return {record: record, undo: undo, redo: redo, go: go, state: function () { return st; },
          sent: function () { set(H.reduce(st, {type: 'sent'})); }, applied: function () { set(H.reduce(st, {type: 'applied'})); }};
}

HD.viewHistory = {mount: mount};
})();
