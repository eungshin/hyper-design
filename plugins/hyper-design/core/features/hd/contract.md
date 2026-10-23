# hd — 계약

터미널 에이전트(Claude Code · Codex · Paseo 무엇이든)가 떠 있는 캔버스를 찾고, 메모를 번호·대상·상태와 함께 읽고, 구조 있는 답을 단다. 사용자가 메모를 붙여 넣을 일이 없게.

```
python $SK/features/hd/hd.py ls [--json]
python $SK/features/hd/hd.py notes [<project>|--out PATH] [--open|--sent|--all] [--json]
python $SK/features/hd/hd.py reply <screen>#<no>|<note-id> --kind <종류> …칸 [--detail …] [--by NAME] [--project P|--out PATH] [--json]
python $SK/features/hd/hd.py projects [--json]
python $SK/features/hd/hd.py save [--name N] [--out PATH] [--json]
python $SK/features/hd/hd.py open <name|path> [--agent ID] [--no-open] [--json]
python $SK/features/hd/hd.py forget <name> [--json]
```
설치(전역 R52): `~/.claude/tools/hd/hd.cmd`·`hd`(sh) 가 이 파일을 부르는 얇은 감싸개, 사용법은 `~/.claude/commands/hd.md`(필요할 때만 읽힘).

## 입력
- 떠 있는 표지 `<HD_HOME | ~/.hyper-design>/active/<pid>.json` = `{pid, project, out, url, token, port, agent, started}` — `canvas/helper.py` 가 시작 때 쓰고 정상 종료(atexit · Ctrl+C · SIGTERM · SIGBREAK) 때 지운다. 강제 종료로 남은 표지는 읽는 쪽이 1초 핑(`GET /api/state`)으로 거른다(지우지 않음). `project` = out 폴더 이름이 `out` 이면 그 위 폴더 이름, 아니면 out 이름
- `<out>/.hd-canvas.json`(canvas `contract.md` 상태 파일) — 읽기만. `state.notes` 와 `state.note-seq`
- `<out>/screens.json` — 반영됨 `screens` 의 id 검사
- 프로젝트 목록 `<HD_HOME | ~/.hyper-design>/projects.json` = `{version:1, projects:[{name, out, kind:'run', created, last_opened}]}` — **링크만**(out 이 어디 있는지). 상태는 `<out>/.hd-canvas.json` 에 이미 있으므로 복사하지 않는다. 주인 = `hd_client`(임시 파일 + `os.replace`); `helper.py` 는 시작 때 그 out 이 없으면 `hd_client.register` 로 넣는다. 깨진 파일은 `projects.json.corrupt-<시각>` 으로 옮기고 `[hd]` 한 줄 + 빈 목록. 모양이 틀린 항목 하나는 건너뛰고 `[hd]` 한 줄(파일은 그대로)

## 출력
- 쓰기는 늘 도우미 `POST /api/reply {note: id | {screen, no}, reply}` 로(상태 파일 쓰는 곳 하나). 도우미가 없으면 `hd reply` 는 실패하고 띄우는 명령을 알려 준다
- `--json` 모양: `ls` → `[{project, out, url, agent, pid, port, started, open}]` · `notes` → `{project, out, rev, helper, which, notes:[{id, screen, no, status, intent, sent, edit, scope, target:{path, quote, count}, text, replies}]}` · `reply` → `{rev, status, note, screen}` · `projects` → `[{name, out, state: running|off|missing, url, pid, last_opened}]` · `save` → `{name, out, kind, created, last_opened, added}` · `open` → `{name, out, url, pid, agent, reused}` · `forget` → 지운 항목 · 오류 → `{error}`(종료 코드 1)
- `notes` 줄: `scope`(canvas R7 `n.scope` = element|screen|all, 없으면 element)가 element 가 아니면 대상 뒤에 `· 범위: 이 화면` / `· 범위: 모든 화면`

## 프로젝트 (링크) 규칙 — `hd_projects.py`
- 이름 = slug(글자·숫자·'-', 소문자, 한글 그대로), 목록에서 하나뿐. 기본 이름 = `project_name`(겹치면 `-2`, `-3`…). `--name` 이 다른 out 의 이름이면 오류
- 같은 out 은 한 항목(경로 비교: 구분자·끝 '/' 무시, 드라이브 경로는 대소문자 무시). 다시 save 하면 이름만 바뀔 수 있다
- 순서 = 마지막으로 연 때 최근 것부터. 상태 = running(살아 있는 표지) · off(꺼짐) · missing(없음: out 에 screens.json 이 없음 — 저절로 지우지 않는다)
- `hd save` 기본 out = 떠 있는 캔버스 하나(없거나 여럿이면 `--out` 필요). `hd forget` = 링크만 지움, 파일은 손대지 않음
- `hd open`: 목록 이름 → 아니면 out 경로(목록에 없으면 넣음). 그 out 을 띄운 도우미(표지 + 핑)가 있으면 그대로 씀. 없으면 `build_ref.py <out>`(실패해도 `index.html` 이 있으면 경고 후 계속) → `helper.py <out> --no-open [--paseo-agent ID]` 를 떼어 띄움(Windows `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP|CREATE_NO_WINDOW`, posix `start_new_session`, 출력 `<out>/../helper.log`) → 표지를 10초까지 기다림 → `last_opened` → `--no-open` 이 아니면 브라우저. `--agent` 기본 = env `PASEO_AGENT_ID`. 떠 있는 도우미의 agent 가 다르면 한 줄로 알린다(바꾸지 않음)


## 답 규칙 (tasks/PLAN-2026-10-23.md §3 — task A2 의 캔버스와 같은 계약)
답 = `{kind, by, at, …칸, detail?}`. AI 종류: `반영됨 {what ≤140, screens ≥1, captured: bool}` · `일부 {done ≤140, left ≤140}` · `대체됨 {where ≤140}` · `답변 {text ≤280}`(질문 메모에만) · `질문 {question ≤140, choices 2–4개 각 ≤40}` · `detail ≤2000` 아무 종류에나 · `by` 1–40자(기본 `agent`). `보류` 없음(미루려면 질문). 사람 종류 `확인`·`다시` 는 캔버스만 — `hd`/도우미는 400. 모르는 칸도 400. 실패한 칸마다 한 줄 이유.
보내지 않은 메모(draft)에는 답하지 않는다(400).
상태(저장하지 않음): 보내지 않음 → draft · 보냄+답 없음 → working · 마지막 질문 → decide · 일부 → partial · 반영됨/대체됨/답변/확인 → done · 다시 → draft.
번호: 메모의 `no`, 없으면 canvas `annotation.migrate` 와 같은 규칙(그 화면의 가장 큰 번호·`note-seq` 다음부터 목록 차례) — 메모 파일은 고치지 않는다.
공유 fixture `tests/fixtures/replies.json` = `[{name, note_intent, sent, from: agent|any, replies, valid, reason?, status?}]` — `from=agent` 는 에이전트가 보낸 답(사람 종류 거절), `reason` 은 오류 글 안 조각, `status` 는 valid 일 때 계산 상태. Python 테스트가 읽고, A2 가 JS 테스트도 같은 파일을 읽게 한다.

## 구조 (층)
- Model `hd_model.py` — 순수: 답 검사·찍기(by/at 은 받은 값), 상태, 번호, 메모 찾기, 줄 객체·사람용 줄. I/O·시계 없음(`tests/test_hd_model.py` 순수성 검사). `canvas/helper.py` 도 이 파일 하나로 검사한다(규칙 하나)
- Client `hd_client.py` — I/O 만: 표지 읽기 · 핑 · 상태 파일·screens.json 읽기 · 답 보내기 · 프로젝트 목록 읽고 쓰기 · 빌드·도우미 띄우기·기다리기 · 브라우저. 규칙 없음
- Model `hd_projects.py` — 순수: 프로젝트 목록 규칙(넣기·고치기·찾기·지우기·순서·이름·줄). 경로를 풀거나 시각을 재는 일은 Client(`tests/test_hd_projects.py` 순수성 검사)
- CLI `hd.py` — argparse → Client → Model → 출력. 캔버스 고르기(하나면 그것, 여럿이면 목록과 함께 오류)만 한다

조각 보고:
- `hd_model` · 답 규칙·상태·번호·줄 · 상태 없음 · 메모 목록·답·note-seq · `check_reply` `stamp` `status` `numbers` `find` `rows` `pick` `format_rows` `format_canvases` `project_name`
- `hd_projects` · 프로젝트 링크 규칙 · 상태 없음 · 목록 객체·경로 글·시각 글 · `slug` `key` `parse` `save` `touch` `forget` `find` `by_out` `ordered` `rows` `format_rows` `link_line` `ProjectError`
- `hd_client` · 파일·HTTP 읽고 보내기 · `projects.json`(주인) · 표지·상태 파일은 helper 가 주인 · HD_HOME · out 경로 · 표지 · `markers` `running` `ping` `read_state` `screen_ids` `post_reply` `load_projects` `save_projects` `register` `serving` `build` `spawn_helper` `wait_serving` `open_browser` `HdError`
- `hd` · 명령 풀이·캔버스 고르기·출력 · 상태 없음 · argv · `main` `resolve` `cmd_ls` `cmd_notes` `cmd_reply` `cmd_projects` `cmd_save` `cmd_open` `cmd_forget`
- `canvas/helper.py` 추가분 · 표지 쓰기·지우기(주인) · `/api/reply`(상태 파일 쓰기는 기존 `_state_write` 하나로) · 시작 때 프로젝트 목록에 넣기(`hd_client.register`, 실패해도 한 줄 남기고 계속) · `write_marker` `reply_post` `hd_home`
- `skills/open/SKILL.md` · 인자 없음 → `hd projects` 후 한 번 묻기 · 이름/경로 → `hd open` · 새로 → PRD 한 번 묻고 `/hyper-design:go` 로 넘긴 뒤 `hd save --out`

## 책임 게이트
canvas `contract.md` 의 책임 게이트를 그대로 따른다(층 · 상태마다 주인 하나 · 오류 탐지: 실패는 한 줄로 알리고 종료 코드 1, 깨진 표지는 건너뜀, 깨진 상태 파일은 오류로 알림 · 새 Model 규칙은 unit 테스트).

## 테스트
`python -m pytest plugins/hyper-design/core/features/hd/tests` — 브라우저 없음(약 25초). `test_hd_model.py`(fixture·순수성·번호·줄·says·범위) · `test_hd_projects.py`(목록 규칙·이름·깨진 파일·순수성) · `test_hd_helper_reply.py`(`/api/reply` 200/400/404/403 · 최신 파일에 붙임 · 표지 쓰기/지우기) · `test_hd_cli.py`(도우미 자식 프로세스 + `hd ls/notes/reply`) · `test_hd_projects_cli.py`(`save → projects → open`(빌드·떼어 띄움·같은 도우미 다시 씀) `→ forget`, 도우미가 스스로 넣기, 없어진 out, 깨진 목록). 스킬은 `python -m pytest plugins/hyper-design/skills/open`. `helper.py` 를 고치면 이것과 canvas `-m "unit or helper"` 도.
