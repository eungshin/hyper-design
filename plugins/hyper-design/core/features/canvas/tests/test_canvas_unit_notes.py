"""메모 목록 저장소(P3) Model — modules/notes.js 순수 함수 단위 테스트(node). 브라우저 없음.

touched(prev, next): 더하거나 빼거나 제자리에서 고친 메모의 화면만(한 번씩), 순서만 바뀐 것은 닿지 않음.
store.commit(): 지난 commit 뒤 닿은 화면 — 셸은 그 카드만 다시 그린다. parse 는 깨진 글이면 빈 목록.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

NOTES_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/notes.js', 'utf8'), {filename: 'notes.js'});
const N = globalThis.HD.notes, out = {};
const a = {id: 'a', screen: 'home', edit: 'title', value: '홈'}, b = {id: 'b', screen: 'login', note: '버튼 키우기'},
      c = {id: 'c', screen: 'pay', edit: 'link', op: 'link', to: 'done'};
const L = [a, b, c], cp = x => JSON.parse(JSON.stringify(x));
out.same = N.touched(L, cp(L));
out.reorder = N.touched(L, [c, a, b]);
out.added = N.touched(L, L.concat([{id: 'd', screen: 'login', note: 'x'}]));
out.removed = N.touched(L, [a, c]);
out.changed = N.touched(L, [a, Object.assign({}, b, {note: '버튼 줄이기'}), c]);
out.moved = N.touched(L, [a, b, Object.assign({}, c, {screen: 'cart'})]);
out.many = N.touched(L, [Object.assign({}, a, {sent: true}), {id: 'e', screen: 'home'}]);
out.fromEmpty = N.touched([], L);
// store: 제자리 고치기도 commit 이 잡는다
const S = N.store(cp(L));
out.first = S.commit();
S.find('a').value = '홈 화면';
out.inPlace = S.commit();
out.again = S.commit();
S.add({id: 'f', screen: 'cart', note: 'm'}); S.remove(n => n.id === 'c');
out.addRemove = S.commit();
S.set(S.list().filter(n => n.id !== 'b'));
out.setDrop = [S.commit(), S.list().map(n => n.id)];
S.list()[0].sent = true;
out.unsent = S.unsent().map(n => n.id);
out.find = [S.find('zz'), S.find('f').screen];
// parse · pendingOf · targets
out.parse = [N.parse(''), N.parse('{bad'), N.parse('{"a":1}'), N.parse('[{"id":"x"},null,3]')];
const P = [{screen: 's', edit: 'title', value: 'A'}, {screen: 's', edit: 'policy', index: 1, value: 'p1'}, {screen: 's', edit: 'title', value: 'B'}, {screen: 't', edit: 'title', value: 'C'}];
out.pend = [N.pendingOf(P, 's', 'title'), N.pendingOf(P, 's', 'policy', 1), N.pendingOf(P, 's', 'policy', 0), N.pendingOf(P, 'u', 'title')];
const K = N.linesKey;
out.lines = [K(L) === K(cp(L)), K(L) === K([Object.assign({}, a, {value: '다른 제목'}), Object.assign({}, b, {note: 'y'}), c]),
             K(L) === K([a, b, Object.assign({}, c, {to: 'cart'})]), K(L) === K([a, b, c, {id: 'g', screen: 'x', edit: 'delete'}]),
             K([]) === K([{id: 'h', screen: 'x', edit: 'text', value: 'v'}]), K([]) === K([{id: 'i', screen: 'new-1', edit: 'new-screen', x: 1, y: 2}])];
out.tg = [N.targets({path: 'p', text: 't', rect: null}), N.targets({targets: [{path: 'q'}], path: 'p'})];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-notes-js-"))
    try:
        (tmp / "n.js").write_text(NOTES_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "n.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_touched_only_screens_whose_notes_changed(out):
    assert out["same"] == [] and out["reorder"] == [], "같은 메모·순서만 바뀜 = 다시 그릴 카드 없음"
    assert out["added"] == ["login"] and out["removed"] == ["login"] and out["changed"] == ["login"]
    assert out["moved"] == ["pay", "cart"], "화면이 바뀐 메모는 예전·새 화면 둘 다"
    assert out["many"] == ["home", "login", "pay"], "한 화면은 한 번만"
    assert out["fromEmpty"] == ["home", "login", "pay"]


def test_store_commit_catches_in_place_edits(out):
    assert out["first"] == [], "처음 commit 은 만든 때와 같다"
    assert out["inPlace"] == ["home"] and out["again"] == []
    assert sorted(out["addRemove"]) == ["cart", "pay"]
    assert out["setDrop"] == [["login"], ["a", "f"]]
    assert out["unsent"] == ["f"] and out["find"] == [None, "cart"]


def test_lines_key_ignores_text_edits_and_memos(out):
    assert out["lines"] == [True, True, False, False, True, False], "글자·이름·메모는 선과 무관 · 잇기·삭제·빈 레이아웃은 선을 바꾼다"


def test_parse_pending_of_and_targets(out):
    assert out["parse"] == [[], [], [], [{"id": "x"}]]
    assert out["pend"] == ["B", "p1", None, None], "마지막 편집 값 · 정책은 그 줄만"
    assert out["tg"] == [[{"path": "p", "text": "t", "rect": None}], [{"path": "q"}]]
