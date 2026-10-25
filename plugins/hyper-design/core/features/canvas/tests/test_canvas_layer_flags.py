"""숨긴·잠근 화면 표시 정리(polish-1) — 브라우저. 화면 b 를 숨기고 잠근 뒤 screens.json 에서 b 를 빼고 다시 빌드·새로고침,
b 를 같은 id 로 되살려 다시 빌드·새로고침하면 b 는 보이고 잠겨 있지 않다(저장소의 옛 id 는 처음 읽을 때 정리돼 다시 써짐).
규칙은 test_canvas_unit_layer_flags.py(unit)."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

import pytest

from test_canvas_v2 import SCRIPTS, browser, ctx, reload  # noqa: F401
from test_canvas_edit import DAYFINE, layers

SID = "keys"


def _build(out):
    r = subprocess.run([sys.executable, str(SCRIPTS / "build_canvas.py"), str(out)], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert r.returncode == 0, r.stderr


def _stored(pg, prefix):
    return pg.evaluate("(p) => { const k = Object.keys(localStorage).find(k => k.startsWith(p)); return k ? JSON.parse(localStorage.getItem(k) || '[]') : null; }", prefix)


def _row(pg, sid):
    return next((l for l in layers(pg) if l["id"] == sid), None)


@pytest.mark.area("layers")
def test_deleted_then_recreated_screen_comes_back_visible_and_unlocked(ctx):
    if not DAYFINE.exists():
        pytest.skip(f"fixture 없음: {DAYFINE}")
    tmp = Path(tempfile.mkdtemp(prefix="hd-layer-flags-"))
    out = tmp / "out"
    shutil.copytree(DAYFINE, out)
    sj = out / "screens.json"
    full = sj.read_text(encoding="utf-8")
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    try:
        _build(out)
        pg.goto((out / "index.html").resolve().as_uri())
        pg.wait_for_function("window.__hdReady !== undefined")
        pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('hd-')).forEach(k => localStorage.removeItem(k))")
        reload(pg)
        # 1) b 숨기고 잠그기(레이어 패널 눈·자물쇠)
        pg.click('#dock .dk-tab[data-p="layers"]')
        pg.click(f'#lyTree [data-ly="{SID}"] .ly-eye')
        pg.click(f'#lyTree [data-ly="{SID}"] .ly-lock')
        assert _row(pg, SID)["lock"] and not pg.locator(f'.card[data-id="{SID}"]').is_visible()
        assert _stored(pg, "hd-hidden:") == [SID] and _stored(pg, "hd-locked:") == [SID]
        # 2) b 를 데이터에서 빼고 다시 빌드 → 새로고침: 저장소의 b 도 빠진다
        d = json.loads(full)
        d["screens"] = [s for s in d["screens"] if s["id"] != SID]
        sj.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        _build(out)
        reload(pg)
        assert pg.locator(f'.card[data-id="{SID}"]').count() == 0
        assert _stored(pg, "hd-hidden:") == [] and _stored(pg, "hd-locked:") == [], ("없는 화면 id 는 읽을 때 정리해 다시 쓴다", _stored(pg, "hd-hidden:"), _stored(pg, "hd-locked:"))
        # 3) b 를 같은 id 로 되살려 다시 빌드 → 새로고침: 보이고 잠겨 있지 않다
        sj.write_text(full, encoding="utf-8")
        _build(out)
        reload(pg)
        pg.wait_for_selector(f'.card[data-id="{SID}"]', state="attached")
        assert not pg.evaluate("(id) => document.querySelector('.card[data-id=\"' + id + '\"]').classList.contains('hid')", SID), "되살린 화면이 숨겨져 있다"
        pg.click('#dock .dk-tab[data-p="layers"]')
        row = _row(pg, SID)
        assert row and not row["lock"] and not row["hid"], ("되살린 화면이 잠겨/숨겨 있다", row)
        assert not errors, errors
    finally:
        pg.close()
        shutil.rmtree(tmp, ignore_errors=True)
