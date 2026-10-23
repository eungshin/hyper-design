# 편집 메모 (edits)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `edits.js` — 편집 메모 하나가 진실 원천: 반영 대기 선·빈 레이아웃·글자 미리보기·도우미가 바로 쓸 것은 모두 메모에서 계산한다. 요청문(`request`)에서 요청 글의 줄바꿈은 `요청: ` 글자 자리에 맞춰 들여 쓴 다음 줄로 남는다(한 줄 메모는 예전 그대로)
- 글자 고치기(`edit:'text'`, task 30): 요소 안 내용 **전부**(글 마디 여럿 · `<br>` · 인라인 자식 b·strong·i·em·span…)를 새 글로 바꾼다(`
` = `<br>`, 앞뒤 공백 그대로). 안에 인라인 아닌 자식(블록·그림·입력·링크 `a`·글 없는 아이콘)이 있으면 일부만 바꾸지 않고 거절 — "안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요". 같은 규칙이 세 곳: `helper.py` `INLINE`·`_inline_only`(파일) · `palette.js` `textOk`(미리보기 · `hd-hit`/`hd-dbl` 답의 `textOk` → 캔버스는 고치기 칸을 열지 않고 토스트)
- 빈 글 저장 = 글 비우기(요소는 남음, `say.text('')` = '글자 비우기 …'). 다른 글자 고치기처럼 반영 대기 · 되돌리기 한 번
- 요소 지우기(`edit:'remove'`): 요소 메뉴 '요소 지우기'(Del) · 고른 요소에서 Delete · 고치기 칸(판·크게 보기)의 [요소 지우기]. `instantOf` — 도우미가 있으면 바로 파일에(`/api/apply`, 되돌리기 = 되살리기), 없으면 반영 대기이고 요청문은 `요청: 요소 지우기 — …`(`say.remove()`; 화면 삭제 글귀는 `say.removeScreen(label)`). 도우미는 시작 태그부터 닫는 태그 끝까지 지운다(void·`/>` = 시작 태그만) · html·head·body·화면 뿌리(body/맨 위의 유일한 요소)·닫는 태그 없는 요소는 거절. 거절 까닭은 토스트로
- 미리보기 `preview(notes, screen)` → `hd-pending` 항목 `{path, text}` · `{path, remove:true}`(숨김). 화면은 안의 마디를 떼어 두었다가 다음 호출에서 그대로 되돌린다
- 한 화면에 편집 여럿 = 원문 위치 뒤에서부터. 같은 요소 두 글자 고치기 = 나중 것 · 겹치는 자리(안팎)는 나중 편집이 실패(앞 것은 씀)
- 소스 위치(task 27 → 30): 고른 요소의 `src`(앱 카드)는 메모 대상에 남고, 요청문에 `   소스: <file>:<line>`(요청 줄 다음, src 가 있는 항목만)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/edits.js`(+ `tests/test_canvas_unit_text_remove.py` · 브라우저 `test_canvas_text_remove.py`) · `history.js` · `view-history.js`(기록 시간줄·되돌리기) · `view-notes.js`(메모·반영 대기 목록) | `unit or tools or notes` |
