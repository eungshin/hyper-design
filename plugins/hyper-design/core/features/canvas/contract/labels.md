# 판 이름표 화면 크기 (label-scale · view-label-scale)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 판 위 이름표가 배율과 상관없이 화면에서 같은 크기인 규칙만(R27 F01·F08).

## 규칙

- 판 이름표 = 카드 제목(`.card > .ftitle`, 11px 한 줄 #6b6b66, 카드 폭에서 말줄임) · 줄 제목(`.glabel`, 12px, 카드 바로 위) · 메모 배지(`.nbadge`, 18px 핀, 화면 오른쪽 위 안 8px) · 화면 안 메모 핀(`.npin`, 20px) · 선 태그(`.alabel`, 11px) · AI 수정 중 칩(`.busy.bchip`, 22px · 12px 글). Figma 프레임 이름·FigJam 메모 핀처럼 전체 보기에서도 읽히고 100% 에서도 화면 글보다 조용하다
- 배율 값: `view-label-scale`(View, 등록부 기능 `labelScale`)이 `#stage` 의 `data-zoom` 을 보고 `#rows` 에 `--lz = 1/z` 를 쓴다(규칙 `HD.labelScale`, Model). 확대 중엔 한 프레임에 한 번 3% 넘게 바뀔 때만, 멈춘 뒤 150ms 에 정확한 값 + document `hd-label-scale` {lz}
- 판 배치는 배율과 상관없다: 이름표는 `transform`/`scale` 로만 크기를 바꾸고 자리 상자(판 px)는 그대로 — 카드 높이(제목 자리 46px)·줄 제목 자리(145px)는 예전과 같다. 그래서 카드·줄 자리는 어느 배율에서 재도 같다(`test_canvas_labels.py`)
- 작게 볼 때(배율 < `HD.labelScale.FAR` 0.35): `#rows[data-lz-far]` — 펼친 카드 설명(`.cbody`)은 `visibility:hidden`(18px 글이 6px 아래라 읽히지 않고, 화면 px 제목을 덮는다). 크기는 남아 줄 사이 계산(`view-rows` `space`)은 배율과 상관없다. 카드 제목은 z-index 없음(펼친 설명·교체 알약이 위)
- 선 태그(F08): 고른·올린 카드의 것만 보이고(예전 그대로), 보이는 태그끼리 화면에서 겹치면 아래로 민다 — `HD.labelScale.stack`(위·왼쪽 먼저, 3px 틈) 의 화면 px 거리를 `--dy` 로. 판 배율이 멈춘 뒤에도 다시 잰다
- 화면 안 출발 버튼 표시(`palette.js` 의 `hd-links-paint`, F08): 1px 점선(선 색) + 16px 번호 — 고른 카드에만(예전 그대로, E20 A)
- AI 수정 중 칩(F12): 글 = 에이전트 이름(`hd-agent` {agent, name} 으로 모은 것) > 사람이 쓴 `by` > "AI". 날 id(agent-9·ag-fake·uuid)는 title 에만(`HD.busy.look(item, names)`). 고른 카드·이어진 카드에서도 강조 테두리가 먼저 보인다. 메모 배지가 있으면 칩은 그 왼쪽으로 비킨다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/label-scale.js` · `view-label-scale.js` · `shell.css` 의 R27 F01 블록 · `view-rows.js` 의 줄 제목 CSS | `unit or flow or helper` `--surface board` — 규칙은 `tests/test_canvas_unit_label_scale.py`, 화면 크기는 `tests/test_canvas_labels.py` |
