"""숨긴·잠근 화면 표시 정리(polish-1) — layer-flags.js(node). 저장된 id 목록을 지금 있는 화면 + 판 글 레이어(@intro·@foot·@dscard)에 맞춰
거르고, 걸러졌거나 깨졌으면 셸이 깨끗한 목록을 다시 쓰게 changed 를 낸다. 없어진 화면이 같은 id 로 다시 생겨도 숨김·잠금이 되살아나지 않는다."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/layer-flags.js', 'utf8'), {filename: 'layer-flags.js'});
const F = globalThis.HD.layerFlags, out = {};
out.stale = F.clean('["a","gone","b"]', ['a', 'b', 'c']);
out.board = F.clean('["@intro","@foot","@dscard","@other"]', ['a']);
out.same = F.clean('["b","a"]', ['a', 'b']);
out.none = F.clean(null, ['a']);
out.broken = F.clean('{nope', ['a']);
out.notList = F.clean('{"a":1}', ['a']);
out.junk = F.clean('["a", 3, null, "a", "", {"x":1}]', ['a']);
out.live = F.live([{screens: [{id: 'a'}, {id: 'b'}]}, {screens: [{id: 'c'}]}, {}], [{edit: 'new-screen', screen: 'new-1'}, {edit: 'text', screen: 'zz'}, null]);
out.liveEmpty = F.live(null, null);
// 그대로 다시: b 숨김·잠금 → b 를 지우고 다시 읽기(정리해 다시 씀) → b 를 같은 id 로 다시 만들고 읽기
const store = {};
store.h = JSON.stringify(['b']); store.l = JSON.stringify(['b']);
let r = F.clean(store.h, ['a']); if (r.changed) store.h = JSON.stringify(r.ids);
let q = F.clean(store.l, ['a']); if (q.changed) store.l = JSON.stringify(q.ids);
out.afterDelete = [store.h, store.l];
out.afterRecreate = [F.clean(store.h, ['a', 'b']).set.b || 0, F.clean(store.l, ['a', 'b']).set.b || 0];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-layer-flags-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_stale_ids_are_dropped_and_marked_for_write_back(js):
    s = js["stale"]
    assert s["ids"] == ["a", "b"] and s["set"] == {"a": 1, "b": 1} and s["dropped"] == ["gone"] and s["changed"] is True and s["bad"] is False, s


def test_board_text_layers_stay_live(js):
    b = js["board"]
    assert b["ids"] == ["@intro", "@foot", "@dscard"] and b["dropped"] == ["@other"], b


def test_clean_list_is_left_alone(js):
    assert js["same"]["ids"] == ["b", "a"] and js["same"]["changed"] is False, js["same"]
    assert js["none"] == {"ids": [], "set": {}, "dropped": [], "changed": False, "bad": False}, "저장값 없음 = 빈 목록, 쓰지 않음"


def test_broken_or_non_list_value_falls_back_to_empty_and_is_rewritten(js):
    for k in ("broken", "notList"):
        assert js[k]["ids"] == [] and js[k]["bad"] is True and js[k]["changed"] is True, (k, js[k])


def test_duplicates_and_non_string_ids_are_removed(js):
    assert js["junk"]["ids"] == ["a"] and js["junk"]["changed"] is True, js["junk"]


def test_live_ids_are_screens_plus_draft_layouts_plus_board_texts(js):
    assert js["live"] == ["a", "b", "c", "new-1", "@intro", "@foot", "@dscard"], js["live"]
    assert js["liveEmpty"] == ["@intro", "@foot", "@dscard"]


def test_recreated_screen_with_the_same_id_is_not_hidden_or_locked(js):
    assert js["afterDelete"] == ["[]", "[]"], ("지운 화면의 id 는 저장소에서도 빠진다", js["afterDelete"])
    assert js["afterRecreate"] == [0, 0], js["afterRecreate"]
