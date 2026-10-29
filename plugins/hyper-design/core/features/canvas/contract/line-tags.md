# 선 태그 (line-tags · view-lines 태그 · 목록 창, R46)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 판의 선 태그 하나하나가 무엇을 말하고 어디에 붙는지만.

## 규칙

- 선 하나(쌍마다 하나, E20) · 방향 하나 = 태그 하나. 글(`HD.lineTags.text`, Model): 이름 붙임 → 이름 · 트리거 하나 → 그 버튼 글 · 둘 이상 → `<첫 버튼 글> 외 <N>`(N = 나머지 트리거 수, 같은 글 버튼도 하나씩 — 예전엔 앞 두 글만 `·` 로 잇고 셋째부터 말없이 사라졌다) · 글 없음 → 반영 대기면 '반영 대기'. 트리거 수는 `graph.overview` 의 `n.ab`·`n.ba`(끊기 대기는 뺀 수)
- 자리(`HD.lineTags.seat`, Model, 화면 px): 제 선이 그 태그 쪽 카드를 떠나는 점에서 시작해 선 옆에 붙는다(가로 마디 아래 · 세로 마디 오른쪽, 선에서 2px — 선을 가리지 않음). 앞 태그와 겹치면(3px 틈) 제 선을 따라 4px 씩 바깥으로, 그다음 반대 옆, 그다음 선 위 가운데. 다른 선으로 건너가지도, 카드 옆 목록처럼 쌓이지도 않는다
- 한도: 선 길이 × 0.45 와 240px 중 작은 것(짧은 선도 시작 자리 한 칸). 그 안에 빈 자리가 없으면 겹친 채 둔다(free:false) — 멀리 밀어 선에서 떨어뜨리지 않는다. 떠 있는 막대(`#selbar`·`#elbar`·`#tools`)와 고른 카드의 펼친 글(`.cbody`)은 늘 피한다(셸 `ctx.avoid`)(빈 자리가 없을 때도 그것만 피한 첫 자리 · 그래도 없으면 태그가 그 위 — z 7)
- 보이는 태그(고른·올린 카드의 것)만 잰다: `mark()` 뒤 · 판 배율이 멈춘 뒤(`hd-label-scale`) · 끄는 프레임(크기·판 자리는 지난 값). 숨은 태그는 떠나는 점(기본 자리)
- 목록 창 `#ltpop`(View, view-lines): 트리거가 둘 이상이거나 이름 붙인 태그 — 태그 또는 그 선에 올리면 태그 옆(`HD.popSide.beside`: 태그 옆 → 판 칸 → 창)에 머리(번호 · 도착 · 버튼 N개) + 트리거마다 한 줄(버튼 글). 줄에 올리면 화면 안 그 버튼 표시만 진하게(`ctx.hilite` → `view-links.hilite` → `hd-links-paint` 의 `hi`). 벗어나면 220ms 뒤 닫힘 · Esc. 트리거 하나뿐인 태그는 창 없이 태그에 올리면 그 버튼 표시만 진하게
- 트리거 목록은 고른 화면이면 화면 안 링크(`view-links.triggers` — 경로가 있어 표시를 진하게 할 수 있다), 아니면 판 데이터의 버튼 글. 화면 안에 없는 트리거를 진하게 하라면 `[hd]` 경고 한 줄 뒤 무시

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/line-tags.js` · `graph.overview` 의 `n` | `-m unit -k line_tags`(`tests/test_canvas_unit_line_tags.py`) |
| `view-lines.js` 태그·목록 창 · `view-links.js` `triggers`·`hilite` · `palette.js` `hi` · `shell.css` R46 블록 | `unit or flow or links or tools` `--surface board` — 화면은 `tests/test_canvas_line_tags.py` |
