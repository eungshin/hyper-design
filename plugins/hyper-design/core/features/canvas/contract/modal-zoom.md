# 크게 보기 확대·굴림 (modal-zoom · view-modal-zoom, R57 C)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 기준: 브라우저·Figma — 커서 자리 확대, 배율 칩이 % 를 보이고 고른다, 화면 위에 그린 것은 내용에 붙어 있다.

## 규칙

- **열 때 = 폭 맞추기**(100% 넘게 키우지 않음) — 화면이 창보다 길면 크게 보기 안에서 아래로 굴린다(그냥 휠). 짧은 화면은 지금처럼 한눈에: 화면 전체를 보이는 배율이 폭 맞추기의 3/4(`TALL`) 이상이면 전체(폰 390×844·데스크톱 1440×1024 = 전체, 1440×4000·860×40000 = 폭 맞추기). 광고 320×50 = 100%
- **창 크기** — 화면 × 배율만큼, 쓸 수 있는 칸(위쪽 줄 아래·두 도크 사이·도구 막대와 떠 있는 대화창 자리 뺌)까지. 창은 칸 가운데. 떠 있는 대화창 높이가 바뀌면(칩 줄) 다시 잰다(배율·굴림 그대로)
- **확대** — Ctrl/⌘+휠 = 커서 자리(덮개 어디서든, 화면 iframe 안이면 `palette.js` 가 `hd-wheel` 로 넘김) · Ctrl/⌘ += = 다음 단계 · Ctrl/⌘ - = 앞 단계 · Ctrl/⌘ 0 = 폭 맞추기(화면 안 초점이면 `palette.js` `hd-key zoom:true`). 범위 10%~400%, 단계 `STOPS`(브라우저 배율 단계). 브라우저 배율은 막는다. 창이 칸에 꽉 찬 쪽은 커서 밑 내용 점이 그대로, 아직 자라는 쪽은 가운데 기준(브라우저 그림 보기처럼)
- **배율 칩** — 크게 보기가 열린 동안 위쪽 `#zoom` 은 크게 보기 배율(`76% ▾`), 메뉴 = 폭 맞추기(Ctrl+0) · 100% · 확대(Ctrl+=) · 축소(Ctrl+-)(`view-menu` `MODAL_ZOOM` → 셸 `modalView`). 닫으면 판 배율로
- **붙어 있기** — `#mview`(굴림 칸) 안의 `#mbox`(화면 × 배율) 안에 iframe(`transform: scale`)·메모 핀 `#mpins`·고른 요소 테두리(`view-modal-pick`)가 있어 굴림을 그대로 따른다. 배율이 바뀌면 셸 `changed(s)` → `mscale` + `drawPins()`(핀·테두리) + `modalMoved()`, 굴림만 바뀌면 `modalMoved()` = 요소 막대 `BK.place()`(막대의 칸 = 보이는 `#mview`) · 글 칸 `placeTedit()` · 열린 우클릭 메뉴는 닫음. 그 자리 글자 고치기(`hd-inline`)는 화면 안이라 그대로. 메모 창(`#pop`)은 옮길 수 있는 창이라 그 자리에 둔다
- **Model `modal-zoom`** — `clamp` · `fit` · `view`(창 크기) · `scroll`(굴림 범위) · `at`(커서 자리 확대) · `step` · `wheel` · `pct`. **View `view-modal-zoom`** — 상태 `{s, mode:'fit'|'user'}`(저장 안 함, 'fit' 이면 창 크기가 바뀔 때 다시 맞춤), 전 셸 `sizeModal` 의 칸 재기를 옮겼다(셸 `sizeModal()` = `MZ.layout()` 한 줄). 다른 화면으로 넘어가면(`hd-here`) 배율 그대로 맨 위부터
- **오류 탐지** — 크기를 못 재면 100% + `[hd]` 경고 한 줄. 옛 `palette.js` 를 가진 out 폴더는 화면 안 Ctrl+휠이 브라우저 배율로 간다(덮개·창 테두리 위는 됨)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/modal-zoom.js` | `unit` (`test_canvas_unit_modal_zoom.py`) |
| `modules/view-modal-zoom.js` · 셸 `MZ`·`modalMoved`·`placeTedit` · `#mview` CSS · `view-menu` `MODAL_ZOOM` · `palette.js` `hd-wheel`·`hd-key zoom` | `unit or modal or menu or tools` + `--surface frame` (`test_canvas_modal_zoom.py`) |
