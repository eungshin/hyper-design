"""hd notes · hd wait 의 낡은 앱 부품 경고 한 줄(stderr — --json 은 그대로). 임시 git 저장소 · 임시 HD_HOME. 브라우저 없음."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402,F401
from partsfix import HD_PY, git, hd, make_out, make_repo, parts_json  # noqa: E402,F401


def test_notes_prints_one_stale_warning_line(tmp_path):
    repo, home = make_repo(tmp_path), tmp_path / "home"
    root = tmp_path / "n"
    hdfix.make_out(root)
    out = root / "proj-a" / "out"
    src = make_out(tmp_path, repo)
    shutil.copy(src / "parts.json", out / "parts.json")
    code, so, se = hd(home, "notes", "--out", str(out), "--json")
    assert code == 0, se
    json.loads(so)
    warn = [ln for ln in se.splitlines() if "낡은 앱 부품" in ln]
    assert len(warn) == 1 and "hd parts --rebuild" in warn[0], se
    (out / "parts.json").unlink()
    code, so, se = hd(home, "notes", "--out", str(out))
    assert code == 0 and "낡은 앱 부품" not in se, "parts.json 이 없으면 조용히"
