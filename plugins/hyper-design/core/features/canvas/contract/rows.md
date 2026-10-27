# 판의 화면 줄 (rows, 51-1 · 줄 = 섹션 51-4)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/rows.js` | Model | 줄 맞추기 계획 + 줄 = 섹션 검사. 상태 없음. `HD.rows = {plan(have [{group, n}], want [이름]) → {remove, insert: [{group, before}]}, target(names, name) → {into, where}|{error}, checkName(names, from, to) → {name, same?}|{error}, space(rows [{bottom, over}], {base, clear}) → [px], CLEAR}` |
| `modules/view-rows.js` | View | 줄(`.flow`·`.glabel`·카드) HTML 과 새 데이터에 맞추기. 상태 = 걷어 둔 줄 요소(이름별, 되살리기 때 다시 끼움). `HD.viewRows.mount({rowsEl, $, $$, esc, warn})` → `{html(rows), polHtml(pol, cls), sync(rows, has(id)) → {removed, added}, space()}`. 등록부가 아니라 셸이 바로 붙인다 — 첫 그리기가 `HD.mountAll` 보다 먼저라서 |
| `view-rows.js` 등록부 기능 `rowHeads`(51-4) | View | 줄 제목 = 섹션. 상태 = 고른 줄 이름 하나(저장 안 함). ctx = `rowsEl · $ · $$ · api · record · toast · selected · warn`(공통 칸만, 셸 줄 0). 의도 보냄: `hd-row-pick {ids}` · `hd-row-delete {ids}` · `hd-rows-changed {renamed?}` / 받음: `hd-row-rename {from, to}` · `hd-row-dissolve {name}` |
| `modules/layers.js` · `view-layers.js` | Model · View | 레이어 줄 id = `HD.layers.rowId(이름)`(= `'row:' + 이름`, 예전 `'g'+차례` 는 view-layers 가 바꾼다) · `renameRow(folded, from, to)` = 접힘을 새 이름으로. 줄 항목: 이름 두 번 누르기 = 이름 바꾸기, 올리면 [줄만 걷기], 오른쪽 메뉴 = 이름 바꾸기 · 줄만 걷기 · 줄 화면 모두 삭제. `hd-row-pick` → `ctx.pick` · `hd-row-delete` → `ctx.del`(셸 deleteCards = 기존 지우기 길) |
| 셸 VS `data()` | — | 지운 카드 떼기 → `RW.sync(nd.rows)` → 떼어 둔 카드 제자리 → 새 카드 자리·크기·숨김 → 폴더·레이어 다시(기존 길) |
| `session.emptied_groups` · `delete_screens` | Model · 도우미 | 지우기로 비게 된 `groups` 이름만 `screens.json` 에서 뺀다(원래 빈 이름은 그대로). 되살리기는 `screens.json` 을 통째로 돌려 `groups` 도 돌아온다 |
| `session.plan_group_rename` · `plan_group_dissolve`(순수) · `group_rename` · `group_dissolve` · `History.group_*` | Model · 도우미 | `POST /api/group-rename {from, to}` · `POST /api/group-dissolve {name}` — screens.json 쓰기 한 번(원본 + manifest → `/api/restore` 로 되돌리기 한 번), 바뀐 화면 파일 없음(`changed: []`). 거절 = `{error(한국어), reason: invalid(400)|missing(404)}`, 쓰지 않음. 계약 `tests/protocol/helper.json` |
| `modules/row-ops.js`(R31) | Model | 폴더(= 줄) 다루기 규칙. 상태 없음. `HD.rowOps = {drop(items, head) → {add?, take?, assign?}(레이어 끌어 놓기), assign(rows [{name, ids}], ids, to) → {to, ids, emptied}|{same}|{error}, titleShift(offs) → {dx, dy}, dragPlan(ids, locked, mx, my) → {moves}|{error}, key(e) → 'ungroup'|'delete'|null, WORDS}` — 규칙은 `tests/test_canvas_unit_row_ops.py` |
| `modules/view-row-drag.js`(R31, 등록부 `rowDrag`) | View | 제목 끌기 = 폴더째 옮기기 + 제목이 카드를 따라감. 상태 = 끄는 중 하나(저장 안 함). ctx = `rowsEl · cardPos(view-card-pos api) · view · locked · toast · warn · lines?` — 저장·되돌리기는 `cardPos.move`(카드 끌기와 같은 길) |
| `board_rows.plan_group_move`(순수) · `group_move` · `History.group_move`(R31) | Model · 도우미 | `POST /api/group-move {ids, to}` → `{group, screens(옮긴 id), emptied, stamp|null, changed: []}` — 화면마다 group = to, to 줄 화면 뒤(옮긴 것끼리 원래 차례), 빈 줄 이름은 groups 에서 뺌. 이미 그 줄 = 쓰지 않음(stamp null). 거절 = 없는 폴더·화면 404 · 빈 ids 400 |

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
- 줄 사이(t51-8, Figma 섹션): 아래 줄 제목은 위 줄 카드 아래 펼친 설명(`.cbody`, 고를 때만 펼침 · 판 배치를 밀지 않는 겹침)과 겹치지 않는다. 고르기로 줄이 움직이지 않게 펼친 설명 자리를 늘 비워 둔다 — 줄마다 `over + CLEAR(40) - bottom - base(.flow padding-top)` 만큼 그 `.flow` 아래 여백(`HD.rows.space`). 셸이 카드 글을 다시 그린 뒤(`paintCardText` — 새 데이터·메모·반영 대기)·처음·글꼴 뒤·줄 높이가 바뀐 뒤 `RW.space()`. 옮긴 카드는 제 자리 기준
- R31 폴더(Figma 섹션): 판 제목 = 폴더 — 앞에 폴더 아이콘(`::before` 마스크, 글 = 이름 그대로라 `.glabel` textContent 를 읽는 곳은 그대로), 500 굵기·회색(판 글·판 메모보다 조용), 올리면 바탕 + 잡기 손, title = 누르기·두 번·끌기 안내. 메뉴·레이어 줄 메뉴 글은 `HD.rowOps.WORDS` 하나 — "폴더만 풀기 — 화면은 남겨요"(Ctrl+Shift+G · Ctrl+Backspace) ≠ "폴더 지우기 — 화면 n개도 지워요"(Del)
- 폴더만 풀기는 예전 줄만 걷기 그대로(화면은 위 폴더로 — 판은 줄 배치라 Figma 처럼 제자리에 둘 빈 자리가 없다: 제자리에 두면 아래 줄이 올라와 겹친다), 걷은 화면은 골라진 채
- 제목 끌기 = 폴더째 옮기기(아무 도구, Space·가운데·오른쪽 버튼은 판): 그 폴더 카드(숨김 포함) 모두 같은 거리 → `card-pos` 저장 + 되돌리기 한 줄. 잠긴 화면이 끼면 옮기지 않고 토스트. 끈 뒤 click 은 삼킨다(고르기 아님)
- 제목 자리 = 그 폴더 카드 옮긴 거리의 가장 작은 값(가로·세로 따로, CSS `translate` — label-scale 의 transform 과 따로) — 폴더째 옮기면 같이, 카드 하나를 오른쪽·아래로 옮기면 그대로, 위로 올리면 그 위로
- 레이어 패널에서 화면 줄을 다른 판 폴더(머리 줄 또는 그 안 화면 줄)에 놓기 = 그 폴더로 옮기기(의도 `hd-row-assign` {ids, to} → `rowHeads` 가 판 먼저 옮기고 `/api/group-move`, 실패면 되돌림, 되돌리기 한 번). 다 빠진 폴더는 판·groups 에서 없어진다
- 옮긴 카드 자리(`card-pos`)는 줄 이름(`g`)을 든다 — 이름 바꾸기·줄만 걷기(그 되돌리기·실패 포함) 뒤 `view-card-pos` 가 `hd-rows-changed` 를 듣고 `HD.rows.rekeyPos` 로 키를 옮겨, 새로고침 뒤에도 제자리(S1c d3e0a23).

## 고치면 돌릴 것

`-m "unit or layers or tools or helper" --surface board` + `tests/protocol` + `-k "rows or row_sections or row_ops or folders or delete"`(test_canvas_unit_rows · test_canvas_unit_row_sections · test_canvas_unit_row_ops · test_canvas_rows · test_canvas_folders · test_canvas_helper 의 지우기)
