"""판의 선 길 찾기(task 38) Model — modules/route.js 의 sides · route · plan 순수 함수(node). 브라우저 없음.

쪽은 DOM 줄이 아니라 지금 상자 자리로 고른다: 세로 범위가 겹치면 마주 보는 왼·오른쪽, 가로 범위가 겹치면 위·아래,
아니면 꺾임 ≤2 의 직각선(가운데 틈에서 꺾음). 통로·띄운 길은 곧은 길이 다른 카드를 지날 때만, 나란한 줄은 실제로 겹칠 때만.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

ROUTE_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/route.js', 'utf8'), {filename: 'route.js'});
const R = globalThis.HD.route, out = {};
const W = 375, H = 900;
// 재현(route_repro.py): usage 바로 왼쪽 84px 에 tabs — 같은 눈의 줄(위 끝 같음), DOM 줄은 달라도 상관없다
const usage = {x: 4956, y: 1188, w: W, h: H}, tabs = {x: 4956 - 84 - W, y: 1188, w: W, h: H};
out.repro = R.plan({usage: usage, tabs: tabs}, [{a: 'usage', b: 'tabs'}], {corridorX: 200})[0];
out.reproLen = R.length(out.repro.pts);
// 위아래 이웃
const up = {x: 0, y: 0, w: W, h: H}, down = {x: 40, y: 1200, w: W, h: H};
out.down = R.route(up, down, {});
out.up = R.route(down, up, {});
// 막힌 길: a → c 사이에 b(같은 줄)
const a = {x: 0, y: 0, w: W, h: H}, b = {x: 500, y: 0, w: W, h: H}, c = {x: 1000, y: 0, w: W, h: H};
out.blocked = R.plan({a: a, b: b, c: c}, [{a: 'a', b: 'c'}], {corridorX: -100})[0];
out.boxB = b;
// 비껴 선 상자(겹침 없음): 꺾임 ≤2
out.diag = R.route({x: 0, y: 0, w: 100, h: 100}, {x: 400, y: 900, w: 100, h: 100}, {});
// 나란한 줄: 같은 도착의 같은 쪽으로 들어가 겹치는 두 선 → 갈라짐 · 겹치지 않는 선들 → 둘 다 lane 0
const p = {x: 0, y: 0, w: 100, h: 100}, q = {x: 200, y: 200, w: 100, h: 100}, t = {x: 400, y: 600, w: 100, h: 100};
out.par = R.plan({p: p, q: q, t: t}, [{a: 'p', b: 't'}, {a: 'q', b: 't'}], {});
const l = {x: 0, y: 0, w: 100, h: 300}, m = {x: 300, y: 0, w: 100, h: 300}, r = {x: 600, y: 0, w: 100, h: 300};
out.free = R.plan({l: l, m: m, r: r}, [{a: 'm', b: 'l'}, {a: 'm', b: 'r'}], {});
out.overlapCount = R.overlaps(out.par[0].pts, out.par[1].pts);
// 끌기: only = 움직인 카드에 닿은 선만 다시, 나머지는 prev 그대로
const prev = R.plan({l: l, m: m, r: r}, [{a: 'm', b: 'l'}, {a: 'l', b: 'r'}], {});
const moved = {x: 300, y: 600, w: 100, h: 300};
out.only = R.plan({l: l, m: moved, r: r}, [{a: 'm', b: 'l'}, {a: 'l', b: 'r'}], {only: {m: 1}, prev: prev});
out.prev = prev;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-route-js-"))
    try:
        (tmp / "route.js").write_text(ROUTE_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "route.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def hits_box(pts, b, pad=0):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        lo_x, hi_x, lo_y, hi_y = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
        if hi_x > b["x"] - pad and lo_x < b["x"] + b["w"] + pad and hi_y > b["y"] - pad and lo_y < b["y"] + b["h"] + pad:
            return True
    return False


def bends(pts):
    return max(0, len(pts) - 2)


def test_repro_neighbour_left_is_short_side_to_side(out):
    """재현: 대상이 84px 왼쪽 같은 눈의 줄 — 출발 왼쪽 → 대상 오른쪽, 길이 ≤ 1.3 × 틈(예전 8515px)."""
    r = out["repro"]
    assert (r["from"], r["to"]) == ("left", "right"), r
    assert r["mode"] == "direct"
    assert out["reproLen"] <= 1.3 * 84, out["reproLen"]


def test_vertical_neighbours_use_top_bottom(out):
    assert (out["down"]["from"], out["down"]["to"]) == ("bottom", "top")
    assert (out["up"]["from"], out["up"]["to"]) == ("top", "bottom")
    assert bends(out["down"]["pts"]) <= 2


def test_diagonal_is_orthogonal_with_at_most_two_bends(out):
    pts = out["diag"]["pts"]
    assert bends(pts) <= 2, pts
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        assert x0 == x1 or y0 == y1, pts


def test_blocked_direct_detours_around_box(out):
    """a → c 곧은 길이 b 를 지나면 돌아간다 — 돌아간 길도 b 를 피한다."""
    r = out["blocked"]
    assert r["mode"] != "direct"
    assert not hits_box(r["pts"], out["boxB"]), r["pts"]


def test_parallel_lanes_only_when_overlapping(out):
    """같은 대상 위로 들어가 겹치는 두 선은 갈라지고, 겹치지 않는 선들은 출발 순서와 상관없이 lane 0."""
    a, b = out["par"]
    assert a["lane"] == 0 and b["lane"] > 0
    assert out["overlapCount"] == 0
    assert [x["lane"] for x in out["free"]] == [0, 0]
    assert (out["free"][0]["from"], out["free"][1]["from"]) == ("left", "right")


def test_drag_reroutes_only_touching_lines(out):
    """only = 움직인 카드에 닿은 선만 다시 — 닿지 않은 선은 prev 의 점 그대로."""
    assert out["only"][1]["pts"] == out["prev"][1]["pts"]
    assert out["only"][0]["pts"] != out["prev"][0]["pts"]
