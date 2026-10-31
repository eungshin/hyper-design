"""부품 쓰는 화면 지도(R58) — Python Model(usage_map) · 빌드 데이터(board_data.index_data 'usage') · components.html 칩·목록 · JS Model(modules/usage.js, node).

규칙: 화면이 부품을 "쓴다" = 그 화면 파일 안 어떤 요소의 class 에 견본 key 가 있다(components.html 거르기와 같은 뜻).
지도 = {key: [화면 id …]}(판 차례, 쓰는 화면이 없는 key 는 빠짐, 배지 'badge' 는 지도에 없음). 앱 프로젝트(개발 서버 카드)·견본 파일 없음 = {}.
components.html: 남은 section 마다 data-used="id id" + 머리 칩 '쓰는 화면 N'(배지 제외) · 맨 위 얇은 목록(이름 + 수 → 그 section).
캔버스(usage.js): read(raw, ids) → {map, bad, unknown} — 없음 = 빈 지도(경고 없음) · 모양이 깨짐 = 빈 지도 + 까닭 · 판에 없는 id = 빼고 알림."""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
MOD = SCRIPTS / "modules"
NODE = shutil.which("node")
SPECIMENS = SCRIPTS.parents[1] / "foundation" / "specimens.html"

sys.path.insert(0, str(SCRIPTS))
import usage_map as UM  # noqa: E402
import board_data as BD  # noqa: E402


# ---------------------------------------------------------------- 순수 규칙
def test_classes_reads_both_quote_styles_and_splits_words():
    html = '<div class="btn primary"><span class=\'chip  is-selected\'></span><p data-class="row">x</p></div>'
    assert UM.classes(html) == {"btn", "primary", "chip", "is-selected"}


def test_usage_keeps_board_order_drops_unused_and_badge():
    keys = ["btn", "chip", "badge", "row", "field"]
    screens = [("home", {"btn", "badge", "row"}), ("list", {"row", "btn-x"}), ("edit", {"btn", "field"})]
    assert UM.usage(keys, screens) == {"btn": ["home", "edit"], "row": ["home", "list"], "field": ["edit"]}
    assert "chip" not in UM.usage(keys, screens), "쓰는 화면이 없는 부품은 지도에 없다"
    assert "badge" not in UM.usage(keys, screens), "배지는 screens.json badges 로 그린다 — 칩 없음"


def test_usage_empty_inputs():
    assert UM.usage([], [("a", {"btn"})]) == {}
    assert UM.usage(["btn"], []) == {}


def test_spec_keys_reads_specimen_sections_in_order():
    keys = UM.spec_keys(SPECIMENS.read_text(encoding="utf-8"))
    assert keys[:3] == ["btn", "cta", "chip"] and "wizard" in keys and "badge" in keys


def test_mark_section_adds_data_used_and_chip_and_badge_gets_none():
    tag = '<section class="spec" data-key="btn" data-title="버튼">'
    out = UM.mark_section(tag, "btn", ["home", "edit"])
    assert 'data-used="home edit"' in out and out.startswith('<section class="spec" data-key="btn" data-title="버튼"')
    assert re.search(r'<button[^>]*class="use-chip"[^>]*data-key="btn"[^>]*>쓰는 화면 2</button>', out), out
    assert UM.mark_section('<section class="spec" data-key="badge" data-title="배지">', "badge", ["home"]) == \
        '<section class="spec" data-key="badge" data-title="배지">', "배지 섹션은 그대로"
    assert UM.mark_section(tag, "btn", []) == tag, "쓰는 화면 0 = 칩 없음"
    assert '&quot;' in UM.mark_section(tag, "btn", ['a"b']), "id 는 이스케이프"


def test_index_lists_names_counts_and_anchors():
    nav = UM.index_html([("btn", "버튼", 2), ("row", "목록 행", 1)])
    assert 'class="use-index"' in nav and nav.count('class="use-link"') == 2
    assert 'href="#spec-btn"' in nav and "버튼" in nav and ">2<" in nav
    assert UM.index_html([]) == "", "부품이 없으면 목록도 없다"


# ---------------------------------------------------------------- 빌드 데이터(board_data) · components.html
def _out(tmp_path, screens, files):
    o = tmp_path / "out"
    (o / "screens").mkdir(parents=True)
    (o / "screens.json").write_text(json.dumps({"groups": ["g"], "screens": screens}), encoding="utf-8")
    for n, src in files.items():
        (o / "screens" / n).write_text(src, encoding="utf-8")
    return o


def test_index_data_carries_usage_in_board_order(tmp_path, monkeypatch):
    monkeypatch.setenv("HD_SPECIMENS", str(SPECIMENS))
    o = _out(tmp_path, [{"id": "a", "group": "g"}, {"id": "b", "group": "g"}, {"id": "a--x", "group": "g"}],
             {"a.html": '<button class="btn primary">x</button>', "b.html": '<a class="row">y</a>',
              "a--x.html": '<button class="btn">x</button><div class="row"></div>'})
    m = json.loads((o / "screens.json").read_text(encoding="utf-8"))
    d = BD.index_data(o, m)
    assert [c["id"] for r in d["rows"] for c in r["screens"]] == ["a", "a--x", "b"]
    assert d["usage"] == {"btn": ["a", "a--x"], "row": ["a--x", "b"]}, "판 차례 그대로(상태 변형은 원래 화면 뒤)"


def test_index_data_app_project_and_no_specimens_are_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HD_SPECIMENS", str(SPECIMENS))
    o = _out(tmp_path, [{"id": "app", "group": "g", "file": "http://127.0.0.1:5173/"}], {})
    assert BD.index_data(o, json.loads((o / "screens.json").read_text(encoding="utf-8")))["usage"] == {}
    monkeypatch.setenv("HD_SPECIMENS", str(tmp_path / "none.html"))
    o2 = _out(tmp_path / "2", [{"id": "a", "group": "g"}], {"a.html": '<button class="btn"></button>'})
    assert BD.index_data(o2, json.loads((o2 / "screens.json").read_text(encoding="utf-8")))["usage"] == {}


def test_build_components_writes_chips_index_and_data_used(tmp_path, monkeypatch):
    monkeypatch.setenv("HD_SPECIMENS", str(SPECIMENS))
    import importlib
    import build_canvas as BC
    BC = importlib.reload(BC)
    o = _out(tmp_path, [{"id": "a", "group": "g"}, {"id": "b", "group": "g"}],
             {"a.html": '<button class="btn primary">x</button><span class="badge">n</span>', "b.html": '<button class="btn">x</button><a class="row"></a>'})
    m = json.loads((o / "screens.json").read_text(encoding="utf-8"))
    BC.build_components(o, m, BD.index_data(o, m)["usage"])
    html = (o / "components.html").read_text(encoding="utf-8")
    assert re.search(r'data-key="btn"[^>]*data-used="a b"', html), "btn 은 두 화면"
    assert re.search(r'data-key="row"[^>]*data-used="b"', html)
    assert ">쓰는 화면 2</button>" in html and ">쓰는 화면 1</button>" in html
    assert not re.search(r'data-key="badge"[^>]*data-used', html), "배지 섹션은 칩 없음"
    nav = re.search(r'<nav class="use-index".*?</nav>', html, re.S)
    assert nav and nav.group(0).count('class="use-link"') == 2, "목록 = 칩이 있는 부품"
    assert nav.start() < html.index('data-key="btn"'), "목록은 맨 위"
    assert "hd-usage-show" in html, "칩을 누르면 캔버스에 알리는 작은 스크립트"
    import specimen_parts as SP
    assert [s["key"] for s in SP.sections(html)] == ["btn", "badge", "row"], "견본 뼈대 읽기(task 49b)는 그대로"
    assert SP.markup(html, "btn") == '<button class="btn primary">텍스트</button>'


# ---------------------------------------------------------------- JS Model(modules/usage.js)
JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/usage.js', 'utf8'), {filename: 'usage.js'});
const U = globalThis.HD.usage, ids = ['a', 'b', 'c'], out = {};
out.ok = U.read({btn: ['a', 'c'], row: ['b']}, ids);
out.none = [U.read(undefined, ids), U.read(null, ids)];
out.badShape = [U.read([], ids), U.read('x', ids), U.read({btn: 'a'}, ids), U.read({btn: [1]}, ids)];
out.unknown = U.read({btn: ['a', 'zz'], row: ['zz']}, ids);
out.count = [U.count(out.ok.map, 'btn'), U.count(out.ok.map, 'nope'), U.count(null, 'btn')];
out.label = [U.label(5), U.bar('버튼', 5)];
out.msg = [U.showMsg({type: 'hd-usage-show', key: 'btn', title: ' 버튼 '}), U.showMsg({type: 'hd-usage-show', key: ''}),
           U.showMsg({type: 'hd-usage-show', key: 'a b'}), U.showMsg({type: 'x', key: 'btn'}), U.showMsg(null)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 없음")
    p = subprocess.run([NODE, "-e", JS, str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_js_read_good_map(js):
    assert js["ok"] == {"map": {"btn": ["a", "c"], "row": ["b"]}, "bad": None, "unknown": []}


def test_js_read_missing_is_quiet_empty(js):
    assert js["none"] == [{"map": {}, "bad": None, "unknown": []}] * 2, "앱 프로젝트·옛 데이터 = 경고 없이 빈 지도"


def test_js_read_broken_shape_is_empty_with_reason(js):
    for r in js["badShape"]:
        assert r["map"] == {} and r["bad"], r


def test_js_read_drops_unknown_ids_and_empty_keys(js):
    assert js["unknown"]["map"] == {"btn": ["a"]} and js["unknown"]["unknown"] == ["zz"] and js["unknown"]["bad"] is None


def test_js_count_label_and_message(js):
    assert js["count"] == [2, 0, 0]
    assert js["label"] == ["쓰는 화면 5", "버튼 · 쓰는 화면 5"]
    assert js["msg"][0] == {"key": "btn", "title": "버튼"}
    assert js["msg"][1:] == [None, None, None, None]
