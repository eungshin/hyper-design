# canvas — 계약

```
python3 $SK/features/canvas/build_canvas.py <out>
python3 $SK/features/canvas/canvas_test.py <out> [--shot PNG]   # 상호작용 점검(Playwright, 선택)
```

## 입력 (out 안)
- `screens.json` — 필수. `groups`·`screens[{id,file,title,group,purpose,policies,branches}]`
- 선택: `decisions.json` · `palettes.json` · `credits.json` · `tokens.css`
- 플러그인 쪽: `foundation/palette.js`, `foundation/specimens.html`(환경변수 `HD_SPECIMENS`로 바꿈)

## 출력
- `out/index.html` — `canvas_template.html`에 데이터(`hd-data`)·`modules/*.js`·`modules/motion.css`를 끼워 넣은 한 파일. 화면 카드는 보일 때 한 번만 불러온다
- `out/foundation.html` · `out/components.html` · `out/palette.js`

## 구조
- `modules/` — 연결 보기. Model(`graph`·`route`·`labels`·`camera`·`style`) / ViewModel(`focus`·`prefs`) / View(`view-links`·`view-motion`·`motion.css`)
- Model·ViewModel 파일은 DOM·저장소·메시지를 쓰지 않는다(`tests/test_canvas_modules.py`의 순수성 검사)
- 화면 ↔ 캔버스 메시지(`hd-pick`·`hd-links`·`hd-link-go` 등)와 "보내기" 요청문 형식은 `/hyper-design:fix`가 읽으므로 바꾸지 않는다

## 테스트 층 (캔버스를 고치는 모든 세션이 따른다)

| 층 | 파일 | 무엇을 | 시간 |
|---|---|---|---|
| unit | `tests/test_canvas_modules.py` | 순수 모듈(node): 그래프·길찾기·태그 자리·색·리듀서·설정·카메라 계획·순수성 | 약 1초 |
| 브라우저 | `test_canvas_baseline.py`(지금 입력 규칙 고정) · `test_canvas_v2.py` · `test_canvas_edit.py`(편집 기능) | DOM 연결·실제 조작 | 테스트당 1~17초 |

브라우저 테스트는 영역 표시를 받는다(`tests/conftest.py`의 `BROWSER` 표 — 표에 없는 브라우저 테스트는 수집 단계에서 실패하니, 새 테스트는 표에 한 줄을 더한다):
`input`(판 조작) · `modal`(크게 보기·주석) · `notes`(메모) · `tools`(도구 막대·카드 옮기기) · `flow`(주요 흐름 화살표) · `links`(연결 보기) · `motion`(카메라·전환).

**어디를 고치면 무엇을 돌리나**

| 고친 곳 | `-m` |
|---|---|
| `modules/route.js` · `labels.js` · `focus.js` · `graph.js` · `style.js` · `prefs.js` · `view-links.js` | `unit or links` |
| `modules/camera.js` · `view-motion.js` · `motion.css` | `unit or motion` |
| `canvas_template.html` 메모·주석 부분 | `notes or modal` |
| `canvas_template.html` 이동·확대·입력 | `input` |
| `canvas_template.html` 도구 막대·카드 옮기기 · `drawArrows` | `tools or flow` |
| `foundation/palette.js` | `links or modal` |
| `build_canvas.py` · 여러 영역에 걸친 변경 | 전체 |

**돌리는 순서 (전체를 반복해서 돌리지 않는다)**
1. 고치는 동안: `-m unit` + 그 기능의 테스트 하나(`-k 이름`) — 수 초.
2. 커밋 직전: 위 표의 영역(`-m "unit or 영역"`).
3. 단계(슬라이스) 끝: 전체 한 번(약 3.5분). 실패하면 그 테스트만 고쳐 다시 돌리고, 전체는 끝에 한 번 더.
4. 스크린샷은 검문·눈 판정이 필요할 때만 따로 찍는다.

고정본(`runs/laundry-v1`·`gym-v2`·`dayfine-onboarding-v1`)은 저장소에 없으면 그 테스트가 건너뛰어진다 — "통과"가 아니라 "건너뜀"인지 요약 줄에서 확인한다.
