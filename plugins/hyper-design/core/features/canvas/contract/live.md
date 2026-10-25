# live — 캔버스가 서버 이벤트로 바로 반영(task 47-4b)

서버 쪽 계약 = `contract/events.md` · `tests/protocol/events.json`. 여기는 캔버스 쪽 구조만.

- `live.js`(Model, `HD.live`) — 이벤트 → 할 일(`plan`): notes.changed·claim·release 는 rev 가 새것일 때만 상태 다시 읽기 · screen.written ai 는 파일 seq 가 새것일 때 바뀐 카드(그중 되살리기 notify 의 메아리는 한 번 먹음, 4초) · human 은 처음 보는 stamp 일 때만 판 데이터 + 카드(캔버스가 스스로 쓴 것은 `own` 이 먼저 잡음, 도장 없는 되살리기는 1.5초 안 반대쪽이 실었으면 건너뜀) · ai.write = AI 기록 · build.done/failed(async) · reset = 상태·파일·AI 기록 다시 맞춤. 흐름 상태 `link`(열림 = 실시간, 오류 = 폴링 + 1·2·4…30초 뒤 다시) · `answer`(async 답 accepted → applied)
- `view-live.js`(View, 셸이 VB 뒤에서 mount) — EventSource 하나 `/api/events?hd=`(다시 붙을 때 `&since=`), `#mode` 뒤 칩 `#livechip`(실시간 · 2초 확인), document 의도 `hd-event`(대화창 진행 줄). 실시간이면 셸 `polling(false)` → `ST.live` · `VB.live` · `aiUndo.live` 가 주기 읽기를 멈춘다(덮개 칩의 /api/watch 는 칩이 있는 동안 그대로)
- 바로 쓰기 = async apply(`view-sync` `{edits, async:true}`). 쓰는 중에 온 다른 쓰기 알림은 끝난 뒤에(쓴 뒤 고른 요소 따라가기가 먼저), 내 쓰기의 알림은 내 답이 맡는다. build.failed{reverted} → `view-optimistic.reverted` 가 먼저 보인 변경을 거두고 토스트, 셸이 그 화면을 파일대로 다시
- 공용 ctx `reload(ids, {stamp, echo})`(features.js) — 교체 길로 카드 다시 싣기. `view-ai-undo` 가 쓴다
- 대화창 진행 줄(S2): `chat.progress` — 보냄 → AI 작업 중 · <화면> → 반영됨 · <화면> → 끝(release, 또는 쓰고 모든 메모에 답함) + 짧은 답

고치면 돌릴 것: `-m unit -k "live or chat"` + `-m "unit or helper or notes" --surface frame -n 4`(브라우저: `test_canvas_claim_watch.py -k polling_off` · `test_canvas_instant.py -k build_fails`)
