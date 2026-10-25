# 판 위 디자인 시스템 카드 (ds-card · view-ds-card, S6)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 근거 `tasks/50-stitch/FINDINGS.md` 1-A·3·6(Stitch 는 DS 카드만 살아 있고 화면은 토큰을 복사 — 우리는 화면과 카드가 같은 `tokens.css` 를 참조).

## 규칙

- **자리** — 판 글(`#intro`) 아래, 화면 줄(`#rows`) 바로 위 자기 줄 `#dscard`(왼쪽 통로 = `#rows` 의 padding-left). 첫 줄 맨 앞에 넣지 않는다(그 줄 카드만 밀려 줄 사이 관계가 바뀜). 자기 줄은 모든 줄을 같은 만큼 내릴 뿐 카드끼리 상대 자리·옮긴 거리(`card-pos`)·선은 그대로
- **그리기** — 카드 = iframe(srcdoc) 하나, `<link id="tokens" href="tokens.css">` 로 화면과 같은 파일을 읽는다. 테마는 셸이 모든 iframe 에 보내는 `hd-palette`(바탕 토큰 파일)·`hd-theme-vars`(내 테마 색)만 받는다(palette.js 와 같은 규칙, 다른 메시지는 모름). 실릴 때 `ctx.frameLoaded('@dscard', frame)` 로 지금 테마를 받는다. 값은 모두 `var(--…)`(단계 띠는 `color-mix(var(--c-…))`) — hex 를 복사하지 않는다
- **Model `dsCard.sections(names)`** — 토큰 이름(빌드가 `hd-data.tokens` 에 넣는 `tokens.css` `:root` 변수 이름, 없으면 `null`) → 색 줄(Primary `--c-primary|--c-brand` · Secondary `--c-secondary|--c-brand-tint` · Accent `--c-accent|--c-tertiary` · Neutral = 실제 토큰 사다리 bg→text-1, 셋 미만이면 회색 글자 값) · 글자 Headline/Body/Label(`--fs-title|h1|headline|h2` · `--fs-body` · `--fs-caption|label|sub`, 같은 꼬리의 `--fw-`·`--lh-`) · 단추 Primary/Secondary/Outlined · 입력 · `--r-*` · `--shadow-*`. 후보가 없는 색 줄은 빼고, 글자·단추는 글자 값으로. 목록이 아니거나 색 토큰 0 = `null`(카드 없음). 이름이 아닌 값은 버리고 `bad` 로 센다
- **누르기** — 끌지 않은 클릭·Enter = Foundation 탭(같은 토큰의 자세한 견본). 클릭은 판으로 올라가지 않는다(고르기 풀기·레이아웃 놓기 없음)
- **숨기기** — 판 글 레이어 `@dscard`(상태 주인 = 셸 `hidden`, 키 `hd-hidden:`): 레이어 패널 눈·왼쪽 [숨긴 것]. 셸 `loadHidden` 이 카드보다 먼저 돌아서 시작 숨김은 카드가 그 키를 읽기만 한다
- **아닌 것** — `.card` 가 아니다: 보내기 요청문의 화면·메모 핀·연결·교체(swap)·크기·선택 대상이 아니다
- **오류 탐지** — 토큰이 없으면 카드 없음, 경고 없음(앱 프로젝트도 같음). `tokens` 가 목록이 아니거나 이름이 아닌 값이 있으면 `[hd]` 경고 한 줄. 숨김 목록이 깨졌으면 보이게 두고 `[hd]` 경고

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/ds-card.js` | `unit` (`test_canvas_unit_ds_card.py`) |
| `modules/view-ds-card.js` · `build_canvas.py` 의 `tokens` · 셸 `@dscard`(loadHidden·레이어 texts) | `unit or dscard` (`test_canvas_ds_card.py`) |
