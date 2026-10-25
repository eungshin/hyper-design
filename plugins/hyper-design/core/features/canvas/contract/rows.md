# 판의 화면 줄 (rows, 51-1 · 줄 = 섹션 51-4)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/rows.js` | Model | 줄 맞추기 계획 + 줄 = 섹션 검사. 상태 없음. `HD.rows = {plan(have [{group, n}], want [이름]) → {remove, insert: [{group, before}]}, target(names, name) → {into, where}|{error}, checkName(names, from, to) → {name, same?}|{error}}` |
| `modules/view-rows.js` | View | 줄(`.flow`·`.glabel`·카드) HTML 과 새 데이터에 맞추기. 상태 = 걷어 둔 줄 요소(이름별, 되살리기 때 다시 끼움). `HD.viewRows.mount({rowsEl, $, $$, esc, warn})` → `{html(rows), polHtml(pol, cls), sync(rows, has(id)) → {removed, added}}`. 등록부가 아니라 셸이 바로 붙인다 — 첫 그리기가 `HD.mountAll` 보다 먼저라서 |
| `view-rows.js` 등록부 기능 `rowHeads`(51-4) | View | 줄 제목 = 섹션. 상태 = 고른 줄 이름 하나(저장 안 함). ctx = `rowsEl · $ · $$ · api · record · toast · selected · warn`(공통 칸만, 셸 줄 0). 의도 보냄: `hd-row-pick {ids}` · `hd-row-delete {ids}` · `hd-rows-changed {renamed?}` / 받음: `hd-row-rename {from, to}` · `hd-row-dissolve {name}` |
| `modules/layers.js` · `view-layers.js` | Model · View | 레이어 줄 id = `HD.layers.rowId(이름)`(= `'row:' + 이름`, 예전 `'g'+차례` 는 view-layers 가 바꾼다) · `renameRow(folded, from, to)` = 접힘을 새 이름으로. 줄 항목: 이름 두 번 누르기 = 이름 바꾸기, 올리면 [줄만 걷기], 오른쪽 메뉴 = 이름 바꾸기 · 줄만 걷기 · 줄 화면 모두 삭제. `hd-row-pick` → `ctx.pick` · `hd-row-delete` → `ctx.del`(셸 deleteCards = 기존 지우기 길) |
| 셸 VS `data()` | — | 지운 카드 떼기 → `RW.sync(nd.rows)` → 떼어 둔 카드 제자리 → 새 카드 자리·크기·숨김 → 폴더·레이어 다시(기존 길) |
| `session.emptied_groups` · `delete_screens` | Model · 도우미 | 지우기로 비게 된 `groups` 이름만 `screens.json` 에서 뺀다(원래 빈 이름은 그대로). 되살리기는 `screens.json` 을 통째로 돌려 `groups` 도 돌아온다 |
| `session.plan_group_rename` · `plan_group_dissolve`(순수) · `group_rename` · `group_dissolve` · `History.group_*` | Model · 도우미 | `POST /api/group-rename {from, to}` · `POST /api/group-dissolve {name}` — screens.json 쓰기 한 번(원본 + manifest → `/api/restore` 로 되돌리기 한 번), 바뀐 화면 파일 없음(`changed: []`). 거절 = `{error(한국어), reason: invalid(400)|missing(404)}`, 쓰지 않음. 계약 `tests/protocol/helper.json` |

## 규칙

- 줄 = `nd.rows`(빌드가 빈 group 을 뺀 차례). 카드가 0 개이면서 새 데이터에 없는 줄은 제목째 걷는다(Figma F18). 카드(빈 레이아웃 포함)가 남은 줄은 데이터에 없어도 둔다
- 판에 없는 줄은 데이터 차례에서 그 뒤에 오는 남은 줄 앞(없으면 마지막 줄 뒤)에 끼운다. 걷어 둔 같은 이름 줄이 있으면 그 요소(되돌리기), 아니면 판에 없는 화면으로 새 카드
- 기준 줄을 못 찾으면 끝에 붙이고 `[hd]` 경고 한 줄
- 레이어 패널 `tree()` 는 DOM `.flow` 를 읽으므로 같은 줄을 따른다
- 줄 = 섹션(51-4, Figma F16·F17): 제목 누르기 = 그 줄 카드(숨김 빼고) 모두 고르기 → 여러 장 막대. 다른 것을 고르면 줄 고르기가 풀린다
- 제목 두 번 누르기 = 그 자리 이름 바꾸기(Enter 저장 · Esc 취소 · 밖 누르기 저장). 새 이름은 앞뒤 빈칸을 자르고, 빈 이름 · 80자 넘음 · 같은 이름 줄 · 없는 줄은 토스트로 이유. 같은 이름이면 쓰지 않는다. groups 항목과 그 줄 화면마다 `group` 을 한 번에 쓴다. 화면에만 있던 이름('기타')이면 지금 줄 차례를 groups 에 적어 자리를 지킨다
- 고른 줄 + Delete/Backspace = 그 줄 화면 모두(숨김 포함) 지우기 — 기존 지우기 길(잠금·되돌리기 한 번 그대로). 셸의 카드 지우기보다 먼저 받는다(window capture)
- 줄만 걷기(Ctrl+Backspace · 제목 오른쪽 메뉴 · 레이어 줄): 그 줄 화면은 판에 보이는 위 줄로, 첫 줄이면 아래 줄로(사용자 결정 ①). 위 줄이면 그 줄 화면 뒤, 아래 줄이면 앞에 붙이고(screens.json 차례도 같게 — 빌드가 같은 차례로 그린다) groups 에서 이름만 뺀다. 줄이 하나뿐이면 거절. 걷은 뒤 그 화면들이 골라진 채
- 판을 먼저 바꾸고(제목 글 · 카드 옮기기) 도우미 답이 실패면 되돌리고 토스트. 되돌리기 = `/api/restore`(그 뒤 파일이 바뀌었으면 409 → 토스트), 다시 하기 = 같은 쓰기를 새 stamp 로. 도우미 없이(file://) 열면 쓰지 않고 토스트
- 모양: 제목 hover = `--ui-badge-soft` 바탕, 고른 줄·고치는 중 = `--ui-mark` 테두리(`--ts` 배율), 메뉴 = `--ui-*` 만
- 알려진 한계: 카드 옮긴 자리(`card-pos`)는 줄 이름(`g`)을 들고 있어, 이름을 바꾸거나 걷은 줄의 옮긴 카드는 새로고침 뒤 제 줄 기본 자리로 돌아간다(셸 `loadCardPos` — 셸 주인 몫)

## 고치면 돌릴 것

`-m "unit or layers or tools or helper" --surface board` + `tests/protocol` + `-k "rows or row_sections or delete"`(test_canvas_unit_rows · test_canvas_unit_row_sections · test_canvas_rows · test_canvas_helper 의 지우기)
