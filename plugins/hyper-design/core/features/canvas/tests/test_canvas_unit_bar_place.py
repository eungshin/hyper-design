"""요소 막대 자리(t51-7a) — bar-place.js(Model): 고른 요소·꼬리표를 덮지 않고 그 바깥 바로 위 → 아래 → 조금 더 위·아래 → 옆,
둘레 내용(형제·글)을 덮지 않는 첫 자리 · 보이는 칸 안 · 다른 막대(#selbar·창 제목·도구 막대)는 절대 덮지 않음. 상자 고정 입력(node), DOM 없음."""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parent.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/bar-place.js', 'utf8'), {filename: 'bar-place.js'});
const P = globalThis.HD.barPlace, out = {};
const R = (x, y, w, h) => ({x: x, y: y, w: w, h: h});
const V = R(0, 0, 1000, 800), S = {w: 200, h: 26}, A = R(100, 300, 200, 20);
const at = (o) => P.place(Object.assign({anchor: A, size: S, view: V}, o));
out.free = at({content: [R(100, 100, 200, 20)]});
out.none = at({});
out.label = at({label: R(100, 283, 30, 14)});
out.lineAbove = at({content: [R(100, 276, 200, 18)]});                                   // 바로 위 줄 → 아래
out.bothSides = at({content: [R(100, 276, 200, 18), R(100, 326, 200, 18)]});            // 위·아래 줄 → 위 줄 위로 조금 올림
out.selbar = at({bars: [R(0, 260, 1000, 40)], content: [R(100, 326, 200, 18)]});        // 위 = 다른 막대(절대) · 아래 = 글 한 줄 → 그 줄 아래로 조금
out.selbarTall = at({bars: [R(0, 260, 1000, 40)], content: [R(100, 326, 200, 60)]});    // 아래 내용이 높아 멀어짐 → 그래도 아래(가장 적게 덮음) — 옆은 위·아래가 막힐 때만
out.tall = P.place({anchor: R(100, 20, 300, 770), size: S, view: V});                    // 위·아래가 보이는 칸 밖 → 오른쪽 옆
out.tallRight = P.place({anchor: R(700, 20, 290, 770), size: S, view: V});               // 오른쪽도 밖 → 왼쪽 옆
out.blocked = P.place({anchor: R(400, 300, 200, 20), size: S, view: V, bars: [R(395, 260, 210, 40), R(395, 318, 210, 40)], content: [R(606, 295, 300, 30)]});   // 위·아래 = 다른 막대 → 옆(내용을 덜 덮는 왼쪽)
out.selbarOnly = at({bars: R(50, 250, 300, 40)});                                       // 막대 하나(목록 아님)도 — 아래로
out.clamp = P.place({anchor: R(950, 300, 40, 20), size: S, view: V});
out.clip = P.place({anchor: R(300, 120, 80, 20), size: S, view: R(200, 100, 500, 600)}); // 보이는 칸(크게 보기 창) 위가 모자람 → 아래
out.over = P.place({anchor: R(0, 0, 1000, 800), size: S, view: V});
out.inside = at({content: [R(110, 302, 50, 16)]});                                       // 고른 요소 안 글 = 비킬 것 아님
out.container = at({content: [R(0, 0, 1000, 800), R(50, 200, 400, 300)]});               // 감싼 상자(조상·배경) = 비킬 것 아님
out.bad = at({content: [null, {x: 'a'}, R(100, 276, 200, 18)], bars: [null, {w: 3}]});
// 크게 보기 타일 장면(t51-5): 첫 타일, 위 = 안내 글(조금 떨어짐), 아래·옆 = 다른 타일
const tile = R(70, 497, 165, 66), MV = R(30, 163, 1080, 706), TS = {w: 217, h: 24};
const tiles = [R(244, 497, 165, 66), R(417, 497, 165, 66), R(70, 571, 165, 66), R(244, 571, 165, 66), R(417, 571, 165, 66)];
out.tiles = P.place({anchor: tile, size: TS, view: MV, content: tiles.concat([R(70, 450, 500, 20), R(70, 398, 500, 35)])});
// 판 제목 장면(t51-3): 꼬리표 + 위 줄(설정 1 / 3) + 아래 줄
out.heading = P.place({anchor: R(86, 225, 328, 26), label: R(84, 212, 26, 13), size: {w: 274, h: 24}, view: R(0, 32, 1140, 968),
                       content: [R(86, 208, 328, 12), R(86, 258, 328, 15)]});
// 무엇을 주든: 'over' 가 아니면 고른 요소·꼬리표·다른 막대를 덮지 않고 보이는 칸 안
const hit = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
const anchors = [R(100, 300, 200, 20), R(0, 0, 300, 30), R(700, 760, 290, 30), R(50, 50, 900, 700), R(400, 40, 100, 20)];
const texts = [R(90, 270, 400, 28), R(90, 324, 400, 28), R(0, 40, 1000, 10), R(600, 700, 400, 50)], bars = [R(380, 0, 240, 36)];
out.never = anchors.map(a => {
  const lb = R(a.x, a.y - 14, 30, 13), p = P.place({anchor: a, label: lb, size: S, view: V, bars: bars, content: texts}), r = R(p.x, p.y, S.w, S.h);
  return p.side === 'over' || (!hit(r, a) && !hit(r, lb) && !bars.some(b => hit(r, b)) && r.x >= 0 && r.y >= 0 && r.x + r.w <= 1000 && r.y + r.h <= 800);
});
// 카드 선택 막대(R27 F07): 판 칸 = 대화 도크(0..340) 오른쪽 340..1140
const BV = R(340, 32, 800, 968), BS = {w: 226, h: 38};
out.cardFree = P.card({cards: R(500, 400, 400, 300), size: BS, view: BV, lift: 18});
out.cardUnderDock = P.card({cards: R(-49, 387, 498, 314), size: BS, view: BV, lift: 18});   // 카드 대부분이 도크 밑
out.cardOff = P.card({cards: R(-3157, 387, 498, 314), size: BS, view: BV, lift: 18});      // 판 칸 밖 전부
out.cardRightEdge = P.card({cards: R(1100, 400, 400, 300), size: BS, view: BV, lift: 18});
out.cardAboveTop = P.card({cards: R(500, -200, 400, 600), size: BS, view: BV, lift: 18});
out.cardTools = P.card({cards: R(-49, 387, 498, 314), size: BS, view: BV, lift: 18, bars: [R(352, 350, 48, 335)]});   // 판 왼쪽 도구 막대를 비킴
out.cardBad = P.card({cards: null, size: BS, view: BV});
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-bar-place-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _xy(p):
    return (p["x"], p["y"], p["side"])


def test_free_space_puts_the_bar_just_above_left_aligned(js):
    assert _xy(js["free"]) == (100, 300 - 6 - 26, "above"), js["free"]
    assert js["none"] == js["free"] and js["free"]["cover"] == 0


def test_bar_sits_above_the_label_not_on_it(js):
    assert _xy(js["label"]) == (100, 283 - 6 - 26, "above"), js["label"]


def test_line_directly_above_flips_the_bar_below(js):
    assert _xy(js["lineAbove"]) == (100, 300 + 20 + 6, "below"), js["lineAbove"]
    assert js["bad"] == js["lineAbove"], "깨진 상자는 건너뛰고 나머지로 판단"


def test_lines_above_and_below_lift_the_bar_just_past_the_line_above(js):
    assert _xy(js["bothSides"]) == (100, 276 - 6 - 26, "above"), js["bothSides"]


def test_other_floating_bars_are_never_covered(js):
    assert _xy(js["selbar"]) == (100, 326 + 18 + 6, "below"), js["selbar"]
    assert _xy(js["selbarTall"])[:1] + _xy(js["selbarTall"])[2:] == (100, "below") and js["selbarTall"]["cover"] > 0, js["selbarTall"]


def test_sides_only_when_above_and_below_have_no_room(js):
    assert js["tall"]["side"] == "right" and js["tall"]["x"] == 100 + 300 + 6, js["tall"]
    assert js["tallRight"]["side"] == "left" and js["tallRight"]["x"] == 700 - 200 - 6, js["tallRight"]
    assert js["blocked"]["side"] == "left" and js["blocked"]["cover"] == 0, js["blocked"]
    assert _xy(js["selbarOnly"]) == (100, 300 + 20 + 6, "below"), js["selbarOnly"]


def test_bar_is_clamped_inside_the_view(js):
    c = js["clamp"]
    assert c["side"] == "above" and c["x"] == 950 + 40 - 200, ("오른쪽 끝 요소 = 막대 오른쪽을 요소 오른쪽에 맞춤", c)
    assert _xy(js["clip"]) == (300, 120 + 20 + 6, "below"), ("보이는 칸 위가 모자라면 아래", js["clip"])
    assert js["over"]["side"] == "over", "보이는 칸을 다 덮는 요소만 겹친다"


def test_content_inside_or_around_the_pick_is_not_an_obstacle(js):
    assert js["inside"] == js["free"] and js["container"] == js["free"], (js["inside"], js["container"])


def test_tile_scene_keeps_the_bar_above_off_the_neighbour_tiles(js):
    p = js["tiles"]
    assert p["side"] == "above" and p["y"] + 24 <= 497 and p["cover"] == 0, ("첫 타일 — 아래 타일을 덮지 않고 위 빈 틈에", p)


def test_heading_scene_clears_the_line_above_and_the_label(js):
    p = js["heading"]
    assert p["side"] == "above" and p["y"] + 24 <= 208 - 3, ("제목 — 위 줄('설정 1 / 3')에 닿지 않게 그 위로", p)


def test_bar_never_covers_the_pick_label_or_other_bars(js):
    assert all(js["never"]), js["never"]


def test_card_bar_stays_inside_the_board_and_off_the_side_dock(js):
    f = js["cardFree"]
    assert not f["hidden"] and f["cx"] == 700 and f["y"] == 400 - 38 - 18, f
    d = js["cardUnderDock"]
    assert not d["hidden"] and d["cx"] - 226 / 2 >= 340 + 8, ("도크 밑으로 나간 카드 — 막대 왼쪽 끝은 판 칸 안", d)
    r = js["cardRightEdge"]
    assert r["cx"] + 226 / 2 <= 1140 - 8, r
    t = js["cardTools"]
    assert t["cx"] - 226 / 2 >= 352 + 48, ("판 위 도구 막대와 겹치지 않음", t)
    assert js["cardAboveTop"]["y"] == 32 + 8, ("카드 위가 판 칸 밖 — 막대는 판 칸 맨 위", js["cardAboveTop"])


def test_card_bar_hides_when_the_card_is_off_the_board(js):
    assert js["cardOff"]["hidden"] and js["cardBad"]["hidden"], (js["cardOff"], js["cardBad"])
