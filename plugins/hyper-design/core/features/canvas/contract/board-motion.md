# 판 위 카드 움직임 · 라이브 상한 (task 35 · 근거 `tasks/34-motion-research/REPORT.md` §4)

`../contract.md` 의 책임 게이트·테스트 층을 따른다.

- **판 모드**: 판 위 카드 iframe 은 화면 주소에 `hd-mode=board` 를 붙여 싣는다(셸 `boardSrc` — `?`/`&`, `#` 앞). `data-src` 는 붙이지 않은 원래 주소 그대로, 실린 주소의 원본은 `data-live`. 크게 보기(`#mframe`)는 붙이지 않는다 = 라이브
- `foundation/palette.js` 가 판 모드면 화면 스크립트보다 먼저: (a) `matchMedia('(prefers-reduced-motion: reduce)')` = 맞음(`no-preference` = 아님, 다른 질의 그대로) — 앱의 무모션 경로를 켠다 (b) `style[data-hd-board]` 하나: transition 0s · animation 1ms/-1ms/1회(!important) — 유한 = 끝 상태, 무한 = 한 번 뒤 멈춤 (c) load 와 그 0.5초 뒤 `getAnimations()` 유한 finish · 무한 pause(실패는 `[hd]` 경고). 움직임 없는 정적 화면은 달라 보이지 않는다
- **라이브 상한**(Model `modules/live-cap.js`, `HD.liveCap = {K: 10, IDLE: 15000, unload}`): 셸 `loadVisible`(이동·확대 뒤 100ms, 그리고 5초마다)이 보이는 카드의 마지막 본 시각을 적고, 실린 카드가 K 를 넘으면 화면 밖 IDLE 넘은 카드를 오래 안 본 것부터 K 까지 내린다. 보이는·고른·크게 보기 카드는 내리지 않는다
- 내리기 = `data-src` 를 원래 주소로 되돌리고 `src = about:blank` — 카드 틀·제목·핀은 그대로, 다시 보이면 `loadVisible` 이 다시 싣는다(`wired` 듣는 이는 그대로, `about:blank` load 는 무시)
- 테스트 고리: `HD.liveCap.K`·`IDLE` 은 부를 때마다 읽는다 — 브라우저 테스트가 줄여서 기다리지 않는다
- 실측(10-24): 지금 Dayfine 무대 19개는 가만히 있을 때 도는 애니메이션 0개(판·크게 보기 모두) — 판 모드의 효과는 상호작용·스피너가 붙을 때

## 고치면 돌릴 것

| 고친 곳 | 돌릴 것 |
|---|---|
| `modules/live-cap.js` | `-m unit -k live_cap` |
| 셸 `loadVisible`·`boardSrc` · `palette.js` 판 모드 | `-m "unit or motion or modal or links or tools"` + `pytest $SK/features/app/tests -k board_card`(slow) |
