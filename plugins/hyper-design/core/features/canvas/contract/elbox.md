# 요소 테두리 · 화면에 묻기 (view-elbox · view-frame-ask)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C11, 2026-10-26). 요소 막대는 `blocks.md`, 메시지 모양은 `../contract.md`(화면 ↔ 캔버스 메시지).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/view-frame-ask.js` | View | 카드 화면에 묻기: 그 자리 요소 `hd-hit-at` → `hd-hit`(1.5초 안에 답 없으면 null + quiet 가 아니면 토스트 '이 화면은 편집할 수 없어요', 안 실린 카드는 싣고 load 뒤에 묻는다) · 조상 `hd-up`(tag `cue…`) → `hd-upchain`(답 없음·실패 = null + `[hd]` 경고). 상태 = 기다리는 답(`hitWait`·`upWait`). ctx `{$, $$, toast, wOf(card), load(frame)}`. `HD.viewFrameAsk.mount(ctx) → {hit(card, cx, cy, quiet, cb, leaf?, deep?), chain(frame, h, cb), lastFrame(card)}` — 셸 `FA` |
| `modules/view-elbox.js` | View | 판 위 요소 테두리: 올린 요소 미리 테두리(도구마다 `tools.hoverOf`, 한 번에 하나만 묻고 마지막 자리만 기억, 판 밖·끄는 중이면 걷기) · 고른 요소 = 테두리 고정 + 소켓 + 부모 점선(`blocks.parentPick`) + 요소 막대(`BK.show`). 상태 = `hov`·`selEl`. ctx 는 머리 주석. `HD.viewElbox.mount(ctx) → {clear(), selected(), select(card, h), unselect(), pickAt(card, x, y, deep?)}` — 셸 `EB` |
| 셸 | — | Esc 사슬에서 `EB.selected()`/`EB.unselect()` · 소켓 끌기·Del·Ctrl+D·고르기 바뀜·쓴 뒤 다시 실림에서 `EB.selected()` 읽기 |

## 규칙

- 남은 겹침(이번에 고치지 않음): `view-blocks` 의 [상위] 묻기(hd-up, 제 tag)와 `rectOf`(view-blocks · view-elbox · 셸 `modalSel`) — 각자 제 tag·제 상자라 합치려면 view-blocks 를 고쳐야 한다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-elbox.js` · `view-frame-ask.js` · 셸 `EB`·`FA` | `unit or tools or modal` + `--surface frame`(요소 막대 테스트 파일이 frame 이웃) |
