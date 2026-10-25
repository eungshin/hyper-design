# 우클릭 메뉴 (view-cmenu)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C2, 2026-10-26).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/view-cmenu.js` | View | 우클릭 메뉴 `#cmenu` 와 옆 목록 `#cmsub` 그리기·자리·키·닫기. 상태 = 지금 항목·열기 토큰·옆 목록 항목·토큰·연 단추. ctx `{$, $$, esc, menu, sub}`. `HD.viewCmenu.mount(ctx) → {open(x, y, head, items) → 토큰, isCurrent(토큰), isOpen(), close()}` — 셸이 직접 붙인다(`CM`) |
| 셸 `pane` 의 `contextmenu` · `openElemMenu` | — | 무엇을 넣을지(선·카드·요소·빈 곳 항목)만 고른다. 셸에 두는 까닭: 항목마다 셸 편집 함수(hide·deleteCards·linkTo …)를 부른다 |

## 규칙

- id `#cmenu`·`#cmsub` 와 단추 모양(`button[data-i]`·`[data-j]`·`.cmh`·`kbd`·`▸`)은 그대로 — `view-blocks.js` 의 Enter·Tab 가드와 브라우저 테스트가 읽는다
- 항목: `{label, key?, act()}` · `{label, sub(cb)}`(옆 목록, `cb(null)` = 찾는 중 · `cb([])` = 고를 요소 없음) · `'-'` 구분선 · `{head}` 소제목. 누르면 메뉴를 닫고 `act()`
- 늦게 오는 답(카드 우클릭의 `hd-hit-at`)은 `open()` 이 준 토큰으로 `isCurrent(tok)` 를 물어 그 메뉴가 아직 떠 있을 때만 바꾼다(다시 열거나 닫았으면 버림)
- 키: ↑↓ = 목록 안에서 돌기(두 목록이 같은 함수) · → = 옆 목록 열기 · ← / Esc(옆 목록에서) = 옆 목록만 닫고 연 단추로. 밖을 누르기(캡처 단계)·창 크기 바뀜 = 닫기. Esc 차례(메뉴가 먼저)는 셸 Esc 사슬이 `isOpen()`/`close()` 로

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-cmenu.js` · 셸 `contextmenu`·`openElemMenu`·Esc 사슬의 메뉴 줄 | `unit or tools or links --surface frame` |
