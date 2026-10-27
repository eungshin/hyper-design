"""R17 시안 A — 요소 막대 아이콘 · 요소 전체 메뉴(묶음 + 단축키 힌트) 규칙(modules/blocks.js, node).

icons(h, o) = 막대에 보일 아이콘: 메모 달기 · 글자 고치기(글을 바꿀 수 있을 때만 — bar 의 글자 켜짐과 같은 규칙) · AI에게 바꿔 달라기 · 전체 메뉴(⋯).
menu(h, o) = 오른쪽 클릭·⋯ 메뉴 묶음 고르기 / 고치기 / 요청 — 꺼진 항목은 빼되 글자는 남긴다(누르면 까닭), 앱 카드 = 고치기는 AI 요청(힌트 없음).
keyOf(act, h, where) = 실제로 듣는 키만 힌트: Shift+Enter 상위 · Enter = 글자면 글자 고치기, 아니면 안쪽 고르기 · 크게 보기 글자 = 더블클릭 · Ctrl+D · Del · Alt+↑/↓.
askText('ai', h) = 메모 창에 미리 채울 바꿔 달라는 글."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")
pytestmark = pytest.mark.unit

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['edits.js', 'blocks.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const B = globalThis.HD.blocks, out = {};
const h = {path: 'p', text: '뜻 보기', full: '뜻 보기', textOk: true, prev: true, next: true, root: false, up: true};
const box = Object.assign({}, h, {textOk: false, text: '', full: ''});
const flat = (gs) => gs.map(g => [g.head, g.items.map(i => [i.act, i.label, i.key])]);
out.icons = B.icons(h, {}).map(i => [i.act, i.label, i.key]);
out.iconsBox = B.icons(box, {}).map(i => i.act);
out.iconsApp = B.icons(h, {app: true}).map(i => [i.act, !!i.ask, i.key]);
out.menu = flat(B.menu(h, {where: 'board'}));
out.menuBox = flat(B.menu(box, {where: 'board'}));
out.menuModal = B.menu(h, {where: 'modal'})[1].items.find(i => i.act === 'text').key;
out.menuRoot = B.menu(Object.assign({}, h, {root: true, up: false}), {}).map(g => [g.head, g.items.map(i => i.act)]);
out.menuImg = B.menu(Object.assign({}, h, {tag: 'img', attrs: {src: 'a.png', alt: ''}}), {})[1].items.map(i => i.act);
out.menuApp = B.menu(h, {app: true}).map(g => [g.head, g.items.map(i => [i.act, !!i.ask, i.key])]);
out.keys = ['parent', 'inner', 'text', 'dup', 'remove', 'up', 'down', 'memo', 'ai', 'swap'].map(a => B.keyOf(a, h, 'board'));
out.keysBox = ['inner', 'text'].map(a => B.keyOf(a, box, 'board'));
out.ai = [B.askText('ai', h), B.askText('ai', {})];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-elmenu-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_bar_icons_memo_text_ai_then_more(js):
    assert js["icons"] == [["memo", "메모 달기", ""], ["text", "글자 고치기", "Enter"], ["ai", "AI에게 바꿔 달라기", ""], ["more", "전체 메뉴", "오른쪽 클릭"]]


def test_text_icon_only_when_text_is_editable(js):
    assert js["iconsBox"] == ["memo", "ai", "more"]


def test_app_card_text_icon_is_an_ai_request_without_key(js):
    assert js["iconsApp"] == [["memo", False, ""], ["text", True, ""], ["ai", False, ""], ["more", False, "오른쪽 클릭"]]


def test_menu_groups_and_real_shortcut_hints(js):
    assert js["menu"] == [   # R27 F05: 10개 이하 — 상위·안쪽·위/아래로 옮기기는 키(Shift+Enter · Enter · Alt+↑/↓), AI 는 막대 아이콘
        ["고르기", [["chain", "레이어 고르기", ""]]],
        ["고치기", [["text", "글자 고치기", "Enter"], ["dup", "복제", "Ctrl+D"], ["remove", "지우기", "Del"],
                    ["insert", "아래에 넣기…", ""], ["swap", "다른 부품으로 바꾸기…", ""]]],
        ["요청", [["memo", "메모 달기", ""]]]], js["menu"]
    assert sum(len(i) for _, i in js["menu"]) <= 10


def test_enter_hint_goes_to_inner_when_not_text(js):
    g = dict((h, items) for h, items in js["menuBox"])
    assert ["text", "글자 고치기", ""] in g["고치기"], "꺼진 글자는 남긴다(누르면 까닭) — 힌트 없음"
    assert js["keysBox"] == ["Enter", ""], "안쪽 고르기는 메뉴에서 빠졌고(R27 F05) Enter 로"



def test_large_view_text_hint_is_double_click(js):
    assert js["menuModal"] == "더블클릭"


def test_root_drops_disabled_edits_and_parent(js):
    assert js["menuRoot"] == [["고르기", ["chain"]], ["고치기", ["text"]], ["요청", ["memo"]]], js["menuRoot"]


def test_attr_item_only_for_elements_with_attributes(js):
    assert js["menuImg"][:2] == ["text", "attr"], js["menuImg"]


def test_app_card_edits_are_ai_requests_without_hints(js):
    g = dict((h, items) for h, items in js["menuApp"])
    assert all(a and not k for _, a, k in g["고치기"]), g["고치기"]
    assert ["chain", False, ""] in g["고르기"] and ["memo", False, ""] in g["요청"]


def test_only_real_keys(js):
    assert js["keys"] == ["Shift+Enter", "", "Enter", "Ctrl+D", "Del", "Alt+↑", "Alt+↓", "", "", ""], "메모 C·AI 단축키는 없다(C = 선 자르기 도구)"


def test_ai_prefill(js):
    assert js["ai"][0].startswith("바꿔 주세요") and js["ai"][1].startswith("바꿔 주세요"), js["ai"]
