"""R31 폴더(판의 화면 줄) 다루기 규칙 — JS modules/row-ops.js(순수): 끌어 놓을 곳 · 다른 폴더로 옮기기 계획 · 제목이 따라갈 자리 · 폴더째 옮기기 ·
단축키 · 메뉴 글. Python board_rows.plan_group_move(순수) + group_move 쓰기 한 번 → 되살리기로 바이트 그대로. I/O 는 임시 폴더·가짜 빌드뿐."""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import board_rows  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/row-ops.js', 'utf8'), {filename: 'row-ops.js'});
const O = globalThis.HD.rowOps, out = {};
const A = {id: 'a', row: 'row:홈'}, B = {id: 'b', row: 'row:설정', folder: 'f1'}, C = {id: 'c', row: 'row:설정'};
out.dropFolder = O.drop([A, B], {kind: 'folder', id: 'f1', name: '내 묶음'});
out.dropFolderSame = O.drop([B], {kind: 'folder', id: 'f1'});
out.dropRow = O.drop([A, B, C], {kind: 'row', id: 'row:설정', name: '설정'});
out.dropRowOther = O.drop([A, C], {kind: 'row', id: 'row:로그인', name: '로그인'});
out.dropDrafts = O.drop([A], {kind: 'row', id: '@drafts', name: '빈 레이아웃'});
out.dropNotes = O.drop([A], {kind: 'row', id: '@notes'});
out.dropNone = O.drop([], {kind: 'row', id: 'row:설정'});
const R = [{name: '로그인', ids: ['l1', 'l2']}, {name: '홈', ids: ['h1']}, {name: '설정', ids: ['s1', 's2']}];
out.aOk = O.assign(R, ['s2', 'h1'], '로그인');
out.aSame = O.assign(R, ['l1'], '로그인');
out.aPart = O.assign(R, ['l1', 's1'], '로그인');
out.aNoRow = O.assign(R, ['l1'], '없음');
out.aNoId = O.assign(R, ['zz'], '홈');
out.aEmpty = O.assign(R, [], '홈');
out.tMin = O.titleShift([{dx: 80, dy: 40}, {dx: 120, dy: 60}, {dx: 80, dy: 40}]);
out.tOne = O.titleShift([{dx: 0, dy: 0}, {dx: 200, dy: 90}]);
out.tUp = O.titleShift([{dx: 0, dy: 0}, {dx: 30, dy: -50}]);
out.tBad = O.titleShift([{dx: 'x', dy: null}, {dx: 10, dy: 5}]);
out.tNone = O.titleShift([]);
out.dOk = O.dragPlan(['a', 'b'], {}, 20.4, -9.6);
out.dZero = O.dragPlan(['a'], {}, 0.2, 0);
out.dLocked = O.dragPlan(['a', 'b'], {b: true}, 10, 10);
out.k = [{key: 'G', ctrlKey: true, shiftKey: true}, {key: 'g', metaKey: true, shiftKey: true}, {key: 'Backspace', ctrlKey: true},
         {key: 'Delete'}, {key: 'Backspace'}, {key: 'g', ctrlKey: true}, {key: 'Delete', ctrlKey: true}, {key: 'g', ctrlKey: true, shiftKey: true, altKey: true}, null].map(O.key);
out.w = {ungroup: O.WORDS.ungroup, del3: O.WORDS.del(3), del0: O.WORDS.del(0)};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-rowops-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 끌어 놓을 곳(레이어 패널)
def test_drop_on_user_folder_adds_only_what_is_not_in_it(js):
    assert js["dropFolder"] == {"add": {"id": "f1", "ids": ["a"]}}
    assert js["dropFolderSame"] == {}, "이미 그 폴더 = 할 일 없음"


def test_drop_on_board_folder_takes_out_of_user_folder_and_moves_other_rows(js):
    assert js["dropRow"] == {"take": ["b"], "assign": {"to": "설정", "ids": ["a"]}}, "같은 판 폴더 화면은 그대로, 사용자 폴더에서는 뺀다"
    assert js["dropRowOther"] == {"assign": {"to": "로그인", "ids": ["a", "c"]}}


def test_drop_on_drafts_notes_or_nothing_does_nothing(js):
    assert js["dropDrafts"] == {} and js["dropNotes"] == {} and js["dropNone"] == {}


# ---------------------------------------------------------------- 다른 폴더로 옮기기 계획(판)
def test_assign_moves_in_row_order_and_reports_emptied_rows(js):
    assert js["aOk"] == {"to": "로그인", "ids": ["h1", "s2"], "emptied": ["홈"]}, "판 폴더 차례 · 다 빠진 폴더는 emptied"
    assert js["aPart"] == {"to": "로그인", "ids": ["s1"], "emptied": []}, "이미 그 폴더인 화면은 빼고"
    assert js["aSame"] == {"same": True}


def test_assign_rejects_unknown_row_screen_or_nothing(js):
    assert "없는 폴더" in js["aNoRow"]["error"]
    assert "없는 화면" in js["aNoId"]["error"]
    assert "옮길 화면" in js["aEmpty"]["error"]


# ---------------------------------------------------------------- 제목이 따라갈 자리 · 폴더째 옮기기
def test_title_follows_the_smallest_card_offset(js):
    assert js["tMin"] == {"dx": 80, "dy": 40}, "폴더째 끌면 제목도 같은 만큼"
    assert js["tOne"] == {"dx": 0, "dy": 0}, "카드 하나를 오른쪽·아래로 = 제목 그대로"
    assert js["tUp"] == {"dx": 0, "dy": -50}, "카드를 위로 올리면 제목도 그 위로(덮지 않게)"
    assert js["tBad"] == {"dx": 0, "dy": 0} and js["tNone"] == {"dx": 0, "dy": 0}, "깨진 값 = 0"


def test_drag_plan_rounds_and_refuses_locked(js):
    assert js["dOk"] == {"moves": {"a": [20, -10], "b": [20, -10]}}
    assert js["dZero"] == {"moves": {}}, "움직이지 않았으면 기록하지 않는다"
    assert "잠긴 화면" in js["dLocked"]["error"]


def test_keys_ungroup_and_delete(js):
    assert js["k"] == ["ungroup", "ungroup", "ungroup", "delete", "delete", None, None, None, None]


def test_menu_words_tell_ungroup_from_delete(js):
    assert js["w"]["ungroup"].startswith("폴더만 풀기") and "남겨요" in js["w"]["ungroup"]
    assert js["w"]["del3"] == "폴더 지우기 — 화면 3개도 지워요" and js["w"]["del0"] == "폴더 지우기 — 화면도 지워요"


# ---------------------------------------------------------------- Python 계획(순수) — 도우미 /api/group-move
DATA = {"groups": ["로그인", "홈", "설정"], "screens": [
    {"id": "l1", "group": "로그인"}, {"id": "h1", "group": "홈"}, {"id": "s1", "group": "설정"},
    {"id": "l2", "group": "로그인"}, {"id": "s2", "group": "설정"}]}


def _d():
    return json.loads(json.dumps(DATA))


def test_plan_move_puts_screens_after_the_target_rows_screens_and_drops_emptied_name():
    d = _d()
    p = board_rows.plan_group_move(d, ["h1"], "설정")
    assert p["screens"] == ["h1"] and p["to"] == "설정" and p["emptied"] == ["홈"]
    assert [s["id"] for s in p["data"]["screens"]] == ["l1", "s1", "l2", "s2", "h1"], "설정 줄 마지막 화면 뒤"
    assert p["data"]["groups"] == ["로그인", "설정"], "빈 줄 이름은 groups 에서 뺀다"
    assert d == DATA, "입력은 그대로(순수)"


def test_plan_move_keeps_original_order_of_moved_screens_and_skips_ones_already_there():
    p = board_rows.plan_group_move(_d(), ["s2", "l1", "h1"], "로그인")
    assert p["screens"] == ["h1", "s2"], "이미 로그인 줄인 l1 은 빼고, 옮길 것은 원래 차례"
    assert [(s["id"], s["group"]) for s in p["data"]["screens"]] == [("l1", "로그인"), ("s1", "설정"), ("l2", "로그인"), ("h1", "로그인"), ("s2", "로그인")], "로그인 줄 마지막(l2) 뒤 · 다른 화면 차례 그대로"
    assert p["emptied"] == ["홈"]


def test_plan_move_same_row_is_a_no_op():
    assert board_rows.plan_group_move(_d(), ["s1"], "설정")["same"] is True


@pytest.mark.parametrize("ids,to,word,reason", [
    (["h1"], "없음", "없는 폴더", "missing"), (["zz"], "홈", "없는 화면", "missing"), ([], "홈", "옮길 화면", "invalid"),
    ("h1", "홈", "옮길 화면", "invalid"), (["h1"], None, "없는 폴더", "missing")])
def test_plan_move_rejects(ids, to, word, reason):
    with pytest.raises(board_rows.GroupError) as e:
        board_rows.plan_group_move(_d(), ids, to)
    assert word in str(e.value) and e.value.reason == reason


OK = lambda out: types.SimpleNamespace(returncode=0, stderr="")  # noqa: E731


def test_group_move_writes_once_and_restore_brings_it_back():
    o = Path(tempfile.mkdtemp(prefix="hd-rowops-out-"))
    try:
        (o / "screens.json").write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        before = (o / "screens.json").read_bytes()
        r = board_rows.group_move(o, ["h1"], "로그인", stamp="m1", build=OK)
        assert (r["group"], r["screens"], r["emptied"], r["stamp"], r["changed"]) == ("로그인", ["h1"], ["홈"], "m1", []), r
        assert json.loads((o / "screens.json").read_text(encoding="utf-8"))["groups"] == ["로그인", "설정"]
        assert (o / ".hd-history" / "m1" / "manifest.json").is_file(), "기록 = 되돌리기 한 번"
        assert "error" not in write_record.restore(o, "m1", build=OK)
        assert (o / "screens.json").read_bytes() == before
        same = board_rows.group_move(o, ["l1"], "로그인", stamp="m2", build=OK)
        assert same["stamp"] is None and not (o / ".hd-history" / "m2").exists(), "이미 그 줄 = 쓰지 않음"
        bad = board_rows.group_move(o, ["zz"], "로그인", stamp="m3", build=OK)
        assert bad["reason"] == "missing" and (o / "screens.json").read_bytes() == before, "거절 = 쓰지 않음"
    finally:
        shutil.rmtree(o, ignore_errors=True)
