# 카드 아래 글 한 상자 (caption · view-caption)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `caption`(Model)·`view-caption`(View) — 카드 아래 글 한 상자(H16 · R21): 제목(한 줄 `[data-f="title"]`) + 본문(여러 줄 자유 글 한 칸 `[data-f="purpose"]`, 안내 글 '설명' 하나 — 긴 안내 줄 없음). 바뀐 칸마다 반영 대기 편집을 한 번의 `ED.add`(view-edit-path) 로(되돌리기 한 번). 제목은 비울 수 없음(편집 없음, `ctx.toast`). 글쇠: 제목 Enter·Shift+Enter = 본문으로, 본문 Enter·Shift+Enter = 줄바꿈, Esc 취소, Ctrl+Enter·밖 누르기 저장
- 본문 = `screens.json` 의 `purpose` 하나(R21): 줄바꿈·빈 줄 그대로, 다 지우면 ''. 옛 데이터의 `policies` 줄은 `caption.body(purpose, policies)` 로 본문 끝 `- 줄` 이 되어 보이고(카드·상자 모두), 본문을 고쳐 저장하면 `caption.diff` 가 `purpose` = 새 본문 + (옛 정책이 있었으면) `{edit:'policies', value: []}` 로 접는다 — 쓴 글은 사라지지 않고, 열고 그대로 닫거나 제목만 고치면 옛 데이터는 그대로. 옛 반영 대기 메모(`policy[i]`·`policies`)는 `caption.pending` 이 읽어 본문에 얹는다. 도우미 `policies` 연산(글 목록 · 50줄 · 줄마다 500자)·옛 `policy` 연산은 그대로
- 판의 카드 아래 글 접기(task 31): 고르지 않은 카드 = 제목만, 고른 카드 = 본문을 카드 아래 떠 있는 읽기 보기(`.cbody > .fdesc`, 줄바꿈 그대로, 판 배치를 밀지 않음)로. 빈 본문 = `.fdesc` 없음. 보일 칸 규칙 = `caption.shown({selected, blank, pending})`(Model, unit), 그리기 = `CAP.fold`(클래스 `capfold-d` + 접힌 카드에 반영 대기가 있으면 작은 표시 `.capmark` '설명 고침'). 보기 상태일 뿐 저장하지 않는다(고르기가 바뀌면 바로). 빈 레이아웃(#225)은 늘 이름·목적 — 상자도 이름(한 줄)·목적(여러 줄)만 → 편집이 아니라 그 메모 안 `n.value`·`n.purpose`(`DR.edit` — view-drafts, 되돌리기 한 번), 목적은 `say.layout` 요청문의 첫째 브리프

- 판의 카드 글(셸 섬 빼기 C8, 2026-10-26): `view-caption.js` 의 `HD.viewCaption.cards(ctx)`(셸 `CT`, `NS` 뒤 직접 붙임) — 맡은 일: 원래 글(`ORIG`)의 주인(`HD.caption.origOf` — 처음 `D.rows`·쓴 뒤 `nd.rows`·카드 복제 `put` 이 같은 길, 합쳐 쌓음) · 카드 제목·본문 그리기(반영 대기 `.pend`·`원래:` 풍선) · 접기 · 위 상자를 그 값으로 열기(잠금 `guard`) · 카드 글 두 번 누르기. ctx `{$, $$, rowsEl, pane, notes, space, selected, typing, guard, closeMenus, toast, placed, layoutOf, editLayout, note, add}` → `{setOrig, orig, put, cardsOf, paint, fold, open, values, commit}`. 셸은 `renderNotes`·`view-sync data`·카드 복제·판 글 ctx 에서 부르기만

- 판 글 레이어(t51-9, `board-text.md`): 이동 도구로 카드 아래 제목·본문을 하나씩 고를 수 있고, Delete = `board-text.captionDelete`(제목 거절 · 본문 = purpose '' + 옛 정책 줄 [])를 이 상자와 같은 `commit` 으로. 상자를 닫은 뒤 그 글이 골라진 채

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/caption.js` · `view-caption.js`(+ unit `test_canvas_unit_caption.py`(본문 합치기·접기) · `test_canvas_unit_caption_list.py`(옛 정책 메모) · 브라우저 `test_canvas_caption_note.py` — 카드 아래 글 한 상자: 두 번 누르기·글자 도구·카드 메뉴 이름/설명 → 바뀐 칸마다 반영 대기, 되돌리기 한 번 · 빈 레이아웃 이름·목적 = `DR.edit`(view-drafts) · 판의 접기) · `cards`(+ unit `test_canvas_unit_card_text.py`) · 셸 `CT` | `unit or tools or notes or helper` + `--surface board` |
