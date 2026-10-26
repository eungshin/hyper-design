# 기록 시간줄 (history · view-history)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(task 33).

## 규칙

- `history`(ViewModel)·`view-history`(View) — 기록 패널(`#hlist`, 도크 패널 `history`)과 되돌리기·다시 하기(Ctrl+Z · Ctrl+Shift+Z · 위쪽 ↶↷)는 시간줄 하나(E2·E8). 셸은 한 일 뒤 같은 차례에 `record({label, undo(), redo(), status?})` 를 부른다.
- **줄** = `{label, status, at, op?, d?, cut?, old?}` — status 화면에만·반영 대기·AI에 보냄·파일에 씀. `op` 는 이번 세션의 되돌리기 함수(있으면 이것을 쓴다 — 세션 안 되돌리기는 그대로). `d` 는 상태 차이: 되돌릴 이름(`TRACK` = `notes`·`card-pos`·`link-names`·`hidden`·`locked`·`folders`·`card-size`(task 46); `edit-log`·`busy`·`note-seq` 는 뺌)마다 항목 단위 `[전, 후]` — 객체는 키마다, 메모처럼 id 가진 배열은 id 마다(자리 포함), 숨김·잠금 같은 글자 배열은 있음/없음, 그 밖은 통째로.
- **차이 잡기**: `view-history` 가 기준 상태(base)를 들고, `record` 때 지금 상태와의 차이를 그 줄의 `d` 로 둔다. 셸의 `ST.setItem`/`removeItem` 은 쓸 때마다 `HI.wrote` 를 부르고, base 는 그 차례가 끝난 뒤(setTimeout 0) 다시 읽는다 — 기록 없이 바뀐 것(AI 답·번호 매기기·메모 쓰기)이 다음 줄에 섞이지 않는다. 한 일과 그 `record` 는 같은 차례여야 한다.
- **줄 누르기(포토샵)**: 줄 = 그 줄 바로 뒤 상태, 아래 줄은 흐리게(다시 하기 — 새 일을 하면 버림), 흐린 줄 누르기 = 거기까지 다시 하기, `시작` = 아무것도 안 한 상태. 줄은 `tabindex=0`, Enter·Space = 누르기. 지난 세션 줄은 `d` 를 `track.write` 로 상태 키(`ST`, 상태 주인 그대로)에 되쓰고 `adopt(이름들)` → 셸 `adoptState` 가 주인마다 다시 읽게 한다(카드 자리 `CP.reload` · hidden·locked·linkNames `LF` · folders · 메모 = `adoptExternal`). op 줄과 섞이면 op 를 부르기 전에 먼저 adopt.
- **잠금**(`lock` = 아래 줄 중 마지막의 다음 — 그 앞으로는 못 간다): 보낸 자리(`sent` → 그 자리 줄에 `cut:'sent'`)·파일에 쓴 자리(`applied` → `cut:'file'`)와 그 앞 · 지난 세션의 파일에 쓴 줄(되살리기 stamp 를 남기지 않음) · 지난 세션의 `d` 없는 줄(선 색·테마 같은 화면 설정 — `live`) · 크기 한도로 `d` 를 잃은 줄(`old`) · 깨진 `d`(`[hd]` 경고). 잠긴 줄을 누르거나 Ctrl+Z 가 막히면 까닭 토스트(`REASON`: 보낸·파일에 쓴·너무 오래된·다시 열기 전 화면 설정 일) — 조용히 무시하지 않는다. 경계선 `.hbound` 도 같은 까닭.
- **남기기**: `hd-edit-log:` 키(상태 파일 `edit-log`)에 해 둔 줄만(되돌린 줄은 버림) 최근 `KEEP`=200 줄, `d` 는 새것부터 합쳐 `MAX_BYTES`≈1 MB 까지 — 넘으면 옛 줄부터 `d` 를 버리고 `old`(잠김). 50단계 제한은 없앴다(남긴 줄은 모두 오간다).

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/history.js`(+ `tests/test_canvas_unit_history.py`) · `view-history.js` · 셸 `adoptState`·`view-layer-flags` 의 `loadHidden`·`loadLocked`·`loadLinkNames`·`ST` 쓰기 알림 | `unit or tools or notes` |
