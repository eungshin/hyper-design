# events — 바뀐 것 알림(서버, task 47-4a)

계약(모양·이어 받기·reset·async apply) = `tests/protocol/events.json`. 여기는 구조만.

- `events.py`(Model) — `EventBus` 세션마다 하나: `publish(type, **data)` → `{id, type, ts(ms), project, …}`, id 는 세션을 연 순간의 시계 ms 부터 +1(나중 세션 id 가 늘 큼). 고리 256 · 구독자 16 · 구독자 줄 512(넘으면 닫음). `subscribe(last)` = 다시 줄 것 + reset 이유를 한 자물쇠 안에서. 상태 주인은 이 객체 하나
- `rebuild.py` — `BuildPlan`(순수: 하나씩 · 빌드 중 쓰기는 묶음 · 앞지른 빌드는 알리지 않음 · 실패면 아직 확인 안 된 쓰기 모두 되돌림) · `Rebuilder`(일이 있을 때만 뜨는 스레드 하나, 첫 쓰기 뒤 0.1초 묶기)
- 내는 곳(세션 부품 — state_store · send_queue · note_archive · busy · ai_undo · history, 길은 `events.emit`): StateStore.put · Queue.reply → `notes.changed`(+ reply 는 `agent.reply`) · Queue.send → `request.sent` · AgentPresence → `agent.hello`·`agent.away`·`agent.progress`(contract/presence.md, 47-5a) · Archive.sweep → `notes.changed` · Busy.claim/release → `claim`/`release` · 지켜보기 → `screen.written`(by ai) · AiUndo 줄 → `ai.write` · History 쓰기 → `screen.written`(by human) · 다시 빌드 실패 → `build.failed` · Rebuilder → `build.*`
- `Builder.run` 은 빌드를 하나씩(동기 apply 와 뒤 빌드가 같은 index.html 을 동시에 쓰지 않게)
- 흐름(router.py `SessionHandler._events`): `/events`·`/api/events`, 토큰 = 머리글 또는 `?hd=`, Last-Event-ID 또는 `?since=`, 1초마다 손님 소켓을 엿봐 닫혔으면 끝(남는 스레드 없음), 15초 조용하면 `: hb`. 세션 close = 버스 close = 흐름 끝
- async apply 고르기 = 본문 `"async": true`(정확히 true). 기본 `/api/apply` 는 그대로(캔버스 낙관 편집이 `applied:[]` 로 되돌리는 것)

고치면 돌릴 것: `-m unit -k events`(test_canvas_unit_events.py) + `pytest tests/protocol`(test_protocol_events.py, slow) + `-m "unit or helper" --surface frame`
