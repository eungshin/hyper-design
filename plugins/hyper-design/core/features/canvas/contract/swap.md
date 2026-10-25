# 스며드는 교체 · 바뀐 곳 보기 (swap · swap-diff · view-swap, 48a·48b)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 규칙

- 붙는 곳: 셸의 다시 싣기 자리 하나 `swapCard(id, frame, url)`(쓴 뒤 `VS` data · AI 덮개 걷힘 `VB` reload 둘 다)가 등록부 `FT.swap.swap` 을 부른다. 기능이 붙지 못하면 옛 길(data-src 로 두고 보일 때 싣기).
- `swap`(Model, 순수) — `plan`(실린 카드 = `preload` · data-src 카드 = `lazy`, 화면 밖 카드는 미리 싣지 않음) · `touching(id, sig)`(끌기 · 메모 창 대상 · 화면 글자 고치기 · 카드 글 고치기 · 크게 보기 그 화면 — 그 카드만) · `next`(`wait`·`defer`·`instant`·`fade`) · 작업 차례 `reduce`(카드마다 하나, 새 start 가 오면 앞 것의 늦은 load 는 무시) · `failed`(시간 초과 `LOAD_MS`=10초 · HTTP 4xx/5xx) · `boardUrl`(셸 `boardSrc` 와 같은 규칙) · `flash(diff, reduced)`(48b 강조 계획 — 움직임 줄이기·many·빈 것 = null) · `FLASH`(Stitch 값: 외곽선 2px `rgba(96,86,240,.5)` 0.6초 보인 뒤 0.4초 사라짐 · 새 블록 0.3초 ease, 6px 아래에서 떠오름 · 새 틀 load 뒤 0.6초 전에는 시작하지 않음 = 판 모드 palette.js 가 load+0.5초에 움직임을 끝내므로). unit `tests/test_canvas_unit_swap.py`.
- `swap-diff`(Model, 순수, 48b) — `diff(옛 나무, 새 나무)` → `{changed, added, removed, many}`. 형제 줄은 통째로 같은 것(해시)끼리 LCS 로 먼저 잇고 그 틈은 같은 열쇠(태그 + #id·[data-region]·.첫 class)끼리 차례로 짝 · 글·속성(src·alt·placeholder·value) 다름 = changed · 인라인(b·span 등)의 바뀜·생김은 그것을 담은 블록 · 빠진 요소는 부모 블록 · 뿌리(body)는 강조 안 함 · 강조한 것의 안쪽은 빼기 · `MAX`(12)개 넘음 = many(강조 없음). 깨진 나무 = 빈 결과. unit `tests/test_canvas_unit_swap_diff.py`.
- `view-swap`(View) — 옛 iframe 바로 뒤 `iframe.hd-swap-next`(absolute, opacity 0)에 새 버전 → load → 옛 화면 스크롤 옮김 → 결정: 만지는 중 = 알약 `button.swap-pill` "새 버전 준비됨 · 반영"(누르면 바로 · 만지기가 끝나면 저절로 — `MutationObserver`, 미룬 카드가 있는 동안만 · 자리 = `.card` 안 `.phone` 밑 가장자리 바로 아래 오른쪽, 화면 안 버튼·탭 막대를 가리지 않는다) · 움직임 줄이기(설정 `motion:false` · `prefers-reduced-motion`) = 바로 · 아니면 새 것이 `FADE_MS`(0.2초) opacity 0→1(옛 것은 밑에 그대로 = 흰 깜빡임 없음) 뒤 옛 iframe 을 지운다. 보이기 직전에 셸 `ctx.frameLoaded(id, 새 틀)`(테마·반영 대기·메모 자리 — 숨어 기다리는 동안 바뀐 메모까지; 없으면 `[hd]` 경고 한 번) → 두 프레임 뒤 보이기. 새 것이 `.phone` 의 첫 iframe 이 된다(셸·다른 View 가 찾는 틀).
- 바뀐 곳 강조(48b, `view-swap`): 바꾸기 직전 옛 틀·새 틀 DOM(같은 출처만 — 앱 카드 등 다른 출처는 강조 없음)을 나무로 뽑아 `swapDiff.diff` → `swap.flash`. 새 블록은 보이기 전에 숨겨 두고(원래 `style` 속성은 그대로 되돌림), 강조는 부모에서 `Element.animate`(WAAPI — 판 모드 CSS 의 transition·animation 0초에 막히지 않음, 화면 문서에 class·style 이 남지 않음). palette.js 메시지는 쓰지 않는다(diff 가 이미 같은 출처 읽기를 요구하므로 같은 길로). 실패하면 `[hd]` 경고 한 줄, 새 화면은 그대로.
- 전/후 보기(48b): 바꿀 때 옛 화면 HTML 스냅숏(스크립트·`data-hd-links`·`data-hd-pick` 빼고 `<base>` 붙임)을 카드마다 마지막 것 하나 메모리에 · done 의도에 `before:true`. `hd-swap-compare {id, on}` = 새 틀 바로 뒤 `iframe.hd-swap-before`(srcdoc, `sandbox="allow-same-origin"` = 스크립트 없음, 지금 스크롤 자리) 겹치기·걷기. 그 카드의 새 교체가 시작되면 걷는다.
- 같은 내용(49c): 옛 틀이 낙관 반영으로 먼저 바뀐 틀(`iframe[data-hd-opt]`, view-optimistic 이 달고 틀과 함께 사라짐)이고 새 틀이 다 실렸을 때 나무가 같으면(`swap.same(diff)` = changed·added·removed 모두 빔, many 아님) `next` = `silent` — 만지는 중이어도 알약·겹치기·강조·전/후 없이 바로 바꾸고 done 에 `silent:true`·`before:false`. 그 카드에서 그 자리 글자 고치기 중(`.card.hd-typing`)이면 아님. 교체 길 밖의 틀(크게 보기)은 `same(frame, url)` → Promise<bool>(화면 밖 숨은 `iframe.hd-swap-probe` 에 실어 견줌, 다른 출처·시간 초과 = false). 낙관 반영 규칙은 `instant.md`.
- 실패 = 새 틀을 버리고 옛 화면 그대로 + `[hd]` 경고 + 의도 `hd-swap` failed → `view-busy` 가 그 카드 `.cerr` 한 줄(앱 카드 실패 줄과 같은 길, 다음 done 이 걷는다).
- 의도: `document` 의 CustomEvent `hd-swap` `{id, phase:'start'|'done'|'failed', why, before?}` — `view-busy`(칩·실패 줄) · `view-links`(done 이면 고른 카드의 링크를 다시 물어 화면 안 번호 ①② 를 새 틀에도, 48b)가 읽는다. `view-busy` → `view-swap` 은 `hd-swap-compare`. View 끼리 직접 부르지 않음. 상태 저장 없음.
- "방금 반영됨 ✓"(`busy.lookDone` · `busy.landed`, `view-busy`): 화면 파일이 바뀌어 걷힌 카드(손 걷기 × 는 아님)의 교체 done 뒤 같은 칩 자리에 `data-kind=done` 칩이 `busy.doneMs(before)`(전/후 보기가 있으면 `COMPARE_MS` 10초, 없으면 `DONE_MS` 2초) 동안 · 앱 카드가 hd-here 로 걷히면 바로. before 면 칩에 `button.bcmp[data-act=compare]` "전/후"(`busy.lookCompare` — 켜면 aria-pressed, 칩 글 "바뀌기 전 화면", 보는 동안 칩이 사라지지 않음 · 끄면 10초 다시). 칩이 걷히면 켜져 있던 전/후 보기도 끈다.

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/swap.js` · `swap-diff.js` · `view-swap.js` · `busy.js`·`view-busy.js` 의 "방금 반영됨"·전/후(48a·48b) | `unit or helper or notes`(+ `-k swap`) |
| `view-links.js` 의 `hd-swap` done 듣기(48b) | `unit or links` |
