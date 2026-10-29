"""메모 창 자리(#223) Model — modules/pop-place.js 순수 함수 단위 테스트(node). 브라우저 없음.

parse: 없음 = 자동 자리(깨짐 아님), 깨진 글·빠진 칸 = 자동 자리 + bad(View 가 [hd] 경고). clamp: 가장 작은 크기 260×160,
창(여백 8) 안으로 크기·자리를 맞춤, 창이 가장 작은 크기보다 작으면 가장 작은 크기가 이긴다. 4번째 인자 min = 다른 떠 있는 창(대화 창 R53)의 가장 작은 크기(없으면 MIN). serialize ↔ parse 왕복.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

POP_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/pop-place.js', 'utf8'), {filename: 'pop-place.js'});
const P = globalThis.HD.popPlace, out = {};
out.min = P.MIN;
out.none = [P.parse(null), P.parse('')];
out.bad = ['{oops', '[]', '"x"', JSON.stringify({x: 1, y: 2, w: 'wide', h: 3}), JSON.stringify({x: 1, y: 2, w: 300}), 'null'].map(P.parse);
out.good = P.parse(JSON.stringify({x: 40, y: 50, w: 320, h: 240}));
out.inside = P.clamp({x: 40, y: 50, w: 320, h: 240}, 1280, 800);
out.small = P.clamp({x: 40, y: 50, w: 100, h: 20}, 1280, 800);
out.offRight = P.clamp({x: 1200, y: 780, w: 320, h: 240}, 1280, 800);
out.offLeft = P.clamp({x: -500, y: -30, w: 320, h: 240}, 1280, 800);
out.tooBig = P.clamp({x: 0, y: 0, w: 5000, h: 5000}, 1280, 800);
out.tinyView = P.clamp({x: 100, y: 100, w: 400, h: 400}, 200, 120);
out.round = P.clamp({x: 10.6, y: 20.4, w: 300.5, h: 200.2}, 1280, 800);
out.minArg = [P.clamp({x: 40, y: 50, w: 100, h: 20}, 1280, 800, {w: 320, h: 240}), P.clamp({x: 40, y: 50, w: 100, h: 20}, 1280, 800, null)];
out.trip = P.parse(P.serialize({x: 10.4, y: 20.6, w: 300, h: 200})).place;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-pop-js-"))
    try:
        (tmp / "pop.js").write_text(POP_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "pop.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_min_size(out):
    assert out["min"] == {"w": 260, "h": 160}


def test_missing_value_is_auto_not_broken(out):
    assert out["none"] == [{"place": None, "bad": False}] * 2


def test_broken_value_falls_back_and_is_flagged(out):
    assert out["bad"] == [{"place": None, "bad": True}] * 6, "깨진 글·모양·빠진 칸 = 자동 자리 + 경고 대상"


def test_good_value_reads_back(out):
    assert out["good"] == {"place": {"x": 40, "y": 50, "w": 320, "h": 240}, "bad": False}


def test_clamp_keeps_inside_and_min(out):
    assert out["inside"] == {"x": 40, "y": 50, "w": 320, "h": 240}, "창 안이면 그대로"
    assert out["small"] == {"x": 40, "y": 50, "w": 260, "h": 160}, "가장 작은 크기"
    assert out["offRight"] == {"x": 1280 - 8 - 320, "y": 800 - 8 - 240, "w": 320, "h": 240}, "오른쪽·아래로 나가면 안으로"
    assert out["offLeft"] == {"x": 8, "y": 8, "w": 320, "h": 240}, "왼쪽·위로 나가면 안으로"
    assert out["tooBig"] == {"x": 8, "y": 8, "w": 1280 - 16, "h": 800 - 16}, "창보다 크면 창 크기로"
    assert out["tinyView"] == {"x": 8, "y": 8, "w": 260, "h": 160}, "창이 아주 작으면 가장 작은 크기가 이긴다"


def test_integers_and_round_trip(out):
    assert out["round"] == {"x": 11, "y": 20, "w": 301, "h": 200}
    assert out["trip"] == {"x": 10, "y": 21, "w": 300, "h": 200}


def test_clamp_takes_other_min(out):
    """R53: 대화 창도 같은 자리 규칙(R58 — 떠 있는 창 자리는 함수 하나)을 쓰고 가장 작은 크기만 다르다."""
    assert out["minArg"][0] == {"x": 40, "y": 50, "w": 320, "h": 240}, "min 을 주면 그 크기가 가장 작은 크기"
    assert out["minArg"][1] == {"x": 40, "y": 50, "w": 260, "h": 160}, "min 이 없으면 메모 창 그대로(260×160)"
