# 메모 창 (view-memo-pop)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C7, 2026-10-26). 창 틀(옮기기·크기·저장한 자리)은 `pop-place.md`, 여러 장 메모는 `memo-batch.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/annotation.js` `make`·`makeId` | Model | 새 메모 모양 하나(첫 대상의 path·text·rect, targets 사본, `sent:false`, 범위는 element 가 아닐 때만) · 메모 id(시각 36진 + 난수 4자리, 부르는 쪽이 `Date.now()`·`Math.random()` 을 넘김). 메모 창·질문 답(`view-send`)이 같이 쓴다 |
| `modules/view-memo-pop.js` | View | 메모 창 `#pop` 하나: 화면 전체(`card`, 배열 = 고른 화면마다) · 판 위 요소(`element`) · 요소 막대(`elem`, 크게 보기면 고른 요소 아래) · 크게 보기 `hd-picked`(메모 도구 요소 모드일 때, Shift = 묶음에 더하기·빼기) · 고치기 `edit` · 지우기 `del`(되돌리기 = 제자리) · 사람 답 `reply`(확인·다시). 범위 `#pscope`·의도 `#pintent`. 상태 = `draft`·`editing`. ctx `{$, $$, esc, notes, save, record, toast, title, modal() → {open, screen, scale, box, picking, frame}, setScreen(id), frame() → popPlace, cardEl, pins(), focusPin(id)}`. `HD.viewMemoPop.mount(ctx) → {card, addCard, element, addElement, elem, edit, del, reply, isOpen(), close(), draft()}` — 셸이 `VN` 앞에 직접 붙인다(`MP`) |
| `modules/pop-side.js` | Model | 메모 창 자동 자리(R27 F09): `beside(target, size, areas, gap?) → {x, y, side}` — 대상 상자 오른쪽 → 왼쪽 → 아래 → 위 중 앞 area(판 자리 `#screens`)에 들어가는 첫 자리, 없으면 다음 area(화면), 어디에도 없으면 가장 넓은 쪽(안으로 자름). 깨진 값 = 첫 area 왼쪽 위(`side:'none'`). 상태 없음. `HD.popSide = {GAP, beside}` |
| 셸 | — | Esc 사슬에서 `MP.isOpen()`/`MP.close()` · 크게 보기 닫기·넘어감에서 `MP.close()` · 핀 ctx `draft: MP.draft()` · 메모 패널·묶음(`VN`·`TH`)에 `MP.edit`·`del`·`reply`·`card` |

## 규칙

- 창 자리: 저장한 자리가 있으면 popPlace, 아니면 자동 = 대상 옆, 대상을 덮지 않게(R27 F09, FigJam 메모 쓰기 창처럼 — `HD.popSide.beside`). 대상 = 크게 보기 고른 요소 · 판 위 요소(메모의 `rect` × 카드 iframe 배율) · 화면 전체 메모는 그 카드 · 둘 다 없으면 누른 점. 판에서는 판 자리(`#screens`) 안을 먼저, 안 되면 화면 안. 대상이 화면 밖이면 메모 패널 왼쪽 · 기본 24,80
- 모양(R27 F09 — 메모 묶음 `#thread` 와 한 식구, 템플릿 마크업을 mount 가 다시 놓는다): 머리 줄 `.phead` = 대상 이름 `#ptitle`(끌기 손잡이, 13.5px) + 닫기 × `#pcancel`(`aria-label` 닫기). 내부 경로는 `#ptitle` 의 `title` 꼬리말만(`body` 는 빈 글), `#ppath` 는 숨김. 글 칸이 가장 또렷(14px). 아래 아이콘 한 줄 = 의도 `#pintent` [바꾸기|질문] · 범위 `#pscope` 아이콘 셋(이름 = `aria-label`, 여러 장이면 '고른 화면 N개') · 📎 `.patt` · 추가 `#padd`(오른쪽 끝). 아이콘 이름은 꼬리말 `#poptip`(`#thtip` 과 같은 모양 — 올리기·키보드 포커스, 창을 닫으면 숨김). 글 칸 안내는 의도를 따른다(바꾸기 '무엇을 바꿀지…' · 질문 '무엇이 궁금한지…')
- 범위 기본: 화면 전체 메모 = 이 화면, 요소 = 이 요소, 여러 장 = `memoBatch.defaultScope` · 이 요소 = 범위 칸 없음(옛 메모와 같음)
- Shift+클릭 = 요소 묶음에 더하기·빼기(`toggleTarget`, 쓰던 글·의도·범위 그대로, 다 빼면 닫힘): 크게 보기 `hd-picked` `add` · 판 메모 도구 요소 모드(P) `addElement(id, h, x, y)` — 같은 화면 요소 메모가 열려 있으면 더하기·빼기, 아니면 새 메모. 화면 모드(M) Shift+클릭 = `addCard(id)`(열린 새 화면 메모에 화면 더하기·빼기 — `memo-tool.md`). 메모 도구의 Shift+클릭은 카드 여러 장 고르기로 가지 않는다
- 고치기·지우기에 없는 id = 토스트 '그 메모가 없어요 — 이미 지워졌어요'
- 첨부 이미지(R22, `attach.md`): `#pop` = `[data-hd-attach]` 상자(칩 자리·클립 단추는 mount 가 만든다). 열 때 `hd-attach-set`(새 메모 = 비움 · 고치기 = 메모의 `attach`, 글 칸에는 경로 줄 없이) · 추가/저장 = 글 끝 경로 줄 + `attach` 칸 · 올리는 중이면 토스트 · 닫으면 비움
- 막 단 메모의 카드는 핀을 바로 보인다(`focusPin`, 크게 보기 아닐 때)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-memo-pop.js` · `annotation.js` `make`·`makeId`(+ `tests/test_canvas_unit_memo_pop.py`) · 셸 `MP` 붙이기 | `unit or helper or notes or tools or modal` |
| `modules/pop-side.js`(자동 자리 규칙 — `tests/test_canvas_unit_pop_side.py`) · 창 모양(F09 — `test_canvas_annotations.py -k composer`) | `unit or notes or tools or modal` |
