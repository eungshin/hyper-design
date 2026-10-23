"""helper.py — POST /api/reply(답 붙이기 · rev+1 · 400/404) 와 떠 있는 표지(HD_HOME/active/<pid>.json). HTTP 만, 브라우저 없음."""
import json, sys, threading, urllib.error, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path.insert(0, str(hdfix.CANVAS))
import helper  # noqa: E402


@pytest.fixture()
def served(tmp_path):
    out = hdfix.make_out(tmp_path)
    srv = helper.make_server(out)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield out, srv
    srv.shutdown(); srv.server_close()


def post(srv, body, token=None):
    req = urllib.request.Request("http://127.0.0.1:%d/api/reply" % srv.server_address[1], data=json.dumps(body).encode("utf-8"),
                                 method="POST", headers={"X-HD-Token": token or srv.token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def state(out):
    return json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))


GOOD = {"kind": "반영됨", "what": "버튼 문구 '다음'→'계속' (home)", "screens": ["home"], "captured": True}


def test_reply_appends_with_rev_plus_one(served):
    out, srv = served
    code, res = post(srv, {"note": {"screen": "home", "no": 1}, "reply": GOOD})
    assert code == 200 and res["rev"] == 4 and res["status"] == "done", res
    doc = state(out)
    assert doc["rev"] == 4 and doc["state"]["card-pos"] == {"home": [1, 2]}, "다른 키는 그대로"
    r = doc["state"]["notes"][0]["replies"]
    assert len(r) == 1 and r[0]["by"] == "agent" and r[0]["at"][:4].isdigit() and r[0]["what"] == GOOD["what"]
    code, res = post(srv, {"note": "n2", "reply": {"kind": "질문", "question": "토큰으로 바꿀까요?", "choices": ["네", "아니요"], "by": "codex"}})
    assert code == 200 and res == {"rev": 5, "status": "decide", "note": "n2", "screen": "home"}
    assert state(out)["state"]["notes"][1]["replies"][0]["by"] == "codex"
    code, res = post(srv, {"note": {"screen": "list", "no": 1}, "reply": {"kind": "일부", "done": "간격 8px", "left": "모바일은 질문"}})
    assert code == 200 and res["status"] == "partial" and res["note"] == "n3", "번호 없는 메모는 화면 목록 차례로"


def test_reply_invalid_is_400_with_one_line_per_field(served):
    out, srv = served
    code, res = post(srv, {"note": "n1", "reply": {"kind": "반영됨", "what": "", "screens": ["ghost"], "captured": "yes"}})
    assert code == 400 and res["errors"], res          # 칸마다 한 줄·차례는 hd_model(test_one_line_reason_per_failed_field)이 지킨다
    code, res = post(srv, {"note": "n1", "reply": {"kind": "답변", "text": "네"}})
    assert code == 400 and "답변은 질문 메모에만" in res["error"]
    code, res = post(srv, {"note": "n4", "reply": GOOD})
    assert code == 400 and "보내지 않은" in res["error"]
    code, res = post(srv, {"note": "n1"})
    assert code == 400
    assert state(out)["rev"] == 3, "거절하면 파일은 그대로"


def test_reply_user_kind_rejected(served):
    out, srv = served
    for kind in ("확인", "다시"):
        code, res = post(srv, {"note": "n1", "reply": {"kind": kind}})
        assert code == 400 and "사람만" in res["error"], res
    code, res = post(srv, {"note": "n1", "reply": {"kind": "보류", "why": "나중에"}})
    assert code == 400 and res["errors"][0].startswith("kind:")


def test_reply_unknown_note_404_and_token(served):
    out, srv = served
    assert post(srv, {"note": "nope", "reply": GOOD})[0] == 404
    assert post(srv, {"note": {"screen": "home", "no": 9}, "reply": GOOD})[0] == 404
    assert post(srv, {"note": "n1", "reply": GOOD}, token="wrong")[0] == 403
    assert state(out)["rev"] == 3


def test_reply_applies_on_latest_file(served):
    out, srv = served
    doc = state(out)
    doc["rev"] = 10; doc["state"]["hidden"] = ["list"]
    (out / ".hd-canvas.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    code, res = post(srv, {"note": "n1", "reply": GOOD})
    assert code == 200 and res["rev"] == 11 and state(out)["state"]["hidden"] == ["list"]


def test_marker_written_on_start_removed_on_stop(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    p, url = hdfix.start_helper(out, home, agent="ag1")
    try:
        m = home / "active" / ("%d.json" % p.pid)
        assert m.is_file()
        d = json.loads(m.read_text(encoding="utf-8"))
        assert d["pid"] == p.pid and d["project"] == "proj-a" and Path(d["out"]) == out.resolve() and d["url"] == url
        assert d["agent"] == "ag1" and d["port"] == int(url.split(":")[2].split("/")[0]) and d["token"] in url and d["started"]
    finally:
        clean = hdfix.stop_helper(p)
    assert clean, "도우미가 정상 종료 신호로 끝나지 않았다"
    assert not m.exists(), "정상 종료하면 표지를 지운다"
