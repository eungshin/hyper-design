"""메모 창 자동 자리(R27 F09) Model — modules/pop-side.js 순수 함수 단위 테스트(node). 브라우저 없음.

beside: 대상 옆 오른쪽 → 왼쪽 → 아래 → 위 중 앞 area(판 자리)에 들어가는 첫 자리, 없으면 다음 area(화면 전체),
어디에도 없으면 가장 넓은 쪽(안으로 자름). 옆은 대상 위쪽 끝, 아래·위는 왼쪽 끝에 맞춘다. 깨진 값 = 첫 area 왼쪽 위(side none).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/pop-side.js', 'utf8'), {filename: 'pop-side.js'});
const S = globalThis.HD.popSide, out = {}, size = {w: 320, h: 160};
const board = {x: 340, y: 40, w: 800, h: 950}, view = {x: 8, y: 8, w: 1424, h: 984};
out.gap = S.GAP;
out.right = S.beside({x: 400, y: 300, w: 200, h: 40}, size, [board, view]);
out.left = S.beside({x: 900, y: 300, w: 200, h: 40}, size, [board, view]);
out.below = S.beside({x: 360, y: 100, w: 760, h: 300}, size, [board, view]);
out.above = S.beside({x: 360, y: 400, w: 760, h: 560}, size, [board, view]);
out.view = S.beside({x: 340, y: 60, w: 700, h: 920}, size, [board, view]);
out.none = S.beside({x: 0, y: 0, w: 1440, h: 1000}, size, [board, view]);
out.clampY = S.beside({x: 400, y: 950, w: 100, h: 20}, size, [board, view]);
out.bad = [S.beside(null, size, [board]), S.beside({x: 1, y: 2, w: 'x', h: 4}, size, [board]), S.beside({x: 1, y: 2, w: 3, h: 4}, size, [])];
// F6(10-31): 배지 아래 오른쪽 끝 맞춤 창(메모 묶음) — 도구 막대 같은 피할 상자를 덮지 않게 옆으로
const tools = {left: 372, top: 368, right: 420, bottom: 664}, scr = {x: 8, y: 8, w: 1424, h: 984}, sz = {w: 320, h: 230};
out.under = S.under({left: 630, right: 650, top: 150, bottom: 170}, sz, scr, [tools]);
out.underClear = S.under({left: 930, right: 950, top: 150, bottom: 170}, sz, scr, [tools]);
out.underFlip = S.under({left: 930, right: 950, top: 900, bottom: 920}, sz, scr, []);
out.underLeft = S.under({left: 1400, right: 1420, top: 300, bottom: 320}, sz, scr, [{left: 1200, top: 300, right: 1440, bottom: 700}]);
out.underBad = [S.under(null, sz, scr, []), S.under({left: 1, right: 2, top: 3, bottom: 'x'}, sz, scr, [null, {left: 'a'}])];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-pop-side-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_right_of_target_first_top_aligned(out):
    assert out["right"] == {"x": 400 + 200 + out["gap"], "y": 300, "side": "right"}


def test_left_when_right_does_not_fit_in_board(out):
    assert out["left"] == {"x": 900 - out["gap"] - 320, "y": 300, "side": "left"}


def test_below_then_above_for_wide_targets(out):
    assert out["below"] == {"x": 360, "y": 100 + 300 + out["gap"], "side": "below"}
    assert out["above"] == {"x": 360, "y": 400 - out["gap"] - 160, "side": "above"}


def test_board_full_falls_to_screen_beside(out):
    """카드가 판 자리를 다 채우면 화면(도크 위)에서 옆자리 — 대상을 덮지 않는다."""
    assert out["view"] == {"x": 340 + 700 + out["gap"], "y": 60, "side": "right"}


def test_no_room_anywhere_takes_widest_side_clamped(out):
    n = out["none"]
    assert 8 <= n["x"] <= 1432 - 320 and 8 <= n["y"] <= 992 - 160 and n["side"] in ("right", "left", "below", "above")


def test_side_spot_is_clamped_inside_area(out):
    assert out["clampY"]["side"] == "right" and out["clampY"]["y"] == 40 + 950 - 160


def test_broken_input_is_first_area_corner(out):
    assert out["bad"][0] == {"x": 340, "y": 40, "side": "none"} and out["bad"][1] == out["bad"][0]
    assert out["bad"][2] == {"x": 8, "y": 8, "side": "none"}


def test_under_badge_moves_off_the_toolbar(out):
    """F6(10-31): 메모 묶음 창(배지 아래 오른쪽 끝 맞춤)이 왼쪽 도구 막대를 덮으면 막대 오른쪽으로 비킨다."""
    assert out["under"] == {"x": 420 + 6, "y": 170 + 6}, ("막대와 겹치면 막대 오른쪽 + 틈", out["under"])
    assert out["underClear"] == {"x": 950 - 320, "y": 176}, "겹치지 않으면 예전 그대로(배지 아래 오른쪽 끝)"
    assert out["underFlip"] == {"x": 630, "y": 900 - 6 - 230}, "아래 자리가 모자라면 배지 위"
    assert out["underLeft"] == {"x": 1200 - 6 - 320, "y": 326}, "오른쪽으로 못 가면 피할 상자 왼쪽"
    assert out["underBad"] == [{"x": 8, "y": 8}, {"x": 8, "y": 8}], "깨진 값 = 화면 왼쪽 위(던지지 않음), 깨진 피할 상자는 무시"
