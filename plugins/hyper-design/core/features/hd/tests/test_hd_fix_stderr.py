"""hdfix.start_helper 의 자식 stderr(task 47-2 단계 2e) — 읽지 않는 PIPE 면 [hd] 줄이 버퍼(Windows 약 4 KB)를 채운 뒤 도우미가 다음 줄에서 멈춘다.
파일로 받으면 줄이 아무리 많아도 요청이 답한다. 브라우저 없음."""
import json, sys, urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

pytestmark = pytest.mark.slow


def _post(url, token, path, body):
    base = url.split("/index.html")[0]
    r = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"), method="POST",
                               headers={"X-HD-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=5) as res:
        return res.status


def test_helper_stderr_does_not_block_requests(tmp_path):
    out, home = hdfix.make_out(tmp_path), tmp_path / "home"
    p, url = hdfix.start_helper(out, home)
    token = url.split("hd=")[1]
    try:
        for i in range(400):                         # attach 한 번 = [hd] 한 줄(약 40 B) — 400번이면 16 KB, PIPE 버퍼를 넘는다
            assert _post(url, token, "/api/attach", {"agent": "ag-%d" % i if i % 2 else None}) == 200
    finally:
        hdfix.stop_helper(p)
    assert "보내기" in hdfix.stderr_of(p), "stderr 는 읽을 수 있는 파일에 남는다"
