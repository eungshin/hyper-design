"""카드 옮긴 자리(card-pos, 셸 C4) — 저장값 거르기 HD.rows.cleanPos(Model)와 View view-card-pos 의 상자 재기·옮기기 한 단계를 node 로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['rows.js', 'align.js', 'view-card-pos.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, R = HD.rows, out = {};
const live = {a: '안내', b: '안내', c: '설정'};
out.keep = R.cleanPos(JSON.stringify({a: {dx: 10, dy: '5', g: '안내'}, c: {dx: 1, dy: 2}}), live);
out.drop = R.cleanPos(JSON.stringify({a: {dx: 1, dy: 1, g: '옛 줄'}, gone: {dx: 1, dy: 1}, b: {dx: 'x', dy: 1}, c: null}), live);
out.empty = R.cleanPos(null, live);
out.broken = R.cleanPos('{oops', live);
out.notObj = R.cleanPos('[1,2]', live);
out.absent = R.cleanPos(JSON.stringify({a: {dx: 1, dy: 2, g: '안내'}, fresh: {dx: 5, dy: 6, g: '새 줄'}, junk: {dx: 'x', dy: 1}, b: {dx: 1, dy: 1, g: '옛 줄'}}), live, true);   // W10 F1 — 밖에서 받은 자리: 아직 판에 없는 카드는 들고 있는다
// View: 상자(판 좌표 = 화면 px / 배율) · 옮기기 한 단계(되돌리기·다시 하기) · 잠긴 카드는 세기만
const el = (id, l, t) => ({dataset: {id}, classList: {contains: () => false, toggle() {}}, offsetWidth: 100, style: {},
  closest: () => null, getBoundingClientRect: () => ({left: l, top: t, width: 50, height: 80})});
const cards = {a: el('a', 110, 20), b: el('b', 210, 20), k: el('k', 310, 20)};
const rows = [], store = {};
const CP = HD.viewCardPos.mount({$: () => null, $$: () => Object.values(cards), rowsEl: {getBoundingClientRect: () => ({left: 10, top: 0})}, stage: {},
  getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; }, hash: 'h', zoom: () => 0.5,
  cardEl: id => cards[id] || null, locked: id => id === 'k', record: op => rows.push(op), toast: () => {}, redraw: () => {}, moved: () => {}});
out.box = CP.boxOf(cards.a, {left: 10, top: 0});
store['hd-card-pos:h'] = JSON.stringify({a: {dx: 3, dy: 4, g: ''}, fresh: {dx: 7, dy: 8, g: '결제'}});
const before = store['hd-card-pos:h'];
CP.reload();
out.reloadAbsent = {fresh: CP.at('fresh') || null, a: CP.at('a') || null, untouched: store['hd-card-pos:h'] === before};
CP.replace({});
out.boxes = CP.boxes(['a', 'b', 'k', 'none']);
out.moved = CP.move({a: [5, 0], none: [1, 1]}, '정렬');
out.after = CP.at('a'); rows[0].undo(); out.undone = CP.at('a') || null; rows[0].redo(); out.redone = CP.at('a');
out.saved = JSON.parse(store['hd-card-pos:h']);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-cardpos-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_clean_pos_keeps_valid_and_takes_live_group(js):
    assert js["keep"] == {"pos": {"a": {"dx": 10, "dy": 5, "g": "안내"}, "c": {"dx": 1, "dy": 2, "g": "설정"}}, "dirty": False, "bad": False}


def test_clean_pos_drops_moved_group_missing_and_broken_entries(js):
    assert js["drop"] == {"pos": {}, "dirty": True, "bad": False}, "다른 줄로 간 화면·없는 화면·숫자 아님·null 은 버리고 다시 쓴다"


def test_clean_pos_empty_and_broken_values(js):
    assert js["empty"] == {"pos": {}, "dirty": False, "bad": False}
    assert js["broken"] == {"pos": {}, "dirty": False, "bad": True}, "깨진 JSON = 빈 자리(다시 쓰지 않음) + bad(경고)"
    assert js["notObj"]["bad"] is True and js["notObj"]["pos"] == {}


def test_box_of_is_stage_units(js):
    assert js["box"] == {"x": 200, "y": 40, "w": 100, "h": 160}


def test_boxes_skip_locked_and_missing(js):
    assert [b["id"] for b in js["boxes"]["boxes"]] == ["a", "b"] and js["boxes"]["locked"] == 1


def test_move_is_one_undo_step(js):
    assert js["moved"] is True
    assert js["after"] == {"dx": 5, "dy": 0, "g": ""}
    assert js["undone"] is None and js["redone"] == js["after"]
    assert js["saved"] == {"a": {"dx": 5, "dy": 0, "g": ""}}


def test_clean_pos_keep_absent_holds_cards_not_on_board_yet(js):
    """W10 F1 — 밖에서 받은 card-pos(hd add)가 새 카드 데이터보다 먼저 닿아도 그 카드의 자리를 버리지 않는다(다시 쓰지도 않음).
    판에 있는 카드의 규칙(다른 줄·숫자 아님 = 버림)은 그대로."""
    assert js["absent"] == {"pos": {"a": {"dx": 1, "dy": 2, "g": "안내"}, "fresh": {"dx": 5, "dy": 6, "g": "새 줄"}}, "dirty": True, "bad": False}


def test_reload_keeps_pos_of_card_not_rendered_yet(js):
    r = js["reloadAbsent"]
    assert r["fresh"] == {"dx": 7, "dy": 8, "g": "결제"}, "다시 읽기 = 아직 없는 카드의 자리도 들고 있다(데이터가 오면 place 가 쓴다)"
    assert r["a"] == {"dx": 3, "dy": 4, "g": ""} and r["untouched"], "버릴 것이 없으면 다시 쓰지 않는다(밖 쓰기를 메아리하지 않음)"
