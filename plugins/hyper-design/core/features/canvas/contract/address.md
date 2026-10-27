# 주소 복사 (R30 — Figma '선택 링크 복사')

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/address.js` | Model | 주소 줄 만들기·읽기 · 40자 글 · 프로젝트 이름(out → 그 위 폴더) · out 폴더 · 복사 대상(고른 묶음 안을 누르면 묶음 전체). 상태 없음. `HD.address = {build, parse, lines, short, projectOf, outOf, fileOf, targets, say}` |
| `modules/view-address.js` | View | 카드·요소 → 주소 항목 → 클립보드 + 토스트, Ctrl/Cmd+L. 상태 = 프로젝트 이름(`GET /api/projects` 의 지금 줄 이름, 없으면 폴더 이름) · 복사 함수. 등록부 `address`(needs `$ toast warn cardEl selected pickedAll picked api`) → `{attach({copy}), cards(ids), element(screen, h, inModal), items(list), copy(items)}` |
| `hd/hd_address.py` | Model(Python) | 같은 줄 읽기(`parse` · `lines`) — `hd locate` 가 쓴다 |

셸: 카드 메뉴 `card-addr`(복제 바로 뒤, 여러 장이면 `(N)`) · 요소 메뉴 `addr`(`blocks.menu` 요청 묶음 끝, `links` = 셸이 덧붙일 연결 항목 수) · `AD = FT.address` 와 `attach({copy: SN.copy})`(보내기와 같은 클립보드 + execCommand 예전 길) 한 줄.

## 규칙

- 줄 = `hd://<프로젝트>/<화면 id>[#<요소 경로>]  <화면 파일 절대 경로> · "<짧은 글>"`, 대상마다 한 줄(고른 차례). 화면 id = 메모 요청문 `screen=…`, 요소 경로 = palette.js `pathOf`(요청문 `path=…`) — 다른 경로 체계를 만들지 않는다. 토큰(`?hd=`)은 넣지 않는다
- 퍼센트 바꾸기는 줄을 깨는 글자만: 프로젝트·화면 = `% 공백 # / ? "` · 제어 글자, 요소 경로 = `% 공백 # "` · 제어 글자. 한글은 그대로. 파일 경로는 그대로(바로 열 수 있게 — 끝의 ` · "` 로 가른다). 글 = 공백 하나로, 40자 넘으면 39자 + `…`, `\` 와 `"` 앞에 `\`
- 왕복: `parse(build(x)) == x` — 공유 fixture `tests/fixtures/addresses.json` 을 JS(`test_canvas_unit_address.py`)와 Python(`hd/tests/test_hd_address.py`)이 같이 읽는다. 줄 모양을 바꾸면 fixture 와 두 parse 를 함께
- 카드 = 그 카드(여러 장 고른 채 그중 하나를 오른쪽 클릭 = 고른 카드 모두). 요소 = 누른 요소가 판에서 고른 묶음(R19) 안이면 묶음 전체, 아니면 그 하나 · 크게 보기 = 그 하나
- Ctrl/Cmd+L: 크게 보기 = 고른 요소 · 판 = 고른 요소 모두 → 없으면 고른 카드. 고른 것이 없거나 입력 중이면 브라우저 기본 그대로
- 요소 메뉴 10개 한도(R27 F05): 셸의 연결 항목까지 세어 넘으면 '주소 복사'만 빠진다(지금은 속성을 고칠 수 있는 요소 + 판의 연결 두 줄일 때 — Ctrl+L 로는 됨)
- 토스트: "주소를 복사했어요" · "주소 N개를 복사했어요" · 실패 "주소를 복사하지 못했어요 — 다시 해 보세요". 판에 없는 카드·경로 없는 요소는 건너뛰고 `[hd]` 경고
- 터미널 쪽: `hd locate <주소…|->` 가 같은 줄을 읽어 화면 파일 · 경로 · 지금 바깥 HTML 앞 300자를 보인다(읽기만, `hd/contract.md`)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/address.js` · `hd/hd_address.py` · `tests/fixtures/addresses.json` | `-m unit -k address` + `hd/tests -k address` |
| `modules/view-address.js` · 셸 메뉴 줄 | `unit or tools --surface frame` |
