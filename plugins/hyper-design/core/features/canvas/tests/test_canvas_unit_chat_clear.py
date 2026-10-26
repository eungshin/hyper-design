"""R25 — 판 안 글 상자(카드 아래 글 상자·판 메모)를 고치는 동안 떠 있는 대화창이 가리면 판을 그만큼 위로(unit — HD.chat.clear).
브라우저 = test_canvas_r24_chat.py."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['annotation.js', 'memo-batch.js', 'edits.js', 'chat.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const C = globalThis.HD.chat, out = {};
// R25 대화창이 고치는 글 상자를 가리면 판을 올린다
const pane = {top: 40, bottom: 1000, left: 0, right: 1100}, dock = {top: 870, bottom: 990, left: 250, right: 890};
out.clear = [C.clear({top: 740, bottom: 900, left: 60, right: 1070}, dock, pane, 16),   // 겹침 → 900+16-870 = 46
  C.clear({top: 500, bottom: 800, left: 60, right: 1070}, dock, pane, 16),                // 이미 위
  C.clear({top: 740, bottom: 960, left: 900, right: 1070}, dock, pane, 16),               // 옆(가로로 안 겹침)
  C.clear({top: 60, bottom: 990, left: 60, right: 1070}, dock, pane, 16),                 // 너무 큼 → 위 끝이 판 위 여백까지만
  C.clear({top: 740, bottom: 900, left: 60, right: 1070}, null, pane, 16)];               // 대화창 없음(패널 안·숨김)
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-chat-r25-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- R25 대화창이 고치는 글 상자를 가리지 않게
def test_clear_moves_board_up_only_when_dock_covers(out):
    assert out["clear"][:3] == [46, 0, 0], "겹칠 때만, 상자 아래 + 여백이 대화창 위에 닿을 만큼"
    assert out["clear"][3] == 4, "너무 큰 상자는 위 끝이 판 위 여백(40+16)에 닿을 때까지만"
    assert out["clear"][4] == 0, "떠 있는 대화창이 없으면 그대로"
