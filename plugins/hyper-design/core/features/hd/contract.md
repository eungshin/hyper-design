# hd — 계약

터미널 에이전트(Claude Code · Codex · Paseo 무엇이든)가 떠 있는 캔버스를 찾고, 메모를 번호·대상·상태와 함께 읽고, 구조 있는 답을 단다. 사용자가 메모를 붙여 넣을 일이 없게.

> 47-3 부터 `hd.py` 는 `hd_sdk`(Hub·Project·Note·Event·HdError) 위 얇은 껍데기 — 객체·오류(`--json` 오류 = `{error, kind, next?}`)는 [hd_sdk/contract.md](hd_sdk/contract.md). 아래 명령·출력·종료 코드는 그대로.

```
python $SK/features/hd/hd.py ls [--json]
python $SK/features/hd/hd.py notes [<project>|--out PATH] [--open|--sent|--all] [--json]
python $SK/features/hd/hd.py reply <screen>#<no>|<note-id> --kind <종류> …칸 [--detail …] [--by NAME] [--project P|--out PATH] [--json]
python $SK/features/hd/hd.py projects [--json]
python $SK/features/hd/hd.py save [--name N] [--out PATH] [--json]
python $SK/features/hd/hd.py open <name|path> [--agent ID] [--no-open] [--json]
python $SK/features/hd/hd.py forget <name> [--json]
python $SK/features/hd/hd.py stop [<name|path>] [--json]
python $SK/features/hd/hd.py attach [--agent ID|none] [<name|path>] [--json]
python $SK/features/hd/hd.py progress "<글>" [<name|path>] [--screen ID] [--agent ID] [--json]   # 진행 한 줄 → 접속 칩·대화창(47-5a)
python $SK/features/hd/hd.py wait [<name|path>] [--timeout S] [--json]
python $SK/features/hd/hd.py claim <screen> [<name|path>] [--note TEXT] [--by ID] [--json]
python $SK/features/hd/hd.py release <screen> [<name|path>] [--json]
python $SK/features/hd/hd.py home [--no-browser] [--port N] [--restart] [--shortcut [--desktop DIR]] [--json]   # 홈 허브 · 바탕 화면 바로 가기 — home/contract.md
```
설치(전역 R52): `~/.claude/tools/hd/hd.cmd`·`hd`(sh) 가 이 파일을 부르는 얇은 감싸개, 사용법은 `~/.claude/commands/hd.md`(필요할 때만 읽힘).

## 입력
- 떠 있는 표지 `<HD_HOME | ~/.hyper-design>/active/<pid>.json` = `{pid, project, out, url, token, port, agent, started, code}`(`code` = 그 도우미가 뜬 코드 도장, 47-7 — 옛 도우미는 없음 = 옛것) — `canvas/helper.py` 가 시작 때 쓰고 정상 종료(atexit · Ctrl+C · SIGTERM · SIGBREAK) 때 지운다. 강제 종료로 남은 표지는 읽는 쪽이 1초 핑(`GET /api/state`)으로 거른다(지우지 않음). `project` = out 폴더 이름이 `out` 이면 그 위 폴더 이름, 아니면 out 이름
- `<out>/.hd-canvas.json`(canvas `contract.md` 상태 파일) — 읽기만. `state.notes` 와 `state.note-seq`
- `<out>/screens.json` — 반영됨 `screens` 의 id 검사
- 프로젝트 목록 `<HD_HOME | ~/.hyper-design>/projects.json` = `{version:1, projects:[{name, out, kind:'run', created, last_opened, title?, starred?, trashed?}]}` — **링크만**(새 칸은 선택 — Home 의 제목·별표·휴지통, 규칙 `hd_projects.update`·`forget_trashed`, home/contract.md)(out 이 어디 있는지). 상태는 `<out>/.hd-canvas.json` 에 이미 있으므로 복사하지 않는다. 주인 = `hd_client`(임시 파일 + `os.replace`); `helper.py` 는 시작 때 그 out 이 없으면 `hd_client.register` 로 넣는다. 깨진 파일은 `projects.json.corrupt-<시각>` 으로 옮기고 `[hd]` 한 줄 + 빈 목록. 모양이 틀린 항목 하나는 건너뛰고 `[hd]` 한 줄(파일은 그대로)

## 출력
- 쓰기는 늘 도우미 `POST /api/reply {note: id | {screen, no}, reply}` 로(상태 파일 쓰는 곳 하나). 도우미가 없으면 `hd reply` 는 실패하고 띄우는 명령을 알려 준다
- `--json` 모양(왕복): `stop` → `{project, out, pid, port, how: route|kill|gone|other}` · `attach` → `{project, out, pid, agent, was}` · `wait` → `notes` 와 같은 모양(`which: working`) · `progress` → `{project, text, screen, event}`. `wait` 시간 넘음은 종료 코드 **2**(다른 오류는 1)
- `--json` 모양: `ls` → `[{project, out, url, agent, pid, port, started, open}]` · `notes` → `{project, out, rev, helper, which, notes:[{id, screen, no, status, intent, sent, edit, scope, target:{path, quote, count}, text, replies}]}` · `reply` → `{rev, status, note, screen}` · `projects` → `[{name, title, out, state: running|off|missing, url, pid, created, last_opened, starred, trashed}]` · `save` → `{name, out, kind, created, last_opened, added}` · `open` → `{name, out, url, pid, agent, reused}` · `forget` → 지운 항목 · 오류 → `{error}`(종료 코드 1)
- `notes` 줄: `scope`(canvas R7 `n.scope` = element|screen|all, 없으면 element)가 element 가 아니면 대상 뒤에 `· 범위: 이 화면` / `· 범위: 모든 화면`

## 프로젝트 (링크) 규칙 — `hd_projects.py`
- 이름 = slug(글자·숫자·'-', 소문자, 한글 그대로), 목록에서 하나뿐. 기본 이름 = `project_name`(겹치면 `-2`, `-3`…). `--name` 이 다른 out 의 이름이면 오류
- 같은 out 은 한 항목(경로 비교: 구분자·끝 '/' 무시, 드라이브 경로는 대소문자 무시). 다시 save 하면 이름만 바뀔 수 있다
- 순서 = 마지막으로 연 때 최근 것부터. 상태 = running(살아 있는 표지) · off(꺼짐) · missing(없음: out 에 screens.json 이 없음 — 저절로 지우지 않는다)
- `hd save` 기본 out = 떠 있는 캔버스 하나(없거나 여럿이면 `--out` 필요). `hd forget` = 링크만 지움, 파일은 손대지 않음
- `hd open`: 목록 이름 → 아니면 out 경로(목록에 없으면 넣음). 그 out 을 띄운 도우미(표지 + 핑, 아니면 `<out>/.hd-helper.json` 의 살아 있는 pid + 답하는 주소 — `live_record`)가 있으면 그대로 씀. 띄운 도우미가 '이미 떠 있음'으로 끝나면 그 도우미를 씀(#271). 없으면 `build_ref.py <out>`(실패해도 `index.html` 이 있으면 경고 후 계속) → `helper.py <out> --no-open [--paseo-agent ID]` 를 떼어 띄움(Windows `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP|CREATE_NO_WINDOW`, posix `start_new_session`, 출력 `<out>/.hd-helper.log` — out 안, #281) → 표지를 10초까지 기다림 → `last_opened` → `--no-open` 이 아니면 브라우저. `--agent` 기본 = env `PASEO_AGENT_ID`. 떠 있는 도우미의 agent 가 다르면 한 줄로 알린다(바꾸지 않음)

## 왕복 (#245 · #230) — 대상 고르기 = `hd_model.choose`
- 대상: 인자 없으면 떠 있는 캔버스 하나(없거나 여럿이면 목록과 함께 오류). 인자 = 표지 project 이름 · 저장한 이름 · out 경로(`hd_projects.key` 로 비교)
- out 같음·안 규칙은 하나(#282): `hd_projects.same`·`inside`(key: 구분자 '/'·끝 '/' 없앰·드라이브 경로 대소문자 무시) — `hd.py` 의 `_same`/`resolve` 와 `canvas/helper.py` 의 `_inside` 가 이것을 부르고, 절대경로로 푸는 일은 Client(`abs_out`)·helper 가 한 번
- `hd stop` — `POST /api/stop`(도우미가 `{stopping:true}` 답 → 서버 정상 종료 → 표지 지움 · `.hd-helper.json` 은 다음 시작의 포트 `{port}` 만 남김) → 표지가 없어지고 포트가 닫힐 때까지 5초. 도우미가 답하지 않으면 표지의 pid 를 강제 종료(Windows `%SystemRoot%\System32\taskkill.exe /PID n /F`, posix SIGKILL)하고 표지를 지운다. 그 pid 가 python 이 아니면(번호 재사용) 죽이지 않고 표지만 지움 · 프로세스가 이미 없으면 표지만 지움. 이름을 주면 응답 없는 표지도 고른다(살아 있는 것이 먼저). 프로젝트 목록(링크)은 그대로
- `hd attach` — `POST /api/attach {agent}` → `/api/forward` 가 보낼 곳과 표지의 `agent` 를 바꾼다(다시 띄우지 않음, 같은 pid). `--agent` 기본 env `PASEO_AGENT_ID`, `none` = 떼기(대기열 파일로). id 규칙 `hd_model.agent_error`: 빈 글 아님 · 128자 이하 · 띄어쓰기 없음 — CLI 와 도우미(400)가 같은 함수. 붙인 뒤 접속 알리기도 한 번(47-5a: `hello` kind paseo · listen false · 맥박 없음 — 접속 칩에 보이기만, 보내기는 그대로 paseo. 옛 서버·실패는 조용히, attach 는 됨)
- 접속(47-5a, 새 길 — 위 attach·대기열은 그대로): 에이전트가 SDK `Hub().hello(<이름>)` 로 접속하면(listen, 맥박 데몬) 캔버스 '보내기'가 이벤트 `request.sent` 로 온다(`Project.requests()` — 터미널·Paseo 없이). 서버 쪽 hello/beat/bye/progress/agents/requests 와 받는 곳 고르기는 `canvas/contract/presence.md`, SDK 는 `hd_sdk/contract.md` '접속'
- `hd progress "<글>"` — `POST /progress {text ≤200, screen?, agent?}`(SDK `Project.progress`) → 이벤트 `agent.progress` → 캔버스 접속 칩·대화창 진행 줄. `--agent` 기본 env `PASEO_AGENT_ID`. 모르는 id 면 보이기만 hello 뒤 한 번 더. 옛 서버 = `NotYet`(종료 코드 1). 예) `hd progress "홈 버튼 고치는 중" --screen home`
- 캔버스도 붙인다(#214): 칩 메뉴가 `GET /api/agents`(`paseo ls -g --json`, 읽기만)로 에이전트를 보여 주고 고르면 같은 `POST /api/attach` — 이 저장소에 실행 중인 것이 하나면 열 때 자동(붙어 있으면 그대로). 규칙은 `canvas/contract/agents.md`
- `hd wait` — 2초마다 `GET /api/state` → `hd_model.pending`(status `working` = 보냄+답 없음)이 하나라도 있으면 `hd notes` 처럼 보여 주고 0. 기본 600초, 넘으면 2. 도우미에 닿지 않으면 그 out 의 표지를 다시 읽어 새 도우미로 이어 간다(`[hd]` 경고 한 줄)
- 도우미 `GET /api/projects` → `hd projects --json` 과 같은 줄(`hd_client.project_rows`) + 허브 썸네일 `thumb` — 라우트는 `home/home_api.route`(허브와 같은 JSON, 새 라우트 new·project·forget·reveal·tabs·home 도) · `POST /api/open {name, agent?}` → `hd open` 과 같은 `hd_client.open_project`(브라우저 없음) → `{name, out, url, pid, agent, reused}`. agent 기본 = 그 도우미의 지금 agent. 모르는 이름·없어진 out 404 `{error}` · 빌드·띄우기 실패 500. 둘 다 `X-HD-Token`
- `hd claim <screen>` (#254) — "이 화면 고치는 중": `POST /api/claim {screen, by?, note?}` → 도우미가 최신 상태 파일 `state.busy` 에 `{via:'cli', since(ms), file, mtime(지금 파일 시각), by?, note?}` 를 넣고 rev+1(rev 를 받지 않는다 — `/api/reply` 와 같음: 쓰는 곳·자물쇠 하나라 CLI 의 409 재시도가 필요 없다). 캔버스는 새로고침 없이 그 카드에 덮개, 파일이 바뀌면 걷힌다. `--by` 기본 env `PASEO_AGENT_ID`(규칙 `agent_error`), `--note` ≤140. 없는 화면 = 한 줄 오류·종료 코드 1(CLI 가 screens.json 으로 먼저, 도우미도 404). 예) `hd claim job --note "제목 줄이는 중"`
- `hd release <screen>` — `POST /api/release {screen}` → `{rev, released}`(없으면 released false, 쓰지 않음). 예) `hd release job`
- `--json`: `claim` → `{rev, screen, file, project, by, note}` · `release` → `{rev, released, project, screen}`
- 도우미는 화면 파일을 1초마다 지켜본다(`GET /api/files?since=N` → `{seq, changed}`) — 캔버스는 바뀐 카드만 다시 싣는다(canvas `contract/busy.md`)

## 답 규칙 (tasks/PLAN-2026-10-23.md §3 — task A2 의 캔버스와 같은 계약)
답 = `{kind, by, at, …칸, detail?}`. AI 종류: `반영됨 {what ≤140, screens ≥1, captured: bool}` · `일부 {done ≤140, left ≤140}` · `대체됨 {where ≤140}` · `답변 {text ≤280}`(질문 메모에만) · `질문 {question ≤140, choices 2–4개 각 ≤40}` · `detail ≤2000` 아무 종류에나 · `by` 1–40자(기본 `agent`). `보류` 없음(미루려면 질문). 사람 종류 `확인`·`다시` 는 캔버스만 — `hd`/도우미는 400. 모르는 칸도 400. 실패한 칸마다 한 줄 이유.
보내지 않은 메모(draft)에는 답하지 않는다(400).
상태(저장하지 않음): 보내지 않음 → draft · 보냄+답 없음 → working · 마지막 질문 → decide · 일부 → partial · 반영됨/대체됨/답변/확인 → done · 다시 → draft.
번호: 메모의 `no`, 없으면 canvas `annotation.migrate` 와 같은 규칙(그 화면의 가장 큰 번호·`note-seq` 다음부터 목록 차례) — 메모 파일은 고치지 않는다.
공유 fixture `tests/fixtures/replies.json` = `[{name, note_intent, sent, from: agent|any, replies, valid, reason?, status?, says?}]` — `from=agent` 는 에이전트가 보낸 답(사람 종류 거절), `reason` 은 오류 글 안 조각, `status` 는 valid 일 때 계산 상태, `says` 는 마지막 답의 캔버스 답 줄(`annotation.says` 와 같아야 하고, `hd_model.says` 는 그 글로 시작 — 뒤에 터미널 덧붙임만). Python 테스트가 읽고, A2 가 JS 테스트도 같은 파일을 읽게 한다.

## 구조 (층)
- Model `hd_model.py` — 순수: 답 검사·찍기(by/at 은 받은 값), 상태, 번호, 메모 찾기, 줄 객체·사람용 줄. I/O·시계 없음(`tests/test_hd_model.py` 순수성 검사). `canvas/helper.py` 도 이 파일 하나로 검사한다(규칙 하나)
- Client `hd_client.py` — I/O 만: 표지 읽기 · 핑 · 상태 파일·screens.json 읽기 · 답 보내기 · 프로젝트 목록 읽고 쓰기 · 빌드·도우미 띄우기·기다리기 · 브라우저. 규칙 없음
- Model `helper_model.py` — 순수: 도우미 규칙 `parse_since` `state_reply`(#273 `?since`) · `too_big`(413 글) · `archive_lines` `archive_notes`(보관 줄) · `history_prune` `queue_prune`(#281 정리 고르기 — 시각 글 비교, 기준 시각은 부르는 쪽). I/O·시계 없음(`tests/test_hd_helper_model.py` 순수성 검사)
- Model `hd_projects.py` — 순수: 프로젝트 목록 규칙(넣기·고치기·찾기·지우기·순서·이름·줄). 경로를 풀거나 시각을 재는 일은 Client(`tests/test_hd_projects.py` 순수성 검사)
- CLI `hd.py` — argparse → Client → Model → 출력. 캔버스 고르기(하나면 그것, 여럿이면 목록과 함께 오류)만 한다

조각 보고:
- `hd_model` · 답 규칙·상태·번호·줄·기다릴 메모·에이전트 id·대상 고르기 · 상태 없음 · 메모 목록·답·note-seq·표지 목록 · `check_reply` `stamp` `status` `numbers` `find` `rows` `pick` `format_rows` `format_canvases` `project_name` `pending` `agent_error` `choose` · 한 out 에 도우미 하나 `helper_record` `start_verdict` · 덮개 `claim_error` `busy_items` `claim` `release`
- `hd_projects` · 프로젝트 링크 규칙 · 상태 없음 · 목록 객체·경로 글·시각 글 · `slug` `key` `same` `inside` `parse` `save` `touch` `forget` `find` `by_out` `ordered` `rows` `format_rows` `link_line` `ProjectError` `update` `forget_trashed` `title_error`
- `hd_client` · 파일·HTTP 읽고 보내기 · `projects.json`(주인) · 표지·상태 파일은 helper 가 주인 · HD_HOME · out 경로 · 표지 · `markers` `running` `ping` `read_state` `screen_ids` `load_projects` `save_projects` `register` `serving` `build` `spawn_helper` `wait_serving` `open_project` `project_rows` `call` `stop` `kill_pid` `attach` `get_state` `claim` `release` `stale` `read_record` `pid_alive` `live_record` `HdError` `NotFound` `TimedOut` `manifest_title` `titles_map` `update_project` `forget_trashed` · 코드 도장(47-7) `code_stamp` `page_code` `is_busy` `freshen`
- `hd` · 명령 풀이·캔버스 고르기·출력 · 상태 없음 · argv · `main` `resolve` `pick_canvas` `cmd_ls` `cmd_notes` `cmd_reply` `cmd_projects` `cmd_save` `cmd_open` `cmd_forget` `cmd_stop` `cmd_attach` `cmd_progress` `cmd_wait` `cmd_claim` `cmd_release` `cmd_home`(home_server.serve · shortcut 을 부를 뿐 — `--restart` 도)
- `canvas/helper.py` 추가분 · 표지 쓰기·지우기(주인) · `/api/reply`(상태 파일 쓰기는 기존 `_state_write` 하나로) · 시작 때 프로젝트 목록에 넣기(`hd_client.register`, 실패해도 한 줄 남기고 계속) · `write_marker` `reply_post` `hd_home` · 왕복 라우트 `/api/stop`(정상 종료) · `/api/attach`(`srv.agent` 하나가 보낼 곳의 주인, 표지 agent 고쳐 씀 `marker_agent`) · `GET /api/projects` · `/api/open`(`hd_client` 를 부를 뿐 — 복사 없음) · `attach_post` `open_post` `marker_agent` · 덮개 `/api/claim`·`/api/release`(상태 파일 쓰기는 `_state_save` 하나) `claim_post` `release_post` · 화면 파일 지켜보기 `FileWatch`(seq·바뀐 화면, I/O 없음) `scan` `_watch_loop`(1초, `server_close` 가 멈춤) `GET /api/files`
- `skills/open/SKILL.md` · 인자 없음 → `hd projects` 후 한 번 묻기 · 이름/경로 → `hd open` · 새로 → PRD 한 번 묻고 `/hyper-design:go` 로 넘긴 뒤 `hd save --out`

## 서버 하나 (task 47-2)
`markers()` = 파일 표지(옛 helper.py) + `hub_markers()`(허브 안 세션 — `home.json` 의 허브에 `GET /v1/sessions`, 허브 프로세스 안이면 `LOCAL` 로 HTTP 없이). 허브 표지는 `prefix` `/v1/p/<이름>` 과 `hub:true` — `_base` 가 prefix 를 붙이고, `stop` 은 그 세션만 닫는다(허브 pid 는 끄지 않음). `open_project` = `resolve` → 떠 있는 것(허브 세션이면 `open_in_hub`, 아니면 `freshen`) → 허브가 있으면 `open_in_hub`(POST /api/open) → 없으면 옛 도우미 띄우기.

## 코드 도장 (47-7) — 다시 열면 늘 지금 코드
- 지금 도장 = `hd_client.code_stamp()`(= `canvas/code_probe.current`, 저장소면 HEAD 의 core 나무). 재지 못하면 None = 판단하지 않음(옛 길: 그대로 다시 씀). 규칙은 순수 `canvas/code_stamp.py`(`reuse_verdict` · `page_after`)
- `hd open`·도우미 `/api/open` 이 떠 있는 옛 도우미를 다시 쓰기 전 `freshen(out, m)`: 페이지(`index.html` 의 `hd-code`)가 옛것 = 다시 빌드 · 프로세스(표지·`.hd-helper.json` 의 `code`)가 옛것이고 쉼 = `stop` 뒤 None → 새로 띄움(같은 포트 — `.hd-helper.json` 의 지난 포트) · 옛것이지만 AI 덮개(`state.busy`) 중 = 그대로 두고 페이지만 다시 빌드, `[hd]` 한 줄(`BUSY_NOTICE`, 이 프로세스에서 out 마다 한 번)
- 허브 세션은 끄지 않는다(`movable` 아님) — 허브가 같은 일을 하고(home/contract.md), 허브 자신이 옛것이면 `/api/open` 답의 `notice` 를 `[hd]` 한 줄로
- `hd home` 이 떠 있는 옛 허브를 다시 쓰면 주소 뒤 `· 새 버전이 있어요 — hd home --restart 로 다시 켜면 반영돼요`(`--json` `stale:true`). `--restart` = 떠 있는 허브를 `POST /api/hub/stop`(없는 옛 허브 = python pid 강제 종료)으로 끄고 같은 포트로 다시 띄움

## 책임 게이트
canvas `contract.md` 의 책임 게이트를 그대로 따른다(층 · 상태마다 주인 하나 · 오류 탐지: 실패는 한 줄로 알리고 종료 코드 1, 깨진 표지는 건너뜀, 깨진 상태 파일은 오류로 알림 · 새 Model 규칙은 unit 테스트).

## 테스트
`python -m pytest plugins/hyper-design/core/features/hd/tests` — 브라우저 없음(약 60초). `test_hd_model.py`(fixture·순수성·번호·줄·says·범위) · `test_hd_projects.py`(목록 규칙·이름·깨진 파일·순수성) · `test_hd_helper_reply.py`(`/api/reply` 200/400/404/403 · 최신 파일에 붙임 · 표지 쓰기/지우기) · `test_hd_cli.py`(도우미 자식 프로세스 + `hd ls/notes/reply`) · `test_hd_roundtrip_model.py`(`pending`·`agent_error`·`choose`) · `test_hd_roundtrip.py`(stop 라우트·강제 종료·표지만 지움 · attach 로 보낼 곳 바뀜(같은 pid, 가짜 paseo) · wait 0/2·도우미 다시 떠도 이어감 · `/api/projects`·`/api/open` 200/404) · `test_hd_claim.py`(claim 규칙 · claim → busy · release → 지움 · 없는 화면 종료 1 · `/api/files` 가 바뀐 화면을 알림) · `test_hd_helper_port.py`(다시 띄워도 같은 포트 · 막힌 포트는 새 포트 + 한 줄 · 둘째 시작 거절 · 죽은 pid 덮어씀 · hd open 이 기록의 도우미를 다시 씀 · 빌드 중에도 GET /api/state 1초 안) · `test_hd_helper_model.py`(since·413 글·보관 줄·정리 고르기·`same`/`inside`·순수성) · `test_hd_projects_cli.py`(`save → projects → open`(빌드·떼어 띄움·같은 도우미 다시 씀) `→ forget`, 도우미가 스스로 넣기, 없어진 out, 깨진 목록) · `test_hd_code_fresh.py`(47-7: 옛 페이지 다시 빌드 · 쉬는 옛 도우미 다시 띄움 · 덮개 중 옛 도우미 그대로 + 한 줄 · 허브 세션 페이지 다시 빌드 · 허브가 옛 도우미를 제 세션으로 · 옛 허브 notice · `/api/hub/restart` · `hd home --restart`) · `test_hd_sdk_presence.py`·`test_hd_sdk_presence_hub.py`(47-5a 접속 — hd_sdk/contract.md) · `test_hd_no_window.py`(canvas·hd·home 의 모든 자식 프로세스가 `creationflags`). 스킬은 `python -m pytest plugins/hyper-design/skills/open`. `helper.py` 를 고치면 이것과 canvas `-m "unit or helper"` 도.
