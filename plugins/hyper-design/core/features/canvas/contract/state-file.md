# 프로젝트 상태 파일 (state-file · view-state-sync)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `state-file`(Model)·`save-merge`(Model)·`view-state-sync`(View) — 프로젝트 상태 파일(#228): 프로젝트별 키(`hd-notes:`·`hd-card-pos:`·`hd-edit-log:`·`hd-link-names:`·`hd-hidden:`·`hd-locked:`·`hd-folders:`·`hd-busy:`·`hd-note-seq:`, 모두 `hashStr(KEYPATH)`)의 읽기·쓰기 주인은 `view-state-sync` 하나(셸·모듈은 `ST.getItem`·`ST.setItem` 을 받는다). 도우미로 열면 `<out>/.hd-canvas.json` 이 진실 원천이고 브라우저 저장소는 캐시: 시작 때 `window.__hdState`(동기) — 파일이 있으면 파일이 이기고 캐시를 덮음, 파일이 없고 브라우저에 값이 있으면 한 번 올림(rev 0 → 1). 쓰기는 300ms 모아 바뀐 키만 `PUT /api/state`, 닫을 때(`pagehide`) 마저 보냄. 파일에 닿았다고 확인 못 한 이름은 쓰기 대기 표시(`hd-unsent:<hash>` = `{base: rev, names}`, 브라우저 저장소)로 남기고 답·409 때 고치거나 지운다 — 300ms 안에 새로고침해 닫을 때 보낸 것이 새 페이지 GET 보다 늦게 닿거나 못 닿아도, 시작 때 파일 rev 가 `base` 와 같으면 그 이름의 브라우저 값이 이기고 다시 올린다(rev 가 다르면 파일이 이기고, 값이 다르면 `[hd]` 경고). 409(다른 곳에서 rev 가 오름 — `hd reply`·`claim` 은 늘 올린다, #269) = `save-merge`(Model) `resolve(보낸 이름, base = 마지막으로 안 서버 상태, 내 상태, 409 답의 state)`: 보낸 이름이 서버에서 안 바뀌었으면(메모는 id 마다 칸끼리 — 내가 고친 칸 + 서버의 답, 둘 다 늘린 `replies` 는 이어 붙임) 서버의 나머지를 받고 내 값을 지켜 새 rev 로 한 번 다시 보낸다 — 받은 `notes`·`note-seq`·`busy`(`stateFile.LIVE`) 는 제자리에서(`onExternal`), 그 밖이 바뀌었으면 다시 보낸 뒤 다시 불러오기. 둘 다 바꾼 이름이 있거나 다시 보낸 것도 409 면 이번 변경을 버리고 토스트 "다른 곳에서 바뀌어 다시 불러왔어요 — 잃은 변경: 카드 자리, 메모"(`[hd]` 경고) 뒤 다시 불러오기. file://·토큰 없음·깨진 스냅숏(`[hd]` 경고) = 브라우저 저장소 그대로. 전역 설정 키(`hd-dock`·`hd-pop`·`hd-canvas-prefs`·`hd-themes`…)는 파일로 가지 않는다
- 이름 목록 지킴(#277, `test_canvas_unit_save_merge.py`): `history.TRACK` ⊆ `stateFile.NAMES` · `stateFile.LIVE` ⊆ `NAMES` · 템플릿 `adoptState` 가 `NAMES` − {edit-log, busy, note-seq} 를 모두 `has('…')` 로 다룬다 — 이름을 더하면 셋을 같이 고친다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/state-file.js` · `save-merge.js` · `view-state-sync.js`(프로젝트별 키 = 상태 파일 · 캐시 · 409 · 쓰기 대기 표시 · 살아 있는 새로 받기) · `helper.py` `/api/state` · 셸 `adoptExternal` | `unit or helper or notes` |
