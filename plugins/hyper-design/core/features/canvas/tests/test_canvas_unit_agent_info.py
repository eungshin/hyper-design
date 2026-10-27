"""받는 터미널 정보 Model(R28) — modules/agent-info.js · attach.js paths 순수 함수(node). 브라우저 없음.

parse: 도우미 답 → 보일지·모델·생각 깊이·선택지·컨텍스트(모양 틀린 컨텍스트 = null → 고리 숨김, 0% 가 아님) ·
short/tip: '340k / 1M' 툴팁 글 · ring: 고리 길이 · menu: 지금 것 표시 · attach.paths: 요청문의 '첨부 이미지:' 경로(들여 쓴 줄 · 한 번 · 6장).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['agent-info.js', 'attach.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const I = globalThis.HD.agentInfo, A = globalThis.HD.attach, out = {};
const full = {agent: 'a1', paseo: true, name: 'HD2', provider: 'claude', model: 'claude-opus-5-5', modelLabel: 'Opus 5.5', effort: 'medium',
              effortOptions: ['low', 'medium', 'high', 'xhigh', 'max', 3], context: {used: 340000, max: 1000000, pct: 34}};
out.full = I.parse(full);
out.none = I.parse({agent: null, paseo: false});
out.notPaseo = I.parse({agent: 'hello', paseo: false});
out.bad = [I.parse(null), I.parse('x')];
out.badCtx = [I.parse(Object.assign({}, full, {context: null})).ctx, I.parse(Object.assign({}, full, {context: {used: -1, max: 10, pct: 3}})).ctx,
              I.parse(Object.assign({}, full, {context: {used: 1, max: 0, pct: 0}})).ctx, I.parse(Object.assign({}, full, {context: {used: 1, max: 10, pct: 140}})).ctx];
out.zero = I.parse(Object.assign({}, full, {context: {used: 0, max: 1000000, pct: 0}})).ctx;
out.label = [I.parse(Object.assign({}, full, {modelLabel: null})).modelLabel, I.parse({agent: 'c', paseo: true, provider: 'codex'}).modelLabel];
out.short = [I.short(340000), I.short(1000000), I.short(1200000), I.short(950), I.short(200000), I.short(1499), I.short(-1)];
out.tip = I.tip({used: 340000, max: 1000000, pct: 34});
out.tipNone = I.tip(null);
out.ring = [I.ring(34, 6), I.ring(0, 6), I.ring(150, 6)];
out.effort = [I.effortLabel('high'), I.effortLabel(null)];
out.menu = I.menu(['low', 'medium'], 'medium');
out.same = [I.same(I.parse(full), I.parse(full)), I.same(I.parse(full), I.parse(Object.assign({}, full, {effort: 'high'})))];
out.modelTip = I.MODEL_TIP;
out.paths = A.paths('요청: 이 화면처럼\n  첨부 이미지: C:\\o\\.hd-attach\\1.png\n첨부 이미지: C:\\o\\.hd-attach\\2.jpg\n첨부 이미지: C:\\o\\.hd-attach\\1.png\n본문 첨부 이미지: 아님');
let many = ''; for (let i = 0; i < 9; i++) many += '첨부 이미지: /o/' + i + '.png\n';
out.pathsCap = A.paths(many).length;
out.pathsNone = [A.paths(''), A.paths(null)];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def res():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-ainfo-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_parse_full_answer(res):
    assert res["full"] == {"show": True, "agent": "a1", "model": "claude-opus-5-5", "modelLabel": "Opus 5.5", "effort": "medium",
                           "options": ["low", "medium", "high", "xhigh", "max"], "ctx": {"used": 340000, "max": 1000000, "pct": 34}}


def test_parse_hides_without_paseo_receiver(res):
    assert res["none"] == {"show": False, "why": "none"} and res["notPaseo"] == {"show": False, "why": "not-paseo"}
    assert all(b == {"show": False, "why": "bad"} for b in res["bad"])


def test_unknown_context_hides_ring_not_zero(res):
    assert res["badCtx"] == [None, None, None, None], "모르거나 틀린 컨텍스트 = null(고리 숨김)"
    assert res["zero"] == {"used": 0, "max": 1000000, "pct": 0}, "진짜 0 은 0%"
    assert res["label"] == ["claude-opus-5-5", "codex"]


def test_tooltip_words_and_short_numbers(res):
    assert res["short"] == ["340k", "1M", "1.2M", "950", "200k", "1k", "?"]
    assert res["tip"] == "컨텍스트 340k / 1M 토큰 · 34% 사용" and res["tipNone"] == ""
    assert res["modelTip"] == "모델은 Paseo에서 바꿔요"


def test_ring_and_menu(res):
    a, z, over = res["ring"]
    assert a["len"] == pytest.approx(37.7, abs=0.01) and a["dash"] == pytest.approx(12.82, abs=0.01)
    assert z["dash"] == 0 and over["dash"] == over["len"], "0..100 으로 자른다"
    assert res["effort"] == ["high", "자동"]
    assert res["menu"] == [{"id": "low", "label": "low", "on": False}, {"id": "medium", "label": "medium", "on": True}]
    assert res["same"] == [True, False]


def test_attach_paths_from_request_text(res):
    assert res["paths"] == ["C:\\o\\.hd-attach\\1.png", "C:\\o\\.hd-attach\\2.jpg"], "들여 쓴 줄도 · 같은 것 한 번 · 줄 머리만"
    assert res["pathsCap"] == 6 and res["pathsNone"] == [[], []]
