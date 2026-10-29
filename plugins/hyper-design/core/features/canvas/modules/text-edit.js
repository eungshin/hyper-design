/* Model — 글자 고치기 규칙(R52, Figma·Photoshop 관례): 고치는 중 키 → 할 일 · 두 번 누르기가 글자 고치기로 가나 · 고치는 중 다른 곳 누르기 → 전환|끝. DOM·저장소·메시지를 쓰지 않는다.
   key({key, shift, ctrl, meta, alt, composing}) → 'save' | 'br' | null
     Enter · Ctrl/Cmd+Enter · Esc = 'save'(저장하고 끝 — 그 요소는 골라진 채, 고친 게 없으면 저장 요청 없음. 되돌리기는 Ctrl+Z) · Shift+Enter = 'br'(줄바꿈) · 그 밖·한글 조합 중 = null
   dbl(tool, where) → bool: 두 번 누른 글자를 그 자리에서 고치나 — 판(board)·크게 보기(modal) 모두 선택(V)만. 손(H)은 아님(크게 보기 손 = 화면 체험, 사용자 10-29). 판에서 글자가 아니면 셸이 하던 일(크게 보기)
   press({editing, text, tool}) → 'switch' | 'end' | null: 고치는 중(editing) 선택(V)으로 누름 — 글자(text) = 지금 것 저장 + 그 글자로 전환 · 글자 아님 = 저장하고 끝(누른 것이 골라진다) ·
     고치는 중이 아니거나 다른 도구(글자 도구는 원래 누르면 고친다 · 손은 화면 체험) = null
   palette.js inlineKey 는 key 와 같은 규칙(화면 안이라 이 파일을 못 읽음 — test_canvas_unit_text_edit 이 두 쪽을 같은 표로 견준다)
   HD.textEdit = {key, dbl, press} */
(function () {
'use strict';
var HD = globalThis.HD = globalThis.HD || {};

function key(e) {
  if (!e || e.composing) return null;               // 한글 조합 중 Enter = 조합 끝내기
  if (e.key === 'Escape') return 'save';
  if (e.key !== 'Enter') return null;
  if (e.shift && !e.ctrl && !e.meta) return 'br';
  return 'save';                                     // Enter · Ctrl/Cmd+Enter(레이어 선택으로)
}
var DBL = {board: {move: 1}, modal: {move: 1}};
function dbl(tool, where) { return !!(DBL[where] && DBL[where][tool]); }
function press(o) {
  o = o || {};
  if (!o.editing || o.tool !== 'move') return null;
  return o.text ? 'switch' : 'end';
}

HD.textEdit = {key: key, dbl: dbl, press: press};
})();
