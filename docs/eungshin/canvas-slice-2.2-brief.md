# 조각 2.2 바로 쓰기 — 계약서 (2026-10-21)

근거: `canvas-edit-rework-2026-10-20.md` E1·E9·E10·E17, §8 조각 2.2 줄. 이 파일이 일꾼이 보는 유일한 설계다.

## 목표
도우미(helper.py)로 열린 캔버스에서 **삭제·잇기·끊기는 누르는 즉시 화면 파일에 쓴다.** 되돌리기는 그 쓰기를 되살린다.
파일에 쓴 뒤 **페이지 전체 새로고침 없이** 바뀐 카드만 다시 불러온다. file:// 로 열면 지금처럼 반영 대기 + 복사.

## 정한 것
| # | 결정 |
|---|---|
| D1 | 바로 쓰는 편집 = 삭제(E1) · 잇기(link) · 끊기(cut·untrigger). 글자·이름·설명·정책은 지금처럼 반영 대기 → [보내기] |
| D2 | 바로 쓴 일은 기록에 `status:'file'` 로 한 줄. **잠그지 않는다**(lock 은 AI 에 보낸 자리만). 되돌리기 = `/api/restore`, 다시 하기 = 같은 편집을 다시 `/api/apply`·`/api/delete` |
| D3 | 삭제 = screens.json 에서 그 화면을 빼고(그리로 가는 branches 도), 화면 파일은 `.hd-history/<stamp>/` 로 옮긴다. 다른 화면 파일에서 그 화면으로 가는 링크는 끊는다(E10). 토스트 `n개 화면을 지웠어요 · 오는 연결 m개도 끊김` + [되돌리기] |
| D4 | 되살리기는 그 stamp 뒤에 파일이 바뀌지 않았을 때만(쓴 직후 해시와 같을 때). 다르면 거절 + 이유 → 캔버스는 토스트 "그 뒤에 파일이 바뀌어 되돌릴 수 없어요" |
| D5 | 빈 레이아웃(draft)·복제 카드 삭제는 지금처럼 메모만 지운다(파일 없음) |
| D6 | 다시 불러오기: 쓴 뒤 캔버스는 `/api/data` 로 새 hd-data 를 받아 바뀐 카드(`changed`)의 iframe 만 다시 싣고(`?v=<stamp>`), 이름·설명·정책·선을 새 데이터로 다시 그린다. 보던 위치·배율·고른 카드·열린 패널 유지. `location.reload` 없앰 |
| D7 | 위쪽 줄 모드 칩(E9): 도우미 = `파일에 바로 씀`, 아니면 `파일로 열림 · 바로 쓰기 안 됨`. 화면 글에 '도우미' 말 안 씀(토스트 포함) |
| D8 | 스킬 go·max·fix: 빌드 뒤 `helper.py <out>` 를 띄우고 출력 주소(`http://127.0.0.1:…/index.html?hd=…`)를 준다. 이미 떠 있으면 다시 띄우지 않는다 — helper 가 뜰 때 `<out>/.hd-helper.json` = `{url, pid}` 를 쓰고 끝날 때 지운다(스킬은 그 url 이 응답하면 재사용) |

## API (helper.py — 모두 POST, JSON, `X-HD-Token` · Host 검사 그대로)
```
/api/apply   {edits:[…]}          → {applied:[id], failed:[{id,reason}], stamp, changed:[screen]}      # 기존 + stamp·changed
/api/delete  {screens:[id]}       → {deleted:[id], cut:[{screen, path, to}], stamp, changed:[screen]}  # D3
/api/restore {stamp}              → {restored:[path], changed:[screen]}  |  409 {error, reason:'changed-since'}   # D4
/api/data    {}                   → build_canvas 의 hd-data 와 같은 객체                                  # D6
```
- 쓰기마다 `.hd-history/<stamp>/manifest.json` = `{files:{relpath:{before:<있었나>, after_sha:<쓴 뒤 sha256 | null(지움)>}}}`. restore 는 after_sha 가 지금 파일과 같을 때만 before 로 되돌리고(없던 파일은 지움) 다시 빌드.
- 다시 빌드 실패 시 기존처럼 원본 복구.
- `build_canvas.build_index` 에서 데이터 만드는 부분을 `index_data(out, m)` 로 떼어 `/api/data` 와 같이 쓴다(출력 index.html 은 그대로).

## 파일 소유 (단계별, 겹치지 않음)
| 단계 | 파일 | 받아들이기 검사 |
|---|---|---|
| A 도우미 | `helper.py`, `build_canvas.py`(index_data 떼기만), `tests/test_canvas_helper.py` | pytest: delete(오는 링크 끊김·branches·파일 이동) → restore 로 바이트 같음 · 그 뒤 파일 바뀌면 409 · apply 의 stamp/changed · /api/data == index.html 의 hd-data |
| B 캔버스 | `modules/view-sync.js`(신규 View) · `canvas_template.html` · `build_canvas.py`(모듈 목록 줄만) · `tests/test_canvas_modules.py`(목록) · `tests/conftest.py`(BROWSER) · `tests/test_canvas_edit.py`/`test_canvas_helper.py` 브라우저 테스트 | 도우미로 연 캔버스: 카드 삭제 → 파일·screens.json 에서 빠짐, 토스트에 오는 연결 수, Ctrl+Z → 되살아남 · 잇기 → 파일에 href, 새로고침 없음(window 표지 유지), 그 카드 iframe 만 다시 실림 · 모드 칩 두 가지 · file:// 은 지금처럼 |
| C 스킬 | `skills/go/SKILL.md` · `skills/max/SKILL.md` · `skills/fix/SKILL.md` | 세 파일에 빌드 뒤 helper 띄우기 단계와 주소 안내가 있다(grep) |

B 는 A 의 API 를 쓴다 → 순서 A → B, C 는 따로.

## view-sync.js (View) 모양
`HD.viewSync.mount(ctx)` → `{on, apply(edits) → Promise, del(ids) → Promise, restore(stamp) → Promise, send(list) → Promise}`
- ctx = `{token, post(url, body), data(newD), reloadCards(ids, v), toast(msg), mode(el)}` — 셸이 판 다시 그리기·카드 다시 싣기를 넘긴다(View 끼리 부르지 않는다).
- 셸의 `helperPost`·`#nsend` 도우미 분기·`location.reload` 는 여기로 옮기고 셸에서 지운다.

## 하지 않는 것
글자 편집의 바로 쓰기, 여러 사람이 같이 고치기, 도우미 자동 재시작, 원격 주소.
