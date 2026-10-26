# 메모 창 (view-memo-pop)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C7, 2026-10-26). 창 틀(옮기기·크기·저장한 자리)은 `pop-place.md`, 여러 장 메모는 `memo-batch.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/annotation.js` `make`·`makeId` | Model | 새 메모 모양 하나(첫 대상의 path·text·rect, targets 사본, `sent:false`, 범위는 element 가 아닐 때만) · 메모 id(시각 36진 + 난수 4자리, 부르는 쪽이 `Date.now()`·`Math.random()` 을 넘김). 메모 창·질문 답(`view-send`)이 같이 쓴다 |
| `modules/view-memo-pop.js` | View | 메모 창 `#pop` 하나: 화면 전체(`card`, 배열 = 고른 화면마다) · 판 위 요소(`element`) · 요소 막대(`elem`, 크게 보기면 고른 요소 아래) · 크게 보기 `hd-picked`(주석 도구일 때, Shift = 묶음에 더하기·빼기) · 고치기 `edit` · 지우기 `del`(되돌리기 = 제자리) · 사람 답 `reply`(확인·다시). 범위 `#pscope`·의도 `#pintent`. 상태 = `draft`·`editing`. ctx `{$, $$, esc, notes, save, record, toast, title, modal() → {open, screen, scale, box, picking, frame}, setScreen(id), frame() → popPlace, cardEl, pins(), focusPin(id)}`. `HD.viewMemoPop.mount(ctx) → {card, element, elem, edit, del, reply, isOpen(), close(), draft()}` — 셸이 `VN` 앞에 직접 붙인다(`MP`) |
| 셸 | — | Esc 사슬에서 `MP.isOpen()`/`MP.close()` · 크게 보기 닫기·넘어감에서 `MP.close()` · 핀 ctx `draft: MP.draft()` · 메모 패널·묶음(`VN`·`TH`)에 `MP.edit`·`del`·`reply`·`card` |

## 규칙

- 창 자리: 저장한 자리가 있으면 popPlace, 아니면 자동(누른 자리 옆 · 크게 보기 고른 요소 아래(넘치면 위) · 메모 패널 왼쪽 · 기본 24,80), 화면 안으로 자른다
- 범위 기본: 화면 전체 메모 = 이 화면, 요소 = 이 요소, 여러 장 = `memoBatch.defaultScope` · 이 요소 = 범위 칸 없음(옛 메모와 같음)
- 고치기·지우기에 없는 id = 토스트 '그 메모가 없어요 — 이미 지워졌어요'
- 첨부 이미지(R22, `attach.md`): `#pop` = `[data-hd-attach]` 상자(칩 자리·클립 단추는 mount 가 만든다). 열 때 `hd-attach-set`(새 메모 = 비움 · 고치기 = 메모의 `attach`, 글 칸에는 경로 줄 없이) · 추가/저장 = 글 끝 경로 줄 + `attach` 칸 · 올리는 중이면 토스트 · 닫으면 비움
- 막 단 메모의 카드는 핀을 바로 보인다(`focusPin`, 크게 보기 아닐 때)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-memo-pop.js` · `annotation.js` `make`·`makeId`(+ `tests/test_canvas_unit_memo_pop.py`) · 셸 `MP` 붙이기 | `unit or helper or notes or tools or modal` |
