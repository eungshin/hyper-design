# hd_sdk — 계약 (task 47-3)

터미널 에이전트(Claude Code · Codex · Paseo · 무엇이든)가 떠 있는 캔버스 서버에 말을 거는 표준 라이브러리 패키지. `hd` CLI(`../hd.py`)는 이 위의 얇은 껍데기다 — 명령·출력·종료 코드는 그대로(`tests/test_hd_cli_lock.py`).
말은 프로토콜 v1(`canvas/tests/protocol/v1.json` · `helper.json` · `hub.json`) — 허브 안 세션은 `/v1/p/<이름>/api/*`, 옛 도우미는 `/api/*`. 어느 쪽인지는 표지의 `prefix` 가 정한다(`hd_client._base`).

```python
import sys; sys.path.insert(0, "<plugin>/core/features/hd")
from hd_sdk import Hub, HdError
hub = Hub()                          # <HD_HOME>/home.json 의 허브(없어도 옛 도우미 표지로 찾는다)
p = hub.pick()                       # 떠 있는 캔버스 하나 — 여럿이면 hub.pick("이름" | out 경로)
for n in p.notes():                  # Note: 보냈고 끝나지 않은 메모
    p.claim(n.screen, by="me", note="고치는 중")
    ...                              # 화면 파일 고치기
    p.reply(n.ref, {"kind": "반영됨", "what": "…", "screens": [n.screen], "captured": False})
```

## 객체 (층 · 맡은 일 · 가진 상태)
| 파일 | 층 | 객체 | 맡은 일 | 상태 |
|---|---|---|---|---|
| `errors.py` | Model(순수) | `HdError` 가족 | 한국어 한 줄 `message` + 다음 행동 `next` · `line()` · `as_dict()` · `from_status(code, body, who)` | 없음 |
| `values.py` | Model(순수) | `Note` · `Event` | 값 객체. Note = `hd_model.rows` 줄 하나(키 순서 그대로, `ref` `is_open` `line`) · Event = events.json 의 `{id, type, ts, project, …}` | 없음(frozen) |
| `sse.py` | Model(순수) | `frames` · `event_of` | SSE 줄 → frame(`retry`·주석·`: hb` 건너뜀, data 여러 줄) → `Event`(reset frame = `Event(type='reset', data{reason, last})`) | 없음 |
| `transport.py` | Client 어댑터 | `HttpTransport` · `client_errors` | `request(method, path, body, timeout) → (code, 답)` = `hd_client.call` · `stream(path, last, timeout)` = `hd_client.stream`(SSE 줄) · hd_client 오류 → 가족 | 표지 하나 |
| `project.py` | Service | `Project` | notes · state · screens · files · reply · claim · release · apply · attach · stop · wait · events | 표지 하나(attach·wait 가 고침) |
| `hub.py` | Service | `Hub` | home.json 의 허브 · hello · new · canvases · project(고르기) · pick(고르기) · projects · open · save · forget | 없음(매번 hd_client 를 읽음) |
| `text.py` | View | — | 사람용 줄(`hd_model.format_rows` · `format_canvases` · `hd_projects.format_rows` · `link_line` 을 부를 뿐) | 없음 |

의존은 아래로만: hub → project → transport → `hd_client`(I/O 주인: 표지·home.json·projects.json·HTTP) → `hd_model`·`hd_projects`(규칙). errors·values 는 I/O 를 모른다(`test_hd_sdk_unit.test_model_modules_are_pure`). 규칙을 새로 만들지 않는다 — 답 검사·찾기·번호·상태·덮개·에이전트 id·고르기는 hd_model 하나(캔버스 `annotation.js` 와 같은 fixture).

## 오류 탐지
- 바깥으로 나가는 오류는 `HdError` 가족뿐: `Offline`(닿지 않음) · `NotFound`(404·없는 메모·화면·이름) · `Conflict`(409) · `TooLarge`(413) · `Unauthorized`(401/403 — 토큰이 바뀜) · `Invalid`(400·규칙 어긋남, 실패한 칸마다 한 줄) · `TimedOut`(종료 코드 2) · `NotYet`(아직 없는 기능). hd_client 의 `HdError`·`NotFound`·`TimedOut`·`Offline` 은 `client_errors` 가 같은 글로 바꾼다.
- `message` = 지금 CLI 글 그대로(`hd: ` 뒤). `next` = 메시지에 다음 행동이 없을 때만(가족 기본값 또는 만드는 쪽이 줌, `next=""` = 메시지가 이미 말함). CLI 는 `line()` = 같은 줄 ` — 다음: …`, `--json` 은 `{error, kind, next?}`(전에는 `{error}` — 키를 더했을 뿐).
- 서버 거절 = `from_status`: `'<도우미|홈 서버>가 거절했어요(<code>): <error 또는 errors 줄들>'`.
- 쓰기 전에 규칙으로 먼저 본다(답·덮개·에이전트 id·없는 화면) — 걸리면 서버에 가지 않는다.

## 아직 (다음 단계)
- `Project.events(since=None, timeout=None, retries=3)`(47-4b) = SSE `<세션>/api/events`(모양 `canvas/tests/protocol/events.json`) → `Event` generator. 끊기면 마지막 id 를 Last-Event-ID 로 다시 붙고(0.5·1·2…초, 연달아 retries 번 넘게 실패 = `Offline`), reset 은 `Event('reset')` 으로 내고 그 `last` 부터 — 받는 쪽은 상태를 다시 읽는다. 흐름이 없는 옛 서버(404)·흐름을 못 여는 transport = `NotYet`. timeout = 그 초 뒤 끝(오류 없음).
- `Project.wait` = 흐름이 열릴 때와 notes.changed·claim·release·reset 마다 상태를 다시 본다(타이머 없이 깨어남). 흐름이 없거나 끊겨 다시 못 붙으면 남은 시간 2초 `GET /api/state`(서버가 다시 뜨면 finder 로 새 표지).
- `Hub.hello()` = 지금은 `GET /v1/sessions`(허브 토큰)로 닿는지·토큰이 맞는지만. 접속 알리기·맥박(AgentPresence)은 task 47-5 가 서버에 hello 라우트를 더할 때.
- `apply(…, async=True)` 는 47-4a 서버가 받으면 그대로 넘어간다(옵션을 몸통에 그대로 실음).

## 테스트
`python -m pytest plugins/hyper-design/core/features/hd/tests -k "sdk or cli_lock"` — `test_hd_sdk_unit.py`(가짜 Transport: 가족·바꾸기·순수성·Note/Event·Project 읽기/쓰기/거절 종류/wait·Hub hello/new/고르기, 1초 안) · `test_hd_sdk_hub.py`(이 프로세스 안 진짜 허브 + 임시 HD_HOME: save → open → notes → reply → claim/release → apply → files → 틀린 토큰 Unauthorized → stop → 닫힌 세션 NotFound → 허브 끔 Offline) · `test_hd_cli_lock.py`(CLI 글자 그대로, 옛 도우미·허브 세션 둘 다).
