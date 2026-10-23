# AI 수정 중 덮개 (busy · view-busy)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `busy`(Model)·`view-busy`(View) — AI 수정 중 덮개(Q2b): 터미널로 넘긴 화면 카드에 덮개, 상태 키 `hd-busy:`, 덮개가 있는 동안만 2초마다 `/api/watch` 로 화면 파일 mtime 을 보고 바뀌면 걷고 그 카드만 다시 싣는다.

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/busy.js` · `view-busy.js`(AI 수정 중 덮개: 터미널로 넘긴 화면 · 화면 파일이 바뀌면 걷힘 · [걷기]) · `helper.py` `/api/watch` | `unit or helper or notes` |
