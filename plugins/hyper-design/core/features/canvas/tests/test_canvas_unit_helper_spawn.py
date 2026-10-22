"""도우미가 띄우는 자식 프로세스(다시 빌드 · paseo send)는 Windows 에서 콘솔 창을 만들지 않는다 — 창 없이 뜬 도우미에서 편집할 때마다 터미널이 깜빡이던 문제."""
import subprocess, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import helper  # noqa: E402


@pytest.mark.skipif(sys.platform != "win32", reason="Windows 전용 플래그")
def test_child_processes_open_no_console_window(monkeypatch, tmp_path):
    seen = []

    def fake_run(args, **kw):
        seen.append(kw.get("creationflags", 0))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(helper.subprocess, "run", fake_run)
    helper._build(tmp_path)
    helper.forward(tmp_path, "메모", agent="a1", paseo="paseo.exe")
    assert len(seen) == 2 and all(f & subprocess.CREATE_NO_WINDOW for f in seen), seen
