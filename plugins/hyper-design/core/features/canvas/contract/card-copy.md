# 카드 바로 복제 (card-copy · view-card-copy · screen_copy.py, 51-6)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 근거 Figma F19(Ctrl+D = 최상위 프레임 복제, 바로 오른쪽에, 복사본이 골라짐). 바로 반영 규칙은 `instant.md`.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/card-copy.js` | Model | 복제 계획. 상태 없음. `HD.cardCopy = {SUFFIX, plan(cards [{id, title, file, app?}](판 차례), srcs) → {items: [{src, id, title, file, after}], refused: [{id, why: app\|missing}]}, freshId}` |
| `modules/view-card-copy.js` | View | 등록부 기능 `cardCopy`(needs `$ $$ toast warn cardEl rowsEl`). 상태 = 쓰기·빌드 확인 전 복사본(편집 id → 카드, 저장 안 함). 셸이 `CC = FT.cardCopy.attach({on, write, app, card, placed, removed, select})` 한 번 → `copy(ids) → bool`(false = 도우미 없음) · `reverted(ids, why)`(build.failed) |
| `screen_copy.py` | Model(서버) | `plan(screens.json, src, want, title, files) → {data, id, title, file, src_file}` · `CopyError(이유, invalid\|missing)`. `screen_edits.apply_edits` 의 `edit:'clone'`(screen = 원본, to = 새 id, value = 제목)이 부르고 파일을 복사한다 — 쓰기 한 번 = 원본 + manifest(새 파일은 before:false) = 되돌리기 한 번 |

## 규칙

- Ctrl/Cmd+D(고른 카드, 고른 요소가 없을 때 — 있으면 요소 복제) · 카드 메뉴 [복제](여러 장이면 모두). 도우미로 열면 파일째 바로 복제(AI·메모 없음), 도우미 없이(file://)·빈 레이아웃은 예전 길(흰 복제 카드 메모 — 보내면 AI 가 복제)
- 새 id = `<원본>-copy`, 쓰였으면 `-copy-2` …(화면 id · 그 폴더의 있는 파일 모두 피함 — 판은 파일을 모르므로 서버가 겹치면 거절) · 파일 = 원본과 같은 폴더 `<새 id>.html`(바이트 그대로) · 제목 = 원본 제목 + ` 복사`(옛 복제 메모와 같은 꼬리)
- 자리 = screens.json 에서 원본 바로 뒤(같은 group) → 판에서 원본 바로 오른쪽(원본의 상태 변형 `<원본>--…` 이 뒤에 이어지면 그 뒤 — 빌드 줄 차례와 같게). 원본을 옮긴 자리(card-pos)는 따라가지 않는다
- 연결: 나가는 것(branches · 파일 안 링크)은 복사본도 그대로, 들어오는 것(다른 화면 → 원본)은 원본에만
- 바로 반영: 복사본 카드를 먼저 끼우고(틀은 원본 파일을 먼저 싣고, 쓴 뒤 바뀐 카드 다시 싣기가 새 파일로) 복사본을 고른 뒤 `/api/apply` 한 번(`view-sync write` — 기록 한 줄, 되돌리기 = 되살리기 = 새 파일까지 사라짐). 거절 = 거두고 원본을 다시 고르고 토스트 `화면 복제 — 파일에 쓰지 못해 되돌렸어요: <까닭>` · 도우미에 닿지 않음·`build.failed` = 거두고 토스트
- 앱 카드(개발 서버 주소) = 거절 토스트(요청으로만) — 셸·Model·서버 모두

## 고치면 돌릴 것

`-m "unit or tools or helper or layers" --surface board` (`test_canvas_unit_card_copy` · `test_canvas_card_copy`)
