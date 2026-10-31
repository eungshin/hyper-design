/* View — 기록 패널(#hlist)과 되돌리기·다시 하기: 시간줄 하나(E8)의 주인. 상태는 HD.history 리듀서, 줄을 누르면 그 줄 바로 뒤 상태로(E2, 포토샵처럼 — 아래 줄은 흐리게 = 다시 하기).
   되돌리기 Ctrl+Z · 버튼 · 줄 누르기(Enter 도) 가 모두 여기 하나로 온다. 잠긴 줄을 누르면 까닭을 토스트로(보냄·파일에 씀·너무 오래됨·지난 세션 화면 설정).
   Ctrl+Z·버튼은 이번 세션 줄까지만(HD.history.canUndo) — 지난 세션 줄은 줄 누르기로만 되돌린다(F15, 막히면 까닭 토스트).
   줄마다 상태 차이(d)를 잡는다: 기록 직전 상태(base)와 기록 때 상태의 차이. base 는 한 일이 끝난 뒤(다음 차례, setTimeout 0) 다시 읽어
     기록 없이 바뀐 것(AI 답·번호 매기기)은 다음 줄에 섞이지 않는다 — 한 일과 그 기록이 같은 차례에 일어나야 한다(셸의 record 자리 모두 그렇다).
   이번 세션 줄은 op 로, 지난 세션 줄은 d 를 ctx.track.write 로 되쓰고 ctx.adopt(이름들) 로 셸이 다시 읽어 그린다(상태 주인은 셸·state-sync 그대로).
   HD.viewHistory.mount(ctx) → {record(op), undo(), redo(), go(to), sent(), applied(), wrote(이름), state()}   op = {label, undo(), redo(), status?}
   op.bind?(f) — 줄이 생길 때 표시 함수 f(note)를 받는다: 그 줄 옆에 짧은 표시(.hn)를 붙이거나('' 이면 지움) 다시 그린다(47-5b, 저장 안 함).
   ctx = {$, esc, list, undoBtn, redoBtn, toast(msg), getItem(k), setItem(k, v), key, track?{read(이름) → 값|null, write(이름, 값|null)}, adopt?(이름들), warn?(msg)}
     key 에 지난 줄을 남긴다(최근 200, d 는 새것부터 1 MB) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var H = HD.history, esc = ctx.esc, list = ctx.list, st, scrollRaf = 0, track = ctx.track, base = null, baseT = 0;
  try { st = H.initial(JSON.parse(ctx.getItem(ctx.key) || '[]')); } catch (e) { st = H.initial([]); if (ctx.warn) ctx.warn('[hd] 기록(edit-log)이 깨져 비우고 시작해요'); }
  if (ctx.warn && st.rows.some(function (r) { return r.bad; })) ctx.warn('[hd] 기록 줄의 상태 차이가 깨져 그 줄은 되돌릴 수 없어요');

  function readAll() {
    var o = {}; if (!track) return o;
    H.TRACK.forEach(function (n) { try { o[n] = track.read(n); } catch (e) { o[n] = null; } });   // 못 읽은 이름 = 없음(그 줄의 차이가 커질 뿐)
    return o;
  }
  base = readAll();
  function wrote() {                                 // 상태가 바뀜 — 이 차례가 끝나면 base 를 새로(같은 차례의 record 가 먼저 쓴다)
    if (!track || baseT) return;
    baseT = setTimeout(function () { baseT = 0; base = readAll(); }, 0);
  }
  function rebase() { clearTimeout(baseT); baseT = 0; base = readAll(); }

  function time() { var d = new Date(); return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  function set(next) {
    st = next;
    try { ctx.setItem(ctx.key, JSON.stringify(H.saved(st))); } catch (e) {}   // 저장 실패 = 이번 세션 기록은 그대로(새로고침하면 잃음)
    render();
  }
  function reason() { return H.REASON[H.why(st)] || '되돌릴 수 없어요'; }
  function render() {
    var lu = st.rows[st.at - 1], lr = st.rows[st.at];
    ctx.undoBtn.disabled = !H.canUndo(st); ctx.redoBtn.disabled = !H.canRedo(st);
    ctx.undoBtn.title = '되돌리기' + (H.canUndo(st) ? ': ' + lu.label : '') + ' (Ctrl+Z)';
    ctx.redoBtn.title = '다시 하기' + (lr ? ': ' + lr.label : '') + ' (Ctrl+Shift+Z)';
    var h = '<li data-i="0" tabindex="0" class="hstart' + (st.lock > 0 ? ' lock' : '') + (st.at === 0 ? ' now' : '') + '"><span class="hl">시작</span></li>';
    st.rows.forEach(function (r, k) {
      var i = k + 1;
      h += '<li data-i="' + i + '" tabindex="0" class="' + (i > st.at ? 'undone' : '') + (i < st.lock ? ' lock' : '') + (i === st.at ? ' now' : '') + '">' +
        '<span class="hl">' + esc(r.label) + '</span>' + (r.note ? '<span class="hn">' + esc(r.note) + '</span>' : '') + '<span class="hs hs-' + r.status + '">' + esc(H.STATUS[r.status]) + '</span><span class="ht">' + esc(r.at) + '</span></li>';
      if (i === st.lock && st.lock > 0) h += '<li class="hbound" aria-label="되돌릴 수 없는 경계">↑ ' + esc(reason()) + '</li>';
    });
    list.innerHTML = h;
    if (!scrollRaf) scrollRaf = (typeof requestAnimationFrame === 'function' ? requestAnimationFrame : setTimeout)(function () {   // 다음 그림 때 한 번 — 저장 직후 배치를 강제로 읽지 않는다(P3)
      scrollRaf = 0;
      var now = list.querySelector('li.now'); if (now && now.scrollIntoView && list.getClientRects().length) now.scrollIntoView({block: 'nearest'});   // 기록 패널이 보일 때만
    });
  }
  function go(to) {
    var s = H.steps(st, to), touched = {};
    function flush() { var n = Object.keys(touched); if (n.length && ctx.adopt) ctx.adopt(n); touched = {}; }
    function data(r, side) {                          // 지난 세션 줄: 지금 값에 차이를 덮어 쓴다
      var names = Object.keys(r.d), cur = {};
      names.forEach(function (n) { cur[n] = track.read(n); });
      var next = H.patch(cur, r.d, side);
      names.forEach(function (n) { track.write(n, next[n]); touched[n] = 1; });
    }
    function one(r, side) {
      if (r.op) { flush(); r.op[side === 'before' ? 'undo' : 'redo'](); }   // 셸이 들고 있는 값을 먼저 맞춘 뒤 op
      else if (r.d && track) data(r, side);
    }
    try {
      s.undo.forEach(function (r) { one(r, 'before'); });
      s.redo.forEach(function (r) { one(r, 'after'); });
      flush();
    } catch (e) {
      if (ctx.warn) ctx.warn('[hd] 기록 줄로 가지 못했어요: ' + (e && e.message || e));
      ctx.toast('그 단계로 가지 못했어요 — 상태를 다시 읽어 주세요(새로고침)');
    }
    set(H.reduce(st, {type: 'go', to: to}));
    rebase();
  }
  function record(op) {
    var cur = readAll(), d = track ? H.diff(base, cur) : null, row = {label: op.label, status: op.status || 'canvas', at: time(), op: op};
    if (d) row.d = d;
    if (typeof op.bind === 'function') op.bind(function (note) { st.rows.forEach(function (r) { if (r.op === op) r.note = note ? String(note) : ''; }); render(); });   // 줄 표시(47-5b: 되돌리기 답 '빌드 실패로 이미 되돌림') — 이번 세션만, 저장 안 함
    base = cur; clearTimeout(baseT); baseT = 0;
    set(H.reduce(st, {type: 'record', row: row}));
  }
  function undo() {
    if (!H.canUndo(st)) { if (st.at > 0) ctx.toast(H.REASON[H.undoWhy(st)] || '되돌릴 수 없어요'); return; }   // 지난 세션 줄 = 기록 패널에서만(F15)
    var r = st.rows[st.at - 1]; go(st.at - 1); ctx.toast('되돌렸어요: ' + r.label);
  }
  function redo() {
    if (!H.canRedo(st)) return;
    var r = st.rows[st.at]; go(st.at + 1); ctx.toast('다시 했어요: ' + r.label);
  }
  function press(li) {
    if (!li) return;
    var i = +li.dataset.i;
    if (i < st.lock) { ctx.toast(reason()); return; }   // 조용히 무시하지 않는다
    go(i);
  }
  list.addEventListener('click', function (e) { press(e.target.closest && e.target.closest('li[data-i]')); });
  list.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var li = e.target.closest && e.target.closest('li[data-i]'); if (!li) return;
    e.preventDefault(); e.stopPropagation(); press(li);
  });
  render();
  return {record: record, undo: undo, redo: redo, go: go, wrote: wrote, state: function () { return st; },
          sent: function () { set(H.reduce(st, {type: 'sent'})); }, applied: function () { set(H.reduce(st, {type: 'applied'})); }};
}

HD.viewHistory = {mount: mount};
})();
