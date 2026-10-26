# 빈 레이아웃 (view-drafts)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C9, 2026-10-26). 승격은 `promote.md`, 카드 글 상자는 `caption.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/edits.js` `layout`·`layoutText`·`layoutOf`·`layoutId` | Model | 빈 레이아웃 메모 모양(`edit:'new-screen'`, 경로 `(새 화면)`, 이름 기본 '빈 레이아웃', 판 좌표 x·y, 요청 글 `say.layout`) · 그 화면의 메모 찾기 · id `new-<시각 5자리><난수 2자리>` |
| `modules/view-drafts.js` | View | 빈 레이아웃 = 메모 하나 = 판 위 흰 카드: 놓기(새 화면 대화상자 → 크기·이름, 대화상자가 없으면 바로), 메모에서 카드 그리기(없어진 것 지움, 닿은 화면만), 이름·목적 고치기(그 메모 안 `value`·`purpose`, 되돌리기 한 단계, 복제 카드는 `say.copy`). 상태 없음(메모 주인 = `NS`). ctx `{$, $$, rowsEl, notes, zoom, save, record, toast, add(label, list, msg), artboard(), place(card), cardEl, scr}`. `HD.viewDrafts.mount(ctx) → {note(cx, cy), add, at(cx, cy), render(ids?), of(id), edit(id, changes)}` — 셸이 직접 붙인다(`DR`) |

## 규칙

- 놓은 자리 = 누른 화면 좌표 → `#rows` 기준 판 좌표(배율 뺀 값, 반올림). 옮긴 거리는 `view-card-pos`
- 없는 빈 레이아웃을 고치려 하면 토스트 '그 빈 레이아웃이 없어요 — 이미 지워졌어요'

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-drafts.js` · `edits.js` 빈 레이아웃 함수(+ `tests/test_canvas_unit_drafts.py`) · 셸 `DR` | `unit or tools or notes or helper` + `--surface board` |
