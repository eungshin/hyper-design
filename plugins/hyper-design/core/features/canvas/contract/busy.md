# AI 수정 중 덮개 (busy · view-busy)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `busy`(Model)·`view-busy`(View) — AI 수정 중 덮개(Q2b): 터미널로 넘긴 화면 카드에 덮개, 상태 키 `hd-busy:`, 덮개가 있는 동안만 2초마다 `/api/watch` 로 화면 파일 mtime 을 보고 바뀌면 걷고 그 카드만 다시 싣는다.

- `hd claim <screen> [--note …] [--by …]`(#254): 도우미 `POST /api/claim` 이 상태 파일 `state.busy` 에 `{via:'cli', since, file, mtime(그때 파일 시각), by?, note?}` 를 넣는다(rev+1, 409 재시도 없음 — `/api/reply` 와 같은 쓰는 곳 하나). `busy.js` 는 via `paseo|queue|cli` 를 받고(by·note 그대로), 덮개 글 = `HD.busy.label`(cli: "<by> 수정 중 · <note>", 없으면 "AI 수정 중") + 도는 표시 + [걷기]. 걷힘 규칙은 같다(파일 mtime 이 기준보다 새로움) · `hd release` = `POST /api/release` 로 그 항목 지움. 캔버스는 `view-state-sync` 의 살아 있는 받기(`busy` 도 LIVE) → 셸 `adoptExternal` → `VB.adopt()`(새로고침 없음). 깨진 busy 값은 `[hd]` 경고 한 줄 후 빈 상태(Python `hd_model.busy_items` 도 같은 규칙, `BUSY_VIA` 는 unit 테스트가 JS 와 맞춰 본다)
- 화면 파일 지켜보기(#254): 도우미가 1초마다 `screens.json` 에 적힌 화면 파일(out 안만) mtime 을 보고 바뀔 때마다 seq+1(`helper.FileWatch`). `GET /api/files?since=N` → `{seq, changed:[화면]}`. `view-busy` 가 1초마다(보일 때만) 받아 `HD.busy.refresh` 로 고른 카드만 다시 싣는다: 판에 있는 카드 · 한 번씩 · 덮개 카드는 빼고(걷는 길이 다시 싣고, 덮개가 있으면 그 길을 바로 돈다) · 판이 방금 스스로 쓴(`VS` data → `VB.wrote`)·다시 실은 화면은 5초 동안 빼고 · 크게 보기가 그 화면이면 그것도. 처음·도우미가 다시 뜸(seq 가 작아짐) = 기준만

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/busy.js` · `view-busy.js`(AI 수정 중 덮개: 터미널로 넘긴 화면 · hd claim · 화면 파일이 바뀌면 걷힘 · [걷기] · 바뀐 카드만 다시) · `helper.py` `/api/watch`·`/api/files`·`/api/claim`·`/api/release` | `unit or helper or notes` + hd 테스트(`test_hd_claim.py`) |
