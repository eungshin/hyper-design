# 카드 아래 글 한 상자 (caption · view-caption)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `caption`(Model)·`view-caption`(View) — 카드 아래 글 한 상자(H16): 제목·설명·정책 줄을 한 상자에서 고치고, 바뀐 칸마다 반영 대기 편집(`title`·`purpose`·`policy`[i]) 을 한 번의 `addEdits` 로(되돌리기 한 번). 정책 줄 지우기 있음(op:delete — 비운 줄, 원래 번호, helper 가 큰 번호부터 한 번에), 더하기는 allowAdd 일 때만. 설명 비우기 = '' 편집, 제목은 비울 수 없음(편집 없음, `ctx.toast`). 빈 레이아웃 카드도 같은 상자(#225): 이름(한 줄)·목적(여러 줄) → 편집이 아니라 그 메모 안 `n.value`·`n.purpose`(셸 `editLayout`, 되돌리기 한 번), 목적은 `say.layout` 요청문의 첫째 브리프. 칸 안내 글은 `ctx.hint`. Shift+Enter(#226): 제목 = 설명으로 넘어감(제목은 한 줄), 설명·목적 = 줄바꿈, 정책 줄 = Enter 와 같음

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/caption.js` · `view-caption.js`(카드 아래 글 한 상자: 두 번 누르기·글자 도구·카드 메뉴 이름/설명 → 바뀐 칸마다 반영 대기, 되돌리기 한 번 · 빈 레이아웃 이름·목적 = 셸 `editLayout`) | `unit or tools or notes` |
