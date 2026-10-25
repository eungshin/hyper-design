# 패널 도크 — 오른쪽 · 왼쪽(S3) (dock · view-dock)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- 오른쪽 패널 도크: 배치는 `dock.js`(키 `hd-dock`, 모든 캔버스 공용), 그리기·끌기는 `view-dock.js`. 패널(`#pLinks`·`#pShow`·`#pNotes`·`#pLayers`)은 옮겨 붙일 뿐 안의 id(`#legend`·`#notes`·`#hidl`)와 그 `hidden` 뜻은 그대로다
- 왼쪽 도크(S3): 상태 `left`(묶음들 — 오른쪽 `groups` 와 같은 규칙) · `lw`(너비 220–560, 기본 340). 접기·닫은 패널 단추는 오른쪽에만. 비면 자리 없음(`#ldock.empty`, `--dockl` 0) — 탭을 끄는 동안(`body.dk-dragging`)만 왼쪽 끝 28px 놓을 자리. 의도 `move/width/heights` 에 `side:'left'`(없으면 오른쪽). 같은 쪽에 혼자 있는 탭 떼기는 그대로, 다른 쪽으로는 옮긴다
- 집 쪽(`SIDE`): 대화(`talk`)의 집은 왼쪽 — 기본 배치, 예전 저장 상태(talk 없음 — 오른쪽 배치·너비는 그대로)에 넣는 자리, 닫았다 다시 열 때. `visible()` 은 왼쪽 → 오른쪽(접히면 빠짐) → 떠 있는 창 차례, `leftWidth(st)` = 비었거나 Tab 이면 0
- 판·크게 보기·Foundation 칸·떠 있는 창 층은 `left:var(--dockl)` 로 왼쪽 도크를 비킨다(`--dockw` 와 같은 inherits:false 방식). 2분할 가운데 = 두 도크 사이 가운데

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/dock.js` · `view-dock.js` · 도크 CSS | `unit or dock or notes`(왼쪽 도크 = `test_canvas_unit_dock_left.py` + 브라우저 `test_canvas_chat_log.py`, `--surface board`) |
