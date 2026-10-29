"""여러 요소 고르기(R19) — el-pick.js(Model) 와 chat.js chips 의 요소 목록. node, DOM 없음.

그냥 누르기 = 그 하나 · Shift+누르기 = 더하기(끝 = 주인)·빼기 · 주인 = 마지막 것 · path 없는 것은 더하지 않음.
Shift+누르기가 요소냐 카드냐(shift): 선택(V) · 고른 요소가 있음 · 누른 카드가 고른 카드 · 빈 레이아웃 아님 = 요소.
대화창 칩: 고른 요소마다 요소 칩 하나(고른 차례, 같은 요소 한 번) + 그 화면 칩 · 보내면 요소마다 요소 메모 하나(같은 글).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['el-pick.js', 'annotation.js', 'memo-batch.js', 'edits.js', 'chat.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const P = globalThis.HD.elPick, C = globalThis.HD.chat, out = {};
const k = s => s && s.path ? P.key(s.screen, s.path) : '';
const A = {screen: 'pay', path: 'button.a'}, B = {screen: 'pay', path: 'p.b'}, X = {screen: 'done', path: 'button.a'};
const ks = l => l.map(k);
let l = P.only(A);
out.only = ks(l);
l = P.toggle(l, B, k); out.addB = ks(l); out.priB = k(P.primary(l));
l = P.toggle(l, X, k); out.addX = ks(l);
l = P.toggle(l, A, k); out.dropA = ks(l); out.priAfterDrop = k(P.primary(l));
l = P.toggle(l, X, k); out.dropPri = ks(l); out.priNow = k(P.primary(l));
out.noPath = ks(P.toggle(P.only(A), {screen: 'pay', path: ''}, k));
out.bad = [ks(P.toggle(null, A, k)), P.primary(null), P.primary([]), P.only(null)];
out.has = [P.has([A, B], {screen: 'pay', path: 'p.b'}, k), P.has([A], X, k)];
out.keep = ks(P.keep([A, X, B], s => s.screen === 'pay'));
const sh = o => P.shift(Object.assign({tool: 'move', els: 1, picked: true, draft: false}, o));
out.shift = [sh({}), sh({els: 0}), sh({picked: false}), sh({tool: 'memo'}), sh({draft: true}), P.shift(null)];
out.scope = [P.menuScope({card: 'pay', elCard: 'pay'}), P.menuScope({card: 'pay', elCard: null}), P.menuScope({card: 'pay', elCard: 'done'}), P.menuScope(null)];
// 대화창 칩 · 보내기
const title = id => ({pay: '결제', done: '완료'})[id] || id;
const h = (path, text) => ({path: path, text: text, kind: 'button', rect: {x: 1, y: 2, w: 3, h: 4}});
const els = [{screen: 'pay', h: h('button.a', '결제하기')}, {screen: 'pay', h: h('p.b', '안내')}, {screen: 'done', h: h('button.a', '닫기')},
             {screen: 'pay', h: h('button.a', '결제하기')}, {screen: 'pay', h: {path: null}}];
const chips = C.chips({ids: ['pay'], titleOf: title, els: els});
out.chips = chips.map(c => c.key);
out.oldEl = C.chips({ids: [], titleOf: title, el: els[0]}).map(c => c.key);
let n = 0; const mk = () => 'm' + (++n);
const r = C.build(chips, '여백 줄이기', {first: 'pay', titleOf: title}, mk);
out.memos = r.memos.map(m => [m.screen, m.path, m.note]);
out.dropOne = C.build(C.visible(chips, {'el:pay:p.b': 1}), '여백', {first: 'pay', titleOf: title}, mk).memos.map(m => m.path);
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-el-pick-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_plain_pick_is_one_and_shift_adds_to_the_end_as_primary(js):
    assert js["only"] == ["pay:button.a"]
    assert js["addB"] == ["pay:button.a", "pay:p.b"] and js["priB"] == "pay:p.b", "Shift = 끝에 더함 = 주인(막대)"
    assert js["addX"] == ["pay:button.a", "pay:p.b", "done:button.a"], "다른 화면의 같은 path 는 다른 요소"


def test_shift_on_a_picked_one_removes_it_and_primary_falls_back_to_the_last(js):
    assert js["dropA"] == ["pay:p.b", "done:button.a"] and js["priAfterDrop"] == "done:button.a"
    assert js["dropPri"] == ["pay:p.b"] and js["priNow"] == "pay:p.b", "주인을 빼면 남은 마지막 것이 주인"


def test_bad_input_does_not_change_the_list(js):
    assert js["noPath"] == ["pay:button.a"], "path 없는 답은 더하지 않는다"
    assert js["bad"] == [["pay:button.a"], None, None, []]
    assert js["has"] == [True, False]
    assert js["keep"] == ["pay:button.a", "pay:p.b"], "놓은 카드의 것만 빠지고 차례 그대로"


def test_shift_click_adds_an_element_only_inside_a_picked_card_with_elements_picked(js):
    assert js["shift"] == ["el", "card", "card", "card", "card", "card"]


def test_chat_chips_one_per_picked_element_and_one_memo_each(js):
    assert js["chips"] == ["screen:done", "screen:pay", "el:pay:button.a", "el:pay:p.b", "el:done:button.a"], "요소마다 칩(고른 카드가 아닌 화면 칩은 앞에), 같은 요소 한 번, path 없는 것 빼기"
    assert js["oldEl"] == ["screen:pay", "el:pay:button.a"], "예전 이름 el(하나)도 그대로"
    assert js["memos"] == [["pay", "button.a", "여백 줄이기"], ["pay", "p.b", "여백 줄이기"], ["done", "button.a", "여백 줄이기"]], "요소마다 요소 메모, 같은 글"
    assert js["dropOne"] == ["button.a", "button.a"], "칩 하나를 빼면 그 요소만 빠진다"


def test_right_click_menu_scope_is_element_only_inside_a_picked_element_card(js):
    """R27 F05: 카드를 오른쪽 클릭 = 카드 메뉴. 그 카드 안 요소를 이미 골랐을 때만 요소 메뉴(카드 항목은 덧붙이지 않음)."""
    assert js["scope"] == ["element", "card", "card", "card"], js["scope"]
