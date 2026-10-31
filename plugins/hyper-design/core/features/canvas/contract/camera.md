# 판 카메라 — 첫 화면 · 눈앞 내용 제자리 (R27 F03·F17 · U2 F1a 10-31)

`../contract.md` 의 책임 게이트·테스트 층을 따른다. 이 파일은 그 기능의 규칙만. Ctrl+클릭 카메라 이동(`camera.js` · `view-motion.js`)은 `board-motion.md`·`contract.md` 표.

## 모듈

| 모듈 | 층 | 맡은 일 · 가진 상태 · 받는 것 · 내보내는 것 |
|---|---|---|
| `modules/camera-anchor.js` | Model | 눈앞 내용 제자리 규칙. 상태 없음. `HD.cameraAnchor = {pick(items, view) → id|null, keep(prev, next, view) → ty}` — items = `[{id, y, h}]` 판 좌표, view = `{h, z, ty}`. 규칙은 `tests/test_canvas_unit_camera_anchor.py` |
| `modules/view-camera-anchor.js` | View | 판 위 덩어리(`#stage` 의 흐름 속 자식 — 소개 글·DS 카드·꼬리말, `#rows` 대신 그 안의 줄들)를 재 두고 바뀌면 세로 이동만 보정. 상태 = 지난 배치 하나(저장 안 함). `HD.viewCameraAnchor.mount({stage, rowsEl, pane, getView, setView, busy})` → `{keep()}`. `#stage` 크기가 바뀌면(ResizeObserver) 스스로 keep |
| 셸 `home()` · `CAM` | — | 첫 카메라 한 번 + 붙이는 줄. 줄 사이를 다시 잰 같은 프레임(`#rows` ResizeObserver · `fonts.ready` · `fonts` `loadingdone`)에 `CAM.keep()` |

## 규칙

- 첫 카메라(`home`, 한 번): 배율 Z0, 첫 화면 줄(`.flow`) 위가 판 위 20px, 왼쪽은 떠 있는 도구 막대 오른쪽 + 16(좁으면 화면 줄이 바로 보이게). 소개 글·DS 카드는 위로 굴려 보는 곁 내용
- 그 뒤로는 사용자가 판을 안 움직였어도 내용 높이 변화(글꼴이 늦게 옴 · 줄 사이 다시 재기 · 메모 더하기·지우기 · 카드 크기)로 카메라를 다시 맞추지 않는다(옛 `rehome` 없앰 — 늦은 보정이 메모를 지울 때 한꺼번에 와 판이 114~220px 튀었다, 점검 10-31). 대신 눈앞 내용이 화면에서 제자리:
  - 기준 = 판 칸에 가장 많이 보이는 덩어리(1px 안으로 같으면 위의 것). 판 가장자리에 조금 걸친 것(DS 카드 끝 20px 등)은 기준이 아니다
  - 기준의 판 y 가 dy 만큼 움직였으면 `ty -= dy·z`(배율·가로는 그대로). 기준 아래쪽 변화는 카메라를 움직이지 않는다
  - 기준이 사라졌으면(줄을 지움) 그다음으로 많이 보이던 덩어리. 보이는 게 없거나 0.01px 아래 움직임이면 ty 그대로(같은 값 — 카메라를 다시 쓰지 않음)
  - 끄는 중(`drag.moved` — 카드 옮기기·판 끌기)에는 보정하지 않고 배치만 새로 잰다(끄는 카드가 포인터에서 떨어지지 않게)
- 사용자 이동·확대·전체 보기(`fit`)·고른 화면 맞추기·Ctrl+클릭 이동은 그대로 — 이 규칙은 그 뒤 내용 높이가 바뀔 때만 ty 를 보정한다
- `fonts.ready` 는 바깥 글꼴 CSS 가 오기 전에 풀리기도 해서 `document.fonts` 의 `loadingdone` 에서도 줄 사이(`RW.space`)를 다시 잰다 — 접힌 설명 높이가 글꼴로 바뀐 것을 다음 메모 더하기·지우기 때까지 미루지 않게

## 고치면 돌릴 것

| 고친 곳 | 돌릴 것 |
|---|---|
| `modules/camera-anchor.js` | `-m unit -k camera_anchor` |
| `modules/view-camera-anchor.js` · 셸 `home`·`CAM`·`#rows` ResizeObserver | `-m unit -k camera_anchor` + `tests/test_canvas_camera_anchor.py` + `-m "input or notes"` |
