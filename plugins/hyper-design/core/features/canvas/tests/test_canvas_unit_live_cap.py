"""판 위 라이브 카드 상한(task 35) Model — modules/live-cap.js 순수 함수 단위 테스트(node). 브라우저 없음.

보이는·고른·크게 보기 카드는 내리지 않는다 · 화면 밖 15초 넘은 것만 · 실린 수가 K 이하가 될 때까지만 · 오래 안 본 것부터.
LOD(figma-lite 1): 화면 위 너비가 MINW(120px) 아래인 카드는 싣지 않고, 실린 것은 바로 내린다 — 고른·크게 보기 카드는 그대로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/live-cap.js', 'utf8'), {filename: 'live-cap.js'});
const L = globalThis.HD.liveCap, out = {};
const ids = (n) => Array.from({length: n}, (_, i) => 'c' + i);
const seen = (n, t) => Object.fromEntries(ids(n).map((id, i) => [id, t + i]));   // c0 이 가장 오래 안 본 것
const now = 100000;
out.defaults = [L.K, L.IDLE];
out.underCap = L.unload({loaded: ids(10), visible: [], lastSeen: seen(10, 0), selected: [], modal: null, now});
out.overCap = L.unload({loaded: ids(13), visible: [], lastSeen: seen(13, 0), selected: [], modal: null, now});
out.keep = L.unload({loaded: ids(13), visible: ['c0'], lastSeen: seen(13, 0), selected: ['c1'], modal: 'c2', now});
out.fresh = L.unload({loaded: ids(13), visible: [], lastSeen: Object.assign(seen(13, 0), {c0: now - 14000, c1: now - 1000}), selected: [], modal: null, now});
out.allVisible = L.unload({loaded: ids(13), visible: ids(13), lastSeen: seen(13, now), selected: [], modal: null, now});
out.neverSeen = L.unload({loaded: ['a', 'b', 'c'], visible: [], lastSeen: {b: now - 20000}, selected: [], modal: null, now, K: 1});
out.knobs = L.unload({loaded: ['a', 'b'], visible: ['a'], lastSeen: {a: now, b: now}, selected: [], modal: null, now, K: 1, idle: 0});
out.minw = L.MINW;
out.readable = [L.readable(119), L.readable(120), L.readable(54), L.readable(390), L.readable(80, 60), L.readable(undefined), L.readable(NaN)];
out.small = L.unload({loaded: ['a', 'b', 'c', 'd'], visible: ['a', 'b', 'c', 'd'], small: ['a', 'b', 'c', 'e'], lastSeen: {}, selected: ['b'], modal: 'c', now});
out.smallThenCap = L.unload({loaded: ids(13), visible: [], small: ['c12'], lastSeen: seen(13, 0), selected: [], modal: null, now});
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-live-cap-"))
    try:
        (tmp / "cap.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "cap.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_defaults_k10_idle15s(out):
    assert out["defaults"] == [10, 15000]


def test_at_or_under_cap_unloads_nothing(out):
    assert out["underCap"] == []


def test_over_cap_unloads_oldest_first_down_to_k(out):
    assert out["overCap"] == ["c0", "c1", "c2"]


def test_visible_selected_modal_never_unloaded(out):
    assert out["keep"] == ["c3", "c4", "c5"]


def test_offscreen_less_than_idle_is_kept(out):
    assert out["fresh"] == ["c2", "c3", "c4"], "화면 밖 15초가 안 된 카드는 상한을 넘어도 그대로"


def test_all_visible_means_cap_is_exceeded_not_forced(out):
    assert out["allVisible"] == []


def test_never_seen_counts_as_oldest(out):
    assert out["neverSeen"] == ["a", "c"]


def test_k_and_idle_can_be_passed(out):
    assert out["knobs"] == ["b"]


def test_readable_threshold_is_on_screen_width_120(out):
    assert out["minw"] == 120
    assert out["readable"] == [False, True, False, True, True, True, True], "모르는 너비는 지금처럼 싣는다"


def test_small_cards_unload_at_once_but_selected_and_modal_stay(out):
    assert out["small"] == ["a"], "작은 카드는 보여도 바로 내린다 · 고른(b)·크게 보기(c) 카드는 그대로 · 읽히는 d·안 실린 e 는 목록에 없다"


def test_small_unloads_count_toward_cap(out):
    assert out["smallThenCap"] == ["c12", "c0", "c1"], "작은 것을 먼저 내리고 남은 실린 수로 상한을 센다"
