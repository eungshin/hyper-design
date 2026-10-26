# 보내기 길 (view-send)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(셸 섬 빼기 C6, 2026-10-26). 요청문 모양은 `send-composition.md`, 받는 곳은 `receivers.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/agents.js` `sentSay` | Model | 도우미로 보낸 한 번의 알림 글. 상태 없음. `sentSay(r{done, left, fw, res}, {agent, warn}) → {text, ms, ok}` (`delivery` 옆) |
| `modules/view-send.js` | View | 보내기 길 하나: `#nsend`(한 번만 — 더블클릭·보내는 중 막음) · 질문 고르기 `answer` · 등록부 `sendNotes` 가 같은 `send`. 도우미가 없거나 `VS.send` 가 거절되면 요청문 복사(복사된 때만 '보냄'), `#nclear` 보낸 것 완료로. 상태 = `sending`. ctx `{$, notes, save, record, toast, history{sent, applied}, sync() → VS, cover() → VB, cardEl, sizes(), agent(), out()}`. `HD.viewSend.mount(ctx) → {send(list), busy(), answer(id, choice), request(list)}` — 셸이 `LV` 뒤에 직접 붙인다(`SN`) |

## 규칙

- 보낸 요청문 = `window.__hdLastSend`(복사 길 · view-sync 의 대기열 길), 도우미 답 = `window.__hdLastHelper {apply, forward}` — 테스트가 읽으므로 이름 그대로
- 도우미 답: 바로 반영된 메모(`r.ok`)는 목록에서 빼고, 남은 것(`r.left`)은 `sent`. 남은 것이 있으면 `HI.sent()`(보낸 자리 = 기록 경계), 없으면 `HI.applied()`. 남은 화면마다 덮개(`VB.mark`, 받은 곳이 있으면 `paseo`, 아니면 `queue`)
- 받는 곳(`window.__hdAgent`)은 보낼 때마다 다시 읽는다(받는 곳 바꾸기가 열린 채로 일어난다)
- 질문에 답하기 = 질문 메모에 답 + 같은 자리 새 메모 하나를 그것만 보내기, 되돌리기 한 단계. 보내는 중이면 토스트로 거절

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/view-send.js` · `agents.js` `sentSay`(+ `tests/test_canvas_unit_send.py`) · 셸 `SN` 붙이기 | `unit or helper or notes or tools` + `--surface board` |
