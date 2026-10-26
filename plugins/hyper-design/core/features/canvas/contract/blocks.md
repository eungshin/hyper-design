# 블록 편집 — 요소 막대 (blocks, task 49a · 49b)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/blocks.js` | Model | 요소 막대 규칙 — 막대 아이콘(`icons`)·요소 메뉴 묶음과 단축키 힌트(`menu`·`keyOf`, R17)·단추 차례·켜짐(`bar`)·앱 카드 판정(`isApp`, `build_canvas.DEV_URL` 과 같은 규칙)·단축키(`keyAct`)·앱 카드 요청 글(`askText`)·막대 너비(`barLimit`·`fit`)·상위 고르기(`parentPick`)·속성 허용 목록(`ATTRS`·`attrOk`·`attrFields`)·부품 요청 글(`partAsk`). 상태 없음 |
| `modules/bar-place.js` | Model | 막대 자리(51-7a) — `HD.barPlace.place({anchor, label, size, view, bars, content})` → `{x, y}`. 위 먼저 → 아래 → 옆; 고른 요소·이름표는 덮지 않고, 붙은 둘레 글은 막대 높이 + 12px 까지 비켜 가고, 다 덮으면 가장 적게 덮는 자리. 상태 없음 |
| `modules/view-blocks.js` | View | `#elbar`·`#elpop`(속성 칸·부품 목록·⋯ 목록) 과 그 CSS · 둘레 글 상자 읽기(같은 출처 화면만, 1초 기억). 상태 = 지금 고른 요소 하나 `{screen, h, app, where, anchor(), frame(), view?(), avoid?()}` + 따라갈 요소 하나(쓴 뒤 15초, 저장하지 않음). `HD.feature('blocks', {needs: ['$','toast','esc','api','cardEl']})` → `{show, hide(where?), place, sel, fire(act), onAct(fn), onPick(fn), onMenu(fn), wrote(res, list)}` — `[⋯]` 는 `onMenu` 로 받은 fn(sel, {x, y}) 로 셸의 요소 메뉴를 막대 아래에 연다 — 편집은 셸이 `onAct` 로 준 `blockAct` 하나로만 나가고, 상위·따라가기로 새로 고른 요소는 `onPick` 으로 셸이 그린다 |
| `specimen_parts.py` | Model(Python) | 부품 견본(`components.html`·`specimens.html` 의 `section.spec[data-key]`) → 화면에 넣을 뼈대(`sections`·`skeleton`·`parts`·`markup`). 파일·네트워크 없음 — 읽기는 `helper.py` 가(`parts_of`·`apply_edits`) |
| 셸 `blockAct`·`modalSel`·`appCard`·`setMode` · `pickList` · 고르기 안내(51-3)는 `view-elbox`(`hoverMode`·부모 점선·`pickAt`) · 묻기 `view-frame-ask`(`elbox.md`) | — | 요소 막대·요소 메뉴의 동작을 이미 있는 편집 길(`editScreenText`·`removeElement` · 메모 창 `MP.elem` = `view-memo-pop` · 편집 쌓기 `ED.add` = `view-edit-path`)로 잇기만 한다 — 그 길이 모두 셸 것이라 모듈로 빼면 셸 함수를 ctx 로 다 넘겨야 해서. `modalSel` = 크게 보기 고른 요소의 sel(셸 `mbox`·`mscale`·`mframe` 을 읽는다). 51-3 은 hover 묻기·고른 요소(`EB.selected`·`EB.select` — view-elbox)·묻기(`FA.hit`·`FA.chain` — view-frame-ask)·우클릭 메뉴(`#cmenu`)를 그대로 쓴다(두 번째 hit-test 없음) |

## 규칙

- 막대(R17 시안 A) = 흰 아이콘 줄 `[⠿] [메모 달기][글자 고치기][AI에게 바꿔 달라기] | [⋯]`(`blocks.icons`) — `[⠿]` = 끌어서 순서 바꾸기 손잡이(49c, `grip` — 규칙은 `instant.md`, 판에서 요소를 끄는 유일한 길이라 남김) · `[글자]` 는 글을 바꿀 수 있을 때만(`h.textOk !== false` — 예전 켜짐과 같은 규칙) · `[⋯]` = 오른쪽 클릭과 같은 요소 메뉴(아래). 단추마다 `data-act`(grip·memo·text·ai·more) 와 꼬리말 `#eltip`(이름 + 단축키 — 도구 막대 꼬리말과 같은 모양, 올리거나 초점). 상위·속성·지우기·복제·바꾸기·아래에 넣기·↑·↓ 는 메뉴와 단축키로. 고르는 길: 판 — 고른 카드를 선택(V)으로 한 번 더 누르기 · 트리거(L)로 요소 누르기 · 크게 보기 — 선택(V) 도구로 요소 누르기
- 요소 메뉴(R17, `blocks.menu` — 오른쪽 클릭·`[⋯]` 같은 것): 묶음 **고르기**(상위 고르기 · 안쪽 고르기 · 레이어 고르기 ▸) · **고치기**(글자 고치기 · 속성 고치기…(속성이 있을 때) · 복제 · 지우기 · 위로·아래로 옮기기 · 아래에 넣기… · 다른 부품으로 바꾸기…) · **연결**(셸 — 트리거 지정/해제·잇기·도착 바꾸기) · **요청**(메모 달기 · AI에게 바꿔 달라기) · 판은 뒤에 **카드** 항목. 꺼진 항목은 빼되 글자 고치기는 남김(누르면 까닭). 오른쪽 맞춤 힌트는 실제로 듣는 키만(`keyOf`): Shift+Enter 상위 · Enter = 글자면 글자 고치기, 아니면 안쪽 고르기 · 크게 보기 글자 = 더블클릭 · Ctrl+D · Del · Alt+↑/↓ — 메모 C 는 선 자르기 도구(C)와 겹쳐 두지 않음. 앱 카드 = 고치기는 ' — AI에게 요청'(힌트 없음). 상위·안쪽·속성·부품은 셸 `elemFire` 가 그 요소를 고른 뒤 막대의 같은 길(`BK.fire`) — 나머지는 예전처럼 `blockAct`
- AI에게 바꿔 달라기(R17) = 메모 창(`MP.elem`, 의도 기본 = 바꾸기)에 `askText('ai')` = `바꿔 주세요: ` 를 채워 연다 — 요소에 AI 요청을 거는 기존 길(앱 카드 요청과 같은 창)
- 켜짐: 상위 = `h.up !== false`(감싼 요소가 body·html 이 아님) · 글자 = `h.textOk !== false` · 지우기·복제·↑·↓·바꾸기·아래에 넣기 = 화면 뿌리 아님 · ↑ = 앞 형제 있음 · ↓ = 뒤 형제 있음(형제 = script·style·template·link·meta 빼고 — `helper.py SIB_SKIP` = `palette.js SIB_SKIP`) · 속성·메모 = 늘. 꺼진 단추를 누르면 까닭 토스트
- 앱 카드(화면 `file` = 개발 서버 주소, 또는 고른 요소에 `src`): 파일을 바꾸는 단추는 모두 "AI에게 요청" — 메모 창에 요청 글을 채워 열고, 메모 대상에 `src` 가 남아 요청문에 `소스:` 줄. 파일·DOM 을 직접 고치지 않는다. `[상위]`·`[메모]` 는 그대로(고르기·메모라서)
- 단축키(막대가 떠 있을 때, 입력 칸 밖): `[`(자판 자리 `BracketLeft` — 한글 자판도) 상위 · Alt+↑/↓ 옮기기 · Ctrl/Cmd+D 복제 · Delete·Backspace 지우기. Esc 는 풀기·창 닫기라 쓰지 않고, Ctrl+Shift+[ 는 프로젝트 탭
- Figma 고르기 키(51-2, 같은 조건 + 메뉴·창(`role=menu|dialog`·`#cmenu`·`#elpop`) 안 Enter/Tab 은 그 메뉴 것): Enter = `enterOf(h)` — 글을 바꿀 수 있고(`textOk`) 글이 있으면 `[글자]`(그 자리 고치기, 앱 카드는 AI 요청), 아니면 첫 자식 요소(`hd-down`) · Shift+Enter = `[상위]`(`[` 와 같음) · Tab/Shift+Tab = 다음·앞 형제(`hd-sib`). 형제·자식 = 옮기기와 같은 빼기(`SIB_SKIP`·`data-hd-dup`·`data-hd-pick`·`data-hd-links`). **끝에서 돈다**(맨 뒤에서 Tab = 맨 앞 — Figma 처럼, 멈추면 Tab 이 아무 일도 안 하는 것처럼 보여서). 형제가 없거나 자식이 없으면 까닭 토스트. 판 위에서 요소를 고른 동안 Tab 은 패널 숨기기(view-menu) 대신 형제 고르기, 입력 칸(대화창 포함)의 Tab 은 건드리지 않는다. 답을 기다리는 중 더 누른 키는 차례로(빠르게 Tab 여러 번)
- 그 자리 글자 고치기를 저장·취소한 뒤 그 요소가 골라진 채 막대가 남는다(Figma F14, 판·크게 보기 — `view-optimistic` 이 그 틀에 `hd-find` → `hd-found` 의 지금 상자로 `ctx.picked`, 셸이 판은 `EB.select`). 쓴 뒤 카드가 다시 실려도 따라가기(49b)로 그대로
- Alt+클릭(51-2, 사용자 결정 ③) = 그 자리 가장 안쪽 요소를 바로 고르기 — 판은 카드를 안 골랐어도(그 카드를 고르고 `hd-hit-at deep:true`), 크게 보기는 선택(V) 도구에서. Ctrl/Cmd+클릭은 지금 뜻(어디로 가나) 그대로
- 읽기만인 탭(`<html data-hd-tab="reader">`)은 막대 단추를 흐리게, 누르면 알리기만(상위는 고르기라 됨)
- 막대 자리(`HD.barPlace.place`, polish-1 → 51-7a 이사): 후보 = 위(왼쪽 맞춤 → 오른쪽 맞춤) → 아래(같은 차례) → 오른쪽 옆 → 왼쪽 옆. 단단한 규칙: 고른 요소 위에는 놓지 않는다(요소가 보이는 칸을 다 덮을 때만 겹침 `over`) · 보이는 칸 안 · 비킬 것(목록)과 겹치지 않음. 무른 규칙: 둘레 글 상자(`others` — 글 마디·그림·입력 칸, 고른 요소 안 것은 빼고)를 덮지 않는 첫 후보, 모두 덮으면 덮는 넓이가 가장 작은 후보(같으면 차례). 둘레 글은 같은 출처 화면(도우미 http)에서만 읽는다 — `file://`·앱 카드는 못 읽어 예전 차례 그대로. 보이는 칸 = 크게 보기는 덮개 `#modal`(도크·위쪽 줄 위가 아님), 판은 판 칸. 비킬 것 = 크게 보기는 창 제목 막대(닫기), 판은 카드 선택 막대 + 왼쪽 도구 막대 `#tools`(둘 다). 판 이동·확대(`placeSelbar`)마다 다시 놓는다. 크게 보기 안 스크롤 = 막대 걷기
- 막대 모양(polish-1 → R17): 한 줄·낮게(약 24px, 22px 아이콘 단추), 흰 바탕 + `--ui-line` 테두리, 마우스가 없으면 반투명(0.9, 올리면 1). 아이콘 넷이라 늘 요소 칸(`barLimit` 최소 220) 안 — 예전 넘침 `⋯`(`fit`·`data-more`·`#elpop` 목록)은 없앴다(`fit`·`barLimit`·`shown` 은 Model 에 남음, 지금 View 는 안 씀)
- 상위 고르기: 화면에 `hd-up` → 조상 hit 들(가까운 것부터 8개) → `parentPick` = 상자가 다른 첫 조상(같은 상자 = 감싸기만 한 요소는 건너뜀). 그 요소도 막대의 모든 편집(지우기·복제·옮기기·바꾸기)을 그대로 받는다 — 섹션 통째로
- 바로 쓰기: 글자·지우기·복제·옮기기·속성·넣기·바꾸기는 `edits.instantOf` — 글자·복제·옮기기는 화면에 먼저 보이고 실패면 되돌림(49c `instant.md`) — 도우미가 있으면 누르는 즉시 파일에(되돌리기 = `/api/restore` 되살리기), 없으면 반영 대기(미리보기: 복제 = 점선 복사본, 옮기기 = 자리 바꿈, 속성 = 잠시 바꿈 — 넣기·바꾸기는 미리보기 없음)
- 쓴 뒤 따라가기(49b): 도우미 `/api/apply` 답 `paths = {편집 id: 그 요소의 새 경로}`(그 화면에 요소 편집 하나일 때 — 옮긴 것·넣은/바꾼 부품·같은 요소) → `view-sync` `ctx.wrote` → 막대가 기억 → 다시 실린 틀(`?v=<stamp>`)의 `hd-here` 에 `hd-find` → `hd-found` 로 다시 고른다(판·크게 보기 모두, 48a 교체 틀). Alt+↑ 를 이어 눌러도 다시 고를 필요가 없다
- 속성 칸(49b): 허용 목록 = img `src`·`alt` · a `href` · input·textarea `placeholder` — 세 곳 같은 목록(`helper.py ATTR_OK` · `palette.js ATTR_OK` · `blocks.js ATTRS`). `on*`·`style` 은 절대 · `href`·`src` 의 `javascript:`·`vbscript:`·`data:`(그림 `src` 의 `data:image/` 만 허용) 거절 · 줄바꿈·2000자 넘음 거절. 바뀐 속성마다 편집 하나(`edit:'attr'`, `op` = 이름, `value` = 값), 한 번에 쓰고 되돌리기 한 번
- 부품 바꾸기·넣기(49b): `[바꾸기]`·`[아래에 넣기]` → 이 프로젝트의 Components(`GET /api/parts` = `out/components.html` 의 견본 목록 `{key, title, ok}`) 고르기. `ok` = 뼈대를 뽑을 수 있음 → 편집 `insert`(바로 아래, 앞 공백 그대로)·`replace`(그 자리) `value` = key. 뼈대는 **도우미가 key 로 뽑는다**(캔버스가 보낸 마크업은 쓰지 않음): 견본의 첫 칸 첫 무대의 첫 요소, 글은 모두 중립 글 `텍스트`, `id`·`for`·`value`·`title` 등은 빼고 `placeholder`=`입력`·`alt`=''·`aria-label`=`설명` — 견본 보기 글은 화면에 들어가지 않는다. 뼈대를 못 뽑음(`on*`·script 등)·도우미 없음·앱 카드 = AI 요청 메모 `이 자리에 <부품> 넣기 — 데이터는 화면에 맞게`(`partAsk`)
- 도우미 `duplicate`: 요소 원문 `[시작, 닫는 태그 끝)` 바로 뒤에 요소 앞 공백 + 복사본(복사본과 그 자손의 `id`·`data-region` 은 뺌). `move` op `up|down`: 앞·뒤 형제와 원문 조각을 맞바꾸고 사이 글·공백은 제자리, 맨 위·맨 아래·화면 뿌리·닫는 태그 없음은 거절. `insert`·`replace`: 화면 뿌리·닫는 태그 없음·빈 부품 거절. 경로는 정확히 하나에 맞을 때만(task 41 그대로). 옮긴 뒤 메모 핀은 quote 로 다시 찾는다(`hd-locate`). 모두 거절되면 쓰지도 다시 빌드하지도 않는다
- 크게 보기 도구: 손(눌러 보기) · 이동(요소 고르기 → 막대) · 주석(메모) · 글자(누른 글자 고치기). 나머지는 판에서만. 오른쪽 클릭 = 판과 같은 요소 메뉴(도착을 판에서 고르는 잇기·도착 바꾸기, 막대에만 있는 상위·속성·부품은 뺌)
- 화면 메시지(palette.js, 기존 것은 그대로): `hd-hit` 계열 답에 `prev`·`next`·`root`·`up`·`tag`·`attrs`(허용 목록의 지금 값) · `hd-pick {on, mode:'text'|'select'}` → 누르면 `hd-dbl` · `hd-sel` · `hd-edit` 이 켜진 화면의 오른쪽 클릭 → `hd-ctx {…hd-hit 칸, x, y}` · 고르는 중 스크롤 → `hd-scroll` · `hd-up {path, tag}` → `hd-upchain {tag, path, chain}` · `hd-find {path, tag}` → 다 실린 뒤 `hd-found {tag, …hd-hit 칸}`(없으면 path null) · `hd-down {path, tag}`(첫 자식) · `hd-sib {path, dir:1|-1, tag}`(형제, 끝에서 돈다) → `hd-hop {tag, …hd-hit 칸}`(없으면 path null) · `hd-hit-at` 의 `deep:true` = 그 자리 요소 그대로(가장 안쪽) · `hd-pending` 항목 `{path, dup:true}` · `{path, move}` · `{path, attr, value}`

- 보이는 고르기 안내(51-3, Figma F6·F10·F11) — 규칙은 Model(`tools.hoverOf` · `blocks.chainOf`·`tone` · `layers.hoverIds`), 그리기는 셸:
  - 다음 클릭 미리 표시: 선택(V)으로 그 카드 하나만 고른 동안 그 카드 안에 올리면 다음 클릭이 고를 요소(누를 수 있는 요소 → 그 요소, Alt = 가장 안쪽)에 얇은 실선 `.elbox.hov`(이름표 없음) — 예전 hover 묻기(`hd-hit-at`) 그대로. 카드 밖·판 밖·글자를 고치는 카드(`.hd-typing`) = 없음, 고른 요소 위 = 없음. 요소 도구(L·P·T)는 예전 테두리 그대로
  - 부모 점선: 요소를 고르면(판) 셸이 `hd-up`(tag `cue…` — 막대 `[상위]` 와 따로)으로 조상을 묻고 `parentPick`(상자가 다른 첫 조상)에 `.elbox.par` — `--ui-muted` 점선, 고른 테두리보다 얇다(1 대 2). 답이 1.5초 없으면 `[hd]` 경고만
  - 레이어 줄에 올리면 판 강조: 화면 = 그 카드, 줄·폴더 = 그 아래 보이는 화면, 판 글 = 그 글(`.lyhov`·`.lyhov-t`, `--ui-mark` 윤곽) — 고르기는 바꾸지 않는다(view-layers `ctx.hover`)
  - 앱 카드: 요소 상자 `data-tone="app"` = `--ui-app`(Figma 인스턴스 보라 자리) · 고른 상자 아래 오른쪽 꼬리표 '요청으로만'
  - 요소 오른쪽 클릭 메뉴 맨 위 '고르기 ▸'(Figma Select layer): 올리기·누르기·→ 로 옆 목록 `#cmsub` = 그 요소(✓) + 조상(`chainOf` — 앞에 남긴 것과 같은 상자인 감싸기는 건너뜀, 가까운 것부터 최대 8) · 고르면 판 = 그 카드만 고르고 그 요소(막대·부모 점선), 크게 보기 = 막대. ← ·Esc = 옆 목록만 닫기
- 도우미 없이 끌어 옮기기(51-3 셸 빚): `h.drop = {from, slot, copy}` → `reorder.plan` → 반영 대기 메모 하나 `{edit:'move', op:'to', to}`(글 `say.moveTo`) · 미리보기 `hd-pending {path, to}`(palette.js — `hd-opt` 의 to 와 같은 자리) · Alt 복제는 도우미 없이 안 됨(view-blocks 와 같은 토스트)

## 아직

- 끌어서 순서 바꾸기 = 49c(`instant.md`) — 같은 부모 안만
- 부품 뼈대 = 견본의 '기본' 모습 하나만(변형 고르기 없음) · 넣은 부품의 글·데이터는 사람이 고치거나 AI 에게
- 판 카드가 아직 안 실린(보이지 않는) 상태에서 쓰면 따라가기는 15초 뒤 걷힌다

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/blocks.js` · `view-blocks.js` · `specimen_parts.py`(+ `tests/test_canvas_unit_blocks.py` · `test_canvas_unit_blocks_b.py` · `test_canvas_unit_blocks_place.py` · `test_canvas_unit_figma_keys.py` · `test_canvas_unit_cues.py` · `test_canvas_unit_bar_place.py` · 브라우저 `test_canvas_blocks.py` · `test_canvas_blocks_b.py` · `test_canvas_blocks_place.py` · `test_canvas_figma_keys.py` · `test_canvas_cues.py` · `test_canvas_blocks_clear.py`) · `bar-place.js` · `helper.py` duplicate·move·attr·insert·replace·`/api/parts` | `unit or tools or modal or helper` |
