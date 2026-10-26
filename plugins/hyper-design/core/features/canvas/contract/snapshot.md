# snapshot — 그림 카드 찍기(R18 1단계)

결정·단계·멈춤 기준 = `tasks/r18-snapshot-2026-10-26.md`. 1단계는 찍기 모듈만 — 판·크게 보기 동작은 그대로이고 아직 아무도 부르지 않는다.

- `snapshot.js`(Model, `HD.snapshot`) — 크기·밀도(1·2)·긴 변 4096 상한 · 찍을 수 없는 까닭(`reach`: 다른 출처·file:// = `unreachable`, 내린 카드 = `unloaded`, 실리는 중 = `loading`) · 요소 지도에 넣을 요소(`pickable` = 고르기(V) deep 과 같은 뜻: html·body·머리 요소·`data-hd-*` 빼고 보이고 카드 안에 걸친 아무 요소)와 모양(`elementMap`: palette.js 경로 + 정수 상자, 같은 경로 두 번째는 뺌, 3000개까지) · 계산된 스타일 줄이기(`styleText`: 이어받는 속성 = 부모와 다를 때, 나머지 = 태그 기본값과 다를 때, 선 굵기는 늘, 논리·입력·움직임·backdrop-filter 는 뺌) · url·@import·@font-face 읽기와 실린 글꼴만 고르기 · 판 바탕(html 없으면 body) · 한 줄 글 줄바꿈 끄기(`oneLine`) · 판정(`verdict`)
- `view-snapshot.js`(View, `HD.viewSnapshot`) — 부모 페이지에서 같은 출처 카드 iframe 문서를 읽어 복제 → 계산된 스타일·그림·글꼴을 data URL 로 넣고 → SVG foreignObject(data: 주소 — blob: 은 canvas 를 더럽힌다) → canvas → WebP(기본)/PNG. 글꼴·그림이 실리길 기다리고(5초), 걷기·경로는 8ms 마다 쉰다. 경로는 카드 palette.js 의 `__hdRules.pathOf` 그대로(두 번째 형식 없음), 그림이 나온 뒤에 채운다(`onImage` 가 먼저)
- 오류 탐지: 찍을 수 없으면 `Error.code` 로 거절(빈 그림을 내지 않음). 넣지 못한 자원(그림·글꼴·CSS·iframe·canvas·video·안쪽 스크롤·palette.js 없음)은 `missing` 줄 + `ok=false` + 콘솔 `[hd] snapshot` 한 줄, `strict` 면 거절
- 가진 상태: 주소 → data URL 저장(`clearCache`), 태그 기본 스타일(숨은 빈 iframe 하나)

고치면 돌릴 것: `-m unit -k snapshot`(test_canvas_unit_snapshot.py) + `-m "unit or tools or links or modal or edit" -n 4 --surface frame,board`
