"""R34 허브 옛 코드 칩 — 서버 판단(code_stamp.hub_stale, 순수)과 칩 글(modules/hub-stale.js, node). I/O 없음.
브라우저 행복 경로(허브 안 세션 · 칩이 뜨고 사라짐 · 다시 켜기)는 test_canvas_one_server.py."""
import json, shutil, subprocess, sys
from pathlib import Path

import pytest

CANVAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CANVAS))
import code_stamp as CS  # noqa: E402

NOW, OLD = "g:aaaaaaaaaaaaaaaa", "g:3f9c2ab0bbbbbbbb"
SINCE = "2026-10-27T09:12:05+09:00"
NODE = shutil.which("node")


def test_hub_stale_reports_the_old_hub_fingerprint_and_start_time():
    """옛 지문으로 뜬 허브 = {짧은 sha, 켠 시각} · 같으면 None · 지금 도장을 모르면(git 실패) None(헛 알림 없음)."""
    assert CS.hub_stale(OLD, NOW, SINCE) == {"sha": "3f9c2ab", "since": SINCE}
    assert CS.hub_stale(NOW, NOW, SINCE) is None
    assert CS.hub_stale(OLD, None, SINCE) is None and CS.hub_stale(OLD, "", SINCE) is None
    assert CS.hub_stale(None, NOW, SINCE) == {"sha": "?", "since": SINCE}, "도장 칸이 없던 옛 허브도 옛것"
    assert CS.hub_stale("w:0123456789abcdef", NOW)["sha"] == "0123456", "설치본(내용 해시) 도장도 같은 모양"


JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[process.argv.length - 1] + '/hub-stale.js', 'utf8'), {filename: 'hub-stale.js'});
const H = globalThis.HD.hubStale, out = {};
out.none = H.read(undefined);
out.fresh = H.read(null);
out.stale = H.read({sha: '3f9c2ab', since: '2026-10-27T09:12:05+09:00'});
out.noSince = H.read({sha: '?'});
out.bad = [H.read('x'), H.read([]), H.read({sha: 3}), H.read({sha: '<b>'}), H.read({sha: 'abc', since: 5})];
out.when = [H.when('2026-10-27T09:12:05+09:00'), H.when('어제'), H.when(null)];
out.tok = [H.tokenOf('<head><script>window.__hdHub=true;window.__hdToken="ab-C_1";</script>'), H.tokenOf('<p>no</p>'), H.tokenOf(null),
           H.tokenOf('window.__hdToken="";')];
out.cmd = H.CMD;
console.log(JSON.stringify(out));
"""


def test_chip_model_reads_server_verdict():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    r = subprocess.run([NODE, "-e", JS, "--", str(CANVAS / "modules")], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["none"] is None, "칸이 없는 답(도우미) = 모름 — 칩을 바꾸지 않는다"
    assert out["fresh"] == {"stale": False}
    s = out["stale"]
    assert s["stale"] and s["label"] == "허브 옛 코드 · 다시 켜기" and "3f9c2ab" in s["title"] and "10-27 09:12 켬" in s["title"]
    assert "hd home --restart" in s["title"]
    assert out["noSince"]["stale"] and "켬" not in out["noSince"]["title"]
    assert all(b["stale"] is False and b["bad"] for b in out["bad"]), "깨진 모양 = 칩 없음 + 까닭(보는 쪽이 [hd] 경고)"
    assert out["when"] == ["10-27 09:12", "", ""]
    assert out["tok"] == ["ab-C_1", None, None, None]
    assert out["cmd"] == "hd home --restart"
