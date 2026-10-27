"""hd parts --check — 앱 부품(out/parts.json) 보기(읽기만). 임시 git 저장소 · 임시 HD_HOME · 도우미 없음. 브라우저 없음."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402,F401
from partsfix import HD_PY, git, hd, make_out, make_repo, parts_json  # noqa: E402,F401


def test_check_lists_parts_and_marks_never_stamped_as_stale(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    out = make_out(tmp_path, repo)
    before = (out / "parts.json").read_bytes()
    code, so, se = hd(home, "parts", "--check", str(out), "--json")
    assert code == 0, se
    rows = json.loads(so)["parts"]
    assert [(r["file"], r["state"], r["stale"]) for r in rows] == [("screens/mock-a.html", "stale", True)], rows
    code, so, se = hd(home, "parts", str(out))
    assert code == 0 and "screens/mock-a.html · 낡음" in so, so
    assert (out / "parts.json").read_bytes() == before, "--check 는 읽기만"

def test_check_unknown_part_name_is_one_line_error(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    out = make_out(tmp_path, repo)
    code, so, se = hd(home, "parts", "--check", "nope", str(out))
    assert code == 1 and se.startswith("hd: ") and "nope" in se and len(se.strip().splitlines()) == 1, se
