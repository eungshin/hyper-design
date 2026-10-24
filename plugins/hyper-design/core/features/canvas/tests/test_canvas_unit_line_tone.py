"""선 화살촉 투명도(#286) Model — modules/line-tone.js 순수 함수 단위 테스트(node). 브라우저 없음.

화살촉은 채운 모양이라 선의 stroke-opacity 가 닿지 않는다 — 선 하나의 상태(판 강조 중·카드에 올림·켜짐·올린 카드 선·반영 대기)에서
선과 같은 투명도 단계(tone)를 정하고, View 가 그 단계의 화살촉(marker)을 단다. 단계는 템플릿 CSS 의 선 stroke-opacity 규칙과 같은 차례:
focusing+on = full · hover+(em|pd) = full · focusing = faint(.18) · hover = hov(투명도 × .4) · pd = full · 나머지 base(투명도).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/line-tone.js', 'utf8'), {filename: 'line-tone.js'});
const T = globalThis.HD.lineTone, out = {};
out.tones = T.TONES;
const s = (o) => T.tone(o);
out.base = s({});
out.pd = s({pd: true});
out.hov = s({hover: true});
out.hovEm = s({hover: true, em: true});
out.hovPd = s({hover: true, pd: true});
out.foc = s({focusing: true});
out.focOn = s({focusing: true, on: true});
out.focPd = s({focusing: true, pd: true});
out.focHovEm = s({focusing: true, hover: true, em: true});
out.focHov = s({focusing: true, hover: true});
out.focHovOn = s({focusing: true, hover: true, on: true});
out.onOnly = s({on: true});
out.none = [T.tone(null), T.tone(undefined)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-tone-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_tone_names(out):
    assert out["tones"] == ["base", "hov", "faint", "full"]


def test_plain_and_pending(out):
    assert out["base"] == "base" and out["onOnly"] == "base", "강조가 없으면 켜짐(on)만으로는 진해지지 않는다(CSS 와 같게)"
    assert out["pd"] == "full", "반영 대기 점선은 투명도와 상관없이 진하게"
    assert out["none"] == ["base", "base"], "상태가 없으면 기본"


def test_hover_dims_others(out):
    assert out["hov"] == "hov" and out["hovEm"] == "full" and out["hovPd"] == "full"


def test_focusing(out):
    assert out["foc"] == "faint" and out["focOn"] == "full"
    assert out["focPd"] == "faint", "판 강조 중엔 반영 대기 선도 흐리게(CSS #rows.focusing 이 이긴다)"
    assert out["focHovEm"] == "full" and out["focHov"] == "faint" and out["focHovOn"] == "full"
