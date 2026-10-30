# 테마 패널 · 팔레트 적용 (view-theme)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(팔레트 적용을 셸에서 옮김 — 셸 섬 빼기 C10, 2026-10-26).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/theme.js` | Model | 테마 목록·내 테마·색 네 칸·대비 규칙(머리 주석) |
| `modules/view-theme.js` | View | 테마 패널 그리기·누르기·저장 + 팔레트 적용: 고른 테마 = `#tokens` href 를 `tokens-<slug>.css` 로(`data-base` 에 원래 주소), 모든 iframe 에 `hd-palette {slug}` · `hd-theme-vars {vars}`, 키 `hd-palette`. 상태 = 테마 상태(`T.load`) · 지금 팔레트 `cur`·`curVars`. ctx `{$, $$, esc, root, bases, readColors(), record, getItem, setItem}`. `HD.viewTheme.mount(ctx) → {render(), send(frame)}` — 셸 `VT` |
| 셸 | — | 새로 실린 틀(판 카드 `frameLoaded` · 크게 보기 · Foundation/Components 탭 · 나눈 칸 `onFrame` — VT 보다 먼저 붙는 VP 는 `if (VT)`)에 `VT.send(frame)` |

## 규칙

- 고르기 전(`cur` 없음)에는 보내지 않는다 · 아직 문서가 없는 틀에 보내기 실패 = 조용히(실리면 다시 보낸다)
- 프로젝트 색(R55, `ds-edit.md`): 목록 끝 '프로젝트 색 · tokens.css'(`@project`) = 바탕 팔레트 없이 tokens.css 그대로. 의도 `hd-theme-project`(토큰 저장 뒤)가 오면 다른 팔레트·내 테마를 미리 보던 중일 때만 그리로 바꾸고 `detail.changed = true`
- 메시지 이름·`hd-palette` 키는 `foundation/palette.js`·DS 카드(`view-ds-card`)가 읽으므로 그대로

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/theme.js` · `view-theme.js` · 셸 `VT.send` | `unit or theme` (+ 판 카드 싣기와 함께 고치면 `board-motion.md` 의 줄) |
