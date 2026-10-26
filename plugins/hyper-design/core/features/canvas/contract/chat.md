# 하단 대화창 v0 (chat, S1)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만. 근거: `tasks/50-stitch/FINDINGS.md` 1-C·4(S1)·7·8.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/chat.js` | Model | 칩(고른 카드 + 고른 요소 − 지운 칩)·범위·칩 줄 접기 `fold`·입력 안내 글 `placeholder`(S1c)·메모 초안·마지막 요청 상태 한 줄. 상태 없음. 메모 모양은 `memo-batch.build`(화면) · 셸 `commitPop` 과 같은 요소 메모, 상태는 `annotation.status` — 규칙을 새로 만들지 않는다. `HD.chat` |
| `modules/view-chat.js` | View | `#hdchat`(입력 카드·칩·상태 줄·숨기기 단추·받는 곳 알약)과 그 CSS. 상태 = 지운 칩 표시 · 칩 펼침(둘 다 저장 안 함) · 마지막 요청 `{text, ids, at}`(`ctx.local` 키 `hd-chat-last:<해시>`, 주인 이 파일). `HD.feature('chat', {needs: ['$','toast','esc','notes','local','store','key','title','rowsEl']})` → `{render, send(text), last}` |
| 셸 ctx `selected()`·`picked()`·`sendNotes(list)` | — | 고른 카드 id · 요소 막대의 고른 요소 `{screen, h, app}` · 메모를 더하고 위쪽 [보내기]와 같은 `SN.send`(view-send) 로 보내기(보내는 중이면 false). 셸 줄은 이 셋뿐(5d2942c) |

## 규칙

- 자리(S1b): 판 아래 가운데(도크가 있으면 그 왼쪽 가운데). 프로젝트 탭 바 `#ptabs` 는 판 아래 왼쪽이고 이 창 왼쪽 끝 앞에서 멈춘다(`HD.tabs.place`). 탭 바가 다 보이는 데 드는 폭(`#ptabs` 의 `data-need`)이 있으면 이 창은 가운데 그대로 폭만 줄여(최소 360) 자리를 준다. 그래도 겹치면(아주 좁은 창) 그때만 탭 위로 올린다. 단축키 안내 줄 `#khint` 는 지웠다. 48a 알약·카드는 판 내용이라 판을 움직이면 비킨다. 크게 보기·다른 탭·`body.bare`(Tab)·읽기만 탭에서는 숨김. 토스트는 대화창이 보일 때만 그 위로(`--hd-chat-top`)
- 모양(S1c, 근거 `tasks/52-composer/FINDINGS.md` '정한 모양'): 폭 min(640px, 100vw−32), 아래 12px. 카드 한 장 = `--ui-surface` radius 16 · 테 1px rgba(0,0,0,.08) + 옅은 그림자 · padding 8 · 세로 gap 6, 포커스면 테 .16. 위에서 아래로: 칩 줄(고른 것이 있을 때만) → 입력칸(카드 안쪽 폭 전체, 14/20, 32px 에서 줄마다 +20, 200px 뒤 스크롤 · `scrollbar-width: thin` — Windows ▲▼ 없음) → 도구 줄 28px(받는 곳 알약 왼쪽 · 보내기 28px 원 오른쪽, `aria-label` 보내기, 비면 #E4E4DF 위 `--ui-muted`). 빈 높이 82px. 입력칸과 단추를 한 줄에 두지 않는다(글 칸이 좁아지고 캐럿·스크롤바가 가운데로 감). 토큰 `--ui-surface`·`--ui-line`·`--ui-muted` 는 셸 `:root`
- 칩 접기(S1c): 칩 3개까지는 다, 넘으면 앞 2개 + `외 N개`(`.ch-more`, 누르면 펼침 — 펼쳐도 칩 줄은 2줄 높이까지, 넘으면 얇은 스크롤). 고른 요소 칩은 접지 않는다. 칩이 3개 이하가 되면 펼침은 풀린다
- 숨기기(S1b·S1c): 카드 오른쪽 위 모서리 ⌄ 단추(20px, 카드에 올리거나 포커스일 때만 보임) = 의도 `hd-chrome {part:'chat', on:false}`(document) → `view-menu` 가 `dock` 에 `chrome` 으로 보낸다. 보이기 설정의 주인은 `dock.js`(`chat` 칸, 키 `hd-dock` — 도구 막대와 같은 작업 공간 설정, `false` 만 숨김, 깨진 값 = 보임). 창 메뉴 `대화창` 체크로 다시 보인다. 몸 `no-chat` 이면 `display:none`(자리를 차지하지 않음, 탭 바가 그 자리까지 넓어짐). 작업 영역 되돌리기 = 보임. Tab(패널 모두 숨기기)은 대화창도 패널처럼 숨기고, 다시 Tab 이면 설정대로 돌아온다(설정은 바꾸지 않음). 받는 쪽이 없으면(`detail.done` 거짓) `[hd]` 경고 + 토스트
- 받는 곳 알약(S1b·S1c): 도구 줄 왼쪽 `.ch-agent`(테 없음, 26px, 점 7px — 붙으면 `--ui-ok`, 최대 180px) = 위쪽 `#aichip` 을 비춘다(MutationObserver — 글·`on`·`hidden`·title, 진실은 view-sync 가 고치는 그 칩 하나). 글: 붙어 있으면 에이전트 이름(없으면 `AI 연결됨`), 아니면 `받는 곳 없음`. 누르면 의도 `hd-agent-pick {anchor}`(document) → `view-agents` 가 같은 메뉴 `#amenu` 를 그 칩 위에 연다(고르기·자동·실패 토스트 모두 그 기능 그대로). 도우미가 없으면 `#aichip` 처럼 숨김. 받는 쪽이 없으면 `[hd]` 경고 + 토스트. 새 서버 라우트 없음
- 칩: 고른 것이 없으면 칩 줄 없음 — 범위는 입력 안내 글 `모든 화면에 대해 무엇을 바꾸거나 만들까요?`(고르면 `무엇을 바꿀까요?`) · 고른 카드마다 `[화면 이름 ×]` · 고른 요소(49a 요소 막대) `[TAG "글" ×]`(TAG = path 마지막 마디의 태그, 없으면 `kind`; 글 = `quote.exact` 또는 `text`, 20자 넘으면 …) — 그 화면 칩도 함께. × = 범위 좁히기·넓히기(요소 칩을 빼면 화면 전체, 모두 빼면 모든 화면). 고르기가 바뀌어 사라진 칩의 × 표시는 버린다(다시 고르면 다시 보임)
- Enter = 보내기 · Shift+Enter = 줄바꿈 · 한글 조합 중 Enter 무시 · Esc = 입력창에서 나가기(고른 것은 그대로)
- 보내기 = 메모 + 바로 보내기: 요소 칩마다 요소 메모(범위 칸 없음, `quote`·`src` 그대로 → 앱 카드면 요청문 `소스:` 줄) · 요소 칩이 없는 화면 칩들 = `memo-batch.build`(scope screen — 여러 장이면 같은 batch, 화면마다 `screen=… · no=N`) · 칩 없음 = 판의 첫 화면에 scope all 메모 하나. intent 는 change. 요청문 형식은 `edits.request` 그대로(바꾸지 않음). 글이 비었으면 보내지 않고 토스트. 보내는 중이면 토스트, 글은 남김. 보낸 뒤 입력창 비움, 고른 것·캔버스 그대로
- 상태 줄(카드 위 20px 한 줄, 12/16 `--ui-badge`, 말이 없으면 숨김): 마지막 요청 글 + 단계 — 보내는 중 → 보냄 / 보냄·대기열(덮개 via queue) → AI 작업 중(덮개 via paseo·cli) → 반영됨 ✓ / 답: … / 결정 필요 / 일부 반영 / 보내지 못함(20초 넘게 보내지 않은 그대로). 여러 메모면 가장 앞선 단계 + (끝난 수/전체). 메모가 목록에 없으면 바로 반영돼 빠진 것 = 반영됨. 새 줄마다 맥박 한 번(600ms scale 1→1.02→1, 움직임 줄이기면 끔), 새로고침 뒤 첫 줄은 맥박 없이
- 받는 곳·진행(47-5b, `receivers.md`): 알약 점 = 받는 에이전트 상태(접속 중 초록 · 자리 비움 회색) · 알약 ⌄ · 진행 줄 = `request.sent` via(`보냄 · <이름> (실시간|Paseo|Claude)` / 대기열) → `agent.progress` 글 → `agent.reply` `답 옴 · …` — 이 요청의 메모 id 로만(보낼 때 `/api/forward` 에 `notes`)
- 대화 패널 안(S3, `chat-log.md`): 의도 `hd-composer {host}` 를 받으면 같은 `#hdchat` 을 그 칸으로 옮긴다(`.docked` — 패널 폭, 상태 줄·⌄ 감춤, 안내 글 한 줄 말줄임, 몸 `chat-docked` = 토스트는 기본 자리). `{host:null}` = 판 아래로 돌아옴. `no-chat`(창 메뉴 `대화창`)은 판 아래 떠 있는 입력창에만. 판 아래 자리 = `#screens`(두 도크 사이) 가운데. 보낸 뒤 의도 `hd-chat-sent {text, chips, screens, notes, agent}` → 대화 패널이 서버에 남긴다
- 다시 그리기: 누르기·키 놓기·화면 메시지(요소 고르기 답) 뒤 60ms, 그리고 1초마다(메모 답·덮개는 다른 길로 바뀐다 — 47-4 SSE 가 오면 이벤트로 바꾼다)
- 오류 탐지: `#aichip` 이 없으면 `[hd]` 경고 한 번 + 받는 곳 칩 없이. ctx 칸(`selected`·`picked`·`sendNotes`)이 없으면 `[hd]` 경고 한 번 + 물러남(카드 칩 = `.card.picked`, 요소 칩 없음, 보내기 = 토스트). 마지막 요청 기록이 깨졌으면 `[hd]` 경고 + 없는 것으로. 보내기가 던지면 `[hd]` + 토스트
- 주소를 직접 부르지 않는다(47-2 에서 바뀜) — 보내기는 셸의 `sendNotes` 하나

## 아직 (S2 이후)

- S2 진행 줄·답·제안 칩(47-4 이벤트 `session.progress/text/suggest/done/failed`) — 상태 줄을 패널로 넓힌다. 그때 `line()` 의 1초 다시 그리기를 이벤트로
- 크게 보기 안 대화창, 질문 intent, 변형 N개(S8) — 대화 기록(S3)은 `chat-log.md`

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/chat.js` · `view-chat.js`(+ `tests/test_canvas_unit_chat.py` · 브라우저 `test_canvas_chat.py`) · 셸 ctx `selected`·`picked`·`sendNotes` | `unit or chat or notes` |
| 모양·칩 접기(S1c — 브라우저 `test_canvas_chat.py` 의 `composer`·`five_picked`·`progress_line`) | `unit or chat or menu or layers or tools --surface board` |
| 자리·숨기기·받는 곳 칩(S1b — `dock.js` `chat` 칸 `test_canvas_unit_chrome.py` · `view-menu` · `view-tabs` · `view-agents`) | `unit or chat or menu or tools --surface board` |
