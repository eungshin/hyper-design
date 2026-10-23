# 카드 메모 묶음 (view-thread)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `view-thread`(View) — 카드 메모 배지 → 그 화면 메모 묶음(#224, Word 메모처럼): 배지(`role=button`, `view-notes` 가 그림) 옆 `#thread` 에 요소·종류·글 전체, 줄마다 [고치기]·[지우기], 아래 [메모 추가]. 고치기·지우기는 메모 패널과 같은 셸 `editMemo`·`delMemo`(지우기 = 되돌리기 한 단계), 더하기 = `openCardMemo`. 배지 누르기는 카드 고르기·끌기로 가지 않는다. Esc·바깥 누르기 = 닫기, 메모가 바뀌면 `renderNotes` 가 `refresh`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-thread.js`(카드 메모 배지 → 그 화면 메모 묶음: 고치기·지우기·메모 추가·완료·다시 열기·답 줄·질문 고르기) · 셸 `editMemo`·`delMemo`·`addReply`·`answerQuestion`·`sendList` | `unit or notes or modal or tools or helper` |
