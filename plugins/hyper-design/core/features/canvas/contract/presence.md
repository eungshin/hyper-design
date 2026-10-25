# presence — 접속한 에이전트 · 받는 곳 고르기 (서버, task 47-5a)

계약(모양·임대·보내기·새 에이전트 열기) = `tests/protocol/presence.json`, 이벤트 모양 = `tests/protocol/events.json` 의 `agent.*` · `request.sent`. 여기는 구조만. `../contract.md` 의 책임 게이트(오류 탐지 포함)를 따른다.

## 객체 (층 · 맡은 일 · 가진 상태)
| 파일 | 층 | 객체 | 맡은 일 | 상태 |
|---|---|---|---|---|
| `presence.py` | Model(순수 규칙) + 상태 주인 | `check_hello` · `lease_of` · `beat_of` · `check_progress` · `sweep_plan` · `public` / `AgentPresence` | hello(임대 1–300초, 기본 30) · beat · bye · progress · list · sweep(임대 끝 = away, 한 시간 지난 away = 잊음) | 에이전트 표(id → 항목) 하나 — 자물쇠 하나, 시계·알림은 받음 |
| `adapters.py` | Model(`choose` · `config_from_env`) + Client 어댑터 | `NoneAdapter` · `PaseoAdapter` · `ClaudeCliAdapter` · `PaseoSpawner` | 접속 안 한(이벤트를 읽지 않는) 에이전트에게 넘기기 · 새 터미널 에이전트 열기 | 없음(찾는 법·켜짐만) |
| `memo_archive.py` | Model(순수) | `pick` · `without` | 완료 메모 보관 고르기 — `modules/archive.js` 와 같은 규칙 | 없음 |
| `session.py` | Service | `Queue.send` · `Archive.sweep` · `Ticker` · `ProjectSession.spawn` | 대기열 파일 + 받는 곳 고르기 + `request.sent` · 서버 쪽 보관 · 세션 시계(1초 presence.sweep, 한 시간 Archive.sweep) | Queue = 붙은 agent · 어댑터 표 |
| `router.py` | Controller | ROUTES | `/hello` `/beat` `/bye` `/progress` `GET /agents` `/agents/spawn` + 옛 뿌리 `/api/…` 별칭(`GET /api/presence`) · `/api/forward` = `Queue.send` | 없음 |

## 받는 곳 고르기(`adapters.choose`, 순수)
받는 곳 = 본문 `to`, 없으면 붙은 에이전트(`POST /api/attach`).
1. 접속 중(here)이고 `listen` = **event**: `request.sent {to, via:'event', notes, text, path}` — 에이전트는 SDK `Project.requests()` 로 받는다. 터미널이 필요 없다
2. kind claude 이고 hello 에 `session` 이 있고 `HD_CLAUDE_WAKE=1` = **claude**: `claude -p --resume <session>`(표준 입력 = 대기열 파일, 출력 = `<stamp>.claude.log`, 창 없음, 기다리지 않음)
3. 모르는 id(오늘의 Paseo id) 또는 kind paseo, Paseo CLI 가 있으면 = **paseo**: `paseo send <id> --prompt-file … --no-wait`(오늘 동작 그대로)
4. 그 밖 = **queue**(대기열 파일만). 어댑터가 실패해도 queue(`[hd]` 한 줄)

대기열 파일은 늘 쓴다(기록). `.sent` 표시는 어댑터(paseo · claude)가 받았을 때만. 모든 보내기는 `request.sent` 를 낸다(via 와 함께 — 캔버스 칩이 어디로 갔는지 보인다).

## 켜짐(모두 기본 꺼짐 — 환경, 세션을 만들 때 읽음 `adapters.config_from_env`)
- `HD_CLAUDE_WAKE=1` — ClaudeCliAdapter 사용. 꺼져 있으면 kind claude 인 away 에이전트에게는 queue
- `HD_ALLOW_SPAWN=1` — `POST /agents/spawn {kind: claude|codex}` = `paseo run --no-wait --json --provider <kind> --cwd <저장소> --title "hd · <프로젝트>" <안내 글>`. 꺼져 있으면 403 `{reason:'disabled'}`. 실제 에이전트를 만드는 밖으로 나가는 일 — 캔버스(47-5b)는 사용자에게 먼저 묻는다
- `HD_CLAUDE_CMD` — claude 실행 파일(테스트의 가짜). Paseo 는 기존 `HD_PASEO_CMD`

## 오류 탐지
- 본문 검사는 순수 규칙(`check_hello` · `check_progress` · `session.check_send`)이 한국어 한 줄로 400. 모르는 id = 404 `reason:'unknown'`(SDK 는 hello 를 다시 보낸다)
- 세션 시계의 일 하나가 실패해도 `[hd]` 한 줄 뒤 다음 일은 계속(`Ticker.step`)
- 자식 프로세스는 모두 `creationflags=NO_WINDOW` — `hd/tests/test_hd_no_window.py` 의 저장소 전체 지킴이가 canvas·hd·home 의 모든 `subprocess.run/Popen/…` 를 본다

## 그 밖(47-5a 에서 같이)
- 뒤 빌드가 깨져 되돌린 async 쓰기의 기록 = 묘비 `.hd-history/<stamp>/reverted.json {ids, reason}` → 그 stamp `POST /api/restore` = 200 `{reverted:true, restored:[], changed:[]}`(캔버스 되돌리기 줄이 '되돌릴 기록이 없어요' 대신 아무 일 없음)
- 완료 메모 보관을 서버도 한다(`Archive.sweep`, 세션을 연 뒤 바로와 한 시간마다) — 캔버스 탭이 없거나 조용해도. 캔버스 탭의 보관과 겹쳐도 보관 파일은 id 로 한 줄, 캔버스는 `notes.changed` 로 다시 읽는다

## 고치면 돌릴 것
`pytest tests/test_canvas_unit_presence.py tests/test_canvas_unit_session_upkeep.py`(unit) + `pytest tests/protocol`(test_protocol_presence.py, slow) + `hd/tests -k "presence or no_window"`
