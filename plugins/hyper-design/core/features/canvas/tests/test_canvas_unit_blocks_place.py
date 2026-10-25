"""요소 막대 크기(polish-1) — blocks.fit·barLimit 이 막대가 요소 칸보다 넓으면 뒤 단추를 "⋯" 로 넘긴다. 상자 고정 입력(node), DOM 없음. 막대 자리는 test_canvas_unit_bar_place.py(bar-place.js)."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/blocks.js', 'utf8'), {filename: 'blocks.js'});
const B = globalThis.HD.blocks, out = {};
const R = (x, y, w, h) => ({x: x, y: y, w: w, h: h});
const V = R(0, 0, 1000, 800);
out.fit = [B.fit([50, 50, 50, 50], 300, 30), B.fit([50, 50, 50, 50], 150, 30), B.fit([50, 50, 50, 50], 10, 30), B.fit([], 100, 30), B.fit([50, 50, 50, 50], 200, 30)];
out.limit = [B.barLimit(R(0, 0, 100, 20), V), B.barLimit(R(0, 0, 600, 20), V), B.barLimit(R(0, 0, 600, 20), R(0, 0, 200, 800))];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-blocks-place-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_fit_moves_tail_buttons_to_the_more_menu(js):
    assert js["fit"] == [4, 2, 1, 0, 4], ("다 들어가면 전부 · 아니면 ⋯ 자리를 남기고 앞에서부터 · 최소 1", js["fit"])


def test_bar_limit_is_the_element_width_with_a_floor_inside_the_view(js):
    assert js["limit"] == [220, 600, 200 - 16], js["limit"]
