/* View — 고른 카드 표시(.picked). 상태 주인은 HD.selection 리듀서 하나, 바뀌면 셸에 알린다(선택 막대·연결 강조는 셸이 잇는다).
   HD.viewSelect.mount(ctx) → {dispatch(intent), state(), ids(), has(id), primary()}
   ctx = {rowsEl, $$, onChange(state, prev)} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function mount(ctx) {
  var S = HD.selection, st = S.initial();
  function paint() {
    var on = {}; st.ids.forEach(function (id) { on[id] = 1; });
    ctx.$$('.card', ctx.rowsEl).forEach(function (c) { c.classList.toggle('picked', !!on[c.dataset.id]); });
  }
  function dispatch(a) {
    var prev = st; st = S.reduce(st, a);
    paint();                                          // 같은 상태여도 다시 칠한다(카드가 새로 그려졌을 수 있다)
    if (ctx.onChange) ctx.onChange(st, prev);
    return st;
  }
  return {dispatch: dispatch, state: function () { return st; }, ids: function () { return st.ids.slice(); },
          has: function (id) { return S.has(st, id); }, primary: function () { return S.primary(st); }};
}

HD.viewSelect = {mount: mount};
})();
