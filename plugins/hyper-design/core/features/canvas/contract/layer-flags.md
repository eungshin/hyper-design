# 숨긴·잠근 화면 표시 정리 (layer-flags, polish-1)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/layer-flags.js` | Model | 저장된 숨김·잠금 id 목록을 지금 있는 id 에 맞춰 거름. 상태 없음. `HD.layerFlags = {BOARD, live(rows, notes), clean(text, live) → {ids, set, dropped, changed, bad}}` |
| `modules/view-layer-flags.js` | View | 숨김·잠금·태그 이름(`hd-link-names:`)의 주인: 저장소 읽기·다시 쓰기·`[hd]` 경고(규칙은 Model), 숨긴 카드 `.hid`·판 글 가리기, `#thid` 개수, 숨기기·잠그기·이름 바꾸기의 되돌리기 줄. 상태 = `hidden`·`locked`·`linkNames`. ctx `{$, $$, rowsEl, cardEl, getItem, setItem, hash, live(), record, toast, redraw, openHidden, hiddenChanged(ids, on), layersChanged, lockedChanged}`. `HD.viewLayerFlags.mount(ctx) → {hidden(), locked(), isHidden(id), isLocked(id), hide(ids, on), lock(ids, on), guard(ids), names{get, set}, loadHidden() → 새로 숨은 id, loadLocked(), loadLinkNames(), renderHidden()}` — 셸이 직접 붙인다(`LF`, 셸 C3 2026-10-26) |
| 셸 `adoptState` · `openHidl` | — | 기록 줄로 오갈 때 `LF.load*` 뒤 고르기·선·패널을 잇기만 · 숨긴 것 단추·메뉴 = 레이어 패널을 숨긴 것만으로. 다른 읽는 곳(정렬 상자·삭제·끌기·요소 막대·레이어 패널·교체 `placed`)은 `LF` 의 읽기 함수를 받는다 |

## 규칙

- 저장 키·형식은 그대로: `hd-hidden:<hash>` · `hd-locked:<hash>` = id 의 JSON 배열(상태 파일 `hidden`·`locked`)
- 지금 있는 id(`live`) = `D.rows` 의 화면 id + 메모의 빈 레이아웃(`edit:'new-screen'` 의 `screen`) + 판 글 레이어 `@intro`·`@foot`·`@dscard`(화면 목록에 없어도 늘 있음). DOM 카드가 아니라 데이터에서 — 빈 레이아웃 카드는 숨김을 읽은 뒤에 그려진다
- 읽을 때(시작 · 기록 줄로 오갈 때 `adoptState`) 숨김·잠금 둘 다 거른다: 없는 id · 중복 · 문자열이 아닌 값은 빼고, 뺀 것이 있으면(`changed`) 깨끗한 목록을 같은 키에 다시 쓴다 — 지운 화면이 같은 id 로 다시 생겨도 숨김·잠금이 되살아나지 않고, 잠금 목록이 쌓이지 않는다
- 깨진 값(JSON 아님·배열 아님) = 빈 목록으로 다시 쓰고 `[hd]` 경고 한 줄 · 없는 id 를 뺐으면 `[hd]` 경고 한 줄(몇 개·어떤 id)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/layer-flags.js` · `view-layer-flags.js`(+ `tests/test_canvas_unit_layer_flags.py` · 브라우저 `test_canvas_layer_flags.py`) | `unit or layers` |
