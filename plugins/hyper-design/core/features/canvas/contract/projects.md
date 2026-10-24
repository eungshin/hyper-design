# 프로젝트 고르기 창 · 머리 홈 단추 (projects · view-projects · view-home)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(#246 view, task 24 → task 44 고르기 창·홈). 아래 탭 바는 `tabs.md`.

## 규칙

- 언제 보이나: 도우미로 열었을 때만(`ctx.api.on`). file:// 이거나 도우미가 없으면 단추·창·홈 단추를 만들지 않고 머리는 'hd' 표시 + 제목(셸이 `HD.projects.shown(manifest 제목, 폴더)` — manifest 제목, 옛 기본 문구 '전체 화면 한눈에 보기'·빈 값이면 out 폴더 이름(out 이면 그 위)). 페이지 제목도 같다. 템플릿에는 단추·창 줄이 없다 — View 가 mount 때 만든다
- 머리(`view-home`): 'hd' 표시 자리가 🏠 홈 단추(`#hhome`, 툴팁 '홈 — 모든 캔버스') → `GET /api/home` → `{url}` 로 이 탭이 간다. 제목(`#title`)·페이지 제목 = `GET /api/projects` 의 지금 줄 `title`(없으면 셸이 쓴 것 그대로 + `[hd]` 경고)
- 고르기 창(`view-projects`): 위쪽 줄 `창 ▾` 앞 `프로젝트`(`#pbtn`) 또는 탭 바 '+' → 대화 창 `#ppick`(`role=dialog`). 카드 차례: + 새 프로젝트 · 폴더 열기 · 최근 프로젝트(도우미가 준 차례, 휴지통 빼고). 카드 = 썸네일(42:26, `thumb` 없으면 빈 무늬) · 제목 · 열림 점 · `지금` · 언제(`HD.projects.ago`: 방금 전·N분 전·N시간 전·어제·MM-DD). 검색 = 제목·이름 대소문자 무시 부분 일치. 불러오는 동안 빈 카드 셋
- 카드 누르기 → `POST /api/open {name}` → 받은 url 로 이 탭이 간다(새 탭 없음 — 탭 바가 프로젝트 사이 이동을 맡는다). 지금 카드 = 창만 닫음. `없음`(out 폴더 없음) 카드는 회색 '폴더 없음', 누르면 까닭 토스트(요청 없음)
- 새 프로젝트 → 그 카드가 이름 칸이 됨(기본 `새 프로젝트 N` = 쓰지 않은 가장 작은 N, 전체 선택) → Enter·만들기 = `POST /api/new {title}`(공백 정리) → url 로 간다. Esc·취소 = 이름 칸만 거둠
- 폴더 열기 → `POST /api/pick-folder` → `{name}` 이면 `/api/open` 으로 이어서 연다 · `{cancel}` 조용히 · `{error}`·4xx/5xx 토스트
- '홈에서 모두 보기' → 의도 `hd-home`(받는 곳 = view-home, 없으면 토스트)
- 떠나기: 이 탭이 다른 주소로 갈 때 보내지 않은 상태 쓰기는 `view-state-sync` 의 pagehide keepalive PUT 이 마저 보내고 못 닿으면 쓰기 대기 표시(`hd-unsent:`)로 다음 시작 때 올린다 — 이 기능들은 따로 저장하지 않는다(`tests/test_canvas_tabs.py::test_leaving_by_tab_keeps_pending_state_write`)
- 실패: 목록을 못 받으면 창에 그 줄 + 토스트. 열기·만들기가 실패하면(4xx/5xx `{error}`·끊김) 도우미의 한 줄을 토스트로, 창은 열어 둔다. 기다리는 동안 그 카드 `aria-busy`, 한 번에 하나만. 모양이 틀린 목록 줄은 빼고 `[hd]` 경고 한 줄
- 층: `projects`(Model, 순수 — 줄 상태·제목·썸네일·지금 표시·언제 글·검색·새 이름·머리 제목) · `view-projects`(View — 창 그리기·`ctx.api` 부르기) · `view-home`(View — 홈 단추·제목). View 끼리는 문서 이벤트 의도로만 잇는다: `hd-home`(→ 홈) · `hd-pick-project`(→ 고르기 창) · `hd-project-title {name, title, current}`(→ 머리 제목). 받은 쪽은 `preventDefault()` 로 받음을 알리고 보낸 쪽은 아무도 안 받으면 토스트
- 등록: `HD.feature('projects', {needs: ['api', '$', 'esc', 'toast']})` → `{open, close}` | `{}` · `HD.feature('home', {needs: ['api', '$', 'toast']})` → `{home, title}` | `{}`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/projects.js` · `view-projects.js` · `view-home.js` · 도우미 `/api/projects`·`/api/open` | `unit or menu or helper`(`tests/test_canvas_unit_projects.py` · `tests/test_canvas_projects.py`) |
