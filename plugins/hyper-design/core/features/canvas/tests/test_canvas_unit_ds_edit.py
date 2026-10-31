"""Foundation 토큰 고치기(R55) — JS Model(modules/ds-edit.js, node, 브라우저 없음).

HD.dsEdit: kindOf(이름) · check(이름, 값, 있는 이름?) → {ok, value, why} — Python token_edit.check 와 같은 표(fixtures/token-values.json) ·
fields(pick) → 고칠 칸들(글자 줄 = --fs/--fw/--lh) · pickMsg(on) → 문서 탭에 보낼 hd-pick · readPick(hd-sel) → 고른 토큰 | null · href(base, slug, v) → 토큰 주소.
palette.js 안 tokenKind 는 같은 규칙 — 표시 사이(/* hd-token-kind */ … /* /hd-token-kind */) 함수를 같은 표로 견준다."""
import json, shutil, subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
PALETTE = HERE.parents[2] / "foundation" / "palette.js"
NODE = shutil.which("node")
TABLE = json.loads((HERE / "fixtures" / "token-values.json").read_text(encoding="utf-8"))

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/ds-edit.js', 'utf8'), {filename: 'ds-edit.js'});
const M = globalThis.HD.dsEdit, T = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')), out = {};
const names = T.kinds.map(k => k[0]);
out.kinds = T.kinds.map(k => M.kindOf(k[0]));
out.values = T.values.map(v => { const r = M.check(v[0], v[1], names); return r.ok ? r.value : null; });
out.whys = T.values.map(v => M.check(v[0], v[1], names).why || '');
out.unknown = M.check('--c-nope', '#E11D48', names);
out.noNames = M.check('--c-brand', '#e11d48');
const src = fs.readFileSync(process.argv[3], 'utf8'), m = /\/\* hd-token-kind[^*]*\*\/([\s\S]*?)\/\* \/hd-token-kind \*\//.exec(src);
out.paletteFound = !!m;
if (m) { const tk = vm.runInThisContext('(function () {' + m[1] + '; return tokenKind; })()'); out.palette = T.kinds.map(k => tk(k[0])); }
out.typeLine = M.fields({token: '--fs-body', kind: 'size', vars: {'--fs-body': '16px', '--fw-body': '400', '--lh-body': '1.55'}});
out.typeNoFw = M.fields({token: '--fs-sub', kind: 'size', vars: {'--fs-sub': '14px'}});
out.color = M.fields({token: '--c-brand', kind: 'color', vars: {'--c-brand': ' #1b1b1b '}});
out.colorRgb = M.fields({token: '--c-overlay', kind: 'color', vars: {'--c-overlay': 'rgba(27, 27, 27, .45)'}});
out.space = M.fields({token: '--stack-s', kind: 'space', vars: {'--stack-s': '0.5rem'}});
out.zero = M.fields({token: '--stack-s', kind: 'space', vars: {'--stack-s': '0'}});
out.shadow = M.fields({token: '--shadow-1', kind: 'shadow', vars: {'--shadow-1': '0 2px 8px rgba(0,0,0,.08)'}});
out.compose = [M.compose(out.space[0], '12'), M.compose(out.color[0], '#e11d48'), M.compose(out.typeLine[1], '600')];
out.pickOn = M.pickMsg(true); out.pickOff = M.pickMsg(false);
out.read = M.readPick({type: 'hd-sel', path: 'div.sw', token: '--c-brand', tokenKind: 'color', label: '  주 색 ', rect: {x: 1, y: 2, w: 3, h: 4}, vars: {'--c-brand': '#1B1B1B'}});
out.readBad = [M.readPick(null), M.readPick({type: 'hd-sel', path: 'x'}), M.readPick({type: 'hd-sel', token: 'c-brand; x'}), M.readPick({type: 'hd-sel', token: '--c-brand', rect: 'no'})];
out.href = [M.href('tokens.css', 'class101', 0), M.href('tokens.css', '@project', 7), M.href('../tokens.css?v=3', '', 9), M.href('tokens.css', null, 0)];
out.docTab = ['screens', 'foundation', 'components', 'x', null].map(M.docTab);
const F = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
out.families = typeof M.family === 'function' ? F.families.map(f => M.family(f[0])) : null;
out.pairs = typeof M.same === 'function' ? F.pairs.map(p => M.same(p[0], p[1])) : null;
out.part = M.readPick({type: 'hd-sel', doc: true, path: 'button.btn', label: ' 버튼 ', rect: {x: 1, y: 2, w: 3, h: 4},
                       part: {key: 'btn', title: '버튼', classes: ['btn', 'primary', 'x"><b'], tag: 'BUTTON', state: 'disabled'}});
out.partBad = [M.readPick({type: 'hd-sel', doc: true, rect: {x: 1, y: 2, w: 3, h: 4}, part: {classes: []}}),
               M.readPick({type: 'hd-sel', doc: true, rect: {x: 1, y: 2, w: 3, h: 4}, part: 'btn'})];
out.reload = typeof M.reloadMsg === 'function' ? [M.reloadMsg('tokens', 't1'), M.reloadMsg('components', 'c2'), M.reloadMsg('x', 1)] : null;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    p = subprocess.run([NODE, "-e", JS, str(MOD), str(HERE / "fixtures" / "token-values.json"), str(PALETTE),
                        str(HERE / "fixtures" / "component-families.json")],
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_kind_is_the_same_table_as_python(r):
    assert r["kinds"] == [k for _, k in TABLE["kinds"]]


def test_value_rule_is_the_same_table_as_python(r):
    assert r["values"] == [w for _, _, w in TABLE["values"]]
    refused = [why for (_, _, w), why in zip(TABLE["values"], r["whys"]) if w is None]
    assert all(refused), "거절에는 까닭이 있다"
    assert r["unknown"]["ok"] is False and "--c-nope" in r["unknown"]["why"]
    assert r["noNames"] == {"ok": True, "value": "#E11D48", "why": ""}, "이름 목록이 없으면 모양만 본다(칸 검사)"


def test_palette_token_kind_follows_the_same_rule(r):
    assert r["paletteFound"], "palette.js 에 /* hd-token-kind */ … /* /hd-token-kind */ 표시가 없다"
    assert r["palette"] == [k for _, k in TABLE["kinds"]]


def test_type_line_edits_size_weight_and_line_height(r):
    assert [(f["name"], f["kind"], f["input"]) for f in r["typeLine"]] == [
        ("--fs-body", "size", "len"), ("--fw-body", "weight", "num"), ("--lh-body", "line", "num")]
    assert (r["typeLine"][0]["num"], r["typeLine"][0]["unit"]) == ("16", "px")
    assert [f["name"] for f in r["typeNoFw"]] == ["--fs-sub"], "없는 짝 토큰은 칸이 없다"


def test_fields_keep_the_current_unit_and_form(r):
    c = r["color"][0]
    assert (c["input"], c["value"], c["hex"]) == ("color", "#1b1b1b", "#1B1B1B")
    assert r["colorRgb"][0]["hex"] == "", "hex 가 아닌 색 = 색 고르기 판은 비우고 글 칸에 원래 값"
    assert (r["space"][0]["num"], r["space"][0]["unit"]) == ("0.5", "rem"), "지금 단위 그대로"
    assert (r["zero"][0]["num"], r["zero"][0]["unit"]) == ("0", "px")
    assert r["shadow"][0]["input"] == "text"
    assert r["compose"] == ["12rem", "#E11D48", "600"]


def test_pick_message_shape(r):
    assert r["pickOn"] == {"type": "hd-pick", "on": True, "mode": "select", "doc": True}
    assert r["pickOff"] == {"type": "hd-pick", "on": False, "mode": "", "doc": True}
    assert r["read"] == {"token": "--c-brand", "kind": "color", "label": "주 색", "rect": {"x": 1, "y": 2, "w": 3, "h": 4}, "vars": {"--c-brand": "#1B1B1B"}}
    assert r["readBad"] == [None, None, None, None]


def test_token_href_and_doc_tabs(r):
    assert r["href"] == ["tokens-class101.css", "tokens.css?v=7", "../tokens.css?v=9", "tokens.css"]
    assert r["docTab"] == [False, True, True, False, False]


# ---- phase C(부품)
FAM = json.loads((HERE / "fixtures" / "component-families.json").read_text(encoding="utf-8"))


def test_family_rule_is_the_same_table_as_python(r):
    """부품 칸은 같은 묶음 토큰만(사용자 결정) — Python component_edit.family·same 과 같은 표."""
    assert r["families"] == [f for _, f in FAM["families"]]
    assert r["pairs"] == [ok for _, _, ok in FAM["pairs"]]


def test_read_part_pick(r):
    assert r["part"] == {"kind": "part", "label": "버튼", "rect": {"x": 1, "y": 2, "w": 3, "h": 4},
                         "part": {"key": "btn", "title": "버튼", "classes": ["btn", "primary"], "tag": "button", "state": "disabled"}}
    assert r["partBad"] == [None, None], "클래스 없는 부품·모양이 틀린 부품 = 고르지 않음"


def test_reload_message_names_the_stylesheet(r):
    assert r["reload"] == [{"type": "hd-css-reload", "sheet": "tokens", "v": "t1"},
                           {"type": "hd-css-reload", "sheet": "components", "v": "c2"}, None]
