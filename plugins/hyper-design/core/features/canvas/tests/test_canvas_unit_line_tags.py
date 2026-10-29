"""선 태그 Model(R46) — modules/line-tags.js + graph.overview 의 트리거 수, 순수 함수 단위 테스트(node). 브라우저 없음.

한 선(방향) = 태그 하나: 트리거 하나면 그 버튼 글, 여럿이면 "첫 글 외 N"(같은 글 버튼도 하나씩 센다), 이름이 있으면 이름.
자리: 태그 쪽 끝 점(양방향의 다른 쪽 = 끝 점)에서 시작, 겹치면 제 선을 따라 비킴 — 한도(max·share) 밖으로는 가지 않고, 떠 있는 막대(avoid)는 늘 피한다.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const n of ['graph', 'line-tags']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + n + '.js', 'utf8'), {filename: n + '.js'});
const G = globalThis.HD.graph, T = globalThis.HD.lineTags, out = {};

out.one = T.text({texts: ['서가'], n: 1});
out.many = T.text({texts: ['사용 방법', '도움말', '자주 묻는 질문'], n: 6});
out.sameText = T.text({texts: ['도움말'], n: 2});
out.named = T.text({texts: ['서가', '보기'], n: 2, name: '  설정 이동 '});
out.pend = T.text({texts: [], n: 0, pend: true});
out.empty = T.text({texts: [], n: 0});
out.noCount = T.text({texts: ['a', 'b']});
out.badCount = T.text({texts: ['a'], n: 'x'});
out.blankTexts = T.text({texts: ['  ', null, '다음'], n: 2});

// graph.overview: 같은 쌍 한 방향 버튼 6개(같은 글 하나 포함) → 선 하나, 글 5개(중복 없음), 트리거 6 · 반대 방향 1 · 끊기 대기 하나는 뺀 수
const e = (f, t, l) => ({from: f, to: t, kind: 'link', label: l});
const g = {screens: [], edges: [e('job', 'use', '사용 방법'), e('job', 'use', '도움말'), e('job', 'use', '자주 묻는 질문'), e('job', 'use', '튜토리얼'),
                              e('job', 'use', '가이드'), e('job', 'use', '도움말'), e('use', 'job', '뒤로')]};
const ov = G.overview(g, {});
out.pairs = ov.length;
out.ov = {lab: ov[0].lab, n: ov[0].n};
out.dropOne = G.overview(g, {drop: {'job>use': 1}})[0].n;
out.tagFromOverview = T.text({texts: ov[0].lab.ab, n: ov[0].n.ab}).text;

// 자리: 아래로 떠나는 선(세로 → 가로) — 끝 점 쪽(ba)은 거꾸로
const r = {pts: [[100, 200], [100, 300], [400, 300]]};
out.anchorA = T.anchor(r, 0); out.anchorB = T.anchor(r, 1);
out.fromB = T.from(r, 1);
out.anchorBad = T.anchor({pts: [[1, 2]]}, 0);
out.walk = [T.walk(r.pts, 50), T.walk(r.pts, 150), T.walk(r.pts, 9999)];

// seat: 같은 점에서 떠나는 세 선(한 묶음) — 태그 높이 16 · 폭 60
const down = [[100, 0], [100, 200], [400, 200]], other = [[100, 0], [100, 120], [-200, 120]];
out.seatOne = T.seat([{pts: down, w: 60, h: 16}]);
out.seatThree = T.seat([{pts: down, w: 60, h: 16}, {pts: other, w: 60, h: 16}, {pts: down, w: 60, h: 16}]);
// 한도: 선이 짧아 비킬 데가 없으면 시작 자리 그대로(겹침, free:false)
const short = [[0, 0], [0, 40]];
out.seatCap = T.seat([{pts: short, w: 60, h: 16}, {pts: short, w: 60, h: 16}, {pts: short, w: 60, h: 16}]);
out.seatMax = T.seat([{pts: down, w: 60, h: 16}, {pts: down, w: 60, h: 16}, {pts: down, w: 60, h: 16}], {max: 10});
// 짧은 양방향 가로선(72px): 두 끝의 태그가 아래·위로 갈린다
const bi = [[0, 100], [72, 100]];
out.seatBi = T.seat([{pts: bi, w: 70, h: 16}, {pts: bi.slice().reverse(), w: 51, h: 16}]);
// 막대(avoid) 밑에는 놓지 않는다
out.seatAvoid = T.seat([{pts: down, w: 60, h: 16}], {avoid: [{l: 0, t: 0, r: 300, b: 60}, {l: 'x'}]});
// 한도 안이 다 막대(줄 제목 등)면 한도를 넘어 제 선 위 막대 없는 첫 자리 · 선 전체가 막대 밑이면 숨김(hidden — 누르기를 가로막지 않게)
const tall = [[0, 0], [0, 300]];
out.seatPastCap = T.seat([{pts: tall, w: 60, h: 16}], {avoid: [{l: -100, t: -10, r: 100, b: 150}]});
out.seatHidden = T.seat([{pts: tall, w: 60, h: 16}], {avoid: [{l: -100, t: -10, r: 100, b: 310}]});
out.seatBad = T.seat([null, {pts: [[0, 0]], w: 1, h: 1}, {pts: down, w: NaN, h: 1}]);
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 없음")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.js"
        p.write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(p), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)


def test_tag_text_one_line_one_tag(out):
    assert out["one"] == {"text": "서가", "more": 0, "named": False}
    assert out["many"] == {"text": "사용 방법 외 5", "more": 5, "named": False}, "트리거 6 = 첫 글 외 5(다 못 보인 수)"
    assert out["sameText"] == {"text": "도움말 외 1", "more": 1, "named": False}, "같은 글 버튼도 하나씩 센다"
    assert out["named"] == {"text": "설정 이동", "more": 1, "named": True}, "이름이 있으면 이름(목록 창은 버튼 글을 보인다)"
    assert out["pend"]["text"] == "반영 대기" and out["empty"]["text"] == ""
    assert out["noCount"]["text"] == "a 외 1", "수를 모르면 글 수"
    assert out["badCount"]["text"] == "a"
    assert out["blankTexts"]["text"] == "다음 외 1", "빈 글은 버리고 수는 그대로"


def test_overview_counts_every_trigger(out):
    assert out["pairs"] == 1, "쌍마다 선 하나(E20)"
    assert out["ov"]["lab"]["ab"] == ["사용 방법", "도움말", "자주 묻는 질문", "튜토리얼", "가이드"]
    assert out["ov"]["n"] == {"ab": 6, "ba": 1}, "예전엔 앞 두 글만 보이고 나머지 트리거는 사라졌다"
    assert out["dropOne"] == {"ab": 5, "ba": 1}, "끊기 대기는 뺀 수"
    assert out["tagFromOverview"] == "사용 방법 외 5"


def test_anchor_is_the_lines_own_exit_point(out):
    assert out["anchorA"] == [100, 200] and out["anchorB"] == [400, 300], "태그 쪽 끝 점 — 카드 오른쪽 틈에 쌓지 않는다"
    assert out["fromB"] == [[400, 300], [100, 300], [100, 200]]
    assert out["anchorBad"] is None
    assert out["walk"] == [{"x": 100, "y": 250, "dir": "v"}, {"x": 150, "y": 300, "dir": "h"}, {"x": 400, "y": 300, "dir": "h"}]


def touches(p, pts, w=60, h=16):
    """태그 상자(가운데 p)가 제 선에서 2px 안 — 선 위든 선 옆이든 선에 붙어 있다."""
    l, t, r, b = p["x"] - w / 2 - 2.01, p["y"] - h / 2 - 2.01, p["x"] + w / 2 + 2.01, p["y"] + h / 2 + 2.01
    for a, c in zip(pts, pts[1:]):
        if max(a[0], c[0]) >= l and min(a[0], c[0]) <= r and max(a[1], c[1]) >= t and min(a[1], c[1]) <= b:
            return True
    return False


def test_seat_slides_along_own_line_within_cap(out):
    down, other = [[100, 0], [100, 200], [400, 200]], [[100, 0], [100, 120], [-200, 120]]
    assert out["seatOne"] == [{"x": 132, "y": 10, "d": 10, "free": True, "side": 0}], "시작 = 카드 가장자리에서 태그 반 칸 + 2, 세로 마디 오른쪽에 붙음"
    a, b, c = out["seatThree"]
    assert all(s["free"] for s in (a, b, c))
    for s, pts in ((a, down), (b, other), (c, down)):
        assert touches(s, pts), ("태그는 제 선에 붙는다", s)
    boxes = [(s["x"] - 30, s["y"] - 8, s["x"] + 30, s["y"] + 8) for s in (a, b, c)]
    for i, p in enumerate(boxes):
        for q in boxes[i + 1:]:
            assert not (p[0] < q[2] + 3 and p[2] + 3 > q[0] and p[1] < q[3] + 3 and p[3] + 3 > q[1]), ("겹치지 않음", boxes)
    assert [x["free"] for x in out["seatCap"]] == [True, True, False]
    assert out["seatCap"][2] == {"x": 32, "y": 10, "d": 10, "free": False, "side": 0}, "한도(선 길이 × share) 안에 자리가 없으면 시작 자리 — 목록처럼 쌓지 않는다"
    assert out["seatMax"][2]["free"] is False and out["seatMax"][2]["d"] == 10, "max 한도"
    a, b = out["seatBi"]
    assert a["free"] and b["free"] and a["side"] == 0 and b["side"] == 1, ("짧은 양방향 선: 아래·위로 갈림", a, b)
    assert a["y"] > 100 > b["y"]


def test_seat_avoids_floating_bars_and_skips_bad_items(out):
    s = out["seatAvoid"][0]
    assert s["y"] - 8 >= 60 + 3, ("막대 밑에 놓지 않는다", s)
    assert out["seatBad"] == [None, None, None]


def test_seat_leaves_the_cap_to_clear_a_heading_and_hides_when_the_whole_line_is_covered(out):
    """R46 회귀(전체 실행 4904741): 줄 제목 옆을 지나는 짧은 선의 태그가 제목을 덮어 제목 두 번 누르기·[보기]를 가로막았다."""
    s = out["seatPastCap"][0]
    assert s["y"] - 8 >= 150 + 3, ("한도 안이 다 막대면 한도 밖 막대 없는 자리", s)
    assert touches(s, [[0, 0], [0, 300]]) and not s.get("hidden"), s
    h = out["seatHidden"][0]
    assert h["hidden"] is True and h["free"] is False, ("선 전체가 막대 밑 = 숨김", h)
    assert "hidden" not in out["seatOne"][0], "보이는 태그에는 hidden 칸이 없다(예전 출력 그대로)"
