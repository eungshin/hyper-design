# 블록 편집 — 요소 막대 (blocks, task 49a · 49b)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/blocks.js` | Model | 요소 막대 규칙 — 단추 차례·켜짐(`bar`)·앱 카드 판정(`isApp`, `build_canvas.DEV_URL` 과 같은 규칙)·단축키(`keyAct`)·앱 카드 요청 글(`askText`)·막대 자리(`place`)·상위 고르기(`parentPick`)·속성 허용 목록(`ATTRS`·`attrOk`·`attrFields`)·부품 요청 글(`partAsk`). 상태 없음 |
| `modules/view-blocks.js` | View | `#elbar`·`#elpop`(속성 칸·부품 목록) 과 그 CSS. 상태 = 지금 고른 요소 하나 `{screen, h, app, where, anchor(), frame(), view?(), avoid?()}` + 따라갈 요소 하나(쓴 뒤 15초, 저장하지 않음). `HD.feature('blocks', {needs: ['$','toast','esc','api','cardEl']})` → `{show, hide(where?), place, sel, onAct(fn), onPick(fn), wrote(res, list)}` — 편집은 셸이 `onAct` 로 준 `blockAct` 하나로만 나가고, 상위·따라가기로 새로 고른 요소는 `onPick` 으로 셸이 그린다 |
| `specimen_parts.py` | Model(Python) | 부품 견본(`components.html`·`specimens.html` 의 `section.spec[data-key]`) → 화면에 넣을 뼈대(`sections`·`skeleton`·`parts`·`markup`). 파일·네트워크 없음 — 읽기는 `helper.py` 가(`parts_of`·`apply_edits`) |
| 셸 `blockAct`·`modalSel`·`elemMemo`·`pickElAt`·`appCard`·`setMode` | — | 요소 막대·요소 메뉴의 동작을 이미 있는 편집 길(`editScreenText`·`removeElement`·`addEdits`·`showPop`)로 잇기만 한다 — 그 길이 모두 셸 것이라 모듈로 빼면 셸 함수를 ctx 로 다 넘겨야 해서. `modalSel` = 크게 보기 고른 요소의 sel(셸 `mbox`·`mscale`·`mframe` 을 읽는다) |

## 규칙

- 막대 = `[상위][글자][속성][지우기][복제][↑][↓] | [바꾸기][아래에 넣기] | [메모]` — `[속성]` 은 고칠 속성이 있는 요소(img·a·input·textarea)에서만. 고르는 길: 판 — 고른 카드를 이동(V)으로 한 번 더 누르기 · 트리거(L)로 요소 누르기 · 크게 보기 — 이동(V) 도구로 요소 누르기
- 켜짐: 상위 = `h.up !== false`(감싼 요소가 body·html 이 아님) · 글자 = `h.textOk !== false` · 지우기·복제·↑·↓·바꾸기·아래에 넣기 = 화면 뿌리 아님 · ↑ = 앞 형제 있음 · ↓ = 뒤 형제 있음(형제 = script·style·template·link·meta 빼고 — `helper.py SIB_SKIP` = `palette.js SIB_SKIP`) · 속성·메모 = 늘. 꺼진 단추를 누르면 까닭 토스트
- 앱 카드(화면 `file` = 개발 서버 주소, 또는 고른 요소에 `src`): 파일을 바꾸는 단추는 모두 "AI에게 요청" — 메모 창에 요청 글을 채워 열고, 메모 대상에 `src` 가 남아 요청문에 `소스:` 줄. 파일·DOM 을 직접 고치지 않는다. `[상위]`·`[메모]` 는 그대로(고르기·메모라서)
- 단축키(막대가 떠 있을 때, 입력 칸 밖): `[`(자판 자리 `BracketLeft` — 한글 자판도) 상위 · Alt+↑/↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete 지우기. Esc 는 풀기·창 닫기라 쓰지 않고, Ctrl+Shift+[ 는 프로젝트 탭
- 읽기만인 탭(`<html data-hd-tab="reader">`)은 막대 단추를 흐리게, 누르면 알리기만(상위는 고르기라 됨)
- 막대 자리(`place`): 요소 위(왼쪽 맞춤, 보이는 칸 오른쪽을 넘으면 오른쪽 맞춤) → 자리가 없거나 비킬 것과 겹치면 아래 → 오른쪽 옆 → 왼쪽 옆. 고른 요소 위에는 놓지 않는다(요소가 보이는 칸을 다 덮을 때만 겹침 `over`). 보이는 칸 = 크게 보기는 덮개 `#modal`(도크·위쪽 줄 위가 아님), 판은 판 칸. 비킬 것 = 크게 보기는 창 제목 막대(닫기), 판은 카드 선택 막대. 판 이동·확대(`placeSelbar`)마다 다시 놓는다. 크게 보기 안 스크롤 = 막대 걷기
- 상위 고르기: 화면에 `hd-up` → 조상 hit 들(가까운 것부터 8개) → `parentPick` = 상자가 다른 첫 조상(같은 상자 = 감싸기만 한 요소는 건너뜀). 그 요소도 막대의 모든 편집(지우기·복제·옮기기·바꾸기)을 그대로 받는다 — 섹션 통째로
- 바로 쓰기: 글자·지우기·복제·옮기기·속성·넣기·바꾸기는 `edits.instantOf` — 도우미가 있으면 누르는 즉시 파일에(되돌리기 = `/api/restore` 되살리기), 없으면 반영 대기(미리보기: 복제 = 점선 복사본, 옮기기 = 자리 바꿈, 속성 = 잠시 바꿈 — 넣기·바꾸기는 미리보기 없음)
- 쓴 뒤 따라가기(49b): 도우미 `/api/apply` 답 `paths = {편집 id: 그 요소의 새 경로}`(그 화면에 요소 편집 하나일 때 — 옮긴 것·넣은/바꾼 부품·같은 요소) → `view-sync` `ctx.wrote` → 막대가 기억 → 다시 실린 틀(`?v=<stamp>`)의 `hd-here` 에 `hd-find` → `hd-found` 로 다시 고른다(판·크게 보기 모두, 48a 교체 틀). Alt+↑ 를 이어 눌러도 다시 고를 필요가 없다
- 속성 칸(49b): 허용 목록 = img `src`·`alt` · a `href` · input·textarea `placeholder` — 세 곳 같은 목록(`helper.py ATTR_OK` · `palette.js ATTR_OK` · `blocks.js ATTRS`). `on*`·`style` 은 절대 · `href`·`src` 의 `javascript:`·`vbscript:`·`data:`(그림 `src` 의 `data:image/` 만 허용) 거절 · 줄바꿈·2000자 넘음 거절. 바뀐 속성마다 편집 하나(`edit:'attr'`, `op` = 이름, `value` = 값), 한 번에 쓰고 되돌리기 한 번
- 부품 바꾸기·넣기(49b): `[바꾸기]`·`[아래에 넣기]` → 이 프로젝트의 Components(`GET /api/parts` = `out/components.html` 의 견본 목록 `{key, title, ok}`) 고르기. `ok` = 뼈대를 뽑을 수 있음 → 편집 `insert`(바로 아래, 앞 공백 그대로)·`replace`(그 자리) `value` = key. 뼈대는 **도우미가 key 로 뽑는다**(캔버스가 보낸 마크업은 쓰지 않음): 견본의 첫 칸 첫 무대의 첫 요소, 글은 모두 중립 글 `텍스트`, `id`·`for`·`value`·`title` 등은 빼고 `placeholder`=`입력`·`alt`=''·`aria-label`=`설명` — 견본 보기 글은 화면에 들어가지 않는다. 뼈대를 못 뽑음(`on*`·script 등)·도우미 없음·앱 카드 = AI 요청 메모 `이 자리에 <부품> 넣기 — 데이터는 화면에 맞게`(`partAsk`)
- 도우미 `duplicate`: 요소 원문 `[시작, 닫는 태그 끝)` 바로 뒤에 요소 앞 공백 + 복사본(복사본과 그 자손의 `id`·`data-region` 은 뺌). `move` op `up|down`: 앞·뒤 형제와 원문 조각을 맞바꾸고 사이 글·공백은 제자리, 맨 위·맨 아래·화면 뿌리·닫는 태그 없음은 거절. `insert`·`replace`: 화면 뿌리·닫는 태그 없음·빈 부품 거절. 경로는 정확히 하나에 맞을 때만(task 41 그대로). 옮긴 뒤 메모 핀은 quote 로 다시 찾는다(`hd-locate`). 모두 거절되면 쓰지도 다시 빌드하지도 않는다
- 크게 보기 도구: 손(눌러 보기) · 이동(요소 고르기 → 막대) · 주석(메모) · 글자(누른 글자 고치기). 나머지는 판에서만. 오른쪽 클릭 = 판과 같은 요소 메뉴(도착을 판에서 고르는 잇기·도착 바꾸기, 막대에만 있는 상위·속성·부품은 뺌)
- 화면 메시지(palette.js, 기존 것은 그대로): `hd-hit` 계열 답에 `prev`·`next`·`root`·`up`·`tag`·`attrs`(허용 목록의 지금 값) · `hd-pick {on, mode:'text'|'select'}` → 누르면 `hd-dbl` · `hd-sel` · `hd-edit` 이 켜진 화면의 오른쪽 클릭 → `hd-ctx {…hd-hit 칸, x, y}` · 고르는 중 스크롤 → `hd-scroll` · `hd-up {path, tag}` → `hd-upchain {tag, path, chain}` · `hd-find {path, tag}` → 다 실린 뒤 `hd-found {tag, …hd-hit 칸}`(없으면 path null) · `hd-pending` 항목 `{path, dup:true}` · `{path, move}` · `{path, attr, value}`

## 아직

- 끌어서 순서 바꾸기(49b 범위 밖)
- 부품 뼈대 = 견본의 '기본' 모습 하나만(변형 고르기 없음) · 넣은 부품의 글·데이터는 사람이 고치거나 AI 에게
- 판 카드가 아직 안 실린(보이지 않는) 상태에서 쓰면 따라가기는 15초 뒤 걷힌다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/blocks.js` · `view-blocks.js` · `specimen_parts.py`(+ `tests/test_canvas_unit_blocks.py` · `test_canvas_unit_blocks_b.py` · 브라우저 `test_canvas_blocks.py` · `test_canvas_blocks_b.py`) · `helper.py` duplicate·move·attr·insert·replace·`/api/parts` | `unit or tools or modal or helper` |
