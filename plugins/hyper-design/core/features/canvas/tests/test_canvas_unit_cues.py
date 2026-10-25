"""보이는 고르기 안내(51-3) — 순수 규칙(node).

tools.hoverOf(tool, {only, typing}): 마우스를 올린 카드 안에서 다음 클릭이 고를 요소를 미리 그릴 방식.
  이동(V) = 그 카드만 골라져 있을 때 'click'(pickElAt 과 같은 규칙), 아니면 null. 요소 도구(L·P·T)는 hitOf 그대로.
  그 카드에서 글자를 고치는 중(typing)이면 어느 도구든 null.
blocks.chainOf(h, chain): '고르기 ▸' 목록 = 그 요소 + 조상(가까운 것부터) — 앞에 남긴 것과 상자가 같은 감싸기 요소는 건너뜀(parentPick 과 같은 판정).
blocks.tone(h, o): 요소 상자 색 — 앱 카드(o.app 또는 h.src.file) = 'app', 아니면 ''.
edits.preview: 도우미 없이 끌어 옮긴 반영 대기 메모 {edit:'move', op:'to', to} = 미리보기 {path, to}(up·down 은 그대로) · say.moveTo(to) = 그 요청 글.
layers.hoverIds(list, id): 레이어 줄에 올리면 판에 강조할 id — 화면 = 그 하나, 줄·폴더 = 그 아래 보이는 화면, 판 글 = 그 id, 숨긴 화면·모르는 id = []."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['tools.js', 'blocks.js', 'layers.js', 'edits.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const E = globalThis.HD.edits, T = globalThis.HD.tools, B = globalThis.HD.blocks, L = globalThis.HD.layers, out = {};
out.hover = {
  moveOnly: T.hoverOf('move', {only: true}), moveNot: T.hoverOf('move', {only: false}), moveNone: T.hoverOf('move'),
  moveTyping: T.hoverOf('move', {only: true, typing: true}), trig: T.hoverOf('trigger', {only: false}),
  textTyping: T.hoverOf('text', {typing: true}), text: T.hoverOf('text', {}), hand: T.hoverOf('hand', {only: true}), bogus: T.hoverOf('nope', {only: true})
};
const r = (x, y, w, h) => ({x: x, y: y, w: w, h: h});
const h = {path: 'a', rect: r(10, 10, 50, 20)};
const chain = [{path: 'w1', rect: r(10, 10, 50, 20)}, {path: 'p', rect: r(0, 0, 100, 40)}, {path: 'w2', rect: r(0, 0, 100.5, 40)}, null, {path: '', rect: r(0, 0, 1, 1)}, {path: 'sec', rect: r(0, 0, 300, 400)}];
out.chain = B.chainOf(h, chain).map(x => x.path);
out.chainBad = [B.chainOf(h, null).map(x => x.path), B.chainOf(null, chain).map(x => x.path)];
out.tone = [B.tone({}, {app: true}), B.tone({src: {file: 'App.svelte'}}, {}), B.tone({}, {app: false}), B.tone(null, null), B.tone({src: {}}, {})];
const list = [
  {kind: 'row', id: 'row:홈', name: '홈'}, {kind: 'screen', id: 's1', row: 'row:홈'}, {kind: 'screen', id: 's2', row: 'row:홈', hid: true},
  {kind: 'folder', id: 'f1', name: 'F'}, {kind: 'screen', id: 's3', folder: 'f1'}, {kind: 'text', id: '@intro'}];
out.ly = {scr: L.hoverIds(list, 's1'), hidden: L.hoverIds(list, 's2'), row: L.hoverIds(list, 'row:홈'), folder: L.hoverIds(list, 'f1'),
          text: L.hoverIds(list, '@intro'), none: L.hoverIds(list, 'zz'), bad: L.hoverIds(null, 's1')};
const mv = (op, to) => Object.assign(E.note('job', {path: 'p', text: 't'}, '', op), {edit: 'move', to: to});
out.prev = E.preview([mv('up'), mv('down'), mv('to', 2), mv('to', 'x')], 'job');
out.say = E.say.moveTo(2);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-cues-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_hover_target_follows_next_click(js):
    h = js["hover"]
    assert h["moveOnly"] == "click"                    # 이동(V) + 그 카드만 고름 = 다음 클릭이 고를 요소(누를 수 있는 것 → 그 요소)
    assert h["moveNot"] is None and h["moveNone"] is None   # 카드를 안 골랐으면 다음 클릭은 카드 고르기 — 요소 테두리 없음
    assert h["moveTyping"] is None and h["textTyping"] is None   # 글자를 고치는 카드 위에는 그리지 않는다
    assert h["trig"] == "click" and h["text"] == "leaf"   # 요소 도구는 예전 그대로
    assert h["hand"] is None and h["bogus"] is None


def test_chain_skips_same_box_wrappers(js):
    assert js["chain"] == ["a", "p", "sec"]            # w1 = a 와 같은 상자, w2 = p 와 같은 상자(1px 안), 빈 칸·path 없음은 뺀다
    assert js["chainBad"] == [["a"], []]


def test_app_tone(js):
    assert js["tone"] == ["app", "app", "", "", ""]


def test_layer_hover_ids(js):
    ly = js["ly"]
    assert ly["scr"] == ["s1"] and ly["hidden"] == []
    assert ly["row"] == ["s1"] and ly["folder"] == ["s3"]   # 줄·폴더 = 그 아래 보이는 화면
    assert ly["text"] == ["@intro"] and ly["none"] == [] and ly["bad"] == []


def test_drop_note_preview(js):
    assert js["prev"][:3] == [{"path": "p", "move": "up"}, {"path": "p", "move": "down"}, {"path": "p", "to": 2}]
    assert len(js["prev"]) == 3                         # 자리가 정수가 아니면 미리보기 없음(잘못 옮겨 보이지 않게)
    assert "3번째 자리" in js["say"]
