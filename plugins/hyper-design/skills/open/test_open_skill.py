"""open 스킬 계약 테스트 — frontmatter, 부르는 명령·경로가 실제로 있는지, go 를 다시 쓰지 않는지."""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE / "SKILL.md"
CORE = HERE.parents[1] / "core"


def _split():
    src = SKILL.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", src, re.S)
    assert m, "frontmatter missing"
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm, m.group(2)


def test_frontmatter():
    fm, _ = _split()
    assert fm["name"] == "open"
    assert "프로젝트" in fm["description"] and "/hyper-design:open" in fm["description"]


def test_referenced_paths_exist():
    _, body = _split()
    for rel in re.findall(r"\$SK/([\w/.\-]+\.py)", body):
        assert (CORE / rel).is_file(), rel
    assert (CORE / "features" / "canvas" / "build_ref.py").is_file()
    assert (HERE.parent / "go" / "SKILL.md").is_file(), "새로 → /hyper-design:go"


def test_commands_match_cli():
    _, body = _split()
    used = set(re.findall(r"hd\.py (\w+)", body))
    assert used == {"projects", "open", "save"}, used
    for flag in ("--no-open", "--agent", "--out", "--name"):
        assert flag in body, flag
    helptext = subprocess.run([sys.executable, str(CORE / "features" / "hd" / "hd.py"), "--help"], capture_output=True, text=True,
                              encoding="utf-8").stdout
    for cmd in used | {"forget"}:
        assert cmd in helptext, cmd
    for cmd, flags in (("open", ("--agent", "--no-open")), ("save", ("--out", "--name"))):
        h = subprocess.run([sys.executable, str(CORE / "features" / "hd" / "hd.py"), cmd, "--help"], capture_output=True, text=True,
                           encoding="utf-8").stdout
        assert all(f in h for f in flags), (cmd, h)


def test_short_and_delegates_to_go():
    _, body = _split()
    assert "/hyper-design:go" in body and "PASEO_AGENT_ID" in body and "[[ASK]]" in body
    assert "save_prd.py" not in body and "build_canvas.py" not in body, "go 의 단계를 다시 쓰지 않는다"
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) <= 60
