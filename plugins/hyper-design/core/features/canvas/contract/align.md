# 정렬 패널 (align · view-align)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `align`(Model)·`view-align`(View) — 정렬 패널(H18, 도크 패널 `align`): 고른 카드(잠김·숨김·삭제 대기 빼고)의 상자로 맞추기 6·간격 같게 2·늘어놓기 2(간격 칸 px, 키 `hd-align-gap`). 옮기기는 `view-card-pos` 의 `move` 가 카드 옮긴 자리(`hd-card-pos:`)에 더하고 기록 한 단계(`card-pos.md`)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/align.js` · `folders.js` · `view-align.js`(정렬 패널) · `view-layers.js` 폴더 · `view-card-pos` `boxes`·`move`·`arrange` | `unit or layers or tools or dock` |
