"""움직이는 화면(안내 단계)의 메모 상태 Model — modules/memo-state.js 순수 함수 단위 테스트(node). 브라우저 없음.

capture(v): 화면이 답에 실은 지금 상태 {hd, trail} → 메모에 적을 view {hd|null, trail(최근 30개 경로)} | null(옛 화면 = 상태 없음).
same(n, now): 메모를 단 때 상태와 지금 상태(hd-located 답 {hd, items{키: {rect, how, now:{text, shown}}}})가 같은가 — view 없는 옛 메모는 늘 같음. hd 가 있으면 그것만, 없으면 대상의 보이는 글 + 보이는지.
plan(view): 그 단계로 가는 차례 — 'hd'(화면 약속 window.hdGoto) 먼저, 'replay'(클릭 기록 다시 하기) 다음.
side(top, bottom, obstacles): 칩 줄 자리 — 위가 비면 위, 위가 막히고 아래가 비면 아래.
row(count, avail, chipW, gap): 한 줄에 보일 칩 수와 '+N'.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/memo-state.js', 'utf8'), {filename: 'memo-state.js'});
const M = globalThis.HD.memoState, out = {};
const many = Array.from({length: 35}, (_, i) => '#b' + i);
out.capture = [M.capture(null), M.capture('x'), M.capture({hd: 'beat-2', trail: ['#next', '#next']}),
               M.capture({hd: '', trail: ['#a', 3, '', '#b']}), M.capture({trail: many}), M.capture({})];
const tip = {path: '#tip', text: '둘째 단계 둘'}, body = {path: 'body', text: '화면'};
const memo = (view, targets) => ({id: 'm1', screen: 's', targets: targets || [tip], view});
const at = (o) => ({hd: o.hd, items: {'m1:0': o.it && o.it.rect !== undefined ? o.it : {rect: null, how: 'path', now: o.it}}});
out.old = [M.same(memo(undefined), at({it: {text: '전혀 다른 글', shown: true}})), M.same(memo(null), at({it: {text: '', shown: false}}))];
const tv = {hd: null, trail: ['#next']};
out.textSame = M.same(memo(tv), at({it: {text: '둘째  단계 둘', shown: true}}));
out.textOther = M.same(memo(tv), at({it: {text: '셋째 단계 셋', shown: true}}));
out.hidden = M.same(memo(tv), at({it: {text: '둘째 단계 둘', shown: false}}));
out.noAnswer = [M.same(memo(tv), null), M.same(memo(tv), {hd: null, items: {}}), M.same(memo(tv), at({it: {rect: null, how: 'none'}}))];
out.cut = [M.same(memo(tv, [{path: '#tip', text: 'a'.repeat(40)}]), at({it: {text: 'a'.repeat(52), shown: true}})),
           M.same(memo(tv, [{path: '#tip', text: '짧은'}]), at({it: {text: '짧은 글 더', shown: true}}))];
out.bodyOnly = M.same(memo(tv, [body]), at({it: {text: '다른', shown: false}}));
const hv = {hd: 'beat-6', trail: []};
out.hd = [M.same(memo(hv), at({hd: 'beat-6', it: {text: '아무 글', shown: true}})), M.same(memo(hv), at({hd: 'beat-7', it: {text: '둘째 단계 둘', shown: true}})),
          M.same(memo(hv), at({hd: undefined, it: {text: '아무 글', shown: true}})), M.same(memo(hv), at({hd: null, it: {text: '둘째 단계 둘', shown: true}}))];
out.plan = [M.plan({hd: 'b', trail: ['#n']}), M.plan({hd: 'b', trail: []}), M.plan({hd: null, trail: ['#n']}), M.plan({hd: null, trail: []}), M.plan(null)];
let tr = [];
for (let i = 0; i < 33; i++) tr = M.record(tr, '#p' + i);
out.record = [tr.length, tr[0], tr[29], M.record(['#a'], '').length, M.record(null, '#a')];
const B = (x, y, w, h) => ({x, y, w, h});
out.side = [M.side(B(0, 0, 100, 20), B(0, 500, 100, 20), []), M.side(B(0, 0, 100, 20), B(0, 500, 100, 20), [B(90, 5, 30, 10)]),
            M.side(B(0, 0, 100, 20), B(0, 500, 100, 20), [B(90, 5, 30, 10), B(0, 505, 10, 10)]), M.side(B(0, 0, 100, 20), B(0, 500, 100, 20), [B(100, 0, 10, 10)])];
out.row = [M.row(2, 100, 20, 4), M.row(5, 100, 20, 4), M.row(0, 100, 20, 4), M.row(3, 10, 20, 4)];
out.preview = [M.preview({no: 26, note: '여기에도 다음 버튼이 있어서'}), M.preview({no: 3, note: 'x'.repeat(300)}).length];
out.fail = M.FAIL;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-memo-state-js-"))
    try:
        (tmp / "t.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "t.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_capture_keeps_state_and_last_30_clicks(out):
    c = out["capture"]
    assert c[0] is None and c[1] is None, "화면이 상태를 싣지 않음(옛 palette) = 상태 없음 — 옛 메모처럼 늘 보임"
    assert c[2] == {"hd": "beat-2", "trail": ["#next", "#next"]}
    assert c[3] == {"hd": None, "trail": ["#a", "#b"]}, "빈 단계 값 = 없음, 경로 아닌 것은 버린다"
    assert c[4]["trail"] == ["#b%d" % i for i in range(5, 35)], "최근 30개만"
    assert c[5] is None, "단계 값도 클릭도 없음 = 처음 실린 화면 — 상태를 적지 않는다(글이 바뀌면 파일이 바뀐 것 = 요소를 찾을 수 없음)"


def test_old_memo_always_same(out):
    assert out["old"] == [True, True], "상태 없는 옛 메모는 지금처럼 늘 보인다"


def test_text_snapshot_decides_step(out):
    assert out["textSame"] is True, "공백만 다른 글은 같은 단계"
    assert out["textOther"] is False, "같은 요소의 글이 바뀜 = 다른 단계"
    assert out["hidden"] is False, "대상이 숨음 = 다른 단계"
    assert out["noAnswer"] == [True, True, True], "아직 모르면(답 없음·그 대상 답 없음·palette 가 now 를 안 실음) 숨기지 않는다"
    assert out["cut"] == [True, False], "40자 이상으로 잘린 스냅숏은 앞부분 맞춤, 짧은 글은 그대로 같아야"
    assert out["bodyOnly"] is True, "핀이 될 대상이 없으면 점선도 없으니 늘 같음"


def test_screen_state_value_wins(out):
    assert out["hd"] == [True, False, True, False], "단계 값이 있으면 그것만 본다(글 무시) · 옛 palette(모름)는 숨기지 않고, 화면이 단계를 안 알리면(null) 다름"


def test_plan_tries_screen_goto_then_replay(out):
    assert out["plan"] == [["hd", "replay"], ["hd"], ["replay"], [], []]


def test_record_keeps_last_30(out):
    n, first, last, empty, fresh = out["record"]
    assert (n, first, last) == (30, "#p3", "#p32")
    assert empty == 1, "빈 경로는 적지 않는다"
    assert fresh == ["#a"]


def test_strip_side_top_unless_blocked(out):
    assert out["side"] == ["top", "bottom", "top", "top"], "위가 막히면 아래 · 둘 다 막히면 위 · 맞닿기만 하면 막힘 아님"


def test_row_fits_chips_with_more(out):
    assert out["row"] == [{"show": 2, "more": 0}, {"show": 3, "more": 2}, {"show": 0, "more": 0}, {"show": 0, "more": 3}]


def test_preview_and_fail_text(out):
    p, n = out["preview"]
    assert p == "메모 26 — 여기에도 다음 버튼이 있어서"
    assert n <= 150
    assert out["fail"] == "이 단계로 바로 갈 수 없어요 — 직접 넘겨 주세요"
