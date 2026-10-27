"""판 메모(R23) — Model modules/board-notes.js 규칙과 상태 파일·기록·409 합치기에 이름이 붙었는지(node).

만들기·고치기·빈 메모 버리기(finish) · 옮기기 · 지우기 · 저장값 거르기(parse) · 409 합치기(merge, save-merge 가 board-notes 에 씀) ·
누른 자리가 빈 판인가(spot — 카드·판 글·선·UI 위에서는 메모를 만들지 않는다)."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['board-notes.js', 'state-file.js', 'history.js', 'save-merge.js', 'layers.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, B = HD.boardNotes, out = {};
let seq = [0.1, 0.5, 0.9, 0.0];
out.id = B.newId(1700000000000, () => seq.shift());
const m0 = B.create({}, 'a', {x: 10.6, y: -4.2}, 5);
out.created = m0.a;
out.typed = B.finish(m0, 'a', '첫 줄\r\n둘째 줄  \n', 6);
out.empty = B.finish(m0, 'a', '  \n ', 6);
out.same = B.finish(out.typed.map, 'a', '첫 줄\n둘째 줄', 7).kind;
out.missing = B.finish(m0, 'zz', 'x', 7).kind;
out.long = B.finish(m0, 'a', 'x'.repeat(2500), 6).map.a.text.length;
out.moved = B.move(out.typed.map, 'a', 100.4, 200.6, 8).a;
out.movedKeepsOld = out.typed.map.a.x;
out.removed = B.remove(out.typed.map, 'a');
out.parse = B.parse(JSON.stringify({a: {x: 1.4, y: 2, text: '가', w: 300, color: 'y', extra: 1}, b: {x: 'no', y: 1, text: '나'}, c: {x: 1, y: 1, text: ''}, d: {x: 0, y: 0, w: 5, h: -1, text: '라'}}));
out.parseBroken = B.parse('{oops');
out.parseList = B.parse('[1]');
out.parseNone = B.parse(null);
const base = {a: {x: 0, y: 0, w: 280, text: '가', at: 1}, b: {x: 5, y: 5, w: 280, text: '나', at: 1}};
const mine = Object.assign({}, base, {a: Object.assign({}, base.a, {x: 50}), n: {x: 9, y: 9, w: 280, text: '새', at: 2}});
const theirs = Object.assign({}, base, {b: Object.assign({}, base.b, {text: '나나'})});
out.merge = B.merge(base, mine, theirs);
out.mergeConflict = B.merge(base, mine, Object.assign({}, base, {a: Object.assign({}, base.a, {x: 70})}));
out.mergeDeleted = B.merge(base, Object.assign({}, base, {a: undefined}), base);
out.resolve = HD.saveMerge.resolve(['board-notes'], {'board-notes': base}, {'board-notes': mine}, {'board-notes': theirs, notes: []});
out.label = HD.saveMerge.LABEL['board-notes'];
out.inNames = HD.stateFile.NAMES.indexOf('board-notes') >= 0;
out.inTrack = HD.history.TRACK.indexOf('board-notes') >= 0;
const d = HD.history.diff({'board-notes': {}}, {'board-notes': out.typed.map});
out.undo = HD.history.patch({'board-notes': out.typed.map}, d, 'before')['board-notes'];
const cards = [{x0: 500, y0: 0, x1: 875, y1: 800}, {x0: 1000, y0: 900, x1: 1375, y1: 1700}];
out.room = {open: B.room({x: 100, y: 1000}, cards), nearCard: B.room({x: 300, y: 100}, cards), tight: B.room({x: 450, y: 100}, cards),
            onCard: B.room({x: 600, y: 100}, cards), underCard: B.room({x: 600, y: 810}, cards), belowBand: B.room({x: 300, y: 860}, cards)};
out.spot = {
  stage: B.spot([['#stage']]),
  between: B.spot([['.cards'], ['.flow'], ['#rows'], ['#stage'], ['#screens']]),
  card: B.spot([['.cover', 'button'], ['.phone'], ['.card'], ['.cards'], ['#rows']]),
  caption: B.spot([['.ftitle'], ['.card'], ['.cards']]),
  boardText: B.spot([['p', '.hint', '.bt'], ['#intro'], ['#stage']]),
  line: B.spot([['path'], ['svg', '#ar'], ['#rows']]),
  rowLabel: B.spot([['.glabel'], ['.flow']]),
  note: B.spot([['.bn-text'], ['.bnote'], ['#bnotes'], ['#stage']]),
  editing: B.spot([['textarea'], ['.bnote']]),
  tools: B.spot([['svg'], ['button', '.tb'], ['#tools'], ['#screens']]),
  nothing: B.spot([])
};
const r0 = {a: {x: 0, y: 0, w: 280, text: '가', at: 1}};
out.resize = {w: B.resize(r0, 'a', 500.6, undefined, 9).a, both: B.resize(r0, 'a', 300, 200.4, 9).a, small: B.resize(r0, 'a', 10, 3, 9).a,
  big: B.resize(r0, 'a', 99999, 99999, 9).a, auto: B.resize({a: Object.assign({}, r0.a, {h: 300})}, 'a', 280, null, 9).a,
  same: B.resize(r0, 'a', 280, undefined, 9) === r0, missing: B.resize(r0, 'zz', 300, 300, 9) === r0, keepsOld: r0.a.w};
out.extent = {grow: B.extent({x0: 0, y0: 0, x1: 1000, y1: 800}, [{x: -300, y: 50, w: 280, h: 60}, {x: 4000, y: 3000, w: 280, h: 90}]),
  none: B.extent({x0: 0, y0: 0, x1: 10, y1: 10}, []), only: B.extent(null, [{x: 5, y: 6, w: 7, h: 8}]), bad: B.extent({x0: 0, y0: 0, x1: 10, y1: 10}, [{x: NaN, y: 0, w: 1, h: 1}])};
out.layerRows = B.layers({b: {x: 900, y: 10, w: 280, text: '\n  둘째 메모  \n아래', at: 1}, a: {x: 5, y: 10, w: 280, text: '첫 메모', at: 1},
  c: {x: 0, y: 5000, w: 280, text: 'x'.repeat(60), at: 1}});
out.layerEmpty = B.layers({});
const LL = HD.layers, tree = LL.build([{id: 'g0', name: '줄', screens: [{id: 's1', name: '화면'}]}], [], {}, null, out.layerRows);
out.tree = tree.map(x => [x.kind, x.id, x.row || null, x.count == null ? null : x.count]);
out.treeNone = LL.build([], [], {}, null, []).length;
out.treeQ = LL.filter(tree, {q: '둘째'}).map(x => x.id);
out.treeFold = LL.filter(tree, {folded: {'@notes': 1}}).map(x => x.id);
out.treeHover = LL.hoverIds(tree, out.layerRows[0].id);
// R26 숨김·잠금 — 메모의 칸 hidden·locked(true 만), 되돌리기는 View 의 기록 한 줄
const f0 = {a: {x: 0, y: 0, w: 280, text: '가', at: 1}, b: {x: 0, y: 90, w: 280, text: '나', at: 1}};
const fh = B.flag(f0, ['a'], 'hidden', true, 9);
out.flag = {hid: fh.a, other: fh.b === f0.b, keepsOld: !('hidden' in f0.a), shown: B.flag(fh, ['a'], 'hidden', false, 10).a,
  same: B.flag(f0, ['a'], 'hidden', false, 9) === f0, missing: B.flag(f0, ['zz'], 'locked', true, 9) === f0, badKey: B.flag(f0, ['a'], 'color', true, 9) === f0,
  lockBoth: (() => { const m = B.flag(f0, ['a', 'b'], 'locked', true, 9); return [m.a.locked, m.b.locked]; })(),
  is: [B.isHidden(fh.a), B.isHidden(f0.a), B.isLocked({locked: true}), B.isLocked({locked: 'yes'}), B.isHidden(null)]};
out.parseFlags = B.parse(JSON.stringify({a: {x: 1, y: 2, text: '가', hidden: true, locked: 'yes'}, b: {x: 1, y: 2, text: '나', locked: true, hidden: 0}}));
out.layerFlags = B.layers({a: {x: 0, y: 0, w: 280, text: '숨김', hidden: true, at: 1}, b: {x: 0, y: 90, w: 280, text: '잠금', locked: true, at: 1}});
const ft = LL.build([], [], {}, null, out.layerFlags);
out.flagTree = ft.map(x => [x.id, x.hid, x.lock]);
out.flagOnly = [LL.filter(ft, {only: 'hidden'}).map(x => x.id), LL.filter(ft, {only: 'locked'}).map(x => x.id)];
out.flagAll = LL.build([], [], {}, null, [{id: 'note:a', name: 'a', hid: true, lock: true}]).map(x => [x.id, x.hid, x.lock]);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-bnotes-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_create_is_an_empty_note_at_the_rounded_point(js):
    assert js["id"].startswith("n") and len(js["id"]) > 5
    assert js["created"] == {"x": 11, "y": -4, "w": 280, "text": "", "at": 5}


def test_finish_keeps_typed_text_and_drops_an_empty_note(js):
    assert js["typed"]["kind"] == "keep" and js["typed"]["map"]["a"]["text"] == "첫 줄\n둘째 줄", "줄바꿈은 남고 \\r\\n·끝 빈칸은 정리"
    assert js["typed"]["map"]["a"]["at"] == 6
    assert js["empty"] == {"map": {}, "kind": "drop"}, "빈 글 = 메모를 뺀다(셸은 기록 줄을 남기지 않는다)"
    assert js["same"] == "same", "그대로면 저장·기록 없음"
    assert js["missing"] == "same"
    assert js["long"] == 2000


def test_move_and_remove_return_new_maps(js):
    assert (js["moved"]["x"], js["moved"]["y"], js["moved"]["text"]) == (100, 201, "첫 줄\n둘째 줄")
    assert js["movedKeepsOld"] == 11, "원래 map 은 그대로(되돌리기가 전 값을 쓴다)"
    assert js["removed"] == {}


def test_parse_keeps_unknown_keys_and_drops_bad_notes(js):
    p = js["parse"]
    assert p["bad"] == "dropped" and sorted(p["map"]) == ["a", "d"]
    assert p["map"]["a"] == {"x": 1, "y": 2, "text": "가", "w": 300, "color": "y", "extra": 1, "at": 0}, "모르는 칸(color·extra)은 그대로"
    assert p["map"]["d"]["w"] == 280 and "h" not in p["map"]["d"], "틀린 폭·높이 = 기본"
    assert js["parseBroken"] == {"map": {}, "bad": "broken"} and js["parseList"]["bad"] == "broken"
    assert js["parseNone"] == {"map": {}, "bad": None}


def test_merge_takes_each_sides_change_per_note_and_fails_on_a_shared_note(js):
    m = js["merge"]
    assert m["ok"] and m["map"]["a"]["x"] == 50 and m["map"]["b"]["text"] == "나나" and m["map"]["n"]["text"] == "새"
    assert js["mergeConflict"] == {"ok": False, "map": None}, "같은 메모를 둘 다 다르게 바꿈 = 실패(잃은 변경 토스트)"
    assert "a" not in js["mergeDeleted"]["map"], "내가 지운 메모는 지운 채"


def test_state_file_history_and_conflict_merge_know_board_notes(js):
    assert js["inNames"] and js["inTrack"], "상태 파일 이름 + 되돌리기 이름"
    assert js["label"] == "판 메모"
    r = js["resolve"]
    assert r["ok"] and r["state"]["board-notes"]["a"]["x"] == 50 and r["state"]["board-notes"]["b"]["text"] == "나나", "409 에서 메모마다 합친다"
    assert js["undo"] == {}, "만들기+쓰기 = 기록 한 줄, 되돌리면 메모가 없다"


def test_spot_is_empty_only_on_bare_board(js):
    s = js["spot"]
    assert s["stage"] == s["between"] == "empty"
    assert s["card"] == s["caption"] == s["boardText"] == s["line"] == s["rowLabel"] == s["tools"] == "busy", "카드·판 글·선·UI 위에서는 만들지 않는다"
    assert s["note"] == "note" and s["editing"] == "busy" and s["nothing"] == "busy"


def test_room_refuses_a_card_and_stops_the_note_before_the_next_card(js):
    r = js["room"]
    assert r["open"] == {"free": True, "x": 86, "y": 974, "w": 280}, "빈 판 = 누른 점이 첫 줄 글자 자리, 기본 폭"
    assert r["nearCard"]["free"] and r["nearCard"]["w"] == 500 - 12 - 286, "오른쪽 카드 앞까지만(카드를 덮지 않음)"
    assert r["tight"]["w"] == 120, "틈이 좁아도 최소 폭"
    assert r["onCard"]["free"] is False, "카드 위 = 만들지 않음"
    assert r["belowBand"]["w"] == 280, "다른 높이의 카드는 폭을 줄이지 않는다"
    assert r["underCard"]["y"] == 804 and r["underCard"]["x"] == 586, "바로 위 카드 밑으로 내려 카드(이름 줄)를 덮지 않는다"


def test_resize_clamps_and_height_is_auto_until_dragged(js):
    r = js["resize"]
    assert r["w"]["w"] == 501 and "h" not in r["w"], "폭만 끈 = 높이는 글 높이대로"
    assert (r["both"]["w"], r["both"]["h"], r["both"]["at"]) == (300, 200, 9)
    assert (r["small"]["w"], r["small"]["h"]) == (120, 52), "최소 폭·높이"
    assert (r["big"]["w"], r["big"]["h"]) == (1600, 4000), "최대 폭·높이"
    assert "h" not in r["auto"], "h=null = 글 높이로 돌아가기"
    assert r["same"] and r["missing"], "그대로·없는 id = 같은 map(기록 없음)"
    assert r["keepsOld"] == 280


def test_extent_grows_to_include_far_notes(js):
    e = js["extent"]
    assert e["grow"] == {"x0": -300, "y0": 0, "x1": 4280, "y1": 3090}, "멀리 있는 메모까지 전체 보기에 든다"
    assert e["none"] == {"x0": 0, "y0": 0, "x1": 10, "y1": 10}
    assert e["only"] == {"x0": 5, "y0": 6, "x1": 12, "y1": 14}
    assert e["bad"] == {"x0": 0, "y0": 0, "x1": 10, "y1": 10}, "숫자가 아닌 상자는 건너뜀"


def test_layer_rows_follow_reading_order_with_first_line_names(js):
    rows = js["layerRows"]
    assert [r["id"] for r in rows] == ["note:a", "note:b", "note:c"], "위→아래, 왼→오른"
    assert rows[0]["name"] == "첫 메모" and rows[1]["name"] == "둘째 메모", "첫 글 줄"
    assert rows[2]["name"] == "x" * 40 + "…"
    assert js["layerEmpty"] == []


def test_layer_tree_has_a_notes_group(js):
    t = js["tree"]
    assert t[-4:] == [["row", "@notes", None, 3], ["note", "note:a", "@notes", None], ["note", "note:b", "@notes", None], ["note", "note:c", "@notes", None]]
    assert js["treeNone"] == 0, "메모가 없으면 묶음도 없다"
    assert js["treeQ"] == ["@notes", "note:b"], "이름 찾기에 메모 글도"
    assert js["treeFold"] == ["g0", "s1", "@notes"], "접으면 메모 줄이 빠진다"
    assert js["treeHover"] == [], "메모 줄 올리기는 카드 강조를 하지 않는다"


def test_flag_hides_and_locks_notes_as_fields_and_keeps_old_data_valid(js):
    """R26 — 숨김·잠금 = 메모의 칸 hidden·locked(true 만 · 끄면 칸을 뺌 → 옛 메모와 같은 모양), 새 map, 바뀐 것 없으면 같은 map."""
    f = js["flag"]
    assert f["hid"]["hidden"] is True and f["hid"]["at"] == 9 and f["other"] and f["keepsOld"]
    assert "hidden" not in f["shown"], "보이기 = 칸을 뺀다(옛 데이터 모양)"
    assert f["same"] and f["missing"] and f["badKey"], "그대로·없는 id·모르는 칸 = 같은 map"
    assert f["lockBoth"] == [True, True]
    assert f["is"] == [True, False, True, False, False], "true 만 숨김·잠금"
    m = js["parseFlags"]["map"]
    assert m["a"]["hidden"] is True and "locked" not in m["a"], "깨진 칸 값은 빼고 메모는 남긴다"
    assert m["b"]["locked"] is True and "hidden" not in m["b"]


def test_layer_rows_carry_hide_and_lock(js):
    rows = js["layerFlags"]
    assert [(r["id"], r["hid"], r["lock"]) for r in rows] == [("note:a", True, False), ("note:b", False, True)]
    assert js["flagTree"] == [["@notes", False, False], ["note:a", True, False], ["note:b", False, True]], "묶음 줄 = 모두 숨김·모두 잠금일 때만"
    assert js["flagOnly"] == [["@notes", "note:a"], ["@notes", "note:b"]], "숨긴 것만·잠긴 것만 거르기에 메모도"
    assert js["flagAll"][0] == ["@notes", True, True]
