# 생성 중 빈 틀 (placeholder · view-placeholder, S5)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만. 근거: `tasks/50-stitch/FINDINGS.md` 1-C(새 화면 착지)·4(S5)·8(애니메이션 값).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/placeholder.js` | Model | 오는 중인 화면과 그 틀의 단계(pending → arriving → done \| failed). 상태 = `{items, cleared, names}`(저장 없음). `step(s, a, at) → {s, fx}` · `look(item)` · `reveal(box, view, o)`(카메라 이동량) · `list`. `HD.placeholder` |
| `modules/view-placeholder.js` | View | 틀 그리기·듣기·카메라·겹쳐 바꾸기·토스트. `HD.feature('placeholder', {needs: ['$','$$','rowsEl','CARD','notes','store','key','toast','warn','prefs']})` → `{state(), run(a)}`. 선택 칸 `view` · `refresh` · `spot`(없으면 `[hd]` 경고 한 번 + 그 부분 없이) |
| `modules/motion.css` 8절 | — | `.hd-gen`(무채색 `--ui-line` 바탕) · `.hd-gen-sheen` 쓸기 2.5s linear ∞ + 숨쉬기 2.5s opacity .3↔.85 · 실패 모양 · 움직임 줄이기 |

## 규칙

- **언제 틀이 뜨나** — (a) 빈 레이아웃 메모(`edit=new-screen`)가 받는 곳이 있는 길로 보내짐(`request.sent` 의 `notes` 에 그 메모, `via` ≠ `queue`) — 대기열은 아무도 일하지 않으니 틀 없음. 새로고침·SSE 없는 판: 보냈고 답이 없고 덮개(`hd-busy`)가 working 이면. (b) `agent.progress`·`claim` 이 판에 카드가 없는 화면 id 를 말함. 빈 레이아웃 id 를 말하면 그 카드
- **어디** — (a) 그 빈 카드 `.phone` 안 `div.hd-gen`(카드에 `.hd-gen-on` — 점선·'빈 레이아웃' 글 숨김). (b) `#rows` 안 `div.hd-gen-slot[data-id]`(카드 크기, 자리 = `ctx.spot(id)` 또는 마지막 줄 맨 오른쪽 카드 옆 64px — `.card` 가 아니라 셸의 카드 목록에 들지 않는다)
- **글** — '만드는 중…' + 받는 곳 이름(`agent.hello`·`/api/presence`) · 파일이 쓰임/반영됨 답 = '화면을 싣는 중…' · 실패 = '만들지 못했어요' + 까닭 + [지우기]
- **카메라** — 새 틀이 판 창(여백 48) 밖이면 `reveal` 만큼만(안 들어가면 그만큼 축소) 0.5초 ease-out(0.22,1,0.36,1). 사람이 판을 누르고 있거나 1.5초 안에 누름·휠이 있었으면 옮기지 않는다, 움직이는 중 누름·휠 = 바로 멈춤. `ctx.view` 가 없으면 옮기지 않음
- **도착** — `screen.written` 이 그 화면(빈 레이아웃이면 판에 없는 새 화면)을 말하면 arriving + `ctx.refresh(새 id)`(판 데이터 다시). 카드가 판에 생김(b) · 빈 레이아웃이 승격돼 사라짐(a, 메모 `moved.from`) = done: 틀(빈 카드는 셸이 지웠으니 그 자리 그림자)이 `CROSS_MS`(0.3초) opacity 1→0, 진짜 카드 0→1(WAAPI, 남는 style 없음) → 토스트 '새 화면이 생겼어요' [보기](카드를 판 창 가운데로). 사람이 빈 레이아웃을 지움 = 조용히 없앰
- **실패** — 빈 레이아웃 답이 질문·답변·일부·다시(사람 '확인'은 아님) · 아직 파일이 안 온 틀의 `release` · 맡은 에이전트의 `agent.away` · 그 화면(빈 레이아웃이면 그 id 나 판에 없는 화면)이 든 `build.failed` · 활동 없이 `TIMEOUT_MS`(10분). 반짝임 멈춤. [지우기] = 틀만 걷음(빈 레이아웃 카드는 남아 다시 보낼 수 있음), 다시 보내기 전에는 다시 띄우지 않음. 실패한 틀에 새 보내기·진행이 오면 다시 pending
- **움직임 줄이기**(설정 `motion:false` = `body.nomotion` · `prefers-reduced-motion`) — 반짝임 없음(옅은 회색 고정), 겹쳐 바꾸기 없이 바로, 카메라는 끝 자리로 바로
- **오류 탐지** — 처리·그리기가 던지면 `[hd]` 경고 한 줄(다른 틀은 그대로). 선택 칸이 없으면 `[hd]` 경고 한 번. 깨진 덮개 상태는 `HD.busy.load` 규칙(빈 상태)

## 셸 붙이는 줄(아직 — main 이 S3 뒤에 붙인다)

`canvas_template.html` 의 `HD.mountAll({...})` 에 칸 둘(공통 칸 — 카메라·데이터 다시 받기):
```
  view: {get: function () { return {z: z, tx: tx, ty: ty}; }, set: function (nz, ntx, nty) { z = nz; tx = ntx; ty = nty; apply(); }, pane: pane},
  refresh: function (ids) { VS.refresh(ids || [], 'f' + Date.now()); },
```
없으면: 틀·실패·겹쳐 바꾸기·토스트는 되고, 카메라 이동·[보기]·AI 가 새로 만든 화면을 바로 판에 싣기(새로고침 전)는 빠진다. 브라우저 테스트는 같은 `view` 칸을 `add_init_script` 로 만든다.

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/placeholder.js` | `-m unit -k placeholder`(`test_canvas_unit_placeholder.py`) |
| `view-placeholder.js` · motion.css 8절 | `unit or motion --surface board`(`test_canvas_placeholder.py`) |
