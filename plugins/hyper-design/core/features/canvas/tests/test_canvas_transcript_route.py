"""S3b 연결 — 세션이 터미널 대화 펌프를 갖고, GET /api/agents/transcript 가 고른·접속한 에이전트에만 답한다."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from test_canvas_unit_q2b import _post, helper, out  # noqa: F401  — 같은 결과 폴더 사본 fixture

pytestmark = [pytest.mark.slow, pytest.mark.area("helper")]


def _get(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("X-HD-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def test_transcript_route_answers_only_for_a_connected_agent(out):  # noqa: F811
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = srv.url.split("/index.html")[0]
    try:
        assert srv.session.transcripts is not None, "세션이 펌프를 갖는다"
        code, _ = _post(base + "/api/hello", {"agent": {"id": "ag-t", "kind": "codex", "listen": False}}, srv.token)
        assert code == 200
        assert _get(base + "/api/agents/transcript?agent=ag-t")[0] == 403, "토큰 없으면 거절"
        code, body = _get(base + "/api/agents/transcript?agent=ag-t", srv.token)
        assert code == 200 and body["source"] == "none" and body["entries"] == [] and "cursor" in body, body
        assert _get(base + "/api/agents/transcript?agent=stranger", srv.token)[0] == 403, "고르지도 접속하지도 않은 에이전트"
        assert "ag-t" in srv.session.transcripts.watching(), "물어본 에이전트는 그 뒤 새 줄을 이벤트로"
    finally:
        srv.shutdown()
        srv.server_close()
