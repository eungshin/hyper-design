"""옛 정책 목록(task 31) — R21 부터 카드 글 상자는 제목 + 본문 한 칸이고, 정책 줄은 본문에 합쳐 보인다(test_canvas_unit_caption.py).
남은 것: 사용자 상태 파일의 옛 반영 대기 메모(policy[i]·policies)를 읽는 규칙과, 본문에 접을 때 쓰는 policies [] 편집.

Model(node): caption.pending(메모, id, 원래) → 반영 대기 목록(옛 줄 편집 위에 새 목록이 이김)
· caption.shown → 판의 카드 아래 글에 무엇을 보일지(고르지 않은 카드 = 제목만 + 고친 표시) · edits.say.field('policies') · edits.directOf.
도우미(apply_edits 직접, 브라우저·빌드 없음): policies 연산 = 목록 통째로 바꿈 · 검사(글 목록·50줄·500자) 거절 · 옛 policy 연산도 그대로.
"""
import json, shutil, subprocess, sys, tempfile, types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const n of ['caption', 'edits']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + n + '.js', 'utf8'), {filename: n + '.js'});
const C = globalThis.HD.caption, E = globalThis.HD.edits, out = {};
const P = [{screen: 's', edit: 'policy', index: 1, value: '바뀐 둘'}, {screen: 's', edit: 'policy', index: 0, op: 'delete', value: ''},
           {screen: 't', edit: 'policies', value: ['남의 것']}];
out.pendOld = C.pending(P, 's', ['하나', '둘', '셋']);
out.pendNone = C.pending(P, 'u', ['하나']);
out.pendNew = C.pending(P.concat([{screen: 's', edit: 'policies', value: ['새 목록']}]), 's', ['하나', '둘', '셋']);
out.pendNewThenOld = C.pending([{screen: 's', edit: 'policies', value: ['가', '나']}, {screen: 's', edit: 'policy', index: 0, value: '옛'}], 's', ['하나']);
out.shown = [
  C.shown({selected: false, blank: false, pending: {}}),
  C.shown({selected: true, blank: false, pending: {}}),
  C.shown({selected: false, blank: false, pending: {purpose: true}}),
  C.shown({selected: false, blank: false, pending: {policies: true}}),
  C.shown({selected: false, blank: true, pending: {}}),
  C.shown({selected: true, blank: false, pending: {purpose: true, policies: true}}),
];
out.say = E.say.field('policies', ['구글만', '쿠폰은 선택'], null, ['구글만']);
out.sayEmpty = E.say.field('policies', [], null, ['하나']);
out.direct = [E.directOf({edit: 'policies'}), E.directOf({edit: 'policy'})];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-caplist-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


OLD = ["하나", "둘", "셋"]


def test_pending_list_newest_list_wins_over_old_line_edits(js):
    assert js["pendOld"] == ["바뀐 둘", "셋"], "옛 줄 편집(바꾸기·지우기)은 원래 번호로"
    assert js["pendNone"] is None, "반영 대기가 없으면 null"
    assert js["pendNew"] == ["새 목록"]
    assert js["pendNewThenOld"] == ["가", "나"], "새 목록 뒤의 옛 줄 편집은 무시(번호가 원래 목록 기준이라)"


def test_shown_rule(js):
    hid, full = {"purpose": False, "policies": False}, {"purpose": True, "policies": True}
    assert js["shown"][0] == dict(hid, mark=False), "고르지 않은 카드 = 제목만"
    assert js["shown"][1] == dict(full, mark=False), "고르면 본문이 보인다"
    assert js["shown"][2] == dict(hid, mark=True) and js["shown"][3] == dict(hid, mark=True), "접힌 카드에도 고친 표시"
    assert js["shown"][4] == dict(full, mark=False), "빈 레이아웃은 늘 이름·목적"
    assert js["shown"][5] == dict(full, mark=False), "펼치면 표시는 칸 자체(pend)"


def test_say_policies_lists_the_whole_new_list(js):
    assert js["say"] == "정책 줄 바꾸기: ① 구글만 ② 쿠폰은 선택 (screens.json의 policies 전체)"
    assert js["sayEmpty"] == "정책 줄 모두 지우기 (screens.json의 policies 전체)"
    assert js["direct"] == [True, True]


# --- helper(브라우저 없음) — apply_edits 직접, 다시 빌드는 성공으로 바꿔 둔다 ---

JOB = {"id": "job", "file": "screens/job.html", "title": "일", "purpose": "일을 고른다", "policies": OLD}


@pytest.fixture(scope="module")
def helper():
    sys.path.insert(0, str(SCRIPTS))
    import helper as h
    return h


@pytest.fixture()
def out(helper, monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="hd-caplist-"))
    o = tmp / "out"
    o.mkdir()
    (o / "screens.json").write_text(json.dumps({"screens": [JOB]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def _pol(o):
    return next(s for s in json.loads((o / "screens.json").read_text(encoding="utf-8"))["screens"] if s["id"] == "job")["policies"]


def test_helper_policies_replaces_the_whole_list(out, helper):
    res = helper.apply_edits(out, [{"id": "p", "screen": "job", "edit": "policies", "value": ["셋", "가운데", "하나"]}], stamp="t0")
    assert res["applied"] == ["p"] and not res["failed"], res
    assert _pol(out) == ["셋", "가운데", "하나"]


def test_helper_policies_validation_refuses_in_korean(out, helper):
    bad = [{"id": "s", "screen": "job", "edit": "policies", "value": "한 줄 글"},
           {"id": "n", "screen": "job", "edit": "policies", "value": ["가", 3]},
           {"id": "l", "screen": "job", "edit": "policies", "value": ["가"] * 51},
           {"id": "c", "screen": "job", "edit": "policies", "value": ["가" * 501]}]
    res = helper.apply_edits(out, bad, stamp="t1")
    assert res["applied"] == [] and [f["id"] for f in res["failed"]] == ["s", "n", "l", "c"], res
    assert all("정책" in f["reason"] for f in res["failed"]), res
    assert _pol(out) == OLD, "거절하면 그대로"


def test_helper_old_policy_ops_still_apply(out, helper):   # 사용자 상태 파일에 남은 옛 반영 대기
    res = helper.apply_edits(out, [{"id": "e", "screen": "job", "edit": "policy", "index": 1, "value": "바뀐 둘"},
                                   {"id": "d", "screen": "job", "edit": "policy", "op": "delete", "index": 0, "value": ""}], stamp="t2")
    assert sorted(res["applied"]) == ["d", "e"], res
    assert _pol(out) == ["바뀐 둘", "셋"]


def test_helper_new_list_after_old_line_ops_wins(out, helper):
    res = helper.apply_edits(out, [{"id": "d", "screen": "job", "edit": "policy", "op": "delete", "index": 0, "value": ""},
                                   {"id": "p", "screen": "job", "edit": "policies", "value": ["둘", "새"]}], stamp="t3")
    assert sorted(res["applied"]) == ["d", "p"], res
    assert _pol(out) == ["둘", "새"], "앞선 줄 지우기가 새 목록을 지우면 안 된다"
