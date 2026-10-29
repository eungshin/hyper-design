"""정보 카드(R47) — Model modules/info-card.js 규칙(공유 사례 contract/info-card-cases.json), 요청문 끼우기(edits.request context),
레이어 배지 수(layers.build cards) — node. Python 미러(hd/hd_info_card.py)도 같은 사례를 여기서 함께 돌린다(둘이 갈라지지 않게).

요청문: 제공자가 없거나 빈 글이면 예전과 한 글자도 같다 · 있으면 화면마다 첫 항목 머리 바로 아래 세 칸 들여 한 번 ·
대화창 길(chat.build 메모 → 같은 request)도 한 번만."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
CASES = HERE.parent / "contract" / "info-card-cases.json"
HD_DIR = HERE.parents[1] / "hd"
NODE = shutil.which("node")

pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['info-card.js', 'annotation.js', 'memo-batch.js', 'edits.js', 'chat.js', 'layers.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const HD = globalThis.HD, I = HD.infoCard, E = HD.edits, out = {};
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')).cases;
out.cases = cases.map(c => {
  const data = {notes: c.notes, links: c.links, groups: c.groups};
  const list = c.folder ? I.reach(data, ['folder:' + c.folder]) : I.collect(data, c.screen);
  return {name: c.name, ids: list.map(n => n.id), text: c.folder ? null : I.text(list)};
});
const memo = (id, screen, note, no, extra) => Object.assign({id, screen, no, targets: [{path: 'body', text: ''}], path: 'body', text: '', rect: null, note, intent: 'change', sent: false}, extra || {});
const list = [memo('m1', 'pay', '버튼 크게', 1), memo('m2', 'pay', '글 짧게', 2), memo('m3', 'done', '색 바꾸기', 1), memo('m4', 'pay', '여백', 3, {scope: 'screen'})];
const card = '유의(정보 카드):\n- 결제 버튼은 하나만\n- 금액은 굵게';
out.plain = E.request(list, 'C:/out', {pay: '390×844(iPhone)'});
out.noProvider = E.request(list, 'C:/out', {pay: '390×844(iPhone)'}, undefined);
out.emptyProvider = E.request(list, 'C:/out', {pay: '390×844(iPhone)'}, () => '');
out.blankProvider = E.request(list, 'C:/out', {pay: '390×844(iPhone)'}, () => '  \n ');
const asked = [];
out.withCard = E.request(list, 'C:/out', {pay: '390×844(iPhone)'}, id => { asked.push(id); return id === 'pay' ? card : ''; });
out.asked = asked;
// 대화창 길: chat.build 가 만든 메모(요소 칩 둘 + 화면 칩) → 같은 request
const chips = HD.chat.chips({ids: ['pay'], els: [{screen: 'pay', h: {path: 'body > button', text: '결제'}}, {screen: 'pay', h: {path: 'body > p', text: '금액'}}]});
let k = 0;
const built = HD.chat.build(chips, '더 눈에 띄게', {first: 'pay', titleOf: x => x}, () => 'c' + (++k)).memos;
out.chatCount = built.length;
out.chatReq = E.request(built, 'C:/out', null, id => id === 'pay' ? card : '');
// 레이어 배지 수
const data = {notes: {a: {text: '화면', at: 1}, b: {text: '줄', at: 2}}, links: {l1: {from: 'note:a', to: 'screen:pay'}, l2: {from: 'note:b', to: 'folder:결제'}}, groups: {pay: '결제', done: '결제', home: '처음'}};
out.counts = I.counts(data, ['pay', 'done', 'home'], ['결제', '처음']);
out.tree = HD.layers.build([{id: 'row:결제', name: '결제', screens: [{id: 'pay', name: '결제'}, {id: 'done', name: '완료'}]}, {id: '@drafts', name: '빈 레이아웃', screens: [{id: 'new-1', name: '새'}]}],
  [], {}, null, null, out.counts).map(x => [x.id, x.card || 0]);
out.treeNoCards = HD.layers.build([{id: 'row:결제', name: '결제', screens: [{id: 'pay', name: '결제'}]}], [], {}).map(x => Object.prototype.hasOwnProperty.call(x, 'card'));
out.brokenData = [I.forScreen(null, 'pay'), I.forScreen({notes: 'x', links: [1, 2], groups: 5}, 'pay'), I.forScreen({notes: {a: {text: 'x'}}, links: {l: null}}, 'pay')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-infocard-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD), str(CASES)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _cases():
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def test_shared_cases_js(js):
    for c, got in zip(_cases(), js["cases"]):
        assert got["ids"] == c["expect"], c["name"]
        if "text" in c:
            assert got["text"] == c["text"], c["name"]


def test_shared_cases_python_mirror():
    sys.path.insert(0, str(HD_DIR))
    try:
        import hd_info_card as P
    finally:
        sys.path.remove(str(HD_DIR))
    for c in _cases():
        data = {"notes": c.get("notes"), "links": c.get("links"), "groups": c.get("groups")}
        lst = P.reach(data, ["folder:" + c["folder"]]) if c.get("folder") else P.collect(data, c["screen"])
        assert [n["id"] for n in lst] == c["expect"], c["name"]
        if "text" in c:
            assert P.text(lst) == c["text"], c["name"]


def test_cases_cover_the_contract():
    names = " ".join(c["name"] for c in _cases())
    for w in ("folder", "depth limit", "cycle", "hidden", "dangling", "paragraph cut", "total cap", "links absent"):
        assert w in names, w
    for c in _cases():
        if "text" in c:
            assert len(c["text"]) <= 1200, "글 덩어리는 1200자를 넘지 않는다: " + c["name"]


def test_request_is_byte_identical_without_a_card(js):
    assert js["noProvider"] == js["plain"]
    assert js["emptyProvider"] == js["plain"], "빈 카드 = 예전 그대로"
    assert js["blankProvider"] == js["plain"]


def test_card_goes_once_per_screen_under_the_first_item_line(js):
    lines = js["withCard"].split("\n")
    heads = [i for i, l in enumerate(lines) if l[:1].isdigit() and ". screen=" in l]
    pay = [i for i in heads if "screen=pay" in lines[i]]
    assert js["withCard"].count("유의(정보 카드):") == 1, "화면마다 한 번"
    first = pay[0]
    assert lines[first + 1:first + 4] == ["   유의(정보 카드):", "   - 결제 버튼은 하나만", "   - 금액은 굵게"], lines
    assert lines[first + 4].startswith('   text="'), "카드 다음은 예전 text 줄"
    assert js["asked"] == ["pay", "done"], "제공자는 화면마다 한 번만 불린다"
    stripped = "\n".join(l for i, l in enumerate(lines) if not (first < i <= first + 3))
    assert stripped == js["plain"], "카드 줄을 빼면 예전 요청문과 같다"


def test_chat_path_carries_the_card_once(js):
    assert js["chatCount"] >= 2, "요소 칩 둘 = 메모 둘(같은 화면)"
    assert js["chatReq"].count("유의(정보 카드):") == 1


def test_layers_badge_counts(js):
    assert js["counts"] == {"screens": {"pay": 2, "done": 1}, "folders": {"결제": 1}}, "화면은 줄 카드를 이어받는다"
    assert js["tree"] == [["row:결제", 1], ["pay", 2], ["done", 1], ["@drafts", 0], ["new-1", 0]]
    assert js["treeNoCards"] == [False, False], "cards 를 안 주면 예전 줄 모양"


def test_broken_data_gives_no_card_instead_of_throwing(js):
    assert js["brokenData"] == ["", "", ""]


def test_python_cards_for_reads_state_names():
    sys.path.insert(0, str(HD_DIR))
    try:
        import hd_info_card as P
    finally:
        sys.path.remove(str(HD_DIR))
    st = {"board-notes": {"a": {"text": "결제 버튼은 하나만", "at": 1}}, "board-links": {"l": {"from": "note:a", "to": "folder:결제"}}}
    assert P.cards_for(st, {"pay": "결제"}, ["pay", "pay", "home"]) == {"pay": "유의(정보 카드):\n- 결제 버튼은 하나만"}
    assert P.cards_for({"board-notes": {"a": {"text": "x"}}}, {}, ["pay"]) == {}, "board-links 가 없는 상태 = 카드 없음"
    assert P.cards_for(None, None, None) == {}
