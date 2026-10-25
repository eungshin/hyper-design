# 판의 화면 줄 (rows, 51-1)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/rows.js` | Model | 줄 맞추기 계획. 상태 없음. `HD.rows = {plan(have [{group, n}], want [이름]) → {remove: [이름], insert: [{group, before}]}}` |
| `modules/view-rows.js` | View | 줄(`.flow`·`.glabel`·카드) HTML 과 새 데이터에 맞추기. 상태 = 걷어 둔 줄 요소(이름별, 되살리기 때 다시 끼움). `HD.viewRows.mount({rowsEl, $, $$, esc, warn})` → `{html(rows), polHtml(pol, cls), sync(rows, has(id)) → {removed, added}}`. 등록부가 아니라 셸이 바로 붙인다 — 첫 그리기가 `HD.mountAll` 보다 먼저라서 |
| 셸 VS `data()` | — | 지운 카드 떼기 → `RW.sync(nd.rows)` → 떼어 둔 카드 제자리 → 새 카드 자리·크기·숨김 → 폴더·레이어 다시(기존 길) |
| `session.emptied_groups` · `delete_screens` | Model · 도우미 | 지우기로 비게 된 `groups` 이름만 `screens.json` 에서 뺀다(원래 빈 이름은 그대로). 되살리기는 `screens.json` 을 통째로 돌려 `groups` 도 돌아온다 |

## 규칙

- 줄 = `nd.rows`(빌드가 빈 group 을 뺀 차례). 카드가 0 개이면서 새 데이터에 없는 줄은 제목째 걷는다(Figma F18). 카드(빈 레이아웃 포함)가 남은 줄은 데이터에 없어도 둔다
- 판에 없는 줄은 데이터 차례에서 그 뒤에 오는 남은 줄 앞(없으면 마지막 줄 뒤)에 끼운다. 걷어 둔 같은 이름 줄이 있으면 그 요소(되돌리기), 아니면 판에 없는 화면으로 새 카드
- 기준 줄을 못 찾으면 끝에 붙이고 `[hd]` 경고 한 줄
- 레이어 패널 `tree()` 는 DOM `.flow` 를 읽으므로 같은 줄을 따른다

## 고치면 돌릴 것

`-m "unit or layers or tools" --surface board` + `-k "rows or delete"`(test_canvas_unit_rows · test_canvas_rows · test_canvas_helper 의 지우기)
