"""표면 프로필(TDR surface) — setup_out이 surface.json을 쓰고, 레퍼런스 테마가 기본값이 되고, 캔버스가 프로필 크기를 쓰고, 프로필이 없으면 오늘(폰) 그대로."""
import json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
CORE = SCRIPTS.parent
SURF = CORE / "surfaces"
CANVAS = CORE / "features" / "canvas"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
sys.path.insert(0, str(SURF)); sys.path.insert(0, str(CANVAS))
import surface  # noqa: E402
import board_data  # noqa: E402

SLOTS = {"name", "label", "frame", "viewport", "market", "flow", "kinds", "states", "audit", "images", "principles", "type", "writer"}


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", env=ENV)


def test_every_profile_has_every_slot_and_examples_exist():
    for name in surface.names():
        p = surface.resolve(name)
        assert SLOTS <= set(p), (name, SLOTS - set(p))
        for f in p["kinds"].values():
            assert (CORE / "foundation" / "examples" / f).exists(), (name, f)


def test_desktop_default_for_layout_without_profile():
    p = surface.resolve("desktop-dashboard")
    assert p["fallback_of"] == "desktop-wizard"
    assert p["frame"]["card"] == {"w": 1080, "h": 680}
    assert p["flow"] == surface.resolve("mobile")["flow"]


def test_setup_out_writes_surface_and_theme(tmp_path):
    out = tmp_path / "out"
    r = run("setup_out.py", out, "--domain", "학습", "--tags", "차분", "--surface", "desktop-wizard", "--theme", "dayfine-dawn.json")
    assert r.returncode == 0, r.stdout + r.stderr
    s = json.loads((out / "surface.json").read_text(encoding="utf-8"))
    assert s["name"] == "desktop-wizard" and s["frame"]["card"]["w"] == 1080
    pal = json.loads((out / "palettes.json").read_text(encoding="utf-8"))
    assert pal["default"] == "dayfine-dawn" and len(pal["options"]) == 3
    tokens = (out / "tokens.css").read_text(encoding="utf-8")
    assert "--c-shell: linear-gradient(" in tokens and "--c-highlight:" in tokens


def test_setup_out_default_is_mobile_without_theme(tmp_path):
    out = tmp_path / "out"
    r = run("setup_out.py", out, "--domain", "생활", "--tags", "생활")
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((out / "surface.json").read_text(encoding="utf-8"))["name"] == "mobile"
    assert "--c-shell" not in (out / "tokens.css").read_text(encoding="utf-8")


def test_canvas_frame_from_profile_and_phone_fallback(tmp_path):
    assert board_data.frame(tmp_path) == (0.72, {"w": 375, "h": 812}, {"w": 390, "h": 844}, 28)
    (tmp_path / "surface.json").write_text(json.dumps(surface.resolve("desktop-wizard"), ensure_ascii=False), encoding="utf-8")
    scale, card, modal, radius = board_data.frame(tmp_path)
    assert card == {"w": 1080, "h": 680} and modal == {"w": 1080, "h": 680} and radius == 16 and scale == 0.4
