"""글자 고치기 규칙(R52) — 순수(node, 브라우저 없음).

HD.textEdit(text-edit.js): 고치는 중 키 → 'save'|'br'|null · 두 번 누르기가 글자 고치기로 가나 · 고치는 중 다른 곳 누르기 → 'switch'|'end'|null.
palette.js 안 textKey(화면 안 그 자리 고치기 키)는 같은 규칙 — 표시 사이(/* hd-text-key */ … /* /hd-text-key */) 함수를 같은 표로 견준다.
브라우저 쪽은 test_canvas_text_edit.py.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
PALETTE = HERE.parents[2] / "foundation" / "palette.js"
NODE = shutil.which("node")

# [이름, {key, shift, ctrl, meta, alt, composing}, 기대]
KEYS = [
    ["Enter", {"key": "Enter"}, "save"],
    ["Shift+Enter", {"key": "Enter", "shift": True}, "br"],
    ["Ctrl+Enter", {"key": "Enter", "ctrl": True}, "save"],
    ["Cmd+Enter", {"key": "Enter", "meta": True}, "save"],
    ["Ctrl+Shift+Enter", {"key": "Enter", "ctrl": True, "shift": True}, "save"],
    ["Esc", {"key": "Escape"}, "save"],
    ["Shift+Esc", {"key": "Escape", "shift": True}, "save"],
    ["조합 중 Enter", {"key": "Enter", "composing": True}, None],
    ["조합 중 Esc", {"key": "Escape", "composing": True}, None],
    ["글자 a", {"key": "a"}, None],
    ["Tab", {"key": "Tab"}, None],
    ["Ctrl+Z", {"key": "z", "ctrl": True}, None],
]

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/text-edit.js', 'utf8'), {filename: 'text-edit.js'});
const T = HD.textEdit, keys = JSON.parse(fs.readFileSync(process.argv[4], 'utf8')), out = {};
out.key = keys.map(k => T.key(k[1]));
out.keyNull = [T.key(null), T.key(undefined), T.key({})];
// palette.js 안 같은 규칙 — DOM KeyboardEvent 모양(shiftKey·ctrlKey·metaKey·isComposing·keyCode 229)
const src = fs.readFileSync(process.argv[3], 'utf8'), m = /\/\* hd-text-key[^*]*\*\/([\s\S]*?)\/\* \/hd-text-key \*\//.exec(src);
out.paletteFound = !!m;
if (m) {
  const textKey = vm.runInThisContext('(function () {' + m[1] + '; return textKey; })()');
  out.palette = keys.map(k => textKey({key: k[1].key, shiftKey: !!k[1].shift, ctrlKey: !!k[1].ctrl, metaKey: !!k[1].meta, altKey: !!k[1].alt,
                                       isComposing: !!k[1].composing, keyCode: k[1].composing ? 229 : 0}));
  out.paletteIme = textKey({key: 'Process', keyCode: 229, isComposing: false});   // 옛 브라우저: 조합 중 = keyCode 229 만
}
out.dbl = [['move', 'board'], ['hand', 'board'], ['text', 'board'], ['memo', 'board'], ['move', 'modal'], ['hand', 'modal'], ['text', 'modal'], ['move', 'x'], [null, 'board']].map(a => T.dbl(a[0], a[1]));
out.press = [
  T.press({editing: true, text: true, tool: 'move'}), T.press({editing: true, text: false, tool: 'move'}),
  T.press({editing: true, text: true, tool: 'hand'}), T.press({editing: true, text: false, tool: 'hand'}),
  T.press({editing: false, text: true, tool: 'move'}), T.press({editing: true, text: true, tool: 'text'}),
  T.press({editing: true, text: true, tool: 'memo'}), T.press(null), T.press({})
];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    d = Path(tempfile.mkdtemp(prefix="hd-textedit-"))
    try:
        (d / "t.js").write_text(JS, encoding="utf-8")
        (d / "keys.json").write_text(json.dumps(KEYS), encoding="utf-8")
        p = subprocess.run([NODE, str(d / "t.js"), str(MOD), str(PALETTE), str(d / "keys.json")], capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_keys_esc_and_ctrl_enter_save_shift_enter_breaks_ime_waits(r):
    got = dict(zip([k[0] for k in KEYS], r["key"]))
    assert got == {k[0]: k[2] for k in KEYS}, got
    assert r["keyNull"] == [None, None, None], "없는 키 = 아무것도 안 함"


def test_palette_inline_keys_follow_the_same_rule(r):
    assert r["paletteFound"], "palette.js 에 /* hd-text-key */ … /* /hd-text-key */ 표시가 없다"
    assert dict(zip([k[0] for k in KEYS], r["palette"])) == {k[0]: k[2] for k in KEYS}, "palette.js textKey 가 modules/text-edit.js key 와 다르다"
    assert r["paletteIme"] is None, "keyCode 229 = 조합 중"


def test_double_click_edits_text_only_with_v_on_board_and_in_large_view(r):
    assert r["dbl"] == [True, False, False, False, True, False, False, False, False], "손(H) 두 번 누르기 = 고치기 아님(크게 보기 손 = 화면 체험, 10-29)"


def test_press_while_editing_switches_on_text_and_ends_elsewhere(r):
    assert r["press"] == ["switch", "end", None, None, None, None, None, None, None], "선택(V)만 — 손은 화면 체험·판 이동, 글자 도구는 원래 누르면 고친다"
