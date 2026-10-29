---
name: fix
description: hyper-design 캔버스에서 '보내기'로 복사한 메모를 화면에 반영한다. 사용자가 `[hyper-design 수정 요청]`으로 시작하는 글을 붙여넣거나 "캔버스 메모 반영해줘"처럼 캔버스 메모를 적용하라고 할 때 트리거.
---

# hyper-design:fix — 캔버스 메모 반영

**붙여넣은 요청문 → 질문은 답하고, 고칠 것은 화면별 수정 에이전트가 그 요소만 고친다.** 다른 요소·다른 화면은 건드리지 않는다.

**경로**: 이 스킬을 불러올 때 표시되는 Base directory의 `../../core`가 공용 폴더다. 맨 처음 한 번 `SK=$(cd "<Base directory>/../../core" && pwd)`로 절대경로를 정하고, 모든 명령·서브에이전트 프롬프트에 그 절대경로를 쓴다.

## 요청문 형식 (캔버스 '보내기'가 만든다)

```
[hyper-design 수정 요청] out=C:/Code/demo/out · 2건
1. screen=order-items · path=main > section.block:nth-of-type(2) > a.row:nth-of-type(1) · no=3
   text="와이셔츠 · 1벌 2,500원" · intent=change
   요청: 가격을 오른쪽 끝으로 붙이고 굵게
2. screen=home · path=main > div.badge:nth-of-type(1) · no=1
   text="바뀜" · intent=question
   요청: 이 배지는 무슨 뜻?
```

## 진행 — 한 턴

### 1. 읽기
- `SK`를 정한다. 첫 줄에서 `out=` 경로(아래 `<out>`)를 읽고, 번호 항목마다 `screen`·`path`·`text`·`intent`·`요청`·`no`를 뽑는다.
- 항목 머리 끝 ` · no=N`(여러 메모가 한 항목이면 `no=3,5`)은 그 항목에 든 캔버스 메모의 화면 안 번호다 — `path`는 ` · no=` 앞까지. 옛 요청문에는 없을 수 있다.
- 빈 레이아웃(새 화면) 요청의 `목적:` 글이 그 화면의 첫째 브리프다 — 그대로 `screens.json` 그 화면의 `purpose`가 된다(`요청:` 아래 들여 쓴 줄은 같은 요청의 다음 줄).
- 항목 아래 덧붙는 줄: `다른 곳:` 줄이 있으면 같은 요청을 그 경로들에도 · `범위: 이 화면 전체`/`범위: 모든 화면`이면 그 요소만이 아니라 그 화면 전체/모든 화면에 · 빈 레이아웃 `요청:` 아래 `- ` 줄은 그 화면에 남긴 메모 본문 · `화면 크기: 834×1194(iPad Pro 11)`이면 그 화면은 그 뷰포트(CSS px) 카드로 보이니 그 너비·높이에 맞게 배치를 고친다(캔버스의 카드 크기 — 화면 파일에 크기를 박지 않는다).
- `out=`이 없으면 한 번만 묻고 턴을 끝낸다: "어느 결과 폴더(out)의 화면인가요? 경로를 알려주세요." `[[ASK]]`

### 2. 질문 (`intent=question`)
- 메인이 채팅으로 바로 답한다 — 항목마다 짧은 한 문단. 파일은 고치지 않는다.
- 답할 때 `<out>/screens/<screen>.html`·`<out>/screens.json`·`<out>/decisions.json`을 필요한 만큼만 읽는다. 전문 용어 금지.

### 2b. 대화창 글 (`intent=chat`)
- 캔버스 하단 대화창에서 보낸 글이다. 사용자는 질문인지 수정 요청인지 고르지 않는다 — **받는 순간 네가 글을 읽고 정한다.**
- 질문·의견·논의·확인("넘어갔나?", "어떻게 생각해?")이면 2번처럼 채팅으로 답하고, 메모를 `답변 --text …`로 닫는다(파일은 고치지 않는다).
- 고치기·만들기 요청이면 3번 그대로 고치고 `반영됨`(또는 `일부`·`질문`)으로 닫는다.
- 둘이 섞였으면 고칠 것은 고치고, 물은 것은 같은 답의 `--text`/`--what`에 함께 적는다. 어느 쪽인지 정말 모호할 때만 `질문 --question …`.
- `범위: 모든 화면`·`screen=<첫 화면> · path=body`는 대화창이 붙인 자리표일 뿐이다 — 질문이면 그 화면을 고치지 않는다.

### 3. 고치기 (`intent=change`)
- 먼저 항목마다 `parts: existing | new`를 정한다. new = `<out>/components.css`·COMPONENTS에 없는 레이아웃 부품·클래스가 필요한 요청(블록 가운데 정렬·구분선·스크롤 목록 등). new는 screen-reviser에게 보내지 않는다 — 메인이 `components.css`를 `<out>/.hd-history/fix-components.css`로 복사해 두고, 디자인 토큰(`var(--…)`)만 써서 부품을 더한 뒤 화면 파일을 Edit.
- existing은 화면별로 묶는다. 고칠 화면 id를 모아 `python3 $SK/features/pack/pack.py <out> --mode revise --screens <id1,id2,…>` → `<out>/packs/plan.json`의 pack마다 하나씩.
- pack마다 서브에이전트 `hyper-design:screen-reviser`를 띄운다 — **한 메시지에 최대 5개, `model` 인자는 넣지 않는다**(정의 파일이 haiku로 정한다). 5개를 넘으면 다음 메시지에서 나머지.
- 프롬프트 형식:

```
PACK=<pack 절대경로>
화면 파일: <out>/screens/<screen>.html
요청:
<번호>. CSS 경로: <path>
   원래 글자: "<text>"
   할 것: <요청>
```
- `hyper-design:screen-reviser`를 서브에이전트 종류로 쓸 수 없으면 일반 서브에이전트를 `model: "haiku"`로 띄우고, 프롬프트 맨 위에 `$SK/../agents/screen-reviser.md`의 본문(입력·순서·규칙·보고)을 그대로 붙인다.

### 4. 확인
- 모두 돌아오면 같은 메시지에서 포그라운드로: `python3 $SK/scripts/selfcheck.py <out>` · `python3 $SK/features/canvas/build_ref.py <out>`(커밋된 캔버스 코드로 빌드 — 작업 트리의 `build_canvas.py`를 다른 세션이 고치는 중이어도 깨지지 않는다).
- 공용 CSS(`components.css`·`tokens.css`)를 고쳤으면 `python3 $SK/scripts/class_users.py <out> --css-old <out>/.hd-history/fix-components.css --css-new <out>/components.css`(클래스를 알면 `--classes a,b`)로 그 클래스를 쓰는 화면을 모두 찾아, 고친 화면과 함께 `python3 $SK/scripts/audit.py <out> --shots <out>/.shots` 캡처로 본다 — 고친 화면만 보지 않는다.
- 빌드 뒤 캔버스 열기는 go 의 '캔버스 열기'와 같다(`helper.py <out> --no-open` 백그라운드 · `<out>/.hd-helper.json` 의 주소가 응답하면 다시 띄우지 않는다. 응답이 없어도 그 `pid` 가 살아 있으면 새로 띄우지 말고 몇 초 뒤 그 주소를 다시 묻는다 — 같은 out 의 둘째 도우미는 어차피 '이미 떠 있어요'로 거절된다).
- selfcheck ❌가 이번 수정 때문이면 메인이 Edit 도구로 고친다(1회). 에이전트가 `not found`로 보고한 요청은 메인이 화면 파일을 읽고 직접 고치거나, 못 찾으면 그대로 보고한다. `needs-part: <무엇>`은 3단계 분류가 틀린 것 — 메인이 new처럼 처리한다.

### 5. 마지막 메시지
- 메모 닫기: `python3 $SK/features/hd/hd.py ls`가 되고 이 `<out>`이 목록에 있으면, 처리한 항목의 `no=` 번호마다(그 항목의 `screen` 과 함께 — `no=3,5`면 둘 다) `hd.py reply <screen>#<no> --out <out> --kind …`. 번호로 닫는다(화면·글로 메모를 다시 찾지 않는다). `no=`가 없는 옛 요청문만 `hd.py notes --out <out> --sent`에서 번호를 본다: 반영됨 `--what … --screens a,b --captured yes|no`(4단계 캡처) · 일부 `--done … --left …` · 대체됨 `--where …` · 질문·대화창(`intent=chat`) 메모는 답변 `--text …` · 미루면 조용히 넘기지 않고 질문 `--question … --choice A --choice B`.
- `hd`가 안 되면 항목마다 한 줄: `<번호> · done` / `<번호> · answered` / `<번호> · not found (이유 한마디)`.
- 안내 한 줄 + 여는 주소(`http://127.0.0.1…?hd=…`): hd로 닫았으면 "메모마다 결과가 붙었어요.", 아니면 "캔버스에서 '보낸 것 완료로'를 누르면 반영된 메모가 정리돼요."
- 마지막 줄: `[[DONE <out>/index.html]]` — 이 줄 없이 턴을 끝내면 미완성으로 처리된다.

## 참고
- 요청문 형식 원본: `$SK/features/canvas/canvas_template.html`의 `requestText` · 수정 에이전트: `plugins/hyper-design/agents/screen-reviser.md` · 설계: `docs/eungshin/tdr-v2.md` 14-3·14-4
