"""판 이름표 배율(R27 F01·F08) — label-scale.js(Model): --lz = 1/판 배율 · 확대 중 덜 쓰기 · 보이는 선 태그 겹침을 아래로 밀기. node, DOM 없음."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/label-scale.js', 'utf8'), {filename: 'label-scale.js'});
const L = globalThis.HD.labelScale, out = {};
out.inv = [L.inv(0.12), L.inv('0.4000'), L.inv(1), L.inv(2), L.inv(0), L.inv(-1), L.inv('x'), L.inv(null), L.inv(Infinity)];
out.fmt = L.fmt(1 / 0.12);
out.put = [L.put('', 2, false), L.put(null, 2, true), L.put('2.0000', 2.05, false), L.put('2.0000', 2.1, false),
           L.put('2.0000', 2.05, true), L.put('2.0000', 2.00001, true), L.put('2.0000', 0, true), L.put('2.0000', NaN, false)];
const R = (l, t, w, h) => ({l: l, t: t, r: l + w, b: t + h});
out.apart = L.stack([R(0, 0, 50, 16), R(100, 0, 50, 16)], 3);                  // 가로로 떨어짐 = 그대로
out.pair = L.stack([R(10, 4, 60, 16), R(0, 0, 80, 16)], 3);                     // 위 것(두 번째)이 먼저 자리, 첫째가 그 아래로
out.three = L.stack([R(0, 0, 60, 16), R(20, 2, 60, 16), R(40, 5, 60, 16)], 2);   // 줄줄이
out.bad = L.stack([null, R(0, 0, 10, 10), {l: 'a'}, R(0, 0, 10, 10)], 2);
out.none = L.stack('x');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-lz-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_inverse_of_board_zoom(out):
    inv = out["inv"]
    assert abs(inv[0] - 1 / 0.12) < 1e-9 and abs(inv[1] - 2.5) < 1e-9 and inv[2] == 1 and inv[3] == 0.5, "--lz = 1/배율 → 이름표가 화면에서 같은 크기"
    assert inv[4:] == [None] * 5, "0·음수·글·없음·무한 = null(View 가 [hd] 경고 후 1)"
    assert out["fmt"] == "8.3333"


def test_write_rarely_while_zooming_exactly_when_still(out):
    assert out["put"] == [True, True, False, True, True, False, False, False], "처음은 늘 · 확대 중엔 3% 넘을 때만 · 멈추면 다를 때 · 깨진 값은 쓰지 않음"


def test_visible_link_tags_never_overlap(out):
    assert out["apart"] == [0, 0]
    assert out["pair"] == [15, 0], "위 것이 자리를 잡고 겹친 것은 그 아래 + 3px"
    assert out["three"] == [0, 16, 31], "앞 것들 아래로 줄줄이(2px 틈)"
    assert out["bad"] == [0, 0, 0, 12], "깨진 상자는 움직이지 않고, 성한 것끼리만 비킨다"
    assert out["none"] == []
