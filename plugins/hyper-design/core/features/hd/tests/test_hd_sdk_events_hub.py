"""hd_sdk events 통합(task 47-4b) — 이 프로세스 안 진짜 허브(빈 포트, 임시 HD_HOME, 가짜 빌드)에서 Project.events() 와 wait.
protocol events.json 의 흐름: 상태 쓰기 → notes.changed·claim·release(rev) · 이어 받기(since) · 너무 오래된 id = reset too-old · wait 가 이벤트로 깨어남."""
import sys, threading, time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402
from test_hd_sdk_hub import hub  # noqa: E402,F401

import hd_sdk as S  # noqa: E402

pytestmark = pytest.mark.slow


def opened(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    h = S.Hub()
    h.save(out=str(out))
    _, p, _ = h.open("proj-a")
    return p


def test_events_follow_state_writes_and_resume(hub, tmp_path):
    p = opened(tmp_path)
    got = []

    def read():
        for e in p.events(timeout=8):
            got.append(e)
            if len(got) == 3:
                return
    t = threading.Thread(target=read, daemon=True)
    t.start()
    time.sleep(0.5)                                   # 흐름이 열린 뒤에 쓴다(since 없음 = 지금부터)
    p.claim("home", by="sdk", note="고치는 중")
    p.release("home")
    st = p.state()
    p._call("PUT", "/api/state", {"rev": st["rev"], "state": {"x": 1}})
    t.join(10)
    assert [e.type for e in got] == ["claim", "release", "notes.changed"]
    assert got[0].data["screen"] == "home" and got[0].data["by"] == "sdk" and got[0].project == "proj-a"
    assert got[2].data["rev"] == got[1].data["rev"] + 1
    again = list(p.events(since=got[0].id, timeout=1.5))
    assert [e.id for e in again] == [got[1].id, got[2].id], "since 다음부터 다시 받는다"
    old = list(p.events(since=1, timeout=1.5))
    assert old and old[0].type == "reset" and old[0].data["reason"] == "too-old" and old[0].id == got[2].id


def test_wait_wakes_on_a_reply_event(hub, tmp_path):
    p = opened(tmp_path)
    st = p.state()
    notes = [dict(n, sent=False) for n in st["state"]["notes"]]
    p._call("PUT", "/api/state", {"rev": st["rev"], "state": {"notes": notes}})   # 보낸 메모 없음 → 기다림
    t0 = time.time()

    def send_later():
        time.sleep(1.0)
        s = p.state()
        p._call("PUT", "/api/state", {"rev": s["rev"], "state": {"notes": [dict(notes[0], sent=True)] + notes[1:]}})
    threading.Thread(target=send_later, daemon=True).start()
    got, ns = p.wait(10)
    took = time.time() - t0
    assert [n.ref for n in ns] == ["home#1"] and 0.9 < took < 1.8, "이벤트로 바로 깨어난다(2초 폴링이 아님): %.2f" % took
