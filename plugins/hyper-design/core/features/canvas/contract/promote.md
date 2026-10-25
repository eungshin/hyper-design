# 빈 레이아웃 승격 (promote · view-promote)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(task 23, #241 · tracking R2).

## 규칙

- **때(trigger)** — 빈 레이아웃 메모(`edit=new-screen`, 화면 id `new-…`)의 마지막 AI 답('확인'은 건너뛰고 그 앞 답)이 `반영됨` 이면 `screens[0]`, `대체됨` 이면 `where` 글에 든 화면 id(글 전체가 id 이거나, 앞뒤가 다른 id 글자로 이어지지 않은 가장 앞 자리) — 그리고 그 화면이 지금 판의 데이터(빈 카드가 아닌 카드)에 있을 때만. 화면이 아직 없으면 아무것도 하지 않고, 데이터가 바뀌면 다시 본다. `다시`·`질문`·`일부`·`답변` 이 마지막이면 아직 아님. 한 화면은 빈 레이아웃 하나만 이어받는다(먼저 온 것)
- **언제 보나** — 셸이 `PR.check()` 를 시작(새로고침 뒤 `loadCardPos`·폴더 정리 다음)·파일에서 온 메모(`adoptExternal`)·화면 파일을 다시 받은 뒤(`view-sync` `data`)에 부른다. 승격하면 빈 레이아웃 메모가 더는 `new-screen` 이 아니라서 되풀이 폴링·새로고침에 한 번만 일어난다
- **승격(promote)** = 한 동작, 되돌리기 한 단계(여럿이 한꺼번에 걸리면 그 묶음이 한 단계):
  - 메모 — 빈 레이아웃 화면의 메모 전부 `screen` → 화면(번호 `no`·답 `replies` 그대로). 빈 레이아웃 메모 자신은 `edit` 를 떼어 그 화면의 메모로 남는다(답이 반영됨·대체됨이라 '완료' 묶음에). 그 메모와 사람 메모에 `moved = {from, name}` → 묶음 줄에 회색 한 줄 "빈 레이아웃 '<이름>'에서 옮겨 왔어요"(`view-thread`)
  - 선 — 빈 레이아웃으로 오는 잇기(`edit=link`, `to=new-…`)는 `to` = 화면(요청 글의 `(new-…)` 도), 나가는 잇기는 위 메모 규칙으로 출발 = 화면
  - 자리 — 화면 카드의 `.phone` 왼쪽 위가 빈 카드의 `.phone` 왼쪽 위로(옮긴 거리 `card-pos` 에 더함, 빈 카드의 옮긴 거리는 지움). 화면에 이미 옮긴 자리가 있어도 빈 레이아웃 자리가 이기고 알림이 그렇게 말한다. 카드를 잴 수 없으면(숨김) 자리는 그대로 + `[hd]` 경고
  - 폴더 — 빈 레이아웃이 든 폴더가 있으면 그 자리(차례)에 화면, 화면은 다른 폴더에서 빠짐. 없으면 폴더는 그대로
  - 숨김·잠금·연결 이름(`hidden`·`locked`·`link-names`)은 옮기지 않는다
- **알림** — "빈 레이아웃 '<이름>' 자리에 <화면 제목>이 들어왔어요"(+ 옮겨 둔 자리를 바꿨으면 "— 따로 옮겨 둔 자리 대신 빈 레이아웃 자리로") + [되돌리기]
- **되돌리기** — 메모·카드 자리·폴더를 승격 전으로(빈 카드가 돌아옴). 돌아온 빈 레이아웃 메모에는 `stay = 화면 id` — 같은 화면으로는 다시 승격하지 않는다(폴링·새로고침에도). AI 가 다른 화면으로 다시 답하면 그때는 걸린다. 다시 하기 = 같은 승격
- **층** — `promote`(Model): `promotable(notes, ids)`·`target`·`promote(state, draftId, screenId, place) → {state, undo, moved, name, memos, lines}`(입력은 고치지 않음)·`say`·`movedSay`. `view-promote`(View): 등록부 `HD.feature('promote', {needs: ['$$', 'rowsEl', 'notes', 'toast', 'record', 'title', 'warn']})` → `attach(shell)` → `{check()}`. 카드 자리·폴더의 주인은 셸이라 셸이 `FT.promote.attach({group, pos{get,set}, folders{get,set}, size?{get,set}})` 로(size = 카드 크기 맵 — 빈 레이아웃 크기를 화면으로 `artboard.carry`, task 46) 읽기/쓰기만 넘긴다(템플릿 손댄 곳: 이 attach 와 `PR.check()` 세 줄). 메모는 셸이 붙잡은 객체에 칸만 바꿔 넣는다(`annotation.adopt` 와 같은 뜻 — 되돌리기 기록 유지). 붙지 못하면 승격 없이 빈 카드가 남는다(`[hd]` + 토스트)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/promote.js` · `view-promote.js` · 셸 `PR` attach·`PR.check()` · `view-thread` 옮겨 온 줄 | `unit or notes or helper` |
