# 캔버스 화면 ↔ 앱 카드 맞음 검증 (twin · twin-diff · view-twin · verify_desk, V2)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 검증에는 AI(토큰)를 쓰지 않는다 — 정해진 스냅숏 + 순수 비교, 같은 입력 = 같은 결과.

## 규칙

- **스냅숏(palette.js, 메시지 처리기 하나):** `hd-snapshot {tag}` → `hd-snapshot-r {tag, screen, items:[{role, text, tag, style:{color, bg, fs, fw, radius}}], size}` — 보이는 요소만, 역할 button·heading·link·input·img(alt)·text(제 글자), 문서 차례, 400개까지(`size` = 상한 전 수). 담는 규칙은 `snapItem` 하나. `hd-snapshot-mark {i}` = 다시 재서 i 번째에 주황 테두리(null = 지움)
- **비교(`twin-diff.js`, Model):** 짝 = (역할, 정규화한 글자), 같은 글자가 여럿이면 차례로. 못 짝지은 것: 글자 같고 역할만 다름 · 같은 자리(앞에 짝지은 수가 같음) 같은 역할 글자만 다름 · 같은 글자 수가 다름 = `unsure`(AI 에 묻지 않음), 나머지 = `missing`(앱에 없음)·`extra`(앱에만). 짝지은 것의 스타일 = 색 RGB 거리 12 · px 1 · 굵기 같음
- **짝(`twin.js` `pair`):** `/api/app-parts` 의 `links`(parts.json — V1 과 같은 읽기 `HD.chatBoth.links`)로 그 화면이 끌어 쓰는 부품 파일을 그대로 싣는 다른 카드, 없으면 부품 파일 이름(.html 뺀 것)이 id 인 앱 무대 카드(개발 서버 주소 = app.json 무대). 없으면 '견줄 앱 화면 없음'
- **보이기(`view-twin.js`):** 짝 있는 캔버스 카드 `.phone` 왼쪽 아래 `.tchip` '앱과 일치'·'다름 N'·'검증 못 함'. 누르면 목록 창 `#twinwin` — 줄 = 두 카드 강조, [이 다른 곳 고쳐 달라고 보내기] = `HD.twin.request` 글(목록만, 20줄까지) 하나로 화면 메모를 만들어 `ctx.sendNotes`(위쪽 [보내기]와 같은 길). 창은 떠 있는 층 `layer('twin')`(셸이 `FL.add`) — Esc·바깥 누르기는 `view-float-stack`, 자리는 `HD.popSide.under`
- **기억:** 열쇠 = (화면 카드 주소 `?v=`, 부품 도장 + 앱 카드 주소 + HMR 수) — 같으면 다시 재지 않는다. 표는 실린 카드끼리만 잰다
- **`hd verify <화면>`:** CLI → `POST /api/verify {screen}`(verify_desk) → 이벤트 `verify.ask {req, screen}` → 열린 페이지가 (안 실린 카드는 실어서) 기억 없이 재고 `POST /api/verify-result {req, result}` → CLI 가 JSON + 한 줄. 종료 코드 0 일치 · 1 다름 · 2 검증 못 함(열린 캔버스 없음 = 바로 · 짝 없음 · 10초 넘김 · 도우미 없음). 브라우저를 띄우지 않는다
- 한계: 글자·구조·스타일 토큰(색·글자 크기·굵기·모서리) 밖의 시각 차이(자리·간격·그림자·그림 내용)는 못 잡는다. 열린 흐름 수로 '캔버스 열림'을 보므로 `hd wait` 등 SDK 흐름만 있으면 10초 뒤 timeout(2)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/twin-diff.js` · `twin.js` | `-m unit -k twin` |
| `modules/view-twin.js` · `palette.js` 스냅숏 · `verify_desk.py` · 라우트 | 위 + `test_canvas_twin.py` + `-m unit -k verify_desk` + `tests/protocol -k every_route` + hd `-k verify` |
