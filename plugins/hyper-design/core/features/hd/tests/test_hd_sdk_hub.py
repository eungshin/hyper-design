"""hd_sdk 통합 — 이 프로세스 안에 진짜 허브(home_server.make_hub, 빈 포트)를 띄우고 임시 HD_HOME 의 home.json 으로 SDK 가 찾게 한다.
Hub → open(허브 POST /api/open → 세션) → Project(notes·reply·claim·release·apply·files·stop)를 진짜 HTTP(/v1/p/<이름>/api/*)로.
빌드는 가짜(index.html 이 이미 있음), paseo 는 없는 명령 — 12270·12279·실제 ~/.hyper-design·실제 에이전트는 건드리지 않는다.
"""
import json, subprocess, sys, threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path[:0] = [str(hdfix.HD), str(hdfix.HD.parent / "home")]
import hd_client as C  # noqa: E402
import hd_sdk as S  # noqa: E402
import home_client as H  # noqa: E402
import home_server  # noqa: E402

pytestmark = pytest.mark.slow


def fake_build(out):
    return subprocess.CompletedProcess([], 0, "", "")


@pytest.fixture()
def hub(tmp_path, monkeypatch):
    monkeypatch.setenv("HD_HOME", str(tmp_path / "home"))
    for k in ("PASEO_AGENT_ID", "HD_PASEO_AGENT", "HD_PASEO_CMD"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(C, "build", lambda out: (0, ""))          # 허브가 열 때 build_ref 대신(hdfix out 에 index.html 이 있다)
    old_local = C.LOCAL
    srv = home_server.make_hub(0, renderer=lambda *a, **k: None, picker=lambda: None, build=fake_build, paseo=str(tmp_path / "no-paseo"))
    C.LOCAL = None                                                # 이 테스트는 허브 '밖'의 SDK 처럼 home.json → /v1/sessions 로 찾는다
    H.write_hub(srv.url, srv.server_address[1], srv.token)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        H.clear_hub()
        C.LOCAL = old_local


def test_sdk_round_trip_through_a_real_hub(hub, tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    h = S.Hub()
    assert h.running and h.url == hub.url and h.hello()["sessions"] == 0
    e, added, _ = h.save(out=str(out))
    assert added and e["name"] == "proj-a"

    e, p, reused = h.open("proj-a")
    assert not reused and p.online and "/v1/p/proj-a/index.html?hd=" in p.url and p.marker.get("hub") is True
    assert h.hello()["sessions"] == 1 and [c.name for c in h.canvases()] == ["proj-a"] and h.pick().name == "proj-a"

    ns = p.notes()
    assert [n.ref for n in ns] == ["home#1", "home#2", "list#1"] and p.state()["rev"] == 3
    res = p.reply("home#1", {"kind": "반영됨", "what": "버튼 문구", "screens": ["home"], "captured": False, "by": "sdk"})
    assert res["status"] == "done" and res["rev"] == 4
    assert [n.ref for n in h.pick("proj-a").notes()] == ["home#2", "list#1"]
    with pytest.raises(S.Invalid):
        p.reply("home#2", {"kind": "반영됨", "what": "x"})

    c = p.claim("list", by="sdk", note="간격")
    assert c["screen"] == "list" and json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))["state"]["busy"]["items"]["list"]["by"] == "sdk"
    assert p.release("list")["released"] is True
    a = p.apply([{"id": "e1", "screen": "home", "edit": "text", "path": "body > h1:nth-of-type(1)", "value": "새 제목"}])
    assert a["applied"] == ["e1"] and "새 제목" in (out / "screens" / "home.html").read_text(encoding="utf-8")
    assert set(p.files()) >= {"seq", "changed"}

    stranger = S.Project(dict(p.marker, token="wrong"))
    with pytest.raises(S.Unauthorized) as ei:
        stranger.notes()
    assert ei.value.next and "다음:" in ei.value.line()
    with pytest.raises(S.NotYet):
        p.events()

    assert p.stop() == "route" and h.hello()["sessions"] == 0
    with pytest.raises(S.NotFound):
        p.notes()                                                 # 세션이 닫힌 프로젝트 = 404 '열려 있지 않은 프로젝트'
    hub.shutdown()
    hub.server_close()
    with pytest.raises(S.Offline) as ei:
        p.notes()
    assert "다음:" in ei.value.line()
