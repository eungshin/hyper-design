# 판 메모 (board-notes · view-board-notes)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(R23, 조사 `tasks/free-text-insight-2026-10-26.md` 안 A).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/board-notes.js` | Model | 판 메모 모양·만들기·쓰기 끝(빈 메모 버리기)·옮기기·지우기·저장값 거르기·409 합치기·새 메모 자리(`room`)·누른 자리 판정(`spot`)·크기(`resize`, R25)·숨김·잠금 칸(`flag` `isHidden` `isLocked`, R26)·전체 보기 범위(`extent`)·레이어 줄(`layers` — hid·lock 포함). 상태 없음. `HD.boardNotes = {NAME, W, MIN_W, MAX_W, MIN_H, MAX, LAYER, FLAGS, parse, newId, create, finish, move, resize, flag, isHidden, isLocked, remove, merge, room, spot, extent, layers, text}` |
| `modules/view-board-notes.js` | View | 상태 이름 `board-notes`(`hd-board-notes:<hash>`)의 주인: `#stage` 안 `#bnotes` 층 그리기, 만들기·제자리 쓰기·고르기·끌기·지우기, 쓰기 + 기록 한 줄. 상태 = 메모 map · 고른 메모 · 쓰는 중 · 끄는 중(저장은 map 만). 등록부 `boardNotes`(needs `$`·`store`·`key`·`record`·`toast`·`warn`·`view`·`selected`) → `{attach({tool(), setTool(t), changed()?, clear()?}), reload(), selected(), map(), layers(), layerSel(), extent(ext), reveal(id)}` · 의도 받음 `hd-note-pick` {id} · `hd-note-flag` {ids, key, on}(R26) |
| 셸 | — | `BN = FT.boardNotes.attach({tool, setTool, changed → LY.render, clear → 카드 고르기 풀기})` · `adoptState` 의 `has('board-notes')` → `BN.reload()` · `fit()` 의 범위 = `BN.extent(CP.extent(…))` · 레이어 `tree()` 에 `notes: BN.layers()`·`notePicked: BN.layerSel()` · 보기 메뉴 '고른 화면에 맞추기' = 고른 메모면 `BN.reveal` (붙이는 줄만) |
| `modules/layers.js` · `view-layers.js` | Model · View | `build(…, notes)` = 맨 끝 '판 메모' 묶음(`@notes`, kind `row`, hid·lock = 모두일 때) + 메모 줄(kind `note`, hid·lock) · 메모 줄 누르기 = 의도 `hd-note-pick` · 눈·자물쇠·아래 막대 숨기기·잠그기 = 의도 `hd-note-flag` |
| `state-file` · `history` · `save-merge` | Model·ViewModel | `NAMES`·`TRACK` 에 `board-notes` · 409 = `HD.boardNotes.merge`(메모마다, 같은 메모를 둘 다 바꾸면 잃은 변경) · 이름표 '판 메모' |

## 규칙

- 저장 모양 `{<id>: {x, y, w, h?, text, color?, hidden?, locked?, at}}` — 판(`#stage`) 좌표 정수 px, `h` 없음 = 글 높이대로, 글 = 평문 2000자. 모르는 칸은 그대로. 깨진 값 = 빈 판 + `[hd]` 경고, 모양이 틀린 메모만 빼고 `[hd]` 경고(다시 쓰지 않음)
- 만들기: 글자 도구(T)로 빈 판 누르기 · 선택(V)으로 빈 판 두 번 누르기. 빈 판 = 누른 요소가 `#screens`·`#stage`·`#intro`·`#rows`·`#foot`·`.flow`·`.cards` 자체이고 조상에 카드·판 글(`.bt`)·DS 카드·줄 이름·선(svg)·도구·단추·입력이 없음(`spot`). 자리 = 누른 점이 첫 줄 글자 자리, 오른쪽 같은 높이의 카드 앞까지 폭(120..280), 바로 위 카드(이름·설명 줄 포함)에 걸치면 그 밑으로(`room`) — 카드를 덮지 않아 카드 누르기는 그대로
- 쓰기: 메모 자체가 그 자리 `<textarea>`(판과 같이 확대). 판을 0.6 배율보다 작게 보고 있으면 메모 자리를 둔 채 0.6 으로. Enter = 줄바꿈(한글 조합 중 키는 건드리지 않음) · Esc · Ctrl+Enter · 밖 누르기 = 끝. 빈 채로 끝 = 버림(저장·기록 없음). 만들기+쓰기 = 기록 한 줄 '판 메모 쓰기'. T 로 만들었으면 끝낸 뒤 V
- V: 누르기 = 고르기(파란 테두리) · 끌기(4px 넘게) = 옮기기 한 줄 · 두 번 누르기·Enter = 고치기(비우면 '판 메모 지우기') · Delete·Backspace = 지우기 한 줄 · Esc = 풀기. 카드를 고르면 메모 고르기는 풀린다. 손(H)·Space = 메모 위에서도 판 끌기. T 로 메모 누르기 = 고치기
- 크기(R25): V 로 고른 메모 오른쪽 아래 손잡이(화면에서 같은 크기 — 고를 때·올릴 때만 배율을 잰다). 끌기 = 폭 120..1600 · 4px 넘게 아래위로도 끌었으면 `h` = 최소 높이 52..4000(글이 길면 더 커져 잘리지 않음), 안 끌었으면 `h` 없음 = 글 높이대로. 놓으면 기록 한 줄 '판 메모 크기' · 손잡이 두 번 누르기 = `h` 빼기('판 메모 높이 자동')
- 레이어 패널(R25): 맨 끝 '판 메모' 묶음(메모 수) 아래 메모마다 줄(위→아래·왼→오른, 이름 = 첫 글 줄 40자). 접기·이름 찾기 됨. 줄 누르기 = 판에서 그 메모 고르기(카드 고르기는 풂) + 배율 1 이하로 그 메모에 맞춤, 고른 메모 줄은 강조. 끌어 폴더에 넣기·늘어놓기·올리기 강조는 아직 없음
- 숨김·잠금(R26): 저장은 메모의 칸 `hidden: true` · `locked: true`(끄면 칸을 뺀다 — 옛 메모·옛 저장값 그대로 맞음, true 아닌 값은 `parse` 가 뺌). 셸 `LF`(`hd-hidden`·`hd-locked` = 화면 id 목록)는 그대로 — 주인은 `view-board-notes` 하나, 레이어 패널은 의도 `hd-note-flag` {ids: ['note:<id>'], key: 'hidden'|'locked', on} 만 보낸다. 메모 줄 눈·자물쇠 · '판 메모' 묶음 줄 눈(메모 모두) · 메모 줄을 고른 채(고른 화면 없음) 아래 막대 숨기기·잠그기. 기록 한 줄씩('판 메모 숨기기'·'숨긴 판 메모 보이기'·'판 메모 잠그기'·'판 메모 잠금 풀기'). 숨긴 메모 = 판에 그리지 않음(고르기 풀림, 줄 누르기로 고르지 않음) · 전체 보기(0)·`fit` 범위에서 뺌 · 거르기 '숨긴 것만'에 나옴. 잠긴 메모(`.lock`) = 고르기만 — 끌기(4px 넘으면 한 번 토스트 '잠긴 판 메모예요 — 레이어 패널에서 풀어요')·크기 손잡이(안 보임)·고치기(두 번 누르기·Enter·T)·지우기(Del) 안 됨, 같은 토스트. 위쪽 '숨긴 화면 N' 수에는 들지 않는다(화면만)
- 전체 보기(0)·`fit` 범위에 메모 상자(높이 = 그려진 높이)를 넣는다 — 멀리 둔 메모도 보인다. 고른 메모가 있고 고른 카드가 없으면 '고른 화면에 맞추기' = 그 메모
- 쉬는 동안 하는 일 없음(그리기는 바뀔 때만, 끄는 동안은 그 상자 left/top·width/min-height 만). 뷰포트 밖 떼기·작게 볼 때 자리표시는 아직 없음(메모가 많아져 느려지면 그때 — 조사 안 B)
- 읽기만인 탭: 만들기·옮기기·고치기·지우기를 하지 않는다(두 번 누르기·Del 은 `view-read-only` 가 막고 알림). file://(도우미 없음) = 다른 프로젝트 키처럼 브라우저 저장소 `hd-board-notes:<hash>` 에만 — 새로고침해도 남고, 파일로는 가지 않는다
- 아직 아님: AI 요청·대화창 칩에 메모 싣기(R22 뒤), 그림

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/board-notes.js`(+ `tests/test_canvas_unit_board_notes.py`) · `view-board-notes.js`(+ `tests/test_canvas_board_notes.py`) · 셸 `BN` 붙이기 · `view-layers.js` 메모 눈·자물쇠(R26) | `unit or tools or notes or layers` + `--surface board` |
