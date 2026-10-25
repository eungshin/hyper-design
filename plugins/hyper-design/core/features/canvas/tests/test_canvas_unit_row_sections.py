"""줄 = 섹션(51-4, Figma F16·F17) — 줄 이름 바꾸기 · 줄만 걷기(그 줄 화면은 위 줄로, 첫 줄이면 아래 줄로) 계획과 검사.

Python(session.py, 순수): plan_group_rename(data, from, to) · plan_group_dissolve(data, name) → 새 screens.json 데이터 + 닿은 화면.
  잘못된 요청은 GroupError(한국어 이유, reason 'invalid'|'missing'). group_rename · group_dissolve = 쓰기 한 번(.hd-history 원본 + manifest)
  → 되살리기(restore)로 바이트 그대로 돌아온다. I/O 는 임시 폴더·가짜 빌드뿐.
JS(modules/rows.js · layers.js, 순수): HD.rows.target(names, name) · HD.rows.checkName(names, from, to) — 판에서 부르기 전 같은 규칙,
  HD.layers.rowId(name) · HD.layers.renameRow(folded, from, to) — 레이어 줄 id = 줄 이름(예전 'g'+차례), 이름을 바꾸면 접힘도 따라간다."""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import board_rows  # noqa: E402
import history  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
['rows.js', 'layers.js', 'layer-flags.js'].forEach(f => vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f}));
const R = globalThis.HD.rows, L = globalThis.HD.layers, F = globalThis.HD.layerFlags, out = {};
const N = ['로그인', '홈', '설정'];
out.tMid = R.target(N, '홈');
out.tFirst = R.target(N, '로그인');
out.tLast = R.target(N, '설정');
out.tOnly = R.target(['홈'], '홈');
out.tUnknown = R.target(N, '없음');
out.cOk = R.checkName(N, '홈', '  홈 (온보딩 이후) ');
out.cSame = R.checkName(N, '홈', '홈 ');
out.cEmpty = R.checkName(N, '홈', '   ');
out.cDup = R.checkName(N, '홈', '설정');
out.cUnknown = R.checkName(N, '없음', '새');
out.cLong = R.checkName(N, '홈', 'x'.repeat(81));
out.id = L.rowId('홈');
out.folded = L.renameRow({'row:홈': 1, 'row:설정': 1, 'f1': 1}, '홈', '메인');
out.foldedNone = L.renameRow({'row:설정': 1}, '홈', '메인');
const t = L.build([{id: L.rowId('홈'), name: '홈', screens: [{id: 'a', name: 'A'}]}], [], {hidden: {a: true}});
out.built = t.map(x => [x.kind, x.id, x.row || null]);
out.cleanOld = F.clean(JSON.stringify(['a', 'g0']), ['a']);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-rowsec-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- JS 규칙(판에서 부르기 전)
def test_js_dissolve_target_is_row_above_else_below(js):
    assert js["tMid"] == {"into": "로그인", "where": "above"}, "사용자 결정 ①: 위 줄에 합친다"
    assert js["tLast"] == {"into": "홈", "where": "above"}
    assert js["tFirst"] == {"into": "홈", "where": "below"}, "첫 줄이면 아래 줄"
    assert "하나뿐" in js["tOnly"]["error"]
    assert "없는 줄" in js["tUnknown"]["error"]


def test_js_rename_check(js):
    assert js["cOk"] == {"name": "홈 (온보딩 이후)"}, "앞뒤 빈칸은 자른다"
    assert js["cSame"] == {"name": "홈", "same": True}, "같은 이름 = 쓰지 않음"
    assert "비었" in js["cEmpty"]["error"]
    assert "이미 있어요" in js["cDup"]["error"]
    assert "없는 줄" in js["cUnknown"]["error"]
    assert "80자" in js["cLong"]["error"]


def test_js_layer_row_id_is_the_group_name_and_fold_follows_rename(js):
    assert js["id"] == "row:홈"
    assert js["built"] == [["row", "row:홈", None], ["screen", "a", "row:홈"]]
    assert js["folded"] == {"row:메인": 1, "row:설정": 1, "f1": 1}, "접힌 줄은 새 이름으로"
    assert js["foldedNone"] == {"row:설정": 1}
    assert js["cleanOld"]["ids"] == ["a"] and js["cleanOld"]["dropped"] == ["g0"], "예전 줄 id 가 숨김 목록에 있어도 걸러진다"


# ---------------------------------------------------------------- Python 계획(순수)
DATA = {"groups": ["로그인", "홈", "설정"], "screens": [
    {"id": "login", "group": "로그인"}, {"id": "home", "group": "홈"}, {"id": "set", "group": "설정"},
    {"id": "home2", "group": "홈"}, {"id": "login2", "group": "로그인"}, {"id": "x"}]}


def _d():
    return json.loads(json.dumps(DATA))


def test_plan_rename_updates_groups_and_every_screen_in_the_row():
    d = _d()
    p = board_rows.plan_group_rename(d, "홈", " 메인 ")
    assert p["data"]["groups"] == ["로그인", "메인", "설정"]
    assert [s.get("group") for s in p["data"]["screens"]] == ["로그인", "메인", "설정", "메인", "로그인", None]
    assert p["screens"] == ["home", "home2"] and p["to"] == "메인"
    assert d == DATA, "입력은 그대로(순수)"


def test_plan_rename_of_implicit_group_keeps_its_place():
    p = board_rows.plan_group_rename(_d(), "기타", "나머지")
    assert p["data"]["groups"] == ["로그인", "홈", "설정", "나머지"] and p["data"]["screens"][5]["group"] == "나머지"
    q = board_rows.plan_group_rename({"screens": [{"id": "a"}, {"id": "b", "group": "B"}]}, "기타", "A")
    assert q["data"]["groups"] == ["A", "B"], "groups 가 없던 데이터도 지금 줄 차례 그대로"


@pytest.mark.parametrize("frm,to,word,reason", [
    ("홈", "  ", "비었", "invalid"), ("홈", "설정", "이미 있어요", "invalid"), ("홈", "기타", "이미 있어요", "invalid"),
    ("없음", "새", "없는 줄", "missing"), ("홈", "x" * 81, "80자", "invalid"), (None, "새", "없는 줄", "missing")])
def test_plan_rename_rejects(frm, to, word, reason):
    with pytest.raises(board_rows.GroupError) as e:
        board_rows.plan_group_rename(_d(), frm, to)
    assert word in str(e.value) and e.value.reason == reason


def test_plan_rename_same_name_is_a_no_op():
    assert board_rows.plan_group_rename(_d(), "홈", "홈 ")["same"] is True


def test_plan_dissolve_merges_into_row_above():
    p = board_rows.plan_group_dissolve(_d(), "홈")
    assert (p["into"], p["where"], p["screens"]) == ("로그인", "above", ["home", "home2"])
    assert p["data"]["groups"] == ["로그인", "설정"]
    assert [s["id"] for s in p["data"]["screens"] if s.get("group") == "로그인"] == ["login", "login2", "home", "home2"], \
        "합친 화면은 위 줄 화면 뒤에(빌드가 같은 차례로 그린다)"
    assert [s["id"] for s in p["data"]["screens"]] == ["login", "set", "login2", "home", "home2", "x"], "다른 줄 화면 차례는 그대로"


def test_plan_dissolve_first_row_goes_below():
    p = board_rows.plan_group_dissolve(_d(), "로그인")
    assert (p["into"], p["where"]) == ("홈", "below")
    assert [s["id"] for s in p["data"]["screens"] if s.get("group") == "홈"] == ["login", "login2", "home", "home2"], "아래 줄 화면 앞에"
    assert p["data"]["groups"] == ["홈", "설정"]


def test_plan_dissolve_skips_empty_group_names():
    d = {"groups": ["A", "빈", "B"], "screens": [{"id": "a", "group": "A"}, {"id": "b", "group": "B"}]}
    p = board_rows.plan_group_dissolve(d, "B")
    assert p["into"] == "A", "판에 없는(화면 0) 줄은 위 줄이 아니다"


def test_plan_dissolve_rejects():
    with pytest.raises(board_rows.GroupError) as e:
        board_rows.plan_group_dissolve({"groups": ["A"], "screens": [{"id": "a", "group": "A"}]}, "A")
    assert "하나뿐" in str(e.value) and e.value.reason == "invalid"
    with pytest.raises(board_rows.GroupError) as e:
        board_rows.plan_group_dissolve(_d(), "없음")
    assert "없는 줄" in str(e.value) and e.value.reason == "missing"


# ---------------------------------------------------------------- 쓰기 한 번 + 되살리기
def _out():
    o = Path(tempfile.mkdtemp(prefix="hd-rowsec-out-"))
    (o / "screens.json").write_text(json.dumps(DATA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return o


OK = lambda out: types.SimpleNamespace(returncode=0, stderr="")  # noqa: E731


def test_group_rename_writes_once_and_restore_brings_it_back():
    o = _out()
    try:
        before = (o / "screens.json").read_bytes()
        r = board_rows.group_rename(o, "홈", "메인", stamp="r1", build=OK)
        assert r["stamp"] == "r1" and r["group"] == "메인" and r["screens"] == ["home", "home2"], r
        d = json.loads((o / "screens.json").read_text(encoding="utf-8"))
        assert d["groups"] == ["로그인", "메인", "설정"] and d["screens"][1]["group"] == "메인"
        assert (o / ".hd-history" / "r1" / "manifest.json").is_file(), "기록 = 되돌리기 한 번"
        assert "error" not in write_record.restore(o, "r1", build=OK)
        assert (o / "screens.json").read_bytes() == before
    finally:
        shutil.rmtree(o, ignore_errors=True)


def test_group_dissolve_writes_once_and_restore_brings_it_back():
    o = _out()
    try:
        before = (o / "screens.json").read_bytes()
        r = board_rows.group_dissolve(o, "설정", stamp="d1", build=OK)
        assert (r["into"], r["where"], r["screens"], r["stamp"]) == ("홈", "above", ["set"], "d1"), r
        assert json.loads((o / "screens.json").read_text(encoding="utf-8"))["groups"] == ["로그인", "홈"]
        assert "error" not in write_record.restore(o, "d1", build=OK)
        assert (o / "screens.json").read_bytes() == before
    finally:
        shutil.rmtree(o, ignore_errors=True)


def test_group_ops_refuse_without_writing():
    o = _out()
    try:
        before = (o / "screens.json").read_bytes()
        r = board_rows.group_rename(o, "홈", "설정", build=OK)
        assert r["reason"] == "invalid" and "이미 있어요" in r["error"] and history._code(r) == 400
        r = board_rows.group_dissolve(o, "없음", build=OK)
        assert r["reason"] == "missing" and history._code(r) == 404
        r = board_rows.group_rename(o, "홈", "홈", build=OK)
        assert r["stamp"] is None and "error" not in r, "같은 이름 = 쓰지 않음"
        assert (o / "screens.json").read_bytes() == before and not (o / ".hd-history").exists()
    finally:
        shutil.rmtree(o, ignore_errors=True)
