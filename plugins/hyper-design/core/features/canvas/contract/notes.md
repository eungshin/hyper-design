# 메모 목록 저장소 (notes)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `notes`(Model) — 메모 목록 저장소(키 `hd-notes:`, 읽기·쓰기는 셸): 목록 하나(`list`·`add`·`remove`·`find`·`unsent`)와 `commit()` = 지난 저장 뒤 메모가 바뀐(더함·뺌·제자리 고침) 화면 id. 셸 `saveNotes` 는 그 카드만 다시 그린다(배지·삭제 대기·카드 글·`hd-pending`), 판의 선은 `linesKey`(잇기·끊기·삭제·빈 레이아웃 메모)가 바뀔 때만 다시
- 보낸 메모 보기(task 29, `view-notes`): 메모 목록·카드 배지 수는 `annotation.visible(n, 켜짐)` 인 메모만 — 보내면 같은 render 에서 사라진다. 메모 막대(`.ntool`, task 32 — 한 줄 아이콘: `#ncnt` 메모 수 · `#nsent` 눈 · `#ndec` 거르기 · `#nclear` 모두 완료, 글은 `title`·`aria-label`) 안 `#nsent` '보낸 메모 보기 (N)'(N = `hiddenCount` = 배지 `.ncb[data-n]`, 템플릿이 아니라 View 가 그림): 0 이고 꺼짐이면 꺼진 단추(자리 유지), 켜짐 = 숨긴 메모도 흐리게(`li.nhid`) + 상태 말(`.nsst` AI 작업 중·완료). 보내기 건수(보내지 않은 것)·'결정 필요 N' 은 그대로. 숨긴 메모가 있으면 `#notes` 는 열려 있다. 켜짐 = 키 `hd-show-sent:<해시>` `'1'|'0'`(캔버스마다, 깨진 값 = `[hd]` 경고 + 꺼짐). 저장소·키는 셸이 `mount(ctx)` 로 건넨다(`ctx.storage`·`ctx.key(prefix)`, #263 — 페이지 속성·document 이벤트·복사한 해시 없음). 바뀌면 `ctx.sentChanged(켜짐)`(의도) → 셸이 핀 `render()`·묶음 `refresh()` 를 부르고, 핀·묶음은 셸이 건넨 `showSent()`(= `VN.showSent()`)로 읽는다
- 요소를 찾을 수 없음(#285): 화면이 메모 대상을 다시 찾지 못하면(`hd-located` how `none` — 경로가 요소 여럿·없음이고 글로도 못 찾음, 규칙 `relocate.lost`) 핀은 없고, 열린 메모 줄에 회색 말 `.nlost` '요소를 찾을 수 없음'(title '화면이 바뀌어 같은 요소가 여러 개이거나 없어요'). 핀이 답을 받으면 셸이 `VN.relost()` — 찾을 수 없는 메모가 바뀐 때만 목록을 다시
- 메모 줄의 고치기·지우기(task 32) = 줄 오른쪽 위 연필·휴지통 아이콘(`data-act="edit"|"del"`, 올리거나 포커스일 때 보임 — 자리는 늘 비워 두어 글이 밀리지 않는다)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/notes.js`(메모 목록 저장소·닿은 화면) · `canvas_template.html` 메모·주석 부분(`saveNotes`·`renderNotes`·보내기) | `unit or notes or modal or tools` |
| `modules/relocate.js`(핀이 될 대상·찾을 수 없음) · `view-pins.js` · `view-notes.js` | `unit or notes or modal` — 규칙은 `tests/test_canvas_unit_relocate.py` |
