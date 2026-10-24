"""프로젝트 탭 바(task 44) Model — modules/tabs.js 순수 함수 단위 테스트(node). 브라우저 없음.

bar: GET /api/tabs 이름 + 프로젝트 줄 → 탭(모르는·휴지통·겹친 이름은 빼고, 지금 프로젝트가 없으면 끝에 더함) ·
close/others: 하나뿐이면 못 닫음, 지금 탭을 닫으면 옆 탭으로 갈 곳 · move/slot: 끌어 놓을 자리 · rename: 빈 값·같은 값 무시, 공백 정리, 길이 한도 ·
step: 이전/다음(끝에서 돌아감) · arrows: 넘칠 때만 ◀ ▶, 끝이면 그쪽 끔.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/tabs.js', 'utf8'), {filename: 'tabs.js'});
const T = globalThis.HD.tabs, out = {};
const rows = [
  {name: 'a', title: '가', state: 'open', current: false},
  {name: 'b', title: '나', state: 'off', current: true},
  {name: 'c', title: '다', state: 'off', current: false},
  {name: 't', title: '휴지', state: 'off', current: false, trashed: true},
  {name: 'm', title: '없음', state: 'missing', current: false}
];
out.bar = T.bar(['c', 'zz', 'a', 'c', 7, 't', 'm'], rows, 'b');
out.barHas = T.bar(['b', 'a'], rows, 'b');
out.barBad = [T.bar(null, rows, 'b').names, T.bar({tabs: 1}, rows, null).names];
out.barNoCur = T.bar(['a'], rows, null);
out.close = [T.close(['a', 'b', 'c'], 'a', 'b'), T.close(['a', 'b', 'c'], 'b', 'b'), T.close(['a', 'b', 'c'], 'c', 'c'),
             T.close(['b'], 'b', 'b'), T.close(['a', 'b'], 'x', 'b')];
out.others = [T.others(['a', 'b', 'c'], 'b', 'b'), T.others(['a', 'b', 'c'], 'c', 'b'), T.others(['b'], 'b', 'b')];
out.move = [T.move(['a', 'b', 'c', 'd'], 'a', 3), T.move(['a', 'b', 'c', 'd'], 'd', 0), T.move(['a', 'b', 'c', 'd'], 'b', 2),
            T.move(['a', 'b', 'c', 'd'], 'b', 1), T.move(['a', 'b', 'c', 'd'], 'c', 4), T.move(['a', 'b'], 'x', 0)];
out.slot = [T.slot([10, 50, 90], 0), T.slot([10, 50, 90], 30), T.slot([10, 50, 90], 95), T.slot([], 5)];
out.rename = [T.rename('가', '  새  이름 '), T.rename('가', '   '), T.rename('가', ' 가 '), T.rename('가', 'x'.repeat(100)), T.rename('가', null),
              T.rename('가', 'a\nb\tc')];
out.step = [T.step(['a', 'b', 'c'], 'b', 1), T.step(['a', 'b', 'c'], 'c', 1), T.step(['a', 'b', 'c'], 'a', -1), T.step(['a'], 'a', 1),
            T.step(['a', 'b'], 'x', 1), T.step([], null, 1)];
out.arrows = [T.arrows(0, 500, 500), T.arrows(0, 900, 500), T.arrows(200, 900, 500), T.arrows(400, 900, 500), T.arrows(399.5, 900, 500)];
out.place = [T.place({left: 0, right: 1440}, 395, 300), T.place({left: 0, right: 1140}, 395, 500), T.place({left: 0, right: 1140}, 395, 2000),
             T.place({left: 0, right: 1440}, null, 300), T.place({left: 0, right: 500}, 395, 300)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-tabs-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bar_drops_unknown_trashed_duplicates_and_appends_current(out):
    b = out["bar"]
    assert b["names"] == ["c", "a", "m", "b"], "받은 차례 그대로 · 모르는·휴지통·겹친·글 아닌 이름은 빼고 · 지금 프로젝트는 끝에"
    assert b["added"] is True and b["dropped"] == 4
    assert [(t["name"], t["title"], t["current"]) for t in b["tabs"]] == [("c", "다", False), ("a", "가", False), ("m", "없음", False), ("b", "나", True)]
    assert b["tabs"][2]["state"] == "missing", "없어진 프로젝트도 탭으로는 남는다(누르면 그때 알림)"


def test_bar_keeps_current_where_it_is(out):
    assert out["barHas"]["names"] == ["b", "a"] and out["barHas"]["added"] is False and out["barHas"]["dropped"] == 0


def test_bar_bad_input_and_unknown_current(out):
    assert out["barBad"] == [["b"], []], "목록이 아니면 빈 목록(지금 것만)"
    assert out["barNoCur"]["names"] == ["a"] and out["barNoCur"]["added"] is False, "지금 프로젝트를 모르면 더하지 않는다"


def test_close_rules(out):
    other, cur_mid, cur_end, only, unknown = out["close"]
    assert other == {"ok": True, "names": ["b", "c"], "go": None, "why": ""}
    assert cur_mid["ok"] and cur_mid["names"] == ["a", "c"] and cur_mid["go"] == "c", "지금 탭을 닫으면 오른쪽 탭으로"
    assert cur_end["names"] == ["a", "b"] and cur_end["go"] == "b", "맨 끝이면 왼쪽 탭으로"
    assert only["ok"] is False and only["names"] == ["b"] and "하나" in only["why"], "하나뿐이면 못 닫는다"
    assert unknown["ok"] is False and unknown["names"] == ["a", "b"]


def test_close_others(out):
    keep_cur, keep_other, only = out["others"]
    assert keep_cur == {"ok": True, "names": ["b"], "go": None, "why": ""}
    assert keep_other["names"] == ["c"] and keep_other["go"] == "c", "남길 탭이 지금 것이 아니면 그리로 간다"
    assert only["ok"] is False


def test_move_by_insertion_slot(out):
    assert out["move"] == [["b", "c", "a", "d"], ["d", "a", "b", "c"], ["a", "b", "c", "d"], ["a", "b", "c", "d"],
                           ["a", "b", "d", "c"], ["a", "b"]], "slot = 원래 목록에서 끼울 자리(0..n), 제자리는 그대로"


def test_slot_from_tab_midpoints(out):
    assert out["slot"] == [0, 1, 3, 0]


def test_rename_validation(out):
    ok, empty, same, long_, none, ctrl = out["rename"]
    assert ok == {"ok": True, "title": "새 이름"}, "앞뒤 공백 빼고 사이 공백 하나로"
    assert empty["ok"] is False and empty["why"] == "empty"
    assert same["ok"] is False and same["why"] == "same"
    assert long_["ok"] is True and len(long_["title"]) == 80, "80자에서 자른다"
    assert none["ok"] is False and none["why"] == "empty"
    assert ctrl == {"ok": True, "title": "a b c"}, "줄바꿈·탭도 공백 하나로"


def test_step_wraps(out):
    assert out["step"] == ["c", "a", "c", None, None, None], "하나뿐이거나 지금 것을 모르면 갈 곳 없음"


def test_arrows_only_when_overflowing(out):
    fit, start, mid, end, near = out["arrows"]
    assert fit == {"over": False, "prev": False, "next": False}
    assert start == {"over": True, "prev": False, "next": True}
    assert mid == {"over": True, "prev": True, "next": True}
    assert end == {"over": True, "prev": True, "next": False}
    assert near["next"] is False, "반 픽셀 차이는 끝으로 본다(배율 반올림)"


def test_place_centres_but_clears_hint_and_edge(out):
    centred, pushed, capped, nohint, tiny = out["place"]
    assert centred == {"left": 570, "max": 1021}, "넉넉하면 판 가운데"
    assert pushed == {"left": 407, "max": 721}, "가운데면 안내와 겹칠 때 안내 오른쪽으로 민다"
    assert capped == {"left": 407, "max": 721}, "넘치면 쓸 수 있는 폭까지(나머지는 ◀ ▶)"
    assert nohint == {"left": 570, "max": 1416}, "안내가 없으면 판 양쪽 끝만"
    assert tiny["max"] == 160 and tiny["left"] == 407, "좁아도 최소 폭은 남긴다(안내 오른쪽)"
