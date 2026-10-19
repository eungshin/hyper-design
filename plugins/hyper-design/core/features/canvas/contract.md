# canvas — 계약

```
python3 $SK/features/canvas/build_canvas.py <out>
python3 $SK/features/canvas/canvas_test.py <out> [--shot PNG]   # 상호작용 점검(Playwright, 선택)
python3 $SK/features/canvas/helper.py <out> [--paseo-agent ID]   # 로컬 도우미(선택) — 출력한 주소로 열면 '보내기'가 화면 파일에 바로 쓴다
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
- 추가된 메시지(기존 것은 그대로): `hd-hit-at {x, y}` → 화면이 `hd-hit {screen, path, text, rect, to}`로 답한다(그 자리 요소, 없으면 `path:null`). 1.5초 안에 답이 없으면(palette.js 없음) 캔버스는 "이 화면은 편집할 수 없어요"를 띄운다
- `hd-hit-at`에 `leaf:true`를 붙이면 글자를 가진 그 자리 요소로 답한다(글자 고치기 — 자기 글자가 없으면 글자 가진 자손이 하나일 때만, 아니면 `path:null`). 답에는 고칠 글 전체 `full`이 있다
- `hd-pending {items:[{path, text}]}` → 화면이 그 요소 글을 잠시 바꿔 점선으로 보인다(반영 대기 미리보기, `items:[]`이면 되돌림)
- 화면 파일을 바꾸는 편집(트리거 지정·해제, 잇기, 도착 바꾸기, 연결 끊기, 글자·카드 이름·설명 고치기)은 메모(`intent=change`, 메모 안 `edit` 종류)로 쌓여 같은 "보내기" 요청문으로 나간다. 카드 이름·설명은 `path=screens.json > screens[id=…] > title|purpose`. 보내지 않은 편집이 있으면 새로고침·닫기 전에 묻고, 변경 기록은 `hd-edit-log:` 키에 남는다

## 로컬 도우미 (`helper.py`, 선택)
- 127.0.0.1에만, 실행마다 새 토큰(주소의 `?hd=`·머리글 `X-HD-Token`), Host 검사. 쓰는 곳은 `<out>` 안뿐이고, 쓰기 전 원본을 `<out>/.hd-history/<시각>/`에 남긴 뒤 `build_canvas.py`로 다시 만든다(실패하면 되돌림)
- 바로 쓰는 편집: 글자 · 카드 이름·설명(`screens.json`) · 잇기/도착 바꾸기 · 끊기/트리거 해제. 나머지 메모는 요청문 그대로 `<out>/.hd-queue/<시각>.txt`에 쓰고, `--paseo-agent`가 있으면 그 파일을 `paseo send … --prompt-file … --no-wait`로 넘긴다
- 도우미로 열어도 저장 키는 file://로 열 때와 같다(`window.__hdKeyPath`). 도우미가 없거나 꺼져 있으면 '보내기'는 지금처럼 요청문을 복사한다

## 테스트 층 (캔버스를 고치는 모든 세션이 따른다)

| 층 | 파일 | 무엇을 | 시간 |
|---|---|---|---|
| unit | `tests/test_canvas_modules.py` | 순수 모듈(node): 그래프·길찾기·태그 자리·색·리듀서·설정·카메라 계획·순수성 | 약 1초 |
| 브라우저 | `test_canvas_baseline.py`(지금 입력 규칙 고정) · `test_canvas_v2.py` · `test_canvas_edit.py`(편집 기능) | DOM 연결·실제 조작 | 테스트당 1~17초 |
| 도우미 | `test_canvas_helper.py` | `helper.py` 편집·적용·서버(브라우저 1개) | 약 11초 |

브라우저 테스트는 영역 표시를 받는다(`tests/conftest.py`의 `BROWSER` 표 — 표에 없는 브라우저 테스트는 수집 단계에서 실패하니, 새 테스트는 표에 한 줄을 더한다):
`input`(판 조작) · `modal`(크게 보기·주석) · `notes`(메모) · `tools`(도구 막대·카드 옮기기·편집) · `flow`(주요 흐름 화살표) · `links`(연결 보기) · `motion`(카메라·전환) · `helper`(로컬 도우미).

**어디를 고치면 무엇을 돌리나**

| 고친 곳 | `-m` |
|---|---|
| `modules/route.js` · `labels.js` · `focus.js` · `graph.js` · `style.js` · `prefs.js` · `view-links.js` | `unit or links` |
| `modules/camera.js` · `view-motion.js` · `motion.css` | `unit or motion` |
| `canvas_template.html` 메모·주석 부분 | `notes or modal` |
| `canvas_template.html` 이동·확대·입력 | `input` |
| `canvas_template.html` 도구 막대·카드 옮기기 · `drawArrows` | `tools or flow` |
| `foundation/palette.js` | `links or modal or tools` |
| `helper.py` | `helper` |
| `build_canvas.py` · 여러 영역에 걸친 변경 | 전체 |

**돌리는 순서 (전체를 반복해서 돌리지 않는다)**
1. 고치는 동안: `-m unit` + 그 기능의 테스트 하나(`-k 이름`) — 수 초.
2. 커밋 직전: 위 표의 영역(`-m "unit or 영역"`).
3. 단계(슬라이스) 끝: 전체 한 번(약 3.5분). 실패하면 그 테스트만 고쳐 다시 돌리고, 전체는 끝에 한 번 더.
4. 스크린샷은 검문·눈 판정이 필요할 때만 따로 찍는다.

고정본(`runs/laundry-v1`·`gym-v2`·`dayfine-onboarding-v1`)은 저장소에 없으면 그 테스트가 건너뛰어진다 — "통과"가 아니라 "건너뜀"인지 요약 줄에서 확인한다.
