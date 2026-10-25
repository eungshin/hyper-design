# 스며드는 교체 (swap · view-swap, 48a)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 규칙

- 붙는 곳: 셸의 다시 싣기 자리 하나 `swapCard(id, frame, url)`(쓴 뒤 `VS` data · AI 덮개 걷힘 `VB` reload 둘 다)가 등록부 `FT.swap.swap` 을 부른다. 기능이 붙지 못하면 옛 길(data-src 로 두고 보일 때 싣기).
- `swap`(Model, 순수) — `plan`(실린 카드 = `preload` · data-src 카드 = `lazy`, 화면 밖 카드는 미리 싣지 않음) · `touching(id, sig)`(끌기 · 메모 창 대상 · 화면 글자 고치기 · 카드 글 고치기 · 크게 보기 그 화면 — 그 카드만) · `next`(`wait`·`defer`·`instant`·`fade`) · 작업 차례 `reduce`(카드마다 하나, 새 start 가 오면 앞 것의 늦은 load 는 무시) · `failed`(시간 초과 `LOAD_MS`=10초 · HTTP 4xx/5xx) · `boardUrl`(셸 `boardSrc` 와 같은 규칙). unit `tests/test_canvas_unit_swap.py`.
- `view-swap`(View) — 옛 iframe 바로 뒤 `iframe.hd-swap-next`(absolute, opacity 0)에 새 버전 → load → 옛 화면 스크롤 옮김 → 결정: 만지는 중 = 알약 `button.swap-pill` "새 버전 준비됨 · 반영"(누르면 바로 · 만지기가 끝나면 저절로 — `MutationObserver`, 미룬 카드가 있는 동안만) · 움직임 줄이기(설정 `motion:false` · `prefers-reduced-motion`) = 바로 · 아니면 새 것이 `FADE_MS`(0.2초) opacity 0→1(옛 것은 밑에 그대로 = 흰 깜빡임 없음) 뒤 옛 iframe 을 지운다. 보이기 직전에 셸 `ctx.frameLoaded(id, 새 틀)`(테마·반영 대기·메모 자리 — 숨어 기다리는 동안 바뀐 메모까지; 없으면 `[hd]` 경고 한 번) → 두 프레임 뒤 보이기. 새 것이 `.phone` 의 첫 iframe 이 된다(셸·다른 View 가 찾는 틀).
- 실패 = 새 틀을 버리고 옛 화면 그대로 + `[hd]` 경고 + 의도 `hd-swap` failed → `view-busy` 가 그 카드 `.cerr` 한 줄(앱 카드 실패 줄과 같은 길, 다음 done 이 걷는다).
- 의도: `document` 의 CustomEvent `hd-swap` `{id, phase:'done'|'failed', why}` — `view-busy` 가 읽는다(View 끼리 직접 부르지 않음). 상태 저장 없음.
- "방금 반영됨 ✓"(`busy.lookDone` · `busy.landed`, `view-busy`): 화면 파일이 바뀌어 걷힌 카드(손 걷기 × 는 아님)의 교체 done 뒤 같은 칩 자리에 `data-kind=done` 칩이 `DONE_MS`(2초) 동안 · 앱 카드가 hd-here 로 걷히면 바로.

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/swap.js` · `view-swap.js` · `busy.js`·`view-busy.js` 의 "방금 반영됨"(48a) | `unit or helper or notes`(+ `-k swap`) |
