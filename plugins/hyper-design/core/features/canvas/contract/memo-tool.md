# 메모 도구 한 칸·두 모드 (tools · view-memo-tool)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(2026-10-29, P 요소 주석 + M 화면 메모 합치기). 메모 창은 `memo-pop.md`, 여러 장은 `memo-batch.md`, 올리기 테두리는 `elbox.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/tools.js` | ViewModel | 도구 규칙: 메모 한 칸(`memo`, 키 M · 보조 P) · `MEMO` 두 모드(`el` P · `screen` M) · `modeOfKey`·`memoMode`(모르는 값 = `el`) · `memoTarget(mode, inPhone)` · `hoverOf(tool, {mode, edge})` · 이름표 `elLabel`·`screenLabel` · 칸 꼬리말 `memoTip`. 상태 없음 — unit `test_canvas_unit_memo_tool.py` |
| `modules/view-memo-tool.js` | View | 칸 모습(귀퉁이 `.tmode` 요소/화면 · `data-tip`·`data-key`·`data-mode`·`aria-label`) · 판 커서(`t-annotate` 요소 · `t-memo` 화면) · P·M 키를 capture 에서 먼저 읽어 모드만. 상태 = `mode`(저장 안 함 — 새로 열면 요소). ctx `{$, pane, tool(), typing(e)}`. `HD.viewMemoTool.mount(ctx) → {mode(), set(m), paint()}` — 셸 `MT` |
| 셸 | — | `setTool` 이 `MT.paint()` · 판 클릭이 `memoTarget` 로 `MP.card`/`MP.addCard`(화면) 또는 `FA.hit` → `MP.element`/`MP.addElement`(요소) · 크게 보기 `setMode('memo')` = 요소 모드면 고르기(picking), 화면 모드면 `MP.card(mscreen)` · `EB` ctx `mode()` |

## 규칙

- 칸 하나(`data-tool="memo"`, 말풍선). P = 요소 모드 · M = 화면 모드 · 칸 단추 = 마지막 모드
- 경계: 카드 제목 줄·본문·[보기] 등 `.phone` 밖(카드 안)과 빈 레이아웃 = 모드와 상관없이 화면 전체 메모
- 누르기 전: 요소 모드 = 그 요소 테두리 + `<종류> · 요소` · 화면 모드·경계 = 카드 전체 테두리 `.elbox.scr` + `<화면 이름> · 화면 전체`
- Shift: 요소 모드 = 요소 더하기·빼기(`MP.addElement`) · 화면 모드 = 열린 새 화면 메모에 화면 더하기·빼기(`MP.addCard`, `memoBatch.toggle`, 쓰던 글 그대로, 다 빼면 닫힘) — 둘 다 카드 여러 장 고르기로 가지 않는다
- 쓰지 않는 조합(이미 뜻이 있음): Alt+클릭(가장 안쪽 요소) · Ctrl+클릭(연결 따라 이동) · C(선 자르기). 메모 창 범위 아이콘·선택(V) 요소 막대 [메모]는 그대로

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/tools.js` 메모 규칙 · `view-memo-tool.js` · 셸 `MT`·판 클릭 메모 줄 · `setMode` | `unit or notes or tools or modal` + `--surface frame` |
