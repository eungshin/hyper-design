# 오른쪽 패널 도크 (dock · view-dock)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- 오른쪽 패널 도크: 배치는 `dock.js`(키 `hd-dock`, 모든 캔버스 공용), 그리기·끌기는 `view-dock.js`. 패널(`#pLinks`·`#pShow`·`#pNotes`·`#pLayers`)은 옮겨 붙일 뿐 안의 id(`#legend`·`#notes`·`#hidl`)와 그 `hidden` 뜻은 그대로다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/dock.js` · `view-dock.js` · 도크 CSS | `unit or dock or notes` |
