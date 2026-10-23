# 편집 메모 (edits)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `edits.js` — 편집 메모 하나가 진실 원천: 반영 대기 선·빈 레이아웃·글자 미리보기·도우미가 바로 쓸 것은 모두 메모에서 계산한다. 요청문(`request`)에서 요청 글의 줄바꿈은 `요청: ` 글자 자리에 맞춰 들여 쓴 다음 줄로 남는다(한 줄 메모는 예전 그대로)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/edits.js` · `history.js` · `view-history.js`(기록 시간줄·되돌리기) · `view-notes.js`(메모·반영 대기 목록) | `unit or tools or notes` |
