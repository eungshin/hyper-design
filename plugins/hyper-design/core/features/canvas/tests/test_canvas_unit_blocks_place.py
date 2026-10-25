"""요소 막대 자리·크기(polish-1) — blocks.place 가 둘레 글 상자(others)를 비켜 위 → 아래 → 옆 중 빈 곳을 고르고,
blocks.fit·barLimit 이 막대가 요소 칸보다 넓으면 뒤 단추를 "⋯" 로 넘긴다. 상자 고정 입력(node), DOM 없음."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/blocks.js', 'utf8'), {filename: 'blocks.js'});
const B = globalThis.HD.blocks, out = {};
const R = (x, y, w, h) => ({x: x, y: y, w: w, h: h});
const V = R(0, 0, 1000, 800), S = {w: 200, h: 26}, A = R(100, 300, 200, 20);
out.free = B.place(A, S, V, null, [R(100, 100, 200, 20)]);                       // 글이 멀리 — 그대로 위
out.prevText = B.place(A, S, V, null, [R(100, 276, 200, 18)]);                  // 바로 위 줄 글 → 아래
out.upDown = B.place(A, S, V, null, [R(100, 276, 200, 18), R(100, 326, 200, 18)]);   // 위·아래 모두 글 → 오른쪽 옆
out.allButLeft = B.place(R(400, 300, 200, 20), S, V, null, [R(400, 276, 200, 18), R(400, 326, 200, 18), R(606, 300, 200, 20)]);
out.least = B.place(A, S, V, null, [R(100, 290, 10, 4), R(100, 326, 300, 30), R(306, 300, 300, 30), R(0, 300, 99, 30)]);   // 어디든 겹침 → 가장 적게(위)
out.inside = B.place(A, S, V, null, [R(110, 302, 50, 16)]);                      // 고른 요소 안 글은 비킬 것이 아님
out.hard = B.place(A, S, V, R(0, 260, 1000, 40), [R(100, 326, 200, 18)]);         // 위는 창 제목 막대(단단) · 아래는 글 → 옆
out.avoidList = B.place(R(100, 300, 260, 20), S, V, [R(0, 0, 1000, 10), R(340, 250, 40, 30)], [R(100, 276, 50, 18), R(100, 326, 300, 18)]);   // 비킬 것 여러 개(도구 막대) — 위 왼쪽 맞춤 = 글 · 위 오른쪽 맞춤 = 도구 막대 · 아래 = 글
out.rightAlign = B.place(R(100, 300, 400, 20), {w: 150, h: 26}, V, null, [R(100, 276, 100, 18)]);   // 왼쪽 맞춤 위는 글 → 오른쪽 맞춤 위
out.noOthers = B.place(A, S, V, null);                                           // 예전처럼(others 없음)
out.bad = B.place(A, S, V, null, [null, {x: 'a'}, R(100, 276, 200, 18)]);        // 깨진 상자는 건너뜀
const anchors = [R(100, 300, 200, 20), R(0, 0, 300, 30), R(700, 760, 290, 30), R(50, 50, 900, 700)];
const texts = [R(90, 270, 400, 28), R(90, 324, 400, 28), R(0, 40, 1000, 10), R(600, 700, 400, 50)];
out.never = anchors.map(a => { const p = B.place(a, S, V, null, texts); return p.over || !(p.x < a.x + a.w && p.x + S.w > a.x && p.y < a.y + a.h && p.y + S.h > a.y); });
out.fit = [B.fit([50, 50, 50, 50], 300, 30), B.fit([50, 50, 50, 50], 150, 30), B.fit([50, 50, 50, 50], 10, 30), B.fit([], 100, 30), B.fit([50, 50, 50, 50], 200, 30)];
out.limit = [B.barLimit(R(0, 0, 100, 20), V), B.barLimit(R(0, 0, 600, 20), V), B.barLimit(R(0, 0, 600, 20), R(0, 0, 200, 800))];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-blocks-place-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_free_space_above_keeps_the_bar_above(js):
    assert js["free"] == {"x": 100, "y": 300 - 26 - 6, "below": False, "side": "", "over": False}, js["free"]
    assert js["noOthers"] == js["free"], "others 가 없으면 예전 자리 그대로"


def test_text_line_above_sends_the_bar_below(js):
    assert js["prevText"] == {"x": 100, "y": 300 + 20 + 6, "below": True, "side": "", "over": False}, js["prevText"]
    assert js["bad"] == js["prevText"], "깨진 상자는 건너뛰고 나머지로 판단"


def test_text_above_and_below_sends_the_bar_beside(js):
    assert js["upDown"]["side"] == "right" and js["upDown"]["x"] == 100 + 200 + 6, js["upDown"]
    assert js["allButLeft"]["side"] == "left" and js["allButLeft"]["x"] == 400 - 200 - 6, js["allButLeft"]


def test_when_every_spot_overlaps_the_least_covered_wins(js):
    assert js["least"]["y"] == 300 - 26 - 6 and not js["least"]["below"] and js["least"]["side"] == "", js["least"]


def test_text_inside_the_selected_element_is_not_an_obstacle(js):
    assert js["inside"] == js["free"], js["inside"]


def test_window_title_bar_stays_hard_and_text_is_soft(js):
    assert js["hard"]["side"] == "right", ("위 = 창 제목 막대(절대 안 됨), 아래 = 글 → 옆", js["hard"])


def test_every_hard_rect_in_an_avoid_list_is_respected(js):
    p = js["avoidList"]
    assert p["side"] == "right" and p["x"] == 100 + 260 + 6, ("위 왼쪽 맞춤 = 글 · 위 오른쪽 맞춤 = 도구 막대(단단) · 아래 = 글 → 옆", p)


def test_right_aligned_above_is_tried_before_going_below(js):
    assert js["rightAlign"] == {"x": 100 + 400 - 150, "y": 300 - 26 - 6, "below": False, "side": "", "over": False}, js["rightAlign"]


def test_bar_never_covers_the_selected_element(js):
    assert all(js["never"]), js["never"]


def test_fit_moves_tail_buttons_to_the_more_menu(js):
    assert js["fit"] == [4, 2, 1, 0, 4], ("다 들어가면 전부 · 아니면 ⋯ 자리를 남기고 앞에서부터 · 최소 1", js["fit"])


def test_bar_limit_is_the_element_width_with_a_floor_inside_the_view(js):
    assert js["limit"] == [220, 600, 200 - 16], js["limit"]
