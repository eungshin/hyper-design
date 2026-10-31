"""눈앞 내용 제자리(U2 F1a) Model — modules/camera-anchor.js 순수 함수 단위 테스트(node). 브라우저 없음.

내용 높이가 바뀌면 카메라를 다시 맞추지 않고, 보이던 맨 위 덩어리(기준)의 화면 위치를 그대로 지키도록 ty 만 보정한다.
기준 = 판 칸에 가장 많이 보이는 덩어리(같으면 위의 것) · 기준이 사라졌으면 다음으로 많이 보이던 것 · 보이는 게 없거나 안 움직였으면 ty 그대로(같은 값).
"""
import json, shutil, subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/camera-anchor.js', 'utf8'), {filename: 'camera-anchor.js'});
const A = globalThis.HD.cameraAnchor, out = {};
// 판 높이 1000, 배율 0.5 — 소개 글(0..1300) · DS 카드(1400..1920) · 줄 1(2000..3200) · 줄 2(3200..4400)
const prev = [{id: 'intro', y: 0, h: 1300}, {id: 'ds', y: 1400, h: 520}, {id: 'r1', y: 2000, h: 1200}, {id: 'r2', y: 3200, h: 1200}];
const shift = (ids, dy) => prev.map(p => ids.includes(p.id) ? Object.assign({}, p, {y: p.y + dy}) : p);
const v = (ty) => ({h: 1000, z: 0.5, ty: ty});
// 첫 화면: 줄 1 위가 판 위 20px(ty = 20 - 2000*0.5 = -980)
out.pickHome = A.pick(prev, v(-980));
out.pickMost = A.pick(prev, v(-1200));              // 줄 1 은 400px · 줄 2 는 600px 보임 — 많이 보이는 것
out.pickTie = A.pick(prev, v(-1100));               // 둘 다 500px — 위의 것
out.pickSliver = A.pick(prev, v(-940));             // DS 카드 끝 20px 만 걸치고 줄 1 이 판을 채움 — 줄 1(점검 10-31: DS 카드가 4px 줄자 첫 줄이 3px 밀렸다)
out.pickNone = A.pick(prev, v(-5000));
// 위쪽 소개 글이 158 줄어 아래가 모두 올라감 → 줄 1 화면 위치 그대로 = ty + 79
out.above = A.keep(prev, shift(['ds', 'r1', 'r2'], -158), v(-980));
// 줄 1 아래 여백만 바뀜(메모 지우기로 줄 사이가 줄어듦) → ty 그대로
out.below = A.keep(prev, shift(['r2'], -52), v(-980));
// 사용자가 줄 2 를 보고 있을 때 줄 1 이 커짐 → 줄 2 제자리
out.userView = A.keep(prev, shift(['r2'], 100), v(-1700));
// 기준(줄 1, 둘 다 500px 이라 위의 것)이 사라짐 → 다음으로 보이던 줄 2 로
out.gone = A.keep(prev, prev.filter(p => p.id !== 'r1').map(p => p.id === 'r2' ? Object.assign({}, p, {y: 2000}) : p), v(-1100));
out.sliver = A.keep(prev, shift(['r1', 'r2'], -4).map(p => p.id === 'ds' ? Object.assign({}, p, {h: 516}) : p), v(-940));
// 보이는 게 없음 · 기준 이전 없음 · 같은 배치 → 그대로
out.none = A.keep(prev, shift(['r1', 'r2'], -158), v(-5000));
out.noPrev = A.keep(null, prev, v(-980));
out.same = A.keep(prev, prev.map(p => Object.assign({}, p)), v(-980.123));
out.tiny = A.keep(prev, shift(['r1', 'r2'], 0.001), v(-980));
// 깨진 값 — 숫자가 아닌 y 는 건너뛴다(던지지 않음)
out.broken = A.keep([{id: 'r1', y: 'x', h: 10}].concat(prev), shift(['r1', 'r2'], -10), v(-980));
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def res():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    p = subprocess.run([NODE, "-e", JS, str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_anchor_is_the_most_visible_block(res):
    assert res["pickHome"] == "r1"
    assert res["pickMost"] == "r2" and res["pickTie"] == "r1", "많이 보이는 것 · 같으면 위의 것"
    assert res["pickSliver"] == "r1", "가장자리에 조금 걸친 덩어리는 기준이 아니다"
    assert res["pickNone"] is None


def test_change_above_the_anchor_shifts_camera_by_the_same_screen_amount(res):
    assert res["above"] == pytest.approx(-980 + 79)


def test_change_below_the_anchor_does_not_move_the_camera(res):
    assert res["below"] == -980


def test_users_view_stays_when_a_row_above_grows(res):
    assert res["userView"] == pytest.approx(-1700 - 50)


def test_removed_anchor_falls_back_to_the_next_visible_block(res):
    assert res["gone"] == pytest.approx(-1100 + 600)


def test_sliver_above_shrinking_does_not_push_the_row_in_view(res):
    assert res["sliver"] == pytest.approx(-940 + 2)


def test_nothing_visible_or_no_change_keeps_ty_exactly(res):
    assert res["none"] == -5000 and res["noPrev"] == -980
    assert res["same"] == -980.123 and res["tiny"] == -980, "움직임이 없으면 같은 값(카메라를 다시 쓰지 않게)"


def test_broken_entries_are_skipped(res):
    assert res["broken"] == pytest.approx(-980 + 5)
