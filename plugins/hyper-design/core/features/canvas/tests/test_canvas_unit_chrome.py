"""창 메뉴 보이기 설정(S1b) — modules/dock.js 의 chrome 칸 단위 테스트(node). 브라우저 없음.

대화창 보이기(chat)는 도구 막대(tools)와 같은 작업 공간 설정: 기본 보임 · chrome{part:'chat', on} 으로 끄고 켬 · hd-dock 에 저장·복구 ·
깨진 값·없는 값 = 보임. 판 아래 안내(hint)는 #khint 를 지우며 없어진 칸 — 의도는 무시하고 저장에서도 빠진다.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/dock.js', 'utf8'), {filename: 'dock.js'});
const K = globalThis.HD.dock, R = K.reduce, out = {};
const d = K.defaults();
out.def = d.chat;
const off = R(d, {type: 'chrome', part: 'chat', on: false});
out.off = off.chat; out.pure = d.chat;
out.on = R(off, {type: 'chrome', part: 'chat', on: true}).chat;
let st = {}; K.save(off, (k, v) => { st[k] = v; });
out.saved = JSON.parse(st[K.KEY]).chat; out.loaded = K.load(k => st[k]).chat;
out.reset = R(off, {type: 'reset'}).chat;
out.bareKeeps = R(off, {type: 'bare', on: true}).chat;
out.junk = [K.normalize({groups: [], chat: 'x'}).chat, K.normalize({groups: []}).chat, K.load(() => '{bad').chat];
out.hintIgnored = R(d, {type: 'chrome', part: 'hint', on: false}) === d;
out.hintDropped = 'hint' in K.normalize({groups: [], hint: false}) || 'hint' in d;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chrome-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_chat_visible_by_default_and_toggles(out):
    assert out["def"] is True, "처음엔 대화창이 보인다"
    assert out["off"] is False and out["on"] is True, "창 메뉴·숨김 단추 = chrome{part:'chat'}"
    assert out["pure"] is True, "reduce 는 원래 상태를 바꾸지 않는다"


def test_chat_hidden_survives_reload_but_reset_shows_it(out):
    assert out["saved"] is False and out["loaded"] is False, "숨김은 hd-dock 에 남아 새로고침 뒤에도 숨김"
    assert out["reset"] is True, "작업 영역 되돌리기 = 다시 보임"
    assert out["bareKeeps"] is False, "Tab(패널 모두 숨기기)은 대화창 설정을 바꾸지 않는다(bare 만 켬)"


def test_chat_broken_value_means_visible(out):
    assert out["junk"] == [True, True, True], "false 가 아닌 값·없음·깨진 저장 = 보임"


def test_hint_part_is_gone(out):
    assert out["hintIgnored"], "판 아래 안내(#khint)는 지웠다 — hint 의도는 무시"
    assert out["hintDropped"] is False, "저장 상태에도 hint 칸이 없다"
