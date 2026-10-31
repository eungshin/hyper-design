# 떠 있는 것 닫기 (float-stack · view-float-stack)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 10-31 사용자 요청(U1 — 메모 설명란이 Esc·다른 메뉴로 안 닫힘, 크게 보기 화면을 누른 뒤 Esc 가 안 들음)을 Figma·FigJam 관례 하나로 묶었다.

## 규칙

- **맨 위 한 층만**: Esc · 바깥 누르기 · 같은 것 다시 누르기는 떠 있는 것 중 맨 위 하나만 닫는다. 맨 위 = 쌓임 차례(z)로 더한 층 중 열린 마지막 — 크게 보기(20) · 메모 묶음 `#thread`(39) · 메모 창 `#pop`(40) · 칩 미리보기 `#mschtip`(60) · 그 위에 '메뉴'(보이는 `[role=menu]`)
- **쓰던 글을 잃지 않는다**: 사람이 글을 쓴 메모 창은 바깥 누르기·다른 메뉴로 닫히지 않는다(`keep`). Esc·×·크게 보기 닫기·탭 바꾸기로 닫히면 글을 그 대상 열쇠(고치는 메모 id · 새 메모의 화면 + 대상 경로)로 하나 맡겨 두고, 같은 대상을 다시 열면 되살린다 + 토스트 '쓰던 글을 되살렸어요'. 추가·저장으로 닫으면 맡기지 않는다
- **여는 것**(`opener`): 배지·핀(메모 묶음), 메모 도구로 누르는 카드·크게 보기 틀(메모 창)은 바깥이 아니다 — 그쪽 click 이 정한다(같은 배지 · 같은 핀 = 닫기, 다른 핀 = 그 메모로, Shift = 묶음에 더하기)
- **크게 보기**: 바깥 누르기 대상은 덮개만(위 막대·도크·도구 막대 누르기로는 닫히지 않는다 — `hit` 'ignore'). 덮개 click 은 그 누르기 때 맨 위가 크게 보기였을 때만 닫는다(`pressedTop`) — 위에 메모 창·묶음이 있으면 그것만. 판 밖 탭(Foundation·Components)으로 가면 닫힌다
- **화면 틀 안**: 크게 보기 틀 안을 눌렀거나 포커스가 그 안에 있어도 같다 — palette.js 는 넘기기만: 왼쪽 누름 `{type:'hd-press'}`(있던 것) · Esc `{type:'hd-esc'}`(입력 칸·그 자리 고치기·문서 탭 밖). 캔버스는 hd-press = 그 iframe 누르기, hd-esc = 셸 문서에 keydown Escape 로 다시 낸다(셸 Esc 사슬 그대로)
- **메뉴**(위 막대·도크 더보기·오른쪽 클릭 메뉴 등)는 주인 모듈이 지금처럼 스스로 닫는다(바꾸지 않음 — `test_existing_menus_still_close_on_esc_and_outside` 로 고정). 층 목록은 메뉴가 맨 위인지만 읽어, 그때의 Esc·누르기로 아래 층을 함께 닫지 않는다
- 칩 미리보기는 꼬리말이라 Esc 로만 닫힌다(`escOnly` — 누르기는 아래 층 몫). 칩 줄은 늘 있는 상태 표시라 닫지 않는다

## 모듈

| 모듈 | 층 | 맡은 일 · 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/float-stack.js` | Model | 닫기 판단: `top(layers)` · `esc(layers)` → 닫을 id · `press(layers)` → `{close, top}`(층 `{id, open, hit, keep}`, 아래 → 위) · 쓰던 글 자리 `stash(slot, key, text)` · `take(slot, key)`. 상태 없음. 모르는 hit = 바깥, 깨진 층은 건너뜀 |
| `modules/view-float-stack.js` | View | window 잡는 단계 pointerdown · keydown(Esc) 와 화면 틀 메시지를 받아 Model 로 판단해 그 층의 `close(why)` 를 부른다. 상태 = 층 목록 · 마지막 누르기 때 맨 위(`pressedTop`) · 이 Esc 때 맨 위. ctx `{frames() → [iframe], warn}`. `mount(ctx) → {add(layer), esc(e), pressedTop()}` |
| 층을 내는 View | View | `view-thread` `layer`('thread') · `view-memo-pop` `layer`('pop', `keep` = 쓴 글) · `view-memo-state` `layer`('chiptip', `escOnly`) — 층마다 따로 바깥 누르기 리스너를 두지 않는다 |
| 셸 | — | 붙이기만: `FL` mount(frames = `[mframe]`) · 크게 보기 층 · `TH`/`MP`/`MS.layer` 를 쌓임 차례로 `add` · Esc 사슬의 `FL.esc(e)` · 덮개 click 의 `FL.pressedTop()` · `showTab` 의 `closeModal` · `MP` ctx `feeds(t)`(메모 도구 누르기) |

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/float-stack.js` | `-m unit -k float_stack`(`test_canvas_unit_float_stack.py`) |
| `modules/view-float-stack.js` · 층 `hit`/`keep` · 셸 붙이기 · `palette.js` 의 hd-esc·hd-press | `unit or notes or modal or tools` + `test_canvas_dismiss.py` · `--surface frame` |
