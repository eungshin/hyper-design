# 프로젝트 탭 바 (tabs · view-tabs)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(task 44, Xmind 시트 바 모양 — 탭 하나 = 프로젝트 하나).

## 규칙

- 언제 보이나: 도우미로 열었을 때만(`ctx.api.on`), 탭이 하나라도 있을 때. 판(`#screens`) 아래 왼쪽(판 왼쪽 끝 + 12px, S1b)에 떠 있고 가운데 대화창(`#hdchat`, 보일 때만)의 왼쪽 끝 앞 12px(없으면 판 오른쪽 끝 앞)까지 넓어진다. 최소 160px, 넘치면 ◀ ▶(`HD.tabs.place` — 창 크기·도크 폭·대화창 크기·보이기·글꼴이 바뀌면 다시). 다 보이는 데 드는 폭을 `data-need` 로 남겨 대화창이 폭을 줄여 준다(`chat.md`). 크게 보기(`modal-open`)·`bare` 때는 숨김. 바가 있으면 토스트를 그 위로 올린다(`body.has-ptabs`)
- 탭 = `GET /api/tabs` 의 이름 차례(모르는·휴지통·겹친 이름은 빼고 `[hd]` 경고) + 지금 프로젝트(없으면 끝에 더하고 `PUT /api/tabs` 로 남김). 제목 = `/api/projects` 의 `title`(처음은 페이지에 한 번 받은 `HD.projectList.get`, `reload()` 는 `fresh`). 지금 탭 = `aria-selected`. 지금 캔버스가 목록에 없으면 더하지 않는다
- 누르기(다른 탭) → `POST /api/open {name}` → 받은 url 로 이 탭이 간다. `없음` 탭은 까닭 토스트. '+' → 의도 `hd-pick-project`(고르기 창)
- 두 번 누르기(지금 탭 — 다른 탭은 한 번 누르면 이미 떠난다, ▾ 메뉴로 바꾼다)·F2 → 제자리 이름 칸(전체 선택). Enter·blur 확정, Esc 취소. `HD.tabs.rename`: 공백 정리, 빈 값·같은 값은 무시(요청 없음), 80자에서 자름 → `POST /api/project {name, title}` → 지금 탭이면 의도 `hd-project-title`(머리·페이지 제목). 실패 = 되돌리고 토스트
- 끌기(4px 넘게) → 끼울 자리 표시 → 놓으면 `HD.tabs.move` → `PUT /api/tabs`(실패 = 되돌리고 토스트). 이름 바꾸는 중엔 끌지 않는다. 끌기는 열기가 아니다
- 우클릭·탭의 ▾·Shift+F10 → 메뉴(`#ptmenu`): 이름 바꾸기 · 탭 닫기 · 다른 탭 닫기(둘 다 탭이 하나뿐이면 끔) · 폴더 열기(`POST /api/reveal {name}`) · 홈(의도 `hd-home`). 닫기는 바에서만 뺀다(프로젝트는 그대로) — 지금 탭을 닫으면 저장한 뒤 오른쪽(없으면 왼쪽) 탭으로 간다. 다른 탭만 남기면 그 탭으로 간다
- 넘치면 스크롤바 없이 ◀ ▶(넘칠 때만 보임, 끝이면 그쪽 끔), 시작 때 지금 탭이 보이게 민다. Ctrl+Shift+[ / ] = 이전/다음 탭(끝에서 돌아감, 입력 중이면 아님)
- 떠나기: 보내지 않은 상태 쓰기는 `view-state-sync` 의 pagehide 길이 마저 보낸다(`projects.md` 와 같음)
- 층: `tabs`(Model, 순수 — bar·close·others·move·slot·rename·step·arrows·place) · `view-tabs`(View — 그리기·끌기·메뉴·`ctx.api`). 상태 = 탭 이름 차례·제목·여는 중·이름 바꾸는 중·끄는 중(이 View 만, 진실 원천은 도우미의 `tabs.json`). 등록 `HD.feature('tabs', {needs: ['api', '$', 'esc', 'toast']})` → `{reload, names}` | `{}`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/tabs.js` · `view-tabs.js` · 도우미 `/api/tabs` | `unit or menu or helper`(`tests/test_canvas_unit_tabs.py` · `tests/test_canvas_tabs.py`) |
