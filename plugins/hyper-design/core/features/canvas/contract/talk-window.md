# 대화 창 하나 (talk-window · view-talk-window, R53)

`../contract.md` 의 책임 게이트(오류 탐지 포함)·테스트 층을 따른다. 근거: `tasks/r53-talk-window-brief.md`, 승인 시안 `Temp/claude/r53-mockup/*.png`.

## 모듈 (맡은 일 · 가진 상태 · 받는 것 · 내보내는 것)

| 모듈 | 층 | |
|---|---|---|
| `modules/talk-window.js` | Model | 접힘↔펼침(`toggle`) · 판 끝 붙기 판정(`snap` — 누른 x 가 판 왼쪽·오른쪽 끝 `SNAP` 40px 안, 도크 위 포함) · 붙은 폭(`width` 320–560, 기본 360) · 붙기/떼기 의도(`dock` · `undock`) · 도크가 그리지 않을 패널(`skip`) · 펼친 창 기본 자리(`box0` 판 아래 가운데 440×640, 아래 12) · 지금 자리(`box`). 상태 없음. `HD.talkWindow` |
| `modules/view-talk-window.js` | View · `HD.feature('talkWindow', {needs: ['$','warn']})` | `#hdtalk` 틀: 머리 줄 · 기록 칸(`#pTalk` 를 옮겨 담음) · 입력창 칸(의도 `hd-composer {host}` 로 `#hdchat` 을 넣음) · 끌기·크기·미리보기. 상태 = 끄는 중인 것(저장 안 함) → `{layout(), place()}` |
| `modules/dock.js` | ViewModel | 자리의 진실: 대화(talk)가 왼쪽 묶음 = 왼쪽에 붙음 · 오른쪽 묶음 = 오른쪽 · 떠 있는 창 = 떠 있음 · `talk {mode, auto}` = 떠 있을 때 접힘/펼침 · 펼친 창 자리를 골랐나. 의도 `talk{mode?, auto?}` |
| `modules/pop-place.js` | Model | 떠 있는 창 자리 맞추기 `clamp(p, vw, vh, min?)` — 메모 창과 같은 함수 하나(R58), 대화 창은 `min` = `HD.talkWindow.MIN` 320×240 |
| 셸 | — | `#hdtalk`(도크 패널 `talk` 자리 — `#dkhold` 안) · `hidden(st)` 에 `HD.talkWindow.skip(st)` · `onLayout` → `TW.layout()` · ctx `dock{state, dispatch(a, quiet), absent, render}` |

## 규칙

- 창 하나 = 기록(위) + 입력창(아래). `view-chat`·`view-chat-log` 는 자기 창을 모른다 — 기록은 `#pTalk` 에 그리고, 입력창은 `hd-composer` 로 받은 칸에 들어간다
- 접힘(떠 있음) = 입력창만, 판(`#screens`) 아래 가운데 — 예전 대화창 자리 규칙 그대로(폭 min(640, 판−32), 탭 바 `data-need` 만큼 줄임(최소 360), 그래도 겹치면 탭 위로) + 위 끝 손잡이 알약 + 오른쪽 위 펼치기(작업 중인 턴 `#pTalk .tk-turn[data-state=running]` 이 있으면 점). 토스트는 접힌 창 위(`--hd-chat-top`)
- 펼침(떠 있음) = 머리 줄 36px(손잡이 · 대화 · 받는 곳 이름 흐리게(`#aichip` 비춤) · 왼쪽에 붙이기 · 접기 — 닫기 없음) + 기록 + 입력창, 둥근 창, 머리 줄 끌어 옮기기 · 오른쪽 아래 모서리·위 끝 크기. 자리는 도크 떠 있는 창 칸(`#dklayer`) 기준, `popPlace.clamp` 로 판 안. 자리를 고르기 전(`auto`)은 판 아래 가운데
- 붙음 = 도크 높이 전체, 늘 펼침, 머리 줄 = 떼어 띄우기 · 접기(= 떠 있는 접힌 창). 혼자 있는 묶음이면 도크 탭 줄을 감추고 창 머리 줄을 쓴다. 왼쪽에 붙으면 왼쪽 도크 폭 = `width(lw)`(기본 360, 320 밑으로 가지 않음) · 오른쪽은 오른쪽 도크 마지막 묶음(오른쪽 폭은 다른 패널과 같이 쓰니 바꾸지 않음)
- 끌기: 머리 줄(접힘이면 알약)을 끌면 창이 따라온다(끄는 동안도 `clamp`). 누른 x 가 판 끝 40px 안이면 그 쪽 붙을 자리 미리보기(왼쪽 = `#ldock.empty` 를 붙을 폭으로 · 오른쪽 = `#dock` 테) + `놓으면 왼쪽에 붙어요`/`놓으면 오른쪽에 붙어요`, 놓으면 붙는다. 붙은 창 머리 줄을 끌면 바로 떨어져 펼친 창으로 따라온다. 접힌 창은 끝이 아닌 곳에 놓으면 제자리. 알약 누르기 = 펼치기
- 숨기기 = 창 메뉴 `대화창` 한 줄(도크 `chat` 칸, 붙은 창도 숨고 그 도크 자리도 빠짐) — 창 메뉴에 대화 패널 줄은 없다. 대화는 닫힌 패널이 되지 않는다(탭 × = 숨김 + 떠 있는 접힌 창)
- 크게 보기(모달)가 열려 있는 동안은 어디에 있든 접힌 창으로 덮개 위에 뜬다(크게 보기 칩·`sizeModal` 은 그대로), 닫으면 제자리
- 도우미 없음(file://, 도크 `absent` talk) = 기록이 없으니 접힌 창만(펼치기·알약·끌기 없음), 저장 배치는 그대로
- 처음(기본 배치) = 왼쪽에 붙은 360px(예전 기본 자리와 같음). 예전 저장 상태: 닫아 둔 대화 = 떠 있는 접힌 창 · `talk` 칸이 없고 왼쪽 폭이 예전 기본 280 이면 360
- 좁은 창: 입력창 도구 줄이 440px 이하(창 폭 ~460 아래)이면 모델 이름 글을 감춘다(`view-agent-info` 컨테이너 규칙 그대로)
- 오류 탐지: `#hdtalk` 없음 = `[hd]` + 기능 빠짐(입력창은 혼자 판 아래) · `#pTalk` 없음 = `[hd]` + 접힌 창만 · `#hdchat` 없음·`hd-composer` 를 받지 않음 = `[hd]` · ctx.dock 없음 = `[hd]` + 접힌 창만. 깨진 `talk` 저장값 = 접힘·auto

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `talk-window.js` · `dock.js` talk 칸 · `pop-place.js` clamp | `unit`(test_canvas_unit_talk_window.py · test_canvas_unit_dock_left.py · test_canvas_unit_pop_place.py) |
| `view-talk-window.js` · 셸 `#hdtalk`·`hidden`·`onLayout`·ctx `dock` | `unit or chat or dock or menu --surface board`(브라우저 test_canvas_chat_log.py · test_canvas_chat.py) |
