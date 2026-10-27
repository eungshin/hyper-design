"""R30 앱 부품 '낡음' 칩 — HD.parts.marks · same(node, 브라우저 없음). 낡음 판단은 도우미(part_stamp.py · GET /api/app-parts), 여기는 보이는 글만."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/parts.js', 'utf8'), {filename: 'parts.js'});
const P = globalThis.HD.parts, out = {};
const body = {parts: [{file: 'screens/mock-a.html', stale: true, dirty: true}, {file: 'screens/mock-b.html', stale: false},
                      {file: 'screens/mock-c.html', stale: true}], stale: ['tabs', 'dict', '', 7]};
out.m = P.marks(body);
out.bad = [P.marks(null), P.marks({}), P.marks({stale: 'tabs'}), P.marks({parts: [], stale: []})];
const many = {parts: ['a', 'b', 'c', 'd', 'e'].map(x => ({file: x + '.html', stale: true})), stale: ['s']};
out.many = P.marks(many).s.title;
out.same = [P.same(out.m, P.marks(body)), P.same(out.m, {}), P.same({}, {}), P.same(out.m, P.marks({parts: [], stale: ['tabs', 'dict']}))];
out.every = P.EVERY;
console.log(JSON.stringify(out));
"""


def run_js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-parts-js-"))
    try:
        (tmp / "p.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "p.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_marks_put_one_stale_chip_per_screen_with_the_rebuild_hint():
    out = run_js()
    assert sorted(out["m"]) == ["dict", "tabs"], "빈 글·글 아닌 id 는 버린다"
    t = out["m"]["tabs"]
    assert t["text"] == "낡음"
    assert "screens/mock-a.html (미커밋 변경 포함)" in t["title"] and "screens/mock-c.html" in t["title"] and "mock-b" not in t["title"]
    assert "hd parts --rebuild" in t["title"]
    assert out["bad"] == [{}, {}, {}, {}], "모양이 틀린 답 = 표시 없음"
    assert "외 2개" in out["many"], "부품이 많으면 셋까지만 이름"
    assert out["every"] == 60000, "60초보다 자주 묻지 않는다(도우미도 60초 캐시)"


def test_same_detects_changes_so_render_runs_only_when_marks_move():
    assert run_js()["same"] == [True, False, True, False]
