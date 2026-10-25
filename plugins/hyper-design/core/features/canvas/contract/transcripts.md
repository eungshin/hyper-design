# transcripts — 고른 터미널의 대화 기록을 대화 패널로 (서버, S3b)

터미널 창을 오가지 않게: 고르거나 붙인 터미널(에이전트)에게 한 말과 그 답·도구 부르기를 캔버스 대화 패널(S3)이 시간 차례로 보인다. 여기는 서버 쪽 모양과 구조만. `../contract.md` 의 책임 게이트(오류 탐지 포함)를 따른다.

## 모양 (S3 가 그대로 그린다)
- 줄 `entry = {id, role: 'user'|'assistant'|'tool', text, at}` — id 는 바뀌지 않는다(Claude = 줄 uuid + `:블록 번호`, uuid 가 없으면 `c<바이트 자리>:n` · Paseo = 항목 id, 없으면 시각·역할·글 해시). tool 의 text = 한 줄 요약(`Edit screens/home.html` · `Bash <설명>`). at = ISO-8601(모르면 `''`)
- `read(since) → (entries, cursor)` — cursor 는 불투명 글. 같은 cursor 로 다시 부르면 새 줄만. since 없음 = 처음부터, `'end'` = 줄 없이 지금 끝
- 이벤트 `agent.transcript {agent, entries}` — 펌프가 지켜보기 시작한 뒤 생긴 새 줄만(지난 기록은 HTTP)
- `GET /api/agents/transcript?agent=<id>&since=<cursor>` → `{entries, cursor, source: 'claude'|'paseo'|'none', error?}` — 한 번에 100줄까지, 빈 목록이 올 때까지 이어 부르면 끝까지. 이벤트와 HTTP 가 겹칠 수 있다 — 받는 쪽은 id 로 한 번만 그린다

## 객체 (층 · 맡은 일 · 상태)
| 파일 | 층 | 객체 | 맡은 일 | 상태 |
|---|---|---|---|---|
| `transcript_parse.py` | Model(순수) | `parse_claude` · `claude_entries` · `parse_paseo` · `tool_summary` · `cap` · 커서 글 | 형식마다 바이트·글 → entries. 덜 쓴 마지막 줄은 먹지 않음 · 깨진 줄 건너뜀 · 글 4000자 · 도구 120자 · 100줄/번 | 없음 |
| `transcripts.py` | Client 어댑터 | `TranscriptSource`(kind · every · read) · `ClaudeTranscript` · `PaseoTranscript` · `NoTranscript` · `source_for` · `REGISTRY` | 파일(지난 바이트 자리부터 1 MB 씩) · `paseo logs <id> --json`(읽기만, NO_WINDOW) | 찾은 파일 경로 하나 |
| `transcript_pump.py` | Service | `TranscriptPump` · `pump_for(session)` | 지켜보는 에이전트마다 읽어 이벤트로 · HTTP 지난 기록 | 지켜보는 표(id → 소스·커서·마지막 오류) — 자물쇠 하나 |

의존: 펌프 → `TranscriptSource` 인터페이스 + 넣어 준 factory(구현을 모른다) · 소스 → 순수 파서. 새 도구 = 구현 클래스 하나 + `REGISTRY` 한 줄.

## 고르기 (`source_for`, `kind_of`)
- kind claude + hello 의 `session` → `ClaudeTranscript`(`<CLAUDE_CONFIG_DIR|~/.claude>/projects/<인코딩한 cwd>/<session>.jsonl`). session 없음 → `NoTranscript`(이유 = `error`) — 폴더의 아무 파일이나 고르지 않는다
  - session 은 SDK 가 보낸다(S3c): Claude Code 는 자식 프로세스에 `CLAUDE_CODE_SESSION_ID`(uuid = jsonl 파일 이름)를 준다 → `hd_sdk.whoami` 가 kind claude 의 hello 에 `session` + `cwd`(os.getcwd()) 를 싣는다. 추정(가장 최근 파일 고르기)은 하지 않는다 — 정확한 파일 하나
  - hello 에 `cwd` 가 있으면(`anywhere=False`) 그 폴더와 위 폴더들(`cwd_chain` — hd 가 띄운 폴더 아래에서 돌 수 있어서)의 projects 폴더에서만 찾는다. 캔버스 힌트·다른 projects 폴더는 보지 않는다. 못 찾으면 `TranscriptUnavailable`
  - `cwd` 없음(옛 SDK) = 예전 길: 저장소·out 폴더 이름 먼저, 없으면 `projects/*/<session>.jsonl` 이름으로만
  - 펌프의 소스 열쇠 = (종류, session, cwd) — 바뀌면 새 소스·END
- kind paseo 또는 kind 없음(붙이기만 한 id = 오늘의 Paseo id, `adapters.choose` 와 같은 규칙) → `PaseoTranscript`
- 그 밖(codex · other) → `NoTranscript`

Claude jsonl 에서 읽는 것: `type` user(사람 말 — `isMeta`·`isSidechain`·`turnOrigin: task_notification`·`<system-reminder>` 등 꼬리표 글·도구 결과는 버림, 슬래시 명령은 `/이름 인자`) · assistant 의 `text` 블록 · `tool_use`(이름 + 대표 인자 하나). 생각(thinking)·system·attachment·api-request*·file-history* 는 버린다.

## 사생활
- 고르거나 붙인 에이전트만(`allowed` = `queue.agent` 이거나 이 프로젝트에 hello 한 에이전트). 그 밖은 403 `reason:'not-selected'`. 고르기가 풀리면 다음 tick 에 뺀다
- 세션 파일은 그 session 이름의 파일 하나만 연다(다른 세션은 열지 않는다). 세션 id 는 `[A-Za-z0-9_-]{1,128}` 만(경로 글자 거절)
- `cwd` 는 폴더 이름으로 바꿀 때 글자·숫자 밖이 모두 `-` 가 되어 `..`·구분자로 projects 밖에 못 나간다(그래도 `projects/<한 칸>/` 인지 다시 본다). 서버는 `cwd` 를 밖으로 내지 않는다(presence `public` 에 없음)
- 대화 기록을 디스크에 쓰지 않는다(이벤트 고리·응답에만)

## 오류 탐지
- 파일 없음·CLI 실패 = `TranscriptUnavailable` — 펌프는 `[hd]` 한 줄(같은 오류는 한 번), 다른 에이전트는 계속 · HTTP 는 200 `{entries:[], cursor: since, error}`
- 깨진 cursor = 400 · agent 없음 = 400
- 긴 줄(1 MB 넘음)은 끝까지 이어 읽고, 32 MB 넘으면 건너뜀(`[hd]` 한 줄)
- 펌프 간격: Claude 1초 · Paseo 3초(CLI 띄우는 값) · NoTranscript 30초. 읽기는 자물쇠 밖

## 고치면 돌릴 것
`pytest tests/test_canvas_unit_transcripts.py`(unit) + `hd/tests -k no_window`
