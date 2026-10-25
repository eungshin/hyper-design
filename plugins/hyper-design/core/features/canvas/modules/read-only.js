/* ViewModel — 읽기만인 탭(#274)에서 처음부터 막을 편집 규칙: 막을 조작부 선택자 · 막을 키 · 편집 도구. DOM·저장소를 쓰지 않는다.
   받아 놓고 버리지 않는다 — 저장하는 순간(추가·Enter·보내기·되돌리기)과 편집 도구를 막고, 글 쓰기 자체는 막지 않아 쓴 글이 칸에 남는다.
   HD.readOnly = {CONTROLS: [선택자], editTool(tool) → bool, key({key, ctrl, meta, shift, alt, typing, field}) → 막나}
     field = 입력 중인 칸 id('pnote' 메모 칸 · 'tedit' 글자 고치기 · 그 밖) */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

var CONTROLS = [
  '#tools [data-tool]:not([data-tool="hand"])',   // 편집 도구(손만 그대로)
  '#selbar button', '#undo', '#redo', '#nsend', '#nclear', '#padd', '#tedel',
  '#thread button[data-act]', '#nlist button[data-act]', '#lyBar button', '.ly-eye', '.ly-lock', '.ly-hov'
];

function editTool(t) { return !!t && t !== 'hand' && !!(HD.tools && HD.tools.SPEC[t]); }

function key(e) {
  if (!e || typeof e.key !== 'string') return false;
  var k = e.key, low = k.toLowerCase(), mod = !!(e.ctrl || e.meta);
  if (e.typing) {
    if (k !== 'Enter') return false;
    if (e.field === 'pnote') return mod;            // 메모 추가 = Ctrl+Enter
    if (e.field === 'tedit') return !e.shift;        // 글자 저장 = Enter(Shift+Enter 줄바꿈)
    return false;
  }
  if (mod) return !e.alt && ['z', 'y', 'x', 'v', 'd'].indexOf(low) >= 0;   // 되돌리기·다시·잘라내기·붙이기·복제
  if (e.alt) return false;
  if (k === 'Delete' || k === 'Backspace') return true;
  return editTool(HD.tools && HD.tools.byKey(low));
}

HD.readOnly = {CONTROLS: CONTROLS, editTool: editTool, key: key};
})();
