"""판 카드 싣기(셸 C10, view-live-cap) — 보이는 카드 판정 HD.liveCap.near(Model)를 node 로: 화면 칸 + 여유 80px 안에 걸치면 보임, 너비 0 = 안 보임.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/live-cap.js', 'utf8'), {filename: 'live-cap.js'});
const L = globalThis.HD.liveCap, pr = {left: 0, top: 0, right: 1000, bottom: 800};
const box = (l, t, w, h) => ({left: l, top: t, right: l + w, bottom: t + h, width: w});
console.log(JSON.stringify({
  inside: L.near(box(10, 10, 100, 100), pr), margin: L.near(box(1070, 10, 100, 100), pr), out: L.near(box(1080, 10, 100, 100), pr),
  above: L.near(box(10, -179, 100, 100), pr), aboveOut: L.near(box(10, -180, 100, 100), pr), zero: L.near(box(10, 10, 0, 100), pr),
  custom: L.near(box(1010, 10, 100, 100), pr, 5), M: L.MARGIN}));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-lcnear-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_near_uses_80px_margin(js):
    assert js["inside"] and js["margin"] and not js["out"]
    assert js["above"] and not js["aboveOut"]
    assert not js["zero"] and not js["custom"] and js["M"] == 80
