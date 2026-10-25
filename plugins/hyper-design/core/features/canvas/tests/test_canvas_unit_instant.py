"""49c 바로 반영 편집 — 순수 규칙(node, 브라우저 없음).

HD.reorder(reorder.js): 형제 상자 위 포인터 → 끼울 자리(세로 목록 = y · 가로 줄·격자 = x) · 끼울 선 · 위/아래 옮기기 목록.
HD.optimistic(optimistic.js): 먼저 보인 편집 → 도우미 답으로 남김/되돌림 · 중간 쓰기의 다시 싣기 건너뛰기(hold) · 알림 글.
HD.swap(swap.js) 덧: 같은 내용 = 'silent'(알약·겹치기 없이) — 그 카드에서 글자를 고치는 중이면 아님.
HD.blocks(blocks.js) 덧: 막대에서 ↑·↓ 를 빼고(단축키·메뉴는 그대로) 끌기 손잡이 켜짐.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js', 'blocks.js', 'swap.js', 'reorder.js', 'optimistic.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const R = HD.reorder, O = HD.optimistic, S = HD.swap, B = HD.blocks, out = {};
// 세로 목록: 세 칸(높이 40, 사이 10)
const col = [{x: 0, y: 0, w: 200, h: 40}, {x: 0, y: 50, w: 200, h: 40}, {x: 0, y: 100, w: 200, h: 40}];
out.colSlots = [[10, 5], [10, 30], [10, 60], [10, 85], [10, 125], [10, 300], [10, -50], [500, 115]].map(p => R.slot({x: p[0], y: p[1]}, col));
// 가로 줄: 세 칸(너비 60, 같은 높이)
const row = [{x: 0, y: 0, w: 60, h: 30}, {x: 70, y: 0, w: 60, h: 30}, {x: 140, y: 0, w: 60, h: 30}];
out.rowSlots = [[10, 15], [50, 15], [80, 15], [190, 15], [400, 15]].map(p => R.slot({x: p[0], y: p[1]}, row));
// 격자 2열: 0 1 / 2 3
const grid = [{x: 0, y: 0, w: 90, h: 40}, {x: 100, y: 0, w: 90, h: 40}, {x: 0, y: 50, w: 90, h: 40}, {x: 100, y: 50, w: 90, h: 40}];
out.gridSlots = [[120, 70], [180, 70], [20, 20], [170, 10]].map(p => R.slot({x: p[0], y: p[1]}, grid));
out.slotBad = [R.slot({x: 1, y: 1}, []), R.slot(null, col), R.slot({x: NaN, y: 0}, col), R.slot({x: 0, y: 0}, [{x: 0, y: 0, w: 0, h: 0}])];
out.hidden = R.slot({x: 10, y: 5}, [{x: 0, y: 0, w: 0, h: 0}, {x: 0, y: 50, w: 200, h: 40}]);
out.colLines = [0, 1, 3].map(s => R.line(s, col));
out.rowLine = R.line(1, row);
out.gridLines = [R.line(2, grid), R.line(4, grid), R.line(1, grid)];
out.lineBad = [R.line(4, col), R.line(-1, col), R.line(0, [])];
out.moves = [R.moves(0, 3), R.moves(2, 0), R.moves(1, 1), R.moves(1, 2), R.moves(0, 1), R.moves(3, 1), R.moves(-1, 2)];
out.targets = [R.target(0, 3), R.target(2, 0), R.target(1, 2)];
// 낙관 상태
let s = O.initial();
const s0 = s;
s = O.reduce(s, {type: 'start', tag: 'a', screen: 'job', steps: 3});
out.startPhase = O.phase(s, 'a');
out.holdStart = O.hold(s, 'job');
s = O.reduce(s, {type: 'step', tag: 'a'}); s = O.reduce(s, {type: 'step', tag: 'a'});
out.holdLast = O.hold(s, 'job');
out.holdOther = O.hold(s, 'lang');
let t = O.reduce(s, {type: 'start', tag: 'b', screen: 'job', steps: 1});
out.holdTwo = O.hold(t, 'job');
const kept = O.reduce(s, {type: 'keep', tag: 'a'});
out.kept = O.phase(kept, 'a');
out.lateRevert = O.phase(O.reduce(kept, {type: 'revert', tag: 'a', why: 'x'}), 'a');
const rev = O.reduce(s, {type: 'revert', tag: 'a', why: '경로 없음'});
out.reverted = [O.phase(rev, 'a'), rev.ops.a.why, O.hold(rev, 'job')];
out.ended = O.phase(O.reduce(kept, {type: 'end', tag: 'a'}), 'a');
out.same = [O.reduce(s0, {type: 'step', tag: 'zz'}) === s0, O.reduce(s0, {type: 'start', tag: 'q', screen: ''}) === s0, O.reduce(s0, null) === s0,
            O.reduce(s, {type: 'start', tag: 'a', screen: 'job', steps: 9}) === s];
out.overStep = O.reduce(O.reduce(O.reduce(O.initial(), {type: 'start', tag: 'c', screen: 'x', steps: 1}), {type: 'step', tag: 'c'}), {type: 'step', tag: 'c'}).ops.c.done;
out.outcome = [
  O.outcome({applied: ['n1'], failed: []}, ['n1']),
  O.outcome({applied: [], failed: [{id: 'n1', reason: '요소를 찾지 못했어요: h1'}]}, ['n1']),
  O.outcome({applied: ['n1'], failed: [{id: 'n2', reason: '겹침'}]}, ['n1', 'n2']),
  O.outcome({applied: []}, ['n1']),
  O.outcome(null, ['n1']),
  O.outcome({applied: ['n1']}, []),
  O.outcome({error: 'too large'}, ['n1'])
];
out.failText = [O.failText('요소 옮기기', '맨 아래', 1, 3), O.failText('글자 고치기', '', 0, 1)];
// 같은 내용 = silent
const ready = {phase: 'ready'};
out.next = [
  S.next(ready, {touching: true, reduced: false, same: true}),
  S.next(ready, {touching: false, reduced: false, same: true, typing: true}),
  S.next(ready, {touching: true, reduced: false, same: true, typing: true}),
  S.next(ready, {touching: false, reduced: false, same: false}),
  S.next({phase: 'loading'}, {same: true}),
  S.next(ready, {touching: false, reduced: true, same: 'yes'})
];
out.sameDiff = [S.same({changed: [], added: [], removed: [], many: false}), S.same({changed: [3], added: [], removed: []}), S.same({changed: [], added: [], removed: [2]}),
                S.same({changed: [], added: [], removed: [], many: true}), S.same(null), S.same({})];
// 막대: ↑·↓ 는 막대에서 빼고 단축키는 그대로 · 손잡이
const h = {path: 'ul > li:nth-of-type(2)', prev: true, next: true, root: false, up: true, textOk: true, tag: 'li'};
out.shown = B.shown(B.bar(h, {})).map(x => x.act);
out.all = B.bar(h, {}).map(x => x.act);
out.keys = [B.keyAct({key: 'ArrowUp', alt: true}), B.keyAct({key: 'ArrowDown', alt: true})];
out.grip = [B.grip(h, {}).on, B.grip(h, {app: true}).on, B.grip(Object.assign({}, h, {root: true}), {}).on, B.grip(Object.assign({}, h, {prev: false, next: false}), {}).on,
            B.grip(Object.assign({}, h, {prev: false}), {}).on, B.grip(Object.assign({}, h, {src: {file: 'a.svelte'}}), {}).on];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    d = Path(tempfile.mkdtemp(prefix="hd-instant-"))
    try:
        (d / "t.js").write_text(JS, encoding="utf-8")
        p = subprocess.run([NODE, str(d / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 끼울 자리
def test_slot_in_a_column_splits_each_item_at_its_middle(r):
    # 첫 칸 위쪽 반 → 0 · 아래쪽 반 → 1 · 둘째 칸 위 반 → 1 · 아래 반 → 2 · 셋째 아래 반 → 3 · 멀리 아래 → 3 · 멀리 위 → 0 · 옆으로 벗어나도 가까운 칸(셋째 위 반 → 2)
    assert r["colSlots"] == [0, 1, 1, 2, 3, 3, 0, 2]


def test_slot_in_a_row_uses_x_not_y(r):
    assert r["rowSlots"] == [0, 1, 1, 3, 3]


def test_slot_in_a_two_column_grid_follows_reading_order(r):
    # 둘째 줄 오른쪽 칸(3)의 왼쪽 반 → 3 앞 · 오른쪽 반 → 맨 뒤 · 첫 칸 왼쪽 반 → 0 · 첫 줄 오른쪽 칸 오른쪽 반 → 2(둘째 줄 첫 칸 앞)
    assert r["gridSlots"] == [3, 4, 0, 2]


def test_slot_without_siblings_or_bad_point_is_minus_one_and_hidden_siblings_are_skipped(r):
    assert r["slotBad"] == [-1, -1, -1, -1]
    assert r["hidden"] == 1, "0 상자(숨은 형제)는 고르지 않는다"


def test_drop_line_sits_between_siblings_horizontal_in_a_column_vertical_in_a_row(r):
    top, mid, end = r["colLines"]
    assert top["dir"] == "h" and top["y"] == -3 and top["w"] == 200 and top["h"] == 2, top
    assert mid["dir"] == "h" and mid["y"] == 44 and mid["x"] == 0, mid       # (40 + 50) / 2 − 1
    assert end["dir"] == "h" and end["y"] == 141, end                       # 마지막 칸 아래 140 + 2 − 1
    assert r["rowLine"]["dir"] == "v" and r["rowLine"]["x"] == 64 and r["rowLine"]["h"] == 30, r["rowLine"]   # (60 + 70) / 2 − 1
    assert r["lineBad"] == [None, None, None]


def test_drop_line_in_a_grid_marks_the_row_end_not_the_gap_between_rows(r):
    end1, end2, mid = r["gridLines"]
    assert end1 == {"x": 191, "y": 0, "w": 2, "h": 40, "dir": "v"}, end1   # 첫 줄 끝 = 둘째 칸 오른쪽(줄 사이 가로 선 아님)
    assert end2 == {"x": 191, "y": 50, "w": 2, "h": 40, "dir": "v"}, end2   # 맨 뒤 = 마지막 칸 오른쪽
    assert mid["dir"] == "v" and mid["x"] == 94, mid                        # 같은 줄 두 칸 사이 (90 + 100) / 2 − 1


# ---------------------------------------------------------------- 칸 → 옮기기 목록
def test_drop_index_becomes_the_up_down_moves_the_helper_understands(r):
    assert r["moves"] == [["down", "down"], ["up", "up"], [], [], [], ["up", "up"], []]
    assert r["targets"] == [2, 0, 1]


# ---------------------------------------------------------------- 낙관 상태
def test_optimistic_pending_then_kept_and_late_signals_are_ignored(r):
    assert r["startPhase"] == "pending" and r["kept"] == "kept"
    assert r["lateRevert"] == "kept", "남긴 뒤 온 되돌림 = 무시"
    assert r["ended"] is None
    assert r["overStep"] == 1, "쓰기 수는 steps 를 넘지 않는다"


def test_optimistic_revert_keeps_the_reason_and_stops_holding(r):
    assert r["reverted"] == ["reverted", "경로 없음", False]


def test_hold_skips_reloads_while_more_writes_for_that_screen_are_left(r):
    assert r["holdStart"] is True, "3칸 중 첫 쓰기의 다시 싣기 = 건너뜀"
    assert r["holdLast"] is False, "마지막 쓰기의 다시 싣기 = 함(같은 내용이면 view-swap 이 조용히)"
    assert r["holdOther"] is False
    assert r["holdTwo"] is True, "같은 화면에 뒤 편집이 기다리면 앞 것의 다시 싣기는 건너뜀"


def test_broken_actions_return_the_same_state(r):
    assert r["same"] == [True, True, True, True]


def test_outcome_keeps_only_when_every_id_was_applied(r):
    a, b, c, d, e, f, g = r["outcome"]
    assert a == {"kept": True, "why": ""}
    assert b == {"kept": False, "why": "요소를 찾지 못했어요: h1"}
    assert c == {"kept": False, "why": "겹침"}
    assert d["kept"] is False and e["kept"] is False and f["kept"] is False and d["why"] and e["why"]
    assert g == {"kept": False, "why": "too large"}


def test_fail_text_names_the_reason_and_partial_moves(r):
    assert r["failText"][0] == "요소 옮기기 — 파일에 쓰지 못해 되돌렸어요 (3칸 중 1칸만 옮겼어요): 맨 아래"
    assert r["failText"][1].startswith("글자 고치기 — 파일에 쓰지 못해 되돌렸어요: ") and r["failText"][1].endswith("않았어요")


# ---------------------------------------------------------------- 같은 내용 = 교체 생략
def test_same_content_swaps_silently_even_while_touching_but_not_while_typing(r):
    assert r["next"] == ["silent", "fade", "defer", "fade", "wait", "instant"]


def test_same_means_no_changed_added_or_removed_block(r):
    assert r["sameDiff"] == [True, False, False, False, False, False]


# ---------------------------------------------------------------- 막대
def test_bar_hides_up_down_but_keeps_them_for_shortcuts_and_menu(r):
    assert "up" not in r["shown"] and "down" not in r["shown"] and "dup" in r["shown"], r["shown"]
    assert "up" in r["all"] and "down" in r["all"]
    assert r["keys"] == ["up", "down"]


def test_grip_is_off_for_app_cards_root_and_lonely_elements(r):
    assert r["grip"] == [True, False, False, False, True, False]
