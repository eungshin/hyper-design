# 프로젝트 메뉴 (projects · view-projects)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(#246 view, task 24).

## 규칙

- 무엇을 보이나: 위쪽 줄 `창 ▾` 앞에 `프로젝트 ▾`(`#pbtn`) — 누르면 메뉴(`#pmenu`)에 저장한 캔버스 줄마다 이름 · 상태(열림 = 떠 있는 도우미의 주소가 있음 / 꺼짐 / 없음 = out 폴더가 없음) · 연 때(`MM-DD HH:MM`). 차례는 도우미가 준 그대로(최근 연 것부터). 지금 캔버스 줄은 `지금`(`aria-current`, out 경로를 `hd_projects.key` 와 같은 규칙으로 `window.__hdOut` 과 비교). `없음` 줄은 못 누르고(`disabled`) 까닭(`hd forget <이름>`)을 적는다
- 언제 보이나: 도우미로 열었을 때만(`ctx.api.on`). file:// 이거나 도우미가 없으면 단추·메뉴를 만들지 않고 다른 것은 그대로. 템플릿에는 줄이 없다 — 단추·메뉴는 View 가 mount 때 만든다
- 부르는 라우트(도우미, `X-HD-Token` — `ctx.api.call`): 메뉴를 열 때마다 `GET /api/projects` → `[{name, out, state, url, pid, last_opened}]` · 줄 누르기 → `POST /api/open {name}` → `{url, …}` → 그 url 을 새 탭에(누른 순간 빈 탭을 열고 답이 오면 주소를 보낸다 — 팝업 차단 피하기). 성공하면 메뉴를 닫는다
- 실패: 목록을 못 받으면 메뉴에 그 줄 + 토스트. 열기가 실패하면(4xx/5xx `{error}`·연결 끊김) 열어 둔 빈 탭을 닫고 도우미의 한 줄을 토스트로, 메뉴는 열어 둔다. 기다리는 동안 그 줄 `aria-busy`·`여는 중…`, 한 번에 하나만. 모양이 틀린 목록 줄은 빼고 `[hd]` 경고 한 줄. 새 탭이 막히면 주소를 토스트로
- 층: `projects`(Model, 순수 — 줄 상태·지금 표시·연 때 글·누를 수 있는지) · `view-projects`(View — 그리기·`ctx.api` 부르기만). 상태 = 열린 메뉴·여는 중인 이름(이 View 만). 등록 `HD.feature('projects', {needs: ['api', '$', 'esc', 'toast']})` → `{open, close}` | `{}`(도우미 없음)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/projects.js` · `view-projects.js` · 도우미 `/api/projects`·`/api/open` | `unit or menu or helper`(`tests/test_canvas_unit_projects.py` · `tests/test_canvas_projects.py`) |
