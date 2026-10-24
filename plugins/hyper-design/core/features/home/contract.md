# home — 계약 (허브 · 프로젝트 API · 썸네일 · 바로 가기)

```
python $SK/features/hd/hd.py home [--no-browser] [--port N]      # 허브(127.0.0.1:12270 · env HD_HUB_PORT, 막혔으면 빈 포트) — 떠 있으면 그 주소를 브라우저로
python $SK/features/hd/hd.py home --shortcut [--desktop DIR]     # 바탕 화면 'Hyper Design.lnk' → pythonw "<hd.py>" home
```
설계: `tasks/42-home/DESIGN.md`(조각 1·2·7·8 · 데이터 · API). 화면(`home.html`·`home.css`·`home-model.js`·`home.js`)은 task 43 몫 — 허브는 그 파일을 낼 뿐.

## 상태 (주인 하나씩)
- `<HD_HOME>/projects.json` — 주인 `hd_client`. 항목에 선택 칸 `title`(1–80자 한 줄) · `starred`(bool) · `trashed`(iso | 없음). 옛 파일 그대로 읽힘, 틀린 새 칸은 그 칸만 버림(`hd_projects.parse`)
- `<HD_HOME>/tabs.json` = `{version:1, tabs:[name]}` — 주인 `home_client`. 읽을 때 모르는·휴지통·겹친 이름은 버림. 깨지면 `[hd]` 한 줄 + 빈 탭. 열기·새로 만들기는 끝에 더하고, 휴지통에 넣으면 뺀다
- `<HD_HOME>/home.json` = `{url, pid, port, token}` — 주인 허브(`home_server.serve`). 재사용 규칙은 `.hd-helper.json` 과 같은 `hd_model.start_verdict`(살아 있는 pid + `GET /api/tabs` 가 답함 → 재사용 · 아니면 덮어씀). 정상 종료(Ctrl+C · SIGTERM · SIGBREAK) 때 지움
- `<HD_HOME>/thumbs/<name>.png` — 주인 `thumb.Thumbs`(일꾼 스레드 하나). 프로필 `<HD_HOME>/thumbs/.profile`
- `<HD_HOME>/projects/<name>/out/` — 새 프로젝트(빈 `screens.json` `{title, groups:[], screens:[]}`) · `<HD_HOME>/hd.ico` · `<HD_HOME>/home.log`(떼어 띄운 허브 출력)

## API — 허브와 캔버스 도우미가 같은 `home_api.route`(같은 JSON)
`X-HD-Token` + Host 검사(허브 `/`·정적 파일·`/thumb/*` 만 토큰 없음). 오류 = `{error: 한국어 한 줄}` + 4xx/5xx, 예상 못 한 실패도 500 한 줄 + 로그 추적(숨기지 않음).
- `GET /api/projects` → `[{name, title, out, state, url, pid, created, last_opened, starred, trashed, thumb}]` — title = 항목 title → screens.json title → name · thumb = `http://127.0.0.1:<허브포트>/thumb/<name>.png?t=<mtime>` | null(그림 없음 · 허브 기록 없음). 허브는 이때 낡은 썸네일을 뒤에서 예약
- `POST /api/open {name, agent?}` → `{name, out, url, pid, agent, reused}` · 모르는 것 404 · 띄우기 실패 500
- `POST /api/new {title?}` → `{name, title, url}` — 빈 제목 = '새 프로젝트 N'(안 쓰인 가장 작은 N) · 이름 = 제목 slug(목록·폴더와 겹치면 -2…) · 틀린 제목 400 · 만들었지만 못 띄움 500
- `POST /api/project {name, title?, starred?, trashed?: bool}` → `{row}` · 모르는 이름 404 · 틀린 값·바꿀 칸 없음 400
- `POST /api/forget {name}` → `{ok}` — 휴지통에 든 것만(아니면 409), 링크만(파일 그대로)
- `POST /api/reveal {name}` → `{ok}` — 탐색기로 out 폴더 · 폴더 없음 404
- `POST /api/pick-folder`(허브만) → `{name}` | `{cancel:true}` | 400 `{error}`(캔버스 아님 — 그 폴더나 그 아래 `out/` 에 index.html · .hd-canvas.json · screens.json 이 없음). 휴지통에 있던 것이면 꺼냄
- `GET /api/tabs` · `PUT /api/tabs {tabs}` → `{tabs}` · 글 목록이 아니면 400
- `GET /api/home`(도우미만) → `{url}` — 허브가 답하지 않으면 `hd.py home --no-browser` 를 떼어 띄우고 10초까지 기다림, 실패 500
- 허브 주소 = `http://127.0.0.1:<port>/?hd=<token>` · 페이지 `<head>` 에 `window.__hdHub=true; window.__hdToken="…"`

## 썸네일
헤드리스 Edge(없으면 Chrome) `--headless=new --screenshot --window-size=1260,780 --virtual-time-budget=6000 --hide-scrollbars` 로 `<out>/index.html`(file://). 낡음 = 그림 없음 또는 max(`.hd-canvas.json`, `index.html` mtime) 보다 오래됨(`home_model.thumb_stale`), 없어진 out·index.html 없음은 건너뜀. 한 번에 하나, 같은 이름은 한 번만 줄 섬, 요청을 막지 않음. 실패는 `[hd]` 한 줄(다음 예약 때 다시). 브라우저 없음 = 그림 없음(한 번 알림). 한 장 약 20초.

## 바로 가기
`<Desktop>/Hyper Design.lnk`(Desktop = `[Environment]::GetFolderPath('Desktop')`) → `pythonw.exe`(sys.executable 옆, 없으면 python.exe) `"<hd.py>" home`, 작업 폴더 HD_HOME, 아이콘 `<HD_HOME>/hd.ico`(256px PNG 를 담은 ICO, 캔버스 "hd" 배지 모양 — 표준 라이브러리로 그림). 아이콘을 못 만들면 `[hd]` 한 줄 + 아이콘 없이. .lnk 는 PowerShell `WScript.Shell`.

## 구조 (층)
- Model `home_model.py` — 순수: 구역·검색·상대 시각·탭 정리·새 이름/제목·빈 매니페스트·썸네일 낡음/주소/이름 검사(순수성 검사 `tests/test_home_model.py`). 항목 규칙은 `hd/hd_projects.py`(`update` · `forget_trashed` · `title_error` · `rows`)
- Client `home_client.py` — I/O: tabs.json · home.json · 허브 띄우기/기다리기 · 새 프로젝트 폴더 · 폴더 등록 · 탐색기 · 폴더 고르기(PowerShell FolderBrowserDialog). projects.json 은 `hd_client`(`update_project` · `forget_trashed` · `manifest_title`)
- Client `thumb.py`(브라우저 찾기·찍기·`Thumbs` 일꾼) · `shortcut.py`(아이콘·.lnk)
- Controller `home_api.py` — 라우트 하나(`route` → (code, 답) | None). 허브·도우미가 부르기만 한다
- Server `home_server.py` — 허브 HTTP(페이지·정적·썸네일·API) · `serve`(기록·재사용·신호). CLI 는 `hd.py home`

조각 보고:
- `home_model` · 구역·검색·시각·탭·새 이름·썸네일 규칙 · 상태 없음 · 줄 객체·iso·이름 목록 · `section` `search` `rel_time` `tabs_parse` `tabs_set` `tabs_add` `tabs_drop` `tabs_doc` `default_title` `new_name` `empty_manifest` `thumb_stale` `thumb_url` `thumb_name`
- `home_client` · tabs.json · home.json 주인 · HD_HOME · `load_tabs` `save_tabs` `change_tabs` `known_names` `read_hub` `write_hub` `clear_hub` `live_hub` `hub_port` `spawn_hub` `ensure_hub` `create_project` `canvas_folder` `register_folder` `reveal` `pick_folder`
- `home_api` · 라우트 · 상태 없음 · Ctx(hub, agent, port, after_rows, picker) · `route` `open_post` `new_post` `project_post` `forget_post` `reveal_post` `pick_post` `tabs_put` `home_get` `with_thumb`
- `home_server` · 허브 HTTP · 서버 하나(토큰·Thumbs) · `make_hub` `serve` `bind`
- `thumb` · 썸네일 줄·일꾼 · 줄(이름 집합) · `find_browser` `render` `stale` `Thumbs`
- `shortcut` · .lnk · 아이콘 · 없음 · `desktop` `pythonw` `badge_png` `ico_bytes` `make_icon` `write_shortcut` `read_shortcut`
- `canvas/helper.py` 추가분 · `/api/projects`·`/api/open`·새 라우트를 `home_api.route` 로(`srv.home_ctx`), `PUT /api/tabs`. `open_post` 는 `home_api.open_post` 를 부르기만

## 테스트
`python -m pytest plugins/hyper-design/core/features/home/tests -k "not page"` — `test_home_model.py`(규칙·순수성) · `test_home_api.py`(이 프로세스 안 허브, 가짜 그리기·고르기·탐색기·띄우기) · `test_home_hub.py`(자식 프로세스: hd home 기록·재사용·정상 종료 · 도우미 새 라우트·/api/home 이 허브를 띄움 · 진짜 빈 캔버스 새로 만들기 · 임시 바탕 화면 바로 가기). 실제 바탕 화면·12270·12279·실제 HD_HOME 은 건드리지 않는다. 고치면 hd 테스트와 canvas `-m "unit or helper"` 도.
