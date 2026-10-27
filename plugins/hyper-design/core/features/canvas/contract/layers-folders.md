# 레이어 폴더 (folders · layers · view-layers)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `folders`(Model)·`layers`(Model, 폴더 줄)·`view-layers`(View) — 레이어 폴더(H17): 패널에서만 묶음(판 카드·화면 파일 그대로, 키 `hd-folders:`), 데이터 줄 = 고정 폴더, 폴더·줄의 [가로로/세로로 늘어놓기]는 정렬 패널 간격으로 `CP.arrange`(view-card-pos)
- R31: 판 폴더(줄)·사용자 폴더 이름 두 번 누르기 = 이름 바꾸기 — 이름 한 번 누르기(그 화면 고르기)는 260ms 미룬다(고르기가 도크의 연결·정렬 패널을 열어 레이어 줄이 움직이면 두 번째 누르기가 빗나갔다). 폴더 줄 이름 title = 이름 전체, 올림 단추는 올렸을 때만 자리를 차지
- R31: 화면 줄 끌어 놓기 규칙 = `HD.rowOps.drop` — 사용자 폴더 = 넣기, 판 폴더 = 사용자 폴더에서 빼기 + 다른 판 폴더 화면은 그 폴더로(`hd-row-assign`, 파일에 씀 — `contract/rows.md`). 오른쪽 메뉴: 판 폴더 = 이름 바꾸기 · 폴더만 풀기 · 폴더 지우기(글 = `HD.rowOps.WORDS`), 사용자 폴더 = 이름 바꾸기 · 폴더 풀기

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/layers.js` · `view-layers.js`(레이어 패널: 나무·숨김·잠금·검색) · 셸 숨기기·잠금 가드 | `unit or layers or tools` |
