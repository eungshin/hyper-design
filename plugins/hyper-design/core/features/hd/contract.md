# hd — 계약

터미널 에이전트(Claude Code · Codex · Paseo 무엇이든)가 떠 있는 캔버스를 찾고, 메모를 번호·대상·상태와 함께 읽고, 구조 있는 답을 단다. 사용자가 메모를 붙여 넣을 일이 없게.

```
python $SK/features/hd/hd.py ls [--json]
python $SK/features/hd/hd.py notes [<project>|--out PATH] [--open|--sent|--all] [--json]
python $SK/features/hd/hd.py reply <screen>#<no>|<note-id> --kind <종류> …칸 [--detail …] [--by NAME] [--project P|--out PATH] [--json]
```
설치(전역 R52): `~/.claude/tools/hd/hd.cmd`·`hd`(sh) 가 이 파일을 부르는 얇은 감싸개, 사용법은 `~/.claude/commands/hd.md`(필요할 때만 읽힘).

## 입력
- 떠 있는 표지 `<HD_HOME | ~/.hyper-design>/active/<pid>.json` = `{pid, project, out, url, token, port, agent, started}` — `canvas/helper.py` 가 시작 때 쓰고 정상 종료(atexit · Ctrl+C · SIGTERM · SIGBREAK) 때 지운다. 강제 종료로 남은 표지는 읽는 쪽이 1초 핑(`GET /api/state`)으로 거른다(지우지 않음). `project` = out 폴더 이름이 `out` 이면 그 위 폴더 이름, 아니면 out 이름
- `<out>/.hd-canvas.json`(canvas `contract.md` 상태 파일) — 읽기만. `state.notes` 와 `state.note-seq`
- `<out>/screens.json` — 반영됨 `screens` 의 id 검사

## 출력
- 쓰기는 늘 도우미 `POST /api/reply {note: id | {screen, no}, reply}` 로(상태 파일 쓰는 곳 하나). 도우미가 없으면 `hd reply` 는 실패하고 띄우는 명령을 알려 준다
- `--json` 모양: `ls` → `[{project, out, url, agent, pid, port, started, open}]` · `notes` → `{project, out, rev, helper, which, notes:[{id, screen, no, status, intent, sent, edit, target:{path, quote, count}, text, replies}]}` · `reply` → `{rev, status, note, screen}` · 오류 → `{error}`(종료 코드 1)

## 답 규칙 (tasks/PLAN-2026-10-23.md §3 — task A2 의 캔버스와 같은 계약)
답 = `{kind, by, at, …칸, detail?}`. AI 종류: `반영됨 {what ≤140, screens ≥1, captured: bool}` · `일부 {done ≤140, left ≤140}` · `대체됨 {where ≤140}` · `답변 {text ≤280}`(질문 메모에만) · `질문 {question ≤140, choices 2–4개 각 ≤40}` · `detail ≤2000` 아무 종류에나 · `by` 1–40자(기본 `agent`). `보류` 없음(미루려면 질문). 사람 종류 `확인`·`다시` 는 캔버스만 — `hd`/도우미는 400. 모르는 칸도 400. 실패한 칸마다 한 줄 이유.
보내지 않은 메모(draft)에는 답하지 않는다(400).
상태(저장하지 않음): 보내지 않음 → draft · 보냄+답 없음 → working · 마지막 질문 → decide · 일부 → partial · 반영됨/대체됨/답변/확인 → done · 다시 → draft.
번호: 메모의 `no`, 없으면 canvas `annotation.migrate` 와 같은 규칙(그 화면의 가장 큰 번호·`note-seq` 다음부터 목록 차례) — 메모 파일은 고치지 않는다.
공유 fixture `tests/fixtures/replies.json` = `[{name, note_intent, sent, from: agent|any, replies, valid, reason?, status?}]` — `from=agent` 는 에이전트가 보낸 답(사람 종류 거절), `reason` 은 오류 글 안 조각, `status` 는 valid 일 때 계산 상태. Python 테스트가 읽고, A2 가 JS 테스트도 같은 파일을 읽게 한다.

## 구조 (층)
- Model `hd_model.py` — 순수: 답 검사·찍기(by/at 은 받은 값), 상태, 번호, 메모 찾기, 줄 객체·사람용 줄. I/O·시계 없음(`tests/test_hd_model.py` 순수성 검사). `canvas/helper.py` 도 이 파일 하나로 검사한다(규칙 하나)
- Client `hd_client.py` — I/O 만: 표지 읽기 · 핑 · 상태 파일·screens.json 읽기 · 답 보내기. 규칙 없음
- CLI `hd.py` — argparse → Client → Model → 출력. 캔버스 고르기(하나면 그것, 여럿이면 목록과 함께 오류)만 한다

조각 보고:
- `hd_model` · 답 규칙·상태·번호·줄 · 상태 없음 · 메모 목록·답·note-seq · `check_reply` `stamp` `status` `numbers` `find` `rows` `pick` `format_rows` `format_canvases` `project_name`
- `hd_client` · 파일·HTTP 읽고 보내기 · 상태 없음(표지·상태 파일은 helper 가 주인) · HD_HOME · out 경로 · 표지 · `markers` `running` `ping` `read_state` `screen_ids` `post_reply` `HdError`
- `hd` · 명령 풀이·캔버스 고르기·출력 · 상태 없음 · argv · `main` `resolve` `cmd_ls` `cmd_notes` `cmd_reply`
- `canvas/helper.py` 추가분 · 표지 쓰기·지우기(주인) · `/api/reply`(상태 파일 쓰기는 기존 `_state_write` 하나로) · `write_marker` `reply_post` `hd_home`

## 책임 게이트
canvas `contract.md` 의 책임 게이트를 그대로 따른다(층 · 상태마다 주인 하나 · 오류 탐지: 실패는 한 줄로 알리고 종료 코드 1, 깨진 표지는 건너뜀, 깨진 상태 파일은 오류로 알림 · 새 Model 규칙은 unit 테스트).

## 테스트
`python -m pytest plugins/hyper-design/core/features/hd/tests` — 브라우저 없음(약 20초). `test_hd_model.py`(fixture·순수성·번호·줄) · `test_hd_helper_reply.py`(`/api/reply` 200/400/404/403 · 최신 파일에 붙임 · 표지 쓰기/지우기) · `test_hd_cli.py`(도우미 자식 프로세스 + `hd ls/notes/reply`). `helper.py` 를 고치면 이것과 canvas `-m "unit or helper"` 도.
