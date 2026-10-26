# 카드 아래 글 한 상자 (caption · view-caption)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `caption`(Model)·`view-caption`(View) — 카드 아래 글 한 상자(H16): 제목·설명·정책을 한 상자에서 고치고, 바뀐 칸마다 반영 대기 편집(`title`·`purpose`·`policies`) 을 한 번의 `ED.add`(view-edit-path) 로(되돌리기 한 번). 설명 비우기 = '' 편집, 제목은 비울 수 없음(편집 없음, `ctx.toast`). 칸 안내 글은 `ctx.hint`. Shift+Enter(#226): 제목 = 설명으로 넘어감(제목은 한 줄), 설명·목적 = 줄바꿈
- 정책 = 자유 메모 한 칸(task 31): 상자 안 정책은 여러 줄 글 한 칸(`[data-f="policies"]`, 글머리표 없음 — Enter·Shift+Enter = 새 줄, 그 밖은 보통 글 고치기·붙여넣기 줄바꿈 그대로). 저장 = `caption.lines`(줄마다 빈칸 정리, 빈 줄 버림) → 목록이 다르면 편집 하나 `{edit:'policies', value:[줄]}`(가운데 넣기·지우기·순서 바꾸기 모두 목록 하나). 카드 미리보기 = `caption.pending`(옛 줄 편집 `policy[i]` 위에 새 목록이 이김). 도우미 `policies` 연산 = 그 화면 `policies` 를 통째로 바꿈(글 목록 · 50줄 · 줄마다 500자, 아니면 한국어 거절) — 옛 `policy`(index, op delete) 메모도 그대로 쓴다
- 판의 카드 아래 글 접기(task 31): 고르지 않은 카드 = 제목만, 고른 카드 = 설명·정책을 카드 아래 떠 있는 읽기 보기(`.cbody`, 판 배치를 밀지 않음)로. 보일 칸 규칙 = `caption.shown({selected, blank, pending})`(Model, unit), 그리기 = `CAP.fold`(클래스 `capfold-d`·`capfold-p` + 접힌 카드에 반영 대기가 있으면 작은 표시 `.capmark` '설명·정책 고침'). 보기 상태일 뿐 저장하지 않는다(고르기가 바뀌면 바로). 빈 레이아웃(#225)은 늘 이름·목적 — 상자도 이름(한 줄)·목적(여러 줄)만 → 편집이 아니라 그 메모 안 `n.value`·`n.purpose`(`DR.edit` — view-drafts, 되돌리기 한 번), 목적은 `say.layout` 요청문의 첫째 브리프

- 판의 카드 글(셸 섬 빼기 C8, 2026-10-26): `view-caption.js` 의 `HD.viewCaption.cards(ctx)`(셸 `CT`, `NS` 뒤 직접 붙임) — 맡은 일: 원래 글(`ORIG`)의 주인(`HD.caption.origOf` — 처음 `D.rows`·쓴 뒤 `nd.rows`·카드 복제 `put` 이 같은 길, 합쳐 쌓음) · 카드 제목·설명·정책 줄 그리기(반영 대기 `.pend`·`원래:` 풍선, 정책은 바뀐 때만 다시) · 접기 · 위 상자를 그 값으로 열기(잠금 `guard`) · 카드 글 두 번 누르기. ctx `{$, $$, rowsEl, pane, notes, polHtml, space, selected, typing, guard, closeMenus, toast, placed, layoutOf, editLayout, note, add}` → `{setOrig, orig, put, cardsOf, paint, fold, open, values, commit}`. 셸은 `renderNotes`·`view-sync data`·카드 복제·판 글 ctx 에서 부르기만

- 판 글 레이어(t51-9, `board-text.md`): 이동 도구로 카드 아래 제목·설명·정책을 하나씩 고를 수 있고, Delete = `board-text.captionDelete`(제목 거절 · 설명 '' · 정책 빈 목록)를 이 상자와 같은 `commit` 으로. 상자를 닫은 뒤 그 글이 골라진 채

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/caption.js` · `view-caption.js`(+ unit `test_canvas_unit_caption_list.py` · 브라우저 `test_canvas_caption_note.py` — 카드 아래 글 한 상자: 두 번 누르기·글자 도구·카드 메뉴 이름/설명 → 바뀐 칸마다 반영 대기, 되돌리기 한 번 · 빈 레이아웃 이름·목적 = `DR.edit`(view-drafts) · 판의 접기) · `cards`(+ unit `test_canvas_unit_card_text.py`) · 셸 `CT` | `unit or tools or notes or helper` + `--surface board` |
