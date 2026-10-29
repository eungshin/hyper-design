# 정보 카드 (info-card · R47 phase B)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 설계 = `tasks/r47-info-card-brief.md`(데이터 계약은 main 세션만 바꾼다). 연결 자체(`board-links`)는 `board-links.md`(phase A).

화면이나 줄(묶음)에 이어진 판 메모 사슬 = 그 화면의 **정보 카드**: AI 요청마다 저절로 따라가는 작은 CLAUDE.md.

## 의존 방향

`board-notes`(메모) ← `board-links`(연결, 메모 id 는 글자로만) ← `info-card`(순수, 둘을 그냥 데이터로 읽음) ← 보내기·레이어·CLI(데이터를 넘겨 받은 결과만 씀).
`edits.js` 는 메모·연결을 모른다 — `request(…, context)` 의 제공자 `context(screenId) → 글` 만 받는다. `chat.js`·`view-chat.js` 는 그대로(대화창도 `ctx.sendNotes` → `view-send.send` → 같은 `request` 라 카드는 한 곳에서만 붙는다).

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/info-card.js` | Model | 모으기·글 만들기. 상태 없음. `HD.infoCard = {HEAD, MAX, PARA, DEPTH, ends, reach, collect, para, text, forScreen, counts}` |
| `modules/edits.js` | Model | `request(notes, out, sizes?, context?)` — 화면마다 첫 항목 머리 바로 아래 줄마다 세 칸 들여 한 번. 제공자가 없거나 빈 글 = 예전과 한 글자도 같은 요청문 |
| `modules/view-send.js` | View | 보낼 때 `ctx.cardData()` 를 한 번 읽어 제공자를 만든다(`HD.infoCard.forScreen`). 칸이 없으면 카드 없이, 제공자가 던지면 `[hd]` 경고 + 그 화면은 카드 없이 |
| `modules/layers.js` · `view-layers.js` | Model · View | `build(…, cards)` → 화면 줄·줄(묶음) 줄에 `card: N` · View 가 이름 뒤 '카드 N' 배지(`.ly-card`, 회색 테두리 알약). 칸이 없으면 배지 없이 |
| 셸 | — | `cardData()` → `{notes: BN.map(), links: BL.map()(view-board-links — 상태 이름 board-links 의 주인, 없으면 {}), groups: {화면 id: 카드의 줄 제목}}` 를 `viewSend`·`viewLayers` 에 `cardData` 칸으로(붙이는 줄만, `// ---- R47` 묶음) |
| `hd/hd_info_card.py` | Model(Python) | 같은 규칙 미러 + `cards_for(state, groups, screens)`. `hd notes`·`hd wait` 사람용 글에 화면마다 첫 메모 아래 네 칸 들여 한 번(`hd_sdk/text.notes(ns, cards)`), `--json` 모양은 그대로. 줄 = screens.json `group`(`Project.groups`) |

## 규칙

- 데이터 `{notes: board-notes, links: board-links, groups: {화면 id: 줄 이름}}`. `folder:<이름>` = 줄(묶음) 이름 = screens.json `screens[].group`(레이어 패널 사용자 폴더 `f<n>` 아님).
- 화면 S 의 카드 = `screen:S` 와 `folder:<S 의 줄>` 에 바로 이어진 메모(depth 1) + 거기서 메모끼리 양쪽으로 이어진 메모(depth ≤ 4, 되돌아오는 고리에 안전).
  `from` 이 메모가 아닌 줄·제자리 줄·모양이 틀린 줄·없는 메모 끝은 건너뛴다(저장은 그대로, 던지지 않음). 숨긴 메모(`hidden: true`)·빈 글 메모는 빼고 그 너머로도 가지 않는다.
- 차례: depth → 메모 `at` → id.
- 글: `유의(정보 카드):` 머리 + 메모마다 `- <첫 문단 한 줄>`(빈칸 하나로, 300자 넘으면 299자 + …). 전체 1200자 이하 — 넘으면 앞에서부터 들어가는 만큼 + `…(N개 더)` 줄. 메모가 없으면 빈 글(요청문에 아무 줄도 없음).
  1200자는 일부러 둔 한도(맥락이 불어나는 걱정) — 사용자에게 묻지 않고 올리지 않는다. 글자 수는 코드 포인트(JS `Array.from` = Python `len`).
- 레이어 배지 '카드 N': 화면 = 그 화면 카드의 메모 수(줄 카드 포함) · 줄 = 그 줄에 이어진 사슬 수. 빈 레이아웃 묶음(`@drafts`)·판 메모 묶음에는 없음.
- 공유 사례 `contract/info-card-cases.json` — JS(`tests/test_canvas_unit_info_card.py`)와 Python(같은 파일 + `hd/tests/test_hd_info_card.py`)이 둘 다 돈다. 규칙을 바꾸면 사례부터.

## 고치면 돌릴 것

`info-card.js`·공유 사례 = `-m unit` + `python -m pytest plugins/hyper-design/core/features/hd/tests/test_hd_info_card.py` · 보내기 끼우기·배지·셸 `cardData` = `-m "unit or helper or notes or tools or layers or chat" --surface board`(`test_canvas_info_card.py` 포함).
