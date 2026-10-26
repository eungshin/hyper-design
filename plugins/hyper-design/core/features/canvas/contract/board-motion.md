# 판 위 카드 움직임 · 라이브 상한 (task 35 · 근거 `tasks/34-motion-research/REPORT.md` §4)

`../contract.md` 의 책임 게이트·테스트 층을 따른다.

- **판 모드**: 판 위 카드 iframe 은 화면 주소에 `hd-mode=board` 를 붙여 싣는다(`HD.swap.boardUrl` — `view-live-cap` 의 `load` 가 부름, `?`/`&`, `#` 앞). `data-src` 는 붙이지 않은 원래 주소 그대로, 실린 주소의 원본은 `data-live`. 크게 보기(`#mframe`)는 붙이지 않는다 = 라이브
- `foundation/palette.js` 가 판 모드면 화면 스크립트보다 먼저: (a) `matchMedia('(prefers-reduced-motion: reduce)')` = 맞음(`no-preference` = 아님, 다른 질의 그대로) — 앱의 무모션 경로를 켠다 (b) `style[data-hd-board]` 하나: transition 0s · animation 1ms/-1ms/1회(!important) — 유한 = 끝 상태, 무한 = 한 번 뒤 멈춤 (c) load 와 그 0.5초 뒤 `getAnimations()` 유한 finish · 무한 pause(실패는 `[hd]` 경고). 움직임 없는 정적 화면은 달라 보이지 않는다
- **라이브 상한**(Model `modules/live-cap.js`, `HD.liveCap = {K: 10, IDLE: 15000, MINW: 48, MARGIN: 80, readable, near, unload}` · View `modules/view-live-cap.js` = 셸 `LC`(셸 C10 — 상태 `seenAt`·타이머, ctx `{$, $$, pane, rowsEl, selected(), modalScreen(), loaded(id, frame)}` → `{load(frame), visible(), schedule()}`, 실린 카드 = 셸 `frameLoaded` 하나(등록부 ctx `frameLoaded` 와 같은 함수)): `LC.visible`(이동·확대 뒤 100ms, 그리고 5초마다)이 보이는 카드의 마지막 본 시각을 적고, 실린 카드가 K 를 넘으면 화면 밖 IDLE 넘은 카드를 오래 안 본 것부터 K 까지 내린다. 보이는·고른·크게 보기 카드는 내리지 않는다
- **LOD — 읽히는 크기 아래는 iframe 없음**(figma-lite 1, 10-26 · `HD.liveCap.MINW = 48` — 처음 120 이었으나 7% 에서 모든 카드가 빈 흰 상자가 되어 축소 윤곽(Figma·Stitch 는 축소해도 내용 윤곽이 보임)을 잃고 메모리 이득은 작아(395→376MB, 내린 틀이 about:blank 로 남음) 점처럼 작을 때만으로 낮춤 — 미리보기 그림이 생기면 올린다, `readable(w)`): `loadVisible` 은 카드의 화면 위 너비(배율이 아니라 `.phone` 상자 너비 — 크기를 바꾼 카드도 같은 규칙)가 MINW 아래면 싣지 않고, 이미 실린 것은 `unload({small})` 가 상한·IDLE 과 상관없이 바로 내린다(아래 '내리기'와 같은 길). 고른 카드·크게 보기 카드는 작아도 싣고 내리지 않는다(고르기가 바뀌면 `scheduleVisible`). 작은 카드는 지금의 안 실린 모습 그대로 = 틀·제목·흰 바탕(Figma·Stitch 의 멀리서 본 프레임처럼 평평한 채움 + 이름, 깨진 틀 없음). 다시 확대하면 100ms 뒤 실린다(실측 dayfine: 7% 에서 실린 카드 12→0 · 다시 50% 로 확대 후 실릴 때까지 0.6~2.9초 = 화면 로드 시간). 메모 핀·연결·교체는 안 실린 카드를 이미 다룬다(data-src)
- **확대 중 선 굵기·태그 배율**(figma-lite 2, 10-26): 셸 `apply()` 는 `#stage` transform·배율 칩을 바로 쓰고, `#rows` 의 `--lw`·`--ts`(아래 전체 스타일 다시 계산)는 `scheduleZoomVars` 로 — 한 프레임에 한 번, 쓴 값과 10% 넘게 다를 때만, 마지막 apply 150ms 뒤 정확한 값(부팅 첫 값은 바로). 이동만(배율 같음)이면 쓰지 않는다. `HDCanvas.view()` 는 그대로 바로 지금 값. 실측 dayfine 60 Ctrl+휠: 스타일 다시 계산 76→43ms(변수를 아예 안 쓰면 8ms)
- 내리기 = `data-src` 를 원래 주소로 되돌리고 `src = about:blank` — 카드 틀·제목·핀은 그대로, 다시 보이면 `LC.visible` 이 다시 싣는다(`wired` 듣는 이는 그대로, `about:blank` load 는 무시)
- 테스트 고리: `HD.liveCap.K`·`IDLE`·`MINW` 은 부를 때마다 읽는다 — 브라우저 테스트가 줄여서 기다리지 않는다
- 실측(10-24): 지금 Dayfine 무대 19개는 가만히 있을 때 도는 애니메이션 0개(판·크게 보기 모두) — 판 모드의 효과는 상호작용·스피너가 붙을 때

## 고치면 돌릴 것

| 고친 곳 | 돌릴 것 |
|---|---|
| `modules/live-cap.js`(`near` = 판 칸 + 여유 80px, `test_canvas_unit_live_cap_near.py`) | `-m unit -k live_cap` |
| `modules/view-live-cap.js` · 셸 `LC`·`frameLoaded` · `apply`/`scheduleZoomVars` · `swap.boardUrl` · `palette.js` 판 모드 | `-m "unit or motion or modal or links or tools"` + `pytest $SK/features/app/tests -k board_card`(slow) |
