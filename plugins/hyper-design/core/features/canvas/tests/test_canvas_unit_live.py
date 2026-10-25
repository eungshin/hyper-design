"""실시간 알림 Model — modules/live.js 순수 함수 단위 테스트(node, task 47-4b). 브라우저 없음.

plan: 이벤트 하나 → 캔버스가 할 일(상태 다시 읽기 · 카드 다시 싣기 · 데이터 새로 · AI 기록 · 되돌리기) — rev 가 새것일 때만, 이미 본 쓰기(stamp)는 한 번만,
  도우미 되살리기(notify)의 지켜보기 메아리(ai)는 한 번 먹는다(두 번 다시 싣지 않음), 다시 받은(이어 받기) 이벤트는 건너뜀.
link: 흐름 상태 기계 — 열림 = 실시간(폴링 끔) · 오류 = 폴링 + 다시 붙기 backoff(1·2·4… 30초).
answer: async apply 답(accepted) → applied 로 읽기(예전 답은 그대로).
"""
import json, shutil, subprocess, tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[2] + '/live.js', 'utf8'), {filename: 'live.js'});
const L = globalThis.HD.live, out = {};
const ev = (id, type, o) => Object.assign({id: id, type: type, ts: 1, project: 'p'}, o || {});
const at = {rev: 5, files: 10, t: 1000};
let s = L.initial(), r;
const step = (e, a) => { r = L.plan(s, e, a || at); s = r.s; return r.acts; };
out.notesOld = step(ev(1, 'notes.changed', {rev: 5}));
out.notesNew = step(ev(2, 'notes.changed', {rev: 6}));
out.claim = step(ev(3, 'claim', {screen: 'home', rev: 7, by: 'a', note: null}));
out.releaseOld = step(ev(4, 'release', {screen: 'home', rev: 4}));
out.dup = step(ev(2, 'notes.changed', {rev: 9}));
out.aiOld = step(ev(5, 'screen.written', {screens: ['home'], by: 'ai', rev: 10, stamp: null}));
out.ai = step(ev(6, 'screen.written', {screens: ['home', 'list'], by: 'ai', rev: 11, stamp: null}));
out.human = step(ev(7, 'screen.written', {screens: ['home'], by: 'human', rev: 11, stamp: 'S1'}));
out.humanAgain = step(ev(8, 'screen.written', {screens: ['home'], by: 'human', rev: 11, stamp: 'S1'}));
let o = L.own(s, 'S2', ['list'], true, 1000); s = o.s; out.ownFresh = o.fresh;
o = L.own(s, 'S1', ['home'], false, 1000); s = o.s; out.ownSeen = o.fresh;
out.humanOwn = step(ev(9, 'screen.written', {screens: ['list'], by: 'human', rev: 11, stamp: 'S2'}));
out.echo = step(ev(10, 'screen.written', {screens: ['list', 'home'], by: 'ai', rev: 12, stamp: null}));
out.echoGone = step(ev(11, 'screen.written', {screens: ['list'], by: 'ai', rev: 13, stamp: null}));
o = L.own(s, 'S3', ['home'], true, 1000); s = o.s;
out.echoLate = step(ev(12, 'screen.written', {screens: ['home'], by: 'ai', rev: 14, stamp: null}), {rev: 5, files: 10, t: 1000 + L.ECHO_MS + 1});
out.aiWrite = step(ev(13, 'ai.write', {seq: 1, stamp: 'x', screen: 'home', label: 'AI 반영 · home', act: 'record'}));
out.done = step(ev(14, 'build.done', {stamps: ['S4'], ids: ['e1'], screens: ['home']}));
out.failed = step(ev(15, 'build.failed', {reason: '빌드 실패', reverted: ['e2'], kept: [], ids: ['e2'], stamps: ['S5'], screens: ['home'], repaired: true}));
out.failedSync = step(ev(16, 'build.failed', {reason: 'x', reverted: ['g1'], kept: [], ids: ['g1'], stamps: [], screens: [], repaired: null}));
out.started = step(ev(17, 'build.started', {stamps: [], ids: [], screens: []}));
out.reset = step({id: 500, type: 'reset', reason: 'too-old', last: 500});
out.last = s.last;
out.afterReset = step(ev(400, 'notes.changed', {rev: 99}));
out.bad = [L.plan(s, null, at).acts, L.plan(s, {type: 'claim'}, at).acts, L.plan(s, ev(600, 'nope', {}), at).acts];
// 흐름 상태 기계
let k = L.initial(), lk;
const lnk = a => { lk = L.link(k, a); k = lk.s; return {mode: k.mode, poll: lk.poll, retry: lk.retry}; };
out.link = [lnk({type: 'error'}), lnk({type: 'error'}), lnk({type: 'error'}), lnk({type: 'open'}), lnk({type: 'error'})];
out.backoff = [1, 2, 3, 4, 5, 6, 7, 20].map(L.backoff);
out.first = L.initial().mode;
// async 답
out.answer = [L.answer({accepted: ['a'], failed: [], stamp: 'S', changed: ['home'], rev: 3, async: true}),
              L.answer({applied: ['b'], stamp: 'T', changed: []}), L.answer(null)];
// stamp 기억은 끝이 있다
let big = L.initial(); for (let i = 0; i < L.SEEN_MAX + 50; i++) big = L.own(big, 'z' + i, [], false, 0).s;
out.seenCap = Object.keys(big.seen).length;
out.oldForgotten = L.own(big, 'z0', [], false, 0).fresh;
// 도장 없는 사람 쓰기(되살리기 keep 없음): 이벤트·캔버스 답 어느 쪽이 먼저 와도 한 번만
let q = L.initial(), qr;
qr = L.plan(q, ev(1, 'screen.written', {screens: ['home'], by: 'human', rev: 1, stamp: null}), {rev: 0, files: 0, t: 1000}); q = qr.s; out.nsEvent = qr.acts;
o = L.own(q, null, ['home'], false, 1200); q = o.s; out.nsOwnAfter = o.fresh;
o = L.own(q, null, ['list'], false, 1300); q = o.s; out.nsOwnFirst = o.fresh;
qr = L.plan(q, ev(2, 'screen.written', {screens: ['list', 'home'], by: 'human', rev: 1, stamp: null}), {rev: 0, files: 0, t: 1400}); q = qr.s; out.nsEventAfter = qr.acts;
o = L.own(q, null, ['home'], false, 1400 + L.RECENT_MS + 1); out.nsLate = o.fresh;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def out():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    tmp = Path(tempfile.mkdtemp(prefix="hd-live-js-"))
    try:
        (tmp / "c.js").write_text(JS, encoding="utf-8")
        r = subprocess.run([NODE, str(tmp / "c.js"), str(MOD)], capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, r.stderr
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_state_events_refetch_only_when_rev_is_newer(out):
    assert out["notesOld"] == [], "rev 가 지금과 같으면 다시 읽지 않는다"
    assert out["notesNew"] == [{"do": "state"}]
    assert out["claim"] == [{"do": "state"}]
    assert out["releaseOld"] == []


def test_replayed_event_is_skipped(out):
    assert out["dup"] == [], "이미 받은 id(이어 받기로 다시 옴)는 건너뛴다"


def test_ai_write_reloads_cards_unless_files_seq_already_seen(out):
    assert out["aiOld"] == [], "폴링이 이미 본 파일 seq 이하 = 건너뜀"
    assert out["ai"] == [{"do": "cards", "ids": ["home", "list"], "seq": 11}]


def test_human_write_refreshes_data_once_per_stamp(out):
    assert out["human"] == [{"do": "data", "ids": ["home"], "stamp": "S1"}]
    assert out["humanAgain"] == []
    assert out["ownFresh"] is True and out["ownSeen"] is False, "캔버스가 스스로 다시 실으려는 쓰기가 이벤트로 이미 왔으면 다시 싣지 않는다"
    assert out["humanOwn"] == [], "캔버스가 이미 다시 실은 쓰기(stamp)의 이벤트 = 건너뜀"


def test_stampless_human_write_reloads_once_either_order(out):
    assert out["nsEvent"] == [{"do": "data", "ids": ["home"], "stamp": "e1"}]
    assert out["nsOwnAfter"] is False, "이벤트가 방금 실은 화면 = 캔버스 답은 다시 싣지 않음"
    assert out["nsOwnFirst"] is True
    assert out["nsEventAfter"] == [{"do": "data", "ids": ["home"], "stamp": "e2"}], "캔버스가 방금 실은 화면(list)은 이벤트가 건너뜀"
    assert out["nsLate"] is True, "RECENT_MS 가 지나면 다시"


def test_restore_echo_is_eaten_once_and_expires(out):
    assert out["echo"] == [{"do": "cards", "ids": ["home"], "seq": 12}], "되살리기 메아리(list)는 먹고 나머지만"
    assert out["echoGone"] == [{"do": "cards", "ids": ["list"], "seq": 13}], "메아리는 한 번만"
    assert out["echoLate"] == [{"do": "cards", "ids": ["home"], "seq": 14}], "ECHO_MS 가 지나면 진짜 AI 쓰기"


def test_ai_write_build_and_reset_actions(out):
    assert out["aiWrite"] == [{"do": "aiWrites"}]
    assert out["done"] == [{"do": "built", "ids": ["e1"]}]
    assert out["failed"] == [{"do": "revert", "ids": ["e2"], "why": "빌드 실패", "screens": ["home"]}]
    assert out["failedSync"] == [], "동기 apply 의 실패는 요청 답이 이미 말했다(repaired null)"
    assert out["started"] == []
    assert out["reset"] == [{"do": "state"}, {"do": "files"}, {"do": "aiWrites"}]
    assert out["last"] == 500 and out["afterReset"] == [], "reset 뒤 기준 id = last"
    assert out["bad"] == [[], [], []]


def test_link_state_machine_falls_back_and_backs_off(out):
    assert out["first"] == "connecting"
    assert out["link"] == [{"mode": "polling", "poll": True, "retry": 1000}, {"mode": "polling", "poll": True, "retry": 2000},
                           {"mode": "polling", "poll": True, "retry": 4000}, {"mode": "live", "poll": False, "retry": None},
                           {"mode": "polling", "poll": True, "retry": 1000}]
    assert out["backoff"] == [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000]


def test_async_answer_reads_as_applied(out):
    a, b, c = out["answer"]
    assert a["applied"] == ["a"] and a["accepted"] == ["a"] and a["async"] is True
    assert b["applied"] == ["b"]
    assert c == {}


def test_seen_stamps_are_bounded(out):
    assert out["seenCap"] <= 200
    assert out["oldForgotten"] is True
