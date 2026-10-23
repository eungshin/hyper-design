# AI 답이 살아서 옴 · 결정 필요 · 받는 곳 없음 (task 16)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- AI 답이 살아서 옴(A2a, task 16): `view-state-sync` 가 페이지가 보이는 동안 2초마다(숨으면 10초) `GET /api/state` — 파일 `rev` 가 더 크고 보내지 않은 변경이 없으면, 바뀐 이름이 `notes`·`note-seq` 뿐일 때 제자리에서 받아 `ctx.onExternal(이름들)` → 셸 `adoptExternal`(같은 id 메모 객체에 칸만 바꿔 넣음 = `annotation.adopt`, 되돌리기 기록 유지) → `saveNotes(true)`(번호를 새로 매긴 때만 다시 씀) → 닿은 카드만 다시. 다른 이름도 바뀌었으면 지금처럼 알리고 다시 불러오기, 보내지 않은 변경이 있으면 먼저 보냄(409 = 충돌 길). 네트워크 실패 3번 연속 = 멈추고 토스트 한 번, 창 focus 에 다시. 묶음(`view-thread`): 답마다 회색 한 줄 `annotation.says`(반영됨 줄에 올리면 `tip` = 화면·캡처), 사람 답은 작게 '완료함/다시 엶' + 시각, 기다리는 질문(`annotation.question`)은 고를 것 단추 → 셸 `answerQuestion` = 질문 메모에 `{kind:'확인', by:'user', answer}`(답 검사 `OPTIONAL` — `hd_model` 과 같음) + 같은 대상 새 메모 `질문 "…" → 고른 것`(intent change)을 그것만 셸 `sendList`(위쪽 [보내기]와 같은 길)로, 되돌리기 한 단계(보내지면 보낸 자리 경계). '결정 필요'(#232, 강조색은 이것 하나): 위쪽 줄 `#decn` '결정 필요 N'(0 이면 숨김, 누르면 메모 패널을 그것만으로) · 메모 패널 `#ndec` '결정 필요만' · 그런 메모가 있는 카드 배지 `.decide`(수는 열린 메모 수). 받는 곳 없음(R4): `--paseo-agent` 없이 도우미로 열면 `#aichip` '받는 곳 없음', 보낸 뒤 토스트가 대기열 파일에만 갔다고 붙이는 법(`hd notes` · `--paseo-agent`)과 함께 말하고, 묶음 상태 말은 working 대신 '대기열'(`annotation.label`). 답 검사·상태는 `hd/tests/fixtures/replies.json` 을 JS(`test_canvas_unit_annotation.py`)와 Python 이 함께 읽는다(drift 검사)
