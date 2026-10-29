"""판 메모 선(R47) — Model modules/board-links.js 규칙과 상태 파일·기록·409 합치기에 이름이 붙었는지(node).

잇기(메모에서만 · 자기 자신·같은 쌍 거절) · 끊기 · 이름 · 저장값 거르기 · 지운 메모의 선 거두기 · 줄 이름 바뀜 따라가기 · 그릴 선(없는 끝 무시) ·
409 선마다 합치기 · 선 경로."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['board-links.js', 'state-file.js', 'history.js', 'save-merge.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, L = HD.boardLinks, out = {};
let seq = [0.1, 0.5, 0.9, 0.0];
out.id = L.newId(1700000000000, () => seq.shift());
const T = '2026-10-29T00:00:00.000Z';
const a1 = L.add({}, 'l1', {from: 'note:a', to: 'note:b', fromSide: 'right', toSide: 'left'}, T);
out.added = a1;
out.toScreen = L.add(a1.map, 'l2', {from: 'note:a', to: 'screen:s1', fromSide: 'nope'}, T).map.l2;
out.toFolder = L.add(a1.map, 'l3', {from: 'note:b', to: 'folder:가입'}, T).ok;
out.reverse = L.add(a1.map, 'l4', {from: 'note:b', to: 'note:a'}, T).ok;
out.self = L.add(a1.map, 'l5', {from: 'note:a', to: 'note:a'}, T);
out.dup = L.add(a1.map, 'l6', {from: 'note:a', to: 'note:b'}, T);
out.fromScreen = L.add({}, 'l7', {from: 'screen:s1', to: 'note:a'}, T).why;
out.badEnd = L.add({}, 'l8', {from: 'note:a', to: 'card:x'}, T).why;
out.taken = L.add(a1.map, 'l1', {from: 'note:a', to: 'screen:zz'}, T).why;
out.keepsOld = Object.keys(a1.map);
out.removed = L.remove(a1.map, 'l1');
out.removeMissing = L.remove(a1.map, 'zz') === a1.map;
out.named = L.rename(a1.map, 'l1', '  왜 \n 이어졌나  ', 'T2').l1;
out.nameLong = L.rename(a1.map, 'l1', 'x'.repeat(60), 'T2').l1.label.length;
out.nameSame = L.rename(out.added.map, 'l1', '', 'T2') === out.added.map;
out.nameClear = L.rename({l1: Object.assign({}, a1.map.l1, {label: '전'})}, 'l1', ' ', 'T2').l1;
out.parse = L.parse(JSON.stringify({
  ok: {from: 'note:a', to: 'screen:s1', fromSide: 'top', toSide: 'diag', label: '  가  ', at: T, extra: 1},
  noAt: {from: 'note:a', to: 'folder:F'},
  fromScreen: {from: 'screen:s1', to: 'note:a', at: T},
  self: {from: 'note:a', to: 'note:a', at: T},
  badEnd: {from: 'note:a', to: 'x', at: T},
  notObj: 3}));
out.parseBroken = L.parse('{oops');
out.parseList = L.parse('[1]');
out.parseNone = L.parse(null);
out.ends = [L.end('note:a'), L.end('folder:가 나:다'), L.end('screen:'), L.end('x:y'), L.end(5)];
const P = {p1: {from: 'note:a', to: 'note:b', at: T}, p2: {from: 'note:b', to: 'screen:s1', at: T}, p3: {from: 'note:c', to: 'folder:F', at: T}};
out.touching = Object.keys(L.touching(P, ['b'])).sort();
out.pruned = Object.keys(L.prune(P, ['b'])).sort();
out.pruneNone = L.prune(P, ['zz']) === P;
const R = {r1: {from: 'note:a', to: 'folder:옛', at: T}, r2: {from: 'note:b', to: 'folder:옛', at: T}, r3: {from: 'note:b', to: 'folder:새', at: T}, r4: {from: 'note:a', to: 'screen:s', at: T}};
out.retarget = L.retarget(R, 'folder:옛', 'folder:새', 'T3');
out.retargetNone = L.retarget(R, 'folder:없음', 'folder:새', 'T3') === R;
out.retargetNoteToFolder = L.retarget(R, 'note:a', 'folder:X', 'T3') === R;
const V = {v1: {from: 'note:a', to: 'screen:s1', at: T}, v2: {from: 'note:a', to: 'screen:gone', at: T}, v3: {from: 'note:gone', to: 'note:a', at: T},
           v4: {from: 'note:a', to: 'screen:s1', at: T}, v5: {from: 'note:a', to: 'folder:F', at: T}, bad: {from: 'x', to: 'y'}};
const alive = {'note:a': 1, 'screen:s1': 1, 'folder:F': 1};
out.live = L.live(V, s => !!alive[s]).map(l => l.id);
out.liveEmpty = L.live(null, () => true);
const base = {b1: {from: 'note:a', to: 'note:b', at: T}, b2: {from: 'note:a', to: 'screen:s', at: T}};
const mine = Object.assign({}, base, {b1: Object.assign({}, base.b1, {label: '내 것'}), n: {from: 'note:c', to: 'note:a', at: T}});
const theirs = Object.assign({}, base); delete theirs.b2;
out.merge = L.merge(base, mine, theirs);
out.mergeConflict = L.merge(base, mine, Object.assign({}, base, {b1: Object.assign({}, base.b1, {label: '남의 것'})}));
out.resolve = HD.saveMerge.resolve(['board-links'], {'board-links': base}, {'board-links': mine}, {'board-links': theirs});
out.lost = HD.saveMerge.lostText(['board-links']);
out.inNames = HD.stateFile.NAMES.indexOf('board-links') >= 0;
out.inTrack = HD.history.TRACK.indexOf('board-links') >= 0;
const d = HD.history.diff({'board-links': {}}, {'board-links': a1.map});
out.undo = HD.history.patch({'board-links': a1.map}, d, 'before')['board-links'];
const box = {x: 0, y: 0, w: 100, h: 50};
out.anchor = L.SIDES.map(s => L.anchor(box, s));
out.near = [L.nearSide(box, {x: 300, y: 25}), L.nearSide(box, {x: 50, y: -200}), L.nearSide(box, {x: -9, y: 30}), L.nearSide(box, {x: 50, y: 90})];
out.path = L.path({x: 0, y: 0}, 'right', {x: 200, y: 0}, 'left');
out.mid = L.mid({x: 0, y: 0}, 'right', {x: 200, y: 100}, 'left');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-blinks-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


T = "2026-10-29T00:00:00.000Z"


def test_add_links_from_a_note_to_a_note_screen_or_folder(js):
    assert js["id"].startswith("l") and len(js["id"]) > 5
    assert js["added"] == {"ok": True, "why": None, "map": {"l1": {"from": "note:a", "to": "note:b", "fromSide": "right", "toSide": "left", "at": T}}}
    assert js["toScreen"] == {"from": "note:a", "to": "screen:s1", "at": T}, "틀린 변은 빼고 잇는다(그릴 때 가까운 변)"
    assert js["toFolder"] is True and js["reverse"] is True, "폴더 끝·반대 방향은 된다"
    assert js["keepsOld"] == ["l1"], "원래 map 은 그대로(되돌리기가 전 값을 쓴다)"


def test_add_refuses_self_duplicate_and_non_note_start(js):
    assert js["self"]["ok"] is False and js["self"]["why"] == "self"
    assert js["dup"]["ok"] is False and js["dup"]["why"] == "dup", "같은 방향 같은 쌍은 하나"
    assert js["fromScreen"] == "bad", "출발은 늘 메모"
    assert js["badEnd"] == "bad" and js["taken"] == "taken"


def test_remove_and_rename(js):
    assert js["removed"] == {} and js["removeMissing"]
    assert js["named"]["label"] == "왜 이어졌나" and js["named"]["at"] == "T2", "이름 = 한 줄로 정리"
    assert js["nameLong"] == 40
    assert js["nameSame"], "그대로 = 같은 map(기록 없음)"
    assert "label" not in js["nameClear"], "비우면 칸을 뺀다"


def test_parse_keeps_unknown_fields_and_drops_bad_links(js):
    p = js["parse"]
    assert p["bad"] == "dropped" and sorted(p["map"]) == ["noAt", "ok"]
    assert p["map"]["ok"] == {"from": "note:a", "to": "screen:s1", "fromSide": "top", "label": "가", "at": T, "extra": 1}, "틀린 변은 빼고 모르는 칸은 그대로"
    assert p["map"]["noAt"]["at"] == ""
    assert js["parseBroken"] == {"map": {}, "bad": "broken"} and js["parseList"]["bad"] == "broken"
    assert js["parseNone"] == {"map": {}, "bad": None}


def test_end_parses_kind_and_id(js):
    assert js["ends"] == [{"kind": "note", "id": "a"}, {"kind": "folder", "id": "가 나:다"}, None, None, None]


def test_prune_takes_links_of_deleted_notes_only(js):
    assert js["touching"] == ["p1", "p2"]
    assert js["pruned"] == ["p3"]
    assert js["pruneNone"], "닿은 선이 없으면 같은 map(쓰기 없음)"


def test_retarget_follows_a_renamed_folder_and_drops_what_would_duplicate(js):
    r = js["retarget"]
    assert r["r1"]["to"] == "folder:새" and r["r1"]["at"] == "T3"
    assert "r2" not in r and r["r3"]["to"] == "folder:새", "이미 새 이름에 이은 같은 쌍은 하나만"
    assert r["r4"]["to"] == "screen:s"
    assert js["retargetNone"] and js["retargetNoteToFolder"]


def test_live_draws_only_links_whose_ends_exist_once_per_pair(js):
    assert js["live"] == ["v1", "v5"], "없는 끝은 그리지 않고(저장은 남김) 같은 쌍은 하나"
    assert js["liveEmpty"] == []


def test_merge_per_link_and_state_registration(js):
    m = js["merge"]
    assert m["ok"] and m["map"]["b1"]["label"] == "내 것" and "b2" not in m["map"] and m["map"]["n"]["from"] == "note:c"
    assert js["mergeConflict"] == {"ok": False, "map": None}, "같은 선을 둘 다 다르게 바꿈 = 실패(잃은 변경 토스트)"
    assert js["resolve"]["ok"] and js["resolve"]["state"]["board-links"] == m["map"], "409 에서 선마다 합친다"
    assert js["lost"] == "판 메모 선"
    assert js["inNames"] and js["inTrack"], "상태 파일 이름 + 되돌리기 이름"
    assert js["undo"] == {}, "잇기 = 기록 한 줄, 되돌리면 선이 없다"


def test_geometry(js):
    assert js["anchor"] == [{"x": 50, "y": 0}, {"x": 100, "y": 25}, {"x": 50, "y": 50}, {"x": 0, "y": 25}]
    assert js["near"] == ["right", "top", "left", "bottom"]
    assert js["path"] == "M0,0 C80,0 120,0 200,0"
    assert js["mid"] == {"x": 100, "y": 50}
