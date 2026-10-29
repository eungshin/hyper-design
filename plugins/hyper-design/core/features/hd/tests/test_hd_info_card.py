"""정보 카드(R47) Python 미러 — 공유 사례(canvas contract/info-card-cases.json)·순수성·`hd notes` 가 화면마다 카드를 한 번 보이기. 브라우저·도우미 없음."""
import ast, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdfix  # noqa: E402

sys.path.insert(0, str(hdfix.HD))
import hd_info_card as P  # noqa: E402

CASES = hdfix.HD.parent / "canvas" / "contract" / "info-card-cases.json"
HD_PY = hdfix.HD / "hd.py"


def test_shared_cases():
    for c in json.loads(CASES.read_text(encoding="utf-8"))["cases"]:
        data = {"notes": c.get("notes"), "links": c.get("links"), "groups": c.get("groups")}
        lst = P.reach(data, ["folder:" + c["folder"]]) if c.get("folder") else P.collect(data, c["screen"])
        assert [n["id"] for n in lst] == c["expect"], c["name"]
        if "text" in c:
            assert P.text(lst) == c["text"], c["name"]


def test_model_is_pure():
    tree = ast.parse((hdfix.HD / "hd_info_card.py").read_text(encoding="utf-8"))
    bad = [",".join(a.name for a in n.names) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert bad == ["re"], "hd_info_card.py 는 re 말고 아무것도 들이지 않는다: %s" % bad


def _notes(out, home):
    r = subprocess.run([sys.executable, str(HD_PY), "notes", "--out", str(out), "--all"], capture_output=True, text=True, encoding="utf-8",
                       env=hdfix.env(home), timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_hd_notes_prints_each_screen_card_once(tmp_path):
    out = hdfix.make_out(tmp_path / "w")
    home = tmp_path / "home"
    before = _notes(out, home)
    assert "유의(정보 카드)" not in before, "연결이 없으면 예전 그대로"
    sj = json.loads((out / "screens.json").read_text(encoding="utf-8"))
    sj["screens"][0]["group"] = "처음"
    (out / "screens.json").write_text(json.dumps(sj, ensure_ascii=False), encoding="utf-8")
    doc = json.loads((out / ".hd-canvas.json").read_text(encoding="utf-8"))
    doc["state"]["board-notes"] = {"a": {"x": 0, "y": 0, "w": 280, "text": "버튼은 하나만", "at": 1},
                                   "b": {"x": 0, "y": 0, "w": 280, "text": "줄 전체: 존댓말", "at": 2}}
    doc["state"]["board-links"] = {"l1": {"from": "note:a", "to": "screen:home", "at": "x"}, "l2": {"from": "note:b", "to": "folder:처음", "at": "x"}}
    (out / ".hd-canvas.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    text = _notes(out, home)
    assert text.count("유의(정보 카드):") == 1, text
    lines = text.splitlines()
    i = lines.index("    유의(정보 카드):")
    assert lines[i - 1].startswith("home #") and lines[i + 1:i + 3] == ["    - 버튼은 하나만", "    - 줄 전체: 존댓말"], text
    stripped = "\n".join(lines[:i] + lines[i + 3:])
    assert stripped == before.rstrip("\n"), "카드 줄을 빼면 예전 출력과 같다"
    r = subprocess.run([sys.executable, str(HD_PY), "notes", "--out", str(out), "--all", "--json"], capture_output=True, text=True,
                       encoding="utf-8", env=hdfix.env(home), timeout=30)
    assert list(json.loads(r.stdout)) == ["project", "out", "rev", "helper", "which", "notes"], "--json 모양은 그대로"
