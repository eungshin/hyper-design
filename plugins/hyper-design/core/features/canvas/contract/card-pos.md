# 카드 옮긴 자리 (view-card-pos)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C4, 2026-10-26).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/rows.js` `cleanPos` | Model | 저장된 `card-pos` 글 → 지금 카드에 맞는 자리만. 상태 없음. `cleanPos(text, live{id: 줄 이름}) → {pos, dirty, bad}` (`rekeyPos` 옆) |
| `modules/view-card-pos.js` | View | 카드 옮긴 자리(`hd-card-pos:<hash>`)의 주인: 읽기·거르기(Model)·저장·카드 놓기, 판 좌표 상자 하나(`boxOf`), 옮기기·정렬 한 단계(되돌리기), `hd-rows-changed` 뒤 줄 이름 옮기기. 상태 = `cardPos`. ctx `{$, $$, rowsEl, stage, getItem, setItem, hash, zoom(), cardEl(id), locked(id), record(op), toast(msg), redraw(), moved()}`. `HD.viewCardPos.mount(ctx) → {load(), reload(), save(), place(card), placeAll(), at(id), put(id, p), set(id, p), map(), replace(m), group(card), boxOf(card, origin), extent(left), boxes(ids), move(moves, label), arrange(ids, op)}` — 셸이 `ST` 바로 뒤에 직접 붙인다(`CP`) |
| 셸 | — | 끌기(`pointerdown`·`pointermove`·`endCardDrag`: `CP.at`·`put`·`place`·`save`·`set`) · `fit` 의 `CP.extent` · 선 끝 `cardBoxes`·`fitCards` 의 `CP.boxOf` · 정렬 패널·레이어 늘어놓기 `CP.boxes`·`arrange` · 승격 `CP.map`/`replace` · `adoptState` 의 `CP.reload()` · 시작 `CP.load()`(빈 레이아웃 카드를 그린 뒤) |

## 규칙

- 저장 형식 그대로: `{id: {dx, dy, g}}`(g = 줄 이름). 읽을 때 없는 화면·다른 줄로 간 화면(g 가 있고 지금 줄과 다름)·수가 아닌 dx/dy·빈 값은 버리고 깨끗한 값을 다시 쓴다. 깨진 JSON·객체 아님 = 빈 자리, 다시 쓰지 않고 `[hd]` 경고 한 줄
- 빈 레이아웃 카드 = 놓은 자리(`data-x`·`data-y`) + 옮긴 거리 · 진짜 카드 = `left/top` = 옮긴 거리, `.moved`
- 상자 하나(`boxOf(card, origin)`) = 화면 상자 − 원점 ÷ 배율. 정렬(원점 `#rows`) · 선 끝 손잡이(원점 `#ar`) · 고른 화면에 맞추기(원점 = 판 칸 + 이동) 가 같은 셈. 판 범위(`extent`)만 레이아웃 상자(offset — 변형 전)
- 옮기기·정렬 = 기록 한 단계(`before`/`after` 를 서로 되돌림), 잠긴 카드는 세기만(토스트), 숨김·삭제 대기는 뺀다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-card-pos.js` · `rows.js` `cleanPos`(+ `tests/test_canvas_unit_card_pos.py`) · 셸 `CP` 붙이기 | `unit or tools or layers or dock` + `--surface board` |
