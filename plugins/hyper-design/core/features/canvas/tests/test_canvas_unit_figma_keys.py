"""Figma 고르기 키(51-2) — modules/blocks.js 순수 규칙(node).

keyAct: Enter = 'enter'(글자면 그 자리 고치기, 아니면 첫 자식) · Shift+Enter = 'parent'([ 와 같음) · Tab = 'next' · Shift+Tab = 'prev'(형제, 끝에서 돈다).
수식키(Ctrl·Cmd·Alt)가 붙으면 아니다. 다른 키는 Shift 가 붙으면 그대로 null(Alt+Shift+↑ 등).
enterOf(h): 글을 바꿀 수 있고(textOk) 글이 있는 요소 = 'text', 아니면 'down'(첫 자식 요소 고르기)."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/blocks.js', 'utf8'), {filename: 'blocks.js'});
const B = globalThis.HD.blocks, out = {};
const k = (key, o) => B.keyAct(Object.assign({key: key}, o || {}));
out.nav = [k('Enter'), k('Enter', {shift: true}), k('Tab', {code: 'Tab'}), k('Tab', {shift: true})];
out.modded = [k('Enter', {ctrl: true}), k('Enter', {alt: true}), k('Enter', {meta: true}), k('Tab', {ctrl: true}), k('Tab', {alt: true}), k('Tab', {shift: true, ctrl: true})];
out.old = [k('ArrowUp', {alt: true, shift: true}), k('[', {code: 'BracketLeft'}), k('Delete'), k('Backspace', {shift: true})];
out.enter = [B.enterOf({textOk: true, full: '시작하기', text: '시작하기'}), B.enterOf({textOk: false, full: '안 글'}), B.enterOf({textOk: true, full: '  ', text: ''}),
             B.enterOf({textOk: true, text: '짧은'}), B.enterOf(null), B.enterOf({})];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-fkeys-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_enter_and_tab_walk_the_tree(js):
    assert js["nav"] == ["enter", "parent", "next", "prev"], "Enter 안으로 · Shift+Enter 부모 · Tab/Shift+Tab 형제(Figma F2·F3·F4)"


def test_modifiers_are_not_navigation(js):
    assert js["modded"] == [None] * 6


def test_existing_keys_keep_their_meaning(js):
    assert js["old"] == [None, "parent", "remove", None]


def test_enter_edits_text_elements_and_goes_down_otherwise(js):
    assert js["enter"] == ["text", "down", "down", "text", "down", "down"]
