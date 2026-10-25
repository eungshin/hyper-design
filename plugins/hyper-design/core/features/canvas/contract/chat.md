# 하단 대화창 v0 (chat, S1)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만. 근거: `tasks/50-stitch/FINDINGS.md` 1-C·4(S1)·7·8.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/chat.js` | Model | 칩(고른 카드 + 고른 요소 − 지운 칩)·범위·메모 초안·마지막 요청 상태 한 줄. 상태 없음. 메모 모양은 `memo-batch.build`(화면) · 셸 `commitPop` 과 같은 요소 메모, 상태는 `annotation.status` — 규칙을 새로 만들지 않는다. `HD.chat` |
| `modules/view-chat.js` | View | `#hdchat`(입력창·칩·상태 줄)과 그 CSS. 상태 = 지운 칩 표시(저장 안 함) · 마지막 요청 `{text, ids, at}`(`ctx.local` 키 `hd-chat-last:<해시>`, 주인 이 파일). `HD.feature('chat', {needs: ['$','toast','esc','notes','local','store','key','title','rowsEl']})` → `{render, send(text), last}` |
| 셸 ctx `selected()`·`picked()`·`sendNotes(list)` | — | 고른 카드 id · 요소 막대의 고른 요소 `{screen, h, app}` · 메모를 더하고 위쪽 [보내기]와 같은 `sendList` 로 보내기(보내는 중이면 false). 셸 줄은 이 셋뿐(5d2942c) |

## 규칙

- 자리: 판 아래 가운데(도크가 있으면 그 왼쪽 가운데). 아래 줄 — 도움말 `#khint`·프로젝트 탭 `#ptabs` — 과 가로로 겹치면 그 위로 올린다(그 줄들은 다른 주인 것이라 이 창만 비킨다; 창 크기·도크·탭이 바뀌면 다시 잼). 48a 알약·카드는 판 내용이라 판을 움직이면 비킨다. 크게 보기·다른 탭·`body.bare`·읽기만 탭에서는 숨김. 토스트는 대화창 위로(`--hd-chat-top`)
- 칩: 고른 것이 없으면 `[모든 화면]`(× 없음) · 고른 카드마다 `[화면 이름 ×]` · 고른 요소(49a 요소 막대) `[TAG "글" ×]`(TAG = path 마지막 마디의 태그, 없으면 `kind`; 글 = `quote.exact` 또는 `text`, 20자 넘으면 …) — 그 화면 칩도 함께. × = 범위 좁히기·넓히기(요소 칩을 빼면 화면 전체, 모두 빼면 모든 화면). 고르기가 바뀌어 사라진 칩의 × 표시는 버린다(다시 고르면 다시 보임)
- Enter = 보내기 · Shift+Enter = 줄바꿈 · 한글 조합 중 Enter 무시 · Esc = 입력창에서 나가기(고른 것은 그대로)
- 보내기 = 메모 + 바로 보내기: 요소 칩마다 요소 메모(범위 칸 없음, `quote`·`src` 그대로 → 앱 카드면 요청문 `소스:` 줄) · 요소 칩이 없는 화면 칩들 = `memo-batch.build`(scope screen — 여러 장이면 같은 batch, 화면마다 `screen=… · no=N`) · 칩 없음 = 판의 첫 화면에 scope all 메모 하나. intent 는 change. 요청문 형식은 `edits.request` 그대로(바꾸지 않음). 글이 비었으면 보내지 않고 토스트. 보내는 중이면 토스트, 글은 남김. 보낸 뒤 입력창 비움, 고른 것·캔버스 그대로
- 상태 줄(입력창 위 한 줄): 마지막 요청 글 + 단계 — 보내는 중 → 보냄 / 보냄·대기열(덮개 via queue) → AI 작업 중(덮개 via paseo·cli) → 반영됨 ✓ / 답: … / 결정 필요 / 일부 반영 / 보내지 못함(20초 넘게 보내지 않은 그대로). 여러 메모면 가장 앞선 단계 + (끝난 수/전체). 메모가 목록에 없으면 바로 반영돼 빠진 것 = 반영됨. 새 줄마다 맥박 한 번(600ms scale 1→1.02→1, 움직임 줄이기면 끔), 새로고침 뒤 첫 줄은 맥박 없이
- 다시 그리기: 누르기·키 놓기·화면 메시지(요소 고르기 답) 뒤 60ms, 그리고 1초마다(메모 답·덮개는 다른 길로 바뀐다 — 47-4 SSE 가 오면 이벤트로 바꾼다)
- 오류 탐지: ctx 칸(`selected`·`picked`·`sendNotes`)이 없으면 `[hd]` 경고 한 번 + 물러남(카드 칩 = `.card.picked`, 요소 칩 없음, 보내기 = 토스트). 마지막 요청 기록이 깨졌으면 `[hd]` 경고 + 없는 것으로. 보내기가 던지면 `[hd]` + 토스트
- 주소를 직접 부르지 않는다(47-2 에서 바뀜) — 보내기는 셸의 `sendNotes` 하나

## 아직 (S2 이후)

- S2 진행 줄·답·제안 칩(47-4 이벤트 `session.progress/text/suggest/done/failed`) — 상태 줄을 패널로 넓힌다. 그때 `line()` 의 1초 다시 그리기를 이벤트로
- 크게 보기 안 대화창, 질문 intent, 변형 N개(S8), 대화 기록(S3)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/chat.js` · `view-chat.js`(+ `tests/test_canvas_unit_chat.py` · 브라우저 `test_canvas_chat.py`) · 셸 ctx `selected`·`picked`·`sendNotes` | `unit or chat or notes` |
