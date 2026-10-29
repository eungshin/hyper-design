# 여러 화면에 같은 메모 (memo-batch)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만.

## 규칙

- **때** — 카드를 여러 장 고르면 선택 막대(`#selbar`)에 [메모]가 보인다(한 장일 때와 같은 단추). 누르면 메모 창이 고른 화면 전체를 대상으로 열린다. 제목 = `고른 화면 N개 — 제목 · 제목 …`
- **범위** — 여러 장이면 '이 요소'는 없다(화면 전체 메모). 고르기 = `고른 화면 N개`(값 `screen`, 기본) · `모든 화면`(값 `all`). 한 장이면 지금처럼 세 개
- **추가** = 한 동작, 되돌리기 한 단계:
  - `screen` — 고른 화면마다 메모 하나(`path=body`, `scope=screen`, 같은 `batch` id). 메모마다 그 화면의 번호(`no`)를 받고 요청문에 따로 `screen=… · no=N` 으로 나간다 — `hd claim`·`hd reply <screen>#<no>` 흐름은 그대로(화면마다 따로 닫힌다). `edits.js` 묶음 규칙은 바꾸지 않는다(화면이 다르면 다른 항목)
  - `all` — 첫 화면에 메모 하나(`scope=all`, `batch` 없음) — '모든 화면' 요청이 여러 번 나가지 않게
- **그 뒤** — 메모는 하나씩 고치고 지운다(`batch` 는 기록용 — 함께 고치기는 아직 없음). 고른 카드 차례 = 화면 고른 차례(겹침 빼고)
- **메모 도구 화면 모드(M) Shift+클릭** — 열린 새 화면 메모에 그 화면 더하기·빼기(`toggle(ids, id)`, 쓰던 글·의도·범위 그대로 — `memo-tool.md`)
- **층** — `memo-batch`(Model): `draft(ids, titleOf)`·`multi`·`toggle`·`scopes(draft, SCOPES)`·`defaultScope`·`label`·`build(draft, {note, intent, scope}, mkId) → [메모]`(입력은 고치지 않음). 셸(템플릿 손댄 곳): `placeSelbar` 의 [메모] 보이기 · `#selbar` [메모] → `MP.card(ids)` · 메모 창(`view-memo-pop`) 범위 단추(`HD.memoBatch.scopes`) · `commitPop` 이 초안이 여러 장이면 `build` 로 메모를 넣고 `record` 한 번

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/memo-batch.js` · 셸 `placeSelbar` · `view-memo-pop` `card`·범위·추가 | `unit or tools or notes` |
