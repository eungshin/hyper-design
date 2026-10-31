"""카드 크기 범위(R57 A) — 캔버스 modules/artboard.js 의 check 와 hd add --size(features/hd/hd_place.py parse_size)가
같은 표에서 같은 답을 내는지(한 쌍의 상수 · 언어마다 하나). 웹·광고(320×50, 728×90)·상세페이지(860×40000)·AI 이미지 = 받고,
정말 예외인 크기(16 미만 · 60000 초과)만 거절. 오류 글은 상수로 만든다."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
HD = HERE.parents[1] / "hd"
sys.path.insert(0, str(HD))
import hd_place as L  # noqa: E402

NODE = shutil.which("node")
CASES = [  # (w, h, 받나)
    (320, 50, True), (728, 90, True), (300, 250, True), (860, 40000, True), (1440, 12190, True),
    (16, 16, True), (60000, 60000, True), (16, 60000, True), (393, 852, True),
    (15, 500, False), (500, 15, False), (60001, 500, False), (500, 60001, False), (0, 0, False),
]
JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/artboard.js', 'utf8'), {filename: 'artboard.js'});
const A = globalThis.HD.artboard, cases = JSON.parse(process.argv[3]);
console.log(JSON.stringify({MIN: A.MIN, MAX: A.MAX, check: cases.map(c => A.check(c[0], c[1])),
  nudge: [A.nudge(A.MIN, 'ArrowDown', true), A.nudge(A.MAX, 'ArrowUp', true)]}));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-size-range-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD), json.dumps(CASES)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_range_is_16_to_60000_in_both_languages(js):
    assert (js["MIN"], js["MAX"]) == (16, 60000)
    assert (L.SIZE_MIN, L.SIZE_MAX) == (js["MIN"], js["MAX"]), "artboard.js 와 hd_place.py 의 상수가 같아야 한다"
    assert js["nudge"] == [16, 60000], "화살표도 범위 끝에서 멈춘다"


def test_same_answer_for_every_case_and_error_built_from_constants(js):
    for (w, h, ok), c in zip(CASES, js["check"]):
        assert c["ok"] is ok, ("canvas", w, h, c)
        if ok:
            assert (c["w"], c["h"]) == (w, h)
            assert L.parse_size("%dx%d" % (w, h), {}) == {"w": w, "h": h}, ("hd add", w, h)
        else:
            assert "16~60000" in c["error"], c
            with pytest.raises(L.PlaceError) as e:
                L.parse_size("%dx%d" % (w, h), {})
            assert "16~60000" in str(e.value), ("hd add", w, h, str(e.value))
