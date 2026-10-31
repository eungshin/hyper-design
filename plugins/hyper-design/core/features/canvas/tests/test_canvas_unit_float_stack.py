"""떠 있는 층 목록 Model — modules/float-stack.js 순수 함수 단위 테스트(node). 브라우저 없음.

esc(layers): 맨 위(열린 것 중 마지막) 하나 — 쓴 글이 있어도(keep) 닫는다.
press(layers): 맨 위 하나만 본다 — 안·여는 것·무시 = 그대로, 바깥 = 닫기, 쓴 글이 있으면(keep) 남김. 그 아래 층은 닫지 않는다.
stash·take: 쓰던 글을 대상 열쇠로 하나 맡겨 두고 같은 열쇠면 한 번 돌려준다.
"""
import json, shutil, subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/float-stack.js', 'utf8'), {filename: 'float-stack.js'});
const F = globalThis.HD.floatStack, out = {};
const L = (id, open, hit, keep) => ({id, open, hit, keep: !!keep});
out.empty = [F.esc([]), F.esc(null), F.press([]), F.press(undefined), F.top([L('modal', false)])];
out.escTop = F.esc([L('modal', true), L('thread', true), L('pop', false)]);
out.escKeep = F.esc([L('modal', true), L('pop', true, 'outside', true)]);
out.pressOut = F.press([L('modal', true, 'ignore'), L('thread', true, 'outside')]);
out.pressIn = F.press([L('modal', true, 'ignore'), L('thread', true, 'inside')]);
out.pressOpener = F.press([L('thread', true, 'opener')]);
out.pressKeep = F.press([L('modal', true, 'outside'), L('pop', true, 'outside', true)]);
out.pressIgnore = F.press([L('modal', true, 'ignore')]);
out.pressModalOverlay = F.press([L('modal', true, 'outside'), L('thread', false, 'outside')]);
out.pressBad = F.press([L('thread', true, 'weird')]);
out.junk = F.press([null, 3, {open: true}, L('pop', true, 'outside')]);
let s = F.stash(null, 'e:m1', '쓰던 글');
out.stash = s;
out.takeOther = F.take(s, 'e:m2');
out.takeSame = F.take(s, 'e:m1');
out.stashEmpty = [F.stash(s, 'e:m3', '   '), F.stash(null, null, '글'), F.stash(null, 'k', 3)];
out.takeNone = F.take(null, 'k');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    p = subprocess.run([NODE, "-e", JS, "--", str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


@pytest.mark.unit
def test_esc_closes_top_open_layer_even_with_text(r):
    assert r["empty"][:2] == [None, None] and r["empty"][4] is None
    assert r["escTop"] == "thread", "열린 것 중 맨 위 하나"
    assert r["escKeep"] == "pop", "Esc 는 쓴 글이 있어도 닫는다(글은 주인이 맡겨 둔다)"


@pytest.mark.unit
def test_press_looks_at_top_layer_only(r):
    assert r["empty"][2] == {"close": None, "top": None} and r["empty"][3] == {"close": None, "top": None}
    assert r["pressOut"] == {"close": "thread", "top": "thread"}, "바깥 = 맨 위만 닫기(크게 보기는 그대로)"
    assert r["pressIn"] == {"close": None, "top": "thread"}
    assert r["pressOpener"] == {"close": None, "top": "thread"}, "여는 것(배지·핀) 누르기는 그쪽 click 이 정한다"
    assert r["pressKeep"] == {"close": None, "top": "pop"}, "쓴 글이 있으면 남고 아래(크게 보기)도 닫지 않는다"
    assert r["pressIgnore"] == {"close": None, "top": "modal"}
    assert r["pressModalOverlay"] == {"close": "modal", "top": "modal"}


@pytest.mark.unit
def test_bad_values_fall_back(r):
    assert r["pressBad"] == {"close": "thread", "top": "thread"}, "모르는 hit = 바깥"
    assert r["junk"] == {"close": "pop", "top": "pop"}, "깨진 층은 건너뛴다"


@pytest.mark.unit
def test_stash_and_take_keep_typed_text_once(r):
    assert r["stash"] == {"key": "e:m1", "text": "쓰던 글"}
    assert r["takeOther"] == {"text": None, "slot": {"key": "e:m1", "text": "쓰던 글"}}, "다른 대상이면 돌려주지 않고 그대로 둔다"
    assert r["takeSame"] == {"text": "쓰던 글", "slot": None}, "같은 대상이면 한 번 돌려준다"
    assert r["stashEmpty"][0] == {"key": "e:m1", "text": "쓰던 글"}, "빈 글은 맡기지 않는다(있던 것 그대로)"
    assert r["stashEmpty"][1] is None and r["stashEmpty"][2] is None
    assert r["takeNone"] == {"text": None, "slot": None}
