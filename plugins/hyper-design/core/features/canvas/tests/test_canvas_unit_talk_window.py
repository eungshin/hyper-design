"""대화 창 하나(R53) Model — modules/talk-window.js 규칙 + 그 의도가 modules/dock.js 리듀서로 만드는 배치(node). 브라우저 없음.

붙기 판정(판 왼쪽·오른쪽 끝 40px 안 = 그 쪽 · 가운데 = 안 붙음 · 깨진 값 = 안 붙음) · 붙은 폭(기본 360, 320–560) ·
접힘 ↔ 펼침(떠 있을 때만) · 붙음 ↔ 떠 있음(dock / undock 의도 → 도크 리듀서) · 도크가 그리지 않을 때(떠 있음·숨김) ·
펼친 창 기본 자리(판 아래 가운데) · 저장 왕복 · 예전 저장 상태(대화 닫힘 → 떠 있는 접힘, 예전 기본 280 → 360).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['dock.js', 'talk-window.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const K = globalThis.HD.dock, T = globalThis.HD.talkWindow, out = {};
const run = (s, acts) => acts.reduce((a, x) => K.reduce(a, x), s);
const board = {left: 360, right: 1100};
out.snap = [T.snap(370, board), T.snap(400, board), T.snap(401, board), T.snap(10, board),
            T.snap(1090, board), T.snap(1060, board), T.snap(1059, board), T.snap(1300, board),
            T.snap(700, board), T.snap('x', board), T.snap(500, null)];
out.width = [T.width(200), T.width(9999), T.width('x'), T.width(400), T.width(undefined)];
const d = K.defaults();
out.def = [T.where(d), T.mode(d), d.lw, T.skip(d)];
// 붙음 → 떠 있음(펼침, 끈 자리) → 접힘 → 펼침
let s = run(d, T.undock(d, {x: 100, y: 60, w: 480, h: 500}, 'expanded'));
const fl = s.floats[T.fi(s)];
out.undock = [T.where(s), T.mode(s), K.leftWidth(s), [fl.x, fl.y, fl.w, fl.h], s.talk.auto, T.skip(s)];
s = run(s, T.toggle(s));
out.compact = [T.mode(s), T.where(s)];
s = run(s, T.toggle(s));
out.expanded = T.mode(s);
out.dockedToggle = T.toggle(d);
// 떠 있음 → 왼쪽(360) · 오른쪽(마지막 묶음)
const left = run(s, T.dock(s, 'left'));
out.left = [T.where(left), T.mode(left), K.leftWidth(left), left.floats.length];
const thin = K.reduce(s, {type: 'width', w: 250, side: 'left'}), narrow = run(thin, T.dock(thin, 'left'));
out.narrow = K.leftWidth(narrow);
const right = run(s, T.dock(s, 'right'));
out.right = [T.where(right), T.mode(right), right.groups[right.groups.length - 1].tabs, K.leftWidth(right)];
out.same = T.dock(d, 'left');
// 기본 자리로 떼기(pop-out) — 크기만 정하고 자리는 View 가 판 아래 가운데로
const pop = run(d, T.undock(d, null, 'expanded'));
out.pop = [T.where(pop), pop.talk.auto, T.box(pop, {w: 1000, h: 800})];
out.box0 = [T.box0({w: 1000, h: 800}), T.box0({w: 400, h: 300})];
out.boxMine = T.box(s, {w: 1000, h: 800});
// 숨김(창 메뉴 '대화창') = 도크도 그리지 않는다
out.hidden = T.skip(K.reduce(d, {type: 'chrome', part: 'chat', on: false}));
// 저장 왕복
let st = {}; K.save(s, (k, v) => { st[k] = v; });
const back = K.load(k => st[k]);
out.round = [T.where(back), T.mode(back), back.floats[T.fi(back)].w, back.talk.auto];
// 예전 저장 상태
out.oldClosed = (o => [T.where(o), T.mode(o), o.closed.indexOf('talk')])(K.normalize({v: 1, w: 300, lw: 280, groups: [{tabs: ['links'], active: 'links'}], closed: ['theme', 'talk']}));
out.oldLw = [K.normalize({v: 1, w: 300, lw: 280, groups: [{tabs: ['links'], active: 'links'}], left: [{tabs: ['talk'], active: 'talk'}]}).lw,
             K.normalize({v: 1, w: 300, lw: 300, groups: [{tabs: ['links'], active: 'links'}], left: [{tabs: ['talk'], active: 'talk'}]}).lw,
             K.normalize({v: 1, w: 300, lw: 280, talk: {mode: 'compact'}, groups: [{tabs: ['links'], active: 'links'}], left: [{tabs: ['talk'], active: 'talk'}]}).lw];
out.badMode = T.mode(K.normalize({v: 1, groups: [{tabs: ['links'], active: 'links'}], floats: [{tabs: ['talk'], active: 'talk', x: 1, y: 2, w: 300, h: 300}], talk: {mode: 'huge'}}));
// 닫기(탭 ×) = 숨김 — 대화는 닫힌 패널이 되지 않는다
const shut = K.reduce(d, {type: 'close', id: 'talk'});
out.close = [T.where(shut), shut.chat, shut.closed.indexOf('talk')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-talkw-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_snap_both_edges_and_middle(out):
    assert out["snap"][:4] == ["left", "left", None, "left"], "판 왼쪽 끝 40px 안(도크 위 포함) = 왼쪽, 41px = 안 붙음"
    assert out["snap"][4:8] == ["right", "right", None, "right"], "오른쪽 끝 40px 안(오른쪽 도크 위 포함) = 오른쪽"
    assert out["snap"][8:] == [None, None, None], "가운데·깨진 값 = 안 붙음"


def test_docked_width_clamp(out):
    assert out["width"] == [320, 560, 360, 400, 360], "붙은 폭 320–560, 깨진 값 = 360(사용자 승인 기본)"


def test_default_is_docked_left_at_360(out):
    assert out["def"] == ["left", "docked", 360, []], "처음 = 왼쪽에 붙은 펼친 창 360px, 도크가 그린다"


def test_undock_floats_expanded_where_dropped(out):
    assert out["undock"] == ["float", "expanded", 0, [100, 60, 480, 500], False, ["talk"]], "떼면 그 자리 펼친 창 · 왼쪽 도크 자리 없어짐 · 창 틀이 그린다"


def test_compact_expanded_toggle_only_while_floating(out):
    assert out["compact"] == ["compact", "float"] and out["expanded"] == "expanded"
    assert out["dockedToggle"] == [], "붙은 창은 늘 펼침"


def test_dock_left_and_right(out):
    assert out["left"] == ["left", "docked", 360, 0], "왼쪽 끝에 놓으면 왼쪽 도크 360px"
    assert out["narrow"] == 320, "붙을 때 폭은 320 밑으로 가지 않는다(입력창 아래 줄이 잘리지 않게)"
    assert out["right"][:3] == ["right", "docked", ["talk"]] and out["right"][3] == 0, "오른쪽 = 오른쪽 도크 마지막 묶음"
    assert out["same"] == [], "이미 그 쪽이면 의도 없음"


def test_pop_out_uses_default_box(out):
    where, auto, box = out["pop"]
    assert where == "float" and auto is True
    assert box == out["box0"][0] == {"x": 280, "y": 148, "w": 440, "h": 640}, "판 아래 가운데, 440×640, 아래 12px"
    assert out["box0"][1] == {"x": 8, "y": 8, "w": 384, "h": 280}, "좁은 판이면 판 안으로 줄임"
    assert out["boxMine"] == {"x": 100, "y": 60, "w": 480, "h": 500}, "옮긴 창은 그 자리"


def test_hidden_window_is_not_drawn_by_dock(out):
    assert out["hidden"] == ["talk"]


def test_round_trip_and_old_states(out):
    assert out["round"] == ["float", "expanded", 480, False]
    assert out["oldClosed"] == ["float", "compact", -1], "예전에 닫은 대화 = 떠 있는 접힌 창"
    assert out["oldLw"] == [360, 300, 280], "예전 기본 280 은 새 기본 360 으로(고른 폭·새 상태는 그대로)"
    assert out["badMode"] == "compact", "깨진 모드 = 접힘"
    assert out["close"] == ["float", False, -1], "닫기 = 창 숨김(창 메뉴 '대화창'으로 다시)"
