# 카드 동작 (view-card-actions)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C9, 2026-10-26). 바로 복제는 `card-copy.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/view-card-actions.js` | View | 카드 삭제(진짜 화면 = 도우미면 `VS.del` 로 파일에서 바로, 실패·도우미 없음 = 삭제 요청 메모 · 빈 레이아웃 = 그 메모와 그리로 가는 잇기째, 되돌리기) · 삭제 대기 표시(`.del` + `.delchip`) · 복제(도우미 = cardCopy, 아니면 흰 복제 카드, 앱 카드 거절) · 들어오는 연결 끊기 · Ctrl/Cmd+D · Del/Backspace(고른 요소가 있으면 요소 지우기). 상태 = `deleted`(메모에서 계산). ctx 는 모듈 머리 주석. `HD.viewCardActions.mount(ctx) → {paint(ids?), isDeleted(id), del(ids), dup(ids), cutIn(ids)}` — 셸이 고르기(`SL`) 뒤 그 자리에 직접 붙인다(`CA`, 단축키 듣기 차례 그대로) |

## 규칙

- 잠긴 카드는 빼고(토스트), 남은 것이 없으면 아무것도 안 함
- Ctrl+D 는 `e.defaultPrevented`(요소 막대가 먼저 받은 요소 복제)·입력 중·크게 보기·다른 탭·고른 요소가 있으면 하지 않는다
- 연결 보기는 삭제 대기 화면을 숨긴 화면처럼 뺀다(`isDeleted`)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-card-actions.js` · 셸 `CA` | `unit or tools or notes or helper` + `--surface board` |
