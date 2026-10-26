# 받는 곳 · 에이전트 상태 · 새 터미널 (task 47-5b, 캔버스 쪽)

서버 쪽은 `presence.md`(47-5a), 모양은 `tests/protocol/presence.json` · `events.json`. `../contract.md` 의 책임 게이트(오류 탐지 포함)·테스트 층을 따른다.

## 모듈 (맡은 일 · 가진 상태 · 받는 ctx · 내보내는 것)
| 모듈 | 층 | |
|---|---|---|
| `agents.js` `menu` · `delivery` | Model | 받는 곳 메뉴 줄(접속한 에이전트 here 먼저 → Paseo 줄(같은 id 한 번) → 목록에 없는 지금 받는 곳 → empty) · 보낸 뒤 말(via paseo·event·claude = 받음). 상태 없음 |
| `presence.js` | Model | 접속 표 `{agents}` — `/api/presence` 답(`load`) + `agent.hello/away/progress`(`apply`, 바뀌지 않으면 같은 객체) → 칩 상태(`chip`: 접속 중 · 진행 글 · 자리 비움 · 표에 없음 = null) |
| `spawn.js` | Model | 새 터미널 확인 글(`ask`: 무엇 · Paseo · 폴더 = 저장소, 없으면 out) · 답 풀이(`answer`: 403 disabled = 꺼짐 설명 + `HD_ALLOW_SPAWN=1`, 다른 403·오류 = 한 줄) |
| `undo-answer.js` | Model | `/api/restore` 답 → done · already(`reverted:true` — 표시 `빌드 실패로 이미 되돌림`) · changed · error |
| `live.js` TYPES | Model | EventSource 가 `agent.*` · `request.sent` 도 듣는다(할 일 없음 — `hd-event` 로만) |
| `view-agents.js` | View | 메뉴 `#amenu` 를 `HD.agents.menu` 로 — 섹션 머리 · 접속 줄(`.ag-conn[data-state]`, 점 초록/회색, `접속 중 · Claude · <진행 글>`) · 목록에 없는 지금 받는 곳(`.ag-orphan`) · `받는 곳 없음` · `+ 새 터미널…`(`.ag-spawn` → 의도 `hd-spawn-ask {repo}`). 대화창 알약에서 열면 왼쪽 끝 맞춤·위로 |
| `view-presence.js` | View · `HD.feature('presence', {needs: ['api','$']})` | 접속 표(저장 안 함). `#aichip[data-state]`(점) + 칩 옆 `#aistate`(진행 글·접속 중·자리 비움). 이름 모르는 칩(`AI 연결됨`)이면 의도 `hd-agent {agent, name}` 로 칩 주인(view-sync)에게. 열 때·받는 곳 바뀔 때·실시간이 아닐 때 15초마다 `GET /api/presence` → `{state, refresh}` |
| `view-spawn.js` | View · `HD.feature('spawn', {needs: ['api','esc','toast']})` | 확인 창 `#hdspawn`(Claude/Codex · 폴더 · 그 뒤 일) — `[열기]` 뒤에만 `POST /api/agents/spawn {kind}`. 꺼짐 = 같은 창이 설명(닫기만), 성공 = 토스트, 그 밖 = 창 안 한 줄 + `[hd]`. 상태 = 열린 창 · 부르는 중 → `{ask, close}` |
| `view-chat.js` | View | 알약 점이 `#aichip[data-state]` 를 따른다(자리 비움 = 회색) · 알약 ⌄. 진행 줄 = `HD.chat.progress(p, ev, screens, ids)`: `request.sent`(이 요청 메모 id) → `보냄 · <이름> (실시간|Paseo|Claude)` / `보냄 · 대기열 — …` → `agent.progress` → `AI 작업 중 · <글>` → `agent.reply` → `답 옴 · <짧은 답>`. 예전 claim·AI 쓰기·release 줄 그대로 |
| `view-sync.js` | View | `/api/forward {text, notes:[메모 id ≤200]}` · 되돌리기 답 already = 토스트 + 기록 줄 표시(`op.bind`) |
| `view-history.js` | View | `op.bind(f)` — 줄 옆 표시 `.hn`(이번 세션만, 저장 안 함) |
| `view-send.js` `send`(`send.md`) | View | 보낸 뒤 말·덮개 종류를 `HD.agents.sentSay`·`delivery` 로(접속한 에이전트 = 'AI 수정 중', 대기열이라 하지 않음) |

받는 곳의 진실은 도우미 `Queue.agent`(POST `/api/attach`) 하나 — 접속한 에이전트를 골라도 같은 attach, 서버가 `adapters.choose` 로 이벤트·paseo·claude·대기열을 고른다. 캔버스는 `to` 를 보내지 않는다.

## 오류 탐지
- `/api/presence` 실패·옛 도우미(404) = `[hd]` 경고 한 번, 칩은 상태 없이(지금 모양). 모양 틀린 줄 = `[hd]` 경고 + 뺌
- 새 터미널 받는 기능이 없으면(view-spawn 안 붙음) `[hd]` + 토스트. 부르기 실패 = 창 안 한 줄 + `[hd]`
- 테스트는 실제 Paseo·Claude 에 보내지 않고 아무것도 띄우지 않는다(에이전트 = 테스트의 HTTP hello/progress/reply, Paseo = 없는 경로, `HD_ALLOW_SPAWN` 지움, `HD_HOME` = 임시)

## 고치면 돌릴 것
| 고친 곳 | `-m` |
|---|---|
| 위 Model(`tests/test_canvas_unit_receivers.py`) | `unit` |
| View · `view-send`(브라우저 `tests/test_canvas_receivers.py` — 영역 chat, 이웃 board) | `unit or chat or helper --surface board` |
