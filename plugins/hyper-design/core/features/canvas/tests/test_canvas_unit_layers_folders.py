"""레이어 폴더(H17) Model — modules/layers.js 의 build(4번째 인자 folders)·filter 단위 테스트(node). 브라우저 없음.

사용자 폴더가 맨 앞(폴더 줄 + 그 화면), 그 화면은 원래 줄에서 빠짐, 폴더·줄에 화면 수, 숨김·잠금은 '모두'일 때,
접힌 폴더는 화면만 빠짐, 폴더 이름이 맞으면 그 화면 모두, 빈 폴더는 거르기가 없을 때만, 인자 셋이면 예전 그대로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

LAYERS_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/layers.js', 'utf8'), {filename: 'layers.js'});
const L = globalThis.HD.layers, out = {};
const groups = [
  {id: 'g0', name: '처음 들어올 때', screens: [{id: 'a', name: '로그인'}, {id: 'b', name: '가입'}, {id: 'c', name: '약관'}]},
  {id: 'g1', name: '운동 기록', screens: [{id: 'd', name: '오늘'}, {id: 'e', name: '달력'}]}
];
const texts = [{id: '@intro', name: '판 글 · 소개'}];
const st = {hidden: {b: true, d: true, e: true}, locked: {a: true, d: true}, memo: {c: 2}};
const F = {v: 1, folders: [
  {id: 'f2', name: '결제 흐름', ids: ['e', 'a', 'zz'], open: true},
  {id: 'f1', name: '빈 폴더', ids: [], open: true}
]};
const brief = xs => xs.map(x => [x.kind, x.id, x.folder || x.row || null, x.count === undefined ? null : x.count, x.hid, x.lock].join(':'));
out.old = L.build(groups, texts, st);
out.oldFiltered = L.filter(out.old, {q: '운동'}).map(x => x.id);
out.oldFolded = L.filter(out.old, {folded: {g0: 1}}).map(x => x.id);
const t = L.build(groups, texts, st, F);
out.tree = brief(t);
out.screenInFolder = t.filter(x => x.id === 'a')[0];
out.all = L.filter(t, {}).map(x => x.id);
out.foldedFolder = L.filter(t, {folded: {f2: 1}}).map(x => x.id);
out.qFolder = L.filter(t, {q: '결제'}).map(x => x.id);
out.qScreen = L.filter(t, {q: '달력'}).map(x => x.id);
out.qRowNotFolder = L.filter(t, {q: '처음'}).map(x => x.id);
out.onlyHidden = L.filter(t, {only: 'hidden'}).map(x => x.id);
out.onlyLocked = L.filter(t, {only: 'locked'}).map(x => x.id);
// 모두 숨김·모두 잠금
const t2 = L.build(groups, texts, {hidden: {a: true, e: true}, locked: {a: true, e: true, b: true, c: true}}, F);
out.agg = brief(t2.filter(x => x.kind !== 'screen' && x.kind !== 'text'));
// 빈 상태 = 줄마다 count 만 붙는다
out.empty = brief(L.build(groups, [], {}, {v: 1, folders: []}));
// 줄이 모두 폴더로 가면 그 줄은 숨는다
const t3 = L.build(groups, [], {}, {v: 1, folders: [{id: 'f1', name: 'x', ids: ['d', 'e'], open: true}]});
out.rowGone = L.filter(t3, {}).map(x => x.id);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-lyf-js-"))
    try:
        (tmp / "ly.js").write_text(LAYERS_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "ly.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_three_arg_build_is_unchanged(out):
    assert out["old"] == [
        {"kind": "row", "id": "g0", "name": "처음 들어올 때", "hid": False, "lock": False, "memo": 0},
        {"kind": "screen", "id": "a", "name": "로그인", "row": "g0", "hid": False, "lock": True, "memo": 0},
        {"kind": "screen", "id": "b", "name": "가입", "row": "g0", "hid": True, "lock": False, "memo": 0},
        {"kind": "screen", "id": "c", "name": "약관", "row": "g0", "hid": False, "lock": False, "memo": 2},
        {"kind": "row", "id": "g1", "name": "운동 기록", "hid": True, "lock": False, "memo": 0},
        {"kind": "screen", "id": "d", "name": "오늘", "row": "g1", "hid": True, "lock": True, "memo": 0},
        {"kind": "screen", "id": "e", "name": "달력", "row": "g1", "hid": True, "lock": False, "memo": 0},
        {"kind": "text", "id": "@intro", "name": "판 글 · 소개", "hid": False, "lock": False, "memo": 0},
    ]
    assert out["oldFiltered"] == ["g1", "d", "e"]
    assert out["oldFolded"] == ["g0", "g1", "d", "e", "@intro"]


def test_folders_first_and_screens_leave_their_row(out):
    assert out["tree"] == [
        "folder:f2::2:false:false",
        "screen:e:f2::true:false",
        "screen:a:f2::false:true",
        "folder:f1::0:false:false",
        "row:g0::2:false:false",
        "screen:b:g0::true:false",
        "screen:c:g0::false:false",
        "row:g1::1:true:true",
        "screen:d:g1::true:true",
        "text:@intro:::false:false",
    ], "폴더 순서 = 폴더 안 순서, 모르는 화면(zz)은 빠짐, 줄의 count = 남은 화면 수"
    s = out["screenInFolder"]
    assert s["folder"] == "f2" and s["row"] == "g0", "폴더 화면도 원래 줄을 안다(빼면 돌아갈 곳)"


def test_hid_and_lock_mean_all(out):
    assert out["agg"] == [
        "folder:f2::2:true:true",
        "folder:f1::0:false:false",
        "row:g0::2:false:true",
        "row:g1::1:false:false",
    ], "모두 숨김 = 숨김, 모두 잠금 = 잠금, 빈 폴더는 둘 다 아님"
    assert out["empty"] == ["row:g0::3:false:false", "screen:a:g0::false:false", "screen:b:g0::false:false", "screen:c:g0::false:false",
                            "row:g1::2:false:false", "screen:d:g1::false:false", "screen:e:g1::false:false"]


def test_filter_with_folders(out):
    assert out["all"] == ["f2", "e", "a", "f1", "g0", "b", "c", "g1", "d", "@intro"]
    assert out["foldedFolder"] == ["f2", "f1", "g0", "b", "c", "g1", "d", "@intro"], "접힌 폴더는 남고 화면만 빠진다"
    assert out["qFolder"] == ["f2", "e", "a"], "폴더 이름이 맞으면 그 화면 모두, 빈 폴더는 숨는다"
    assert out["qScreen"] == ["f2", "e"]
    assert out["qRowNotFolder"] == ["g0", "b", "c"], "줄 이름이 맞아도 폴더로 간 화면은 줄 아래가 아니다"
    assert out["onlyHidden"] == ["f2", "e", "g0", "b", "g1", "d"]
    assert out["onlyLocked"] == ["f2", "a", "g1", "d"]
    assert out["rowGone"] == ["f1", "d", "e", "g0", "a", "b", "c"], "화면이 모두 폴더로 간 줄은 보이지 않는다"
