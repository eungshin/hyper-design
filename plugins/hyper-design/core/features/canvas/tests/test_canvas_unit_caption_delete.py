"""카드 글 상자에서 지우기(#243, task 15) — caption.diff 의 지우기 편집 · say 글귀 · helper 가 정책 줄을 지우고 설명을 비운다.

Model(node): 비운 정책 줄 = {field:'policy', index, op:'delete', value:''} (원래 번호 그대로), 비운 설명 = '' 편집, 비운 제목 = 편집 없음,
빈 새 줄 = 버림. 도우미(브라우저·HTTP·빌드 없음, apply_edits 직접): 한 번 적용에 정책 줄 여럿 지우기(큰 번호부터) · 설명 '' · 없는 번호 = 실패 한 줄만.
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
const C = globalThis.HD.caption, S = globalThis.HD.edits.say, out = {};
const b = {title: '홈', purpose: '설명 글', policies: ['하나', '둘', '셋']};
out.twoPol = C.diff(b, {title: '홈', purpose: '설명 글', policies: ['', '둘', '  \n ']});
out.purpose = C.diff(b, {title: '홈', purpose: ' \n ', policies: ['하나', '둘', '셋']});
out.title = C.diff(b, {title: '  ', purpose: '설명 글', policies: ['하나', '둘', '셋']});
out.newEmpty = C.diff(b, {title: '홈', purpose: '설명 글', policies: ['하나', '둘', '셋', ' ']}, {allowAdd: true});
out.emptyStays = C.diff({title: '홈', purpose: '', policies: ['']}, {title: '홈', purpose: '', policies: ['']});
out.mixed = C.diff(b, {title: '홈', purpose: '설명 글', policies: ['새 하나', '', '셋']});
out.sayDel = S.field('policy', '', 1, '둘');
out.sayDelNoOld = S.field('policy', '', 1);
out.sayPurpose = S.field('purpose', '');
out.sayEdit = S.field('policy', '새', 0);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-capdel-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cleared_policy_lines_become_deletes_with_original_indexes(js):
    assert js["twoPol"] == [{"field": "policy", "index": 0, "op": "delete", "value": "", "old": "하나"},
                            {"field": "policy", "index": 2, "op": "delete", "value": "", "old": "셋"}], js["twoPol"]
    assert js["mixed"] == [{"field": "policy", "index": 0, "value": "새 하나", "old": "하나"},
                           {"field": "policy", "index": 1, "op": "delete", "value": "", "old": "둘"}], js["mixed"]


def test_cleared_purpose_is_an_empty_edit(js):
    assert js["purpose"] == [{"field": "purpose", "value": "", "old": "설명 글"}], js["purpose"]


def test_cleared_title_and_empty_new_line_are_not_edits(js):
    assert js["title"] == [], "제목은 비울 수 없다"
    assert js["newEmpty"] == [], "빈 새 줄은 버린다"
    assert js["emptyStays"] == [], "원래 빈 칸이 그대로면 편집이 아니다"


def test_say_delete_text(js):
    assert js["sayDel"] == '정책 2번째 줄 "둘" 지우기 (screens.json의 policies[1])'
    assert js["sayDelNoOld"] == "정책 2번째 줄 지우기 (screens.json의 policies[1])"
    assert js["sayPurpose"] == "화면 설명 비우기 (screens.json의 purpose)"
    assert js["sayEdit"] == '정책 1번째 줄을 "새"(으)로 바꾸기 (screens.json의 policies[0])', "바꾸기 글귀는 그대로"


# --- helper(브라우저 없음) — apply_edits 를 바로 부른다: screens.json 하나뿐인 작은 out, 다시 빌드(하위 프로세스)는 성공으로 바꿔 둔다 ---

JOB = {"id": "job", "file": "screens/job.html", "title": "일", "purpose": "일을 고른다", "policies": ["하나", "둘", "셋"]}


@pytest.fixture(scope="module")
def helper():
    sys.path.insert(0, str(SCRIPTS))
    import helper as h
    return h


@pytest.fixture(scope="module")
def outdir():
    tmp = Path(tempfile.mkdtemp(prefix="hd-capdel-"))
    yield tmp / "out"
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture()
def out(outdir, helper, monkeypatch):
    """테스트마다 screens.json 을 처음 모양으로 다시 쓰고 기록(.hd-history)을 비운다 — 같은 폴더를 모듈에서 한 번 만든다."""
    shutil.rmtree(outdir, ignore_errors=True)
    outdir.mkdir(parents=True)
    (outdir / "screens.json").write_text(json.dumps({"screens": [JOB]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(helper, "_build", lambda o: types.SimpleNamespace(returncode=0, stderr=""))
    return outdir


def _job(o):
    return next(s for s in json.loads((o / "screens.json").read_text(encoding="utf-8"))["screens"] if s["id"] == "job")


def test_helper_deletes_policy_lines_and_clears_purpose_in_one_apply(out, helper):
    res = helper.apply_edits(out, [
        {"id": "d0", "screen": "job", "edit": "policy", "op": "delete", "index": 0, "value": ""},
        {"id": "e1", "screen": "job", "edit": "policy", "index": 1, "value": "바뀐 둘째"},
        {"id": "d2", "screen": "job", "edit": "policy", "op": "delete", "index": 2, "value": ""},
        {"id": "p", "screen": "job", "edit": "purpose", "value": ""},
    ], stamp="t0")
    assert sorted(res["applied"]) == ["d0", "d2", "e1", "p"] and not res["failed"], res
    job = _job(out)
    assert job["policies"] == ["바뀐 둘째"], "원래 번호로 바꾸고, 지우기는 큰 번호부터"
    assert job["purpose"] == ""
    hist = list((out / ".hd-history").iterdir())
    assert len(hist) == 1, "한 번 적용 = 기록 하나"


def test_helper_empty_policy_value_without_op_is_a_delete(out, helper):   # 지금 셸은 op 를 싣지 않는다 — 빈 값 = 지우기
    res = helper.apply_edits(out, [{"id": "d", "screen": "job", "edit": "policy", "index": 1, "value": ""}], stamp="t1")
    assert res["applied"] == ["d"], res
    assert _job(out)["policies"] == ["하나", "셋"]


def test_helper_delete_out_of_range_fails_alone(out, helper):
    res = helper.apply_edits(out, [
        {"id": "bad", "screen": "job", "edit": "policy", "op": "delete", "index": 7, "value": ""},
        {"id": "ok", "screen": "job", "edit": "policy", "op": "delete", "index": 0, "value": ""},
    ], stamp="t2")
    assert res["applied"] == ["ok"] and [f["id"] for f in res["failed"]] == ["bad"], res
    assert _job(out)["policies"] == ["둘", "셋"]
