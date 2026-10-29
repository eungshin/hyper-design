"""읽기만인 탭(#274 후속) ViewModel — modules/read-only.js 순수 규칙 단위 테스트(node). 브라우저 없음.

읽기만인 탭은 편집을 받아 놓고 버리지 않고 처음부터 막는다: 막을 조작부(선택자) · 막을 키 · 편집 도구.
손(화면 이동)·보기·메모 글 쓰기 자체는 막지 않는다 — 저장하는 순간(추가·Enter)만 막아 쓴 글이 칸에 남는다.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['tools.js', 'read-only.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const R = globalThis.HD.readOnly, out = {};
out.controls = R.CONTROLS;
out.tools = ['hand', 'move', 'trigger', 'knife', 'memo', 'text', 'layout', 'annotate', 'nope', null].map(R.editTool);   // annotate = 메모 칸으로 합쳐 없어진 이름(2026-10-29)
const k = (o) => R.key(o);
out.keys = {
  v: k({key: 'v'}), V: k({key: 'V'}), h: k({key: 'h'}), m: k({key: 'm'}), p: k({key: 'p'}), e: k({key: 'e'}), zero: k({key: '0'}),
  del: k({key: 'Delete'}), bs: k({key: 'Backspace'}), esc: k({key: 'Escape'}),
  undo: k({key: 'z', ctrl: true}), redo: k({key: 'Z', ctrl: true, shift: true}), y: k({key: 'y', meta: true}), copy: k({key: 'c', ctrl: true}),
  altV: k({key: 'v', alt: true}),
  typingV: k({key: 'v', typing: true}), typingDel: k({key: 'Backspace', typing: true}),
  pnoteEnter: k({key: 'Enter', typing: true, field: 'pnote'}), pnoteCtrlEnter: k({key: 'Enter', ctrl: true, typing: true, field: 'pnote'}),
  teditEnter: k({key: 'Enter', typing: true, field: 'tedit'}), teditShiftEnter: k({key: 'Enter', shift: true, typing: true, field: 'tedit'}),
  otherEnter: k({key: 'Enter', typing: true, field: 'lyQ'}),
  none: [R.key(null), R.key({})]
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-ro-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_edit_tools(out):
    assert out["tools"] == [False, True, True, True, True, True, True, False, False, False], "손만 편집이 아니다 · 모르는(없어진) 도구 이름은 편집 도구가 아니다"
    assert out["keys"]["p"] is True and out["keys"]["m"] is True, "메모 칸의 두 키(P 요소 · M 화면)는 읽기 전용에서 막힌다"


def test_controls_cover_saving_buttons(out):
    c = " ".join(out["controls"])
    for sel in ("#padd", "#nsend", "#undo", "#redo", "#selbar", "#tedel", "#nclear", "#thread", "#nlist", "#lyBar", ".ly-eye", ".ly-lock"):
        assert sel in c, sel
    assert '[data-tool="hand"]' in c and ":not(" in c, "손 도구는 막지 않는다"


def test_keys_outside_typing(out):
    k = out["keys"]
    assert k["v"] and k["V"] and k["m"] and k["e"], "편집 도구 키"
    assert not k["h"] and not k["zero"] and not k["esc"], "손·맞추기·닫기는 그대로"
    assert k["del"] and k["bs"] and k["undo"] and k["redo"] and k["y"]
    assert not k["copy"] and not k["altV"]
    assert k["none"] == [False, False]


def test_typing_keeps_text_but_blocks_save(out):
    k = out["keys"]
    assert not k["typingV"] and not k["typingDel"], "글 쓰기는 막지 않는다 — 쓴 글은 칸에 남는다"
    assert k["pnoteCtrlEnter"] and not k["pnoteEnter"], "메모 칸: Ctrl+Enter(추가)만"
    assert k["teditEnter"] and not k["teditShiftEnter"], "글자 고치기: Enter(저장)만, Shift+Enter 줄바꿈은 그대로"
    assert not k["otherEnter"], "찾기 칸 등은 그대로"
