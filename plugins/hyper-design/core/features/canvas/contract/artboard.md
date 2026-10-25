# 카드(아트보드) 크기 (artboard · view-artboard, task 46)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 조사·채택 근거는 Photoshop 새 문서·캔버스 크기, Illustrator 대지 옵션, Figma 프레임 프리셋(`tasks/46-canvas-size/RESEARCH.md`, 저장소 밖).

## 규칙

- **카드마다 크기** — 상태 이름 `card-size` = `{카드 id: {w, h, preset?}}`(CSS px 정수 100~4000, `preset` = 고른 프리셋 이름). 없으면 프로젝트 카드 크기(`D.card` = 표면 프로필). `stateFile.NAMES`·`history.TRACK`(되돌리기·기록 줄)에 있고 `LIVE` 는 아니다(파일에서 바뀌면 다시 불러오기). 셸 `adoptState` 는 `has('card-size')` 면 `AB.reload()`
- **주인** — `view-artboard`(View) 하나가 상태를 갖고 저장한다(`ctx.store`, 키 `hd-card-size:<hash>`). 최근 크기 6개·내 프리셋은 전역 키 `hd-artboard`(`ctx.local` — 파일로 가지 않음, Photoshop 처럼 프로젝트를 넘어 쓴다). 셸은 `sizeOf(id)` 하나로 읽는다 — 카드 안 배율(`wOf` = 카드 실제 폭 / 그 카드 폭: 요소 고르기·글자 고치기·소켓·테두리), `view-lines` 상자 대체값, `view-links` 배율·긴 화면 펼치기, `view-motion` 요소 자리, `view-pins` 핀 배율이 모두 `ctx.sizeOf` 를 받는다. 크게 보기는 크기를 바꾼 카드면 그 크기(`modalSize`), 아니면 표면 프로필의 크게 보기 크기
- **입히기** — 카드 요소에 `--card-w`·`--card-h`(+ `data-size="W×H"`)를 그 카드에만 둔다(`.card`·`.phone`·iframe 이 같은 변수를 읽음). 바로 바뀐다(펼치기 움직임 없이 — 선·맞추기가 같은 프레임에 잰다). 줄 안 카드는 줄이 다시 흘러 오른쪽 카드가 밀리고(겹치지 않음), 바뀐 카드의 왼쪽 위는 그대로(Illustrator·Figma 기본 기준점). 9점 기준점·Relative·늘어난 곳 색은 래스터 개념이라 뺐다
- **Model `artboard`** — 프리셋 묶음(`CATS` 최근·모바일·태블릿·웹/데스크톱·사용자 정의, `PRESETS` 실제 기기 이름·px) · `check`(정수·범위, 한국어 오류) · `of`·`set`(null 또는 기본과 같은 크기 = 항목 지움)·`common` · `swap`·`orient`·`presetOf`(가로로 맞으면 `이름 가로`) · `label`·`full`(요청문 `W×H(프리셋)`) · `pushRecent`(MRU 6) · `savePreset`(같은 이름 = 덮어쓰기) · `prefs`·`norm`(깨진 항목은 빼고 `bad` → View 가 `[hd]` 경고) · `carry`(빈 레이아웃 → 승격된 화면) · `nudge`(화살표 ±1, Shift ±10)
- **새 화면 대화상자** — N 도구로 빈 곳 누르기 · 우클릭 `여기에 레이아웃` · 레이어 [+] 가 연다(`newScreenAt`). 왼쪽 묶음 탭 · 가운데 프리셋 카드(이름 + `W × H` + 비율 그림) · 오른쪽 상세(이름·너비·높이 px·세로/가로·프리셋으로 저장) · 취소/만들기. 처음 고른 크기 = 프로젝트 카드 크기. Enter = 만들기(프리셋 카드에서는 그 카드로), Esc = 취소, 바깥 누르기 = 취소. 만들면 빈 레이아웃 메모 하나(이름 = 메모 `value`) + 그 카드 크기(`seed` — 기록 없이, 되돌리기는 카드 만들기 한 단계). `새 화면 만들고 잇기`는 기본 크기로 바로. 복제 카드는 원본 크기
- **고른 카드 크기** — 선택 막대 맨 앞 `W×H ▾`(여러 장 크기가 다르면 `여러 크기 ▾`) → 어두운 팝오버: W·H 칸 + 가로·세로 바꾸기 · 묶음별 프리셋 줄(누르면 바로 적용·닫힘) · `기본 크기로 (W×H)` · 적용. 고른 카드 모두에 한 번에, 되돌리기 한 단계. 잠긴 카드는 셸 `guard` 가 알리고 뺀다. 고른 카드가 바뀌면 닫힌다. 닫으면 초점은 크기 단추로(Esc·0 같은 판 키가 바로 닿게)
- **AI 요청** — 크기는 카드의 보기일 뿐 화면 HTML 을 고치지 않는다. 보내는 요청문(`edits.request(notes, out, sizes)`)에서 기본 크기가 아닌 카드의 항목 아래 `   화면 크기: 834×1194(iPad Pro 11) — 이 뷰포트에 맞게 배치` 줄 — fix 스킬이 읽는다(`skills/fix/SKILL.md`, `test_fix_skill.py`)
- **오류 탐지** — 잘못된 W·H = 칸 빨간 테두리(`aria-invalid`) + 한국어 한 줄, 적용·만들기 안 함. 저장 실패 = 토스트. 깨진 저장값 = 기본 크기 + `[hd]` 경고. 기능이 붙지 못하면(`FT.artboard` 없음) 크기 단추가 숨고 N 도구는 기본 크기로 바로 놓는다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/artboard.js` | `unit` (`test_canvas_unit_artboard.py`) |
| `modules/view-artboard.js` · 셸 `AB` attach·`sizeOf`·`wOf`·`newScreenAt`·`modalSize` · 선택 막대 크기 단추 | `unit or tools or modal` (`test_canvas_artboard.py`) |
| `edits.request` 의 `화면 크기:` 줄 | `unit` + `skills/fix/test_fix_skill.py` |
