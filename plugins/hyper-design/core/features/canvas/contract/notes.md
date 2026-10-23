# 메모 목록 저장소 (notes)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만(contract.md 에서 옮김 — task 22).

## 규칙

- `notes`(Model) — 메모 목록 저장소(키 `hd-notes:`, 읽기·쓰기는 셸): 목록 하나(`list`·`add`·`remove`·`find`·`unsent`)와 `commit()` = 지난 저장 뒤 메모가 바뀐(더함·뺌·제자리 고침) 화면 id. 셸 `saveNotes` 는 그 카드만 다시 그린다(배지·삭제 대기·카드 글·`hd-pending`), 판의 선은 `linesKey`(잇기·끊기·삭제·빈 레이아웃 메모)가 바뀔 때만 다시

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/notes.js`(메모 목록 저장소·닿은 화면) · `canvas_template.html` 메모·주석 부분(`saveNotes`·`renderNotes`·보내기) | `unit or notes or modal or tools` |
