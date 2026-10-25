# 바로 반영 편집 (instant, task 49c)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만. 요소 막대 자체는 `blocks.md`, 다시 싣기는 `swap.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/reorder.js` | Model | 끌어서 순서 바꾸기 규칙 — 형제 상자 위 포인터 → 끼울 자리 `slot`(가장 가까운 형제의 앞·뒤 절반, 세로 목록 = y · 같은 줄 형제가 있으면 x — 격자도 읽는 차례) · 끼울 선 `line`(세로 목록 = 사이 가로 선, 줄 안 = 사이 세로 선, 격자 줄 끝 = 앞 칸 오른쪽) · `target` · `moves(from, slot)` → `['down'…]`·`['up'…]`·`[]`(도우미 없음 반영 대기용) · `plan(from, slot, copy)` → `null`(제자리) · `{to, writes:1}` · `{dup:true, to|null, writes:1|2}`(51-5) · `copyPath(path)`(복제 뒤 복사본 = 마지막 nth-of-type + 1). 상태 없음 |
| `modules/optimistic.js` | Model | 낙관 반영 상태 — tag 마다 `{screen, steps, done, phase: pending→kept|reverted, why}` · `outcome(res, ids)`(ids 가 모두 `applied` = 남김, 아니면 되돌림 + 도우미 까닭) · `hold(s, screen)`(그 화면에 지금 것 말고 쓰기가 더 남음 = 이번 다시 싣기 건너뜀) · `failText` · `partText`(Alt 복제는 썼지만 옮기기 못 함) · `item(note)`(편집 메모 → palette `hd-opt` 항목: 지우기 `{path, remove}`·복제·옮기기(up/down · op `to` = `{path, to}`)·글자, 그 밖 = null — 49d) |
| `modules/view-optimistic.js` | View | 셸이 `HD.viewOptimistic.mount(ctx)` 로 붙인다(view-sync 처럼 — 쓰기·반영 대기·틀 찾기가 셸 것). 상태 = 진행 중 변경 + 화면마다 '방금 낙관 반영함'(`take` 가 한 번 읽음) + 열린 글자 고치기(tag 마다). ctx = `{on, write, queue, frames, toast, picked, warn}` → `{inline, run, edit, moves, hold, take, typing}`(`edit(label, screen, note, where)` = 메모 하나를 `item` 으로 바로 반영, 못 하면 null · `moves` = `h.drop` 놓기 계획대로 move op:to 또는 복제해 옮기기) |
| `foundation/palette.js` | (화면 안) | `hd-inline`·`hd-opt`·`hd-opt-undo`·`hd-sibs`·`hd-grab` — 머리 주석 '바로 반영' |

## 규칙

- 글자 고치기(T 도구 · [글자] · 요소 메뉴 · 크게 보기 두 번 누르기): 고른 요소 **하나만** 그 카드 틀 안에서 `contenteditable`(글꼴·크기 그대로, 파란 테두리, 글 전체 선택). Enter = 저장 · Shift+Enter = 줄바꿈(`br`, 파일에는 helper 글 바꾸기 그대로 `<br>`) · Esc = 취소(원래 마디) · 밖을 누름(blur) = 저장 · 붙여 넣기 = 글만 · 한글 조합 중 Enter 는 조합 끝내기. 저장 뒤 요소 모양 = helper 가 쓸 모양(글 + br). 화면 전체를 contenteditable 로 하거나 틀 HTML 통째로 저장하지 않는다. 끝나면 틀 포커스를 캔버스로 돌린다(도구 키·Ctrl+Z).
- 글 칸(`#tedit`)은 앱 카드(Svelte — 요청 + 소스 줄, DOM 직접 고치기 없음)와 1.5초 안에 `hd-inline-on` 이 없는 화면(옛 palette.js)에만.
- 낙관 반영(글자·지우기·복제·옮기기·끌어 옮기기, 도우미가 있을 때 — 지우기는 49d): 그 화면의 실린 틀(판 카드 · 크게 보기, 교체 중 숨은 틀 빼고)에 같은 tag 로 먼저 바꾸고 기존 `/api/apply` 를 그대로 보낸다(약속·fixture 그대로, 메모의 `opt` 표시는 `wire` 가 보내지 않음). `applied` 에 있으면 남김. `applied:[]`·`failed` 면 모든 틀에서 tag 를 되돌리고 토스트 `"<이름> — 파일에 쓰지 못해 되돌렸어요: <까닭>"` — 반영 대기로 다시 넣지 않는다(셸 `pend` 가 `opt` 메모를 거름). 도우미에 닿지 않으면(네트워크) 되돌리고 반영 대기로. 도우미가 없으면 예전처럼 반영 대기(미리보기 점선).
- 끌어서 순서 바꾸기: 막대 손잡이 `[⠿]` 를 끌기 · 크게 보기 고르기(V)에서 고른 요소를 눌러 4px 넘게 끌기. 같은 부모 안만(v1). 끄는 동안 `#eldrop` 끼울 선(제자리면 흐리게) · Esc = 취소 · 놓으면 화면은 한 번에(palette `hd-opt {path, to}`), 도우미에는 **`move op:'to', to:<형제 요소 사이 자리, 0부터>` 하나**(51-5, F20) = 쓰기 하나 = 되돌리기 기록 한 줄. 자리 = `reorder.plan` 의 `to`(옮긴 뒤 자리 — 앞·뒤 틈은 제자리라 쓰지 않음), 형제 = helper `SIB_SKIP`(script·style·template·link·meta) 뺀 요소 — palette `hd-sibs`·`kids()` 도 같게(캔버스가 넣은 `data-hd-dup/pick/links` 도 뺌). 거절·`build.failed` = 화면 순서를 되돌리고 알림. 막대에서 ↑·↓ 는 빠졌고 Alt+↑/↓·요소 메뉴는 그대로(위/아래 한 칸 쓰기).
- Alt 끌기 = 복제해 놓기(51-5, F21): 끄는 중 Alt(포인터 사건의 `altKey` · Alt 누름·뗌 — 틀 안 끌기는 palette `hd-grab` 의 `alt`) = 커서 `copy` + 끼울 선 옆 파란 '+' 배지 `#eldrop-copy`, 제자리 틈도 흐리게 하지 않는다. 놓을 때 Alt 면 원본은 제자리, 복사본을 놓은 틈에(palette `hd-opt {path, dup, to}`, hit = 복사본). 도우미: `duplicate`(복사본 = 원본 바로 뒤) → 틈이 바로 뒤가 아니면 복사본(`copyPath(답의 paths[원본])`)을 `move op:to`. `apply_edits` 한 묶음은 모든 패치를 같은 원문에서 골라 복사본 경로가 없고 두 패치가 겹치므로 **쓰기 2번 = 되돌리기 기록 2줄**(바로 뒤 틈이면 1). 옮기기만 실패 = 화면도 파일처럼(복사본 = 원본 바로 뒤) + `partText`. 도우미 없으면 거절(토스트).
- 놓기 계획 전달(51-5 임시): 셸 `blockAct('reorder')` 는 아직 `OP.moves(label, id, h, dirs, where)` 만 넘기므로 view-blocks 가 `h.drop = {from, slot, copy}` 를 싣고 view-optimistic 이 읽는다(dirs 는 셸의 빈 목록 거르기를 지나게 — Alt 제자리면 `['down']`).
- 두 번 깜빡이지 않기: 쓴 뒤 다시 불러오기에서 `hold` 인 화면은 건너뛴다(끌어 옮기기 중간·뒤에 기다리는 편집). 판 카드는 `view-swap` 이 새 틀과 지금 틀의 나무가 같으면(`swap.same`) `silent` — 만지는 중이어도 알약·겹치기·바뀐 곳 강조·전/후 없이 바로(그 카드에서 글자를 고치는 중 `.card.hd-typing` 이면 아님). 크게 보기 틀은 방금 낙관 반영한 화면이면 `FT.swap.same(mframe, url)`(화면 밖 숨은 틀에 실어 견줌)이 같다고 하면 다시 싣지 않고, 고른 요소 막대는 palette `hd-opt-done` 의 hit 로 옮긴 자리에 다시 붙는다. "방금 반영됨 ✓" 칩은 AI 덮개가 걷힌 카드에만이라 바뀌지 않는다(silent done 은 `before:false`).

- 지우기(49d): 요소 막대 [지우기]·Del·요소 메뉴·글 칸 [요소 지우기] = 셸 `removeElement` 가 `OP.edit` 로 — palette 는 그 요소를 문서에서 **떼어 둔다**(숨김이 아님: 도우미가 쓴 새 파일과 나무가 같아 판 카드 교체는 `silent`, 크게 보기는 다시 싣지 않음). 거절 = 제자리로 + 토스트(복제와 같은 길).
- 다시 빌드(49d, `build_ref.py`): 풀어 둔 core 나무를 나무 sha 로 임시 폴더 캐시(`HD_BUILD_REF_CACHE`)에 두고 sha 가 같으면 git archive·풀기를 건너뛴다.

## 아직

- 끌어 옮기기는 같은 부모 안만 · 끄는 동안 틀 자동 스크롤 없음 · 판 카드에서는 손잡이로만(카드 틀은 판 끌기가 먼저)
- 해소(51-3 c755b57): 셸의 도우미 없음 길(`blockAct` `VS.on` 거짓)은 `h.drop` 을 읽어 반영 대기 메모 하나 `{edit:'move', op:'to', to}` 를 쌓고, palette `hd-pending {path, to}` 로 새 자리를 미리 보인다. Alt 복제는 도우미 없으면 거절(토스트).
- Alt 끌기 = 되돌리기 2번(복제 · 옮기기) — 한 번에 하려면 helper 에 "자리에 복제" op 가 필요(helper 주인에게 요청할 일) · Alt 끌기 뒤 막대는 복사본이 아니라 원본을 다시 고른다(쓴 뒤 따라가기가 원본 경로를 먼저 받음)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/reorder.js` · `optimistic.js` · `view-optimistic.js` · `view-blocks.js` 끌기 · palette.js 바로 반영 메시지 · 셸 `editScreenText`·`blockAct`·VS `data`·`pend` (+ `tests/test_canvas_unit_instant.py` · 브라우저 `test_canvas_instant.py`) | `unit or helper or modal or tools` + `--surface frame` |
