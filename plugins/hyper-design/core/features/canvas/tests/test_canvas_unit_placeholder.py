"""생성 중 빈 틀(S5) Model — modules/placeholder.js 순수 함수 단위 테스트(node). 브라우저 없음.

빈 레이아웃을 보내면(받는 곳이 있음) 그 카드 틀 pending · 대기열이면 아님 · 진행/claim 이 판에 없는 화면을 말하면 screen 틀 ·
파일이 쓰이면 arriving · 카드가 생기거나 승격되면 done · 질문·release·연결 끊김·빌드 실패·오래 조용함 = failed(까닭) ·
[지우기] 뒤에는 다시 보내기 전까지 안 뜸 · 카메라는 다 보이면 안 움직이고, 안 보이면 모자란 만큼만.
"""
import json, shutil, subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "modules"
NODE = shutil.which("node")

JS = r"""
const fs = require('fs'), vm = require('vm');
vm.runInThisContext(fs.readFileSync(process.argv[1] + '/placeholder.js', 'utf8'), {filename: 'placeholder.js'});
const P = globalThis.HD.placeholder, out = {};
const cards = new Set(['home', 'pay']);
const at = (x) => Object.assign({t: 1000, has: (id) => cards.has(id), drafts: {L1: 'new-a'}, promoted: {}, working: {}}, x || {});
const run = (s, evs, x) => { let fx = []; for (const e of evs) { const r = P.step(s, e, at(x)); s = r.s; fx = fx.concat(r.fx); } return {s, fx}; };
const st = (r, id) => r.s.items[id] ? r.s.items[id].state : null;
const sent = {type: 'request.sent', via: 'event', to: 'a1', notes: ['L1'], text: 'x'};

// 보내기
let r = run(P.initial(), [{type: 'agent.hello', agent: {id: 'a1', name: '클로드'}}, sent]);
out.sent = {state: st(r, 'new-a'), by: r.s.items['new-a'].by, fx: r.fx.map(f => f.do), look: P.look(r.s.items['new-a'])};
out.queue = st(run(P.initial(), [Object.assign({}, sent, {via: 'queue'})]), 'new-a');
out.otherNote = Object.keys(run(P.initial(), [Object.assign({}, sent, {notes: ['zz']})]).s.items).length;
const base = r.s;
const s0 = JSON.stringify(base);

// 진행·claim
out.progNew = st(run(P.initial(), [{type: 'agent.progress', agent: 'a1', text: '만드는 중', screen: 'coupon'}]), 'coupon');
out.progKind = run(P.initial(), [{type: 'agent.progress', agent: 'a1', text: 'x', screen: 'coupon'}]).s.items.coupon.kind;
out.progKnown = Object.keys(run(P.initial(), [{type: 'agent.progress', agent: 'a1', text: 'x', screen: 'home'}]).s.items).length;
out.progDraft = run(P.initial(), [{type: 'agent.progress', agent: 'a1', text: 'x', screen: 'new-a'}]).s.items['new-a'].kind;
out.claimNew = st(run(P.initial(), [{type: 'claim', screen: 'coupon', by: 'a1', rev: 3}]), 'coupon');

// 도착
out.written = st(run(base, [{type: 'screen.written', screens: ['coupon'], by: 'ai', rev: 4}]), 'new-a');
r = run(base, [{type: 'screen.written', screens: ['coupon'], by: 'ai', rev: 4}]);
out.landing = r.fx.filter(f => f.do === 'landing').map(f => f.ids);
out.writtenOld = st(run(base, [{type: 'screen.written', screens: ['home'], by: 'ai', rev: 4}]), 'new-a');
r = run(P.initial(), [{type: 'agent.progress', agent: 'a1', text: 'x', screen: 'coupon'}, {type: 'screen.written', screens: ['coupon'], by: 'ai', rev: 5}]);
out.screenArr = st(r, 'coupon');
cards.add('coupon'); r = run(r.s, [{type: 'scan'}]); cards.delete('coupon');
out.screenDone = {left: Object.keys(r.s.items).length, fx: r.fx};
out.replied = st(run(base, [{type: 'agent.reply', note: 'L1', kind: '반영됨', screen: 'new-a', status: 'done'}]), 'new-a');
r = run(base, [{type: 'scan'}], {drafts: {}, promoted: {'new-a': 'pay'}});
out.promoted = {left: Object.keys(r.s.items).length, fx: r.fx};
r = run(base, [{type: 'scan'}], {drafts: {}});
out.deleted = r.fx;

// 실패
out.question = run(base, [{type: 'agent.reply', note: 'L1', kind: '질문', screen: 'new-a'}]).s.items['new-a'];
out.confirm = st(run(base, [{type: 'agent.reply', note: 'L1', kind: '확인'}]), 'new-a');
out.release = run(base, [{type: 'release', screen: 'new-a', rev: 9}]).s.items['new-a'].why;
out.releaseArr = st(run(base, [{type: 'agent.reply', note: 'L1', kind: '반영됨'}, {type: 'release', screen: 'new-a', rev: 9}]), 'new-a');
out.away = run(base, [{type: 'agent.away', agent: 'a1', reason: 'bye'}]).s.items['new-a'].why;
out.awayOther = st(run(base, [{type: 'agent.away', agent: 'b2', reason: 'bye'}]), 'new-a');
out.build = run(base, [{type: 'build.failed', reason: 'parse error', screens: ['coupon'], reverted: []}]).s.items['new-a'];
out.buildOther = st(run(base, [{type: 'build.failed', reason: 'x', screens: ['home'], reverted: []}]), 'new-a');
out.tickSoon = st(run(base, [{type: 'tick'}], {t: 1000 + P.TIMEOUT_MS - 1}), 'new-a');
out.tickLate = st(run(base, [{type: 'tick'}], {t: 1000 + P.TIMEOUT_MS + 1}), 'new-a');
out.failLook = P.look(run(base, [{type: 'agent.away', agent: 'a1'}]).s.items['new-a']);
out.retry = st(run(base, [{type: 'agent.away', agent: 'a1'}, sent]), 'new-a');

// 지우기
r = run(base, [{type: 'agent.away', agent: 'a1'}, {type: 'clear', id: 'new-a'}]);
out.cleared = {left: Object.keys(r.s.items).length, fx: r.fx.map(f => f.do)};
out.clearedScan = Object.keys(run(r.s, [{type: 'scan'}], {working: {'new-a': 1}}).s.items).length;
out.clearedResend = st(run(r.s, [sent]), 'new-a');
out.resendForgets = 'new-a' in run(r.s, [sent]).s.cleared;
out.seed = st(run(P.initial(), [{type: 'scan'}], {working: {'new-a': 1}}), 'new-a');
out.pure = JSON.stringify(base) === s0;

// 카메라
const view = {w: 1000, h: 800, z: 0.5, tx: 0, ty: 0};
out.inView = P.reveal({x: 100, y: 100, w: 200, h: 400}, view);
out.right = P.reveal({x: 1100, y: 100, w: 200, h: 400}, view);
out.big = P.reveal({x: 100, y: 100, w: 200, h: 1400}, view);
out.centre = P.reveal({x: 100, y: 100, w: 200, h: 400}, view, {centre: true});
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def res():
    if not NODE:
        pytest.skip("node 가 PATH 에 없음")
    p = subprocess.run([NODE, "-e", JS, str(MOD)], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_sending_a_blank_layout_to_a_receiver_starts_its_frame(res):
    assert res["sent"]["state"] == "pending" and res["sent"]["by"] == "클로드" and res["sent"]["fx"] == ["show"]
    assert res["sent"]["look"] == {"state": "pending", "title": "만드는 중…", "sub": "클로드", "shimmer": True, "clear": False}
    assert res["queue"] is None, "대기열 = 아무도 일하지 않음 — 틀 없음"
    assert res["otherNote"] == 0
    assert res["seed"] == "pending", "새로고침 뒤: 보냈고 덮개가 일하는 중이면 틀"
    assert res["pure"]


def test_progress_or_claim_on_a_screen_without_a_card_starts_a_screen_frame(res):
    assert res["progNew"] == "pending" and res["progKind"] == "screen" and res["claimNew"] == "pending"
    assert res["progKnown"] == 0, "판에 있는 화면은 틀이 아님"
    assert res["progDraft"] == "draft"


def test_file_landing_moves_to_arriving_then_done(res):
    assert res["written"] == "arriving" and res["landing"] == [["coupon"]]
    assert res["writtenOld"] == "pending", "판에 있던 화면 쓰기는 새 화면이 아님"
    assert res["screenArr"] == "arriving"
    assert res["screenDone"] == {"left": 0, "fx": [{"do": "done", "id": "coupon", "to": "coupon"}]}
    assert res["replied"] == "arriving"
    assert res["promoted"] == {"left": 0, "fx": [{"do": "done", "id": "new-a", "to": "pay"}]}
    assert res["deleted"] == [{"do": "drop", "id": "new-a"}], "사람이 빈 레이아웃을 지움 = 조용히 없앰"


def test_failures_stop_the_frame_with_a_reason(res):
    q = res["question"]
    assert q["state"] == "failed" and "질문" in q["why"]
    assert res["confirm"] == "pending"
    assert res["release"] == "파일 없이 작업이 끝났어요" and res["releaseArr"] == "arriving"
    assert res["away"] == "AI 연결이 끊겼어요" and res["awayOther"] == "pending"
    assert res["build"]["state"] == "failed" and res["build"]["why"].startswith("빌드가 깨졌어요") and res["buildOther"] == "pending"
    assert res["tickSoon"] == "pending" and res["tickLate"] == "failed"
    assert res["failLook"]["shimmer"] is False and res["failLook"]["clear"] is True and res["failLook"]["title"] == "만들지 못했어요"
    assert res["retry"] == "pending", "다시 보내면 다시 만드는 중"


def test_clear_removes_the_frame_until_sent_again(res):
    assert res["cleared"] == {"left": 0, "fx": ["paint", "drop"]}
    assert res["clearedScan"] == 0 and res["clearedResend"] == "pending" and res["resendForgets"] is False


def test_camera_moves_only_as_much_as_needed(res):
    assert res["inView"] is None
    r = res["right"]
    assert r["z"] == 0.5 and r["ty"] == 0 and abs(r["tx"] - (-348)) < 1e-6, r     # 1100+200 → 오른쪽 여백 48 안으로
    b = res["big"]
    assert abs(b["z"] - 704 / 2800) < 1e-9 and abs(200 * b["z"] + b["ty"] - 48) < 1e-6, b    # 안 들어가면 그만큼 축소, 위 여백 48
    c = res["centre"]
    assert abs(c["tx"] + (200 + 200) * c["z"] - 500) < 1e-6 and abs(c["ty"] + (200 + 400) * c["z"] - 400) < 1e-6, c
