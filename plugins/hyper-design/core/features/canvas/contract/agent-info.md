# 받는 터미널 정보 · 진짜 이미지 보내기 (agent-info · view-agent-info · 서버 agent_meta/agent_info, R28 시안 A)

`../contract.md` 의 책임 게이트(오류 탐지 포함)·테스트 층을 따른다. 근거: `tasks/paseo-composer-insight-2026-10-27.md`(Paseo 컴포저가 이미지·모델·생각 깊이·컨텍스트를 어떻게 다루는지).

## 모듈 (맡은 일 · 가진 상태 · 받는 것 · 내보내는 것)

| 모듈 | 층 | |
|---|---|---|
| `agent_meta.py` | Model(순수) | 모델 표 `MODELS`(Paseo model-manifest 와 같은 이름·최대 토큰, 모르면 `[1m]` = 1M · 그 밖 `DEFAULT_MAX` 200k) · usage 합(input + cache_creation + cache_read + output) · jsonl 꼬리의 마지막 usage(옆 대화·`<synthetic>` 빼고) · `context` {used, max, pct(반올림, 0..100)} \| None · 생각 깊이 선택지(`paseo provider models` 줄 → 그 모델 것, 없으면 `DEFAULT_EFFORTS`) · `check_effort` · 답 모양 `info` · paseo 인자 `send_argv`(이미지마다 `--image`) · `update_argv`. 상태 없음 |
| `agent_info.py` `AgentInfo` | Edge | 붙은 받는 곳(`Queue.agent`) 하나만: `paseo ls -g --json`(Queue 5초 캐시) · 선택지(`paseo provider models <p> --thinking --json`, 300초 캐시) · `<PASEO_HOME|~/.paseo>/agents/*/<id>.json` 의 `runtimeInfo.sessionId`·`cwd`(30초 캐시) → Claude 세션 jsonl 끝 512 KB(`transcripts.ClaudeTranscript.locate`, 에이전트 폴더 안만). effort 바꾸기 = `PaseoAdapter.update_thinking` 뒤 ls 캐시 비움 |
| `adapters.PaseoAdapter` | Client 어댑터 | `send(path, text, target, images)` = `paseo send <id> --prompt-file <f> [--image <abs>]… --no-wait` · `update_thinking(id, opt)` = `paseo agent update <id> --thinking <opt>` · `read_json(rest)`(읽기만). 다른 어댑터는 images 를 받고 쓰지 않는다(claude -p 는 글의 경로 줄로) |
| `send_queue.Queue.images` | Edge | 보낼 이미지 = 본문 `images`(있으면) 또는 글의 `첨부 이미지:` 줄(`attach_rules.paths_in`) → `<out>/.hd-attach` 바로 안 · 규칙 이름 · 있는 파일 · 6장까지(`attach_rules.pick_images`). 뺀 것은 `[hd]` 한 줄 |
| `router.py` | Controller | `GET /api/agents/info` · `POST /api/agents/effort {effort}` (둘 다 `X-HD-Token`) |
| `modules/agent-info.js` | Model | `HD.agentInfo` — 답 읽기 `parse`(틀린 컨텍스트 = null) · `short`(340k · 1M) · `tip` · `ring` · `effortLabel` · `menu` · `same`. 머리 주석이 API |
| `modules/view-agent-info.js` | View · `HD.feature('agentInfo', {needs: ['api','toast','esc']})` | 대화창 도구 줄 칸 `[data-hd-agent-info]`(view-chat 이 칸만 둔다)을 채움: 모델 이름(보기만) · 생각 깊이 알약 + 메뉴 · 컨텍스트 고리 + %. 상태 = 마지막 정보 · 열린 메뉴 · 바꾸는 중(저장 안 함) → `{refresh, info}` |

## 규칙

- 답 `GET /api/agents/info`: 받는 곳 없음 `{agent:null, paseo:false}` · Paseo 목록에 없음(접속만 한 에이전트 등) `{agent, paseo:false}` · 그 밖 `{agent, paseo:true, name, provider, model, modelLabel, effort(thinking, 'auto'·없음 = null → 알약 '자동'), effortOptions, context:{used,max,pct}|null}`. context 는 provider claude 이고 세션 기록의 usage 를 읽었을 때만 — 모르면 null 이고 고리를 숨긴다(0% 로 보이지 않는다)
- `POST /api/agents/effort {effort}`: 받는 곳이 Paseo 에이전트가 아님 409 · 선택지 밖·모양 틀림 400(paseo 를 부르지 않음) · Paseo 거절 502 `{error: '생각 깊이를 바꾸지 못했어요 — <까닭>'}` · 성공 = 새 정보(GET 과 같은 모양)
- 모델 바꾸기는 없다(Paseo CLI 에 길이 없음 — 툴팁 `모델은 Paseo에서 바꿔요`)
- 모양(시안 A, R27 위계 — 내용이 먼저, 메타는 조용히): 받는 곳 알약 뒤에 12px #6b6b66 — 칩 아이콘 + 모델 이름 · 테 1px 알약 `🧠 medium ⌄`(메뉴 = 위로 열림, 머리 '생각 깊이 (effort)', 지금 것 `지금`) · 16px 고리 + 11px `34%`(80% 넘으면 주황). 툴팁 = 검은 작은 상자(모델 · 고리 `컨텍스트 340k / 1M 토큰 · 34% 사용`). 도구 줄이 440px 이하(탭 바에 자리를 준 360px · 대화 패널 안)이면 모델 글은 감추고 아이콘만(툴팁 앞에 이름)
- 받는 곳이 Paseo 가 아니면 줄째 숨김. 다시 읽기: 열 때 · `hd-agent`(받는 곳 바뀜, 잡는 단계) · 15초마다(창이 숨었으면 건너뜀)
- 진짜 이미지(시안 A ①): 캔버스 `/api/forward` 본문에 `images` = 요청문의 `첨부 이미지:` 경로(`HD.attach.paths`, view-sync). 받는 곳이 paseo 면 `--image` 로 넘기고, 글의 경로 줄은 그대로(대기열·claude·이벤트 받는 곳과 기록이 경로를 본다)
- 오류 탐지: 칸 없음·옛 도우미(404)·못 닿음·모양 틀림 = `[hd]` 경고 한 번 + 숨김 · 바꾸기 실패 = 서버 까닭 토스트 + 알약 그대로 · 서버: 기록 파일·세션을 못 읽음 = context null + `[hd]` 한 줄(같은 까닭은 한 번) · 선택지를 못 읽음 = 기본 선택지 + `[hd]` 한 줄
- 테스트는 실제 Paseo 에이전트에 보내거나 바꾸지 않는다: 서버 = 가짜 run·가짜 Queue/어댑터, 브라우저 = `/api/agents/*` 가로채기 + 없는 paseo 경로

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `agent_meta.py` · `attach_rules.paths_in/pick_images` · `adapters.PaseoAdapter` · `send_queue.Queue.images` | `unit`(test_canvas_unit_agent_meta.py) + `-m slow -k agent_meta` + `tests/protocol -k helper_protocol` |
| `modules/agent-info.js` · `attach.js` `paths` | `unit`(test_canvas_unit_agent_info.py) |
| `view-agent-info.js` · 대화창 칸 · view-sync `images` | `unit or chat`(브라우저 test_canvas_agent_info.py) |
