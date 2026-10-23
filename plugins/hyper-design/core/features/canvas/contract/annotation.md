# 메모 주석·핀 (annotation · view-pins)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `annotation`(Model)·`view-pins`(View) — 메모 주석·핀(task 11, W3C Web Annotation 처럼 대상 = 선택자 여럿): 메모마다 화면별로 바뀌지 않는 번호 `n.no`(만들 때 그 화면에서 지금까지 쓴 가장 큰 번호 + 1, 지워도 다시 쓰지 않음 — 키 `hd-note-seq:` = `{화면 id: 마지막 번호}`, 옛 메모는 불러올 때 화면마다 목록 차례대로 `migrate`). 대상마다 `path`·`rect` 에 `quote:{exact, prefix, suffix}`(palette.js 가 채움, 없으면 `exact = text`). 답 `n.replies`(AI: 반영됨·일부·대체됨·답변·질문 — `hd reply` #231 · 사람: 확인 = 완료, 다시 = 다시 열기, `n.sent=false`) → 상태는 저장하지 않고 계산(`status`: draft·working·decide·partial·done, `isOpen` = done 아님, `rework` = 다시 수, `validReply` = 종류별 꼭 있는 칸). 판 핀: 실린 카드의 열린 사람 메모(편집·화면 전체·빈 레이아웃 빼고) 대상 중 다시 찾은 자리(`hd-locate`)가 있는 것만, 고른·올린·막 메모를 단 카드 또는 화면이 실제의 60% 이상일 때만 보임, decide = `--ui-accent` 하나·나머지 `--ui-badge`. 핀 누르기 = 그 메모로 열린 `view-thread`(셸이 `ctx.openThread`), 묶음 줄에 올리기 = 그 핀·요소 테두리(`ctx.highlight`). 크게 보기 핀(`drawPins` → `view-pins.paint`)도 `n.no`·다시 찾은 자리. 완료한 메모는 핀·배지 수·메모 패널·보내기에서 빠지고 묶음 아래 접힌 '완료 N' 에 [다시 열기]. 메모 패널 [보낸 것 완료로] = 보낸 열린 메모에 '확인'(지우지 않음), 보낸 편집은 예전처럼 목록에서 뺌 — 되돌리기 한 단계

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/annotation.js`(번호·답·상태·답 검사) · `view-pins.js`(판·크게 보기 핀, 다시 찾기, 핀 → 묶음) · 셸 `numberNotes`·`drawPins`·[보낸 것 완료로] | `unit or notes or modal or tools` |
