# 레이어 폴더 (folders · layers · view-layers)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `folders`(Model)·`layers`(Model, 폴더 줄)·`view-layers`(View) — 레이어 폴더(H17): 패널에서만 묶음(판 카드·화면 파일 그대로, 키 `hd-folders:`), 데이터 줄 = 고정 폴더, 폴더·줄의 [가로로/세로로 늘어놓기]는 정렬 패널 간격으로 셸 `arrangeCards`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/layers.js` · `view-layers.js`(레이어 패널: 나무·숨김·잠금·검색) · 셸 숨기기·잠금 가드 | `unit or layers or tools` |
