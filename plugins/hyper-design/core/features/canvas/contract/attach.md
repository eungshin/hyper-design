# 첨부 이미지 (attach · view-attach · 서버 attach_rules/Attachments, R22)

`../contract.md` 의 책임 게이트(오류 탐지 포함)·테스트 층을 따른다. 붙인 스크린샷을 out 안 파일로 저장하고, 그 절대 경로를 요청 글에 넣어 터미널 에이전트(Claude Code — Paseo/CLI)가 열 수 있게 한다.

## 모듈 (맡은 일 · 가진 상태 · 받는 것 · 내보내는 것)

| 모듈 | 층 | |
|---|---|---|
| `attach_rules.py` | Model(순수) | 종류 = 앞 바이트(PNG·JPEG·WebP·GIF, 이름·Content-Type 은 안 봄) · 한도 `MAX_BYTES` 10 MB(풀린 바이트) · 본문 한도 `BODY_MAX`(base64 + 머리) · base64/`data:` 풀기 · 파일 이름 `<시각>-<n>.<ext>` · `parse_rel`(`.hd-attach/<그 모양 이름>` 만). 상태 없음 |
| `attach_store.py` `Attachments` | Edge | `<out>/.hd-attach/` 에 한 장씩(임시 파일 + `out_io._replace`) · 이름 고르기 자물쇠 하나(세션 쓰기 자물쇠는 잡지 않음) · 읽기. 폴더가 out 밖으로 풀리면(링크) 400, 쓰기 실패면 임시 파일을 지우고 500 |
| `router.py` | Controller | `POST /api/image {data, name?}` → `{path(절대), rel, type, size}` · 400(모양·base64) · 413(크기) · 415(이미지 아님) · 500(쓰기 실패) `{error}`. `GET /api/image?rel=` → `{rel, path, type, data(base64)}` · 400(rel) · 404. 둘 다 `X-HD-Token`. 본문 한도는 이 주소만 `BODY_MAX`(`router.BODY_MAX`, 나머지는 2 MB 그대로) |
| `modules/attach.js` | Model | `HD.attach` — check(종류·크기) · 칩 목록 add/done/remove/busy/saved/fromSaved(6장) · 요청 글 줄 lines/strip/withText. 머리 주석이 API |
| `modules/view-attach.js` | View · `HD.feature('attach', {needs: ['toast','esc','api']})` | `[data-hd-attach]` 상자의 붙여넣기·끌어 놓기·`[data-hd-attach-pick]`(클립 단추) → 저장 → `[data-hd-attach-slot]` 에 썸네일 칩(×). 상태 = 상자마다 칩 목록(WeakMap, 저장 안 함) · 저장된 이미지 미리보기 → `{items(host), set(host, saved)}` |

## 규칙

- 상자 주인(메모 창 `view-memo-pop` · 대화창 `view-chat` — 대화 패널 안 입력창도 같은 요소)과는 의도로만(상자에 bubbles CustomEvent): `hd-attach-get {items, busy, done}` · `hd-attach-set {items}`(빈 배열 = 비우기) · 이 기능이 내는 `hd-attach-changed {count, busy}`
- 요청 글 줄: 이미지마다 `첨부 이미지: <절대 경로>`(줄 머리 `attach_rules.LINE` = `HD.attach.LINE`), 글 끝에. 고쳐 저장해도 한 번만(strip 뒤 붙임). 요청문(`edits.request`)에서는 `요청:` 의 이어지는 줄로 들여 써진다 — 읽는 쪽은 `첨부 이미지: (.+)$` 로
- 메모는 `attach: [{path, rel, type, size, name}]` 칸을 지닌다 — 메모 창을 다시 열면 칩, 썸네일은 `GET /api/image`(점 폴더라 정적 경로로는 404). 대화창으로 보낸 메모도 같은 칸
- 올리는 중이면 보내기·추가를 막고 토스트(반쪽 경로를 보내지 않음). 보낸 뒤·창을 닫으면 칩을 비운다(파일은 남는다)
- 도우미 없음(file://): 붙여넣기·끌어 놓기·클립 단추 = 토스트 `이미지 첨부는 도우미로 열었을 때만 돼요 — …`, 칩 없음. 글 붙여넣기는 그대로(파일이 있을 때만 가로챔)
- 오류 탐지: 종류·크기·장 수 = 토스트(올리지 않음) · 서버 거절·못 닿음 = 그 칩만 빼고 토스트(서버 이유) · 미리보기 못 읽음 = `[hd]` 경고 + 빈 칩 · 칩 자리 없는 상자 = `[hd]` 경고 한 번

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `attach_rules.py` · `attach_store.py` · `router.py` `/api/image` | `unit`(test_canvas_unit_attach_py.py) + `-m slow -k attach` + `tests/protocol -k helper_protocol` |
| `modules/attach.js` | `unit`(test_canvas_unit_attach.py) |
| `view-attach.js` · 메모 창·대화창 첨부 | `unit or chat or notes --surface board,frame`(브라우저 test_canvas_attach.py) |
