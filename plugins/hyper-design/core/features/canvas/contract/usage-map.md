# 부품 쓰는 화면 지도 (usage-map · view-usage, R58)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 사용자 결정(10-31, ①): Components 탭의 부품마다 쓰는 화면 수를 보이고, 누르면 판에서 그 화면들을 보인다. R55(부품을 고치면 쓰는 모든 화면이 바뀜) 전에 어느 화면인지 먼저 본다.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `usage_map.py` | Model(Python) | `classes(html)` · `spec_keys(견본 html)` · `usage(keys, [(id, classes)])` → `{key: [화면 id]}` · `mark_section` · `index_html` · components.html 안 `CSS`·`JS`. I/O 없음 |
| `board_data.usage(out, cards)` | Edge | 견본 파일(`HD_SPECIMENS`, 없으면 `foundation/specimens.html`)·화면 파일 읽기 → hd-data `usage` |
| `build_canvas.build_components(out, m, usage=None)` | Edge | 남은 section 마다 `data-used`·`id="spec-<key>"`·머리 칩, `<body>` 바로 뒤 목록, 칩 스크립트 |
| `modules/usage.js` | Model | `read(raw, ids)` → `{map, bad, unknown}` · `count` · `label(n)` · `bar(title, n)` · `showMsg(d)`. 상태 없음 |
| `modules/view-usage.js` | View | 판 강조·막대·걷기. 상태 = 지도 · 꺼짐 · 지금 부품(이 View 만). `HD.feature('usage', {needs: ['$', '$$', 'toast', 'warn', 'rowsEl', 'cardEl', 'focus']})` → `{show(key, title), clear(), current()}` |
| `modules/view-ds-inspect.js` | View | 부품 창 머리 '쓰는 화면 N' — 수는 의도 `hd-usage-count`, 누르면 의도 `hd-usage-show` |

## 규칙

- **쓴다** — 화면 파일 안 어떤 요소의 `class` 에 견본 key 가 있다(`data-class` 같은 다른 속성은 아님 — `usage_map.classes`, components.html 거르기 `used_classes` 도 같은 함수). 차례 = 판 차례(상태 변형은 원래 화면 뒤). 쓰는 화면이 없는 key 는 지도에 없다. 배지(`badge`)는 지도·칩 없음(screens.json badges 로 그림)
- **데이터** — hd-data `usage` `{key: [화면 id]}`(`board_data.index_data` — 빌드·도우미 `/api/data` 같은 것) · components.html section `data-used="id id"`. 앱 프로젝트(개발 서버 카드)·견본 파일 없음 = `{}`(아무것도 안 보임, 경고 없음)
- **Components 탭** — section 머리(제목 `.spec::before`) 오른쪽 끝 칩 '쓰는 화면 N' · 맨 위 얇은 목록 '부품 N' + 이름·수(누르면 그 section 으로). 칩·목록은 window 잡는 단계에서 받아 선택(V) 고르기와 겹치지 않는다
- **보이기** — 칩 → `hd-usage-show {key, title}`(그 iframe 에서만 받음) · 속성 창 칩 → 의도 `hd-usage-show`. Screens 탭 단추를 눌러 판으로 → 그 카드 `.use-hit`(테두리) · `#rows.use-on` 나머지 카드 흐림(.22)·선 흐림 → 카메라 `ctx.focus(ids, 1)`(셸 `fitCards`, 100% 까지) → 판 위 가운데 막대 `#useBar` '버튼 · 쓰는 화면 5 · ✕'
- **걷기** — ✕ · Esc(Screens 탭, 입력 칸 밖) · 다른 탭으로
- **오류 탐지** — `usage` 가 객체가 아님·값이 글 목록이 아님 = `[hd]` 경고 한 번 + 칩 숨김(문서 탭에 `hd-usage-off` → `html.use-off`) · 판에 없는 화면 id = 빼고 `[hd]` 한 줄 · 지도에 없는 부품을 누름 = 토스트 '이 부품을 쓰는 화면을 찾지 못했어요'
- 판 데이터가 바뀐 뒤(도우미 쓰기) 지도는 새로고침 때 다시 읽는다(components.html 도 페이지를 다시 줄 때 다시 빌드)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `usage_map.py` · `board_data.usage` · `modules/usage.js` | `unit` (`test_canvas_unit_usage_map.py`) |
| `modules/view-usage.js` · 칩 스크립트 · 속성 창 칩 · `build_components` | `unit or dsedit --surface frame,board` (`test_canvas_usage_map.py`) |
