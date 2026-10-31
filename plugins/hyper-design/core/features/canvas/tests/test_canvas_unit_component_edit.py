"""Components 고치기(R55 phase C) — Python 규칙(component_edit.py, 순수) + 쓰기 한 번(screen_edits.apply_component, .hd-history 원본 → restore).

사용자 결정: 부품 속성은 Foundation 토큰 가운데 **같은 묶음** 안에서만 고른다(자유 값 없음).
component_edit: family(이름) · rules(css) · slots(css, classes, tag, titles) → 그 요소를 겨누는 규칙과 바꿀 칸 ·
check(…) → 까닭 | None · rewrite(css, selector, prop, index, from, to) → 그 var(--from) 하나만 var(--to) 로.
묶음 규칙은 JS(modules/ds-edit.js family)와 같은 표(fixtures/component-families.json) — test_canvas_unit_ds_edit.py 가 같은 표로 견준다."""
import json, os, subprocess, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import component_edit as CE  # noqa: E402
import screen_edits  # noqa: E402
import write_record  # noqa: E402

pytestmark = pytest.mark.unit
TABLE = json.loads((HERE / "fixtures" / "component-families.json").read_text(encoding="utf-8"))

TOKENS = """:root {
  --c-bg: #FAFAFA; --c-brand: #1B1B1B; --c-on-brand: #FFFFFF; --c-accent: #0F7EC2; --c-brand-pressed: #444444;
  --c-disabled-bg: #DEDEDE; --c-text-disabled: #9F9F9F; --c-focus: #737373; --c-text-1: #1B1B1B;
  --fs-strong: 16px; --fs-sub: 14px; --stack-s: 8px; --stack-m: 16px; --block-pad: 24px;
  --r-s: 8px; --r-m: 12px; --r-l: 16px; --h-btn: 56px; --h-btn-s: 44px; --icon: 24px;
}
"""

CSS = """/* components — .btn.primary { background: var(--c-brand) } 이 주석은 규칙이 아니다 */
* { box-sizing: border-box; }
.block .btn { align-self: stretch; }
.btn svg, .done svg { width: 20px; height: 20px; }
.btn { display: inline-flex; gap: var(--stack-s); height: var(--h-btn); padding: 0 var(--block-pad); border-radius: var(--r-m); font-size: var(--fs-strong); font-weight: 600; }
.btn.primary { background: var(--c-brand); color: var(--c-on-brand); }
.btn.primary:active { background: var(--c-brand-pressed); }
.btn:disabled, .btn[aria-disabled="true"] { background: var(--c-disabled-bg); color: var(--c-text-disabled); pointer-events: none; }
.btn:focus-visible, .chip:focus-visible, .row:focus-visible { outline: 2px solid var(--c-focus); outline-offset: 2px; }
.btn.secondary { background: var(--c-bg); color: var(--c-text-1); }
.btn.small { height: var(--h-btn-s); padding: 0 var(--stack-m); font-size: var(--fs-sub); }
.btn.is-loading::after { content: "a;b{"; border: 2px solid var(--c-on-brand); }
@media (min-width: 900px) { .btn.primary { background: var(--c-accent); } }
.chip { background: var(--c-bg); }
.icon-btn { width: var(--icon); }
"""
TITLES = {"btn": "버튼", "chip": "칩", "row": "목록 행"}


def groups(classes, tag="button", css=CSS):
    return CE.slots(css, classes, tag, TITLES)


def by_sel(gs):
    return {g["selector"]: g for g in gs}


# ---- 묶음 규칙(JS 와 같은 표)
def test_family_table():
    assert [CE.family(n) for n, _ in TABLE["families"]] == [f for _, f in TABLE["families"]]
    assert [CE.same(a, b) for a, b, _ in TABLE["pairs"]] == [ok for _, _, ok in TABLE["pairs"]]


# ---- 고른 요소를 겨누는 규칙
def test_primary_button_lists_base_variant_then_states():
    gs = groups(["btn", "primary"])
    sels = [g["selector"] for g in gs]
    assert sels[:2] == [".btn", ".btn.primary"], "바탕 규칙과 변형 먼저"
    assert ".btn.secondary" not in sels and ".btn.small" not in sels, "요소에 없는 클래스의 규칙은 아니다"
    assert ".block .btn" not in sels and ".btn svg, .done svg" not in sels, "다른 요소 안·안쪽 요소를 겨누는 규칙은 아니다"
    assert not any("is-loading" in s for s in sels)
    assert not any(g["selector"] == ".btn.primary" and g.get("media") for g in gs), "@media 안 규칙은 건너뛴다"
    states = [(g["selector"], g["state"]) for g in gs if g["state"]]
    assert states == [(".btn.primary:active", "누를 때"), ('.btn:disabled, .btn[aria-disabled="true"]', "못 누를 때"),
                      (".btn:focus-visible, .chip:focus-visible, .row:focus-visible", "초점")]
    assert all(not g["state"] for g in gs[:2])


def test_slots_are_var_tokens_only_with_plain_labels():
    g = by_sel(groups(["btn", "primary"]))
    assert [(s["label"], s["token"], s["family"]) for s in g[".btn.primary"]["slots"]] == [
        ("배경", "--c-brand", "color"), ("글자 색", "--c-on-brand", "color")]
    base = [(s["prop"], s["label"], s["index"], s["token"]) for s in g[".btn"]["slots"]]
    assert base == [("gap", "간격", 0, "--stack-s"), ("height", "높이", 0, "--h-btn"), ("padding", "안쪽 여백", 0, "--block-pad"),
                    ("border-radius", "모서리", 0, "--r-m"), ("font-size", "글자 크기", 0, "--fs-strong")], "글자 값(600·inline-flex)은 칸이 아니다"


def test_selector_list_naming_other_components_carries_a_note():
    g = by_sel(groups(["btn", "primary"]))
    assert g[".btn:focus-visible, .chip:focus-visible, .row:focus-visible"]["shared"] == ["버튼", "칩", "목록 행"]
    assert g['.btn:disabled, .btn[aria-disabled="true"]']["shared"] == [], "모두 이 요소를 겨누면 함께 바뀌는 것 없음"
    assert g[".btn"]["shared"] == []


def test_rule_without_editable_slot_is_not_listed():
    assert groups(["icon-btn"], "span") == [], "--icon 은 묶음이 없는 토큰 = 바꿀 칸 없음"


# ---- 쓰기 규칙
def test_rewrite_changes_exactly_that_occurrence():
    out = CE.rewrite(CSS, ".btn.primary", "background", 0, "--c-brand", "--c-accent")
    assert ".btn.primary { background: var(--c-accent); color: var(--c-on-brand); }" in out
    assert out.count("var(--c-brand)") == CSS.count("var(--c-brand)") - 1, "주석 안 같은 글은 그대로"
    assert out.replace("var(--c-accent); color", "var(--c-brand); color", 1) == CSS
    two = CE.rewrite(CSS, ".btn.small", "padding", 0, "--stack-m", "--stack-s")
    assert ".btn.small { height: var(--h-btn-s); padding: 0 var(--stack-s);" in two


def test_rewrite_state_rule_and_selector_list():
    a = CE.rewrite(CSS, ".btn.primary:active", "background", 0, "--c-brand-pressed", "--c-text-1")
    assert ".btn.primary:active { background: var(--c-text-1); }" in a
    sel = '.btn:disabled, .btn[aria-disabled="true"]'
    b = CE.rewrite(CSS, sel, "color", 0, "--c-text-disabled", "--c-focus")
    assert '.btn[aria-disabled="true"] { background: var(--c-disabled-bg); color: var(--c-focus);' in b


def test_check_refuses_with_reason():
    names = list(CE.TE.decls(TOKENS))
    ok = CE.check(CSS, names, ".btn.primary", "background", 0, "--c-brand", "--c-accent")
    assert ok is None
    cases = [
        ((".btn.primary", "background", 0, "--c-brand", "--r-m"), "같은 묶음"),            # 다른 묶음
        ((".btn.primary", "background", 0, "--c-brand", "--c-nope"), "없는 토큰"),         # 모르는 토큰
        ((".btn.primary", "background", 0, "--c-bg", "--c-accent"), "--c-brand"),         # from 이 그 자리와 다름
        ((".btn.nope", "background", 0, "--c-brand", "--c-accent"), "규칙"),               # 모르는 선택자
        ((".btn.primary", "border", 0, "--c-brand", "--c-accent"), "속성"),                # 모르는 속성
        ((".btn.primary", "background", 3, "--c-brand", "--c-accent"), "자리"),            # 없는 자리
        ((".btn.primary", "background", 0, "--c-brand", "--c-accent); x: url(y"), "토큰 이름"),
        ((".icon-btn", "width", 0, "--icon", "--icon"), "바꿀 수 없는"),
    ]
    for args, word in cases:
        why = CE.check(CSS, names, *args)
        assert why and word in why, (args, why)
    with pytest.raises(CE.ComponentError):
        CE.rewrite(CSS, ".btn.primary", "background", 0, "--c-bg", "--c-accent")


def test_titles_from_components_html():
    html = '<section class="spec" data-key="btn" data-title="버튼"></section><section data-title="칩" class="spec" data-key="chip">'
    assert CE.titles(html) == {"btn": "버튼", "chip": "칩"}


# ---- 쓰기 한 번(Edge)
def _out(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "tokens.css").write_text(TOKENS, encoding="utf-8", newline="\n")
    (out / "components.css").write_text(CSS, encoding="utf-8", newline="\n")
    (out / "components.html").write_text('<section class="spec" data-key="btn" data-title="버튼"></section>', encoding="utf-8")
    return out


def _ok(out):
    return subprocess.CompletedProcess([], 0, "", "")


def test_apply_component_writes_once_with_history_and_restore(tmp_path):
    out = _out(tmp_path)
    before = (out / "components.css").read_bytes()
    r = screen_edits.apply_component(out, ".btn.primary", "background", 0, "--c-brand", "--c-accent", build=_ok)
    assert r.get("error") is None, r
    assert r["stamp"] and r["to"] == "--c-accent"
    assert "background: var(--c-accent)" in (out / "components.css").read_text(encoding="utf-8")
    assert (out / ".hd-history" / r["stamp"] / "components.css").read_bytes() == before
    back = write_record.restore(out, r["stamp"], build=_ok)
    assert "restored" in back, back
    assert (out / "components.css").read_bytes() == before


def test_apply_component_refuses_without_writing(tmp_path):
    out = _out(tmp_path)
    before = (out / "components.css").read_bytes()
    for args in ((".btn.primary", "background", 0, "--c-brand", "--r-m"), (".btn.primary", "background", 0, "--c-brand", "--c-nope"),
                 (".x", "background", 0, "--c-brand", "--c-accent"), (".btn.primary", "background", "0", "--c-brand", "--c-accent")):
        r = screen_edits.apply_component(out, *args, build=_ok)
        assert r.get("reason") == "invalid" and r["error"], (args, r)
    assert (out / "components.css").read_bytes() == before
    assert not (out / ".hd-history").exists()


def test_component_slots_reads_files(tmp_path):
    out = _out(tmp_path)
    r = screen_edits.component_slots(out, ["btn", "primary"], "button")
    assert [g["selector"] for g in r["rules"]][:2] == [".btn", ".btn.primary"]
    assert r["tokens"]["--c-accent"] == {"value": "#0F7EC2", "label": "포인트 색", "family": "color"}
    assert r["tokens"]["--c-brand"]["label"] == "버튼·강조 색"
    assert "--icon" not in r["tokens"], "묶음이 없는 토큰은 고를 목록에 없다"
    assert screen_edits.component_slots(tmp_path, ["btn"], "button").get("reason") == "missing"


def test_file_watch_reports_components_change(tmp_path):
    import busy
    out = _out(tmp_path)
    (out / "screens.json").write_text(json.dumps({"screens": []}), encoding="utf-8")
    fw = busy.FileWatch()
    assert fw.tick(busy.scan(out, {})) == []
    f = out / "components.css"
    st = f.stat()
    os.utime(f, (st.st_atime, st.st_mtime + 5))
    assert fw.tick(busy.scan(out, {})) == ["@components"]
