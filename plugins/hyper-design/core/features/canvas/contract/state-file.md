# 프로젝트 상태 파일 (state-file · view-state-sync)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `state-file`(Model)·`save-merge`(Model)·`view-state-sync`(View) — 프로젝트 상태 파일(#228): 프로젝트별 키(`hd-notes:`·`hd-card-pos:`·`hd-edit-log:`·`hd-link-names:`·`hd-hidden:`·`hd-locked:`·`hd-folders:`·`hd-busy:`·`hd-note-seq:`, 모두 `hashStr(KEYPATH)`)의 읽기·쓰기 주인은 `view-state-sync` 하나(셸·모듈은 `ST.getItem`·`ST.setItem` 을 받는다). 도우미로 열면 `<out>/.hd-canvas.json` 이 진실 원천이고 브라우저 저장소는 캐시: 시작 때 `window.__hdState`(동기) — 파일이 있으면 파일이 이기고 캐시를 덮음, 파일이 없고 브라우저에 값이 있으면 한 번 올림(rev 0 → 1). 쓰기는 300ms 모아 바뀐 키만 `PUT /api/state`, 닫을 때(`pagehide`) 마저 보냄. 파일에 닿았다고 확인 못 한 이름은 쓰기 대기 표시(`hd-unsent:<hash>` = `{base: rev, names}`, 브라우저 저장소)로 남기고 답·409 때 고치거나 지운다 — 300ms 안에 새로고침해 닫을 때 보낸 것이 새 페이지 GET 보다 늦게 닿거나 못 닿아도, 시작 때 파일 rev 가 `base` 와 같으면 그 이름의 브라우저 값이 이기고 다시 올린다(rev 가 다르면 파일이 이기고, 값이 다르면 `[hd]` 경고). 409(다른 곳에서 rev 가 오름 — `hd reply`·`claim` 은 늘 올린다, #269) = `save-merge`(Model) `resolve(보낸 이름, base = 마지막으로 안 서버 상태, 내 상태, 409 답의 state)`: 보낸 이름이 서버에서 안 바뀌었으면(메모는 id 마다 칸끼리 — 내가 고친 칸 + 서버의 답, 둘 다 늘린 `replies` 는 이어 붙임) 서버의 나머지를 받고 내 값을 지켜 새 rev 로 한 번 다시 보낸다 — 받은 `notes`·`note-seq`·`busy`(`stateFile.LIVE`) 는 제자리에서(`onExternal`), 그 밖이 바뀌었으면 다시 보낸 뒤 다시 불러오기. 둘 다 바꾼 이름이 있거나 다시 보낸 것도 409 면 이번 변경을 버리고 토스트 "다른 곳에서 바뀌어 다시 불러왔어요 — 잃은 변경: 카드 자리, 메모"(`[hd]` 경고) 뒤 다시 불러오기. file://·토큰 없음·깨진 스냅숏(`[hd]` 경고) = 브라우저 저장소 그대로. 전역 설정 키(`hd-dock`·`hd-pop`·`hd-canvas-prefs`·`hd-themes`…)는 파일로 가지 않는다
- 묻기·크기(#273): 2초 묻기는 `GET /api/state?since=<rev>` — 도우미가 `{rev, unchanged:true}` 로 답하면 아무것도 하지 않는다(본문 있는 옛 답도 그대로 받는다). PUT 이 413 이면 도우미의 `{error}` 글을 토스트로 한 번(성공할 때까지 다시 띄우지 않음), 다음 변경까지 다시 보내지 않고(묻기도) 보관을 바로 해 본다
- 완료 메모 보관(#273): `archive`(Model) `pickArchive(notes, now)` = 완료(`annotation.status` done) 중 마지막 답 `at` 이 30일 넘은 것 + 완료가 200개를 넘으면 가장 오래 전에 끝난 것부터(시각 모름 = 가장 오래됨) 넘친 것. 보내기 전·작업 중·결정 필요·일부 반영·id 없는 메모는 고르지 않는다. 쓰는 탭이 열 때와 그 뒤 한 시간에 한 번 `POST /api/archive {notes}`(→ `<out>/.hd-notes-archive.jsonl`), `{ok:true}` 일 때만 `without`(보낸 그대로인 메모만)으로 notes 에서 빼 한 번 저장 + `onExternal(['notes'])`. 실패는 `[hd]` 경고만(다음 시간에 다시). 보관은 됐는데 빼는 저장이 실패하면 다음 보관 때 같은 메모가 한 번 더 간다(보관 파일에 겹칠 수 있음)
- 두 탭(#274): `BroadcastChannel('hd:' + hash)` — 규칙 `stateFile.tab`(Model): 새 탭이 `hello`, 쓰는 탭만 `here` 로 답 → 답을 받은 탭은 읽기만(150ms 안에 답이 없으면 쓰는 탭 + `here` 알림, 동시에 시작했으면 먼저 연 탭이 이김). 읽기만인 탭은 PUT·닫을 때 보내기·보관·쓰기 대기 표시를 하지 않고(묻기는 그대로) 프로젝트 키 쓰기를 버린다(토스트 한 번). 위쪽 `#hd-tab-lock` "다른 탭에서 열려 있어요 — 여기서 편집하기": 누르면 그 탭이 쓰고(`take`) 다른 탭이 읽기만, 버린 쓰기가 있었으면 파일 상태로 다시 불러온다. 쓰는 탭이 새로고침하면 읽기만인 탭은 답하지 않으니 계속 쓰는 탭
- 이름 목록 지킴(#277, `test_canvas_unit_save_merge.py`): `history.TRACK` ⊆ `stateFile.NAMES` · `stateFile.LIVE` ⊆ `NAMES` · 템플릿 `adoptState` 가 `NAMES` − {edit-log, busy, note-seq} 를 모두 `has('…')` 로 다룬다 — 이름을 더하면 셋을 같이 고친다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/state-file.js` · `save-merge.js` · `archive.js` · `view-state-sync.js`(보관 · 두 탭 · 프로젝트별 키 = 상태 파일 · 캐시 · 409 · 쓰기 대기 표시 · 살아 있는 새로 받기) · `helper.py` `/api/state` · 셸 `adoptExternal` | `unit or helper or notes` |
