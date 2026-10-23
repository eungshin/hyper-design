"""카드 글 상자에서 지우기(#243, task 15) — caption.diff 의 지우기 편집 · say 글귀 · helper 가 정책 줄을 지우고 설명을 비운다.

Model(node): 비운 정책 줄 = {field:'policy', index, op:'delete', value:''} (원래 번호 그대로), 비운 설명 = '' 편집, 비운 제목 = 편집 없음,
빈 새 줄 = 버림. 도우미(브라우저 없음): 한 번 적용에 정책 줄 여럿 지우기(큰 번호부터) · 설명 '' · 없는 번호 = 실패 한 줄만.
"""
import json, os, shutil, subprocess, sys, tempfile, threading, urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
REPO = SCRIPTS.parents[4]
NODE = shutil.which("node")
DAYFINE = REPO / "runs" / "dayfine-onboarding-v1" / "out"

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


# --- helper(브라우저 없음) ---

@pytest.fixture()
def out():
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-capdel-"))
    o = tmp / "out"
    shutil.copytree(DAYFINE, o)
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(o)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr
    yield o
    shutil.rmtree(tmp, ignore_errors=True)


def _helper():
    sys.path.insert(0, str(SCRIPTS))
    import helper
    return helper


def _job(o):
    return next(s for s in json.loads((o / "screens.json").read_text(encoding="utf-8"))["screens"] if s["id"] == "job")


def _post(url, body, token):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-HD-Token": token})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read())


def test_helper_deletes_policy_lines_and_clears_purpose_over_http(out):
    helper = _helper()
    pol = _job(out)["policies"]
    assert len(pol) == 3
    srv = helper.make_server(out, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = srv.url.split("/index.html")[0]
    try:
        code, res = _post(base + "/api/apply", {"edits": [
            {"id": "d0", "screen": "job", "edit": "policy", "op": "delete", "index": 0, "value": ""},
            {"id": "e1", "screen": "job", "edit": "policy", "index": 1, "value": "바뀐 둘째"},
            {"id": "d2", "screen": "job", "edit": "policy", "op": "delete", "index": 2, "value": ""},
            {"id": "p", "screen": "job", "edit": "purpose", "value": ""},
        ]}, srv.token)
    finally:
        srv.shutdown(); srv.server_close()
    assert code == 200 and sorted(res["applied"]) == ["d0", "d2", "e1", "p"] and not res["failed"], res
    job = _job(out)
    assert job["policies"] == ["바뀐 둘째"], "원래 번호로 바꾸고, 지우기는 큰 번호부터"
    assert job["purpose"] == ""
    hist = list((out / ".hd-history").iterdir())
    assert len(hist) == 1, "한 번 적용 = 기록 하나"


def test_helper_empty_policy_value_without_op_is_a_delete(out):   # 지금 셸은 op 를 싣지 않는다 — 빈 값 = 지우기
    res = _helper().apply_edits(out, [{"id": "d", "screen": "job", "edit": "policy", "index": 1, "value": ""}], stamp="t1")
    assert res["applied"] == ["d"], res
    assert len(_job(out)["policies"]) == 2


def test_helper_delete_out_of_range_fails_alone(out):
    pol = _job(out)["policies"]
    res = _helper().apply_edits(out, [
        {"id": "bad", "screen": "job", "edit": "policy", "op": "delete", "index": 7, "value": ""},
        {"id": "ok", "screen": "job", "edit": "policy", "op": "delete", "index": 0, "value": ""},
    ], stamp="t2")
    assert res["applied"] == ["ok"] and [f["id"] for f in res["failed"]] == ["bad"], res
    assert _job(out)["policies"] == pol[1:]
