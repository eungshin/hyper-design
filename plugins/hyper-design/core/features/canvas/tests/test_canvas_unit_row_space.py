"""줄 사이 띄우기(t51-8) — 아래 줄 제목은 위 줄 카드의 펼친 설명(.cbody)을 덮지 않는다(Figma 섹션: 제목은 위 섹션 내용과 겹치지 않는다).

HD.rows.space(rows, {base, clear}) (modules/rows.js, 순수): rows = 줄마다 {bottom, over}(같은 판 좌표 — bottom = 그 줄 카드가 차지한 아래 끝,
over = 그 줄 카드 아래 펼친 설명의 가장 아래 끝, 없으면 bottom 이하) → 줄마다 덧붙일 아래 여백 px(정수, 0 이상).
기본 줄 사이(base, 다음 줄 .flow padding-top)로 모자랄 때만: over + clear 가 bottom + base 를 넘는 만큼. 깨진 값은 0."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/rows.js', 'utf8'), {filename: 'rows.js'});
const R = globalThis.HD.rows, out = {}, o = {base: 90, clear: 40};
out.fits = R.space([{bottom: 1000, over: 1050}], o);
out.exact = R.space([{bottom: 1000, over: 1050.0}], {base: 90, clear: 40});
out.over = R.space([{bottom: 1000, over: 1200}], o);
out.frac = R.space([{bottom: 1000, over: 1100.2}], o);
out.none = R.space([{bottom: 1000, over: 0}], o);
out.rows = R.space([{bottom: 900, over: 1300}, {bottom: 2000, over: 2010}, {bottom: 3000, over: 3100}], o);
out.bad = R.space([null, {bottom: 'x', over: 5}, {bottom: 1, over: NaN}, {}], o);
out.noRows = R.space(null, o);
out.noOpt = R.space([{bottom: 0, over: 500}]);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-rowspace-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_short_description_keeps_the_base_gap(js):
    assert js["fits"] == [0], "설명 끝 + 띄움(40) ≤ 줄 아래 + 기본 줄 사이(90) = 그대로"
    assert js["exact"] == [0]
    assert js["none"] == [0], "펼친 설명이 없는 줄"


def test_long_description_pushes_the_next_row_down_by_the_overhang(js):
    assert js["over"] == [150], "1200 + 40 - (1000 + 90)"
    assert js["frac"] == [51], "소수는 올린다 — 반 픽셀이라도 겹치지 않게"


def test_each_row_counts_only_its_own_descriptions(js):
    assert js["rows"] == [350, 0, 50]


def test_bad_input_is_no_extra_space(js):
    assert js["bad"] == [0, 0, 0, 0]
    assert js["noRows"] == []
    assert js["noOpt"] == [0], "base·clear 가 없으면 띄우지 않는다(깨진 호출)"
