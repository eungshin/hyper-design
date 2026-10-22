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
- `out/index.html` — `canvas_template.html`에 데이터(`hd-data`, 화면 파일에서 미리 뽑은 화면 사이 링크 `links` 포함 — `palette.js` 의 `links()` 와 같은 규칙: `href`·`data-href`·`onclick` 안 `.html`)·`modules/*.js`·`modules/motion.css`를 끼워 넣은 한 파일. 화면 카드는 보일 때 한 번만 불러온다
- `out/foundation.html` · `out/components.html` · `out/palette.js`

## 구조
- `modules/` — 판의 선·고른 화면 안 연결·편집·도크. 선은 `view-lines` 하나뿐(E20 A: 고르면 같은 선이 진해짐, 번호 = 출발 화면마다), `view-links` 는 고른 화면 안(버튼 테두리·번호·소켓·패널 줄 목록)만, `view-link-panel` 이 연결 패널(줄마다 이름·휴지통). Model(`graph`·`route`·`camera`·`style`·`edits`) / ViewModel(`prefs`·`tools`·`dock`·`selection`) / View(`view-links`·`view-motion`·`view-dock`·`view-edge-pan`·`view-select`·`view-lines`·`motion.css`)
- `busy`(Model)·`view-busy`(View) — AI 수정 중 덮개(Q2b): 터미널로 넘긴 화면 카드에 덮개, 상태 키 `hd-busy:`, 덮개가 있는 동안만 2초마다 `/api/watch` 로 화면 파일 mtime 을 보고 바뀌면 걷고 그 카드만 다시 싣는다. `line-ends`(Model)·`view-line-ends`(View) — 선 끝 손잡이(Q3): 선 누르기 = 그 쌍 강조 + 도착 끝 손잡이, 다른 카드로 끌어 놓기 = 도착 바꾸기(메뉴 '도착 바꾸기'와 같은 편집·되돌리기 한 단계)
- `caption`(Model)·`view-caption`(View) — 카드 아래 글 한 상자(H16): 제목·설명·정책 줄을 한 상자에서 고치고, 바뀐 칸마다 반영 대기 편집(`title`·`purpose`·`policy`[i]) 을 한 번의 `addEdits` 로(되돌리기 한 번). 정책 줄 더하기·지우기 없음(helper 가 못 씀)
- `align`(Model)·`view-align`(View) — 정렬 패널(H18, 도크 패널 `align`): 고른 카드(잠김·숨김·삭제 대기 빼고)의 상자로 맞추기 6·간격 같게 2·늘어놓기 2(간격 칸 px, 키 `hd-align-gap`). 옮기기는 셸 `moveCards` 가 카드 옮긴 자리(`hd-card-pos:`)에 더하고 기록 한 단계
- `folders`(Model)·`layers`(Model, 폴더 줄)·`view-layers`(View) — 레이어 폴더(H17): 패널에서만 묶음(판 카드·화면 파일 그대로, 키 `hd-folders:`), 데이터 줄 = 고정 폴더, 폴더·줄의 [가로로/세로로 늘어놓기]는 정렬 패널 간격으로 셸 `arrangeCards`
- 새 기능은 `canvas_template.html` 밖 모듈로 만들고 템플릿에는 붙이는 줄만 둔다(스트랭글러 — 맞닿는 기존 덩어리는 그 조각에서 같이 빼낸다). 판 바깥 UI 색은 `:root`의 `--ui-*`(무채색)만 쓴다
- 오른쪽 패널 도크: 배치는 `dock.js`(키 `hd-dock`, 모든 캔버스 공용), 그리기·끌기는 `view-dock.js`. 패널(`#pLinks`·`#pShow`·`#pNotes`·`#pLayers`)은 옮겨 붙일 뿐 안의 id(`#legend`·`#notes`·`#hidl`)와 그 `hidden` 뜻은 그대로다
- `edits.js` — 편집 메모 하나가 진실 원천: 반영 대기 선·빈 레이아웃·글자 미리보기·도우미가 바로 쓸 것은 모두 메모에서 계산한다
- `notes`(Model) — 메모 목록 저장소(키 `hd-notes:`, 읽기·쓰기는 셸): 목록 하나(`list`·`add`·`remove`·`find`·`unsent`)와 `commit()` = 지난 저장 뒤 메모가 바뀐(더함·뺌·제자리 고침) 화면 id. 셸 `saveNotes` 는 그 카드만 다시 그린다(배지·삭제 대기·카드 글·`hd-pending`), 판의 선은 `linesKey`(잇기·끊기·삭제·빈 레이아웃 메모)가 바뀔 때만 다시
- Model·ViewModel 파일은 DOM·저장소·메시지를 쓰지 않는다(`tests/test_canvas_modules.py`의 순수성 검사 — 층 표 `LAYER` 의 Model·ViewModel 전부. 모듈 목록은 `build_canvas.MODULES` 하나뿐이고 테스트가 그것을 읽으며, view-* 가 아닌 모듈이 `LAYER` 에 없으면 실패)
- 화면 ↔ 캔버스 메시지(`hd-pick`·`hd-links`·`hd-link-go` 등)와 "보내기" 요청문 형식은 `/hyper-design:fix`가 읽으므로 바꾸지 않는다
- 추가된 메시지(기존 것은 그대로): `hd-hit-at {x, y}` → 화면이 `hd-hit {screen, path, text, rect, to}`로 답한다(그 자리 요소, 없으면 `path:null`). 1.5초 안에 답이 없으면(palette.js 없음) 캔버스는 "이 화면은 편집할 수 없어요"를 띄운다
- `hd-hit-at`에 `leaf:true`를 붙이면 글자를 가진 그 자리 요소로 답한다(글자 고치기 — 자기 글자가 없으면 글자 가진 자손이 하나일 때만, 아니면 `path:null`). 답에는 고칠 글 전체 `full`이 있다
- `hd-pending {items:[{path, text}]}` → 화면이 그 요소 글을 잠시 바꿔 점선으로 보인다(반영 대기 미리보기, `items:[]`이면 되돌림)
- 화면 파일을 바꾸는 편집(트리거 지정·해제, 잇기, 도착 바꾸기, 연결 끊기, 글자·카드 이름·설명 고치기)은 메모(`intent=change`, 메모 안 `edit` 종류)로 쌓여 같은 "보내기" 요청문으로 나간다. 카드 이름·설명은 `path=screens.json > screens[id=…] > title|purpose`. 보내지 않은 편집이 있으면 새로고침·닫기 전에 묻고, 변경 기록은 `hd-edit-log:` 키에 남는다

## 책임 게이트 (조각마다 — god object 를 다시 만들지 않게)
기계 검사(`tests/test_canvas_modules.py`의 `gate`, unit 층에서 돈다):
- **책임** — 모듈 머리 주석 첫 줄 = `/* 층 — 맡은 일 */`. 한 줄로 못 쓰면 모듈을 나눈다
- **협력** — 의존은 아래 층으로만: Model 은 다른 층을 모르고, ViewModel 은 View 를 모른다. View 끼리는 `HD.viewX` 를 직접 부르지 않는다 — 셸이 `mount(ctx)` 로 함수를 건네거나 의도(`dispatch`)로 잇는다
- ~~비대 방지(셸 function 수 래칫)~~ — 2.2 재평가로 뺌(10-21): 진짜 1 · 잡음 2 · 대응 6분. 셸에 새 기능을 두지 않는 것은 조각 보고(아래)에서 사람이 본다

조각 보고(커밋 전, 사람이 본다):
- **자율** — 새 상태마다 주인 모듈 하나와 저장 키 하나. 다른 모듈은 그 상태를 읽기만 하거나 의도를 보낸다
- 새 모듈마다 한 줄: 맡은 일 · 가진 상태 · 받는 `ctx` · 내보내는 의도/함수
- 셸에 새로 생긴 위쪽 `function` 이 있으면 왜 모듈이 아닌지 한 줄

## 로컬 도우미 (`helper.py`, 선택)
- 127.0.0.1에만, 실행마다 새 토큰(주소의 `?hd=`·머리글 `X-HD-Token`), Host 검사. 쓰는 곳은 `<out>` 안뿐이고, 쓰기 전 원본을 `<out>/.hd-history/<시각>/`에 남긴 뒤 `build_canvas.py`로 다시 만든다(실패하면 되돌림)
- 바로 쓰는 편집: 글자 · 카드 이름·설명(`screens.json`) · 잇기/도착 바꾸기 · 끊기/트리거 해제. 나머지 메모는 요청문 그대로 `<out>/.hd-queue/<시각>.txt`에 쓰고, `--paseo-agent`가 있으면 그 파일을 `paseo send … --prompt-file … --no-wait`로 넘긴다
- `POST /api/watch {files}` → `{mtimes: {file: mtime|null}}`(out 밖·없는 파일 = null) — AI 수정 중 덮개가 끝을 아는 유일한 신호
- 도우미로 열어도 저장 키는 file://로 열 때와 같다(`window.__hdKeyPath`). 도우미가 없거나 꺼져 있으면 '보내기'는 지금처럼 요청문을 복사한다

## 테스트 층 (캔버스를 고치는 모든 세션이 따른다)

| 층 | 파일 | 무엇을 | 시간 |
|---|---|---|---|
| unit | `tests/test_canvas_modules.py` | 순수 모듈(node): 그래프·길찾기·태그 자리·색·리듀서·설정·카메라 계획·순수성·책임 게이트 | 약 1초 |
| 브라우저 | `test_canvas_baseline.py`(지금 입력 규칙 고정) · `test_canvas_v2.py` · `test_canvas_edit.py`(편집 기능) | DOM 연결·실제 조작 | 테스트당 1~17초 |
| 도우미 | `test_canvas_helper.py` | `helper.py` 편집·적용·서버(브라우저 1개) | 약 11초 |

브라우저 테스트는 영역 표시를 받는다(`tests/conftest.py`의 `BROWSER` 표 — 표에 없는 브라우저 테스트는 수집 단계에서 실패하니, 새 테스트는 표에 한 줄을 더한다):
`input`(판 조작) · `modal`(크게 보기·주석) · `notes`(메모) · `tools`(도구 막대·카드 옮기기·편집) · `flow`(판에 늘 그리는 선) · `links`(고르기 강조·화면 안 연결) · `motion`(카메라·전환) · `helper`(로컬 도우미) · `dock`(오른쪽 패널 도크).

**어디를 고치면 무엇을 돌리나**

| 고친 곳 | `-m` |
|---|---|
| `modules/route.js` · `graph.js` · `style.js` · `prefs.js` · `view-links.js` · `view-link-panel.js`(연결 패널: 이름·휴지통) | `unit or links` |
| `modules/edits.js` · `history.js` · `view-history.js`(기록 시간줄·되돌리기) · `view-notes.js`(메모·반영 대기 목록) | `unit or tools or notes` |
| `modules/dock.js` · `view-dock.js` · 도크 CSS | `unit or dock or notes` |
| `modules/view-menu.js`(위쪽 보기 메뉴 = 배율 칩 · 창 메뉴 · Tab) · 위쪽 줄 | `unit or menu or dock` |
| `modules/layers.js` · `view-layers.js`(레이어 패널: 나무·숨김·잠금·검색) · 셸 숨기기·잠금 가드 | `unit or layers or tools` |
| `modules/align.js` · `folders.js` · `view-align.js`(정렬 패널) · `view-layers.js` 폴더 · 셸 `boxesOf`·`moveCards`·`arrangeCards` | `unit or layers or tools or dock` |
| `modules/theme.js` · `view-theme.js`(테마 패널: 고르기·복제·색 네 칸·대비) · `foundation/palette.js` 의 `hd-theme-vars` | `unit or theme` |
| `modules/viewport.js` · `view-viewport.js`(창 나누기·동시 스크롤 · 카메라 계산 zoomAt·fit) | `unit or menu or input` |
| `helper.py` · `modules/view-sync.js`(화면 파일에 바로 쓰기: 잇기·끊기·삭제·되살리기·바뀐 카드만 다시·모드 칩) | `unit or helper` |
| `modules/camera.js` · `view-motion.js` · `motion.css` | `unit or motion` |
| `modules/view-edge-pan.js` (끄는 중 가장자리 판 밀기) | `unit or tools or input` |
| `modules/selection.js` · `view-select.js` (고른 카드: 누르기 = 고르기 + 연결 강조, Shift = 여러 장) | `unit or tools or input or links` |
| `modules/notes.js`(메모 목록 저장소·닿은 화면) · `canvas_template.html` 메모·주석 부분(`saveNotes`·`renderNotes`·보내기) | `unit or notes or modal or tools` |
| `canvas_template.html` 이동·확대·입력 | `input` |
| `canvas_template.html` 도구 막대·카드 옮기기 · `drawArrows` | `tools or flow` |
| `modules/view-lines.js` · `graph.overview` · `style.rowColor` (판의 선 하나뿐: 쌍마다 하나·줄 색·번호·태그·강조·자르기 맞춤·보이기/굵기/투명도/색) | `unit or flow or links or tools` |
| `modules/busy.js` · `view-busy.js`(AI 수정 중 덮개: 터미널로 넘긴 화면 · 화면 파일이 바뀌면 걷힘 · [걷기]) · `helper.py` `/api/watch` | `unit or helper or notes` |
| `modules/line-ends.js` · `view-line-ends.js`(선 누르기 = 쌍 강조 + 도착 끝 손잡이 · 끌어 놓기 = 도착 바꾸기) | `unit or flow or tools` |
| `modules/caption.js` · `view-caption.js`(카드 아래 글 한 상자: 두 번 누르기·글자 도구·카드 메뉴 이름/설명 → 바뀐 칸마다 반영 대기, 되돌리기 한 번) | `unit or tools or notes` |
| `foundation/palette.js` | `links or modal or tools` |
| `helper.py` | `helper` |
| `build_canvas.py` | `unit or flow or links` |
| 여러 영역에 걸친 변경 | 그 영역들을 `or` 로 묶어서(전체는 아래 3 에서만) |

**돌리는 순서 (전체를 반복해서 돌리지 않는다)**
1. 고치는 동안: `-m unit` + 그 기능의 테스트 하나(`-k 이름`) — 수 초.
2. 큰 실행 전: 바꾸거나 지운 선택자·키·문구를 `tests/` 에서 먼저 찾아(grep) 걸리는 옛 테스트를 고친다 — 큰 실행을 '어디가 깨지나' 찾기에 쓰지 않는다.
3. 커밋 직전: 위 표의 영역(`-m "unit or 영역"`). 실패하면 고친 뒤 실패한 것만(`--lf`) 다시.
4. 번호 조각(2.5 · 2 · 2.2 …) 끝: 전체 한 번(약 9분). a·b·c 하위 조각에서는 돌리지 않는다. 실패하면 `--lf` 로 확인하고, 전체를 다시 돌리지 않는다.
   브라우저 테스트가 든 실행(영역·전체)은 `-n 4`(pytest-xdist, 일꾼마다 페이지를 따로 빌드 — test_canvas_edit.py 219초 → 73초)로 나눠 돌린다. 한 테스트만 고칠 때·`--lf` 는 나누지 않는다.
   전체 실행에는 `--durations=20` 을 붙여 느린 테스트 상위 목록을 남긴다(따로 프로파일링 실행을 하지 않는다). 큰 실행 전에는 바꾸거나 지운 선택자·id·함수 이름을 테스트에서 grep 해 `-k` 로 먼저 돌린다(전역 규칙 `~/.claude/ctx/testing.md` R54~R56).
5. 스크린샷은 검문·눈 판정이 필요할 때만 따로 찍는다.
6. 검토 비용 기록(`tests/tracking/`): 실행은 conftest 가 `runs.json` 에 자동으로 남긴다. 조각을 커밋할 때 `process.json` 에 한 항목(테스트 분·전체 수·게이트 걸림 진짜/잡음·잡은 버그·낭비와 고칠 점), 번호 조각 끝에 `python3 tests/tracking/review.py` 로 한도를 넘은 곳을 보고 규칙을 고친다.

고정본(`runs/laundry-v1`·`gym-v2`·`dayfine-onboarding-v1`)은 저장소에 없으면 그 테스트가 건너뛰어진다 — "통과"가 아니라 "건너뜀"인지 요약 줄에서 확인한다.
