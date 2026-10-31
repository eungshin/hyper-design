"""접근성 검사(R59) Model — modules/a11y.js 순수 함수(node) · 빌드가 axe.min.js 를 out 에 싣는다 · 코드 도장 입력에 든다. 브라우저 없음.

axe-core 결과(palette.js hd-a11y 의 실제 답 — fixtures/a11y_axe_result.json)를 디자이너 말로 바꾼다:
문제마다 {rule, impact, count, nodes:[{path, label, detail, text, ask}]} · 차례 = critical > serious > moderate > minor(같으면 규칙 표 차례) ·
한국어 제목(대비는 지금 비율·필요 비율·글자/배경 색이 글에 든다) · 모르는 규칙은 axe 의 help 글 · path 는 편집·첨부 길과 같은 모양(' > ' 조각 또는 #id)."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
FIX = HERE / "fixtures" / "a11y_axe_result.json"
NODE = shutil.which("node")
JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['pop-place.js', 'a11y.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const A = globalThis.HD.a11y, raw = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')).result, o = {};
o.rules = A.RULES;
o.items = A.items(raw);
o.summary = A.summary(o.items);
o.total = A.total(o.items);
o.empty = [A.items({violations: []}), A.summary([]), A.EMPTY];
o.unknown = A.items({violations: [{id: 'frame-title', impact: 'moderate', help: 'Frames must have a title', nodes: [{impact: 'moderate', target: ['iframe'], any: [], hd: null}]},
                                  {id: 'link-name', impact: 'serious', help: 'Links must have discernible text', nodes: [{impact: 'serious', target: ['#go'], any: []},
                                                                                                                     {impact: 'serious', target: ['.nav a'], any: []},
                                                                                                                     {impact: 'serious', target: ['nav > a.more:nth-of-type(2)'], any: []}]},
                                  {id: 'label', impact: 'minor', help: 'Form elements must have labels', nodes: [{impact: 'minor', target: ['input'], any: []}]}]});
o.bad = [A.check(null), A.check({}), A.check({violations: 'x'}), A.check({violations: []}), A.check(raw)];
o.tone = ['critical', 'serious', 'moderate', 'minor', 'weird'].map(A.tone);
o.place = [A.place({left: 300, top: 100, right: 900, bottom: 900}, {w: 300, h: 400}, 1440, 1000),
           A.place({left: 400, top: 100, right: 1300, bottom: 900}, {w: 300, h: 400}, 1440, 1000),
           A.place({left: 0, top: 100, right: 1440, bottom: 900}, {w: 300, h: 2000}, 1440, 1000)];
console.log(JSON.stringify(o));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-a11y-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD), str(FIX)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_rules_are_the_eight_designer_rules(out):
    assert out["rules"] == ["color-contrast", "button-name", "link-name", "image-alt", "input-image-alt", "label", "select-name", "target-size"]


def test_items_sorted_by_impact_then_rule_table(out):
    assert [(i["rule"], i["impact"], i["count"]) for i in out["items"]] == [
        ("button-name", "critical", 1), ("image-alt", "critical", 1), ("color-contrast", "serious", 1), ("target-size", "serious", 2)]


def test_korean_titles_and_numbers(out):
    by = {i["rule"]: i for i in out["items"]}
    c = by["color-contrast"]["nodes"][0]
    assert c["text"] == "글자와 배경 대비가 낮아요 — 지금 2.5:1, 4.5:1 이상 필요"
    assert "#9CA3AF" in c["detail"] and "#FFFFFF" in c["detail"]
    assert c["ask"] == "이 글자 대비를 4.5:1 이상으로 — 지금 #9CA3AF on #FFFFFF"
    assert by["button-name"]["nodes"][0]["text"] == '이름 없는 단추 — 화면 읽기 도구가 "단추"라고만 읽어요'
    assert by["target-size"]["nodes"][0]["text"] == "누르는 칸이 작아요 — 지금 16×16, 24×24 이상"
    assert by["image-alt"]["title"].startswith("그림에 설명(alt)이 없어요")
    for i in out["items"]:
        assert i["hint"] and all(n["ask"] for n in i["nodes"]), f"{i['rule']}: 고치는 법 한 줄·AI 요청 글이 있어야 한다"


def test_labels_name_the_element_like_chat_chips(out):
    by = {i["rule"]: i for i in out["items"]}
    assert by["color-contrast"]["nodes"][0]["label"] == "글자 · 이 금액은 부가세 포함이에요"
    assert by["button-name"]["nodes"][0]["label"] == "버튼"
    assert by["image-alt"]["nodes"][0]["label"] == "그림 · hero.png"


def test_path_uses_edit_path_format(out):
    by = {i["rule"]: i for i in out["items"]}
    assert by["color-contrast"]["nodes"][0]["path"] == "p.hint:nth-of-type(1)", "palette.js 가 붙인 hd.path 를 쓴다"
    assert by["target-size"]["nodes"][0]["path"] == "div.tiny:nth-of-type(1) > button:nth-of-type(1)"
    link = [i for i in out["unknown"] if i["rule"] == "link-name"][0]
    assert [n["path"] for n in link["nodes"]] == ["#go", None, "nav > a.more:nth-of-type(2)"], \
        "hd 가 없으면 axe target 이 같은 모양일 때만(아니면 null — 목록에는 남고 핀만 없다)"


def test_unknown_rule_falls_back_to_axe_help(out):
    u = [i for i in out["unknown"] if i["rule"] == "frame-title"][0]
    assert u["title"] == "Frames must have a title" and u["nodes"][0]["text"] == "Frames must have a title"
    assert u["nodes"][0]["ask"].endswith("Frames must have a title")
    assert [i["rule"] for i in out["unknown"]] == ["link-name", "frame-title", "label"], "serious > moderate > minor"


def test_summary_counts_nodes_by_group(out):
    assert out["total"] == 5
    assert out["summary"] == "문제 5 · 이름 1 · 대체 글 1 · 대비 1 · 크기 2"
    assert out["empty"] == [[], "문제 0", "접근성 문제 없음 (v1 규칙 8개 기준)"]


def test_bad_result_shape_is_reported(out):
    assert out["bad"][0] and out["bad"][1] and out["bad"][2], "깨진 결과는 까닭 글(View 가 [hd] + 토스트)"
    assert out["bad"][3] is None and out["bad"][4] is None


def test_tone_uses_existing_ui_tokens(out):
    assert out["tone"] == ["var(--ui-danger)", "var(--ui-danger)", "var(--ui-accent)", "var(--ui-muted)", "var(--ui-muted)"]


def test_panel_sits_beside_the_large_view_inside_the_window(out):
    right, left, clamped = out["place"]
    assert right == {"x": 912, "y": 100, "w": 300, "h": 400}, "오른쪽에 자리가 있으면 오른쪽"
    assert left == {"x": 88, "y": 100, "w": 300, "h": 400}, "오른쪽이 모자라면 왼쪽"
    assert clamped == {"x": 1132, "y": 8, "w": 300, "h": 984}, "양옆 다 모자라면 창 오른쪽 안 · 높이·자리는 창 안(popPlace.clamp)"


# ---------------------------------------------------------------- 빌드 · 코드 도장
def _bc():
    sys.path.insert(0, str(SCRIPTS))
    try:
        import build_canvas as BC
        import code_probe as CP
    finally:
        sys.path.pop(0)
    return BC, CP


def test_build_copies_axe_unmodified_and_only_when_changed(tmp_path):
    BC, _ = _bc()
    BC.copy_palette(tmp_path)
    got = tmp_path / "axe.min.js"
    assert got.is_file() and got.read_bytes() == BC.AXE_JS.read_bytes(), "out/axe.min.js = vendor 파일 그대로"
    old = 1_000_000_000
    import os
    os.utime(got, (old, old))
    BC.copy_palette(tmp_path)
    assert got.stat().st_mtime == old, "같은 내용이면 다시 쓰지 않는다(write_if_changed)"


def test_code_inputs_include_axe():
    BC, CP = _bc()
    assert BC.AXE_JS.resolve() in [p.resolve() for p in CP.code_inputs()]
