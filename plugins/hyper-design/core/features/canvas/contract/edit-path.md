# 편집 쌓는 길 (view-edit-path)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C5, 2026-10-26).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/view-edit-path.js` | View(DOM 없음) | 화면 파일을 바꾸는 편집(메모 `intent=change`)을 쌓는 길 하나. 상태 없음(메모 주인 = `NS`, 기록 = `view-history`). ctx `{notes, save(), record(op), toast(msg, undo?, ms?), title(id), sync() → VS, linksOf(from, cb)}`. `HD.viewEditPath.mount(ctx) → {scr(id), note(screen, h, text, op?, to?), add(label, list, msg?, drops?, keep?), linkTo(from, hits, to), cutText(to), linksTo(from, to, cb), cutPairs(pairs, oneWay?)}` — 셸이 `NS` 바로 뒤에 직접 붙인다(`ED`) |
| 셸 편집 동작(요소 메뉴·트리거·끌어 잇기·카드 글·삭제·복제 …) | — | 무엇을 쌓을지 고르고 `ED.add` 로 넘긴다. 등록부 기능은 ctx `queue(l, list, msg)` = `ED.add(…, keep=true)` |

## 규칙

- 문구는 `HD.edits.say`, 메모 모양은 `HD.edits.note`(Model) — 이 모듈은 고르지 않고 잇기만
- 바로 쓰기: 도우미가 켜져 있고(`VS.on`) keep 이 아니고 drops 가 없고 모든 편집이 `HD.edits.instantOf` 면 `VS.write(label, list)` — 이 길은 기록 줄·반영 대기를 남기지 않는다(쓰기 뒤 일은 view-sync). 도우미가 받았지만 거절한 편집이 있으면 까닭 토스트(6초). Promise 가 거절되면(도우미 꺼짐·끊김) 같은 편집을 `keep=true` 로 다시 쌓는다(실패를 숨기지 않고 반영 대기로)
- 반영 대기: `put` = drops 를 빼고 list 를 더함(`sent=false`) · `take` = list 를 빼고 drops 를 되돌림 — `record({label, status:'pending', undo: take, redo: put})` 의 두 방향이 서로의 역. 쌓은 뒤 `[되돌리기]` 토스트
- 선 자르기: 쌍마다(oneWay 가 아니면 양쪽) 그 화면 안 링크를 묻고, 반영 대기 연결(`HD.edits.pendingLink`)이면 끊기 대신 그 편집 취소(drops, E4). 링크를 모르는 화면(palette.js 없음) = 토스트 + 빈 목록

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-edit-path.js`(+ `tests/test_canvas_unit_edit_path.py`) · 셸 `ED` 붙이기 · `queue` | `unit or helper or tools or links` |
