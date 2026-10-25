"""창 없이 뜬 허브·도우미(pythonw)의 자식 프로세스는 콘솔 창을 띄우지 않는다 — hd_client 의 빌드·pid 보기·끄기, 세션의 다시 빌드·paseo. 브라우저 없음."""
import subprocess, sys
from pathlib import Path

HD = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HD), str(HD.parent / "canvas")]
import hd_client  # noqa: E402
import session  # noqa: E402

FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _fake(seen):
    def run(args, **kw):
        seen.append(kw.get("creationflags", 0))
        return subprocess.CompletedProcess(args, 0, "" if kw.get("text") or kw.get("encoding") else b"", "")
    return run


def test_hd_client_children_open_no_console_window(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(hd_client.subprocess, "run", _fake(seen))
    hd_client.build(tmp_path)
    if sys.platform == "win32":
        hd_client._image(4242)
    assert seen and all(f == FLAG for f in seen), seen


def test_session_children_open_no_console_window(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(session.subprocess, "run", _fake(seen))
    session.run_build(tmp_path)
    session.forward(tmp_path, "메모", agent="a1", paseo="paseo.exe")
    session.list_agents(paseo="paseo.exe")
    assert len(seen) == 3 and all(f == FLAG for f in seen), seen
