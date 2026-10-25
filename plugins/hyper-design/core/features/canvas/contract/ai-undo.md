# AI 되돌리기 (ai-undo · view-ai-undo · 도우미 AiUndo, 48c)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 규칙

- 도우미(`ai_undo.py` `AiUndo`, 순수 규칙 `hd/helper_model.py` `ai_*`): `POST /api/claim` 이 200 이면 그 화면 파일을 `.hd-history/<stamp>/<rel>` 에 남긴다(직접 쓰기와 같은 모양). 덮개 동안 지켜보기가 그 화면이 바뀐 것을 보거나 `release` 때 마지막으로 보면 매니페스트(`by:"ai"`, after_sha)를 쓰고 처음 한 번만 기록 줄 `{seq, stamp, screen, label:"AI 반영 · <화면 제목>", at}` 을 남긴다. 덮개 하나 = 줄 하나(또 바뀌면 되살리기 기준만 새로). 안 바뀌었으면 release 때 남긴 것도 지운다.
- `GET /api/ai-writes?since=<seq>` → `{seq, writes}`(since 없음·-1 = 기준만, 숫자 아님 = 400). 기록은 도우미 메모리 — 도우미가 다시 뜨면 seq 가 줄고 캔버스는 기준만 다시 잡는다.
- 되살리기 = `POST /api/restore {stamp, keep:true, notify:true}`: keep = 되살리기 전 모습을 새 stamp 로 남기고 답에 `redo`(다시 하기에 쓸 stamp) · notify = 지켜보기 기준을 먹지 않아(absorb 안 함) 바뀐 화면으로 알린다 · 그 뒤 파일이 바뀌었으면 409(`changed-since`), 없으면 404, 빌드 실패 = 되돌리고 500.
- `ai-undo`(Model, 순수): `fresh` · `first` · `body` · `outcome` · `again(src, now)`(카드 다시 싣기 주소 — hd-mode 등 그대로, v 만 새로). unit `tests/test_canvas_unit_ai_undo.py`.
- `view-ai-undo`(View, `HD.feature('aiUndo')`, 셸·템플릿 줄 없음): 2초마다(숨은 탭 건너뜀) `GET /api/ai-writes` → 새 줄마다 `ctx.record({label, status:'file', undo, redo})`. 되돌리기·다시 하기 = 같은 줄의 `cur` stamp 로 되살리고 답의 `redo` 를 다음 `cur` 로. 성공하면 바뀐 카드를 직접 다시 싣는다(`ctx.cardEl` 의 `.phone iframe`) — view-busy 는 막 다시 실은 카드를 5초 건너뛰므로 AI 반영 직후 되돌리기를 지켜보기에만 맡기면 카드가 안 바뀐다. 실패 = 토스트(409 는 직접 쓰기와 같은 글) + 깨진 답·못 닿음은 `[hd]` 경고.

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/ai-undo.js` · `view-ai-undo.js` | `unit or helper`(+ `-k ai_undo`) |
| `session.py` `AiUndo` · `History.restore` keep/notify · `router.py` `/api/ai-writes` · `hd/helper_model.py` `ai_*` | `unit or helper` + `--surface frame` · `hd/tests/test_hd_ai_undo_model.py` · protocol |
