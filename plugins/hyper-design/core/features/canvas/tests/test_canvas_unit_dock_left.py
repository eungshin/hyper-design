"""왼쪽 도크(S3) — modules/dock.js 의 left 칸 단위 테스트(node). 브라우저 없음.

대화(talk)는 처음에 왼쪽 · 예전 저장 상태(talk 없음)는 오른쪽 배치 그대로 + 대화만 왼쪽 · 왼쪽 ↔ 오른쪽 끌기 · 같은 쪽 혼자 떼기는 그대로 ·
닫기 = 창 숨김(R53 — 대화는 닫힌 패널이 되지 않고 떠 있는 접힌 창으로, 창 메뉴 '대화창'으로 다시) · 너비·높이는 쪽마다 · 왼쪽 너비 0 = 비었거나 Tab · 저장 왕복.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/dock.js', 'utf8'), {filename: 'dock.js'});
const K = globalThis.HD.dock, R = K.reduce, out = {};
const tabs = gs => gs.map(g => g.tabs.join('+') + ':' + g.active).join(' | ');
const d = K.defaults();
out.def = [tabs(d.left), K.leftWidth(d), tabs(d.groups)];
const pre = {v: 1, w: 410, groups: [{tabs: ['links', 'notes'], active: 'notes'}], closed: ['theme']};
const old = K.normalize(pre);
out.old = [tabs(old.left), tabs(old.groups), old.w];
let s = R(d, {type: 'move', id: 'talk', to: 0});                  // 오른쪽 첫 묶음에 합치기
out.toRight = [tabs(s.left), tabs(s.groups).split(' | ')[0], K.leftWidth(s)];
s = R(s, {type: 'move', id: 'talk', to: 'new', side: 'left'});      // 다시 왼쪽(비어 있던 왼쪽에 새 묶음)
out.back = [tabs(s.left), tabs(s.groups).indexOf('talk') < 0];
out.lone = R(s, {type: 'move', id: 'talk', to: 'new', side: 'left'}) === s;
const both = R(s, {type: 'move', id: 'notes', to: 0, side: 'left'});
out.merge = tabs(both.left);
out.lh = R(R(both, {type: 'move', id: 'notes', to: 'new', side: 'left'}), {type: 'heights', hs: [3, 1], side: 'left'}).left.map(g => g.h);
s = R(s, {type: 'close', id: 'talk'});
out.closed = [s.left.length, s.closed.indexOf('talk') >= 0, K.leftWidth(s), s.chat];
s = R(s, {type: 'chrome', part: 'chat', on: true});
out.reopen = [tabs(s.floats), s.chat];
out.lw = [R(s, {type: 'width', w: 9999, side: 'left'}).lw, R(s, {type: 'width', w: 400, side: 'left'}).w, R(s, {type: 'width', w: 400}).lw];
out.bare = K.leftWidth(R(d, {type: 'bare', on: true}));
out.collapse = [K.leftWidth(R(d, {type: 'collapse', on: true})), K.visible(R(d, {type: 'collapse', on: true}))];
let st = {}; K.save(R(R(d, {type: 'move', id: 'talk', to: 1}), {type: 'width', w: 300, side: 'left'}), (k, v) => { st[k] = v; });
const back = K.load(k => st[k]);
out.round = [tabs(back.left), tabs(back.groups).indexOf('talk') >= 0, back.lw];
out.junk = [K.normalize({groups: [], left: 'x', lw: 'q'}).lw, tabs(K.normalize({groups: [], left: [{tabs: ['zzz', 'talk', 'talk']}]}).left)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-dockl-js-"))
    try:
        (tmp / "d.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "d.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_talk_starts_on_the_left(out):
    assert out["def"] == ["talk:talk", 360, "links:links | align:align | notes+pending+history+layers:notes"], "대화 기본 360px(R53 사용자 승인 — 280 에서는 입력창 아래 줄이 잘림) · 표시는 도크 패널이 아니다"


def test_old_saved_layout_keeps_right_and_adds_talk_left(out):
    assert out["old"] == ["talk:talk", "links+notes+align+pending+history+layers:notes", 410], "예전 오른쪽 배치·너비 그대로, 대화만 왼쪽에"


def test_drag_between_sides(out):
    assert out["toRight"] == ["", "links+talk:talk", 0], "오른쪽으로 옮기면 왼쪽 도크는 없어진다(너비 0)"
    assert out["back"] == ["talk:talk", True], "다시 왼쪽으로"
    assert out["lone"], "같은 쪽에 혼자 있는 탭은 떼어도 그대로"
    assert out["merge"] == "talk+notes:notes", "다른 패널도 왼쪽 묶음에 합칠 수 있다"
    assert out["lh"] == [3, 1], "왼쪽 묶음 높이"


def test_close_hides_the_window(out):
    assert out["closed"] == [0, False, 0, False], "닫기 = 왼쪽 도크에서 빠지고 창 숨김(닫힌 패널 아님, R53)"
    assert out["reopen"] == ["talk:talk", True], "창 메뉴 '대화창'으로 다시 = 떠 있는 창"


def test_widths_per_side(out):
    assert out["lw"] == [560, 300, 360], "왼쪽 너비는 왼쪽만, 최대 560"
    assert out["bare"] == 0, "Tab(패널 모두 숨기기)이면 왼쪽도 0"
    assert out["collapse"] == [360, ["talk"]], "오른쪽 접기는 왼쪽에 닿지 않는다"


def test_save_round_trip_and_junk(out):
    assert out["round"] == ["", True, 300]
    assert out["junk"] == [360, "talk:talk"], "깨진 값 = 기본, 모르는·겹친 패널은 버림"
