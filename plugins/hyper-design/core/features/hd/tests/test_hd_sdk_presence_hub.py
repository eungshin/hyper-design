"""hd_sdk 접속 통합(task 47-5a) — 이 프로세스 안 진짜 허브(빈 포트, 임시 HD_HOME, 가짜 빌드). 터미널 없이 받기:
Hub.hello(프로젝트) → 목록에 here → 캔버스 보내기(POST /api/forward to = 내 id) → Project.requests() 가 받음 → progress → bye = away. 실제 에이전트·paseo 없음."""
import sys, threading, time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402
from test_hd_sdk_hub import hub  # noqa: E402,F401

import hd_sdk as S  # noqa: E402

pytestmark = pytest.mark.slow


def test_an_agent_receives_a_canvas_request_without_a_terminal(hub, tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    h = S.Hub()
    h.save(out=str(out))
    h.open("proj-a")
    p = h.hello("proj-a", id="ag-sdk", name="SDK", kind="codex", lease=3)
    try:
        assert p.me == "ag-sdk" and p.heartbeat is not None and p.heartbeat.every == 1.0
        rows = {a["id"]: a for a in p.agents()}
        assert rows["ag-sdk"]["state"] == "here" and rows["ag-sdk"]["kind"] == "codex" and rows["ag-sdk"]["listen"] is True
        got = []

        def read():
            for e in p.requests(timeout=8):
                got.append(e)
                return
        t = threading.Thread(target=read, daemon=True)
        t.start()
        time.sleep(0.5)
        canvas = S.Project(p.marker)                 # 캔버스 쪽(같은 세션 토큰) — 보내기 = POST /api/forward
        res = canvas._call("POST", "/api/forward", {"text": "버튼 문구 바꿔 주세요", "to": "ag-sdk", "notes": ["n1"]})
        assert res["via"] == "event", res
        t.join(10)
        assert got and got[0].data["text"] == "버튼 문구 바꿔 주세요" and got[0].data["notes"] == ["n1"] and got[0].id == res["event"]
        time.sleep(4)                                # 임대 3초보다 길게 — 맥박이 here 로 지킨다
        assert {a["id"]: a for a in p.agents()}["ag-sdk"]["state"] == "here"
        assert isinstance(p.progress("버튼 고치는 중", screen="home"), int)
        assert {a["id"]: a for a in p.agents()}["ag-sdk"]["progress"]["text"] == "버튼 고치는 중"
    finally:
        p.bye()
    assert {a["id"]: a for a in p.agents()}["ag-sdk"]["state"] == "away"
