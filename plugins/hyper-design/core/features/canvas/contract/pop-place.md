# 메모 창 틀 (pop-place · view-pop-place)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `pop-place`(Model)·`view-pop-place`(View) — 메모 창(`#pop`) 틀(#223): 머리 줄 끌어 옮기기·오른쪽 아래 모서리 크기(가장 작게 260×160, 창 안으로). 한 번 옮기거나 키우면 다음부터 늘 그 자리(키 `hd-pop`, 모든 캔버스 공용), 머리 줄 두 번 누르기 = 자동 자리. 열린 동안 대상 카드에 `.memo-target` 테두리. 자동 자리 계산은 셸 `placePop`

- 붙이기(task 22, 등록부 첫 증명): `view-pop-place` 가 `HD.feature('popPlace', {needs: ['$', 'local', 'warn']})` 로 등록하고 셸은 `mountAll` 결과의 `popPlace` 를 `PP` 로 쓴다. 붙지 못했으면 메모 창은 자동 자리에만 열린다(`[hd]` 오류 + 토스트)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/pop-place.js` · `view-pop-place.js`(메모 창 옮기기·크기·저장한 자리·대상 카드 표시) · `view-memo-pop`(자동 자리·열기·닫기) | `unit or notes or modal or tools` |
