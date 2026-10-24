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


# ── 템플릿 선 CSS 와 line-tone.js 가 같은 말을 하는지(손으로 옮긴 규칙의 지킴이) ──
# 템플릿의 `path.ln` stroke-opacity 규칙을 작은 캐스케이드(특이도 + 차례)로 상태마다 풀고,
# 그 상태에서 HD.lineTone.tone() 이 고른 단계의 화살촉 fill-opacity 값과 글자 그대로 같아야 한다.
import itertools, re

TEMPLATE = HERE.parent / "canvas_template.html"
STATE_KEYS = ("focusing", "hover", "on", "em", "pd")
ROW_CLASS = {"lnhov": "hover", "focusing": "focusing"}   # #rows.<이름> → 상태
PATH_CLASS = {"on", "em", "pd", "ln"}                    # 선 path 에 붙는 상태 클래스(그 밖 클래스 규칙은 이 지킴이 밖)


def _norm(v):
    return re.sub(r"\s+", "", v)


def _rules(css):
    """(선택자, 선언 dict, 차례) — 주석 뺀 평평한 규칙만(@규칙 안은 이 지킴이 밖)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = []
    for i, m in enumerate(re.finditer(r"([^{}]+)\{([^{}]*)\}", css)):
        decl = {}
        for d in m.group(2).split(";"):
            if ":" in d:
                k, v = d.split(":", 1)
                decl[k.strip()] = v.strip()
        for sel in m.group(1).split(","):
            out.append((sel.strip(), decl, i))
    return out


def _line_match(sel, st):
    """선 path 선택자면 (맞음, 특이도) — 모르는 모양이면 None."""
    parts = sel.split()
    if not parts or not re.fullmatch(r"path(\.[\w-]+)+", parts[-1]):
        return None
    pcls = parts[-1].split(".")[1:]
    if "ln" not in pcls or any(c not in PATH_CLASS for c in pcls):
        return None
    ids, cls, typ = 0, len(pcls), 1
    ok = all(st[c] for c in pcls if c != "ln")
    for anc in parts[:-1]:
        if anc == "svg.ar":
            cls, typ = cls + 1, typ + 1
            continue
        m = re.fullmatch(r"#rows\.([\w-]+)", anc)
        if not m or m.group(1) not in ROW_CLASS:
            return None
        ids, cls = ids + 1, cls + 1
        ok = ok and st[ROW_CLASS[m.group(1)]]
    return ok, (ids, cls, typ)


def _line_opacity(rules, st):
    best = None
    for sel, decl, order in rules:
        if "stroke-opacity" not in decl or "!important" in decl["stroke-opacity"]:
            continue
        r = _line_match(sel, st)
        if r and r[0] and (best is None or (r[1], order) >= best[0]):
            best = ((r[1], order), decl["stroke-opacity"])
    return _norm(best[1])


def _marker_opacity(rules):
    out = {}
    for sel, decl, _ in rules:
        if "fill-opacity" not in decl:
            continue
        m = re.fullmatch(r"svg\.ar marker\.lnm(?:\[data-tone=\"(\w+)\"\])? path", sel)
        if m:
            out[m.group(1) or "base"] = _norm(decl["fill-opacity"])
    return out


TONE_ALL = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/line-tone.js', 'utf8'), {filename: 'line-tone.js'});
const states = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
console.log(JSON.stringify(states.map((s) => globalThis.HD.lineTone.tone(s))));
"""


def check_css_agrees(template_text, mod_dir):
    """틀린 상태 목록(빈 목록 = 같음). 테스트가 일부러 바꾼 사본으로도 부를 수 있게 함수로 둔다."""
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", template_text, flags=re.S))
    rules = _rules(css)
    marks = _marker_opacity(rules)
    assert set(marks) == {"base", "hov", "faint", "full"}, f"화살촉 단계 CSS 를 못 찾음: {marks}"
    states = [dict(zip(STATE_KEYS, bits)) for bits in itertools.product([False, True], repeat=len(STATE_KEYS))]
    tmp = Path(tempfile.mkdtemp(prefix="hd-tone-css-"))
    try:
        (tmp / "t.js").write_text(TONE_ALL, encoding="utf-8")
        (tmp / "s.json").write_text(json.dumps(states), encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(mod_dir), str(tmp / "s.json")],
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        tones = json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = []
    for st, t in zip(states, tones):
        line = _line_opacity(rules, st)
        if marks.get(t) != line:
            bad.append((st, t, marks.get(t), line))
    return bad


def test_tone_matches_template_line_css(out):
    bad = check_css_agrees(TEMPLATE.read_text(encoding="utf-8"), MOD)
    assert not bad, "선 CSS 와 line-tone.js 가 다름(한쪽을 바꾸면 다른 쪽도): " + "; ".join(
        f"{ {k for k, v in s.items() if v} } tone={t} 화살촉={m} 선={l}" for s, t, m, l in bad[:6])


def test_guard_catches_drift(out):
    """지킴이가 실제로 어긋남을 잡는지 — 템플릿 사본에서 판 강조 흐림 값만 바꾼다."""
    t = TEMPLATE.read_text(encoding="utf-8")
    drift = t.replace("#rows.focusing path.ln{stroke-opacity:.18}", "#rows.focusing path.ln{stroke-opacity:.3}")
    assert drift != t, "고칠 줄을 못 찾음 — 이 테스트의 문자열을 템플릿에 맞춘다"
    assert check_css_agrees(drift, MOD), "흐림 값을 바꿨는데 지킴이가 못 잡음"
