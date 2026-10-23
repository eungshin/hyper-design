"""기능 등록부(modules/features.js) — HD.feature · HD.mountAll 규칙 단위 테스트(node). 브라우저 없음.

needs 칸이 ctx 에 없으면 그 기능만 빠지고 [hd] console.error + toast, 나머지는 붙는다 · mount 가 던져도 같다 ·
같은 이름 두 번 = 뒤의 것 버림 · mountAll 두 번 = 처음 결과 · 등록 차례대로 붙는다.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

FEAT_JS = r"""
const fs = require('fs'), vm = require('vm');
const logged = [];
console.error = (m) => logged.push(String(m));
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/features.js', 'utf8'), {filename: 'features.js'});
const HD = globalThis.HD, out = {}, order = [], toasts = [];
HD.feature('a', {needs: ['$'], mount: c => { order.push('a'); return {who: 'a', has: typeof c.$}; }});
HD.feature('needsMore', {needs: ['$', 'nope', 'alsoNope'], mount: () => { order.push('needsMore'); return 1; }});
HD.feature('throws', {mount: () => { order.push('throws'); throw new Error('boom'); }});
HD.feature('a', {mount: () => { order.push('a2'); return 'second'; }});
HD.feature('b', {mount: () => { order.push('b'); return {who: 'b'}; }});
HD.feature('noMount', {needs: []});
out.names = HD.features.names();
out.missing = HD.features.missing(['$', 'x'], {$: 1});
const ctx = {$: () => null, toast: m => toasts.push(m)};
const got = HD.mountAll(ctx);
out.got = got; out.order = order; out.toasts = toasts;
out.again = HD.mountAll(ctx) === got;
out.logged = logged; out.errors = HD.features.errors();
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-feat-js-"))
    try:
        (tmp / "f.js").write_text(FEAT_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "f.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_registers_in_order_and_refuses_duplicates(out):
    assert out["names"] == ["a", "needsMore", "throws", "b"], "같은 이름 두 번·mount 없음은 등록되지 않는다"
    assert any("두 번 등록" in m and "a" in m for m in out["errors"])
    assert any("noMount" in m and "mount" in m for m in out["errors"])


def test_missing_needs_skip_only_that_feature_loudly(out):
    assert out["missing"] == ["x"]
    assert "needsMore" not in out["got"] and "needsMore" not in out["order"], "칸이 모자라면 mount 하지 않는다"
    msg = [m for m in out["logged"] if "needsMore" in m]
    assert msg and msg[0].startswith("[hd] ") and "nope, alsoNope" in msg[0], out["logged"]
    assert any("needsMore" in t for t in out["toasts"]), "사용자에게도 토스트"


def test_throwing_mount_does_not_stop_the_others(out):
    assert out["order"] == ["a", "throws", "b"], "등록 차례대로, 던진 기능 뒤도 붙는다"
    assert out["got"] == {"a": {"who": "a", "has": "function"}, "b": {"who": "b"}}
    assert any("throws" in m and "boom" in m for m in out["logged"])
    assert any("throws" in t for t in out["toasts"])


def test_mount_all_twice_returns_first_result(out):
    assert out["again"] and any("두 번 불렀" in m for m in out["errors"])
