"""R50 요소 막대에 기능 고정하기 — 규칙(modules/blocks.js, node).

pins(raw) = 저장된 고정 목록 정리: 없음 = 기본(지금 막대 memo·text·ai) · 배열 아님 = 기본 + 경고 · 모르는 act 버림 + 경고 · 중복 제거 · 6개 자르기.
pin(list, act) = 핀 토글: 고정됨 = 빼기 · 아니면 끝에 더하기 · 6개면 거절(까닭) · 고정할 수 없는 동작(묶음 머리 등) 거절.
pinState(list, act) = 메뉴 줄 핀 모양 {on, ok, why}.
icons(h, {pins}) = 손잡이 뒤 고정 차례 그대로 + ⋯ 맨 끝 · 그 요소에 못 쓰는 동작은 숨기지 않고 꺼짐(on:false) + 까닭(title).
menu(h, {pins}) = 실제 동작 줄(옆 목록 안 항목 포함)에 pinned·pinOk — 묶음 머리('레이어 고르기 ▸'·'부품 ▸')에는 없음."""
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
const root = Object.assign({}, h, {root: true, up: false});
out.max = B.PIN_MAX;
out.clean = {
  none: B.pins(undefined), nul: B.pins(null), notArray: B.pins('memo'), obj: B.pins({a: 1}),
  empty: B.pins([]), unknown: B.pins(['memo', 'zzz', 3, 'dup']), dupes: B.pins(['dup', 'dup', 'memo']),
  heads: B.pins(['chain', 'part', 'more', 'grip', 'remove']),
  many: B.pins(['memo', 'text', 'ai', 'dup', 'remove', 'attr', 'addr', 'swap'])
};
const six = ['memo', 'text', 'ai', 'dup', 'remove', 'attr'];
out.toggle = {
  add: B.pin(['memo', 'text', 'ai'], 'dup'), drop: B.pin(['memo', 'text', 'ai'], 'text'),
  full: B.pin(six, 'swap'), fullDrop: B.pin(six, 'memo'), head: B.pin(['memo'], 'part'), bad: B.pin('x', 'dup')
};
out.state = {on: B.pinState(['memo'], 'memo'), off: B.pinState(['memo'], 'dup'), full: B.pinState(six, 'swap'), fullOn: B.pinState(six, 'dup'), head: B.pinState(six, 'chain')};
const ic = (x, o) => B.icons(x, o).map(i => [i.act, i.on, i.title]);
out.icons = {
  def: B.icons(h, {}).map(i => i.act),
  order: B.icons(h, {pins: ['dup', 'memo', 'remove']}).map(i => i.act),
  box: ic(box, {}), root: ic(root, {pins: ['remove', 'memo', 'swap']}),
  noAttr: ic(h, {pins: ['attr']}), img: ic(Object.assign({}, h, {tag: 'img', attrs: {src: 'a.png', alt: ''}}), {pins: ['attr']}),
  addr: B.icons(h, {pins: ['addr', 'dup']}).map(i => [i.act, i.key, i.on]),
  app: B.icons(h, {app: true, pins: ['dup', 'memo']}).map(i => [i.act, !!i.ask, i.on]),
  broken: B.icons(h, {pins: 'oops'}).map(i => i.act), empty: B.icons(h, {pins: []}).map(i => i.act)
};
const flat = (gs) => [].concat(...gs.map(g => g.items)).flatMap(i => [i].concat(i.sub || [])).map(i => [i.act, i.pinned === undefined ? null : i.pinned, i.pinOk === undefined ? null : i.pinOk]);
out.menu = flat(B.menu(h, {pins: ['memo', 'dup']}));
out.menuFull = flat(B.menu(h, {pins: six}));
out.barMenu = typeof B.barMenu === 'function' ? {icon: B.barMenu(['memo', 'text', 'dup'], 'dup'), iconDef: B.barMenu(undefined, 'memo'), more: B.barMenu(['dup'], 'more'), moreDef: B.barMenu(['memo', 'text', 'ai'], 'more'), grip: B.barMenu([], 'grip')} : null;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-elpins-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


DEF = ["memo", "text", "ai"]


def test_missing_pins_are_todays_bar_without_warning(js):
    c = js["clean"]
    assert c["none"] == {"list": DEF, "warn": ""} and c["nul"] == {"list": DEF, "warn": ""}


def test_broken_pins_fall_back_to_default_with_warning(js):
    c = js["clean"]
    for k in ("notArray", "obj"):
        assert c[k]["list"] == DEF and c[k]["warn"].startswith("[hd]"), c[k]


def test_empty_list_is_kept_user_unpinned_everything(js):
    assert js["clean"]["empty"] == {"list": [], "warn": ""}


def test_unknown_acts_dropped_with_one_warning_duplicates_removed(js):
    c = js["clean"]
    assert c["unknown"]["list"] == ["memo", "dup"] and c["unknown"]["warn"].startswith("[hd]"), c["unknown"]
    assert c["dupes"]["list"] == ["dup", "memo"], c["dupes"]
    assert c["heads"]["list"] == ["remove"] and c["heads"]["warn"], "묶음 머리·손잡이·⋯ 는 고정 목록에 들지 않는다"


def test_list_cut_to_six(js):
    assert js["max"] == 6
    assert js["clean"]["many"]["list"] == ["memo", "text", "ai", "dup", "remove", "attr"], js["clean"]["many"]


def test_toggle_adds_at_end_and_removes(js):
    t = js["toggle"]
    assert t["add"] == {"pins": ["memo", "text", "ai", "dup"]}
    assert t["drop"] == {"pins": ["memo", "ai"]}


def test_toggle_refuses_seventh_but_can_still_remove_at_six(js):
    t = js["toggle"]
    assert t["full"].get("why") == "막대에는 6개까지 — 하나를 빼고 고정해 주세요" and "pins" not in t["full"], t["full"]
    assert t["fullDrop"] == {"pins": ["text", "ai", "dup", "remove", "attr"]}
    assert t["head"].get("why") and "pins" not in t["head"], "묶음 머리는 고정할 수 없다"
    assert t["bad"] == {"pins": DEF + ["dup"]}, "깨진 목록 = 기본에서 토글"


def test_pin_state_for_menu_rows(js):
    s = js["state"]
    assert s["on"] == {"on": True, "ok": True, "why": ""}
    assert s["off"] == {"on": False, "ok": True, "why": ""}
    assert s["full"] == {"on": False, "ok": False, "why": "막대에는 6개까지 — 하나를 빼고 고정해 주세요"}
    assert s["fullOn"]["ok"] is True, "6개여도 고정된 줄은 뺄 수 있다"
    assert s["head"]["ok"] is False


def test_icons_follow_pin_order_grip_is_view_more_is_last(js):
    i = js["icons"]
    assert i["def"] == DEF + ["more"]
    assert i["order"] == ["dup", "memo", "remove", "more"]
    assert i["broken"] == DEF + ["more"] and i["empty"] == ["more"]


def test_unusable_pinned_action_is_off_with_reason_not_hidden(js):
    i = js["icons"]
    t = [x for x in i["box"] if x[0] == "text"][0]
    assert t[1] is False and "글자만 바꿀 수 없어요" in t[2], "'글자'도 숨기지 않고 꺼진 아이콘(예전 숨김 규칙을 통일)"
    assert [x[0] for x in i["box"]] == DEF + ["more"], "막대 모양이 요소마다 흔들리지 않는다"
    r = dict((a, (on, why)) for a, on, why in i["root"])
    assert r["remove"][0] is False and "화면 뿌리" in r["remove"][1] and r["swap"][0] is False and r["memo"][0] is True, r
    assert i["noAttr"][0][1] is False and "속성" in i["noAttr"][0][2], i["noAttr"]
    assert i["img"][0][1] is True, i["img"]


def test_icons_keys_and_app_card(js):
    i = js["icons"]
    assert i["addr"][:2] == [["addr", "Ctrl+L", True], ["dup", "Ctrl+D", True]], i["addr"]
    assert i["app"][:2] == [["dup", True, True], ["memo", False, True]], "앱 카드 = 파일 바꾸는 고정 동작은 AI 요청"


def test_menu_rows_carry_pin_fields_but_group_heads_do_not(js):
    m = dict((a, (p, ok)) for a, p, ok in js["menu"])
    assert m["chain"] == (None, None) and m["part"] == (None, None), "묶음 머리에는 핀 없음"
    assert m["memo"] == (True, True) and m["dup"] == (True, True) and m["text"] == (False, True), m
    assert m["insert"] == (False, True) and m["swap"] == (False, True), "옆 목록 '부품 ▸' 안 항목도 하나하나 고정"
    f = dict((a, (p, ok)) for a, p, ok in js["menuFull"])
    assert f["swap"] == (False, False) and f["dup"] == (True, True), f


PREFS_JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/prefs.js', 'utf8'), {filename: 'prefs.js'});
const P = globalThis.HD.prefs, mk = o => k => (k in o ? o[k] : null), K = 'hd-canvas-prefs', out = {};
out.fresh = 'elbarPins' in P.load(mk({}));
out.kept = P.load(mk({[K]: JSON.stringify({v: 3, elbarPins: ['dup', 'memo']})})).elbarPins;
out.broken = P.load(mk({[K]: JSON.stringify({v: 3, elbarPins: 'dup'})})).elbarPins;
const w = {};
out.saved = !!P.save(Object.assign(P.defaults(), {elbarPins: ['addr']}), (k, v) => { w[k] = v; });
out.written = JSON.parse(w[K]).elbarPins;
out.failed = P.save(P.defaults(), () => { throw new Error('quota'); });
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def pjs():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-elpins-prefs-"))
    try:
        (tmp / "t.js").write_text(PREFS_JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_prefs_keep_pins_and_leave_broken_value_for_the_bar_to_warn(pjs):
    assert pjs["fresh"] is False, "칸 없음 = 기본 막대(설정 기본값은 그대로)"
    assert pjs["kept"] == ["dup", "memo"]
    assert pjs["broken"] == "dup", "깨진 값은 그대로 실어 막대가 기본으로 + [hd] 경고(blocks.pins)"
    assert pjs["saved"] and pjs["written"] == ["addr"]


def test_prefs_save_failure_is_reported(pjs):
    assert pjs["failed"] is None, "저장 실패 = null(막대가 토스트로 알린다)"


def test_bar_right_click_menu_offers_unpin_and_reset_to_default(js):
    """막대 오른쪽 클릭 메뉴(Office 빠른 실행 '초기화'): 고정 아이콘 = 빼기 + 기본으로 되돌리기 · ⋯·손잡이 = 되돌리기만(다 빼도 돌아올 길) ·
    이미 기본이면 되돌리기 없음(빈 메뉴 = 띄우지 않음)."""
    m = js["barMenu"]
    assert m is not None, "HD.blocks.barMenu 가 없다"
    assert m["icon"] == ["unpin", "reset"]
    assert m["iconDef"] == ["unpin"]
    assert m["more"] == ["reset"] and m["grip"] == ["reset"]
    assert m["moreDef"] == []

