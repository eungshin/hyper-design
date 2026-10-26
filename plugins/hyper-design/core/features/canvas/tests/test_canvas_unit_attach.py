"""첨부 이미지 Model(R22) — modules/attach.js 순수 함수(node). 브라우저 없음.

check: 종류(PNG·JPEG·WebP·GIF)·크기(10 MB)·빈 파일 → 한국어 이유 · add/done/remove: 칩 목록(받은 배열을 바꾸지 않음, 6장 한도) ·
busy/saved: 올리는 중 수 · 메모에 남기는 모양 · lines/strip/withText: 요청 글의 '첨부 이미지: <절대 경로>' 줄(고쳐 저장해도 한 번만).
서버 말(attach_rules.LINE · MAX_BYTES)과 같은지도 본다.
"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
sys.path.insert(0, str(HERE.parent))
import attach_rules as AR  # noqa: E402

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/attach.js', 'utf8'), {filename: 'attach.js'});
const A = globalThis.HD.attach, out = {};
out.line = A.LINE; out.max = A.MAX; out.count = A.COUNT;
out.check = [A.check({type: 'image/png', size: 10, name: 'a.png'}), A.check({type: 'image/svg+xml', size: 10, name: 'a.svg'}),
             A.check({type: 'image/jpeg', size: A.MAX + 1}), A.check({type: 'image/gif', size: 0}), A.check({type: 'IMAGE/WEBP', size: A.MAX}), A.check(null)];
const l0 = [];
let r = A.add(l0, {id: 'a', name: 'a.png', type: 'image/png', size: 5, url: 'blob:a'});
out.pure = l0.length === 0;
out.added = r.list;
r = A.add(r.list, {id: 'b', name: 'b.gif', type: 'image/gif', size: 6, url: 'blob:b'});
let l = A.done(r.list, 'a', {path: 'C:\\o\\.hd-attach\\x-1.png', rel: '.hd-attach/x-1.png', type: 'image/png', size: 5});
out.busy = [A.busy(r.list), A.busy(l)];
out.saved = A.saved(l);
out.doneMissing = JSON.stringify(A.done(l, 'zz', {path: 'p'})) === JSON.stringify(l);
out.removed = A.remove(l, 'b').map(c => c.id);
let full = [];
for (let i = 0; i < A.COUNT; i++) full = A.add(full, {id: 'f' + i}).list;
out.cap = A.add(full, {id: 'over'});
out.from = A.fromSaved([{path: '/o/.hd-attach/1.png', rel: '.hd-attach/1.png', type: 'image/png', size: 3}, {path: ''}, null, 'x']);
out.fromBad = A.fromSaved(null);
const S = [{path: 'C:\\o\\.hd-attach\\x-1.png'}, {path: 'C:\\o\\.hd-attach\\x-2.jpg'}];
out.lines = A.lines(S);
out.with = A.withText('버튼을 키워 주세요  ', S);
out.again = A.withText(A.withText('버튼을 키워 주세요', S), S);
out.onlyImg = A.withText('  ', S.slice(0, 1));
out.dropped = A.withText(out.with, []);
out.strip = A.strip('위\n첨부 이미지: /a.png\n아래\n첨부 이미지: /b.png');
out.none = A.withText('그대로', []);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def res():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-attach-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_same_words_and_limit_as_the_server(res):
    assert res["line"] == AR.LINE and res["max"] == AR.MAX_BYTES


def test_check_type_size_empty(res):
    ok, svg, big, empty, upper, none = res["check"]
    assert ok is None and upper is None, "PNG·대문자 종류·한도 딱 = 받음"
    assert "PNG·JPEG·WebP·GIF" in svg and "a.svg" in svg
    assert "너무 커요" in big and "10 MB" in big
    assert empty == "빈 이미지예요" and none


def test_chip_list_add_done_remove(res):
    assert res["pure"], "받은 배열을 바꾸지 않는다"
    assert res["added"] == [{"id": "a", "name": "a.png", "type": "image/png", "size": 5, "url": "blob:a", "state": "up"}]
    assert res["busy"] == [2, 1], "저장되기 전 = 올리는 중"
    assert res["saved"] == [{"path": "C:\\o\\.hd-attach\\x-1.png", "rel": ".hd-attach/x-1.png", "type": "image/png", "size": 5, "name": "a.png"}]
    assert res["doneMissing"], "지운 칩에 늦게 온 답은 버린다"
    assert res["removed"] == ["a"]
    assert res["cap"]["why"] and len(res["cap"]["list"]) == res["count"], "한도를 넘으면 더하지 않고 이유"


def test_saved_items_come_back_as_chips(res):
    assert res["from"] == [{"id": ".hd-attach/1.png", "name": "", "type": "image/png", "size": 3, "url": "", "state": "ok",
                            "path": "/o/.hd-attach/1.png", "rel": ".hd-attach/1.png"}]
    assert res["fromBad"] == []


def test_text_lines_once(res):
    assert res["lines"] == "첨부 이미지: C:\\o\\.hd-attach\\x-1.png\n첨부 이미지: C:\\o\\.hd-attach\\x-2.jpg"
    assert res["with"] == "버튼을 키워 주세요\n" + res["lines"]
    assert res["again"] == res["with"], "고쳐 저장해도 줄은 한 번만"
    assert res["onlyImg"] == "첨부 이미지: C:\\o\\.hd-attach\\x-1.png", "글 없이 이미지만"
    assert res["dropped"] == "버튼을 키워 주세요", "이미지를 모두 빼면 줄도 빠진다"
    assert res["strip"] == "위\n아래" and res["none"] == "그대로"
