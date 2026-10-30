# Foundation 토큰 고치기 (ds-edit · view-ds-inspect, R55)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 사용자 요청(10-30): Foundation·Components 탭에서 선택 도구로 토큰(·컴포넌트)을 골라 바꾸면 그것을 쓰는 모든 화면이 한 번에 바뀐다. 이 파일은 phase F(Foundation 토큰). phase C(컴포넌트)는 같은 고르기·창에 종류(kind)를 더한다.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/ds-edit.js` | Model | 토큰 종류(`kindOf`) · 값 검사(`check` — Python 과 같은 표) · 고칠 칸(`fields`·`compose`) · 문서 탭 고르기 메시지(`pickMsg`·`readPick`) · 토큰 주소(`href`) · `docTab`. 상태 없음 |
| `modules/view-ds-inspect.js` | View | 문서 탭 도구(손·선택) · 속성 창 · 저장·되돌리기 · 모든 틀 다시 읽기. 상태 = 문서 탭 도구·지금 탭·고른 토큰·경고한 탭(이 View 만). `HD.feature('dsEdit', {needs: ['$', '$$', 'toast', 'warn', 'api', 'record']})` → `{tab(name), tool(t), current()}` |
| `token_edit.py` | Model(Python) | `kind` · `decls`(첫 `:root{…}`, 주석 건너뜀, 같은 이름은 뒤 것) · `check` · `rewrite`(그 선언 하나만) — I/O 없음 |
| `screen_edits.apply_token` · `history.History.token` · `router` `POST /api/token` | Edge | 쓰기 한 번 = `.hd-history/<stamp>/tokens.css` 원본 + manifest → `/api/restore` 로 되돌림 |
| 셸 | — | `showTab` → `FT.dsEdit.tab(name)` · `setTool` → 문서 탭이면 `FT.dsEdit.tool(t)` · Ctrl+Z 는 모든 탭 |

## 규칙

- **도구** — Foundation·Components 탭에서는 도구 막대(`#tools`)를 그 탭 칸으로 옮기고 손·선택(V)만 보인다(다른 도구·구분선·숨긴 것은 숨김). 문서 iframe 은 막대 자리(64px)를 비킨다. H·V 키. 위쪽 줄·대화창은 그대로, `#vbtn`·`#zoom` 은 쉰다(셸 그대로). Screens 로 돌아오면 막대는 판으로, 판 도구 눌림 그대로
- **고르기** — 선택이면 그 탭 `iframe.doc` 에 `hd-pick {on:true, mode:'select', doc:true}`, 손이면 `on:false`(손 = 그냥 보기, R52). palette.js 는 `[data-var]`(closest)를 누르면 `hd-sel` + `token`·`tokenKind`·`label`(견본이 보이는 이름)·`vars`(그 토큰 + 글자 줄 짝 `--fw-`·`--lh-` 의 지금 값)·`rect` 로 답하고 그 견본에 고른 테두리(스크롤을 따라감). 견본 밖 = `path:null`(창 닫기). 마우스 올림 테두리도 견본에만. 문서 안을 누른 뒤의 H·V·Esc·Ctrl+Z/Y 는 `hd-key` 로 캔버스에 넘긴다
- **속성 창**(`#dsInsp`) — 견본 오른쪽 → 왼쪽 → 아래, 문서 칸 안으로(`HD.popPlace.clamp`, R58). 제목 = 견본 이름 + 토큰 이름. 색 = 색 판 + HEX · 크기·여백·모서리 = 숫자 + 지금 단위 · 굵기 = 100~900 · 줄 높이 = 숫자 · 그림자·그 밖 = 글. 글자 줄 = 크기·굵기·줄 높이 칸(있는 짝만) — 어느 칸을 고치나가 종류. Enter·change = 저장, Esc·×·밖 누르기 = 닫기. 틀린 값 = 그 칸을 원래 값으로 + 빨간 테두리 + 까닭 한 줄(쓰지 않음)
- **값 규칙**(Python `token_edit.check` = JS `HD.dsEdit.check`, 표 `tests/fixtures/token-values.json`) — 있는 토큰 이름만(`없는 토큰: --x`), 200자 이하, `; { } < > \` · 제어 문자 · `url(` · `expression` · 주석 · `@import` 거절. 색 = `#hex`(3·4·6·8, 대문자로) · `rgb/rgba/hsl/hsla(숫자)` · 길이 = `0` 또는 숫자 + `px|rem|em|%|vw|vh`(음수 없음) · 굵기 = 100~900 정수 · 줄 높이 = 0.5~5 또는 길이 · 그림자 = `#·글자·숫자·공백·.,()%/-` 만
- **저장** — `POST /api/token {name, value}` → `tokens.css` 첫 `:root{…}` 의 그 선언(같은 이름이 여럿이면 뒤 것) 값만 바꿈(다른 바이트 그대로). 400 `{error, reason:'invalid'}` · 404(tokens.css 없음) · 빌드 확인 실패 = 되돌리고 500. 답 `{name, value, old, stamp}`
- **반영** — 저장 뒤 의도 `hd-theme-project`(테마 패널: 다른 팔레트·내 테마 색을 미리 보던 중이면 프로젝트 색 `@project` 로 → 토스트 '테마 미리 보기를 끄고 프로젝트 색으로 바꿨어요') → 모든 iframe 에 `hd-tokens-reload {v}`(카드·크게 보기·DS 카드·문서 탭·나눈 칸 — `#tokens` 를 지금 팔레트 주소 + `?v=`), 셸 `#tokens` 도 프로젝트 색일 때. Foundation `.val` 은 다시 읽는다
- **되돌리기** — 기록 한 줄 '토큰 바꾸기 --이름'(status file): Ctrl+Z·되돌리기 단추 = `/api/restore {stamp}` 뒤 다시 읽기, 다시 하기 = 같은 값 다시 쓰기(새 stamp). 그 뒤 tokens.css 가 바뀌었으면 409 까닭 토스트. 새로고침 뒤에는 파일 쓰기 줄이라 되돌릴 수 없다(기록 규칙 그대로)
- **다른 탭·AI** — 도우미 `/api/files` 바뀐 목록에 `@tokens`(tokens.css mtime, 화면 id 아님) → view-busy 가 의도 `hd-tokens-changed` → 다시 읽기만(화면 카드는 화면 파일이 끌어 쓰는 파일 규칙 F25 로 이미 다시 실림)
- **테마** — 테마 목록 끝에 '프로젝트 색 · tokens.css'(`@project`, 잠김 표시) — 바탕 팔레트 없이 tokens.css 그대로. palette.js·DS 카드도 `@project` = 원래 주소
- **읽기만 탭** — 선택(V)·고르기·창은 된다(`HD.readOnly.key` 의 `doc`, `PICK` 단추는 막지 않음), 저장만 막고 '여기서 편집하기' 토스트. 창에 '읽기만 하는 탭이라 저장은 막혀 있어요'
- **오류 탐지** — 탭에 `iframe.doc` 이 없음 · 문서에 `[data-var]` 가 없음(`hd-pick-on` 의 `tokens: 0`) · 실린 문서가 1.5초 안에 답하지 않음(palette.js 없음) = `[hd]` 경고 한 번 뒤 그 탭은 그냥 문서(고르기 끔). 저장 실패 = 도우미 까닭 토스트 + 칸 되돌림. 도우미 없음(file://) = 저장 대신 토스트
- **phase C 자리** — `readPick`·`fields` 는 종류를 받는다: 컴포넌트는 `data-part` 같은 표시 + 새 종류로 같은 창·고르기에 더한다(이 파일에 규칙 줄 추가)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/ds-edit.js` · `token_edit.py` · `palette.js` 의 `hd-token-kind` | `unit` (`test_canvas_unit_ds_edit.py` · `test_canvas_unit_token_edit.py`) |
| `modules/view-ds-inspect.js` · `/api/token` · palette.js 토큰 고르기 · 셸 `showTab`·`setTool` 한 줄 | `unit or dsedit or theme or dscard --surface frame` (`test_canvas_ds_edit.py`) |
