# 판의 선 길 (route · view-lines)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 판의 선이 어디로 지나는지(task 38)의 규칙만.

## 규칙

- 길은 `route.plan(boxes, pairs, o)`(Model, 순수) 하나가 정한다 — 쪽 고르기·꺾는 곳·막힘 검사·나란한 줄. `view-lines` 는 카드 상자를 재서 넘기고 받은 `d` 를 쓰기만 한다
- 쪽은 DOM 줄(`.flow`)이 아니라 지금 상자 자리로: 세로 범위가 겹치면 마주 보는 왼·오른쪽(겹친 범위 가운데에서 곧게), 가로 범위가 겹치면 위·아래, 둘 다 아니면 틈이 넓은 축의 직각선(꺾임 ≤2, 틈 가운데에서 꺾음). 줄 색만 DOM 줄을 쓴다
- 돌아가기는 막혔을 때만: 곧은 길(비껴 선 상자면 다른 축도)이 다른 카드 상자(8px 넓힘)를 지나면 줄 위로 띄운 길(위 → 가로 → 아래로 대상 위), 그것도 막히면 왼쪽 통로(`min(LEFT, 가장 왼쪽 카드) − 56 − 22·lane`). `render()` 는 통로를 썼을 때만 그 x 를 돌려준다(아니면 `LEFT`)
- 나란한 줄(lane)은 앞 선과 같은 줄 위에서 실제로 겹칠 때만 올린다(출발 순서로 띄우지 않음) — lane 마다 ±14px(끝점·꺾는 곳 함께)
- 태그: 선 하나(방향 하나)에 하나, 제 선이 카드를 떠나는 점에서 선에 붙는다 — 규칙은 `line-tags.md`(R46, 예전 '카드 오른쪽 틈에 44px 씩 쌓음'은 어느 선의 태그인지 보이지 않아 뺐다)
- 카드 끌기(셸이 `.card.moving` 을 단 동안): 첫 프레임에 상자·쌍 목록을 한 번 재 두고, 다음 프레임부터는 DOM 자리 읽기 없이 움직인 카드의 `style.left/top` 만으로 그 카드에 닿은 선의 `d`·태그 자리만 쓴다(`plan` 의 `only`·`prev`). 선을 숨겼으면 끄는 동안 길 찾기·쓰기 없음. 놓으면(`.moving` 없음) 전부 다시
- 선 svg(`#ar`)는 `will-change: transform` 으로 제 층(view-lines 가 mount 때 단다)
- 화살촉(#286): 채운 marker 라 선의 `stroke-opacity` 가 닿지 않는다 — 색마다 투명도 단계(`lineTone.TONES` = base·hov·faint·full)별 marker(`hd-ln-<색>-<단계>`·`hd-lns-…`, `data-tone`)를 두고 `mark()` 가 선마다 `lineTone.tone({focusing, hover, on, em, pd})` 단계의 것을 단다(바뀐 선만). 단계 = 템플릿 선 CSS 와 같은 차례(선 CSS 를 바꾸면 `line-tone.js` 도). 선에 `opacity` 는 주지 않는다(래스터 그대로)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/route.js`(`plan`·`route`·`sides`) | `unit or flow or links` — 규칙은 `tests/test_canvas_unit_route.py` |
| `modules/view-lines.js`(재기·끌기 프레임·태그 자리·화살촉 단계) · `modules/line-tone.js` | `unit or flow or links or tools` `--surface board` — 단계 규칙은 `tests/test_canvas_unit_line_tone.py`, 태그는 `line-tags.md` |
