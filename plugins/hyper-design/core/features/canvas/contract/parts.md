# 앱 부품 '낡음' 칩 (parts · view-parts, R30)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. parts.json 모양·도장 규칙은 `../contract.md` '앱 부품'.

## 규칙

- 낡음 판단은 도우미: `GET /api/app-parts` → `{parts:[{file, state, stale, stamp, current, dirty, dirty_now, built_at, label}], stale:[화면 id]}` (`session.parts` = `parts_file.PartsWatch` — 60초 캐시, 읽기만, 빌드하지 않음). 화면 → 끌어 쓰는 파일은 `busy._deps`(F25, iframe·link·script) 그대로라서 부품을 iframe 으로 싣는 화면만 고른다.
- `parts`(Model) `HD.parts.marks(body)` → `{화면 id: {text:'낡음', title}}`(title = 낡은 부품 이름 셋까지 · 미커밋 변경 포함 표시 · `hd parts --rebuild`) · `same(a, b)`. 모양이 틀린 답 = 표시 없음.
- `view-parts`(View): 열 때 한 번 + `HD.parts.EVERY`(60초)마다(탭이 보일 때만) 묻고, 카드 `.phone` 왼쪽 위에 `.pchip`(`role=status`, busy 상태 칩과 같은 모양 — 화면을 가리지 않음). 교체 `hd-swap` done 이면 그 카드에 다시 붙인다. 도우미가 없으면(`api.on` 거짓) 아무것도 하지 않는다. 읽기 실패는 `[hd]` 경고 한 줄(다시 성공할 때까지 한 번).
- 터미널: `hd notes` · `hd wait` 가 낡은 부품이 있으면 stderr 에 `[hd] 낡은 앱 부품 N개: … — 다시 빌드: hd parts --rebuild <이름>` 한 줄(hd/contract.md '앱 부품').

## 고치면 돌릴 것

| 고친 곳 | `-m` |
|---|---|
| `modules/parts.js` · `view-parts.js` · `router` `/api/app-parts` · `session.parts` | `-m unit -k parts` + `-m slow -k parts_file` + `tests/protocol -k every_route` + hd `-k parts` |
