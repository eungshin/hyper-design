"""R25 — 판 메모(board-notes)를 'AI에게'(R27 F19 — 고르기만으로는 아님)로 넣으면 대화창에 노트 칩, 보내면 요청 글 끝에 '노트:' 줄(가까운 화면 이름), 칩을 빼면 빠짐(unit — modules/chat.js).
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
const title = id => ({pay: '결제', done: '완료'})[id] || null;
const notes = [{id: 'bn1', text: '버튼을 키워 주세요\n둘째 줄', near: 'pay'}, {id: 'bn2', text: '  ', near: null}, {id: 'bn3', text: '여백이 너무 넓어요 — 전체적으로 줄이기', near: null}];
out.chips = C.chips({ids: ['done'], titleOf: title, els: [], notes: notes});
out.scope = [C.scope(out.chips), C.scope(out.chips.filter(c => c.kind === 'note')), C.placeholder(out.chips.filter(c => c.kind === 'note'))];
let k = 0; const mk = () => 'm' + (++k);
out.withScreen = C.build(out.chips, '이거 반영해 줘', {first: 'pay', titleOf: title}, mk).memos.map(m => ({screen: m.screen, scope: m.scope, note: m.note}));
k = 0; out.onlyNotes = C.build(out.chips.filter(c => c.kind === 'note'), '   ', {first: 'pay', titleOf: title}, mk);
k = 0; out.dismissed = C.build(C.visible(out.chips, {'note:bn1': 1, 'note:bn3': 1}), '여백', {first: 'pay', titleOf: title}, mk).memos.map(m => m.note);
out.noteText = C.noteText([{text: 'a\nb', near: '결제'}, {text: 'c', near: null}]);
out.nearest = [C.nearest({x: 100, y: 500, w: 200, h: 60}, [{id: 'pay', x: 0, y: 0, w: 300, h: 400}, {id: 'done', x: 400, y: 0, w: 300, h: 400}]),
  C.nearest({x: 650, y: 500, w: 100, h: 60}, [{id: 'pay', x: 0, y: 0, w: 300, h: 400}, {id: 'done', x: 400, y: 0, w: 300, h: 400}]), C.nearest({x: 0, y: 0, w: 1, h: 1}, [])];
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


# ---------------------------------------------------------------- R25 노트 칩 · 요청 글
def test_note_chips_follow_screen_chips_and_skip_empty(out):
    c = out["chips"]
    assert [x["key"] for x in c] == ["screen:done", "note:bn1", "note:bn3"], "빈 메모는 칩 없음 · 화면 칩 뒤"
    assert c[1]["kind"] == "note" and c[1]["label"] == '노트 "버튼을 키워 주세요 둘째 줄"' and c[1]["id"] == "bn1"
    assert c[2]["label"] == '노트 "여백이 너무 넓어요 — 전체적으로 줄…"', "노트 칩 글은 20자"
    assert out["scope"] == ["screen", "all", "무엇을 바꿀까요?"], "노트는 범위를 정하지 않는다(노트만 = 모든 화면)"


def test_build_appends_note_section(out):
    m = out["withScreen"]
    assert len(m) == 1 and m[0]["screen"] == "done" and m[0]["scope"] == "screen"
    assert m[0]["note"] == "이거 반영해 줘\n\n노트:\n- 버튼을 키워 주세요\n  둘째 줄 (가까운 화면: 결제)\n- 여백이 너무 넓어요 — 전체적으로 줄이기"
    o = out["onlyNotes"]
    assert o["why"] == "" and len(o["memos"]) == 1 and o["memos"][0]["scope"] == "all", "글 없이 노트만 보내도 된다"
    assert o["memos"][0]["note"].startswith("노트:\n- 버튼을 키워 주세요")
    assert out["dismissed"] == ["여백"], "뺀 노트 칩은 요청에 없다"
    assert out["noteText"] == "노트:\n- a\n  b (가까운 화면: 결제)\n- c"


def test_nearest_card(out):
    assert out["nearest"] == ["pay", "done", None]
