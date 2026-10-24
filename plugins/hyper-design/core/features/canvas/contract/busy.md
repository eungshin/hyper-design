# AI 수정 중 상태 칩 (busy · view-busy)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- **화면을 가리지 않는다**(task 37): 바쁨 표시는 카드 위 덮개가 아니라 카드 오른쪽 위의 작은 **상태 칩**(화면 틀 안, 판 위 높이 22px 이하)이다. 카드 가운데를 누르면 늘 카드가 받는다(칩은 자기 누르기만). 크게 보기가 그 화면이면 같은 칩을 제목 막대(`#modal .mbar`)에 — 화면 위 덮개는 어디에도 없다.
- `busy`(Model)·`view-busy`(View) — AI 수정 중 상태 칩(Q2b): 터미널로 넘긴 화면 카드에 칩, 상태 키 `hd-busy:`, 칩이 있는 동안만 2초마다 `/api/watch` 로 화면 파일 mtime 을 보고 바뀌면 걷고 그 카드만 다시 싣는다.
- 칩 모양 = `HD.busy.look(item) → {kind, text, title}`(순수, unit 테스트): paseo·cli = `working`(도는 표시 + "AI 수정 중" / cli 는 `label` 을 `MAX`(24)자로 줄임 + 카드 강조 테두리 `.phone[data-busy=working]`) · queue = `queued`(점 + "대기열", 테두리 없음 — 아무도 일하지 않으니 조용히). `title` = 글 전체 + 걷히는 때. 칩 안 [×](`data-act=lift`, aria-label "걷기") = 손으로 걷기. 움직임 줄이기 = 도는 표시 멈춤. 칩 CSS 는 `view-busy` 가 `<style id="hd-busy-css">` 로 넣는다(템플릿 옛 `.busy` 덮개 규칙을 덮어씀).

- `hd claim <screen> [--note …] [--by …]`(#254): 도우미 `POST /api/claim` 이 상태 파일 `state.busy` 에 `{via:'cli', since, file, mtime(그때 파일 시각), by?, note?}` 를 넣는다(rev+1, 409 재시도 없음 — `/api/reply` 와 같은 쓰는 곳 하나). `busy.js` 는 via `paseo|queue|cli` 를 받고(by·note 그대로), 칩 글 = `HD.busy.look`(전체 글 = `HD.busy.label`, cli: "<by> 수정 중 · <note>", 없으면 "AI 수정 중") + 도는 표시 + [×]. 걷힘 규칙은 같다(파일 mtime 이 기준보다 새로움) · `hd release` = `POST /api/release` 로 그 항목 지움. 캔버스는 `view-state-sync` 의 살아 있는 받기(`busy` 도 LIVE) → 셸 `adoptExternal` → `VB.adopt()`(새로고침 없음). 깨진 busy 값은 `[hd]` 경고 한 줄 후 빈 상태(Python `hd_model.busy_items` 도 같은 규칙, `BUSY_VIA` 는 unit 테스트가 JS 와 맞춰 본다)
- 화면 파일 지켜보기(#254): 도우미가 1초마다 `screens.json` 에 적힌 화면 파일(out 안만) mtime 을 보고 바뀔 때마다 seq+1(`helper.FileWatch`). `GET /api/files?since=N` → `{seq, changed:[화면]}`. `view-busy` 가 1초마다(보일 때만) 받아 `HD.busy.refresh` 로 고른 카드만 다시 싣는다: 판에 있는 카드 · 한 번씩 · 칩 카드는 빼고(걷는 길이 다시 싣고, 칩이 있으면 그 길을 바로 돈다) · 판이 방금 스스로 쓴(`VS` data → `VB.wrote`)·다시 실은 화면은 5초 동안 빼고 · 크게 보기가 그 화면이면 그것도. 처음·도우미가 다시 뜸(seq 가 작아짐) = 기준만
- 앱 카드 걷기(#272): 앱 카드(`file` = 개발 서버 주소, `HD.busy.isApp`)는 mtime 이 없어 위 규칙으로 걷히지 않는다. `view-busy` 가 `message` 를 듣고, 그 카드 iframe 이 보낸 `hd-here`(화면 id = `d.screen`, 보낸 창 = 그 카드 iframe 일 때만 — 크게 보기 등은 무시, `error` 알림 무시)를 `{type:'here', id, kind:'hmr'|'load', at: 받은 시각, first}` 로 넘긴다. 규칙 `HD.busy.shouldLift(item, event)`(순수, `test_canvas_unit_busy_lift.py`): 앱 카드만 · `at > since` · hmr(감싸개가 `vite:afterUpdate` 뒤 `hd-here {hmr:true}`) = 걷기 · load = 이 판에서 그 카드의 첫 로드(판 새로 고침·처음 보임)가 아니면 걷기. 걷어도 다시 싣지 않는다(이미 새 화면). [×] 는 그대로

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/busy.js` · `view-busy.js`(AI 수정 중 상태 칩: 터미널로 넘긴 화면 · hd claim · 화면 파일이 바뀌면 걷힘 · [걷기] · 바뀐 카드만 다시) · `helper.py` `/api/watch`·`/api/files`·`/api/claim`·`/api/release` | `unit or helper or notes` + hd 테스트(`test_hd_claim.py`) · 앱 카드 걷기는 `pytest $SK/features/app/tests` |
