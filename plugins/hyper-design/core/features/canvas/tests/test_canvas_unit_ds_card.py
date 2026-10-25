"""판 위 디자인 시스템 카드(S6) Model — modules/ds-card.js 순수 함수 단위 테스트(node). 브라우저 없음.

토큰 이름(tokens.css :root 변수) → 카드 칸(색 네 줄·글자 Aa 셋·단추 셋·입력·모서리·그림자). 값은 늘 var(--…) 참조라
테마를 바꾸면 카드가 화면과 함께 바뀐다. 없는 토큰은 다음 후보 → 그래도 없으면 그 줄을 빼거나 글자 값으로.
토큰이 없으면(목록 없음·색 토큰 0) 카드 없음(null).
"""
import json, shutil, subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

FULL = ["--c-bg", "--c-surface", "--c-line", "--c-text-1", "--c-text-2", "--c-text-3", "--c-brand", "--c-on-brand",
        "--c-brand-text", "--c-brand-tint", "--c-brand-pressed", "--c-accent", "--c-line-strong", "--shadow-1", "--shadow-2",
        "--font", "--fs-title", "--fw-title", "--lh-title", "--fs-h2", "--fs-body", "--fw-body", "--lh-body", "--fs-sub",
        "--fs-caption", "--fw-caption", "--r-s", "--r-m", "--r-l", "--r-pill", "--h-btn-s"]

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/ds-card.js', 'utf8'), {filename: 'ds-card.js'});
const C = globalThis.HD.dsCard, full = JSON.parse(process.argv[2]), out = {};
out.full = C.sections(full);
out.none = [C.sections(null), C.sections([]), C.sections('x'), C.sections(['--fs-body', '--r-m'])];
out.min = C.sections(['--c-brand']);
out.secondary = C.sections(['--c-brand', '--c-secondary', '--c-brand-tint']).colors.filter(c => c.key === 'secondary')[0];
out.junk = C.sections(['--c-brand', 7, null, 'c-text', '--c-text-1; color:red', '--c-bg']);
out.tones = C.tones('--c-brand');
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    p = subprocess.run([NODE, "-e", JS, str(MOD), json.dumps(FULL)], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_four_colour_rows_from_project_tokens(r):
    cols = {c["key"]: c for c in r["full"]["colors"]}
    assert [c["key"] for c in r["full"]["colors"]] == ["primary", "secondary", "accent", "neutral"]
    assert (cols["primary"]["token"], cols["secondary"]["token"], cols["accent"]["token"]) == ("--c-brand", "--c-brand-tint", "--c-accent")
    assert all(len(c["steps"]) >= 5 for c in cols.values()), "줄마다 단계 여러 개"
    assert "var(--c-brand)" in cols["primary"]["steps"][3]["css"], "가운데 단계 = 토큰 그대로"
    # 중립 = 실제 토큰 사다리(바탕 → 글자), 섞은 값이 아니다
    assert [s["css"] for s in cols["neutral"]["steps"]] == ["var(--c-bg)", "var(--c-surface)", "var(--c-line)", "var(--c-line-strong)",
                                                             "var(--c-text-3)", "var(--c-text-2)", "var(--c-text-1)"]


def test_every_value_is_a_live_var_reference(r):
    """모든 색·글자 값이 var(--…) — 숫자를 복사하지 않아야 테마를 바꿀 때 카드가 함께 바뀐다(Stitch 와의 차이)."""
    blob = json.dumps(r["full"])
    assert "#" not in blob.replace("#fff", "").replace("#000", ""), "hex 를 박지 않는다(섞기용 흰·검정만)"
    for t in r["tones"]:
        assert t["css"].count("var(--c-brand)") == 1


def test_type_samples_headline_body_label(r):
    ty = {t["key"]: t for t in r["full"]["type"]}
    assert list(ty) == ["headline", "body", "label"]
    assert ty["headline"]["size"] == "var(--fs-title)" and ty["headline"]["weight"] == "var(--fw-title)"
    assert ty["body"]["size"] == "var(--fs-body)" and ty["label"]["size"] == "var(--fs-caption)"
    assert r["full"]["font"] == "var(--font)"


def test_buttons_input_radius_shadow(r):
    b = {x["key"]: x for x in r["full"]["buttons"]}
    assert list(b) == ["primary", "secondary", "outlined"]
    assert (b["primary"]["bg"], b["primary"]["fg"]) == ("var(--c-brand)", "var(--c-on-brand)")
    assert b["outlined"]["bg"] == "transparent" and "var(--c-line-strong)" in b["outlined"]["border"]
    assert r["full"]["input"]["border"] == "1px solid var(--c-line)" and r["full"]["input"]["radius"] == "var(--r-m)"
    assert r["full"]["radius"] == ["--r-s", "--r-m", "--r-l", "--r-pill"]
    assert r["full"]["shadow"] == ["--shadow-1", "--shadow-2"]


def test_no_tokens_no_card(r):
    assert r["none"] == [None, None, None, None], "목록 없음·빈 목록·잘못된 값·색 토큰 0 = 카드 없음"


def test_fallbacks_when_tokens_are_missing(r):
    m = r["min"]
    assert [c["key"] for c in m["colors"]] == ["primary", "neutral"], "후보가 하나도 없는 색 줄은 뺀다"
    neutral = m["colors"][1]
    assert len(neutral["steps"]) >= 5 and all("var(" not in s["css"] or "--c-brand" not in s["css"] for s in neutral["steps"]), \
        "중립 토큰이 모자라면 회색 단계 글자 값"
    bp = m["buttons"][0]
    assert bp["bg"] == "var(--c-brand)" and bp["fg"] == "#fff", "버튼 위 글자 토큰이 없으면 흰색"
    assert m["type"][1]["size"] == "16px" and m["font"] is None
    assert m["radius"] == [] and m["shadow"] == [] and m["input"]["radius"] == "8px"
    assert r["secondary"]["token"] == "--c-secondary", "이름이 있으면 --c-secondary 먼저"


def test_junk_names_are_dropped_and_counted(r):
    j = r["junk"]
    assert j["bad"] == 4, "숫자·null·-- 없는 이름·CSS 를 끼운 이름은 버리고 센다(View 가 [hd] 경고)"
    assert "red" not in json.dumps(j)
