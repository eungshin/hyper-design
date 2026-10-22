"""선 끝 손잡이(Q3) Model — modules/line-ends.js 순수 함수 단위 테스트(node). 브라우저 없음.

ends(d) 의 첫·마지막 점, handles(line) 의 손잡이 수·자리·방향, dropTarget 의 놓기 규칙(E18: 삭제 대기 막기, 숨긴 카드 없음).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

LINE_ENDS_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/route.js', 'utf8'), {filename: 'route.js'});
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/line-ends.js', 'utf8'), {filename: 'line-ends.js'});
const L = globalThis.HD.lineEnds, R = globalThis.HD.route, out = {};
out.curve = L.ends('M10,20 C10,0 50,0 50,40');
out.poly = L.ends('M1.5,2 L30,2 L30,-4.5');
out.rel = L.ends('M10,10 l5,5 h10 v-3');
const routed = R.routeCurve({x: 100, y: 300, dir: 'up'}, {x: 600, y: 900}, {lift: 16, apex: 10, laneX: -40});
out.routed = L.ends(routed);
const d = 'M0,0 L100,0 L100,50';
out.one = L.handles({from: 'a', to: 'b', both: false, plan: false, d: d});
out.both = L.handles({from: 'a', to: 'b', both: true, plan: false, d: d});
out.plan = L.handles({from: 'a', to: 'b', both: false, plan: true, d: d});
const boxes = [
  {id: 'a', x: 0, y: 0, w: 100, h: 200, hid: false, del: false},
  {id: 'b', x: 200, y: 0, w: 100, h: 200, hid: false, del: false},
  {id: 'c', x: 400, y: 0, w: 100, h: 200, hid: false, del: false},
  {id: 'x', x: 600, y: 0, w: 100, h: 200, hid: false, del: true},
  {id: 'h', x: 800, y: 0, w: 100, h: 200, hid: true, del: false},
  {id: 'lo', x: 1000, y: 0, w: 100, h: 200, hid: false, del: false},
  {id: 'hi', x: 1050, y: 50, w: 100, h: 200, hid: false, del: false},
];
const ln = {from: 'a', to: 'b'};
out.hit = L.dropTarget(boxes, [450, 100], ln);
out.edge = L.dropTarget(boxes, [400, 200], ln);
out.miss = L.dropTarget(boxes, [150, 100], ln);
out.own = L.dropTarget(boxes, [50, 100], ln);
out.cur = L.dropTarget(boxes, [250, 100], ln);
out.del = L.dropTarget(boxes, [650, 100], ln);
out.hid = L.dropTarget(boxes, [850, 100], ln);
out.over = L.dropTarget(boxes, [1075, 100], ln);
out.underOnly = L.dropTarget(boxes, [1020, 20], ln);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-q3-js-"))
    try:
        (tmp / "q3.js").write_text(LINE_ENDS_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "q3.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ends_first_and_last_point(out):
    """곡선(M…C…)·꺾은선(M…L…L…)·상대 명령의 첫 점과 마지막 점, route.js 가 만든 선은 출발·도착 점 그대로."""
    assert out["curve"] == {"start": [10, 20], "end": [50, 40]}
    assert out["poly"] == {"start": [1.5, 2], "end": [30, -4.5]}
    assert out["rel"] == {"start": [10, 10], "end": [25, 12]}
    assert out["routed"] == {"start": [100, 300], "end": [600, 900]}


def test_handles_one_way_both_and_plan(out):
    """한 방향 = 도착 끝에 손잡이 하나, 양방향 = 시작 끝에 거꾸로 하나 더, 기획 갈래 = 없음."""
    assert out["one"] == [{"from": "a", "to": "b", "at": [100, 50]}]
    assert out["both"] == [{"from": "a", "to": "b", "at": [100, 50]}, {"from": "b", "to": "a", "at": [0, 0]}]
    assert out["plan"] == []


def test_drop_target_rules(out):
    """다른 카드 = 그 카드(가장자리 포함), 빈 곳·출발 카드·지금 도착 카드·숨긴 카드 = 없음, 삭제 대기 = 막힘, 겹치면 위(나중) 카드."""
    assert out["hit"] == {"id": "c"}
    assert out["edge"] == {"id": "c"}
    assert out["miss"] is None
    assert out["own"] is None
    assert out["cur"] is None
    assert out["del"] == {"blocked": "del"}
    assert out["hid"] is None
    assert out["over"] == {"id": "hi"}
    assert out["underOnly"] == {"id": "lo"}
