# 요소 테두리 · 화면에 묻기 (view-elbox · view-frame-ask)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C11, 2026-10-26). 요소 막대는 `blocks.md`, 메시지 모양은 `../contract.md`(화면 ↔ 캔버스 메시지).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/view-frame-ask.js` | View | 카드 화면에 묻기: 그 자리 요소 `hd-hit-at` → `hd-hit`(1.5초 안에 답 없으면 null + quiet 가 아니면 토스트 '이 화면은 편집할 수 없어요', 안 실린 카드는 싣고 load 뒤에 묻는다) · 조상 `hd-up`(tag `cue…`) → `hd-upchain`(답 없음·실패 = null + `[hd]` 경고). 상태 = 기다리는 답(`hitWait`·`upWait`). ctx `{$, $$, toast, wOf(card), load(frame)}`. `HD.viewFrameAsk.mount(ctx) → {hit(card, cx, cy, quiet, cb, leaf?, deep?), chain(frame, h, cb), lastFrame(card)}` — 셸 `FA` |
| `modules/view-elbox.js` | View | 판 위 요소 테두리: 올린 요소 미리 테두리(도구마다 `tools.hoverOf`, 메모 도구 = 이름표 `<종류> · 요소` · 화면 모드·카드 제목·테두리 = 카드 전체 `.elbox.scr` + `<화면 이름> · 화면 전체` — `memo-tool.md`, 한 번에 하나만 묻고 마지막 자리만 기억, 판 밖·끄는 중이면 걷기) · 고른 요소 목록(R19) = 모두 테두리 고정(`.elbox.sel`), 주인(마지막 것, `.pri`)만 소켓 + 부모 점선(`blocks.parentPick`) + 요소 막대(`BK.show`). 상태 = `hov`·`sels`. ctx 는 머리 주석. `HD.viewElbox.mount(ctx) → {clear(), selected() → 주인, all(), select(card, h), toggle(card, h), unselect(), keep(ok(cardId)), pickAt(card, x, y, deep?, add?)}` — 셸 `EB` |
| `modules/el-pick.js` | Model | 여러 요소 고르기 규칙(R19): `only`·`toggle`(있으면 빼고 없으면 끝에 = 주인)·`primary`(마지막)·`has`·`keep`·`key(screen, path)` · Shift+누르기가 요소냐 카드냐 `shift({tool, els, picked, draft})`. 상태 없음. `HD.elPick` — unit `test_canvas_unit_el_pick.py` |
| `modules/view-modal-pick.js` | View | 크게 보기 여러 요소: 고른 목록(`hd-sel` 답, Shift = `add:true`)과 테두리 `#mbox .msel-box`(주인 `.pri`). 상태 = 목록(저장 안 함 — 닫기·다시 싣기·도구 바뀜·스크롤이면 셸이 `clear`). ctx `{box, scale()}`. `HD.viewModalPick.mount(ctx) → {pick(screen, d, add) → 주인 d|null, clear(), all(), paint()}` — 셸 `ML` |
| 셸 | — | Esc 사슬에서 `EB.selected()`/`EB.unselect()` · 소켓 끌기·Del·Ctrl+D·고르기 바뀜·쓴 뒤 다시 실림에서 `EB.selected()` 읽기 |

## 규칙

- 여러 요소(R19): 선택(V)으로 요소를 하나 고른 뒤, **고른 카드** 화면 안 Shift+클릭 = 그 요소 더하기·빼기(`el-pick.shift` = 'el'). 고른 요소가 없거나, 고르지 않은 카드거나, 빈 레이아웃이면 Shift+클릭 = 지금처럼 카드 여러 장(E15). 다른 카드의 요소 = 먼저 Shift+클릭으로 그 카드를 더한 뒤 그 카드 안 Shift+클릭(카드 고르기에서 빠진 카드의 요소는 `keep` 이 푼다). 그냥 클릭 = 그 하나 · Esc·도구 바꾸기 = 모두 풀기. 요소 막대·요소 메뉴·소켓 끌기·Del 은 주인(마지막 것) 하나에만 — 여러 요소 한꺼번에 고치기는 아직 없다. 대화창은 고른 요소마다 칩(셸 ctx `pickedAll`) — `chat.md`
- 크게 보기: `palette.js` 가 `hd-sel` 에 Shift 면 `add:true` → 셸이 `ML.pick` → 막대는 주인만

- 남은 겹침(이번에 고치지 않음): `view-blocks` 의 [상위] 묻기(hd-up, 제 tag)와 `rectOf`(view-blocks · view-elbox · 셸 `modalSel`) — 각자 제 tag·제 상자라 합치려면 view-blocks 를 고쳐야 한다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-elbox.js` · `view-frame-ask.js` · `el-pick.js` · `view-modal-pick.js` · 셸 `EB`·`FA`·`ML` | `unit or tools or modal` + `--surface frame`(요소 막대 테스트 파일이 frame 이웃 · 여러 요소 = `test_canvas_el_multi.py`) |
