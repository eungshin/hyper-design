"""빈 레이아웃(셸 C9) — 빈 레이아웃 메모 모양 HD.edits.layout·layoutText·layoutOf·layoutId(Model)를 node 로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const E = globalThis.HD.edits, out = {};
out.id = E.layoutId(1700000000000, 0.5);
out.idWant = 'new-' + (1700000000000).toString(36).slice(-5) + (0.5).toString(36).slice(2, 4);
const n = E.layout('new-x', {x: 10, y: 20});
out.n = {screen: n.screen, path: n.path, text: n.text, edit: n.edit, value: n.value, x: n.x, y: n.y, op: n.op, note: n.note, sent: n.sent};
out.noteSame = n.note === E.say.layout('빈 레이아웃', 'new-x', undefined);
const named = E.layout('new-y', {x: 0, y: 0}, '로그인');
out.named = [named.value, named.note === E.say.layout('로그인', 'new-y', undefined)];
out.text = E.layoutText({value: 'A', screen: 's', purpose: '목적'}) === E.say.layout('A', 's', '목적');
const list = [{edit: 'text', screen: 'new-x'}, n, named];
out.of = E.layoutOf(list, 'new-y') === named; out.none = E.layoutOf(list, 'zz');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-drafts-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_layout_id(js):
    assert js["id"] == js["idWant"]


def test_layout_note_shape(js):
    n = js["n"]
    assert (n["screen"], n["path"], n["text"], n["edit"], n["value"], n["x"], n["y"], n["op"], n["sent"]) == \
        ("new-x", "(새 화면)", "빈 레이아웃", "new-screen", "빈 레이아웃", 10, 20, "new", False)
    assert js["noteSame"] and js["named"] == ["로그인", True] and js["text"]


def test_layout_of(js):
    assert js["of"] is True and js["none"] is None
