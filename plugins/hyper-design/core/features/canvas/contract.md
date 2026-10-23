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
- `caption`(Model)·`view-caption`(View) — 카드 아래 글 한 상자(H16): 제목·설명·정책 줄을 한 상자에서 고치고, 바뀐 칸마다 반영 대기 편집(`title`·`purpose`·`policy`[i]) 을 한 번의 `addEdits` 로(되돌리기 한 번). 정책 줄 지우기 있음(op:delete — 비운 줄, 원래 번호, helper 가 큰 번호부터 한 번에), 더하기는 allowAdd 일 때만. 설명 비우기 = '' 편집, 제목은 비울 수 없음(편집 없음, `ctx.toast`). 빈 레이아웃 카드도 같은 상자(#225): 이름(한 줄)·목적(여러 줄) → 편집이 아니라 그 메모 안 `n.value`·`n.purpose`(셸 `editLayout`, 되돌리기 한 번), 목적은 `say.layout` 요청문의 첫째 브리프. 칸 안내 글은 `ctx.hint`. Shift+Enter(#226): 제목 = 설명으로 넘어감(제목은 한 줄), 설명·목적 = 줄바꿈, 정책 줄 = Enter 와 같음
- `align`(Model)·`view-align`(View) — 정렬 패널(H18, 도크 패널 `align`): 고른 카드(잠김·숨김·삭제 대기 빼고)의 상자로 맞추기 6·간격 같게 2·늘어놓기 2(간격 칸 px, 키 `hd-align-gap`). 옮기기는 셸 `moveCards` 가 카드 옮긴 자리(`hd-card-pos:`)에 더하고 기록 한 단계
- `folders`(Model)·`layers`(Model, 폴더 줄)·`view-layers`(View) — 레이어 폴더(H17): 패널에서만 묶음(판 카드·화면 파일 그대로, 키 `hd-folders:`), 데이터 줄 = 고정 폴더, 폴더·줄의 [가로로/세로로 늘어놓기]는 정렬 패널 간격으로 셸 `arrangeCards`
- `pop-place`(Model)·`view-pop-place`(View) — 메모 창(`#pop`) 틀(#223): 머리 줄 끌어 옮기기·오른쪽 아래 모서리 크기(가장 작게 260×160, 창 안으로). 한 번 옮기거나 키우면 다음부터 늘 그 자리(키 `hd-pop`, 모든 캔버스 공용), 머리 줄 두 번 누르기 = 자동 자리. 열린 동안 대상 카드에 `.memo-target` 테두리. 자동 자리 계산은 셸 `placePop`
- `view-thread`(View) — 카드 메모 배지 → 그 화면 메모 묶음(#224, Word 메모처럼): 배지(`role=button`, `view-notes` 가 그림) 옆 `#thread` 에 요소·종류·글 전체, 줄마다 [고치기]·[지우기], 아래 [메모 추가]. 고치기·지우기는 메모 패널과 같은 셸 `editMemo`·`delMemo`(지우기 = 되돌리기 한 단계), 더하기 = `openCardMemo`. 배지 누르기는 카드 고르기·끌기로 가지 않는다. Esc·바깥 누르기 = 닫기, 메모가 바뀌면 `renderNotes` 가 `refresh`
- `annotation`(Model)·`view-pins`(View) — 메모 주석·핀(task 11, W3C Web Annotation 처럼 대상 = 선택자 여럿): 메모마다 화면별로 바뀌지 않는 번호 `n.no`(만들 때 그 화면에서 지금까지 쓴 가장 큰 번호 + 1, 지워도 다시 쓰지 않음 — 키 `hd-note-seq:` = `{화면 id: 마지막 번호}`, 옛 메모는 불러올 때 화면마다 목록 차례대로 `migrate`). 대상마다 `path`·`rect` 에 `quote:{exact, prefix, suffix}`(palette.js 가 채움, 없으면 `exact = text`). 답 `n.replies`(AI: 반영됨·일부·대체됨·답변·질문 — `hd reply` #231 · 사람: 확인 = 완료, 다시 = 다시 열기, `n.sent=false`) → 상태는 저장하지 않고 계산(`status`: draft·working·decide·partial·done, `isOpen` = done 아님, `rework` = 다시 수, `validReply` = 종류별 꼭 있는 칸). 판 핀: 실린 카드의 열린 사람 메모(편집·화면 전체·빈 레이아웃 빼고) 대상 중 다시 찾은 자리(`hd-locate`)가 있는 것만, 고른·올린·막 메모를 단 카드 또는 화면이 실제의 60% 이상일 때만 보임, decide = `--ui-accent` 하나·나머지 `--ui-badge`. 핀 누르기 = 그 메모로 열린 `view-thread`(셸이 `ctx.openThread`), 묶음 줄에 올리기 = 그 핀·요소 테두리(`ctx.highlight`). 크게 보기 핀(`drawPins` → `view-pins.paint`)도 `n.no`·다시 찾은 자리. 완료한 메모는 핀·배지 수·메모 패널·보내기에서 빠지고 묶음 아래 접힌 '완료 N' 에 [다시 열기]. 메모 패널 [보낸 것 완료로] = 보낸 열린 메모에 '확인'(지우지 않음), 보낸 편집은 예전처럼 목록에서 뺌 — 되돌리기 한 단계
- `state-file`(Model)·`view-state-sync`(View) — 프로젝트 상태 파일(#228): 프로젝트별 키(`hd-notes:`·`hd-card-pos:`·`hd-edit-log:`·`hd-link-names:`·`hd-hidden:`·`hd-locked:`·`hd-folders:`·`hd-busy:`·`hd-note-seq:`, 모두 `hashStr(KEYPATH)`)의 읽기·쓰기 주인은 `view-state-sync` 하나(셸·모듈은 `ST.getItem`·`ST.setItem` 을 받는다). 도우미로 열면 `<out>/.hd-canvas.json` 이 진실 원천이고 브라우저 저장소는 캐시: 시작 때 `window.__hdState`(동기) — 파일이 있으면 파일이 이기고 캐시를 덮음, 파일이 없고 브라우저에 값이 있으면 한 번 올림(rev 0 → 1). 쓰기는 300ms 모아 바뀐 키만 `PUT /api/state`, 닫을 때(`pagehide`) 마저 보냄. 409 = 이번 변경을 버리고 토스트 "다른 곳에서 바뀌어 다시 불러왔어요" 뒤 다시 불러오기. file://·토큰 없음·깨진 스냅숏(`[hd]` 경고) = 브라우저 저장소 그대로. 전역 설정 키(`hd-dock`·`hd-pop`·`hd-canvas-prefs`·`hd-themes`…)는 파일로 가지 않는다
- AI 답이 살아서 옴(A2a, task 16): `view-state-sync` 가 페이지가 보이는 동안 2초마다(숨으면 10초) `GET /api/state` — 파일 `rev` 가 더 크고 보내지 않은 변경이 없으면, 바뀐 이름이 `notes`·`note-seq` 뿐일 때 제자리에서 받아 `ctx.onExternal(이름들)` → 셸 `adoptExternal`(같은 id 메모 객체에 칸만 바꿔 넣음 = `annotation.adopt`, 되돌리기 기록 유지) → `saveNotes(true)`(번호를 새로 매긴 때만 다시 씀) → 닿은 카드만 다시. 다른 이름도 바뀌었으면 지금처럼 알리고 다시 불러오기, 보내지 않은 변경이 있으면 먼저 보냄(409 = 충돌 길). 네트워크 실패 3번 연속 = 멈추고 토스트 한 번, 창 focus 에 다시. 묶음(`view-thread`): 답마다 회색 한 줄 `annotation.says`(반영됨 줄에 올리면 `tip` = 화면·캡처), 사람 답은 작게 '완료함/다시 엶' + 시각, 기다리는 질문(`annotation.question`)은 고를 것 단추 → 셸 `answerQuestion` = 질문 메모에 `{kind:'확인', by:'user', answer}`(답 검사 `OPTIONAL` — `hd_model` 과 같음) + 같은 대상 새 메모 `질문 "…" → 고른 것`(intent change)을 그것만 셸 `sendList`(위쪽 [보내기]와 같은 길)로, 되돌리기 한 단계(보내지면 보낸 자리 경계). '결정 필요'(#232, 강조색은 이것 하나): 위쪽 줄 `#decn` '결정 필요 N'(0 이면 숨김, 누르면 메모 패널을 그것만으로) · 메모 패널 `#ndec` '결정 필요만' · 그런 메모가 있는 카드 배지 `.decide`(수는 열린 메모 수). 받는 곳 없음(R4): `--paseo-agent` 없이 도우미로 열면 `#aichip` '받는 곳 없음', 보낸 뒤 토스트가 대기열 파일에만 갔다고 붙이는 법(`hd notes` · `--paseo-agent`)과 함께 말하고, 묶음 상태 말은 working 대신 '대기열'(`annotation.label`). 답 검사·상태는 `hd/tests/fixtures/replies.json` 을 JS(`test_canvas_unit_annotation.py`)와 Python 이 함께 읽는다(drift 검사)
- 새 기능은 `canvas_template.html` 밖 모듈로 만들고 템플릿에는 붙이는 줄만 둔다(스트랭글러 — 맞닿는 기존 덩어리는 그 조각에서 같이 빼낸다). 판 바깥 UI 색은 `:root`의 `--ui-*`(무채색)만 쓴다
- 오른쪽 패널 도크: 배치는 `dock.js`(키 `hd-dock`, 모든 캔버스 공용), 그리기·끌기는 `view-dock.js`. 패널(`#pLinks`·`#pShow`·`#pNotes`·`#pLayers`)은 옮겨 붙일 뿐 안의 id(`#legend`·`#notes`·`#hidl`)와 그 `hidden` 뜻은 그대로다
- `edits.js` — 편집 메모 하나가 진실 원천: 반영 대기 선·빈 레이아웃·글자 미리보기·도우미가 바로 쓸 것은 모두 메모에서 계산한다. 요청문(`request`)에서 요청 글의 줄바꿈은 `요청: ` 글자 자리에 맞춰 들여 쓴 다음 줄로 남는다(한 줄 메모는 예전 그대로)
- 한 번 보내기가 말하는 것(task 17 · A2b, `edits.items` → `request`, 항목 머리·text·요청 세 줄 형식은 그대로): **빈 레이아웃 = 항목 하나**(R5) — 보낼 목록에 그 `new-screen` 메모가 있으면 같은 화면 메모(편집 아닌 것)는 따로 나가지 않고 `요청:` 아래 `       - 본문`(번호 `n.no` 차례, 질문은 `(질문) `)으로 실리며 함께 '보냄'. 목적도 메모 본문도 없으면(복제 빼고, `edits.emptyLayouts`) 보내기는 그대로 가고 결과 알림 앞에 한 번 `say.emptyLayout`. **같은 글 = 항목 하나**(R6) — 같은 화면·의도·범위·공백 정리한 글의 메모(편집은 하나씩)와 여러 요소 메모는 첫 경로가 `path=`, 나머지는 `   다른 곳: 경로 ("20자 이하 글") · …`. **범위**(R7) — 메모 `n.scope` = `element|screen|all`(없음 = element, 상태 파일 판은 그대로). 메모 창 `#pscope`(말은 `annotation.SCOPES`, 기본 이 요소 · 화면 전체 메모는 이 화면), 요청문 `   범위: 이 화면 전체|모든 화면`, 묶음 줄 `.thsc`(`annotation.scopeWord`), 핀은 그대로. 질문에 고른 답의 새 메모는 질문 메모의 범위를 이어받는다. 덧붙는 줄 차례 = 메모 본문 · 범위 · 다른 곳
- `notes`(Model) — 메모 목록 저장소(키 `hd-notes:`, 읽기·쓰기는 셸): 목록 하나(`list`·`add`·`remove`·`find`·`unsent`)와 `commit()` = 지난 저장 뒤 메모가 바뀐(더함·뺌·제자리 고침) 화면 id. 셸 `saveNotes` 는 그 카드만 다시 그린다(배지·삭제 대기·카드 글·`hd-pending`), 판의 선은 `linesKey`(잇기·끊기·삭제·빈 레이아웃 메모)가 바뀔 때만 다시
- Model·ViewModel 파일은 DOM·저장소·메시지를 쓰지 않는다(`tests/test_canvas_modules.py`의 순수성 검사 — 층 표 `LAYER` 의 Model·ViewModel 전부. 모듈 목록은 `build_canvas.MODULES` 하나뿐이고 테스트가 그것을 읽으며, view-* 가 아닌 모듈이 `LAYER` 에 없으면 실패)
- 화면 ↔ 캔버스 메시지(`hd-pick`·`hd-links`·`hd-link-go` 등)와 "보내기" 요청문 형식은 `/hyper-design:fix`가 읽으므로 바꾸지 않는다
- 추가된 메시지(기존 것은 그대로): `hd-hit-at {x, y}` → 화면이 `hd-hit {screen, path, text, rect, to}`로 답한다(그 자리 요소, 없으면 `path:null`). 1.5초 안에 답이 없으면(palette.js 없음) 캔버스는 "이 화면은 편집할 수 없어요"를 띄운다
- `hd-hit-at`에 `leaf:true`를 붙이면 글자를 가진 그 자리 요소로 답한다(글자 고치기 — 자기 글자가 없으면 글자 가진 자손이 하나일 때만, 아니면 `path:null`). 답에는 고칠 글 전체 `full`이 있다
- 메모 자리(task 11): `hd-picked`·`hd-hit` 답에 `quote:{exact, prefix, suffix}`(요소 글 ≤200자, 문서 글에서 앞·뒤 32자). `hd-locate {items:[{key, path, quote}]}` → 화면이 `hd-located {items:[{key, rect|null, how:'path'|'quote'|'none'}]}` — path 가 있고 (quote 가 없거나 그 요소 글에 `quote.exact` 가 있음) = path, 아니면 문서 글에서 `quote.exact` 를 찾아(앞·뒤 글이 맞는 곳 먼저) 그 글을 감싼 가장 작은 요소 = quote, 못 찾으면 none. 캔버스는 카드 iframe 이 실릴 때(다시 실을 때 포함)·크게 보기가 실릴 때·메모가 바뀐 카드에 묻는다. rect 는 지금 `rect` 와 같은 화면 CSS px
- `hd-pending {items:[{path, text}]}` → 화면이 그 요소 글을 잠시 바꿔 점선으로 보인다(반영 대기 미리보기, `items:[]`이면 되돌림)
- 화면 파일을 바꾸는 편집(트리거 지정·해제, 잇기, 도착 바꾸기, 연결 끊기, 글자·카드 이름·설명 고치기)은 메모(`intent=change`, 메모 안 `edit` 종류)로 쌓여 같은 "보내기" 요청문으로 나간다. 카드 이름·설명은 `path=screens.json > screens[id=…] > title|purpose`. 보내지 않은 편집이 있으면 새로고침·닫기 전에 묻고, 변경 기록은 `hd-edit-log:` 키에 남는다

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
- 127.0.0.1에만, 실행마다 새 토큰(주소의 `?hd=`·머리글 `X-HD-Token`), Host 검사. 쓰는 곳은 `<out>` 안뿐이고, 쓰기 전 원본을 `<out>/.hd-history/<시각>/`에 남긴 뒤 `build_canvas.py`로 다시 만든다(실패하면 되돌림)
- 바로 쓰는 편집: 글자 · 카드 이름·설명(`screens.json`) · 잇기/도착 바꾸기 · 끊기/트리거 해제. 나머지 메모는 요청문 그대로 `<out>/.hd-queue/<시각>.txt`에 쓰고, `--paseo-agent`가 있으면 그 파일을 `paseo send … --prompt-file … --no-wait`로 넘긴다
- `POST /api/watch {files}` → `{mtimes: {file: mtime|null}}`(out 밖·없는 파일 = null) — AI 수정 중 덮개가 끝을 아는 유일한 신호
- 도우미로 열어도 저장 키는 file://로 열 때와 같다(`window.__hdKeyPath`). 도우미가 없거나 꺼져 있으면 '보내기'는 지금처럼 요청문을 복사한다
- 프로젝트 상태 파일 `<out>/.hd-canvas.json` = `{"version":1, "rev":N, "updated":"<iso>", "state":{"notes":…, "card-pos":…, "edit-log":…, "link-names":…, "hidden":…, "locked":…, "folders":…, "busy":…, "note-seq":…}}`(값은 풀어 둔 JSON, 해시 없는 이름, 모르는 키는 그대로) — 터미널 에이전트(`hd`)가 읽는 곳. `index.html` 을 줄 때 `window.__hdState = {rev, state}` 를 끼워 넣는다
- `GET /api/state` → `{rev, state}`(없으면 rev 0) · `PUT /api/state {rev, state:{바뀐 이름: 값|null(지움)}}` → rev 가 파일과 같으면 합쳐 `rev+1` 로 쓰고 `{rev}`, 다르면 `409 {rev, state}` · 깨진 JSON 400 · 2 MB 넘음 413. 둘 다 `X-HD-Token`. 쓰기는 임시 파일 + `os.replace`, 바로 앞 것 하나는 `.hd-canvas.json.bak`. 깨진 상태 파일은 `.hd-canvas.json.corrupt-<시각>` 으로 옮기고 한 줄 남긴 뒤 빈 상태(도우미는 멈추지 않는다). 점으로 시작하는 파일이라 정적 경로로는 내주지 않는다

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
| `modules/state-file.js` · `view-state-sync.js`(프로젝트별 키 = 상태 파일 · 캐시 · 409 · 살아 있는 새로 받기) · `helper.py` `/api/state` · 셸 `adoptExternal` | `unit or helper or notes` |
| `modules/busy.js` · `view-busy.js`(AI 수정 중 덮개: 터미널로 넘긴 화면 · 화면 파일이 바뀌면 걷힘 · [걷기]) · `helper.py` `/api/watch` | `unit or helper or notes` |
| `modules/line-ends.js` · `view-line-ends.js`(선 누르기 = 쌍 강조 + 도착 끝 손잡이 · 끌어 놓기 = 도착 바꾸기) | `unit or flow or tools` |
| `modules/caption.js` · `view-caption.js`(카드 아래 글 한 상자: 두 번 누르기·글자 도구·카드 메뉴 이름/설명 → 바뀐 칸마다 반영 대기, 되돌리기 한 번 · 빈 레이아웃 이름·목적 = 셸 `editLayout`) | `unit or tools or notes` |
| `modules/pop-place.js` · `view-pop-place.js`(메모 창 옮기기·크기·저장한 자리·대상 카드 표시) · 셸 `placePop`·`showPop`·`hidePop` | `unit or notes or modal or tools` |
| `modules/view-thread.js`(카드 메모 배지 → 그 화면 메모 묶음: 고치기·지우기·메모 추가·완료·다시 열기·답 줄·질문 고르기) · 셸 `editMemo`·`delMemo`·`addReply`·`answerQuestion`·`sendList` | `unit or notes or modal or tools or helper` |
| `modules/annotation.js`(번호·답·상태·답 검사) · `view-pins.js`(판·크게 보기 핀, 다시 찾기, 핀 → 묶음) · 셸 `numberNotes`·`drawPins`·[보낸 것 완료로] | `unit or notes or modal or tools` |
| `foundation/palette.js` 의 `quote`·`hd-locate` | `unit or notes or modal` |
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
