# 움직이는 화면의 메모 (memo-state · view-memo-state)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 안내 단계·탭처럼 한 화면 파일 안에서 내용이 바뀌는 화면에 단 메모(10-31 사용자 요청 — 'AI 사전' 코치마크 메모 26).

## 규칙

- **메모는 단 때의 화면 상태를 함께 적는다** — `n.view = {hd, trail}`(`HD.memoState.capture`, 메모 창이 `hd-picked`·`hd-hit` 답의 `view` 에서). `hd` = 화면이 알린 지금 단계 값(아래 '화면 쪽 약속', 없으면 null) · `trail` = 이 페이지를 읽은 뒤 고르기 중이 아닌 클릭의 요소 경로(최근 30개, palette.js 가 적음). 단계 값도 클릭도 없으면(처음 실린 그대로의 화면) view 를 적지 않는다 — 그 글이 바뀌면 단계가 아니라 화면 파일이 바뀐 것이라 예전처럼 '요소를 찾을 수 없음'. view 가 없는 메모(옛 메모 포함)는 지금처럼 늘 보인다
- **같은가**(`HD.memoState.same`, 순수): 화면 답 `hd-located` 의 `view.hd` 와 항목마다 `now:{text, shown}`(path 가 요소 하나에 맞을 때의 `textOf` 글·보이나). 메모에 `hd` 가 있으면 그것만 견준다(답에 view 가 없음 = 옛 palette = 같음 · `null` = 화면이 단계를 안 알림 = 다름). 없으면 핀이 될 대상마다 보이고 글이 같아야 같음(공백 하나로, 40자 이상 스냅숏은 앞부분 맞춤 — 판 `hd-hit` 은 40자로 잘라 적는다). 답이 없으면 아직 모름 = 같음
- **다르면 화면 위 점선·번호를 그리지 않는다**(`view-pins` — 판 `.npbox/.npin`, 크게 보기 `.pin-box/.pin`). 상태가 있는 메모는 크게 보기에서 답이 오기 전 저장한 rect 로 그리지 않는다. 다른 단계의 메모는 '요소를 찾을 수 없음'(`lost`)이 아니다. palette.js 는 문서가 바뀌면(MutationObserver · transitionend, 120ms 에 한 번) 마지막 `hd-locate` 를 다시 재고 답이 달라졌을 때만 보낸다 — 단계가 바뀌면 다시 판단
- **칩 줄**(`view-memo-state`): 숨은 메모(`PN.away(id, modal)`)의 번호 칩을 화면 내용 밖에 — 판 카드 위쪽 빈 줄(왼쪽부터, `.pres` 자리 남김 · 다른 카드·제목·묶음 이름·선 태그에 겹치면 카드 아래 = `HD.memoState.side`), 크게 보기 머리 줄(제목 바로 뒤). 한 줄에 넘치면 `+N`(`row`). 칩 = 판 핀과 같은 색·숫자(decide = 강조색). 올리기·포커스 = 미리보기 `#mschtip`(자리 = 공용 `HD.popSide.beside`, 칩 줄 아래 먼저) — 떠 있는 층 'chiptip'(`float-stack.md`): 꼬리말이라 Esc 로만 닫힘(누르기는 아래 층 몫). 칩 줄은 닫지 않는다
- **칩 누르기 = 그 단계로**: `HD.memoState.plan` 차례 — `hd`: `{type:'hd-goto', tag, state}` → 화면 `window.hdGoto(state)` → `hd-gone {tag, ok, how}` · `replay`: 카드·크게 보기 iframe 을 다시 읽고(`src` 다시) `{type:'hd-replay', tag, trail}` → 경로마다 요소가 하나가 될 때까지(1.5초) `el.click()`, 사이 250ms → `hd-replayed {tag, ok, done}`. 한 가지가 끝나면 그 메모 핀이 그려질 때까지(3초) 기다려 그 메모를 고른 상태(메모 묶음이 그 메모로 열림, 판이면 핀 보임). 다 실패하면 토스트 "이 단계로 바로 갈 수 없어요 — 직접 넘겨 주세요", 칩은 그대로. 키보드로 넘긴 단계·안쪽 iframe 안 클릭은 기록에 없어 다시 하기가 실패할 수 있다(→ 토스트)
- 상태: 칩·가는 중(busy)·답 기다림은 저장하지 않는다(View). 메모 칸 `view` 의 주인 = 메모 창(만들 때 한 번), 다른 모듈은 읽기만

## 화면 쪽 약속 (화면을 만드는 쪽이 지키면 좋은 것 — 선택)

단계가 있는 화면(코치마크·마법사·탭 안내)은 둘을 지키면 메모가 글 스냅숏 대신 단계 값으로 갈리고, 칩 누르기가 화면을 다시 읽지 않고 바로 간다.

```js
document.documentElement.dataset.hdState = 'beat-' + beat;   // 단계가 바뀔 때마다(그리는 함수 안) — 글 하나, 같은 단계 = 같은 값
window.hdGoto = (state) => { /* 그 단계로 그리고 */ return true; };   // 모르는 값이면 false
```

- 값은 화면 안에서 단계마다 달라야 하고, 같은 단계는 다시 와도 같은 값(순번·이름). 사용자가 한 일(눌러 봄)에 따라 같은 단계 안에서 글만 바뀌는 것은 값을 바꾸지 않는다
- `hdGoto` 는 이전 단계를 거치지 않고 그 단계를 그릴 수 있어야 한다(필요한 앞 상태는 스스로 맞춘다). 던지거나 false = 실패 → 캔버스는 클릭 기록 다시 하기로
- 약속이 없는 화면도 된다 — 대상 요소의 보이는 글이 단계마다 다르면 글 스냅숏으로 갈린다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/memo-state.js` | `-m unit -k memo_state`(`test_canvas_unit_memo_state.py`) |
| `modules/view-memo-state.js` · `view-pins.js` 의 away · `palette.js` 의 now·trail·hd-goto·hd-replay·문서 바뀜 다시 재기 | `unit or notes or modal or tools` + `test_canvas_memo_state.py` · `--surface frame` |
