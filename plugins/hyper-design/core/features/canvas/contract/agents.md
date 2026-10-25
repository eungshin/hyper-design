# 보낼 곳 고르기 (agents · view-agents, #214)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(task 36).

## 규칙

- 무엇을 보이나: 위쪽 줄 보낼 곳 칩 `#aichip`(view-sync 가 그림: `AI 연결됨 · <이름>` / `받는 곳 없음`)과 옆 `▾`(`#aibtn`, 이 기능이 만듦). 칩이나 ▾ 를 누르면 메뉴 `#amenu` — 줄마다 이름(40자, 넘으면 …) · 폴더 이름 · 상태 점(running = 초록), 지금 보낼 곳은 ✓(`aria-checked`), 마지막 줄 `받는 곳 없음(대기열 파일만)`. 닫힌(closed)·보관된 에이전트는 없다
- 줄 차례(`HD.agents.rank`, Model): 에이전트 `cwd` 가 이 캔버스의 저장소(같거나 그 아래 폴더) 먼저 → running · idle · 그 밖 → 이름. 저장소 = 도우미가 준 `repo`(앱 프로젝트면 `app.json` 의 `repo`, 아니면 out 위로 처음 `.git` 이 있는 폴더)
- 고르기: `POST /api/attach {agent: id|null}`(기존 라우트) → 성공하면 칩에 의도 `hd-agent {agent, name}` 를 보내고 view-sync 가 칩과 `window.__hdAgent`(셸의 보내기 알림이 읽음)를 고친다. 실패하면 도우미의 한국어 까닭을 토스트, 칩·보낼 곳 그대로
- 자동: 캔버스를 열 때 보낼 곳이 없고(`__hdAgent` 도 도우미 `current` 도 없음) `GET /api/agents?auto=1`(이미 붙어 있거나 저장소를 모르면 도우미가 paseo 를 띄우지 않고 `skipped:true`) → `HD.agents.suggest` 가 하나(이 저장소에서 running 인 것이 정확히 하나)를 찾으면 붙이고 토스트 `보내기 → <이름> (바꾸려면 칩을 누르세요)`. 붙어 있는 것은 바꾸지 않는다. 사용자가 이 캔버스에서 `받는 곳 없음` 을 고르면 자동을 끈다(전역 설정 키 `hd-agent-off:<프로젝트 해시>` = `'1'`, 에이전트를 고르면 지움)
- 도우미 `GET /api/agents`(`X-HD-Token`) → `{agents:[{id, name, status, cwd, provider}], current, repo, error?}` — `paseo ls -g --json`(읽기만)을 바이트로 받아 UTF-8 로 푼다(한글 이름), 보관된 것 뺌, 5초 캐시. Paseo 가 없으면 200 `{agents:[], error:'Paseo 를 찾을 수 없어요'}` → 메뉴에 그 글. 보내기 자체는 그대로(`/api/forward` → `paseo send <id> --prompt-file … --no-wait`)
- 다른 자리의 칩(S1b 하단 대화창 받는 곳 칩): document 의도 `hd-agent-pick {anchor}` → 같은 메뉴를 그 칩 옆에(아래 자리가 모자라면 위로) 열고 `detail.done = true`. 같은 칩을 다시 누르면 닫는다. 열린 메뉴의 기준 칩에 `aria-expanded`
- 언제 보이나: 도우미로 열었을 때만(`ctx.api.on`). 아니면 아무것도 만들지 않는다. 템플릿에는 줄이 없다
- 층: `agents`(Model, 순수 — 줄·차례·제안·이름 자르기) · `view-agents`(View — 메뉴·`ctx.api` 부르기·자동). 상태 = 열린 메뉴·고르는 중·자동 끔 키(이 View 만). 보낼 곳의 주인은 도우미 `srv.agent` 하나, 캔버스 쪽 사본 `window.__hdAgent` 는 view-sync 가 고친다. 등록 `HD.feature('agents', {needs: ['api', '$', 'esc', 'toast', 'local', 'key']})` → `{open, close, auto() → Promise}` | `{}`(도우미 없음)
- 테스트는 가짜 paseo(`ls` = 한글 JSON, `send` = 로그)만 쓴다 — 실제 에이전트에 보내지 않는다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/agents.js` · `view-agents.js` · 도우미 `/api/agents` · view-sync 칩 | `unit or helper`(`tests/test_canvas_unit_agents.py` · `tests/test_canvas_agents.py`) + `hd/tests` |
