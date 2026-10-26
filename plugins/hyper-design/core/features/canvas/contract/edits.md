# 편집 메모 (edits)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `edits.js` — 편집 메모 하나가 진실 원천: 반영 대기 선·빈 레이아웃·글자 미리보기·도우미가 바로 쓸 것은 모두 메모에서 계산한다. 요청문(`request`)에서 요청 글의 줄바꿈은 `요청: ` 글자 자리에 맞춰 들여 쓴 다음 줄로 남는다(한 줄 메모는 예전 그대로). 항목 머리 = `번호. screen=… · path=…` 끝에 ` · no=N[,M…]`(#279 — 그 항목에 든 메모의 화면 안 번호 `n.no`, 차례대로·겹침 없이, 번호 없는 옛 메모뿐이면 이 조각 없음). fix 스킬의 `ITEM_RE` 가 읽고 메모를 번호로 닫는다(`hd reply <screen>#<no>`, `test_fix_skill.py`) · 셋째 인자 `sizes = {화면 id: 'W×H(프리셋)'}`(기본 크기가 아닌 카드, task 46 `contract/artboard.md`)면 그 항목 아래 `   화면 크기: …` 줄
- 글자 고치기(`edit:'text'`, task 30): 요소 안 내용 **전부**(글 마디 여럿 · `<br>` · 인라인 자식 b·strong·i·em·span…)를 새 글로 바꾼다(`
` = `<br>`, 앞뒤 공백 그대로). 안에 인라인 아닌 자식(블록·그림·입력·링크 `a`)이 있으면 일부만 바꾸지 않고 거절 — "안에 다른 요소가 있어 글자만 바꿀 수 없어요 — 요소를 골라 주세요". 예외 **아이콘 + 글**(R15): 글이 있고 자식 요소가 글이 없거나(svg·img·빈 i/span = 아이콘) 글 든 인라인만으로 된 것이면(예: `<a><svg…/> 이전</a>` · `<button><svg/> <b>뜻</b> 보기</button>` · `<a><i class="ic"></i><span>다음</span> 단계</a>`) 글 조각만 바꾸고 아이콘은 원문 그대로. 글 묶음 = 바로 아래 글·`<br>`·글 든 인라인 요소가 이어진 것(아이콘에서 끊김). 묶음이 하나이고 바뀐 곳(앞뒤 같은 글자를 뺀 가운데, 넣기만이면 앞 글자의 마디)이 글 마디 하나 안이면 **그 마디만** 고친다 — b·span 꾸밈 그대로(그 마디 안 공백은 하나로, 엔티티는 글자로 풀려 다시 escape). 그 밖(여러 마디에 걸친 바뀜 · 마디가 비거나 가장자리 공백이 바뀜 · 아이콘 사이 글 묶음 여럿)은 첫 글 묶음 = 앞뒤 공백 + 새 글 — **그 묶음 안 꾸밈(b·span…)은 없어지고**, 뒤 글 묶음은 비운다. 거절(BLOCK_REASON): 글 든 자식이 블록·링크 `a` 이거나 글 조각 안에 아이콘이 든 것(`<span><svg/>다음</span>` — 어디까지가 글인지 모호). 그 자리 고치기는 첫 글 묶음만 감싼 `span[data-hd-txt]` 를 contenteditable 로(아이콘은 칸 밖). 같은 규칙이 세 곳: `html_edit.py` `INLINE`·`_inline_only`·`_icon_text`·`_icon_text_patch`(파일, unit `test_canvas_unit_icon_text.py`) · `palette.js` `textOk`/`textMode`/`runChars`/`oneLeaf`/`setIconText`(미리보기·바로 반영 · `hd-hit`/`hd-dbl` 답의 `textOk` → 캔버스는 고치기 칸을 열지 않고 토스트)
- 바로 쓰기(task 49a): 도우미가 있으면 글자 고치기도 `instantOf` — 누르는 즉시 파일에(되돌리기 = 되살리기), 거절되면 반영 대기 + 까닭 토스트. 도우미가 없으면 예전처럼 반영 대기 → 보내기
- 요소 복제(`edit:'duplicate'`)·옮기기(`edit:'move'`, `op` up|down) — `directOf`·`instantOf`, 미리보기 `{path, dup:true}`·`{path, move}`, 글귀 `say.duplicate()`·`say.move(dir)`. 규칙·도우미 동작은 `blocks.md`
- 속성(`edit:'attr'`, `op` = 속성 이름, `value` = 새 값)·부품 넣기(`edit:'insert'`)·바꾸기(`edit:'replace'`, `value` = 견본 key) — task 49b, `directOf`·`instantOf`, 미리보기 `{path, attr, value}`(넣기·바꾸기는 없음), 글귀 `say.attr(name, v)`·`say.insert(title)`·`say.replace(title)`. 규칙·허용 목록·뼈대는 `blocks.md`
- 빈 글 저장 = 글 비우기(요소는 남음, `say.text('')` = '글자 비우기 …'). 다른 글자 고치기처럼 반영 대기 · 되돌리기 한 번
- 요소 지우기(`edit:'remove'`): 요소 메뉴 '요소 지우기'(Del) · 고른 요소에서 Delete · 고치기 칸(판·크게 보기)의 [요소 지우기]. `instantOf` — 도우미가 있으면 바로 파일에(`/api/apply`, 되돌리기 = 되살리기), 없으면 반영 대기이고 요청문은 `요청: 요소 지우기 — …`(`say.remove()`; 화면 삭제 글귀는 `say.removeScreen(label)`). 도우미는 시작 태그부터 닫는 태그 끝까지 지운다(void·`/>` = 시작 태그만) · html·head·body·화면 뿌리(body/맨 위의 유일한 요소)·닫는 태그 없는 요소는 거절. 거절 까닭은 토스트로
- 미리보기 `preview(notes, screen)` → `hd-pending` 항목 `{path, text}` · `{path, remove:true}`(숨김). 화면은 안의 마디를 떼어 두었다가 다음 호출에서 그대로 되돌린다
- 한 화면에 편집 여럿 = 원문 위치 뒤에서부터. 같은 요소 두 글자 고치기 = 나중 것 · 겹치는 자리(안팎)는 나중 편집이 실패(앞 것은 씀)
- 정책 목록(`edit:'policies'`, task 31): `value` = 줄 목록 전체(path `screens.json > screens[id=…] > policies`), 바로 쓸 수 있는 편집(`directOf`) — 보내면 도우미가 그 목록으로 통째로 바꾸고, 도우미가 거절하면(글 목록·50줄·500자) 다른 바로 쓰기 편집처럼 요청문으로 넘어간다. 요청문 글귀 `say.field('policies', 목록)` = `정책 줄 바꾸기: ① … ② … (screens.json의 policies 전체)`(빈 목록 = `정책 줄 모두 지우기 …`), fix 스킬 형식 그대로. 옛 `policy`(index) 메모는 읽고 쓰기만 그대로 둔다
- 소스 위치(task 27 → 30): 고른 요소의 `src`(앱 카드)는 메모 대상에 남고, 요청문에 `   소스: <file>:<line>`(요청 줄 다음, src 가 있는 항목만)

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/edits.js`(+ `tests/test_canvas_unit_text_remove.py` · 브라우저 `test_canvas_text_remove.py`) · `history.js` · `view-history.js`(기록 시간줄·되돌리기) · `view-notes.js`(메모·반영 대기 목록) | `unit or tools or notes` |
