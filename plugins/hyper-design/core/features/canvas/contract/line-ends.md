# 선 끝 손잡이 (line-ends · view-line-ends)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `line-ends`(Model)·`view-line-ends`(View) — 선 끝 손잡이(Q3): 선 누르기 = 그 쌍 강조 + 도착 끝 손잡이, 다른 카드로 끌어 놓기 = 도착 바꾸기(메뉴 '도착 바꾸기'와 같은 편집·되돌리기 한 단계)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/line-ends.js` · `view-line-ends.js`(선 누르기 = 쌍 강조 + 도착 끝 손잡이 · 끌어 놓기 = 도착 바꾸기) | `unit or flow or tools` |
