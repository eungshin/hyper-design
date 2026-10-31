# 카드 메모 묶음 (view-thread)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `view-thread`(View) — 카드 메모 배지 → 그 화면 메모 묶음(#224, Word 메모처럼): 배지(`role=button`, `view-notes` 가 그림) 옆 `#thread` 에 요소·종류·글 전체, 줄마다 고치기·지우기·완료, 머리 줄 [+] = 메모 추가. 고치기·지우기는 메모 패널과 같은 `MP.edit`·`MP.del`(열린 메모 글 `.tht` 더블클릭 = 고치기)(view-memo-pop, 지우기 = 되돌리기 한 단계), 더하기 = `openCardMemo`. 배지 누르기는 카드 고르기·끌기로 가지 않는다. Esc·바깥 누르기 = 닫기(떠 있는 층 'thread' — `float-stack.md`, 맨 위일 때만), 같은 배지·같은 핀을 다시 누르면 닫기(다른 핀 = 그 메모로). 메모가 바뀌면 `renderNotes` 가 `refresh` — 연 자리(배지 · 핀) 그대로: 핀으로 열었으면 배지로 옮겨 붙지 않고, 핀이 다시 그려졌으면 마지막 자리(U1 F1b). 자리 = 공용 `HD.popSide.under`(배지·핀 아래 오른쪽 끝, 셸 ctx `avoid()` = 왼쪽 도구 막대 `#tools` 를 피함, F6)
- 아이콘 동작(R26): 줄 동작은 메타 줄(번호·대상·상태·의도 — 작은 회색 한 줄, 대상은 말줄임) 오른쪽 끝 `.thib` 아이콘 — 연필(`edit`)·휴지통(`del`)·체크(`done`), 닫힌 메모는 되돌리기 화살표(`reopen`), 머리 줄 `+`(`add`). `data-act`·`aria-label`(이름) 그대로, 꼬리말 `#thtip`(요소 막대 `#eltip` 과 같은 모양 — 올리기·키보드 포커스). 평소 흐림, 줄에 올리거나 키보드 포커스면 진하게. 메모 글(`.tht`)이 가장 또렷하다. 메모 패널(`view-notes`) 줄의 연필·휴지통도 같은 흐림 규칙
- 보낸 메모 숨기기(task 29): 묶음 줄은 `annotation.visible(n, 켜짐)` 인 메모만 — 꺼짐이면 AI 작업 중·완료 메모는 빠지고 '완료 N' 묶음도 켜졌을 때만, 숨긴 수는 회색 한 줄 `.thhid`. 켜짐은 셸이 건넨 `ctx.showSent()`, 바뀌면 셸이 `refresh`(#263)
- 긴 답 본문(R26): 답에 `detail`(≤50000, `hd reply --detail-file`)이 있으면 그 답 줄 아래 `.thdet` 에 전체(줄바꿈 그대로, 240px 넘으면 그 안에서 스크롤, 글 고르기 됨). 줄 툴팁(`annotation.tip`)은 detail 앞 300자만
- 다시 찾지 못한 대상(`ctx.lost(n)`, #285)이 있는 열린 메모 줄 = `.thlost` '요소를 찾을 수 없음'(title = 같은 요소가 여러 개이거나 없어요)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-thread.js`(카드 메모 배지 → 그 화면 메모 묶음: 고치기·지우기·메모 추가·완료·다시 열기·답 줄·질문 고르기) · `view-memo-pop` `edit`·`del`·`reply` · `view-send` `answer`·`send` | `unit or notes or modal or tools or helper` |
