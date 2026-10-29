# 글자 고치기 관례 (R51·R52, Figma·Photoshop)

- 규칙 = `modules/text-edit.js`(Model `HD.textEdit`): `key` 고치는 중 키 · `dbl` 두 번 누르기가 고치기로 가나 · `press` 고치는 중 다른 곳 누르기.
  - Enter · Ctrl/Cmd+Enter · Esc = 저장하고 끝(그 요소는 골라진 채 — `view-optimistic` repick). 고친 게 없으면 쓰기 요청 없음. 되돌리기 = 이미 있는 Ctrl+Z(따로 취소 없음). Shift+Enter = 줄바꿈. 한글 조합 중 = 아무것도.
  - 두 번 누르기: 판·크게 보기 모두 선택(V)만. 손(H)은 아님(크게 보기 손 = 화면 체험, 10-29). 판의 글자 아닌 곳(·답 없는 카드) = 하던 대로 크게 보기.
  - 고치는 중 선택(V)으로 다른 글자 누르기 = 지금 것 저장 + 그 글자로 전환 · 글자 아닌 곳 = 저장하고 끝, 앞 요소를 다시 고르지 않음(누른 것이 골라진다).
- 화면 안(`foundation/palette.js`)은 모듈을 못 읽어 `textKey` 를 표시(`/* hd-text-key */ … /* /hd-text-key */`) 사이에 같은 규칙으로 둔다 — unit 이 같은 표로 견준다.
  크게 보기 전환 = palette 가 누른 글자를 `hd-dbl` 로 · 글자 아님 = `hd-inline-done` 에 `away:true`.
- 판 = `modules/view-text-edit.js`(View): 판 카드 iframe 은 누르기를 받지 않으므로 셸 덮개 누르기에서 `TE.click`·`TE.dbl`. 고치는 중 판 pointerdown = `OP.away('board')`(끝난 고치기를 다시 고르지 않음).
- 앱 카드·옛 palette 의 글 칸(`#tedit`)도 같은 `key`.

고치면 돌릴 것: `-m "unit or tools or modal or helper"` (+ `--surface frame`) — 이 기능의 테스트 `test_canvas_unit_text_edit.py` · `test_canvas_text_edit.py`.
