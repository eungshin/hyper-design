"""메모 도구 한 칸·두 모드(2026-10-29 브리프) — 순수 규칙(node).

tools.js: 말풍선 '메모' 한 칸(data-tool="memo") · 키 P = 요소 모드 · M = 화면 모드(byKey 는 둘 다 memo, modeOfKey 가 모드) ·
  누른 곳의 대상 memoTarget(mode, inPhone) — 카드 제목 줄·테두리 띠(.phone 밖) = 모드와 상관없이 화면 전체 ·
  미리 보기 hoverOf('memo', {mode, edge}) — 요소 = 'any'(그 자리 요소) · 화면 / 테두리 = 'screen'(카드 전체 테두리) ·
  이름표 elLabel(kind) = '<종류> · 요소' · screenLabel(title) = '<화면 이름> · 화면 전체' · 칸 꼬리말 memoTip(mode).
memo-batch.toggle(ids, id): 화면 모드 Shift+클릭 = 고른 화면 목록에 더하기·빼기(차례 그대로)."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['tools.js', 'memo-batch.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const T = globalThis.HD.tools, B = globalThis.HD.memoBatch, out = {};
out.order = T.ORDER;
out.keys = ['p', 'm', 'v', 'c'].map(T.byKey);
out.modeOfKey = ['p', 'm', 'v', '', null].map(T.modeOfKey);
out.mode = ['el', 'screen', 'nope', null, undefined].map(T.memoMode);
out.hit = [T.hitOf('memo', 'el'), T.hitOf('memo', 'screen'), T.hitOf('memo'), T.hitOf('text')];
out.hover = [T.hoverOf('memo', {mode: 'el'}), T.hoverOf('memo', {mode: 'screen'}), T.hoverOf('memo', {mode: 'el', edge: true}),
             T.hoverOf('memo', {mode: 'el', typing: true}), T.hoverOf('text', {edge: true}), T.hoverOf('move', {only: true, edge: true}),
             T.hoverOf('memo', {mode: 'bogus'})];
out.target = [T.memoTarget('el', true), T.memoTarget('el', false), T.memoTarget('screen', true), T.memoTarget('screen', false), T.memoTarget('x', true)];
out.labels = [T.elLabel('button'), T.elLabel('nope'), T.elLabel(), T.screenLabel('결제'), T.screenLabel('')];
out.tips = ['el', 'screen'].map(function (m) { return T.memoTip(m); });
out.toggle = [B.toggle(['a', 'b'], 'c'), B.toggle(['a', 'b'], 'a'), B.toggle(['a'], 'a'), B.toggle(null, 'a'), B.toggle(['a'], ''), B.toggle(['a', 'a', 'b'], 'b')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-memo-tool-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_one_memo_slot_two_keys(js):
    assert "annotate" not in js["order"] and js["order"].count("memo") == 1, "요소 주석·화면 메모가 한 칸"
    assert js["keys"] == ["memo", "memo", "move", "knife"], "P·M 둘 다 메모 칸 · V·C 는 그대로"
    assert js["modeOfKey"] == ["el", "screen", None, None, None]
    assert js["mode"] == ["el", "screen", "el", "el", "el"], "모르는 모드 = 요소(기본)"


def test_target_edge_is_always_whole_screen(js):
    assert js["target"] == ["element", "screen", "screen", "screen", "element"], "화면 내용 밖(제목·테두리) = 늘 화면 전체"


def test_hover_preview_by_mode(js):
    assert js["hit"] == ["any", None, "any", "leaf"]
    assert js["hover"] == ["any", "screen", "screen", None, None, None, "any"]


def test_labels_and_tips(js):
    assert js["labels"] == ["버튼 · 요소", "영역 · 요소", "영역 · 요소", "결제 · 화면 전체", "화면 · 화면 전체"]
    el, sc = js["tips"]
    assert el["key"] == "P" and sc["key"] == "M"
    assert el["tip"].split("|")[0] == "메모 · 요소" and sc["tip"].split("|")[0] == "메모 · 화면 전체", "꼬리말 첫 줄이 지금 모드를 말한다"
    assert all("제목" in t["tip"] and "Shift" in t["tip"] for t in (el, sc)), "경계·Shift 규칙을 누르기 전에 알 수 있게"
    assert el["corner"] == "요소" and sc["corner"] == "화면"
    assert el["aria"] == "메모 · 요소 (P)" and sc["aria"] == "메모 · 화면 전체 (M)"


def test_batch_toggle(js):
    assert js["toggle"] == [["a", "b", "c"], ["b"], [], ["a"], ["a"], ["a"]]
