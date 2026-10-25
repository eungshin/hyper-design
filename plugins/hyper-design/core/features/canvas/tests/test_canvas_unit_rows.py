"""판 줄 맞추기(51-1, FINDINGS D) — 화면을 다 지운 줄은 제목째 바로 없어지고, 새로 생긴 줄은 제자리에 끼워진다.

HD.rows.plan(have, want) (modules/rows.js, 순수): have = 지금 판의 줄 [{group, n}](n = 그 줄 카드 수, 빈 레이아웃 포함), want = 새 데이터의 줄 이름
(nd.rows 차례) → {remove: [이름], insert: [{group, before: 이름|null}]}. 빈 줄(n 0)이면서 새 데이터에 없으면 걷는다. 카드가 남은 줄은
새 데이터에 없어도 둔다. want 에 있는데 판에 없는 줄은 want 에서 그 뒤에 오는 남은 줄 앞에(없으면 끝에) 끼운다.
session.emptied_groups(groups, before, after): 지우기로 비게 된 group 이름만 groups 에서 뺀다(원래 빈 이름은 그대로).
delete_screens 는 그것을 쓰고, 되살리기는 screens.json 을 통째로 돌려 groups 도 돌아온다. I/O 는 임시 폴더·가짜 빌드뿐."""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import session  # noqa: E402

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/rows.js', 'utf8'), {filename: 'rows.js'});
const R = globalThis.HD.rows, out = {};
const row = (g, n) => ({group: g, n: n});
out.same = R.plan([row('A', 2), row('B', 1)], ['A', 'B']);
out.emptied = R.plan([row('A', 2), row('B', 0), row('C', 1)], ['A', 'C']);
out.emptyButWanted = R.plan([row('A', 0)], ['A']);
out.cardsLeft = R.plan([row('A', 1), row('X', 1)], ['A']);
out.newMiddle = R.plan([row('A', 1), row('C', 1)], ['A', 'B', 'C']);
out.newEnds = R.plan([row('B', 1)], ['A', 'B', 'C', 'D']);
out.swapOut = R.plan([row('A', 0), row('C', 1)], ['B', 'C']);
out.bad = R.plan(null, undefined);
// 옮긴 카드 자리의 줄 이름 옮기기(S1c) — 줄 이름 바꾸기·줄만 걷기 뒤 지금 줄 이름으로
const pos = {a: {dx: 10, dy: 5, g: '옛'}, b: {dx: -3, dy: 0, g: '걷힘'}, c: {dx: 1, dy: 1, g: '그대로'}, gone: {dx: 9, dy: 9, g: '옛'}};
out.rekey = R.rekeyPos(pos, {a: '새', b: '위 줄', c: '그대로'});
out.rekeySame = R.rekeyPos({c: {dx: 1, dy: 1, g: '그대로'}}, {c: '그대로'});
out.rekeyBad = R.rekeyPos(null, null);
out.posUntouched = pos.a.g;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-rows-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_plan_keeps_rows_that_match(js):
    assert js["same"] == {"remove": [], "insert": []}


def test_plan_removes_only_empty_rows_missing_from_data(js):
    assert js["emptied"] == {"remove": ["B"], "insert": []}, "화면을 다 지운 줄 = 제목째 걷기"
    assert js["emptyButWanted"] == {"remove": [], "insert": []}, "데이터에 화면이 있으면 남긴다"
    assert js["cardsLeft"] == {"remove": [], "insert": []}, "카드(빈 레이아웃 포함)가 남은 줄은 두기"


def test_plan_inserts_new_rows_in_data_order(js):
    assert js["newMiddle"] == {"remove": [], "insert": [{"group": "B", "before": "C"}]}
    assert js["newEnds"] == {"remove": [], "insert": [{"group": "A", "before": "B"}, {"group": "C", "before": None}, {"group": "D", "before": None}]}
    assert js["swapOut"] == {"remove": ["A"], "insert": [{"group": "B", "before": "C"}]}, "걷은 줄은 기준이 되지 않는다"


def test_plan_bad_input_is_a_no_op(js):
    assert js["bad"] == {"remove": [], "insert": []}


def test_emptied_groups_drops_only_names_that_became_empty():
    before = [{"id": "a1", "group": "A"}, {"id": "b1", "group": "B"}, {"id": "b2", "group": "B"}, {"id": "x"}]
    after = [s for s in before if s["id"] in ("b2", "x")]
    assert session.emptied_groups(["A", "B", "C", "기타"], before, after) == ["B", "C", "기타"], "C 는 원래 비어 있었다 — 그대로"
    after2 = [s for s in before if s["id"] in ("a1", "b1", "b2")]
    assert session.emptied_groups(["A", "B", "기타"], before, after2) == ["A", "B"], "group 없는 화면 = '기타'"
    assert session.emptied_groups(None, before, after) is None, "groups 가 없으면 그대로"


def _out():
    o = Path(tempfile.mkdtemp(prefix="hd-rows-out-"))
    (o / "screens").mkdir()
    for i in ("a1", "b1", "b2"):
        (o / "screens" / f"{i}.html").write_text(f"<main><h1>{i}</h1></main>", encoding="utf-8")
    sj = {"groups": ["A", "B", "C"], "screens": [{"id": "a1", "group": "A"}, {"id": "b1", "group": "B"}, {"id": "b2", "group": "B"}]}
    (o / "screens.json").write_text(json.dumps(sj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return o


def test_delete_screens_drops_emptied_group_and_restore_brings_it_back():
    o = _out()
    ok = lambda out: types.SimpleNamespace(returncode=0, stderr="")
    try:
        before = (o / "screens.json").read_bytes()
        res = session.delete_screens(o, ["a1"], stamp="d1", build=ok)
        assert res["deleted"] == ["a1"], res
        assert json.loads((o / "screens.json").read_text(encoding="utf-8"))["groups"] == ["B", "C"], "비게 된 A 만 뺀다"
        res = session.delete_screens(o, ["b1"], stamp="d2", build=ok)
        assert json.loads((o / "screens.json").read_text(encoding="utf-8"))["groups"] == ["B", "C"], "b2 가 남은 B 는 둔다"
        assert "error" not in session.restore(o, "d2", build=ok)
        r = session.restore(o, "d1", build=ok)
        assert "error" not in r, r
        assert (o / "screens.json").read_bytes() == before, "되살리기 = groups 까지 바이트 그대로"
    finally:
        shutil.rmtree(o, ignore_errors=True)


def test_rekey_pos_follows_renamed_or_dissolved_row(js):
    r = js["rekey"]
    assert r["pos"]["a"] == {"dx": 10, "dy": 5, "g": "새"}, "이름 바꾼 줄 = 새 이름으로(자리 그대로)"
    assert r["pos"]["b"] == {"dx": -3, "dy": 0, "g": "위 줄"}, "걷은 줄의 카드 = 들어간 줄 이름으로"
    assert r["pos"]["c"] == {"dx": 1, "dy": 1, "g": "그대로"}
    assert r["pos"]["gone"] == {"dx": 9, "dy": 9, "g": "옛"}, "판에 없는 카드(떼어 둠)는 건드리지 않는다"
    assert r["changed"] is True and js["rekeySame"]["changed"] is False
    assert js["rekeyBad"] == {"pos": {}, "changed": False}
    assert js["posUntouched"] == "옛", "입력은 고치지 않는다"
