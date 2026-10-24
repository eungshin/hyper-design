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
- 기능별 규칙은 `contract/<기능>.md`(파일 하나 = 기능 하나 — 구조 규칙과 '고치면 돌릴 것' 줄). 목록은 그 폴더 자체다(여기에 줄을 더하지 않는다). 모듈 머리 주석이 아니라 파일로 둔 까닭: 규칙이 Model·View·셸에 걸치고, 머리 주석은 `index.html` 에 그대로 실려 나가며, 머리 주석은 한 줄 책임 + API 만 말한다
- 새 기능은 `canvas_template.html` 밖 모듈로 만들고 템플릿에는 붙이는 줄만 둔다(스트랭글러 — 맞닿는 기존 덩어리는 그 조각에서 같이 빼낸다). 판 바깥 UI 색은 `:root`의 `--ui-*`(무채색)만 쓴다
- 기능 등록부 `features`(ViewModel) — View 가 읽힐 때 `HD.feature(이름, {needs, mount(ctx)})` 로 등록하고, 셸은 기존 mount 들 뒤에서 `HD.mountAll(ctx)` 를 한 번 부른다(공통 ctx 칸은 `modules/features.js` 머리 주석). `needs` 칸이 없거나 mount 가 던지면 그 기능만 빠지고 `[hd]` console.error + 토스트, 나머지는 붙는다. 기존 mount 는 그 자리에 둔다(스트랭글러) — 지금 등록부로 붙는 것: `popPlace`
- Model·ViewModel 파일은 DOM·저장소·메시지를 쓰지 않는다(`tests/test_canvas_modules.py`의 순수성 검사 — Model·ViewModel 전부). 모듈 목록은 손으로 적지 않는다: 빌드(`build_canvas.modules()`)가 `modules/*.js` 를 모두 끼우고(view-* 아닌 것 먼저 — 등록부가 View 보다 먼저 읽히게, 그 안은 이름 차례) 테스트가 같은 함수를 읽는다. 층도 표가 아니라 파일이 말한다: 머리 주석 첫 줄 `/* Model|ViewModel|View — …` 이고 파일 이름과 맞아야 한다(view-* = View, 그 밖 = Model·ViewModel — 다르거나 없으면 실패). HD 이름의 주인 모듈은 파일의 `HD.이름 =` 에서 읽는다(이름 하나 = 주인 하나)
- 화면 ↔ 캔버스 메시지(`hd-pick`·`hd-links`·`hd-link-go` 등)와 "보내기" 요청문 형식은 `/hyper-design:fix`가 읽으므로 바꾸지 않는다
- 추가된 메시지(기존 것은 그대로): `hd-hit-at {x, y}` → 화면이 `hd-hit {screen, path, text, rect, to}`로 답한다(그 자리 요소, 없으면 `path:null`). 1.5초 안에 답이 없으면(palette.js 없음) 캔버스는 "이 화면은 편집할 수 없어요"를 띄운다
- `hd-hit-at`에 `leaf:true`를 붙이면 글자를 가진 그 자리 요소로 답한다(글자 고치기 — 자기 글자가 없으면 글자 가진 자손이 하나일 때만, 아니면 `path:null`). 답에는 고칠 글 전체 `full`이 있다
- 메모 자리(task 11): `hd-picked`·`hd-hit` 답에 `quote:{exact, prefix, suffix}`(요소 글 ≤200자, 문서 글에서 앞·뒤 32자). `hd-locate {items:[{key, path, quote}]}` → 화면이 `hd-located {items:[{key, rect|null, how:'path'|'quote'|'none'}]}` — path 가 있고 (quote 가 없거나 그 요소 글에 `quote.exact` 가 있음) = path, 아니면 문서 글에서 `quote.exact` 를 찾아(앞·뒤 글이 맞는 곳 먼저) 그 글을 감싼 가장 작은 요소 = quote, 못 찾으면 none. 캔버스는 카드 iframe 이 실릴 때(다시 실을 때 포함)·크게 보기가 실릴 때·메모가 바뀐 카드에 묻는다. rect 는 지금 `rect` 와 같은 화면 CSS px
- `hd-pending {items:[{path, text} | {path, remove:true}]}` → 화면이 그 요소의 글 전체를 잠시 바꾸거나(빈 글 허용) 지울 요소를 숨겨 점선으로 보인다(반영 대기 미리보기, `items:[]`이면 되돌림 — `contract/edits.md`)
- 화면 파일을 바꾸는 편집(트리거 지정·해제, 잇기, 도착 바꾸기, 연결 끊기, 글자·카드 이름·설명 고치기)은 메모(`intent=change`, 메모 안 `edit` 종류)로 쌓여 같은 "보내기" 요청문으로 나간다. 카드 이름·설명은 `path=screens.json > screens[id=…] > title|purpose`. 보내지 않은 편집이 있으면 새로고침·닫기 전에 묻고, 변경 기록은 `hd-edit-log:` 키에 남는다

## 새 기능 더하기 (공용 파일을 고치지 않는다)
1. `modules/<이름>.js`(첫 줄 `/* Model — 맡은 일`) · `modules/view-<이름>.js`(첫 줄 `/* View — 맡은 일`) — 빌드가 `modules/*.js` 를 모두 끼우고 층은 파일 이름 + 머리 주석으로 정해진다(`build_canvas.py` 그대로)
2. View 파일 끝에 등록 한 번: `HD.feature('<이름>', {needs: ['$', 'toast', …], mount: function (ctx) { … return api; }})` — ctx 칸은 `modules/features.js` 머리 주석. 셸이 그 api 를 써야 할 때만 템플릿에 한 줄(`X = FT.<이름>`), 아니면 0줄
3. 테스트: Model 규칙은 `tests/test_canvas_unit_<이름>.py`(이름만으로 unit), 브라우저 테스트는 `@pytest.mark.area(...)` 를 단다(`conftest.py` 그대로 — 새 영역일 때만 `AREAS` 한 줄)
4. 계약: `contract/<이름>.md` — 규칙 몇 줄 + '고치면 돌릴 것'(`-m`) 한 줄. `contract.md` 는 그대로
5. 셸 ctx 에 없는 칸이 필요하면 그때만 셸의 `HD.mountAll({...})` 에 칸을 더한다(모든 기능이 함께 쓰는 공통 칸만)

## 책임 게이트 (조각마다 — god object 를 다시 만들지 않게)
기계 검사(`tests/test_canvas_modules.py`의 `gate`, unit 층에서 돈다):
- **책임** — 모듈 머리 주석 첫 줄 = `/* 층 — 맡은 일 */`. 한 줄로 못 쓰면 모듈을 나눈다
- **협력** — 의존은 아래 층으로만: Model 은 다른 층을 모르고, ViewModel 은 View 를 모른다. View 끼리는 `HD.viewX` 를 직접 부르지 않는다 — 셸이 `mount(ctx)` 로 함수를 건네거나 의도(`dispatch`)로 잇는다
- ~~비대 방지(셸 function 수 래칫)~~ — 2.2 재평가로 뺌(10-21): 진짜 1 · 잡음 2 · 대응 6분. 셸에 새 기능을 두지 않는 것은 조각 보고(아래)에서 사람이 본다

조각 보고(커밋 전, 사람이 본다):
- **자율** — 새 상태마다 주인 모듈 하나와 저장 키 하나. 다른 모듈은 그 상태를 읽기만 하거나 의도를 보낸다
- **오류 탐지** — 실패를 숨기지 않는다. 빈 `catch {}` 는 저장소 읽기·쓰기에만(이유 주석 한 줄), 사용자 동작이 실패하면 토스트로 알린다. 저장값이 깨졌거나 없는 id 를 받으면 기본값으로 돌아가고 콘솔에 `[hd]` 경고 한 줄. 새 Model 의 규칙은 unit 테스트로 고정한다(오류가 브라우저 테스트가 아니라 unit 에서 먼저 잡히게)
- 이 게이트는 캔버스 밖 새 기능(프로젝트 열기·앱 프로젝트 등)에도 같은 뜻으로 적용한다: 층(Model 순수 · View `mount(ctx)` · 셸은 붙이는 줄만), 상태마다 주인 하나
- 새 모듈마다 한 줄: 맡은 일 · 가진 상태 · 받는 `ctx` · 내보내는 의도/함수
- 셸에 새로 생긴 위쪽 `function` 이 있으면 왜 모듈이 아닌지 한 줄

## 로컬 도우미 (`helper.py`, 선택)
- 포트(#270): `--port` 가 없으면 `<out>/.hd-helper.json` 의 지난 포트를 먼저 열고, 막혔으면 빈 포트로(`[hd]` 한 줄) — 주소(origin)가 같아야 캔버스 localStorage(도크·테마·설정·보낸 것 보기·안 보낸 표시)가 이어진다. `.hd-helper.json` = 떠 있는 동안 `{url, pid, port, token}`(주소를 찍기 전에 씀) · 정상 종료 뒤 `{port}`
- 한 out 에 도우미 하나(#271): 시작할 때 `.hd-helper.json` 의 pid 가 살아 있고 그 주소가 답하면 띄우지 않고 한국어 한 줄 + 종료 코드 1. 죽은 pid·답 없는 주소면 덮어쓴다(규칙 `hd_model.start_verdict`)
- 읽기(`GET /api/state`·`index.html` 의 `__hdState`)는 빌드 자물쇠 없이 읽는다(쓰기가 임시 파일 + `os.replace` — Windows 에서 읽는 중이라 바꾸기가 막히면 잠깐 다시). 깨진 파일일 때만 자물쇠 안에서 옮긴다. 쓰기(apply·delete·restore·PUT·reply·claim·release)는 그대로 하나씩 — 긴 빌드 중에도 `hd` 핑(1초)이 답한다
- 127.0.0.1에만, 실행마다 새 토큰(주소의 `?hd=`·머리글 `X-HD-Token`), Host 검사. 쓰는 곳은 `<out>` 안뿐이고(안인지는 `hd_projects.inside` — `hd` 와 같은 out 규칙 하나, #282), 쓰기 전 원본을 `<out>/.hd-history/<시각>/`에 남긴 뒤 다시 빌드한다(실패하면 되돌림). CLI 로 뜬 도우미는 `hd open` 과 같은 `build_ref.py`(저장소면 git HEAD 코드, 아니면 작업 트리 — #278)로, 같은 프로세스에서 `make_server` 를 쓰는 테스트는 작업 트리 `build_canvas.py` 로
- 정리(#281): 시작할 때와 쓰기마다 `.hd-history/<시각>/` 이 가장 새 200개 밖이면서 30일보다 오래됐으면 지우고, `.hd-queue/<시각>.txt` 중 보냄·걷힘 표시(`<시각>.sent` — paseo send 가 받았을 때 도우미가 씀 · `<시각>.lifted` — 다 처리한 쪽이 씀)가 붙은 7일 넘은 것을 표시와 함께 지운다. 시각 이름이 아닌 것(`fix-components.css` 등)은 손대지 않는다(고르기 = `hd/helper_model.py`). 떼어 띄운 도우미의 로그는 `<out>/.hd-helper.log`
- 바로 쓰는 편집: 글자 · 카드 이름·설명(`screens.json`) · 잇기/도착 바꾸기 · 끊기/트리거 해제. 나머지 메모는 요청문 그대로 `<out>/.hd-queue/<시각>.txt`에 쓰고, `--paseo-agent`가 있으면 그 파일을 `paseo send … --prompt-file … --no-wait`로 넘긴다
- `POST /api/watch {files}` → `{mtimes: {file: mtime|null}}`(out 밖·없는 파일 = null) — AI 수정 중 덮개가 끝을 아는 유일한 신호
- 도우미로 열어도 저장 키는 file://로 열 때와 같다(`window.__hdKeyPath`). 도우미가 없거나 꺼져 있으면 '보내기'는 지금처럼 요청문을 복사한다
- 프로젝트 상태 파일 `<out>/.hd-canvas.json` = `{"version":1, "rev":N, "updated":"<iso>", "state":{"notes":…, "card-pos":…, "edit-log":…, "link-names":…, "hidden":…, "locked":…, "folders":…, "busy":…, "note-seq":…}}`(값은 풀어 둔 JSON, 해시 없는 이름, 모르는 키는 그대로) — 터미널 에이전트(`hd`)가 읽는 곳. `index.html` 을 줄 때 `window.__hdState = {rev, state}` 를 끼워 넣는다
- `GET /api/state[?since=<rev>]` → `{rev, state}`(없으면 rev 0) · since 가 파일 rev 와 같으면 몸통 없이 `{rev, unchanged:true}`(#273 — 2초 읽기), 0 이상 정수가 아니면 400 · `PUT /api/state {rev, state:{바뀐 이름: 값|null(지움)}}` → rev 가 파일과 같으면 합쳐 `rev+1` 로 쓰고 `{rev}`, 다르면 `409 {rev, state}` · 깨진 JSON 400 · 2 MB 넘음 413 `{error}`(크기와 "완료 메모를 보관으로 옮기세요"). 둘 다 `X-HD-Token`. 쓰기는 임시 파일 + `os.replace`, 바로 앞 것 하나는 `.hd-canvas.json.bak`. 깨진 상태 파일은 `.hd-canvas.json.corrupt-<시각>` 으로 옮기고 한 줄 남긴 뒤 빈 상태(도우미는 멈추지 않는다). 점으로 시작하는 파일이라 정적 경로로는 내주지 않는다
- 완료 메모 보관(#273): `POST /api/archive {notes:[{…}]}` → 메모마다 JSON 한 줄을 `<out>/.hd-notes-archive.jsonl` 끝에 붙여(있던 것 + 새 줄을 임시 파일에 쓰고 `os.replace`, 쓰기 자물쇠 안) `{ok:true, count}` · 객체 목록이 아니면 400(쓰지 않음) · `GET /api/archive` → `{notes:[…]}`(마지막 2000 줄, 새것이 뒤, 깨진 줄은 건너뛰고 `[hd]` 한 줄). 둘 다 `X-HD-Token`. 상태 파일에서 빼는 일은 캔버스(`{ok}` 뒤 한 번 저장)

## 테스트 층 (캔버스를 고치는 모든 세션이 따른다)

| 층 | 파일 | 무엇을 | 시간 |
|---|---|---|---|
| unit | `tests/test_canvas_modules.py` · `test_canvas_unit_*.py` | 순수 모듈(node)·I/O 없는 Python: 그래프·길찾기·태그 자리·색·리듀서·설정·카메라 계획·순수성·책임 게이트 | 약 5초(`-m unit`) |
| slow | `test_canvas_unit_*.py` 안의 `@pytest.mark.slow`(build_ref git·실제 빌드 · `/api/watch` 서버) | 하위 프로세스·서버가 드는 것 — unit 에서 빠짐 | 약 7초(`-m slow`) |
| 브라우저 | `test_canvas_baseline.py`(지금 입력 규칙 고정) · `test_canvas_v2.py` · `test_canvas_edit.py`(편집 기능) | DOM 연결·실제 조작 | 테스트당 1~17초 |
| 도우미 | `test_canvas_helper.py` | `helper.py` 편집·적용·서버(브라우저 1개) | 약 11초 |

unit 은 I/O 가 없다: git·하위 프로세스 빌드·HTTP 서버가 드는 새 테스트는 `@pytest.mark.slow` 를 붙인다(전체 실행에서 돈다). `build_ref.py` 를 고치면 `-m slow`.

**격리(serial)**: `-n` 에서만 가끔 깨지는 테스트는 `tests/conftest.py` 의 `SERIAL` 에 둔다 — `-n` 실행에서는 빠지고(고르지 않음), 전체 실행 뒤 한 번 `pytest tests -m serial`(-n 없이)로 따로 돌린다. 지금: `test_line_click_shows_end_handles_and_drag_retargets`(task 20·28: 재현되지 않아 원인 미확인 — 다시 깨지면 그때 핀 아래 요소·카드 상자를 잡는다). `test_v2_no_vertical_through_cards` 는 task 28 이 원인(부하에서 카드 재배치 뒤 선이 늦게 다시 그려짐)을 잡아 다시 재기로 고치고 뺐다. 원인을 찾아 고치면 `SERIAL` 에서 뺀다.

브라우저 테스트는 테스트 파일 안에서 영역 표시를 받는다 — 테스트마다 `@pytest.mark.area("tools", "notes")`(파일 전체면 `pytestmark = pytest.mark.area(...)`). conftest 가 그것을 `-m` 으로 고르는 표시로 바꿔 단다. 영역 표시가 없거나 `AREAS` 에 없는 영역이면 수집 단계에서 실패한다. `tests/conftest.py` 를 고칠 일은 새 영역(`AREAS` 한 줄)뿐이다:
`input`(판 조작) · `modal`(크게 보기·주석) · `notes`(메모) · `tools`(도구 막대·카드 옮기기·편집) · `flow`(판에 늘 그리는 선) · `links`(고르기 강조·화면 안 연결) · `motion`(카메라·전환) · `helper`(로컬 도우미) · `dock`(오른쪽 패널 도크).

**어디를 고치면 무엇을 돌리나**

| 고친 곳 | `-m` |
|---|---|
| 기능별(`contract/<기능>.md` 의 '고치면 돌릴 것') | 그 파일에 적힌 `-m` |
| `modules/features.js`(기능 등록부) · 셸 `HD.mountAll` ctx | `unit or notes or modal or tools`(등록부로 붙는 기능의 영역) |
| `modules/route.js` · `graph.js` · `style.js` · `prefs.js` · `view-links.js` · `view-link-panel.js`(연결 패널: 이름·휴지통) | `unit or links` |
| `modules/view-menu.js`(위쪽 보기 메뉴 = 배율 칩 · 창 메뉴 · Tab) · 위쪽 줄 | `unit or menu or dock` |
| `modules/theme.js` · `view-theme.js`(테마 패널: 고르기·복제·색 네 칸·대비) · `foundation/palette.js` 의 `hd-theme-vars` | `unit or theme` |
| `modules/viewport.js` · `view-viewport.js`(창 나누기·동시 스크롤 · 카메라 계산 zoomAt·fit) | `unit or menu or input` |
| `helper.py` · `modules/view-sync.js`(화면 파일에 바로 쓰기: 잇기·끊기·삭제·되살리기·바뀐 카드만 다시·모드 칩) | `unit or helper` |
| `modules/camera.js` · `view-motion.js` · `motion.css` | `unit or motion` |
| `modules/view-edge-pan.js` (끄는 중 가장자리 판 밀기) | `unit or tools or input` |
| `modules/selection.js` · `view-select.js` (고른 카드: 누르기 = 고르기 + 연결 강조, Shift = 여러 장) | `unit or tools or input or links` |
| `canvas_template.html` 이동·확대·입력 | `input` |
| `canvas_template.html` 도구 막대·카드 옮기기 · `drawArrows` | `tools or flow` |
| `modules/view-lines.js` · `graph.overview` · `style.rowColor` (판의 선 하나뿐: 쌍마다 하나·줄 색·번호·태그·강조·자르기 맞춤·보이기/굵기/투명도/색) | `unit or flow or links or tools` |
| `foundation/palette.js` 의 `quote`·`hd-locate` | `unit or notes or modal` |
| `foundation/palette.js` | `links or modal or tools` |
| `helper.py` | `helper`(+ `-m slow -k helper_upkeep`, hd 테스트) |
| `build_canvas.py` | `unit or flow or links` |
| 여러 영역에 걸친 변경 | 그 영역들을 `or` 로 묶어서(전체는 아래 3 에서만) |

**돌리는 순서 (전체를 반복해서 돌리지 않는다)**
1. 고치는 동안: `-m unit` + 그 기능의 테스트 하나(`-k 이름`) — 수 초.
2. 큰 실행 전: 바꾸거나 지운 선택자·키·문구를 `tests/` 에서 먼저 찾아(grep) 걸리는 옛 테스트를 고친다 — 큰 실행을 '어디가 깨지나' 찾기에 쓰지 않는다.
3. 커밋 직전: 위 표의 영역(`-m "unit or 영역"`). 실패하면 고친 뒤 실패한 것만(`--lf`) 다시.
4. 번호 조각(2.5 · 2 · 2.2 …) 끝: 전체 한 번(약 9분). a·b·c 하위 조각에서는 돌리지 않는다. 실패하면 `--lf` 로 확인하고, 전체를 다시 돌리지 않는다.
   브라우저 테스트가 든 실행(영역·전체)은 `-n 4`(pytest-xdist, 일꾼마다 페이지를 따로 빌드 — test_canvas_edit.py 219초 → 73초)로 나눠 돌린다. 한 테스트만 고칠 때·`--lf` 는 나누지 않는다.
   `-n` 전체 실행 뒤에는 `-m serial`(-n 없이)을 한 번 더 — 격리 테스트는 `-n` 실행에서 빠져 있다.
   전체 실행에는 `--durations=20` 을 붙여 느린 테스트 상위 목록을 남긴다(따로 프로파일링 실행을 하지 않는다). 큰 실행 전에는 바꾸거나 지운 선택자·id·함수 이름을 테스트에서 grep 해 `-k` 로 먼저 돌린다(전역 규칙 `~/.claude/ctx/testing.md` R54~R56).
5. 스크린샷은 검문·눈 판정이 필요할 때만 따로 찍는다.
6. 검토 비용 기록(`tests/tracking/`): 실행은 conftest 가 `runs.json` 에 자동으로 남긴다. 조각을 커밋할 때 `process.json` 에 한 항목(테스트 분·전체 수·게이트 걸림 진짜/잡음·잡은 버그·낭비와 고칠 점), 번호 조각 끝에 `python3 tests/tracking/review.py` 로 한도를 넘은 곳을 보고 규칙을 고친다.

고정본(`runs/laundry-v1`·`gym-v2`·`dayfine-onboarding-v1`)은 저장소에 없으면 그 테스트가 건너뛰어진다 — "통과"가 아니라 "건너뜀"인지 요약 줄에서 확인한다.
