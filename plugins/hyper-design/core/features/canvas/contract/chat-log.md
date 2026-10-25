# 대화 패널 (chat-log · view-chat-log · 서버 chat_log/ChatLog, S3)

`../contract.md` 의 책임 게이트(오류 탐지 포함)·테스트 층을 따른다. 근거: `tasks/50-stitch/FINDINGS.md` 1-C(Agent log)·4(S2·S3)·8, `tasks/PLAN-2026-10-25.md` Wave 4.

## 모듈 (맡은 일 · 가진 상태 · 받는 것 · 내보내는 것)

| 모듈 | 층 | |
|---|---|---|
| `chat_log.py` | Model(순수) | 기록 한 줄 모양(`from_event` · `check_post` · `reply_text`) · 턴 붙이기(`assign`, 상태 = 다음 seq · 메모 → 턴 · 마지막 턴·시각) · 한도(`over` · `trim`, 500 턴 + 50) · 읽기(`parse_lines` · `since` · `parse_since`). 상태 없음 |
| `chat_store.py` `ChatLog` | Service | `<out>/.hd-chat.jsonl` 덧붙이기(자기 자물쇠) · 한도 넘으면 오래된 턴 → `.hd-chat-archive.jsonl` + 남은 것 임시 파일·`os.replace` · `tap(ev)` = `EventBus.taps`(구독자보다 먼저 — 이벤트를 받은 탭이 바로 읽어도 있다) · `post` · `get` |
| `events.py` `EventBus.taps` | Model | publish 안에서 구독자보다 먼저 부르는 함수들. 탭이 던지면 `[hd]` 한 줄, 알림은 나간다 |
| `router.py` | Controller | `GET /api/chat?since=` → `{seq, records[, reset]}`(since 정수 아님 = 400) · `POST /api/chat` ask/undone(틀림 400, 모르는 턴 404) |
| `modules/chat-log.js` | Model | 기록 → 턴·상태·줄·닿은 화면·되돌릴 stamp, 자동 스크롤, 터미널 대화 섞기(`HD.chatLog`, 머리 주석이 API) |
| `modules/view-chat-log.js` | View · `HD.feature('chatLog', {needs: ['$','toast','esc','api','reload','cardEl']})` | `#pTalk` 그리기 · 기록 읽기 · ask/undone 남기기 · 턴 누르기 · 되돌리기 · 입력창 자리 의도. 상태 = 받은 기록·seq·터미널 줄·펼친 도구 줄(저장 안 함) → `{refresh, records, shown}` |
| 셸 | — | `#ldock`(왼쪽 도크 자리) · `#pTalk` · 도크 아이콘 `talk` · `--dockl` · ctx `focus(ids)`(= `fitCards(ids, z)` — 지금보다 크게는 안 함) |

## 규칙

- 기록 = 서버가 이미 내는 이벤트에서: `request.sent` → sent · `agent.progress` → progress(터미널에서 에이전트가 알린 줄) · `agent.reply`(S3 에서 `text` 칸 더함) → reply(칸 `rkind` = 답 종류 — 기록 `kind` 와 겹치지 않게) · `ai.write`(act record) → write(stamp) · `build.done` → built · `build.failed` → failed. 캔버스가 남기는 것: ask(대화창 의도 `hd-chat-sent` — 보낸 글·칩·화면·받는 곳 이름) · undone(턴 되돌림 성공)
- 턴 붙이기: ask·sent = 메모 id 가 겹치는 턴 · reply = 그 메모 턴(모르면 마지막) · progress·write = 마지막 턴 · built = 마지막 턴이 10분 안에 움직였을 때만(아니면 버림 — 사람 편집 빌드가 지난 턴에 붙지 않게, built 는 시간을 늘리지 않음) · failed = 열린 마지막 턴, 아니면 새 턴 · 옛 턴에 늦게 온 답은 마지막 턴을 되돌리지 않는다
- 턴 상태(View 표시): 작업 중(회전 1s) · 대기 중(via queue, 진행 없음) · 끝 ✓(답 · 다음 턴이 옴 · 10분 조용함) · 결정 필요 · 실패(빨간 줄 뒤 쓰기·빌드·답 없음) · 되돌림. built 줄은 그 턴에 AI 쓰기가 앞설 때만
- 턴 누르기 = 닿은 카드 `.tk-hl` 1.8초 + 판을 그 카드들로(크게는 안 함). 닿은 카드가 판에 없으면 토스트
- [되돌리기] = 끝난 턴의 AI 쓰기 stamp 를 새것부터 `POST /api/restore {stamp, keep, notify}`(48c `HD.aiUndo.body/outcome` 그대로) — 하나라도 거절되면 그 이유 토스트로 멈춤, 되살린 카드는 `ctx.reload`. 다 되면 `POST /api/chat undone`
- 읽기: 처음 · `hd-event`(request.sent · agent.* · ai.write · build.* · notes.changed) 80ms 뒤 · 패널이 보이는 동안 4초마다(숨은 탭 건너뜀). 맨 아래를 보고 있으면 새 줄을 따라가고, 올려 읽는 중이면 그대로(24px)
- 입력창 자리: 패널이 보이면(왼쪽·오른쪽·떠 있는 창 — `#pTalk` 에 자리가 있음, ResizeObserver) 의도 `hd-composer {host}` → view-chat 이 같은 `#hdchat` 을 패널 아래로(`.docked`, 상태 줄·⌄ 감춤). 안 보이면 `{host:null}` = 판 아래. 창 메뉴: `대화` = 패널 켜고 끄기 · `대화창` = 판 아래 떠 있는 입력창 설정 — 패널이 보이면 꺼진 줄(입력창은 늘 패널에)
- 터미널 대화(S3b 계약, 공급자 모름): 받는 곳(`window.__hdAgent`)이 있으면 `GET /api/agents/transcript?agent=&since=<cursor>` → `{entries:[{id, role:'user'|'assistant'|'tool', text, at}], cursor, source}` + 이벤트 `agent.transcript {agent, entries}`. 턴과 `at` 차례로 섞음 · user = '터미널에서' 오른쪽 말풍선 · tool = 회색 '도구 · <짧게>'(펼침, 다시 그려도 펼친 채) · 캔버스 요청이 터미널에도 찍히면(요청 글 또는 요청문 앞 80자가 들어 있음) 한 번만. 404·깨진 답·source none = 조용한 한 줄 `이 터미널의 대화는 가져올 수 없어요`
- 움직임(§8): 새 줄 맥박 600ms(scale 1→1.02→1, 처음 그림은 없음) · 패널 나타남 400ms `cubic-bezier(0.34,0.88,0.34,1)` fade+6px · 회전 1s linear — `prefers-reduced-motion` 이면 모두 끔
- 오류 탐지: `#pTalk` 없음 = `[hd]` + 기능 빠짐 · `/api/chat` 404(옛 도우미)·깨진 답·못 닿음 = `[hd]` 한 번(기록 없이) · ask/undone 기록 실패 = `[hd]` · view-chat 이 `hd-composer` 를 받지 않음 = `[hd]` · ctx.focus 없음 = `[hd]` + 강조만 · 되돌리기 실패 = 토스트. 서버: 깨진 줄 건너뜀 + `[hd]` · 쓰기 실패 `[hd]`(메모리 기록은 남음) · 보관 실패 = 그대로 두고 `[hd]`. 도우미 없음(file://) = 대화 패널은 이 페이지에 없다(view-dock `absent` — 그리지 않고 창 메뉴 줄은 꺼짐, 저장 배치는 그대로), 입력창은 판 아래 그대로
- S3b 가 붙는 자리: `session.py` `ProjectSession.__init__` 의 `# ── S3b 자리` 주석(펌프 — `agent.transcript` publish, 시계 일이면 Ticker) · `router.py` ROUTES GET 의 `# ── S3b 자리` 줄(`/api/agents/transcript`). `agent.transcript` 는 이미 `events.TYPES` · `live.js` TYPES 에 있다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `chat_log.py` · `chat_store.py` `ChatLog` · `router.py` `/api/chat` · `events.py` taps | `unit`(test_canvas_unit_chat_log_py.py — ChatLog 파일은 `-m slow -k chatlog`) + `unit or helper` |
| `modules/chat-log.js` | `unit`(test_canvas_unit_chat_log.py) |
| `view-chat-log.js` · 셸 `#pTalk`·`#ldock`·`focus` · view-chat `hd-composer` | `unit or chat or dock or helper --surface board`(브라우저 test_canvas_chat_log.py) |
