# 표시 팝오버 (view-show-pop, R27 F02)

`../contract.md` 의 책임 게이트·테스트 층을 따른다.

## 규칙

- 선 색·굵기·투명도·선 보이기·움직임 줄이기(`#pShow`)는 늘 열린 도크 패널이 아니라 위쪽 줄 단추 `#showbtn`(배율 칩 `#zoom` 앞 — 겹치던 보기 단추 `#vbtn` 은 U3 F11 에서 뺐다) 아래 팝오버 `#showpop` 에 산다 — 드물게 쓰는 설정이 판 옆 자리를 차지하지 않게
- 이 모듈은 `#pShow` 를 옮겨 붙이고 열고 닫기만 한다. 안의 동작(선 색 고르기·슬라이더 = `view-lines.js`, 움직임 줄이기 = `view-motion.js`)과 id 는 그대로
- 열기 = 단추 · 닫기 = 단추 다시 · Esc · 팝오버 밖 누르기. `aria-expanded` 가 열림을 말한다. 상태 = 열림 하나(저장 안 함)
- `#pShow` 나 `#zoom` 이 없으면 붙지 않고 `[hd]` 경고 한 줄(표시 없이)
- 등록부 기능 `showPop`(needs `$`) → `{open(), close(), isOpen()}`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-show-pop.js` | `unit or menu or dock`(`test_canvas_edit.py -k view_and_window_menus` · `test_canvas_v2.py -k reduce_motion`) |
