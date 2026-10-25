"""48b 바뀐 곳 보기 — 옛 화면과 새 화면의 블록 차이(순수 규칙, node, 브라우저 없음).

HD.swapDiff(swap-diff.js, Model): 두 화면 나무(View 가 DOM 에서 뽑음 — {i, t: tag, k: 짝 열쇠, x: 제 글, a: 속성 글, c: [자식]})를 견줘
새 화면에서 잠깐 강조할 요소(changed = 외곽선) · 떠오를 요소(added) · 빠진 요소(removed, 옛 나무 id)를 고른다.
- 글자만 바뀐 인라인(b·span 등)은 그것을 담은 블록을 강조 · 빠진 요소는 그 부모 블록을 강조 · 판 뿌리(body)는 강조하지 않는다
- 사이에 끼운 형제는 그것만 added(뒤 형제들이 모두 '바뀜'이 되지 않게) · 강조한 요소 안쪽은 다시 강조하지 않는다
- MAX 개를 넘으면 many(화면이 통째로 바뀜 — 강조 없음, 겹쳐 바꾸기만)
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/swap-diff.js', 'utf8'), {filename: 'swap-diff.js'});
const D = globalThis.HD.swapDiff, out = {};
// 나무 만들기: h(tag, text, kids, extra) — id 는 이름(name)으로 찾는다
function tree(spec) {
  let n = 0; const ids = {};
  function mk(s) { const [tag, name, text, kids, a] = s; const i = n++; ids[name] = i;
    return {i: i, t: tag, k: tag + (a && a.k ? a.k : ''), x: text || '', a: (a && a.a) || '', c: (kids || []).map(mk)}; }
  return {root: mk(spec), ids: ids};
}
function run(o, nw) {
  const A = tree(o), B = tree(nw), r = D.diff(A.root, B.root);
  const nameB = {}, nameA = {}; Object.keys(B.ids).forEach(k => nameB[B.ids[k]] = k); Object.keys(A.ids).forEach(k => nameA[A.ids[k]] = k);
  return {changed: r.changed.map(i => nameB[i]).sort(), added: r.added.map(i => nameB[i]).sort(), removed: r.removed.map(i => nameA[i]).sort(), many: r.many};
}
const page = (kids) => ['body', 'body', '', kids];
const list = (names, texts) => ['ul', 'ul', '', names.map((nm, j) => ['li', nm, texts[j]])];
out.MAX = D.MAX;
out.same = run(page([['h1', 'h', 'Hi'], ['p', 'p', 'a']]), page([['h1', 'h', 'Hi'], ['p', 'p', 'a']]));
out.text = run(page([['h1', 'h', 'Hi'], ['p', 'p', 'a']]), page([['h1', 'h', 'Hi'], ['p', 'p', 'b']]));
out.inline = run(page([['p', 'p', 'x', [['b', 'b', 'old']]]]), page([['p', 'p', 'x', [['b', 'b', 'new']]]]));
out.insert = run(page([list(['l1', 'l2', 'l3'], ['one', 'two', 'three'])]), page([list(['l1', 'lnew', 'l2', 'l3'], ['one', 'NEW', 'two', 'three'])]));
out.remove = run(page([list(['l1', 'l2', 'l3'], ['one', 'two', 'three'])]), page([list(['l1', 'l3'], ['one', 'three'])]));
out.attr = run(page([['img', 'img', '', [], {a: 'src=a.png'}]]), page([['img', 'img', '', [], {a: 'src=b.png'}]]));
out.nested = run(page([['section', 's', 'T', [['p', 'p', 'a']]]]), page([['section', 's', 'U', [['p', 'p', 'b']]]]));
out.addInline = run(page([['p', 'p', 'x']]), page([['p', 'p', 'x', [['span', 'sp', 'new']]]]));
out.addBlock = run(page([['h1', 'h', 'Hi']]), page([['h1', 'h', 'Hi'], ['div', 'card', '', [['p', 'cp', 'inside']]]]));
out.root = run(page([['p', 'p', 'a']]).map((v, j) => j === 2 ? 'body text' : v), page([['p', 'p', 'a']]));
out.rootRemove = run(page([['p', 'p', 'a'], ['p', 'q', 'b']]), page([['p', 'p', 'a']]));
const many = (pre) => page(Array.from({length: D.MAX + 1}, (_, j) => ['p', 'p' + j, pre + j]));
out.many = run(many('a'), many('b'));
const edge = (pre) => page(Array.from({length: D.MAX}, (_, j) => ['p', 'p' + j, pre + j]));
out.edge = run(edge('a'), edge('b'));
out.reorderKey = run(page([['div', 'x', '', [], {k: '.hero'}], ['div', 'y', 'b', [], {k: '.card'}]]), page([['div', 'x', '', [], {k: '.hero'}], ['div', 'y', 'c', [], {k: '.card'}]]));
let bad = [];
for (const [o, n] of [[null, null], [{}, null], [null, {i: 0, t: 'body', k: 'body', x: '', a: '', c: []}], [{i: 0, c: 'x'}, {i: 0, c: [null, 5]}]]) {
  try { const r = D.diff(o, n); bad.push([r.changed.length, r.added.length, r.removed.length, r.many]); } catch (e) { bad.push('throw ' + e.message); }
}
out.bad = bad;
out.inl = ['b', 'span', 'STRONG', 'p', 'button', 'a', 'img', 'li'].map(D.isInline);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.js"
        p.write_text(JS, encoding="utf-8")
        res = subprocess.run([NODE, str(p), str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


E = {"changed": [], "added": [], "removed": [], "many": False}


def test_same_screen_highlights_nothing(r):
    assert r["same"] == E


def test_text_change_highlights_that_block(r):
    assert r["text"] == dict(E, changed=["p"])


def test_inline_text_change_highlights_its_block(r):
    assert r["inline"] == dict(E, changed=["p"]), "굵은 글 한 조각이 아니라 그 문단"


def test_inserted_sibling_is_the_only_new_thing(r):
    assert r["insert"] == dict(E, added=["lnew"]), "뒤 형제들이 '바뀜'이 되지 않는다"


def test_removed_element_highlights_its_parent(r):
    assert r["remove"] == dict(E, changed=["ul"], removed=["l2"])


def test_attribute_change_counts(r):
    assert r["attr"] == dict(E, changed=["img"])


def test_highlighted_block_hides_its_inside(r):
    assert r["nested"] == dict(E, changed=["s"])


def test_added_inline_highlights_block_added_block_fades_in(r):
    assert r["addInline"] == dict(E, changed=["p"])
    assert r["addBlock"] == dict(E, added=["card"]), "새 블록만 — 그 안쪽은 따로 세지 않는다"


def test_root_is_never_highlighted(r):
    assert r["root"] == E
    assert r["rootRemove"] == dict(E, removed=["q"])


def test_too_many_changes_means_whole_screen(r):
    assert r["MAX"] == 12
    assert r["edge"]["many"] is False and len(r["edge"]["changed"]) == 12
    assert r["many"] == dict(E, many=True)


def test_different_keys_pair_by_key(r):
    assert r["reorderKey"] == dict(E, changed=["y"])


def test_broken_trees_are_empty_not_errors(r):
    assert r["bad"] == [[0, 0, 0, False]] * 4


def test_inline_tags(r):
    assert r["inl"] == [True, True, True, False, False, False, False, False]
