"""카드(아트보드) 크기(task 46) Model — modules/artboard.js 순수 함수 단위 테스트(node). 브라우저 없음.

프리셋 묶음(모바일·태블릿·웹/데스크톱 + 사용자 정의) · 검사(정수 16~60000, 한국어 오류 — R57) · 카드마다 크기(없으면 프로젝트 기본) ·
방향 바꾸기 · 최근 크기 6개 · 내 프리셋 저장 · 깨진 저장값은 버리고 알림 · 빈 레이아웃 → 화면 승격 때 크기 이어받기 · 요청문 글.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/artboard.js', 'utf8'), {filename: 'artboard.js'});
const A = globalThis.HD.artboard, out = {}, DEF = {w: 375, h: 812};
out.cats = A.CATS.map(c => c.id);
out.byName = {};
A.PRESETS.forEach(p => { out.byName[p.name] = [p.cat, p.w, p.h]; });
out.check = [A.check(393, 852), A.check('834', '1194'), A.check(15, 800), A.check(400, 60001), A.check(393.5, 852), A.check('', 852), A.check('abc', 852), A.check(null, null)];
const s0 = {};
out.ofMissing = A.of(s0, 'pay', DEF);
const s1 = A.set(s0, ['pay', 'home'], {w: 834, h: 1194, preset: 'iPad Pro 11'}, DEF);
out.s0Untouched = s0;
out.s1 = s1;
out.ofSet = A.of(s1, 'pay', DEF);
out.back = A.set(s1, ['pay'], null, DEF);
out.sameAsDefault = A.set(s1, ['home'], {w: 375, h: 812}, DEF);
out.swap = A.swap({w: 393, h: 852, preset: 'iPhone 16'});
out.orient = [A.orient({w: 393, h: 852}), A.orient({w: 1440, h: 1024}), A.orient({w: 500, h: 500})];
out.presetOf = [A.presetOf(393, 852), A.presetOf(852, 393), A.presetOf(401, 801), A.presetOf(300, 300, [{name: '내 폰', w: 300, h: 300}])];
out.full = [A.full({w: 834, h: 1194, preset: 'iPad Pro 11'}), A.full({w: 500, h: 700})];
out.label = A.label({w: 393, h: 852});
let r = [];
[[393, 852], [834, 1194], [393, 852], [1, 2], [1440, 1024], [412, 917], [744, 1133], [1920, 1080], [440, 956]].forEach(p => { r = A.pushRecent(r, {w: p[0], h: p[1]}); });
out.recent = r;
const sv1 = A.savePreset([], '  내 태블릿 ', '800', '1280');
const sv2 = A.savePreset(sv1.saved, '내 태블릿', 900, 1300);
out.save = [sv1, sv2, A.savePreset([], '', 800, 1280), A.savePreset([], '이름', 10, 1280)];
out.norm = A.norm({pay: {w: 834, h: 1194, preset: 'iPad Pro 11'}, bad1: {w: 'x', h: 3}, bad2: null, bad3: {w: 60001, h: 800}, ok2: {w: 500, h: 700}});
out.normJunk = [A.norm(null), A.norm([1, 2]), A.norm('x')];
out.prefs = [A.prefs(null), A.prefs({recent: [{w: 393, h: 852}, {w: 'x'}], saved: [{name: 'a', w: 300, h: 300}, {name: '', w: 300, h: 300}, 7]})];
out.carry = [A.carry({'new-1': {w: 834, h: 1194}}, 'new-1', 'pay'), A.carry({}, 'new-1', 'pay')];
out.nudge = [A.nudge(393, 'ArrowUp', false), A.nudge(393, 'ArrowDown', true), A.nudge(16, 'ArrowDown', true), A.nudge(59995, 'ArrowUp', true), A.nudge(393, 'a', false), A.nudge('', 'ArrowUp', false)];
out.common = [A.common(s1, ['pay', 'home'], DEF), A.common(s1, ['pay', 'x'], DEF), A.common({}, ['x', 'y'], DEF)];
out.list = {
  mobile: A.list('mobile', {recent: [], saved: []}).length,
  recent: A.list('recent', {recent: [{w: 393, h: 852}], saved: []}),
  saved: A.list('saved', {recent: [], saved: [{name: '내 폰', w: 300, h: 300}]})};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-artboard-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_catalogue_has_real_devices(out):
    assert out["cats"] == ["recent", "mobile", "tablet", "desktop", "saved"]
    b = out["byName"]
    assert b["iPhone 16"] == ["mobile", 393, 852]
    assert b["iPhone 16 Pro Max"] == ["mobile", 440, 956]
    assert b["Android Compact"] == ["mobile", 412, 917]
    assert b["iPad mini"] == ["tablet", 744, 1133]
    assert b["iPad Pro 11"] == ["tablet", 834, 1194]
    assert b["Desktop"] == ["desktop", 1440, 1024]
    assert b["MacBook Air"] == ["desktop", 1280, 832]
    assert b["Web 1920"] == ["desktop", 1920, 1080]


def test_check_integers_in_range_with_korean_error(out):
    ok1, ok2, small, big, frac, empty, word, none = out["check"]
    assert ok1 == {"ok": True, "w": 393, "h": 852} and ok2 == {"ok": True, "w": 834, "h": 1194}
    for bad in (small, big, frac, empty, word, none):
        assert bad["ok"] is False and "16~60000" in bad["error"], bad
    assert "너비" in small["error"] and "높이" in big["error"]


def test_size_of_card_defaults_and_set_is_pure(out):
    assert out["ofMissing"] == {"w": 375, "h": 812, "custom": False}
    assert out["s0Untouched"] == {}, "입력은 고치지 않는다"
    assert out["s1"] == {"pay": {"w": 834, "h": 1194, "preset": "iPad Pro 11"}, "home": {"w": 834, "h": 1194, "preset": "iPad Pro 11"}}
    assert out["ofSet"] == {"w": 834, "h": 1194, "preset": "iPad Pro 11", "custom": True}
    assert out["back"] == {"home": {"w": 834, "h": 1194, "preset": "iPad Pro 11"}}, "null = 기본 크기로"
    assert "home" not in out["sameAsDefault"], "기본과 같은 크기(프리셋 이름 없음) = 저장하지 않음"


def test_orientation_and_preset_lookup(out):
    assert out["swap"] == {"w": 852, "h": 393, "preset": "iPhone 16 가로"}
    assert out["orient"] == ["portrait", "landscape", "portrait"]
    assert out["presetOf"] == ["iPhone 16", "iPhone 16 가로", "", "내 폰"]
    assert out["full"] == ["834×1194(iPad Pro 11)", "500×700"]
    assert out["label"] == "393×852"


def test_recent_is_mru_six_without_duplicates_or_invalid(out):
    assert out["recent"] == [{"w": 440, "h": 956}, {"w": 1920, "h": 1080}, {"w": 744, "h": 1133}, {"w": 412, "h": 917},
                             {"w": 1440, "h": 1024}, {"w": 393, "h": 852}]


def test_save_preset(out):
    s1, s2, noname, small = out["save"]
    assert s1["ok"] and s1["saved"] == [{"name": "내 태블릿", "w": 800, "h": 1280}]
    assert s2["ok"] and s2["saved"] == [{"name": "내 태블릿", "w": 900, "h": 1300}], "같은 이름 = 덮어쓰기"
    assert noname["ok"] is False and "이름" in noname["error"]
    assert small["ok"] is False and "16~60000" in small["error"]


def test_norm_drops_broken_entries(out):
    n = out["norm"]
    assert n["sizes"] == {"pay": {"w": 834, "h": 1194, "preset": "iPad Pro 11"}, "ok2": {"w": 500, "h": 700}}
    assert sorted(n["bad"]) == ["bad1", "bad2", "bad3"]
    assert [j["sizes"] for j in out["normJunk"]] == [{}, {}, {}]
    assert out["normJunk"][0]["bad"] == [] and out["normJunk"][1]["bad"] == ["*"]


def test_prefs_normalize(out):
    assert out["prefs"][0] == {"recent": [], "saved": []}
    assert out["prefs"][1] == {"recent": [{"w": 393, "h": 852}], "saved": [{"name": "a", "w": 300, "h": 300}]}


def test_carry_moves_draft_size_to_screen(out):
    assert out["carry"][0] == {"pay": {"w": 834, "h": 1194}}
    assert out["carry"][1] == {}


def test_nudge_arrow_keys(out):
    assert out["nudge"] == [394, 383, 16, 60000, None, None]


def test_common_and_tab_lists(out):
    assert out["common"][0] == {"w": 834, "h": 1194, "preset": "iPad Pro 11", "custom": True}
    assert out["common"][1] is None, "크기가 다르면 공통 없음"
    assert out["common"][2] == {"w": 375, "h": 812, "custom": False}
    assert out["list"]["mobile"] >= 6
    assert out["list"]["recent"] == [{"name": "iPhone 16", "w": 393, "h": 852}], "최근 = 맞는 프리셋 이름(없으면 W×H)"
    assert out["list"]["saved"] == [{"name": "내 폰", "w": 300, "h": 300, "saved": True}]
