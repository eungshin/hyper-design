"""빈 레이아웃 목적(#225) — modules/edits.js 의 say.layout 과 요청문 줄바꿈 단위 테스트(node). 브라우저 없음.

say.layout(이름, id, 목적): 목적이 있으면 '목적: …'이 첫째 브리프(여러 줄 그대로), 없거나 빈칸뿐이면 예전 글 그대로.
request: 요청 글의 줄바꿈은 '요청: ' 뒤 글자 자리에 맞춘 들여 쓴 다음 줄로 남는다(한 줄 메모는 예전 형식 그대로).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/edits.js', 'utf8'), {filename: 'edits.js'});
const E = globalThis.HD.edits, out = {};
out.none = E.say.layout('결제', 'new-ab', undefined);
out.blank = E.say.layout('결제', 'new-ab', '  \n ');
out.purpose = E.say.layout('결제', 'new-ab', '  카드로 결제한다\n쿠폰은 선택 ');
const n = {id: 'x', screen: 'new-ab', path: '(새 화면)', text: '결제', intent: 'change', note: out.purpose};
out.req = E.request([n, {id: 'y', screen: 'home', path: 'body', text: 'Home', intent: 'question', note: '한 줄 메모'}], 'C:/o');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-layout-js-"))
    try:
        (tmp / "l.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "l.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


OLD = '새 화면 "결제"(new-ab)을 빈 레이아웃으로 만들기 — 내용은 이 화면에 남긴 메모를 따라 채우기'


def test_layout_without_purpose_is_unchanged(out):
    assert out["none"] == OLD and out["blank"] == OLD


def test_layout_purpose_is_first_brief_and_keeps_lines(out):
    assert out["purpose"] == ('새 화면 "결제"(new-ab)을 빈 레이아웃으로 만들기 — 목적: 카드로 결제한다\n쿠폰은 선택'
                              ' · 내용은 이 목적과 이 화면에 남긴 메모를 따라 채우기')


def test_request_keeps_line_breaks_as_indented_lines(out):
    lines = out["req"].split("\n")
    assert lines[0] == "[hyper-design 수정 요청] out=C:/o · 2건"
    assert lines[3] == '   요청: 새 화면 "결제"(new-ab)을 빈 레이아웃으로 만들기 — 목적: 카드로 결제한다'
    assert lines[4] == "       쿠폰은 선택 · 내용은 이 목적과 이 화면에 남긴 메모를 따라 채우기", "둘째 줄은 '요청: ' 글자 자리에 맞춰"
    assert lines[5].startswith("2. screen=home") and lines[7] == "   요청: 한 줄 메모", "한 줄 메모는 예전 형식 그대로"
    assert len(lines) == 8
