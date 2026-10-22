"""정렬 패널·레이어 폴더 Model — modules/align.js · modules/folders.js 순수 함수 단위 테스트(node). 브라우저 없음.

align: 고른 상자 덮개 기준 6가지 맞추기, 가장자리 틈 같게 분배(첫·끝 그대로), gap 띄워 한 줄·한 칸 늘어놓기.
folders: 폴더 만들기(번호·이름), 이름 바꾸기, 지우기, 넣기·빼기, 접기, 없는 화면 정리, 저장·읽기, 화면 → 폴더.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

ALIGN_FOLDERS_JS = r"""
const fs = require('fs'), vm = require('vm');
for (const n of ['align', 'folders']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + n + '.js', 'utf8'), {filename: n + '.js'});
const A = globalThis.HD.align, F = globalThis.HD.folders, out = {};

// 맞추기: 크기 다른 상자 3개(덮개 x 0..240, y 0..280)
const a = {id: 'A', x: 0, y: 0, w: 100, h: 50}, b = {id: 'B', x: 150, y: 30, w: 60, h: 120}, c = {id: 'C', x: 40, y: 200, w: 200, h: 80};
out.bounds = A.bounds([a, b, c]);
out.align = {};
for (const how of ['left', 'hcenter', 'right', 'top', 'vcenter', 'bottom']) out.align[how] = A.align([a, b, c], how);
out.alignOne = A.align([a], 'left');
out.alignDone = A.align([a, {id: 'D', x: 0, y: 90, w: 30, h: 10}], 'left');

// 분배: 4개, 틈 30·120·100 → (560-310)/3
const row = [{id: 'R', x: 300, y: 0, w: 100, h: 10}, {id: 'P', x: 0, y: 0, w: 100, h: 10}, {id: 'S', x: 500, y: 0, w: 60, h: 10}, {id: 'Q', x: 130, y: 0, w: 50, h: 10}];
const flip = bs => bs.map(o => ({id: o.id, x: o.y, y: o.x, w: o.h, h: o.w}));
out.distX = A.distribute(row, 'x');
out.distY = A.distribute(flip(row), 'y');
out.distTwo = A.distribute(row.slice(0, 2), 'x');

// 늘어놓기: x 순 B, C, A
const st = [{id: 'A', x: 300, y: 50, w: 100, h: 40}, {id: 'B', x: 0, y: 10, w: 80, h: 60}, {id: 'C', x: 150, y: -20, w: 120, h: 30}];
out.stack40 = A.stack(st, 'x', 40);
out.stackNone = A.stack(st, 'x', 40, 'none');
out.stackNeg = A.stack(st, 'x', -5);
out.stackBad = A.stack(st, 'x', 'abc');
out.stackY = A.stack(flip(st), 'y', 40);
out.stackTieY = A.stack([{id: 'D', x: 0, y: 100, w: 50, h: 50}, {id: 'E', x: 0, y: 0, w: 50, h: 50}], 'x', 10);
out.stackTieIn = A.stack([{id: 'G', x: 0, y: 0, w: 50, h: 50}, {id: 'F', x: 0, y: 0, w: 50, h: 50}], 'x', 10);
out.stackOne = A.stack([st[0]], 'x', 40);

// 폴더
const R = F.reduce, s0 = F.initial();
const s1 = R(s0, {type: 'create', ids: ['a', 'b']});
const s2 = R(s1, {type: 'create', ids: ['b', 'c', 'c'], name: '  로그인  '});
const s3 = R(s2, {type: 'create', ids: []});
out.create = {s0, s1, s2, s3, gap: R({v: 1, folders: [{id: 'f5', name: 'x', ids: [], open: true}]}, {type: 'create', ids: ['z']}).folders[0]};
out.rename = {ok: R(s2, {type: 'rename', id: 'f1', name: '  홈 '}).folders[1].name,
  empty: R(s2, {type: 'rename', id: 'f1', name: '   '}) === s2, same: R(s2, {type: 'rename', id: 'f2', name: '로그인'}) === s2,
  unknown: R(s2, {type: 'rename', id: 'f9', name: 'x'}) === s2, other: R(s2, {type: 'rename', id: 'f1', name: '홈'}).folders[0] === s2.folders[0]};
out.remove = {ok: R(s2, {type: 'remove', id: 'f2'}), unknown: R(s2, {type: 'remove', id: 'f9'}) === s2};
out.add = {ok: R(s2, {type: 'add', id: 'f1', ids: ['c', 'd']}), already: R(s2, {type: 'add', id: 'f1', ids: ['a']}) === s2,
  unknown: R(s2, {type: 'add', id: 'f9', ids: ['c']}) === s2};
out.take = {ok: R(s2, {type: 'take', ids: ['b', 'zz']}), none: R(s2, {type: 'take', ids: ['zz']}) === s2};
out.fold = {closed: R(s2, {type: 'fold', id: 'f1', open: false}).folders[1].open, same: R(s2, {type: 'fold', id: 'f1', open: true}) === s2,
  unknown: R(s2, {type: 'fold', id: 'f9', open: false}) === s2};
out.prune = {ok: R(s2, {type: 'prune', live: ['a', 'c']}), all: R(s2, {type: 'prune', live: ['a', 'b', 'c']}) === s2, empty: R(s2, {type: 'prune', live: []})};
out.noop = {unknownType: R(s2, {type: 'zzz'}) === s2, nullAction: R(s2, null) === s2};
const store = {}, set = (k, v) => { store[k] = v; }, get = k => store[k];
F.save(s2, set, 'hd-folders:x');
out.load = {round: F.load(get, 'hd-folders:x'), missing: F.load(get, 'nope'), garbage: F.load(() => 'not json{', 'k'),
  wrongV: F.load(() => '{"v":2,"folders":[]}', 'k'), throws: F.load(() => { throw new Error('blocked'); }, 'k'),
  dup: F.load(() => JSON.stringify({v: 1, folders: [{id: 'f1', name: 'a', ids: ['x', 'y'], open: false}, {id: 'f2', name: ' ', ids: ['y', 'z', 3]}, {id: 'bad', ids: []}, {id: 'f1', ids: []}]}), 'k')};
let saved = true; try { F.save(s2, () => { throw new Error('full'); }, 'k'); } catch (e) { saved = false; }
out.saveNoThrow = saved;
out.of = [F.of(s2, 'b'), F.of(s2, 'a'), F.of(s2, 'zz'), F.of(null, 'a')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-align-js-"))
    try:
        (tmp / "af.js").write_text(ALIGN_FOLDERS_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "af.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- align ---

def test_bounds_covers_all_boxes(out):
    assert out["bounds"] == {"x": 0, "y": 0, "w": 240, "h": 280}


def test_align_left_right_hcenter(out):
    al = out["align"]
    assert al["left"] == {"B": [-150, 0], "C": [-40, 0]}, "왼쪽 = 덮개 왼쪽 0, 이미 맞은 A 는 빠짐"
    assert al["right"] == {"A": [140, 0], "B": [30, 0]}, "오른쪽 = 240"
    assert al["hcenter"] == {"A": [70, 0], "B": [-60, 0], "C": [-20, 0]}, "가로 가운데 = 120"


def test_align_top_bottom_vcenter(out):
    al = out["align"]
    assert al["top"] == {"B": [0, -30], "C": [0, -200]}
    assert al["bottom"] == {"A": [0, 230], "B": [0, 130]}, "아래 = 280"
    assert al["vcenter"] == {"A": [0, 115], "B": [0, 50], "C": [0, -100]}, "세로 가운데 = 140"


def test_align_needs_two_and_omits_zero_moves(out):
    assert out["alignOne"] == {}
    assert out["alignDone"] == {}, "이미 맞으면 옮길 것 없음"


def test_distribute_equal_edge_gaps_first_last_stay(out):
    # 틈 (560 - 310) / 3 = 83.33 → Q 는 183.33 으로(+53), R 은 316.67 로(+17), P·S 는 그대로
    assert out["distX"] == {"Q": [53, 0], "R": [17, 0]}
    assert out["distY"] == {"Q": [0, 53], "R": [0, 17]}
    assert out["distTwo"] == {}, "3개 미만은 분배 안 함"


def test_stack_row_gap_order_and_tops(out):
    # x 순 B(0..80) → C 는 120 으로, A 는 280 으로; 위는 B 의 y 10 에 맞춤
    assert out["stack40"] == {"C": [-30, 30], "A": [-20, -40]}
    assert out["stackNone"] == {"C": [-30, 0], "A": [-20, 0]}, "cross none = y 그대로"


def test_stack_gap_clamps_and_defaults(out):
    assert out["stackNeg"] == {"C": [-70, 30], "A": [-100, -40]}, "음수 gap → 0"
    assert out["stackBad"] == {"C": [10, 30], "A": [60, -40]}, "숫자 아닌 gap → 80"


def test_stack_column_mirrors_row(out):
    assert out["stackY"] == {"C": [30, -30], "A": [-40, -20]}


def test_stack_ties_and_minimum(out):
    assert out["stackTieY"] == {"D": [60, -100]}, "x 같으면 y 순 — E 가 먼저"
    assert out["stackTieIn"] == {"F": [60, 0]}, "x·y 같으면 넣은 순 — G 가 먼저"
    assert out["stackOne"] == {}


# --- folders ---

def test_folder_create_numbers_names_and_steals_ids(out):
    c = out["create"]
    assert c["s0"] == {"v": 1, "folders": []}
    assert c["s1"]["folders"] == [{"id": "f1", "name": "새 폴더 1", "ids": ["a", "b"], "open": True}]
    assert c["s2"]["folders"] == [{"id": "f2", "name": "로그인", "ids": ["b", "c"], "open": True},
                                  {"id": "f1", "name": "새 폴더 1", "ids": ["a"], "open": True}], "새 폴더가 맨 앞, b 는 옮겨 감"
    assert c["s3"]["folders"][0] == {"id": "f3", "name": "새 폴더 3", "ids": [], "open": True}, "빈 폴더도 됨"
    assert c["gap"]["id"] == "f6" and c["gap"]["name"] == "새 폴더 6", "가장 큰 번호 + 1"


def test_folder_rename(out):
    r = out["rename"]
    assert r["ok"] == "홈", "앞뒤 빈칸 정리"
    assert r["empty"] and r["same"] and r["unknown"], "빈 이름·같은 이름·없는 폴더 = 같은 객체"
    assert r["other"], "안 바꾼 폴더는 같은 객체"


def test_folder_remove(out):
    assert out["remove"]["ok"]["folders"] == [{"id": "f1", "name": "새 폴더 1", "ids": ["a"], "open": True}]
    assert out["remove"]["unknown"]


def test_folder_add_moves_from_other_folders(out):
    ad = out["add"]
    assert [f["ids"] for f in ad["ok"]["folders"]] == [["b"], ["a", "c", "d"]]
    assert ad["already"] and ad["unknown"]


def test_folder_take(out):
    assert [f["ids"] for f in out["take"]["ok"]["folders"]] == [["c"], ["a"]]
    assert out["take"]["none"]


def test_folder_fold(out):
    assert out["fold"]["closed"] is False
    assert out["fold"]["same"] and out["fold"]["unknown"]


def test_folder_prune_keeps_empty_folders(out):
    assert [f["ids"] for f in out["prune"]["ok"]["folders"]] == [["c"], ["a"]]
    assert out["prune"]["all"]
    assert [f["ids"] for f in out["prune"]["empty"]["folders"]] == [[], []]


def test_folder_noop_actions_return_same_object(out):
    assert out["noop"] == {"unknownType": True, "nullAction": True}


def test_folder_load_save(out):
    ld = out["load"]
    assert ld["round"] == out["create"]["s2"]
    for k in ("missing", "garbage", "wrongV", "throws"):
        assert ld[k] == {"v": 1, "folders": []}, k
    assert ld["dup"]["folders"] == [{"id": "f1", "name": "a", "ids": ["x", "y"], "open": False},
                                    {"id": "f2", "name": "새 폴더 2", "ids": ["z"], "open": True}], "한 화면은 한 폴더, 잘못된 폴더는 버림"
    assert out["saveNoThrow"]


def test_folder_of(out):
    assert out["of"] == ["f2", "f1", None, None]
