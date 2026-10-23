"""fix 스킬 계약 테스트 — frontmatter, 참조, 요청문 예시가 캔버스(modules/edits.js)가 만드는 형식과 맞는지."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE / "SKILL.md"
EDITS = HERE.parents[1] / "core" / "features" / "canvas" / "modules" / "edits.js"

HEADER_RE = re.compile(r"^\[hyper-design 수정 요청\] out=.+ · \d+건$")
ITEM_RE = re.compile(r"^(\d+)\. screen=[^\s·]+ · path=.+$")
TEXT_RE = re.compile(r'^   text=".*" · intent=(change|question)$')
NOTE_RE = re.compile(r"^   요청: .+$")


def _split():
    src = SKILL.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", src, re.S)
    assert m, "frontmatter missing"
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm, m.group(2)


def _example():
    _, body = _split()
    for block in re.findall(r"```\n(.*?)```", body, re.S):
        lines = block.rstrip("\n").splitlines()
        if lines and lines[0].startswith("[hyper-design 수정 요청]"):
            return lines
    raise AssertionError("no example request block")


def test_frontmatter():
    fm, _ = _split()
    assert fm["name"] == "fix"
    assert "[hyper-design 수정 요청]" in fm["description"]


def test_body_refs():
    _, body = _split()
    for s in ("pack.py", "--mode revise", "hyper-design:screen-reviser", "selfcheck.py", "build_ref.py", "class_users.py", "hd.py reply", "--captured"):
        assert s in body, s
    assert 'model: "opus"' not in body
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 80


def test_example_matches_canvas_format():
    lines = _example()
    assert HEADER_RE.match(lines[0]), lines[0]
    n = int(re.search(r"(\d+)건$", lines[0]).group(1))
    items = lines[1:]
    assert len(items) == 3 * n
    for i in range(n):
        m = ITEM_RE.match(items[3 * i])
        assert m and int(m.group(1)) == i + 1, items[3 * i]
        assert TEXT_RE.match(items[3 * i + 1]), items[3 * i + 1]
        assert NOTE_RE.match(items[3 * i + 2]), items[3 * i + 2]
    intents = {TEXT_RE.match(items[3 * i + 1]).group(1) for i in range(n)}
    assert intents == {"change", "question"}


def test_template_emits_same_format():
    # 캔버스가 실제로 만드는 요청문(modules/edits.js request)이 이 스킬이 읽는 형식과 같은지 — 소스 글이 아니라 출력으로 본다
    import json, shutil, subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node 없음")
    # 명령 줄 인자는 ASCII 로만(Windows 코드 페이지가 한글을 깨뜨림) — 여러 줄 메모 하나 + 질문 하나
    js = ("require(%s); const n=[{screen:'a',path:'div:nth-of-type(1)',text:'old',intent:'change',note:'fix it\\nsecond line'},"
          "{screen:'b',path:'body',text:'',intent:'question',note:'why?'}]; process.stdout.write(HD.edits.request(n,'C:/out'))") % json.dumps(str(EDITS))
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, encoding="utf-8", check=True).stdout.splitlines()
    assert HEADER_RE.match(out[0]), out[0]
    items = [i for i, l in enumerate(out) if ITEM_RE.match(l)]
    assert len(items) == 2, out
    for i in items:
        assert TEXT_RE.match(out[i + 1]), out[i + 1]
        assert NOTE_RE.match(out[i + 2]), out[i + 2]


def test_other_places_and_scope_lines_keep_the_format():
    # task 17: 같은 글 두 요소 = 한 항목 + '다른 곳:' 줄, 범위 = '범위:' 줄 — 머리·text·요청 줄은 그대로 읽히고, 덧붙은 줄은 스킬 본문이 말한다
    import json, shutil, subprocess
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node 없음")
    js = ("require(%s); const n=[{screen:'a',path:'a.one',text:'x',intent:'change',note:'bold',no:1},"
          "{screen:'a',path:'a.two',text:'y',intent:'change',note:'bold',no:2},"
          "{screen:'a',path:'body',text:'',intent:'change',note:'gradient',scope:'all',no:3}]; process.stdout.write(HD.edits.request(n,'C:/out'))") % json.dumps(str(EDITS))
    out = subprocess.run([node, "-e", js], capture_output=True, text=True, encoding="utf-8", check=True).stdout.splitlines()
    assert HEADER_RE.match(out[0]) and out[0].endswith(" · 2건"), out[0]
    items = [i for i, l in enumerate(out) if ITEM_RE.match(l)]
    assert items == [1, 5], out
    for i in items:
        assert TEXT_RE.match(out[i + 1]), out[i + 1]
        assert NOTE_RE.match(out[i + 2]), out[i + 2]
    assert out[4].startswith("   다른 곳: a.two") and out[8] == "   범위: 모든 화면", out
    _, body = _split()
    assert "다른 곳:" in body and "범위:" in body
