"""카드 글(셸 C8) — 원래 글 모으기 HD.caption.origOf(Model)와 view-caption cards 의 원래 글·반영 대기 값·카드 글 편집 메모를 node 로.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
globalThis.window = globalThis; globalThis.addEventListener = () => {};
for (const f of ['caption.js', 'notes.js', 'edits.js', 'view-caption.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, out = {};
const rows = [{group: 'G', screens: [{id: 'a', title: '홈', purpose: '첫 화면', policies: ['p1']}, {id: 'b'}]}];
out.orig = HD.caption.origOf(rows);
out.bad = HD.caption.origOf(null);
out.policiesCopied = out.orig.a.policies !== rows[0].screens[0].policies;
// View cards: 원래 글은 합쳐 쌓고(새 데이터에 없는 화면도 남음), 값 = 반영 대기가 이김, 고친 칸마다 편집 메모 하나
const NS = HD.notes.store([]), added = [];
const CT = HD.viewCaption.cards({$: () => null, $$: () => [], rowsEl: {}, pane: {addEventListener() {}}, notes: NS, polHtml: () => '', space: () => {},
  selected: () => null, typing: () => false, guard: () => false, closeMenus: () => {}, toast: () => {}, placed: () => {},
  layoutOf: () => null, editLayout: () => {}, note: (id, h, text) => HD.edits.note(id, h, text), add: (label, list) => added.push([label, list])});
CT.setOrig(rows);
CT.setOrig([{group: 'G', screens: [{id: 'a', title: '홈2', purpose: '', policies: []}]}]);
out.keepB = !!CT.orig('b'); out.a = CT.orig('a');
CT.commit('a', [{field: 'title', value: '새 홈', old: '홈2'}]);
out.edit = added.map(([l, list]) => [l, list.map(n => [n.edit, n.value, n.path])]);
added[0][1].forEach(n => NS.add(n));
out.values = CT.values('a');
out.blank = CT.values('zzz');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-ctext-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_orig_of_rows(js):
    assert js["orig"] == {"a": {"title": "홈", "purpose": "첫 화면", "policies": ["p1"]}, "b": {"title": "", "purpose": "", "policies": []}}
    assert js["bad"] == {} and js["policiesCopied"]


def test_set_orig_merges(js):
    assert js["keepB"] and js["a"] == {"title": "홈2", "purpose": "", "policies": []}


def test_commit_one_note_per_field_and_pending_wins(js):
    assert js["edit"] == [["카드 글", [["title", "새 홈", "screens.json > screens[id=a] > title"]]]]
    assert js["values"] == {"title": "새 홈", "purpose": "", "policies": []}
    assert js["blank"] is None
