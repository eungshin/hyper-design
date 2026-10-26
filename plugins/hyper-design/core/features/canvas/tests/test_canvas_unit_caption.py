"""카드 아래 글 한 상자(H16 · R21) Model — modules/caption.js 순수 함수 단위 테스트(node). 브라우저 없음.

R21: 상자는 제목 + 본문(자유 글 한 칸) 둘. 본문 = purpose 하나(여러 줄). 옛 데이터의 policies 줄은 본문 끝에 '- ' 줄로 합쳐 보이고,
본문을 고쳐 저장하면 purpose 에 접혀 들어가며 policies 는 빈 목록이 된다(쓴 글은 사라지지 않는다).
body(purpose, policies) → 보일 본문 · diff(before{title,purpose,policies}, after{title,body}) → 바뀐 칸마다 편집(old 에는 원래 글).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

CAPTION_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/caption.js', 'utf8'), {filename: 'caption.js'});
const C = globalThis.HD.caption, out = {};
const b = {title: '로그인', purpose: '구글로 시작한다.\n쿠폰은 선택.', policies: []};
const old = {title: '로그인', purpose: '구글로 시작한다.', policies: ['[R8] 구글만', '  ', '쿠폰 체크는 해제']};
out.body = [C.body('설명', ['하나', ' ', '둘']), C.body('', ['하나']), C.body('설명', []), C.body('', []), C.body(null, null)];
out.same = C.diff(b, {title: '로그인', body: '구글로 시작한다.\n쿠폰은 선택.'});
out.sameSpaces = C.diff(b, {title: '  로그인 ', body: '구글로 시작한다. \n  쿠폰은 선택.  '});
out.title = C.diff(b, {title: '  로그인   ·  구글\n계속 ', body: b.purpose});
out.emptyTitle = C.diff(b, {title: '   ', body: b.purpose});
out.body1 = C.diff(b, {title: '로그인', body: '  구글로   시작.  \n\n\t 쿠폰은\t선택. '});
out.emptyBody = C.diff(b, {title: '로그인', body: ' \n '});
out.oldSame = C.diff(old, {title: '로그인', body: C.body(old.purpose, old.policies)});
out.oldTitle = C.diff(old, {title: '새 로그인', body: C.body(old.purpose, old.policies)});
out.oldFold = C.diff(old, {title: '로그인', body: C.body(old.purpose, old.policies) + '\n새 줄'});
out.oldDropPolicies = C.diff(old, {title: '로그인', body: '구글로 시작한다.'});
out.oldEmpty = C.diff(old, {title: '로그인', body: ''});
out.norm = [C.normalise('title', ' a \n b '), C.normalise('purpose', ' a  b \n  c\t d ')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-cap-js-"))
    try:
        (tmp / "cap.js").write_text(CAPTION_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "cap.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


OLDP = ["[R8] 구글만", "  ", "쿠폰 체크는 해제"]


def test_body_merges_old_policies_as_dash_lines(out):
    assert out["body"] == ["설명\n- 하나\n- 둘", "- 하나", "설명", "", ""], "옛 정책 줄은 본문 끝 '- ' 줄, 빈 줄은 버림"


def test_unchanged_is_empty(out):
    assert out["same"] == []
    assert out["sameSpaces"] == [], "빈칸만 다른 것은 바뀐 게 아니다"


def test_title_changed_is_normalised(out):
    assert out["title"] == [{"field": "title", "value": "로그인 · 구글 계속", "old": "로그인"}]


def test_emptied_title_is_not_an_edit(out):   # #243 — 제목은 비울 수 없다
    assert out["emptyTitle"] == []


def test_body_is_free_multiline_text(out):
    assert out["body1"] == [{"field": "purpose", "value": "구글로 시작.\n\n쿠폰은 선택.", "old": "구글로 시작한다.\n쿠폰은 선택."}], "줄바꿈·빈 줄 그대로"
    assert out["emptyBody"] == [{"field": "purpose", "value": "", "old": "구글로 시작한다.\n쿠폰은 선택."}], "다 지우면 빈 본문"


def test_old_policies_untouched_until_body_changes(out):
    assert out["oldSame"] == [], "열고 그대로 닫으면 옛 데이터를 건드리지 않는다"
    assert out["oldTitle"] == [{"field": "title", "value": "새 로그인", "old": "로그인"}], "제목만 고치면 본문·정책은 그대로"


def test_changed_body_folds_old_policies_into_purpose(out):
    assert out["oldFold"] == [
        {"field": "purpose", "value": "구글로 시작한다.\n- [R8] 구글만\n- 쿠폰 체크는 해제\n새 줄", "old": "구글로 시작한다."},
        {"field": "policies", "value": [], "old": OLDP},
    ], "본문을 고치면 정책 줄이 purpose 로 접히고 policies 는 빈 목록"
    assert out["oldDropPolicies"] == [{"field": "policies", "value": [], "old": OLDP}], "purpose 가 그대로면 정책 비우기만"
    assert out["oldEmpty"] == [{"field": "purpose", "value": "", "old": "구글로 시작한다."},
                               {"field": "policies", "value": [], "old": OLDP}], "다 지우면 둘 다 빈 것"


def test_normalise_rules(out):
    assert out["norm"] == ["a b", "a b\nc d"]
