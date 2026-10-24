# 판의 선 길 (route · view-lines)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 판의 선이 어디로 지나는지(task 38)의 규칙만.

## 규칙

- 길은 `route.plan(boxes, pairs, o)`(Model, 순수) 하나가 정한다 — 쪽 고르기·꺾는 곳·막힘 검사·나란한 줄. `view-lines` 는 카드 상자를 재서 넘기고 받은 `d` 를 쓰기만 한다
- 쪽은 DOM 줄(`.flow`)이 아니라 지금 상자 자리로: 세로 범위가 겹치면 마주 보는 왼·오른쪽(겹친 범위 가운데에서 곧게), 가로 범위가 겹치면 위·아래, 둘 다 아니면 틈이 넓은 축의 직각선(꺾임 ≤2, 틈 가운데에서 꺾음). 줄 색만 DOM 줄을 쓴다
- 돌아가기는 막혔을 때만: 곧은 길(비껴 선 상자면 다른 축도)이 다른 카드 상자(8px 넓힘)를 지나면 줄 위로 띄운 길(위 → 가로 → 아래로 대상 위), 그것도 막히면 왼쪽 통로(`min(LEFT, 가장 왼쪽 카드) − 56 − 22·lane`). `render()` 는 통로를 썼을 때만 그 x 를 돌려준다(아니면 `LEFT`)
- 나란한 줄(lane)은 앞 선과 같은 줄 위에서 실제로 겹칠 때만 올린다(출발 순서로 띄우지 않음) — lane 마다 ±14px(끝점·꺾는 곳 함께)
- 태그: 왼·오른쪽으로 떠나는 선은 떠나는 점 옆, 위·아래로 떠나는 선은 카드 오른쪽 틈의 위·아래 끝(줄 머리글에 얹히지 않게) — 같은 카드·같은 쪽이면 44px 씩 쌓음
- 카드 끌기(셸이 `.card.moving` 을 단 동안): 첫 프레임에 상자·쌍 목록을 한 번 재 두고, 다음 프레임부터는 DOM 자리 읽기 없이 움직인 카드의 `style.left/top` 만으로 그 카드에 닿은 선의 `d`·태그 자리만 쓴다(`plan` 의 `only`·`prev`). 선을 숨겼으면 끄는 동안 길 찾기·쓰기 없음. 놓으면(`.moving` 없음) 전부 다시
- 선 svg(`#ar`)는 `will-change: transform` 으로 제 층(view-lines 가 mount 때 단다)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/route.js`(`plan`·`route`·`sides`) | `unit or flow or links` — 규칙은 `tests/test_canvas_unit_route.py` |
| `modules/view-lines.js`(재기·끌기 프레임·태그 자리) | `unit or flow or links or tools` |
