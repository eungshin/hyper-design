"""접속·보내기 계약 잠금(task 47-5a) — presence.json 을 이 프로세스 안 진짜 허브(home_server.make_hub)에 다시 보낸다.

허브·가짜 빌드·흐름 읽기는 test_protocol_events.py 것을 그대로 쓴다(임시 HD_HOME · 12270·12279 아님 · paseo 없음 · 실제 에이전트 없음).
routes = 줄마다 한 요청(한 세션에서 차례로 — 앞 줄이 만든 에이전트를 뒤 줄이 본다), flows = 여러 요청·흐름(흐름마다 새 세션).
이벤트 모양은 events.json 의 types(agent.* · request.sent 도 거기).
"""
import json, pathlib, sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_protocol_events import Stream, fill, hub, read_events  # noqa: E402,F401  — hub = 픽스처
from test_protocol_v1 import check, send  # noqa: E402

pytestmark = pytest.mark.slow
DOC = json.loads((HERE / "presence.json").read_text(encoding="utf-8"))


def test_presence_routes(hub):
    port, vars_ = hub["port"], dict(hub["vars"])
    errs = []
    for route in DOC["routes"]:
        for case in route["cases"]:
            label = "%s %s [%s]" % (route["method"], route["path"], case["name"])
            exp, req = case["expect"], case["request"]
            status, _, raw = send(port, None, dict(req, token=req.get("token", False)), vars_)
            if status != exp["status"]:
                errs.append("%s: 상태 %s 이어야 하는데 %s %s" % (label, exp["status"], status, raw[:300]))
                continue
            if "json" in exp:
                errs += ["%s: %s" % (label, e) for e in check(fill(exp["json"], vars_), json.loads(raw))]
    assert not errs, "\n".join(errs)


@pytest.mark.parametrize("flow", DOC["flows"]["cases"], ids=lambda f: f["name"])
def test_presence_flow(hub, flow):
    port, vars_ = hub["port"], dict(hub["vars"])
    streams, errs = {}, []
    try:
        for n, step in enumerate(flow["steps"]):
            label = "%s #%d" % (flow["name"], n)
            if "open" in step:
                s = streams[step["open"]] = Stream(port, step["request"], vars_)
                assert s.status == 200, (label, s.status, s.body)
                assert s.frame().get("retry") == "2000", label
            elif "send" in step:
                status, _, raw = send(port, None, fill(step["send"], vars_), vars_)
                exp = step["expect"]
                assert status == exp["status"], (label, status, raw[:300])
                body = json.loads(raw) if raw else None
                if "json" in exp:
                    errs += ["%s: %s" % (label, e) for e in check(fill(exp["json"], vars_), body)]
                for var, key in step.get("save", {}).items():
                    vars_[var] = body[key]
            elif "events" in step:
                _, e = read_events(streams[step["events"]], step["types"], step.get("shapes"), vars_, label)
                errs += e
            else:
                raise AssertionError("모르는 단계: %r" % step)
    finally:
        for s in streams.values():
            s.close()
    assert not errs, "\n".join(errs)


def test_forward_to_a_listening_agent_still_writes_the_queue_file(hub):
    """이벤트로 보내도 대기열 파일은 남는다(기록 · 에이전트가 이벤트를 놓쳐도 파일로 찾는다)."""
    port, v = hub["port"], hub["vars"]
    assert send(port, None, {"method": "POST", "path": "/v1/p/proj-c/hello", "token": v["session"], "body": {"agent": {"id": "ag-9"}}}, v)[0] == 200
    st, _, raw = send(port, None, {"method": "POST", "path": "/v1/p/proj-c/api/forward", "token": v["session"], "body": {"text": "글", "to": "ag-9"}}, v)
    res = json.loads(raw)
    assert st == 200 and res["via"] == "event" and pathlib.Path(res["path"]).read_text(encoding="utf-8") == "글", res
