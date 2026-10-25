# 블록 편집 — 요소 막대 (blocks, task 49a)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/blocks.js` | Model | 요소 막대 규칙 — 단추 차례·켜짐(`bar`)·앱 카드 판정(`isApp`, `build_canvas.DEV_URL` 과 같은 규칙)·단축키(`keyAct`)·앱 카드 요청 글(`askText`)·막대 자리(`place`). 상태 없음 |
| `modules/view-blocks.js` | View | `#elbar` 하나와 그 CSS. 상태 = 지금 고른 요소 하나 `{screen, h, app, where, anchor()}`(저장하지 않음). `HD.feature('blocks', {needs: ['$','toast','esc']})` → `{show, hide(where?), place, sel, onAct(fn)}` — 편집은 셸이 `onAct` 로 준 `blockAct` 하나로만 나간다 |
| 셸 `blockAct`·`elemMemo`·`pickElAt`·`appCard`·`setMode` | — | 요소 막대·요소 메뉴의 동작을 이미 있는 편집 길(`editScreenText`·`removeElement`·`addEdits`·`showPop`)로 잇기만 한다 — 그 길이 모두 셸 것이라 모듈로 빼면 셸 함수를 ctx 로 다 넘겨야 해서 |

## 규칙

- 막대 = `[글자][지우기][복제][↑][↓] | [메모]`. 고르는 길: 판 — 고른 카드를 이동(V)으로 한 번 더 누르기(두 번 누르기 = 여전히 크게 보기) · 트리거(L)로 요소 누르기 · 크게 보기 — 이동(V) 도구로 요소 누르기
- 켜짐: 글자 = `h.textOk !== false`(안에 블록 자식이면 꺼짐, 까닭 = `edits.md` 의 글자 규칙) · 지우기·복제·↑·↓ = 화면 뿌리 아님 · ↑ = 앞 형제 있음 · ↓ = 뒤 형제 있음(형제 = script·style·template·link·meta 빼고 — `helper.py SIB_SKIP` = `palette.js SIB_SKIP`) · 메모 = 늘. 꺼진 단추를 누르면 까닭 토스트
- 앱 카드(화면 `file` = 개발 서버 주소, 또는 고른 요소에 `src`): 편집 단추는 모두 "AI에게 요청" — 메모 창에 `askText` 글(`edits.say.duplicate()` 등)을 채워 열고, 메모 대상에 `src` 가 남아 요청문에 `소스:` 줄. 파일·DOM 을 직접 고치지 않는다
- 단축키(막대가 떠 있을 때, 입력 칸 밖): Alt+↑/↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete 지우기
- 읽기만인 탭(`<html data-hd-tab="reader">`)은 막대 단추를 흐리게, 누르면 알리기만
- 막대 자리: 요소 위 왼쪽(판 = 종류 꼬리표 위), 자리가 없거나 카드 선택 막대와 겹치면 아래, 창 안으로. 판 이동·확대(`placeSelbar`)마다 다시 놓는다. 크게 보기 안 스크롤 = 막대 걷기
- 바로 쓰기: 글자·지우기·복제·옮기기는 `edits.instantOf` — 도우미가 있으면 누르는 즉시 파일에(되돌리기 = `/api/restore` 되살리기), 없으면 반영 대기(미리보기: 복제 = 점선 복사본, 옮기기 = 자리 바꿈)
- 도우미 `duplicate`: 요소 원문 `[시작, 닫는 태그 끝)` 바로 뒤에 요소 앞 공백 + 복사본(복사본과 그 자손의 `id`·`data-region` 은 뺌). `move` op `up|down`: 앞·뒤 형제와 원문 조각을 맞바꾸고 사이 글·공백은 제자리, 맨 위·맨 아래·화면 뿌리·닫는 태그 없음은 거절. 경로는 정확히 하나에 맞을 때만(task 41 그대로). 옮긴 뒤 메모 핀은 quote 로 다시 찾는다(`hd-locate`)
- 크게 보기 도구: 손(눌러 보기) · 이동(요소 고르기 → 막대) · 주석(메모) · 글자(누른 글자 고치기). 나머지는 판에서만. 오른쪽 클릭 = 판과 같은 요소 메뉴(도착을 판에서 고르는 잇기·도착 바꾸기는 뺌)
- 화면 메시지(palette.js, 기존 것은 그대로): `hd-hit` 계열 답에 `prev`·`next`·`root` · `hd-pick {on, mode:'text'|'select'}` → 누르면 `hd-dbl` · `hd-sel` · `hd-edit` 이 켜진 화면의 오른쪽 클릭 → `hd-ctx {…hd-hit 칸, x, y}` · 고르는 중 스크롤 → `hd-scroll` · `hd-pending` 항목 `{path, dup:true}` · `{path, move}`

## 아직 (49b)

- 속성 칸(이미지 src·alt·링크), 부품 교체·삽입, 끌어서 순서 바꾸기, 부모 요소 고르기(지금은 누른 자리의 누를 수 있는 요소 → 그 요소)
- 옮긴 뒤 고른 요소를 따라가기(지금은 바뀐 카드를 다시 실으면 막대가 걷힌다 — Alt+↑ 를 이어 누르려면 다시 고른다)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/blocks.js` · `view-blocks.js`(+ `tests/test_canvas_unit_blocks.py` · 브라우저 `test_canvas_blocks.py`) · `helper.py` duplicate·move | `unit or tools or modal or helper` |
