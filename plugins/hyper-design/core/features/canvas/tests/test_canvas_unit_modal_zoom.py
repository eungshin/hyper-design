"""크게 보기 확대(R57 C) Model — modules/modal-zoom.js 순수 함수(node). 브라우저 없음.

열 때 = 폭 맞추기(100% 넘게 키우지 않음) — 긴 화면은 크게 보기 안에서 아래로 굴린다. 짧은 화면(폰처럼 화면 전체를 보여도 폭 맞추기와
크게 다르지 않은 것)은 지금처럼 전체가 보인다. Ctrl+휠 = 커서 자리 확대, Ctrl+= / Ctrl+- = 정한 단계, 10%~400%. 창은 내용만큼(칸까지) 자라고 가운데에 있다."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")
JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/modal-zoom.js', 'utf8'), {filename: 'modal-zoom.js'});
const Z = globalThis.HD.modalZoom, o = {};
o.range = [Z.MIN, Z.MAX, Z.clamp(0.01), Z.clamp(9), Z.clamp(0.5), Z.clamp(NaN)];
// 칸 1100×800
o.fitPhone = Z.fit(390, 844, 1100, 800);          // 전체 보기 0.948 — 폭 맞추기(1)와 크게 다르지 않음 = 지금처럼 전체
o.fitTall = Z.fit(1440, 4000, 1100, 800);          // 상세·긴 웹 = 폭 맞추기
o.fitTallSb = Z.fit(1440, 4000, 1100, 800, 12);    // 세로 굴림 막대만큼 덜
o.fitSmall = Z.fit(320, 50, 1100, 800);            // 광고 = 100% 에서 멈춤
o.fitWide = Z.fit(1440, 1024, 1100, 800);          // 데스크톱 = 전체(폭이 먼저 닿음 0.764)
o.viewTall = Z.view(1440, 4000, o.fitTall, 1100, 800);
o.viewSmall = Z.view(320, 50, 1, 1100, 800);
o.viewSb = Z.view(1000, 4000, 1, 1100, 800, 12);   // 세로로 굴리면 막대 자리만큼 창이 넓다
o.scroll = [Z.scroll(1440, 4000, 0.5, {w: 720, h: 800}, -10, 99999), Z.scroll(1440, 4000, 0.5, {w: 720, h: 800}, 30, 300)];
// 커서 자리 확대: 창이 칸에 꽉 찼을 때(가로·세로 모두 굴림) 커서 밑 내용 점이 그대로
const st = {cw: 1440, ch: 4000, s: 1, x: 200, y: 1000, aw: 1100, ah: 800};
const p = {x: 100, y: -50};                         // 창 가운데에서 커서까지
const a = Z.at(st, 2, p);
o.at = a;
o.under = [(st.x + p.x + 550) / st.s, (st.y + p.y + 400) / st.s, (a.x + p.x + a.w / 2) / a.s, (a.y + p.y + a.h / 2) / a.s];
o.atClamp = Z.at(st, 40, p).s;
o.atEdge = Z.at({cw: 1440, ch: 4000, s: 1, x: 0, y: 0, aw: 1100, ah: 800}, 0.5, {x: -500, y: -390});   // 줄이면 굴림이 음수가 되지 않는다
o.steps = [Z.step(1, 1), Z.step(1, -1), Z.step(0.76, 1), Z.step(0.76, -1), Z.step(4, 1), Z.step(0.1, -1), Z.step(1.04, 1)];
o.wheel = [Z.wheel(1, -100) > 1, Z.wheel(1, 100) < 1, Z.wheel(4, -500), Z.wheel(0.1, 500)];
o.pct = [Z.pct(0.7643), Z.pct(2), Z.pct(0.1)];
console.log(JSON.stringify(o));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-modal-zoom-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_range_is_10_to_400_percent(out):
    assert out["range"] == [0.1, 4, 0.1, 4, 0.5, 1], "깨진 값 = 100%"


def test_open_fits_width_capped_at_100_short_screens_whole(out):
    assert abs(out["fitPhone"] - 800 / 844) < 1e-6, "폰 = 지금처럼 전체가 보인다"
    assert abs(out["fitTall"] - 1100 / 1440) < 1e-6, "긴 화면 = 폭 맞추기(굴림)"
    assert abs(out["fitTallSb"] - 1088 / 1440) < 1e-6
    assert out["fitSmall"] == 1, "작은 화면을 100% 넘게 키우지 않는다"
    assert abs(out["fitWide"] - 1100 / 1440) < 1e-6, "데스크톱 = 전체(폭이 먼저 닿음)"


def test_window_grows_with_content_up_to_the_box(out):
    assert out["viewTall"] == {"w": 1100, "h": 800}
    assert out["viewSmall"] == {"w": 320, "h": 50}
    assert out["viewSb"] == {"w": 1012, "h": 800}


def test_scroll_is_clamped(out):
    assert out["scroll"][0] == {"x": 0, "y": 1200}
    assert out["scroll"][1] == {"x": 0, "y": 300}, "창보다 좁은 쪽은 0"


def test_zoom_at_cursor_keeps_point_under_cursor(out):
    a, u = out["at"], out["under"]
    assert a["s"] == 2 and (a["w"], a["h"]) == (1100, 800)
    assert abs(u[0] - u[2]) < 0.6 and abs(u[1] - u[3]) < 0.6, u
    assert out["atClamp"] == 4
    e = out["atEdge"]
    assert e["x"] == 0 and e["y"] == 0 and e["s"] == 0.5


def test_steps_and_wheel_and_label(out):
    assert out["steps"] == [1.1, 0.9, 0.8, 0.75, 4, 0.1, 1.1]
    assert out["wheel"][:2] == [True, True] and out["wheel"][2:] == [4, 0.1]
    assert out["pct"] == ["76%", "200%", "10%"]
