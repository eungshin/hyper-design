# 판 메모 선 (board-links · view-board-links)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(R47, 설계 `tasks/r47-info-card-brief.md` 단계 A). 선이 이은 메모 묶음을 화면 요청에 싣는 정보 카드는 `contract/info-card.md`(단계 B).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/board-links.js` | Model | 선 모양·잇기(`add` — 메모에서만, 자기 자신·같은 방향 같은 쌍 거절)·끊기(`remove`)·이름(`rename`)·저장값 거르기(`parse`)·지운 메모의 선(`touching` `prune`)·이름 바뀐 끝 따라가기(`retarget`)·그릴 선(`live`)·409 합치기(`merge`)·선 경로(`anchor` `nearSide` `path` `mid`). 상태 없음. 메모 id 는 글자로만 안다(board-notes 를 부르지 않음). `HD.boardLinks = {NAME, LABEL_MAX, SIDES, KINDS, parse, end, newId, add, remove, rename, touching, prune, retarget, live, merge, anchor, nearSide, path, mid}` |
| `modules/view-board-links.js` | View | 상태 이름 `board-links`(`hd-board-links:<hash>`)의 주인: `#stage` 안 보이는 선 `svg#blk-l`(카드 아래) · 누르는 띠와 이름 `svg#blk-h`(카드 위, 카드 상자를 뚫은 clip) · 변의 점 `#blk-dots`. 상태 = 선 map · 고른 선 · 끄는 중 · 거둔 선(메모 id 마다, 메모리만). 등록부 `boardLinks`(needs `$`·`$$`·`store`·`key`·`record`·`toast`·`warn`·`view`·`rowsEl`·`boardNotes`) → `{attach({tool(), changed()?}), reload(), map(), notesChanged(), selected(), schedule()}` · 의도 받음 document `hd-rows-changed` {renamed: {from, to}}(view-rows) |
| 셸 | — | `BL = FT.boardLinks.attach({tool, changed → LY.render})`(선이 바뀌면 레이어 '카드 N' 배지) · 정보 카드 `cardData().links` = `BL.map()` · `adoptState` 의 `has('board-links')` → `BL.reload()` · `BN` 의 `changed` → `BL.notesChanged()`(메모 바뀜 신호 — view-board-notes 는 선을 모른다) · ctx `boardLinks()` = `BL.map()`(없으면 `{}`, 정보 카드가 읽기만) (붙이는 줄만) |
| `state-file` · `history` · `save-merge` | Model·ViewModel | `NAMES`·`TRACK` 에 `board-links` · 409 = `HD.boardLinks.merge`(선마다, 같은 선을 둘 다 바꾸면 잃은 변경) · 이름표 '판 메모 선' |

의존 방향: `board-notes` ← `board-links`(메모 id 글자만) ← `info-card`(둘을 평범한 데이터로) ← 보내기·대화창·CLI(제공 함수만 받음).

## 규칙

- 저장 모양 `{<id>: {from: 'note:<메모 id>', to: 'note:<id>' | 'screen:<화면 id>' | 'folder:<줄 이름>', fromSide?, toSide?, label?, at}}` — side `top|right|bottom|left`(없으면 그릴 때 가까운 변) · label 평문 한 줄 40자 · at = ISO 시각 글. 모르는 칸은 그대로. 깨진 값 = 선 없음 + `[hd]` 경고, 모양이 틀린 선(출발이 메모 아님·자기 자신·모르는 끝)만 빼고 `[hd]` 경고
- `folder:<줄 이름>` = screens.json `screens[].group`(판의 줄 제목 `.glabel`) — 화면 S 를 담은 폴더 = S.group. 레이어 패널 사용자 폴더(`f<n>`)는 판에 없어 아직 끝이 아니다(나중에 따로 앞붙이)
- 없는 끝(지운 화면·숨긴 메모·없는 줄)을 가리키는 선은 저장에 남기고 그리지 않는다(`live`, 던지지 않음) — 같은 끝이 돌아오면 다시 보인다. 같은 방향 같은 쌍은 하나만 그린다
- 잇기: 선택(V)에서 메모에 올리거나 고르면 네 변 가운데 흰 점(화면에서 같은 크기, 메모가 화면에서 18px 보다 낮으면 숨김 — 작게 볼 때 점이 메모를 덮지 않게). 점을 끌면 점선이 따라오고 놓을 곳(메모·화면 카드·줄 제목)에 옅은 테두리, 놓으면 선 하나 + 기록 한 줄 '판 메모 선 잇기'. 같은 쌍 = 토스트 '이미 이은 선이에요', 자기 자신·빈 곳 = 아무 일 없음
- 모양(Obsidian Canvas·FigJam): 옅은 회색 곡선(1.5px, 화살표 끝) · 카드 아래 · 이름은 선 가운데 위. 고른 선 = 진한 회색. `#rows.focusing` 중에는 흐리게
- 선 누르기 = 고르기(누르는 띠 14px, 카드 위는 뚫려 카드 누르기는 그대로) · Delete·Backspace = 끊기 한 줄 '판 메모 선 끊기' · 두 번 누르기·Enter = 그 자리 이름 칸(Enter·밖 누르기 = 저장 한 줄 '판 메모 선 이름', Esc = 취소, 비우면 이름을 뺌) · Esc·다른 곳 누르기 = 풀기
- 메모 지우기: 셸이 메모가 바뀔 때마다 `notesChanged()` → 사라진 메모에 닿은 선을 거둔다(기록 줄 없이 — 같은 차례라 '판 메모 지우기' 줄의 차이에 함께 들어 새로고침 뒤 되돌리기도 함께). 같은 세션에서 되돌려 메모가 돌아오면 거둔 선도 돌아온다. 처음 보는(한 번도 없던) 메모 끝은 거두지 않는다
- 줄 이름 바꾸기(R31): `hd-rows-changed` {renamed} → `retarget('folder:<옛>', 'folder:<새>')`(기록 없이 — 그 줄의 되돌리기가 다시 이름을 바꿔 따라온다). 바꾸면 같은 쌍이 되는 선은 하나만 남긴다. 화면 id 가 바뀌는 신호는 아직 없다(그 선은 남고 그려지지 않음)
- 읽기만인 탭(`html[data-hd-tab=reader]`): 점 없음 · 끊기(토스트)·이름 안 됨 · 고르기만
- 쉬는 동안 하는 일 없음: 선이 없으면 그리지 않는다. 메모·카드 자리(MutationObserver)·배율이 바뀌면 한 프레임에 한 번 다시
- 이은 선은 정보 카드(`contract/info-card.md`)로 보내기 요청문에 화면마다 '유의(정보 카드):' 로 실린다 — 셸 `cardData()` 가 `BL.map()` 을 읽는다(진실 원천 하나)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/board-links.js`(+ `tests/test_canvas_unit_board_links.py`) · `view-board-links.js`(+ `tests/test_canvas_board_links.py`) · 셸 `BL` 붙이기 | `unit or tools or notes` + `--surface board` |
