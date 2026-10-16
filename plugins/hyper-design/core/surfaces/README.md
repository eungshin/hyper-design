# 표면 프로필 — 계약

같은 파이프라인이 어떤 화면(폰·데스크톱 창)을 만드는지는 프로필 한 장이 정한다. go/max 본문에는 "모바일이면 … 아니면 …"을 쓰지 않는다 — 다른 점은 전부 여기서 읽는다.

- 고르기: `setup_out.py out --surface <이름>`(기본 `mobile`) → `out/surface.json`에 복사. `out/surface.json`이 없으면 모든 스크립트가 `mobile.json`을 쓴다(오늘과 같다).
- 프로필 파일이 없는 데스크톱 레이아웃(`desktop-scroll`·`desktop-dashboard` 등)은 **데스크톱 기본**으로 짓는다: 창 크기·뷰포트·감사·이미지·작성 안내는 `desktop-wizard`, 흐름 고리·화면 종류·상태는 `mobile`. `surface.json`에 `fallback_of`가 남고, 메인은 그 가정을 decisions.json에 적는다.
- 읽기: `surface.py`의 `load(out)` · `resolve(이름)`.

## 슬롯 (모든 프로필이 전부 가진다)

| 슬롯 | 뜻 | 읽는 곳 |
|---|---|---|
| `name` · `label` | 프로필 이름 · 사람이 읽는 이름 | 전부 |
| `frame` | `device`(작성자에게 말할 이름) · `card`·`modal` `{w,h}` · `radius` · `scale`(첫 배율) | canvas, pack |
| `viewport` | 캡처·측정 창 `{width,height}` | audit |
| `market` | `source`: `app_store`(market.py) \| `prd_refs`(PRD의 `prd_section` 절에서 관례를 뽑는다, market.py 금지) · `min_seen`: 관례로 인정할 최소 제품 수 | go, selfcheck |
| `flow` | 흐름 고리. `field`: spec_inventory.json의 칸. `objects` + `loop`(대상마다 칸) 또는 `steps` + `step`(단계마다 필수 칸) + `last_kind`(마지막 단계 화면의 kind) | go, selfcheck |
| `kinds` | 화면 kind → 구조 예시 파일(`foundation/examples/`). 키가 곧 쓸 수 있는 kind | go, pack |
| `states` | `traits`: 특성 → 상태 · `extra_traits`: 상태 없는 특성 · `go`: 1차에 펼칠 상태 · `cap`: 화면당 상태 상한 | expand_states, selfcheck, audit |
| `audit` | `touch`(44px 터치 크기) · `focus_visible`(키보드 초점이 보이는가) | audit |
| `images` | `kinds`: image_slots.json에 쓸 수 있는 kind · `note`: 메인에게 한 줄 | go, selfcheck |
| `principles` | 원칙 덮어쓰기 `{"replaces": [원칙 번호], "rules": [줄]}` — pack이 원칙 전문 뒤에 "부딪히면 이것이 이긴다"로 붙인다. mobile은 `{}` | pack |
| `type` | 이 표면의 글자 크기 `{역할: "크기/줄높이·굵기"}`. mobile은 `{}`(파운데이션 기본) | pack |
| `writer` | 작성 에이전트에게 주는 표면 한 줄 | pack |

명세 규칙의 상태(`error`·`confirm`·`done`)는 프로필과 무관하게 언제나 쓸 수 있다.

## 흐름 고리 모양

- `objects`(mobile): `[{"name", "create", "view", "edit", "after"}]` — after에 결과 화면(`kind: result` 또는 `--done`).
- `steps`(desktop-wizard): 순서대로 `[{"name", "screen", "pass": "통과 조건 한 줄"}]` — 마지막 단계의 화면은 `kind: result`.

## 새 프로필

슬롯을 전부 채운 `<이름>.json` 하나. 새 슬롯이 필요하면 이 표에 먼저 적고, 읽는 스크립트가 없을 때의 기본값(mobile)을 지킨다.

## 테마(사용자 지정 레퍼런스) — 프로필과 별개

PRD가 레퍼런스 테마를 지정하면 `setup_out.py --theme <foundation/themes/*.json>`. 팔레트 라이브러리 형식 + 선택 칸 `shell`(→ `--c-shell`, 창 바탕·그라데이션)·`highlight`(→ `--c-highlight`, 예문 강조). 점수와 무관하게 기본값이 되고 대안 2개는 라이브러리에서(TDR surface D7). `--c-shell`이 없는 토큰에서는 부품이 `--c-bg`로 떨어진다.
