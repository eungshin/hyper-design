"""48a 스며드는 교체 — 순수 규칙(node, 브라우저 없음).

HD.swap(swap.js, Model): 화면 파일이 바뀐 카드를 어떻게 바꿀지.
- 안 실린 카드(화면 밖, data-src) = 옛 길(lazy) · 실린 카드 = 숨긴 두 번째 iframe 에 미리 싣기(preload)
- 다 실렸을 때: 그 카드를 만지는 중(끌기·글자 고치기·메모 창·크게 보기·카드 글 고치기) = 미룸(알약) · 움직임 줄이기 = 바로 · 아니면 0.2초 겹쳐 바꿈
- 같은 카드에 새 교체가 오면 앞 것은 낡음(늦게 온 load 를 무시)
- 실패(시간 초과·HTTP 4xx/5xx) = 옛 화면 그대로 + 그 카드의 실패 줄 글
HD.busy(busy.js) 덧: "방금 반영됨 ✓" 칩 — AI 덮개가 걷힌 카드가 교체를 마치면 DONE_MS 동안. 손으로 걷은(×) 카드는 아님.
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
for (const f of ['busy.js', 'swap.js']) vm.runInThisContext(fs.readFileSync(process.argv[2] + '/' + f, 'utf8'), {filename: f});
const S = globalThis.HD.swap, B = globalThis.HD.busy, out = {};
out.consts = {FADE_MS: S.FADE_MS, LOAD_MS: S.LOAD_MS, PILL: S.PILL, DONE_MS: B.DONE_MS};
out.plan = [S.plan({live: true}), S.plan({live: false}), S.plan(null), S.plan({})];
const none = {moving: [], memo: null, edit: null, caption: [], modal: null};
out.touch = {
  idle: S.touching('a', none),
  moving: S.touching('a', Object.assign({}, none, {moving: ['b', 'a']})),
  movingOther: S.touching('a', Object.assign({}, none, {moving: ['b']})),
  memo: S.touching('a', Object.assign({}, none, {memo: 'a'})),
  edit: S.touching('a', Object.assign({}, none, {edit: 'a'})),
  caption: S.touching('a', Object.assign({}, none, {caption: ['a']})),
  modal: S.touching('a', Object.assign({}, none, {modal: 'a'})),
  modalOther: S.touching('a', Object.assign({}, none, {modal: 'b'})),
  bad: [S.touching('a', null), S.touching('', Object.assign({}, none, {memo: ''})), S.touching('a', {moving: 'a'})]
};
out.next = [
  S.next({phase: 'loading'}, {touching: false, reduced: false}),
  S.next({phase: 'ready'}, {touching: true, reduced: false}),
  S.next({phase: 'ready'}, {touching: true, reduced: true}),
  S.next({phase: 'ready'}, {touching: false, reduced: true}),
  S.next({phase: 'ready'}, {touching: false, reduced: false}),
  S.next(null, {touching: false, reduced: false}),
  S.next({phase: 'ready'}, null)
];
let s = S.initial();
const s1 = S.reduce(s, {type: 'start', id: 'a', url: 'screens/a.html?v=1'});
const j1 = s1.jobs.a;
const s2 = S.reduce(s1, {type: 'start', id: 'a', url: 'screens/a.html?v=2'});
const j2 = s2.jobs.a;
out.seq = {first: j1.phase, url2: j2.url, newer: j2.seq > j1.seq, startCopies: s1 !== s && s.jobs.a === undefined};
out.stale = {readyOld: S.reduce(s2, {type: 'ready', id: 'a', seq: j1.seq}) === s2, current1: S.current(s2, 'a', j1.seq), current2: S.current(s2, 'a', j2.seq)};
const s3 = S.reduce(s2, {type: 'ready', id: 'a', seq: j2.seq});
out.ready = s3.jobs.a.phase;
out.endOld = S.reduce(s3, {type: 'end', id: 'a', seq: j1.seq}) === s3;
out.end = Object.keys(S.reduce(s3, {type: 'end', id: 'a', seq: j2.seq}).jobs);
out.badActions = [S.reduce(s3, null) === s3, S.reduce(s3, {type: 'start', id: '', url: 'x'}) === s3, S.reduce(s3, {type: 'start', id: 'b'}) === s3,
                  S.reduce(s3, {type: 'nope'}) === s3, S.reduce(s3, {type: 'ready', id: 'zz', seq: 1}) === s3];
out.pending = S.pending(S.reduce(S.reduce(s3, {type: 'start', id: 'b', url: 'b.html'}), {type: 'start', id: 'c', url: 'c.html'})).sort();
out.failed = [S.failed({timedOut: true}), S.failed({status: 404}), S.failed({status: 500}), S.failed({status: 200}), S.failed({status: 0}), S.failed({}), S.failed(null)];
out.why = S.errorText('HTTP 404');
out.board = ['screens/a.html', 'screens/a.html?v=w1', 'screens/a.html?v=1#top', 'http://127.0.0.1:5/x.html'].map(S.boardUrl);
// "방금 반영됨 ✓" — 덮개가 걷힌(파일이 바뀐) 카드가 교체를 마치면
out.doneLook = B.lookDone();
let r = {};
let d = B.landed(r, {type: 'lifted', ids: ['a', 'b'], at: 100});
out.landed1 = {rec: Object.keys(d.rec).sort(), show: d.show};
const sw = B.landed(d.rec, {type: 'swapped', id: 'a', at: 200});
out.landedSwap = {rec: Object.keys(sw.rec), show: sw.show};
out.landedOther = B.landed(sw.rec, {type: 'swapped', id: 'z', at: 200}).show;
out.landedOld = B.landed({a: 100}, {type: 'swapped', id: 'a', at: 100 + B.LANDED_WAIT + 1}).show;
out.landedBad = [B.landed(null, {type: 'swapped', id: 'a', at: 1}).show, B.landed({}, null).show, B.landed({}, {type: 'lifted', ids: 'a', at: 1}).rec];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def r():
    if not NODE:
        pytest.skip("node 없음")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.js"
        p.write_text(JS, encoding="utf-8")
        res = subprocess.run([NODE, str(p), str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_constants(r):
    assert r["consts"] == {"FADE_MS": 200, "LOAD_MS": 10000, "PILL": "새 버전 준비됨 · 반영", "DONE_MS": 2000}


def test_unloaded_card_keeps_lazy_path(r):
    assert r["plan"] == ["preload", "lazy", "lazy", "lazy"]


def test_touching_card_is_only_that_card(r):
    t = r["touch"]
    assert t["idle"] is False
    assert (t["moving"], t["memo"], t["edit"], t["caption"], t["modal"]) == (True, True, True, True, True)
    assert t["movingOther"] is False and t["modalOther"] is False
    assert t["bad"] == [False, False, False], "깨진 신호 = 만지지 않음(교체가 막히지 않게)"


def test_next_step(r):
    assert r["next"] == ["wait", "defer", "defer", "instant", "fade", "wait", "fade"]


def test_newer_swap_makes_older_load_stale(r):
    assert r["seq"] == {"first": "loading", "url2": "screens/a.html?v=2", "newer": True, "startCopies": True}
    assert r["stale"] == {"readyOld": True, "current1": False, "current2": True}
    assert r["ready"] == "ready" and r["endOld"] is True and r["end"] == []
    assert r["badActions"] == [True, True, True, True, True]
    assert r["pending"] == ["a", "b", "c"]


def test_failure_reason(r):
    assert r["failed"] == ["시간 초과", "HTTP 404", "HTTP 500", None, None, None, None]
    assert r["why"] == "새 버전을 싣지 못했어요(HTTP 404) — 옛 화면을 그대로 둬요"


def test_board_url_matches_shell(r):
    assert r["board"] == ["screens/a.html?hd-mode=board", "screens/a.html?v=w1&hd-mode=board", "screens/a.html?v=1&hd-mode=board#top",
                          "http://127.0.0.1:5/x.html?hd-mode=board"]


def test_done_chip_only_after_ai_lift(r):
    assert r["doneLook"]["kind"] == "done" and r["doneLook"]["text"] == "방금 반영됨 ✓" and r["doneLook"]["title"]
    assert r["landed1"] == {"rec": ["a", "b"], "show": False}
    assert r["landedSwap"] == {"rec": ["b"], "show": True}
    assert r["landedOther"] is False, "덮개가 걷히지 않은 카드(직접 쓰기) = 칩 없음"
    assert r["landedOld"] is False
    assert r["landedBad"] == [False, False, {}]
