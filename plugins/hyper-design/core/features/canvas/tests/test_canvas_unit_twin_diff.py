"""V2 — 캔버스 화면 ↔ 앱 화면 맞음 비교(unit — modules/twin-diff.js, 순수 · AI 없음 · 같은 입력 = 같은 결과).
짝 = (역할, 정규화한 글자), 같은 글자가 여럿이면 차례로. 못 짝지은 것은 missing(앱에 없음) · extra(앱에만) · unsure(확실하지 않음 — 역할만 다름 ·
같은 자리 글자 다름 · 같은 글자 수가 다름). 짝지은 것의 스타일은 허용 오차(색 거리 · px 1) 밖이면 style. 브라우저 = test_canvas_twin.py."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/twin-diff.js', 'utf8'), {filename: 'twin-diff.js'});
const D = globalThis.HD.twinDiff, out = {};
const st = (o) => Object.assign({color: 'rgb(17, 17, 17)', bg: 'rgba(0, 0, 0, 0)', fs: 16, fw: 400, radius: 0}, o || {});
const it = (role, text, s) => ({role: role, text: text, tag: 'x', style: st(s)});
const A = [it('heading', '결제'), it('text', '카드를 고르세요'), it('button', '지금 결제하기'), it('link', '다음')];
out.same = D.diff(A, A.map(x => Object.assign({}, x)));
out.again = JSON.stringify(D.diff(A, A)) === JSON.stringify(D.diff(A, A));
out.spaces = D.diff([it('text', '  카드를\n  고르세요 ')], [it('text', '카드를 고르세요')]);
out.norm = [D.norm(' a   b​ '), D.norm(null), D.norm('é')];
out.missing = D.diff(A, [A[0], A[1], A[3]]);
out.extra = D.diff(A, A.concat([it('link', '도움말')]));
const dupA = [it('button', '삭제', {color: 'rgb(0, 0, 0)'}), it('button', '삭제', {color: 'rgb(255, 0, 0)'})];
const dupB = [it('button', '삭제', {color: 'rgb(0, 0, 0)'}), it('button', '삭제', {color: 'rgb(0, 0, 255)'})];
out.dup = D.diff(dupA, dupB);
out.dupCount = D.diff(dupA.concat([it('button', '삭제', {color: 'rgb(0, 0, 0)'})]), dupB);
out.within = D.diff([it('button', '저장', {color: 'rgb(10, 20, 30)', fs: 16, radius: 8})],
                    [it('button', '저장', {color: 'rgb(12, 22, 33)', fs: 16.8, radius: 8.9})]);
out.over = D.diff([it('button', '저장', {color: 'rgb(10, 20, 30)', bg: '#ffffff', fs: 16, fw: 400, radius: 8})],
                  [it('button', '저장', {color: 'rgb(40, 20, 30)', bg: 'rgb(255, 255, 255)', fs: 18, fw: 600, radius: 8})]);
out.clear = D.diff([it('text', 'a', {bg: 'rgba(0, 0, 0, 0)'})], [it('text', 'a', {bg: 'rgba(255, 255, 255, 0)'})]);
out.role = D.diff([it('button', '다음')], [it('link', '다음')]);
out.changed = D.diff(A, [A[0], A[1], it('button', '결제하기'), A[3]]);
out.empty = [D.diff([], []), D.diff(null, undefined), D.diff([{nope: 1}, it('text', 'a')], [it('text', 'a')])];
out.counts = [D.count(out.same), D.count(out.missing), D.count(out.over), D.count(out.changed), D.count(null)];
out.color = [D.color('rgb(1, 2, 3)'), D.color('rgba(1,2,3,0.5)'), D.color('#0a0b0c'), D.color('transparent'), D.color('oklch(1 0 0)')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-twin-diff-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_exact_match_is_all_pairs_and_no_differences(out):
    d = out["same"]
    assert d == {"match": 4, "missing": [], "extra": [], "style": [], "unsure": []}
    assert out["again"], "같은 입력 = 같은 결과(글자 그대로)"
    assert out["spaces"]["match"] == 1, "공백·줄바꿈은 정규화해서 견준다"
    assert out["norm"] == ["a b", "", "é"], "nbsp·0폭 글자 지움 · 공백 하나로 · NFC"


def test_missing_and_extra_name_the_item_and_its_index(out):
    assert out["missing"]["missing"] == [{"a": 2, "b": None, "role": "button", "text": "지금 결제하기"}]
    assert out["missing"]["match"] == 3 and not out["missing"]["extra"]
    assert out["extra"]["extra"] == [{"a": None, "b": 4, "role": "link", "text": "도움말"}]
    assert out["extra"]["match"] == 4 and not out["extra"]["missing"]


def test_duplicate_text_pairs_in_order(out):
    d = out["dup"]
    assert d["match"] == 1 and len(d["style"]) == 1, d
    s = d["style"][0]
    assert (s["a"], s["b"]) == (1, 1), "둘째 '삭제' 는 둘째 '삭제' 와 — 차례로"
    assert s["props"] == [{"prop": "color", "a": "rgb(255, 0, 0)", "b": "rgb(0, 0, 255)"}]
    c = out["dupCount"]
    assert c["unsure"] == [{"a": 2, "b": None, "role": "button", "text": "삭제", "why": "dup", "other": None}], \
        "같은 글자 수가 다르면 어느 것이 빠졌는지 확실하지 않다 — missing 이 아니라 unsure"
    assert not c["missing"]


def test_style_within_tolerance_matches_and_over_it_lists_each_prop(out):
    assert out["within"]["match"] == 1 and not out["within"]["style"], "색 거리 · px 1 안은 같다"
    s = out["over"]["style"]
    assert len(s) == 1 and out["over"]["match"] == 0
    assert [p["prop"] for p in s[0]["props"]] == ["color", "fs", "fw"], "bg #ffffff = rgb(255,255,255) 는 같다 · radius 같음"
    assert s[0]["props"][1] == {"prop": "fs", "a": 16, "b": 18}
    assert out["clear"]["match"] == 1, "둘 다 투명이면 rgb 가 달라도 같다"


def test_unsure_is_reported_not_guessed(out):
    r = out["role"]
    assert r["unsure"] == [{"a": 0, "b": 0, "role": "button", "text": "다음", "why": "role", "other": {"role": "link", "text": "다음"}}]
    assert not r["missing"] and not r["extra"]
    c = out["changed"]
    assert c["unsure"] == [{"a": 2, "b": 2, "role": "button", "text": "지금 결제하기", "why": "text", "other": {"role": "button", "text": "결제하기"}}], \
        "같은 자리(앞뒤 짝 사이)에서 같은 역할의 글자만 다르면 하나의 불확실 — 빠짐+더함 둘이 아니다"
    assert c["match"] == 3 and not c["missing"] and not c["extra"]


def test_bad_input_is_empty_not_a_throw_and_count_sums_differences(out):
    e0, e1, e2 = out["empty"]
    assert e0 == e1 == {"match": 0, "missing": [], "extra": [], "style": [], "unsure": []}
    assert e2["match"] == 1 and not e2["missing"], "모양이 틀린 항목은 건너뛴다(차례 번호는 원래 것)"
    assert out["counts"] == [0, 1, 1, 1, 0]


def test_color_parse(out):
    assert out["color"] == [[1, 2, 3, 1], [1, 2, 3, 0.5], [10, 11, 12, 1], [0, 0, 0, 0], None]
