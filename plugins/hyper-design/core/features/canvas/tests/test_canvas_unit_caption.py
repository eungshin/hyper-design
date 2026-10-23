"""카드 아래 글 한 상자(H16) Model — modules/caption.js 순수 함수 단위 테스트(node). 브라우저 없음.

diff(before, after, opts): 바뀐 칸만 편집 한 줄씩(빈칸 정리는 지금 고치기 칸과 같게), 비운 제목·설명은 편집 아님,
정책은 목록 하나로(task 31 — 바뀌면 {field:'policies'} 하나, 빈 줄 버림, 더하기 막음 없음), old 에는 원래 글.
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
const b = {title: '로그인', purpose: '구글로 시작한다.\n쿠폰은 선택.', policies: ['[R8] 구글만', '쿠폰 체크는 해제']};
const w = o => Object.assign({}, b, {policies: b.policies.slice()}, o);
out.same = C.diff(b, w({}));
out.sameSpaces = C.diff(b, w({title: '  로그인 ', purpose: '구글로 시작한다. \n  쿠폰은 선택.  '}));
out.title = C.diff(b, w({title: '  로그인   ·  구글\n계속 '}));
out.emptyTitle = C.diff(b, w({title: '   ', purpose: ' \n '}));
out.purpose = C.diff(b, w({purpose: '  구글로   시작.  \n\t 쿠폰은\t선택. '}));
out.policy = C.diff(b, w({policies: ['[R8] 구글만', '쿠폰   체크는 처음엔 해제 ']}));
out.emptyPolicy = C.diff(b, w({policies: ['', '쿠폰 체크는 해제']}));
const added = w({policies: ['[R8] 구글만', '쿠폰 체크는 해제', '', '  새 줄  ']});
out.add = C.diff(b, added);
out.many = C.diff(b, w({title: '새 제목', policies: ['구글만', '쿠폰 체크는 해제']}));
out.norm = [C.normalise('title', ' a \n b '), C.normalise('policy', 'x\t\ty'), C.normalise('purpose', ' a  b \n  c\t d ')];
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


def test_unchanged_is_empty(out):
    assert out["same"] == []
    assert out["sameSpaces"] == [], "빈칸만 다른 것은 바뀐 게 아니다"


def test_title_changed_is_normalised(out):
    assert out["title"] == [{"field": "title", "value": "로그인 · 구글 계속", "old": "로그인"}]


def test_emptied_title_is_not_an_edit_but_purpose_and_policy_are(out):   # #243 — 제목은 비울 수 없고, 설명은 '', 정책 줄은 지우기
    assert out["emptyTitle"] == [{"field": "purpose", "value": "", "old": "구글로 시작한다.\n쿠폰은 선택."}]
    assert out["emptyPolicy"] == [{"field": "policies", "value": ["쿠폰 체크는 해제"], "old": ["[R8] 구글만", "쿠폰 체크는 해제"]}], "비운 줄 = 목록에서 빠짐"


def test_purpose_keeps_newlines(out):
    assert out["purpose"] == [{"field": "purpose", "value": "구글로 시작.\n쿠폰은 선택.", "old": "구글로 시작한다.\n쿠폰은 선택."}]


OLDP = ["[R8] 구글만", "쿠폰 체크는 해제"]


def test_policy_change_is_the_whole_list(out):
    assert out["policy"] == [{"field": "policies", "value": ["[R8] 구글만", "쿠폰 체크는 처음엔 해제"], "old": OLDP}]


def test_added_line_is_in_the_list_and_empty_line_dropped(out):
    assert out["add"] == [{"field": "policies", "value": OLDP + ["새 줄"], "old": OLDP}], "빈 새 줄은 버린다"


def test_several_changes_carry_old(out):
    assert out["many"] == [
        {"field": "title", "value": "새 제목", "old": "로그인"},
        {"field": "policies", "value": ["구글만", "쿠폰 체크는 해제"], "old": OLDP},
    ]


def test_normalise_rules(out):
    assert out["norm"] == ["a b", "x y", "a b\nc d"]
