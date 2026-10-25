# 판 글 레이어 (board-text · view-board-text, t51-9)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 근거 `tasks/51-figma/FINDINGS.md` F1·F9·F10·F12·F14·F15 · 틈 #22(사용자 결정: Delete = 숨기기가 아니라 파일에서 빼기).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/board-text.js` | Model | 판 글 묶음(소개 안내 줄·제목·요약·아이디어·사람·정한 것·시장 관례 · 끝 글 색 출처·사진 출처 · DS 카드)과 출처 칸·되는 일. 상태 없음. `HD.boardText = {IDS, NAMES, CAPTION, blocks, apply, pending, check, keepEm, plain, captionDelete, layers, say, blockOf}` |
| `modules/view-board-text.js` | View | `HD.viewBoardText.paint(els, D, hidden)`(셸이 처음 그림) + 등록부 기능 `boardText`(needs `$ $$ esc toast warn notes selected rowsEl`). 상태 = 고른 판 글 하나(저장 안 함) · 바로 반영 중 편집 · 받은 데이터. 셸은 `BT = FT.boardText.attach({data, on, write, queue, hide, hidden, tool, pickCard, guard, caption, reload, changed})` 한 번 — 쓰기 길·숨김·카드 글 상자는 셸 것. 의도 받음 `hd-board-pick {id}`(레이어 줄) |
| `board_text.py` | Model(서버) | `plan(screens, decisions, {op, to, value})` → 바뀐 파일만 · `BoardError(이유, invalid|missing)`. `screen_edits.apply_edits` 의 `edit:'board'`(screen `'@board'`) 가 부른다 — 쓰기 한 번 = 원본 + manifest = 되돌리기 한 번 |

## 규칙

- 묶음 하나 = 요소 하나 = 레이어 하나: id `intro-hint|story|ideas|people|decisions|market` · `foot-palettes|credits` · `dscard`, 레이어 id = `'@' + id`(셸 `setHidden` 이 그대로 숨김). 예전에 숨겨 둔 `@intro`·`@foot` 은 레이어 패널에 남아 다시 보이게 할 수 있다
- 이동 도구(V) 누르기 = 고르기(파란 실선 상자 `#btsel` + 이름표) · 올리기 = 얇은 실선 `#bthov` · Esc·빈 곳 = 풀기. 판 글을 고르면 카드 고르기는 풀리고, 카드 아래 글(제목·설명·정책)을 고르면 그 카드 하나가 골라진 채(설명·정책이 보이는 자리 — task 31). 줄 제목은 `rowHeads`(51-4) 그대로
- Enter·두 번 누르기 = 고치기: 소개 칸은 그 자리(Enter 저장 · 여러 줄 칸 Shift+Enter 줄바꿈 · Esc 취소 · 밖 누르기 저장), 카드 아래 글은 카드 글 상자(caption.md), DS 카드는 Foundation 탭. 글자 도구(T) 누르기 = 바로 그 자리 고치기. 고친 뒤 골라진 채(F14). 제목의 `<em>` 강조 글이 새 글에 그대로 있으면 다시 감싼다(`keepEm`)
- Delete·Backspace(F15): 파일 묶음(story·ideas·people → screens.json, decisions·market → decisions.json — 판에 나오는 그 종류 항목 전부) = 파일에서 빼기 · 만든 글(안내 줄)·출처(색·사진 — 지우면 출처 표시 의무가 사라짐)·DS 카드(tokens.css 는 화면이 씀) = 판에서 숨기기(되돌리기 한 줄, 토스트가 까닭). 카드 제목 = 거절 토스트 · 설명 = '' · 정책 = 빈 목록(카드 글 상자와 같은 편집, 반영 대기)
- 쓰기: 도우미로 열면 판을 먼저 바꾸고(바로 반영) `/api/apply` 한 번(`view-sync write` — 기록 한 줄·되돌리기 = 되살리기), 거절이면 판을 되돌리고 까닭 토스트, 뒤 빌드가 깨지면(`build.failed`) 판 글을 파일대로 다시 불러온다. 도우미 없이 = 반영 대기 메모(`edit:'board'`, 보내기 요청문에 실림)로 판에 미리 보임
- 칸 키 = 판 차례(`decisions.items.N` = build_canvas 가 거른 정한 것 N 번째 → 서버가 같은 거르기로 decisions.json 번호를 찾는다). 이름 칸은 비울 수 없고 2000자까지

## 고치면 돌릴 것

`-m "unit or layers or tools or notes or helper" --surface board` (`test_canvas_unit_board_text` · `test_canvas_board_text`)
