import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
IMGGEN = HERE.parent / "imggen.py"
REPO = HERE.parents[5]
REAL_SHEET = REPO / "runs/imggen-test/sheet-items.png"
sys.path.insert(0, str(HERE.parent))
import imggen  # noqa: E402

FAKE_GEN = r'''
import re, sys
from PIL import Image, ImageDraw
prompt, path = sys.argv[1], sys.argv[2]
m = re.search(r"(\d+) columns x (\d+) rows", prompt)
cols, rows = int(m.group(1)), int(m.group(2))
ar = re.search(r"(\d+):(\d+) aspect ratio", prompt)
rw, rh = int(ar.group(1)), int(ar.group(2))
cw = 200; ch = round(cw * rh / rw); g = 24
W, H = g + cols * (cw + g), g + rows * (ch + g)
im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
for r in range(rows):
    for c in range(cols):
        x, y = g + c * (cw + g), g + r * (ch + g)
        d.rectangle((x, y, x + cw - 1, y + ch - 1), fill=(230, 228, 222))
        d.ellipse((x + 40, y + 30, x + cw - 40, y + ch - 30), fill=((r * 60) % 255, (c * 70) % 255, 120))
im.save(path)
'''


def synth_sheet(path, cols=4, rows=4, cell=200, gap=24):
    W, H = gap + cols * (cell + gap), gap + rows * (cell + gap)
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    k = 0
    for r in range(rows):
        for c in range(cols):
            x, y = gap + c * (cell + gap), gap + r * (cell + gap)
            d.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(228, 226, 220))
            d.rectangle((x + 50, y + 50, x + cell - 50, y + cell - 50), fill=((k * 37) % 255, (k * 91) % 255, (k * 53) % 255))
            k += 1
    im.save(path)


def border_has_white(cell):
    w, h = cell.size
    px = cell.load()
    for x in range(w):
        for y in (0, 1, h - 2, h - 1):
            if px[x, y] == (255, 255, 255):
                return True
    for y in range(h):
        for x in (0, 1, w - 2, w - 1):
            if px[x, y] == (255, 255, 255):
                return True
    return False


def make_out(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    slots = [{"slot": f"p{i}", "kind": "photo", "what": f"물건 {i}", "ratio": "1:1", "en": f"object number {i}"} for i in range(5)]
    slots.append({"slot": "ic-basket", "kind": "icon", "what": "바구니", "en": ["basket"]})
    slots.append({"slot": "wide", "kind": "photo", "what": "넓은 사진", "ratio": "4:3", "en": ["a wide kitchen table", "table"]})
    (out / "image_slots.json").write_text(json.dumps(slots, ensure_ascii=False), encoding="utf-8")
    return out


def run(out, *args, env_extra=None, home=None):
    env = dict(os.environ)
    env.pop("HD_IMAGE_CMD", None)
    env["PYTHONIOENCODING"] = "utf-8"
    if home:
        env["HOME"] = env["USERPROFILE"] = str(home)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(IMGGEN), str(out), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=120)


def status(out):
    return json.loads((out / ".images/status.json").read_text(encoding="utf-8"))


def credits(out):
    p = out / "credits.json"
    return {c["file"]: c for c in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}


PHOTO_FILES = [f"assets/photos/p{i}.jpg" for i in range(5)] + ["assets/photos/wide.jpg"]


def test_crop_synthetic_4x4(tmp_path):
    p = tmp_path / "sheet.png"
    synth_sheet(p)
    cells, ok = imggen.crop_sheet(p, 4, 4, (1, 1))
    assert ok
    assert len(cells) == 16
    assert not any(border_has_white(c) for c in cells)


def test_fake_generator_done(tmp_path):
    out = make_out(tmp_path)
    gen = tmp_path / "fake_gen.py"
    gen.write_text(FAKE_GEN, encoding="utf-8")
    cmd = f'"{sys.executable}" "{gen}"'
    r = run(out, "--cmd", cmd, home=tmp_path)
    assert r.returncode == 0, r.stderr
    st = status(out)
    assert st["state"] == "done", st
    assert st["generated"] == 6 and st["placeholders"] == 0
    cr = credits(out)
    for f in PHOTO_FILES:
        assert (out / f).exists()
        assert cr[f]["license"] == "generated"
    assert not (out / "assets/photos/ic-basket.jpg").exists()
    w, h = Image.open(out / "assets/photos/wide.jpg").size
    assert (w, h) == (1200, 900)


def test_no_generator_fallback(tmp_path):
    out = make_out(tmp_path)
    r = run(out, "--cmd", str(tmp_path / "does-not-exist"), home=tmp_path / "nohome")
    assert r.returncode == 0, r.stderr
    st = status(out)
    assert st["state"] == "fallback"
    assert st.get("reason") == "no generator"
    for f in PHOTO_FILES:
        assert (out / f).exists()
    assert not any(f in credits(out) for f in PHOTO_FILES)


def test_failing_generator_fallback(tmp_path):
    out = make_out(tmp_path)
    gen = tmp_path / "bad_gen.py"
    gen.write_text("import sys\nsys.stderr.write('boom\\n')\nsys.exit(3)\n", encoding="utf-8")
    r = run(out, "--cmd", f'"{sys.executable}" "{gen}"', home=tmp_path)
    assert r.returncode == 0, r.stderr
    st = status(out)
    assert st["state"] == "fallback"
    assert st["generated"] == 0
    for f in PHOTO_FILES:
        assert (out / f).exists()
    assert not any(f in credits(out) for f in PHOTO_FILES)


def test_placeholders_only(tmp_path):
    out = make_out(tmp_path)
    r = run(out, "--placeholders-only", home=tmp_path)
    assert r.returncode == 0
    st = status(out)
    assert st["state"] == "fallback" and st["reason"] == "placeholders-only"
    assert Image.open(out / "assets/photos/p0.jpg").size == (1200, 1200)


@pytest.mark.skipif(not REAL_SHEET.exists(), reason="real sheet not present")
def test_real_sheet_crop():
    cells, _ = imggen.crop_sheet(REAL_SHEET, 4, 4, (1, 1))
    assert len(cells) == 16
