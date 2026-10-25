# 앱 프로젝트 — Dayfine 앱 카드 (features/app · #222 1–3)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(task 27). 코드는 `core/features/app/`.

정적 HTML 화면 대신 **진짜 앱 컴포넌트**(Dayfine `C:/Code/dictionary/ui_host/popup`, Svelte 5 + Vite)의 twin 무대를 카드로 띄운다.
카드 = 앱 개발 서버의 무대 페이지 주소. 메모로 고르면 답에 소스 위치(`src: 파일:줄`)가 실린다 → 앱 세션 에이전트가 진짜 코드를 고치고 Vite HMR 이 카드를 바꾼다.

## 여는 법 (Windows 예 — `<port>` 는 빈 포트, `<out>` 은 아무 폴더)

```
# 1) 개발 서버(앱 저장소는 읽기만 — 감싸개는 hyper-design 쪽, 캐시는 OS 임시 폴더). cwd = 앱 폴더, 또는 HD_APP_DIR=<앱 폴더>
cd C:/Code/dictionary/ui_host/popup
node node_modules/vite/bin/vite.js --mode twin --config $SK/features/app/dayfine.vite.mjs --host 127.0.0.1 --port <port> --strictPort
#    (= npx vite --mode twin --config $SK/features/app/dayfine.vite.mjs --port <port>)
# 2) out 폴더 + 빌드
python3 $SK/features/app/app_out.py C:/Code/dictionary/ui_host/popup <out> --dev-url http://127.0.0.1:<port> --build
# 3) 프로젝트로(그대로 — hd 는 고치지 않음)
python3 $SK/features/hd/hd.py save --out <out> --name dayfine
python3 $SK/features/hd/hd.py open dayfine
```
다시 열 때: `<out>/app.json` 의 `dev_cmd` 를 `ui_dir` 에서 다시 띄우고(같은 포트) `hd open dayfine`. 포트가 바뀌면 2) 를 새 `--dev-url` 로 다시.

## 규칙

- 감싸개 `dayfine.vite.mjs`: 앱의 `vite.config.js` 를 그대로 읽고 플러그인 `hd-stage`(개발 서버에서만, `apply:'serve'`) 하나를 더한다. 앱의 평소 dev·build 는 이 파일을 거치지 않는다. 앱 저장소에 파일을 만들지 않는다(`cacheDir` = OS 임시 폴더)
  - `GET /hd-stage/<화면>.html` — `<화면>` = `<무대 id>` 또는 `<무대 id>--<설정 탭>`. 무대 하나를 붙인다: `src/twin/stages.js` 의 `STAGES[id].component` + `stageProps(id)`, 설정 스토어는 twin 페이지처럼 `usage-tab` 스냅샷(`applyConfigSnapshot`), 탭은 `window.__dictSettingsTab`. `/hd-stage.html?id=&tab=` 도 같은 페이지. 캔버스가 다시 실을 때 붙이는 `?v=` 는 버린다. 모르는 무대 = 페이지에 `[hd]` 한 줄 + console.error, 이름이 틀리면 400
  - 카드 주소를 **경로** 모양으로 둔 까닭: 캔버스(`idOf(file)`)와 `palette.js`(`screenId()`)가 화면 id 를 경로 마지막 조각에서 읽는다 — `?id=` 모양이면 모든 카드가 `hd-stage` 가 된다
  - 그 페이지에만 `foundation/palette.js` 를 `/@hd/palette.js` 로(늘 지금 파일), `window.__hdSrc = {root: 저장소 뿌리, base: 저장소 안 앱 폴더}`. 무대 페이지의 상대 경로(`fonts/…`)는 앱 `public/` 에서 준다(twin 모드는 `publicDir` 이 꺼져 있음, 밖으로 나가는 경로는 거절)
- out 만들기 `app_out.py`(I/O) + `app_stages.py`(Model, 순수): 무대 목록은 `src/twin/registry.js` 를 **글로 읽는다**(node 에 묻지 않음 — 리터럴 배열·객체라 충분, unit 이 하위 프로세스 없이 돈다). 카드 = 무대마다 하나(제목 = 컴포넌트 이름, 설명 = `TWIN_LABELS`, 정책 줄 = 소스·픽스처 경로, 줄 = 그룹 `분자`·`유기체`) + 설정 탭마다 하나(`settings-window--<탭>`, `SettingsApp.svelte` 의 `const tabs`). `app.json` = `{kind:'app', repo, ui_dir, dev_cmd, dev_url, stages}` · `surface.json`(카드 520×640, 크게 보기 960×720 — 이미 있으면 그대로)
- `build_canvas.py`: 화면 `file` 이 `http(s)://127.0.0.1|localhost[:포트]/…` 이면 카드가 그 주소를 그대로 싣는다(파일 읽기·링크 미리 뽑기 없음, `is_dev_url`). 다른 값은 예전 규칙 그대로
- 소스 위치(`palette.js`): 고른 요소나 가장 가까운 조상의 `__svelte_meta.loc` → `hd-picked`·`hd-hit`·`hd-dbl` 답과 `hd-located` 항목에 `src:{file, line, column}`(저장소 기준 경로 — `__hdSrc.root` 아래 절대 경로면 잘라 내고, 상대면 `base/` 를 붙임, 저장소 밖 절대 경로는 그대로) · `comp:[안쪽 컴포넌트부터 ≤8]`. 메타가 없으면 두 칸 모두 없다(정적 화면 그대로)
- 진입 모듈이 깨져도 빈 페이지가 아니다(#280): 감싸개의 `ENTRY` 는 앱 모듈을 하나씩 동적으로 읽는다(`ENTRY_DEPS`). 못 읽거나(없음·던짐) 쓰는 이름을 내보내지 않으면 무대 뿌리에 `[hd] <모듈>: <메시지>` 한 줄 + 부모 창에 `hd-here {screen, error:"<모듈>: <메시지>"}`. 모르는 무대·mount 실패도 같은 길(`무대 <id>: …`). 카드가 그 한 줄을 화면 밑 `.cerr` 로 보인다(카드마다 같은 글은 한 번 — `contract/busy.md`)
- 앱 카드 "AI 수정 중" 칩 걷기(#272): 앱 카드는 `file` 이 주소라 mtime 이 없다. 감싸개가 HMR 뒤(`vite:afterUpdate`) `hd-here {screen, hmr:true}` 를 보내고, `view-busy` 가 그 카드 iframe 의 `hd-here`(HMR · 덮개 뒤 다시 실림 — 이 판에서 그 카드의 첫 로드는 빼고, `error` 알림도 빼고)로 `HD.busy.shouldLift` 를 본다(`contract/busy.md`). × 는 그대로 손으로 걷기. HMR 알림은 페이지 안 어느 모듈이 바뀌어도 온다(무대 페이지는 `stages.js` 가 모든 무대 컴포넌트를 읽어 사실상 앱 전체) — 다른 무대를 고쳐도 걷힐 수 있다
- origin: 캔버스(도우미·file://)와 카드(`127.0.0.1:<vite>`)는 다른 origin — postMessage 는 `'*'` 로 보내고 `e.source` 로 거르므로 그대로 된다. HMR 웹소켓은 카드 페이지 자기 origin(개발 서버)에 붙는다(`[vite] connected.` — 테스트가 본다)

## 아직 (다른 곳의 일)

- 의존(앱 비공개 모듈 — 앱 쪽에서 이름·내보내기가 바뀌면 카드가 `[hd] <모듈>: …` 한 줄을 보인다): `/src/styles/theme.css` · `/src/twin/stages.js`(`STAGES`·`STAGE_FIXTURES`·`stageProps`) · `/src/settings/store.js`(`applyConfigSnapshot`) · 설정 탭 건넴 `window.__dictSettingsTab` · CSS 변수 `--popup-bg`·`--popup-text`·`--popup-font-size`. 목록 원본 = `dayfine.vite.mjs` 의 `ENTRY_DEPS`(unit 테스트가 이 줄과 맞춰 본다)
- 무대: 지금 10개. Welcome · Tutorial 틀 · History · Popup 은 dictionary 세션이 twin 무대로 더할 때까지 카드가 없다(더하면 `app_out.py` 를 다시 돌리면 된다)
- `__svelte_meta` 는 Svelte 비공개 API(5.56.0 에서 확인) — 바뀌면 `src` 가 빠질 뿐 고르기는 그대로. 글 마디는 부모 요소의 줄만 준다
- 카드 ≠ 진짜 창(pywebview 브리지 없음, 드래그·닫기 무반응) — 눈 확인은 앱의 규칙(R-UI6)대로

## 고치면 돌릴 것

| 고친 곳 | 돌릴 것 |
|---|---|
| `features/app/*` | `pytest $SK/features/app/tests -m unit`(약 3초 — 가짜 앱 나무로 `ENTRY` 실패 길 포함) · 커밋 전 `pytest $SK/features/app/tests`(slow: vite + Playwright 약 35초, 앱·node_modules 가 없으면 건너뜀) |
| `foundation/palette.js` 의 `src` | 위 + `-m "unit or links or modal or tools or notes"`(캔버스) |
| `build_canvas.py` 의 `is_dev_url` | 위 unit + `-m "unit or flow or links"`(캔버스) |
