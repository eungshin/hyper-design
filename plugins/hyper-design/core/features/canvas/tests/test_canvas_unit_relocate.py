"""다시 찾은 메모 자리(#285) Model — modules/relocate.js 순수 함수 단위 테스트(node). 브라우저 없음.

pinnable(t): 핀이 될 대상(path 가 있고 body·'(새 화면)' 아님). key(id, i) = 'id:i'.
lost(id, targets, map): 화면이 hd-located 로 답한 자리(map{key: {rect, how}})에서 핀이 될 대상 하나라도 how === 'none'(같은 요소가
여럿이거나 없음 — task 41) = 요소를 찾을 수 없음. 답이 없으면(map 없음·그 키 없음) 아직 모름 = false.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/relocate.js', 'utf8'), {filename: 'relocate.js'});
const L = globalThis.HD.relocate, out = {};
const btn = {path: 'button.pay', text: '결제'}, body = {path: 'body'}, fresh = {path: '(새 화면)'}, none = {path: ''};
out.pinnable = [btn, body, fresh, none, null].map(L.pinnable);
out.key = L.key('m1', 2);
const R = {x: 1, y: 2, w: 3, h: 4};
out.found = L.lost('m1', [btn], {'m1:0': {rect: R, how: 'path'}});
out.quote = L.lost('m1', [btn], {'m1:0': {rect: R, how: 'quote'}});
out.gone = L.lost('m1', [btn], {'m1:0': {rect: null, how: 'none'}});
out.second = L.lost('m1', [btn, btn], {'m1:0': {rect: R, how: 'path'}, 'm1:1': {rect: null, how: 'none'}});
out.noAnswer = [L.lost('m1', [btn], null), L.lost('m1', [btn], {})];
out.bodyNone = L.lost('m1', [body], {'m1:0': {rect: null, how: 'none'}});
out.empty = L.lost('m1', [], {'m1:0': {rect: null, how: 'none'}});
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-reloc-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_pinnable_and_key(out):
    assert out["pinnable"] == [True, False, False, False, False]
    assert out["key"] == "m1:2"


def test_lost_only_when_screen_answered_none(out):
    assert out["found"] is False and out["quote"] is False
    assert out["gone"] is True, "같은 요소가 여럿이거나 없음(how none) = 요소를 찾을 수 없음"
    assert out["second"] is True, "대상 중 하나라도 못 찾으면"
    assert out["noAnswer"] == [False, False], "아직 답이 없으면 모름 — 표시하지 않는다"
    assert out["bodyNone"] is False and out["empty"] is False, "핀이 될 대상이 아니면 잃을 것도 없다"
