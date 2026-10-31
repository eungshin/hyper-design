# Foundation 토큰 · Components 부품 고치기 (ds-edit · view-ds-inspect, R55)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 사용자 요청(10-30): Foundation·Components 탭에서 선택 도구로 토큰(·컴포넌트)을 골라 바꾸면 그것을 쓰는 모든 화면이 한 번에 바뀐다. phase F = Foundation 토큰, phase C = Components 부품 — 같은 고르기·창·되돌리기·다시 읽기에 종류(kind 'part')를 더했다. 사용자 결정(10-30): 부품 속성은 Foundation 토큰 가운데 **같은 묶음** 안에서만 고른다(자유 값 없음 — 값은 Foundation 탭에서만 바뀐다).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/ds-edit.js` | Model | 토큰 종류(`kindOf`) · 부품 칸 묶음(`family`·`same` — Python `component_edit` 와 같은 표 `tests/fixtures/component-families.json`) · 다시 읽기 메시지(`reloadMsg`) · 값 검사(`check` — Python 과 같은 표) · 고칠 칸(`fields`·`compose`) · 문서 탭 고르기 메시지(`pickMsg`·`readPick`) · 토큰 주소(`href`) · `docTab`. 상태 없음 |
| `modules/view-ds-inspect.js` | View | 문서 탭 도구(손·선택) · 속성 창 · 저장·되돌리기 · 모든 틀 다시 읽기. 상태 = 문서 탭 도구·지금 탭·고른 토큰·경고한 탭(이 View 만). `HD.feature('dsEdit', {needs: ['$', '$$', 'toast', 'warn', 'api', 'record']})` → `{tab(name), tool(t), current()}` |
| `component_edit.py` | Model(Python) | `family`·`same` · `rules`(맨 위 규칙만, @media 안 건너뜀) · `slots`(요소를 겨누는 규칙·바꿀 칸) · `check` · `rewrite`(그 var(--from) 하나만) · `titles` — I/O 없음 |
| `token_edit.py` | Model(Python) | 쉬운 이름 `label`(Foundation 표 COLOR_NAMES… — build_canvas 가 가져다 씀) · `kind` · `decls`(첫 `:root{…}`, 주석 건너뜀, 같은 이름은 뒤 것) · `check` · `rewrite`(그 선언 하나만) — I/O 없음 |
| `screen_edits.apply_token`·`apply_component`·`component_slots` · `history.History.token`·`component` · `router` `POST /api/token`·`/api/component`·`/api/component-slots` | Edge | 쓰기 한 번 = `.hd-history/<stamp>/tokens.css`(또는 `components.css`) 원본 + manifest → `/api/restore` 로 되돌림 · slots = 읽기만 |
| 셸 | — | `showTab` → `FT.dsEdit.tab(name)` · `setTool` → 문서 탭이면 `FT.dsEdit.tool(t)` · Ctrl+Z 는 모든 탭 |

## 규칙

- **도구** — Foundation·Components 탭에서는 도구 막대(`#tools`)를 그 탭 칸으로 옮기고 손·선택(V)만 보인다(다른 도구·구분선·숨긴 것은 숨김). 문서 iframe 은 막대 자리(64px)를 비킨다. H·V 키. 위쪽 줄·대화창은 그대로, `#vbtn`·`#zoom` 은 쉰다(셸 그대로). Screens 로 돌아오면 막대는 판으로, 판 도구 눌림 그대로
- **고르기** — 선택이면 그 탭 `iframe.doc` 에 `hd-pick {on:true, mode:'select', doc:true}`, 손이면 `on:false`(손 = 그냥 보기, R52). palette.js 는 `[data-var]`(closest)를 누르면 `hd-sel` + `token`·`tokenKind`·`label`(견본이 보이는 이름)·`vars`(그 토큰 + 글자 줄 짝 `--fw-`·`--lh-` 의 지금 값)·`rect` 로 답하고 그 견본에 고른 테두리(스크롤을 따라감). 견본 밖 = `path:null`(창 닫기). 마우스 올림 테두리도 견본에만. 문서 안을 누른 뒤의 H·V·Esc·Ctrl+Z/Y 는 `hd-key` 로 캔버스에 넘긴다
- **속성 창**(`#dsInsp`) — 견본 오른쪽 → 왼쪽 → 아래, 문서 칸 안으로(`HD.popPlace.clamp`, R58). 제목 = 견본 이름 + 토큰 이름. 색 = 색 판 + HEX · 크기·여백·모서리 = 숫자 + 지금 단위 · 굵기 = 100~900 · 줄 높이 = 숫자 · 그림자·그 밖 = 글. 글자 줄 = 크기·굵기·줄 높이 칸(있는 짝만) — 어느 칸을 고치나가 종류. Enter·change = 저장, Esc·×·밖 누르기 = 닫기. 틀린 값 = 그 칸을 원래 값으로 + 빨간 테두리 + 까닭 한 줄(쓰지 않음)
- **값 규칙**(Python `token_edit.check` = JS `HD.dsEdit.check`, 표 `tests/fixtures/token-values.json`) — 있는 토큰 이름만(`없는 토큰: --x`), 200자 이하, `; { } < > \` · 제어 문자 · `url(` · `expression` · 주석 · `@import` 거절. 색 = `#hex`(3·4·6·8, 대문자로) · `rgb/rgba/hsl/hsla(숫자)` · 길이 = `0` 또는 숫자 + `px|rem|em|%|vw|vh`(음수 없음) · 굵기 = 100~900 정수 · 줄 높이 = 0.5~5 또는 길이 · 그림자 = `#·글자·숫자·공백·.,()%/-` 만
- **저장** — `POST /api/token {name, value}` → `tokens.css` 첫 `:root{…}` 의 그 선언(같은 이름이 여럿이면 뒤 것) 값만 바꿈(다른 바이트 그대로). 400 `{error, reason:'invalid'}` · 404(tokens.css 없음) · 빌드 확인 실패 = 되돌리고 500. 답 `{name, value, old, stamp}`
- **반영** — 저장 뒤 의도 `hd-theme-project`(테마 패널: 다른 팔레트·내 테마 색을 미리 보던 중이면 프로젝트 색 `@project` 로 → 토스트 '테마 미리 보기를 끄고 프로젝트 색으로 바꿨어요') → 모든 iframe 에 `hd-css-reload {sheet:'tokens', v}`(카드·크게 보기·DS 카드·문서 탭·나눈 칸 — `#tokens` 를 지금 팔레트 주소 + `?v=`), 셸 `#tokens` 도 프로젝트 색일 때. Foundation `.val` 은 다시 읽는다
- **되돌리기** — 기록 한 줄 '토큰 바꾸기 --이름'(status file): Ctrl+Z·되돌리기 단추 = `/api/restore {stamp}` 뒤 다시 읽기, 다시 하기 = 같은 값 다시 쓰기(새 stamp). 그 뒤 tokens.css 가 바뀌었으면 409 까닭 토스트. 새로고침 뒤에는 파일 쓰기 줄이라 되돌릴 수 없다(기록 규칙 그대로)
- **다른 탭·AI** — 도우미 `/api/files` 바뀐 목록에 `@tokens`(tokens.css mtime, 화면 id 아님) → view-busy 가 의도 `hd-css-changed {sheet:'tokens'}` → 다시 읽기만(화면 카드는 화면 파일이 끌어 쓰는 파일 규칙 F25 로 이미 다시 실림)
- **테마** — 테마 목록 끝에 '프로젝트 색 · tokens.css'(`@project`, 잠김 표시) — 바탕 팔레트 없이 tokens.css 그대로. palette.js·DS 카드도 `@project` = 원래 주소
- **읽기만 탭** — 선택(V)·고르기·창은 된다(`HD.readOnly.key` 의 `doc`, `PICK` 단추는 막지 않음), 저장만 막고 '여기서 편집하기' 토스트. 창에 '읽기만 하는 탭이라 저장은 막혀 있어요'
- **오류 탐지** — 탭에 `iframe.doc` 이 없음 · 문서에 `[data-var]` 가 없음(`hd-pick-on` 의 `tokens: 0`) · 실린 문서가 1.5초 안에 답하지 않음(palette.js 없음) = `[hd]` 경고 한 번 뒤 그 탭은 그냥 문서(고르기 끔). 저장 실패 = 도우미 까닭 토스트 + 칸 되돌림. 도우미 없음(file://) = 저장 대신 토스트
- **부품 고르기**(phase C) — `[data-var]` 가 없고 `.spec-stage` 가 있는 문서 = 부품 문서(`hd-pick-on` 의 `parts`). 선택(V)으로 `.spec-stage` 안을 누르면 components.css 맨 위 규칙(겹 선택자 하나)이 겨누는 요소 가운데 그 견본 묶음(`section[data-key]`) 클래스를 가진 가장 가까운 요소, 없으면 가장 가까운 것 · Alt = 가장 안쪽. `hd-sel` + `part {key, title, classes, tag, state}`. 테두리·손·키는 토큰과 같다
- **부품 창** — `POST /api/component-slots {classes, tag}` → 규칙마다 묶음: 바탕·변형(클래스 적은 것부터, 머리글 = 선택자) 다음 '상태' 아래 상태 규칙(누를 때 · 못 누를 때 · 올렸을 때 · 초점 · 켰을 때 …, 고른 견본의 상태면 '이 견본'). 선택자 목록이 다른 부품도 부르면 '버튼·칩·… 함께 바뀌어요'. 칸 = `var(--토큰)` 자리만(묶음 없는 토큰·글자 값은 보이지 않음): 쉬운 속성 이름(배경 · 글자 색 · 테두리 · 모서리 · 안쪽 여백 · 높이 · 글자 크기 · 굵기 · 그림자 · 간격 …, 없으면 CSS 이름) + 토큰 단추(색 점·모서리 조각 · 쉬운 이름 · 흐린 값). 단추 = 같은 묶음 토큰 목록(`#dsList`, 화면 안 · ↑↓ Enter Esc). 칸 없는 요소 = '이 요소에는 토큰으로 바꿀 칸이 없어요'
- **부품 묶음**(`family`) — 색 `--c-*` · 모서리 `--r-*` · 여백 · 글자 크기 `--fs-*` · 높이·너비 `--h-*`/`--w-*`(`box`) · 굵기 `--fw-*` · 줄 높이 `--lh-*` · 그림자 `--shadow-*` · 그 밖(`--icon`·`--font`) = 묶음 없음(바꿀 수 없음)
- **부품 저장** — `POST /api/component {selector, prop, index, from, to}` → 그 선택자의 마지막 규칙 · 그 속성 마지막 선언 · index 번째 `var(` 의 이름만(다른 바이트 그대로). 400 까닭: 모르는 선택자·속성·자리 · `from` 이 그 자리와 다름 · `to` 가 tokens.css 첫 `:root` 에 없음 · 다른 묶음 · 묶음 없는 토큰. 기록 한 줄 '부품 바꾸기 <부품> <속성>', 되돌리기 = restore, 다시 하기 = 같은 몸통 다시
- **다시 읽기 한 메시지** — `hd-css-reload {sheet:'tokens'|'components', v}`(옛 `hd-tokens-reload` 도 palette.js 가 받음). components = components.css 링크 + `?v=`. `/api/files` 의 `@components` → 의도 `hd-css-changed {sheet}`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/ds-edit.js` · `token_edit.py` · `palette.js` 의 `hd-token-kind` | `unit` (`test_canvas_unit_ds_edit.py` · `test_canvas_unit_token_edit.py`) |
| `modules/ds-edit.js` family · `component_edit.py` | `unit` (`test_canvas_unit_ds_edit.py` · `test_canvas_unit_component_edit.py`) |
| `modules/view-ds-inspect.js` · `/api/token`·`/api/component` · palette.js 토큰·부품 고르기 · 셸 `showTab`·`setTool` 한 줄 | `unit or dsedit or theme or dscard --surface frame` (`test_canvas_ds_edit.py`) |
